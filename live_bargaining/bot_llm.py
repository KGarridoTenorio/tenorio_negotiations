import asyncio
import re
import logging
from typing import Any, Dict, Optional

import httpx
from ollama import AsyncClient
from otree.channels import utils as channel_utils
from otree.database import db

from .constants import C
from .offer import Offer
from .prompts import PROMPTS, system_final_prompt


class BotLLM:
    def __init__(self):
        self.get_player_participant = None
        self.role = None
        self.interaction_list = None
        self.offer_list = None
        self.client = None
        self.config = None

        self.role = None
        self.role = None
        self.role = None

        raise RuntimeError

    def send_asyncio_data(self, data: Dict[str, Any]):
        asyncio.create_task(channel_utils.group_send(
            group=self.config['group_name'], data=data))

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

        db.commit()

    @staticmethod
    def extract_content(response: Dict[str, Any]) -> str:
        def remove_inner(string: str, start_char: str, end_char: str):
            while start_char in string and end_char in string:
                start_pos = string.find(start_char)
                end_pos = string.find(end_char, start_pos) + 1
                if 0 <= start_pos < end_pos:
                    string = string[:start_pos] + string[end_pos:]
                else:
                    break
            return string
        
        def clean_leading_non_alphanum(s: str) -> str:
            # Remove all leading characters that are not a-z, A-Z, or 0-9
            return re.sub(r'^[^a-zA-Z0-9]+', '', s)

        try:
            content: str = response['message']['content'].strip()
        except KeyError as _:
            print(f"\nUnexpected response format: {response}\n")
            return f"\nUnexpected response format: {response}\n"

        # Extract text within the quotes if quotes are found
        if content.count('"') > 1:
            start = content.find('"') + 1
            end = content.rfind('"')
            x = content[start:end]
            # Prevent cases in which user introduces parameters inside ""
            if len(x) > 30:
                content = x
        else:
        # Remove 'System" starts
            if content.lower().startswith("system:"):
                content = content[7:].strip()
            if content.lower().startswith("system,"):
                content = content[7:].strip()

        # Remove text within parentheses if no quotes are found
        content = remove_inner(content, '(', ')')
        # Remove content within square brackets
        content = remove_inner(content, '[', ']')

        s = 0

        # Remove text before "optimal_offer"
        if 'optimal_offer' in content and s != 3:
            split_list = content.split('optimal_offer', 1)
            content = split_list[1].strip() if len(split_list) > 1 else content
            s+=1

        s = 0

        # Remove text before the first colon
        while ':' in content and s != 3:
            split_list = content.split(':', 1)
            content = split_list[1].strip() if len(split_list) > 1 else content
            s+=1

        s = 0

        # Remove internal thoughts
        while 'Here is the most efficient offer' in content and s != 3:
            split_list = content.split('Here is the most efficient offer', 1)
            content = split_list[1].strip() if len(split_list) > 1 else content
            s+=1

        s = 0

        while 'response' in content and s != 3:
            split_list = content.split('response', 1)
            content = split_list[1].strip() if len(split_list) > 1 else content
            s+=1

        # Cleaning text from leaading non-alphanumeric characters
        content = clean_leading_non_alphanum(content)
        # Split the content at line breaks and take only the first part
        content = content.split('\n', 1)[0]
        content = content.strip()
        content = content.strip('"')

        return content

    ############################################################################
    # Methods that use the LLMs
    ############################################################################
    def _ensure_client(self):
        if self.client is None:
            logging.getLogger("httpx").level = logging.WARNING
            auth = httpx.BasicAuth(username=self.config['llm_user'],
                                   password=self.config['llm_pass'])
            self.client = AsyncClient(host=self.config['llm_host'], auth=auth)

    async def get_llm_response(self, content: str) -> Dict[str, Any]:
        # Ensure we have a client
        self._ensure_client()

        assert isinstance(content, str)
        system_prompt = system_final_prompt(self.config)
        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}]

        return await self.client.chat(
            model=self.config['llm_model'],
            options={'temperature': self.config['llm_temp']},
            messages=messages)

    async def interpret_constraints(self, message: str) -> Optional[int]:
        # Ensure we have a client
        self._ensure_client()

        def log(result):
            file_name = \
                "live_bargaining/static/live_bargaining/debug/constraints.csv"
            cleaned_llm_output = llm_output.replace("\n", " ### ")
            with open(file_name, "a") as f:
                f.write(f"{message};{cleaned_llm_output};{result}\n")

        # Make the call
        content = PROMPTS['constraints'] + message
        messages = [{'role': 'user', 'content': content}]
        response = await self.client.chat(model=self.config['llm_constraint'],
                                          messages=messages)
        llm_output = response['message']['content']

        # Search for the pattern in the message, return as float
        match = C.PATTERN_CONSTRAINT.search(llm_output)
        if match is None:
            log(None)
            return None

        match_str = match.group(0).replace('[', '').replace(']', '')
        if match_str:
            log(round(float(match_str)))
            return round(float(match_str))
        log(None)

    async def interpret_offer(self, message: str, idx: int = None) \
            -> Optional[Offer]:
        def get_int(p) -> Optional[float]:
            try:
                return round(float("".join(s for s in p if s.isdigit() or s == '.')), 2)
            except ValueError:
                pass

        # Ensure we have a client
        self._ensure_client()

        # Defaults to User Offer
        if idx is None:
            idx = self.config['idx']

        # If user message contains at least a number -> let LLM interpret the offer
        if re.search(r'\d', message):
            messages = [{'role': 'user',
                        'content': PROMPTS['understanding_offer'] + message}]
            # Make the call
            response = await self.client.chat(model=self.config['llm_reader'],
                                            messages=messages)
            llm_output = response['message']['content']
            print('\n[DEBUG Bot_llm.interpret_offer]', llm_output + '\n')
        # Otherwise, output an empty offer [,] directly
        else:
            llm_output = '[,]'
            print('\n[DEBUG Bot_llm.interpret_offer]', llm_output + '\n')

        # Regular expression to find the pattern [Price, Quality]
        price = quality = None
        match_list = list(C.PATTERN_OFFER.finditer(llm_output))
        for match in reversed(match_list):
            parts = [part.replace('<', '').replace('>', '').strip()
                     for part in match.group(1).split(',')]
            ints = [get_int(part.replace('€', '')) for part in parts]

            if len(ints) == 1:
                price = quality = None
            elif len(ints) == 2:
                price, quality = ints
                break
            elif len(ints) == 3:
                if ints[0] is not None and ints[2] is not None:
                    price, quality = ints[0], ints[2]
                    break
                elif ints[1:] == [None, None] and ints[0] is not None:
                    price = ints[0]
                    quality = None
                    break
                elif ints[:2] == [None, None] and ints[2] is not None:
                    quality = ints[2]
                    price = None
                    break
                elif ints == [None, None, None]:
                    price = None
                    quality = None
                else:
                    price = quality = None
            else:
                price = quality = None

        file_name = "live_bargaining/static/live_bargaining/debug/interpret.csv"
        cleaned = llm_output.replace("\n", " ### ")
        with open(file_name, "a") as f:
            f.write(f"{message};{cleaned};{price};{quality}\n")

        return Offer(idx=idx, from_chat=True, price=price, quality=quality)
