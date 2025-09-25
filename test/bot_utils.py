import asyncio
import logging
import random
from typing import Any, Dict, List, Optional, Tuple

import httpx
from ollama import Client
from otree.channels import utils as channel_utils
from otree.database import db
from otree.models import Participant

from live_bargaining.offer import Offer, OfferList
from live_bargaining.pareto import pareto_efficient_offer
from live_bargaining.prompts import PROMPTS
from .constants import C, Config
from .utils import log_llm_response, log_constraints, log_interpret, log_removed


class InteractionList(list):
    def add_user_message(self, user_message: Optional[str]):
        if user_message:
            self.append({"role": "user", "content": user_message})

    def add_bot_message(self, user_message: Optional[str]):
        if user_message:
            self.append({"role": "system", "content": user_message})


class BotUtils:
    def __init__(self):
        self.client = None
        self.config: Optional[Config] = None
        self.role: Optional[str] = None
        self.user_message: Optional[str] = None
        self.offer_user: Optional[Offer] = None
        self.interaction_list: Optional[InteractionList] = None
        self.offer_list: Optional[OfferList] = None
        self.offers_pareto_efficient = None

        # TODO Only for development (make extract_content static)
        self.trail = ""

        # The Player must be able to set these, but they will be ignored
        self.price_proposed = None
        self.price_accepted = None
        self.offers = None
        self.time_end = None

    @property
    def constraint_user(self) -> int:
        return self.config['bot_vars'].get('final_constraint')

    @property
    def constraint_bot(self) -> int:
        if self.role == C.ROLE_SUPPLIER:
            return self.config['production_cost']
        else:
            return self.config['market_price']

    def add_profits(self, offer: Offer):
        offer.profits(self.role, self.constraint_user, self.constraint_bot)

    def get_player_participant(self) -> Tuple['Player', 'Participant']:
        participant = db.query(
            Participant).filter_by(code=self.config['code']).one()
        return participant._get_current_player(), participant

    def send_asyncio_data(self, data: Dict[str, Any]):
        player, participant = self.get_player_participant()
        group_name = C.GROUP_NAME % (player.group.session.code,
                                     participant._index_in_pages,
                                     participant.code)
        asyncio.ensure_future(
            channel_utils.group_send(group=group_name, data=data))

    def get_greediness(self, constraint_user: int, constraint_bot: int) -> int:
        if constraint_user != 0:
            return pareto_efficient_offer(constraint_user, constraint_bot,
                                          self.role, self.config['max_greedy'])
        else:
            return self.config['default_greedy']

    @staticmethod
    def extract_content(response: Dict[str, Any]) -> str:
        try:
            content: str = response['message']['content'].strip()
        except KeyError as _:
            print(f"\nUnexpected response format: {response}\n")
            return f"\nUnexpected response format: {response}\n"

        org = content
        removed = ""

        # Remove text before the first colon
        if ':' in content:
            removed = "[:]" + content.split(':')[0].strip()
            content = content.split(':', 1)[1].strip()

        # Split the content at line breaks and take only the first part
        if '\n' in content:
            if removed:
                removed += "\n"
            removed += "[EOL]" + content.split('\n', 1)[1]
            content = content.split('\n', 1)[0]

        # Extract text within the quotes if quotes are found
        start = content.find('"') + 1
        end = content.rfind('"')
        if 0 < start < end:
            if removed:
                removed += "\n"
            removed += "[Q1]" + content[:start] + "\n[Q2]" + content[end:]
            content = content[start:end]
        else:
            # Remove text within parentheses if no quotes are found
            while '(' in content and ')' in content:
                start = content.find('(')
                end = content.find(')', start) + 1
                if 0 <= start < end:
                    if removed:
                        removed += "\n"
                    removed += "[B]" + content[start:end]
                    content = content[:start] + content[end:]

        # Remove 'System" starts
        if content.lower().startswith("system:"):
            if removed:
                removed += "\n"
            removed += "[SYS]" + content[:7]
            content = content[7:].strip()
        if content.lower().startswith("system,"):
            if removed:
                removed += "\n"
            removed += "[SYS]" + content[:7]
            content = content[7:].strip()

        if removed:
            log_removed(org, content.strip(), removed)

        return content.strip()

    def random_draw_constraint(self) -> int:
        # Randomly draw constraint for the user
        user_role = C.opposite(self.role)
        if user_role == C.ROLE_SUPPLIER:
            return random.randint(self.config['production_cost_low'],
                                  self.config['production_cost_high'])
        else:
            return random.randint(self.config['market_price_low'],
                                  self.config['market_price_high'])

    def store_send_data(self,
                        llm_output: str = None,
                        bot_vars: Dict[str, Any] = None):
        player, participant = self.get_player_participant()

        # Store bot_vars if updated
        if bot_vars:
            player.bot_vars = {**player.bot_vars, **bot_vars}

        # Store and send LLM output
        if llm_output:
            data = player.process_llm_output(self.role, llm_output)
            self.send_asyncio_data(data)
            self.interaction_list.add_bot_message(llm_output)

        # Store and send interactions
        if self.interaction_list:
            player.llm_interactions = self.interaction_list
            self.send_asyncio_data({'interactions': self.interaction_list})

        # Store and send offers
        if self.offer_list:
            player.offers = self.offer_list
            self.send_asyncio_data({'offers': self.offer_list})

        # Send trail
        if self.trail:
            self.send_asyncio_data({'trail': self.trail})

        db.commit()

    ############################################################################
    # Methods that use the LLMs
    ############################################################################
    def _ensure_client(self):
        if self.client is None:
            logging.getLogger("httpx").level = logging.WARNING
            auth = httpx.BasicAuth(username=self.config['llm_user'],
                                   password=self.config['llm_pass'])
            self.client = Client(host=self.config['llm_host'], auth=auth)

    def get_llm_response(self, messages: List[Dict[str, str]]) \
            -> Dict[str, Any]:
        # Ensure we have a client
        self._ensure_client()

        try:
            return self.client.chat(
                model=self.config['llm_model'],
                options={'temperature': self.config['llm_temp']},
                messages=messages)
        except httpx.ConnectError as _:
            self.store_send_data(llm_output=C.LLM_ERROR)

    def interpret_constraints(self, message: str) -> Optional[int]:
        # Ensure we have a client
        self._ensure_client()

        # Make the call
        content = PROMPTS['constraints'] + message
        messages = [{'role': 'user', 'content': content}]
        response = self.client.chat(model=self.config['llm_constraint'],
                                    messages=messages)
        llm_output = response['message']['content']

        # Search for the pattern in the message, return as float
        match = C.PATTERN_CONSTRAINT.search(llm_output)
        if match is None:
            # Only for testing
            log_constraints(message, llm_output)
            return

        match_str = match.group(0).replace('[', '').replace(']', '')
        if match_str:
            # Only for testing
            log_constraints(message, llm_output, match, round(float(match_str)))
            return round(float(match_str))
        else:
            # Only for testing
            log_constraints(message, llm_output, match)

    def interpret_offer(self, message: str, idx: int = None) -> Optional[Offer]:
        def get_int(p) -> Optional[int]:
            try:
                return round(float("".join(s for s in p if s.isdigit())))
            except ValueError:
                pass

        # Ensure we have a client
        self._ensure_client()

        # Defaults to User Offer
        if idx is None:
            idx = self.config['idx']

        # Make the call
        messages = [{'role': 'user',
                     'content': PROMPTS['understanding_offer'] + message}]
        response = self.client.chat(model=self.config['llm_reader'],
                                    messages=messages)
        llm_output = response['message']['content']

        # Only for testing
        log_llm_response(response)

        # TODO Handle "less than", e.g. <1

        # Regular expression to find the pattern [Price, Quality]
        price = quality = None
        match_list = list(C.PATTERN_OFFER.finditer(llm_output))
        for match in reversed(match_list):
            parts = [part.replace('<', '').replace('>', '').strip()
                     for part in match.group(1).split(',')]
            ints = [get_int(part) for part in parts]

            if len(ints) == 2:
                price, quality = ints
            elif len(ints) == 3:
                if ints[0] is not None and ints[2] is not None:
                    price, quality = ints[0], ints[2]
                elif ints[:2] == [None, None] and ints[2] is not None:
                    quality = ints[2]
                elif ints == [None, None, None]:
                    price = None
                    quality = None
                else:
                    print("\nINTS", ints)
                    raise NotImplementedError
            else:
                print("\vINTS", ints)
                raise NotImplementedError

        # Only for testing
        matches = " ".join(match.group() for match in match_list)
        log_interpret(message, llm_output, matches, price, quality)

        return Offer(idx=idx, from_chat=True, price=price, quality=quality)
