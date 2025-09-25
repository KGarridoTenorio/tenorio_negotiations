import random
from functools import cached_property
from typing import Any, Dict, List, Union

from otree.api import *
from otree.database import db, wrap_column, AUTO_SUBMIT_DEFAULTS, OTreeColumn
from sqlalchemy.sql import sqltypes as st

from live_bargaining.offer import Offer
from live_bargaining.utils import now_datetime
from .bot_negotiation import NegotiationBot
from .constants import C
from .utils import reset_logs

AUTO_SUBMIT_DEFAULTS[st.JSON] = None


# Do not user .append / += [] (list), .update (dict) or form_fields!
def JsonField(**kwargs) -> OTreeColumn:
    return wrap_column(st.JSON, **kwargs)


class Subsession(BaseSubsession):
    def initialize_subsession(self):
        # TODO Only for testing
        reset_logs()

        config = self.session.config
        for group in self.get_groups():
            if config['market_price'] < 0:
                group.market_price = random.randint(
                    config['market_price_low'],
                    config['market_price_high'])
            else:
                group.market_price = config['market_price']
            if config['production_cost'] < 0:
                group.production_cost = random.randint(
                    config['production_cost_low'],
                    config['production_cost_high'])
            else:
                group.production_cost = config['production_cost']
            group.max_greedy = config['max_greedy']

            # Make sure all players get a Role
            for player in group.get_players():
                player._role = C.ROLES[1 - player.id_in_group % 2]
        db.commit()


def creating_session(sub_session: Subsession):
    sub_session.initialize_subsession()


class Group(BaseGroup):
    market_price = models.IntegerField()
    production_cost = models.IntegerField()
    max_greedy = models.BooleanField()


class Player(BasePlayer):
    # -1 means Bot opponent
    other_id = models.IntegerField(initial=-1)
    price_proposed = models.IntegerField()
    price_accepted = models.IntegerField()
    quality_proposed = models.IntegerField()
    quality_accepted = models.IntegerField()

    offers = JsonField(initial=[])
    chat_data = JsonField(initial=[])
    llm_interactions = JsonField()
    bot_vars = JsonField(initial={})

    time_start = models.StringField(max_length=20)
    time_end = models.StringField(max_length=20)

    @cached_property
    def other(self) -> Union['Player', NegotiationBot]:
        if self.other_id == -1:
            return NegotiationBot(self)
        raise NotImplementedError

    @property
    def bot_opponent(self) -> bool:
        return self.other_id == -1

    @property
    def proposal(self) -> str:
        price = self.field_maybe_none('price_proposed')
        quality = self.field_maybe_none('quality_proposed')
        offer = '(none)<br> '
        if None not in (price, quality):
            offer = f"€ {price}<br>{quality}"
        return offer

    @property
    def live_ids(self) -> List[int]:
        return [idx for idx in [self.id_in_group, self.other_id] if idx > 0]

    def process_offer(self, price: int, quality: int) -> List[Dict[str, int]]:
        """ Offer made via the interface """
        assert isinstance(self.offers, list)
        self.price_proposed = price
        self.quality_proposed = quality

        offer_user = Offer(idx=self.id_in_group, price=price, quality=quality)
        offer_user.test = "from process_offer"
        self.offers = self.offers + [offer_user]
        if not self.bot_opponent:
            self.other.offers = self.other.offers + [offer_user]            
        else:
            self.other.receive_offer_from_human(price, quality)

        return self.offers

    def process_accept(self, price: int, quality: int):
        """ User accepts the opposing offer """
        # TODO Think about timing issues: accept and new offer at the same time
        if not self.bot_opponent:
            assert price == self.other.price_proposed
            assert quality == self.other.quality_proposed
        self.time_end = self.other.time_end = now_datetime()
        self.price_accepted = self.other.price_accepted = price
        self.quality_accepted = self.other.quality_accepted = quality

    def process_chat(self, data: Dict[str, Any]) -> Dict[int, Any]:
        """ Process a chat message from the user """
        assert isinstance(self.chat_data, list)
        body = data['body']

        tmp = self.chat_data + [{'nick': f"{self.role} (Me)", 'body': body}]
        self.chat_data = tmp
        result = {self.id_in_group: {'chat': self.chat_data}}

        if not self.bot_opponent:
            tmp = self.other.chat_data + [{'nick': self.role, 'body': body}]
            self.other.chat_data = tmp
            result[self.other.id_in_group] = {'chat': self.other.chat_data}
        else:
            self.other.receive_chat_from_human(body)

        return result

    def process_llm_output(self, role: str, body: str) -> Dict[str, Any]:
        """ Send LLM output to the user """
        assert isinstance(self.chat_data, list)
        self.chat_data = self.chat_data + [{'nick': f"{role}", 'body': body}]
        return {'chat': self.chat_data}

    ############################################################################
    # This is only used on the reset page
    ############################################################################
    def reset(self, data: Dict[str, Any]) -> Dict[int, Any]:
        self.price_proposed = None
        self.price_accepted = None
        self.quality_proposed = None
        self.quality_accepted = None
        self.offers = []
        self.chat_data = []
        self.llm_interactions = None
        self.bot_vars = {}
        self.time_start = None
        self.time_end = None

        self._role = data['role']
        self.group.production_cost = data['cost']
        self.group.market_price = data['market']
        self.group.max_greedy = data['max_greedy']
        db.commit()

        reset_logs()

        return {self.id_in_group: {'chat': [], 'offers': [], }}
