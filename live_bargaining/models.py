import json
import random
from functools import cached_property
from typing import Any, Dict, List, Tuple, Union

from otree.api import *
from otree.database import db, wrap_column, AUTO_SUBMIT_DEFAULTS, OTreeColumn
from sqlalchemy.sql import sqltypes as st

from .bot_negotiation import NegotiationBot
from .constants import C
from .matching import Matching
from .offer import Offer
from .session_counter import SessionCounter
from .utils import now_datetime

AUTO_SUBMIT_DEFAULTS[st.JSON] = None


# Do not user .append / += [] (list), .update (dict) or form_fields!
def JsonField(**kwargs) -> OTreeColumn:
    return wrap_column(st.JSON, **kwargs)


class Subsession(BaseSubsession, Matching):
    def initialize_subsession(self):
        BotProfits.create_new(self)

        config = self.session.config
        preference_role = config['preference_role']
        if not preference_role:
            if self.round_number == 1:
                preference_role = C.ROLES[1 - self.session.id % 2]
            else:
                group = self.get_groups()[0]
                preference_role = group.in_previous_rounds()[0].preference_role

        max_greedy = self._get_max_greedy(config)
        for group in self.get_groups():
            group.initialize_group(config, preference_role, max_greedy)

        db.commit()

    @staticmethod
    def _get_max_greedy(config: Dict[str, Any]) -> bool:
        if SessionCounter.in_greedy_list() and \
                not config['override_make_it_greedy']:
            # the first 4 sessions are non-greedy
            return False
        elif config['override_make_it_NON_greedy']:
            return False
        else:
            # the next 4 sessions are greedy
            return True


def creating_session(sub_session: Subsession):
    if sub_session.round_number == 1:
        sub_session.session.initialize()
    sub_session.initialize_subsession()


def vars_for_admin_report(sub_session: Subsession) -> Dict[str, Any]:
    actual_round_number = sub_session.get_players()[0].participant._round_number
    actual_round_number = actual_round_number or 1

    # Change to the sub_session of the current round
    sub_session = sub_session.session.get_subsessions()[actual_round_number - 1]
    # sub_session.session.debug_log[0] can be used for session wide stuff

    return {
        'actual_round_number': actual_round_number,
        'preference_role': sub_session.get_groups()[0].preference_role,
        'session_log_lines': sub_session.session.debug_log[0],
        'log_lines': sub_session.session.debug_log[actual_round_number],
    }


class Group(BaseGroup):
    preference_role = models.StringField(max_length=10)
    single_player = models.IntegerField()
    market_price = models.IntegerField()
    production_cost = models.IntegerField()
    max_greedy = models.BooleanField()
    demand=models.IntegerField()

    def initialize_group(self, config: Dict[str, Any],
                         preference_role: str, max_greedy: bool):
        self.preference_role = preference_role
        low = config['market_price_low']
        high = config['market_price_high']
        self.market_price = round(random.uniform(low, high))
        low = config['production_cost_low']
        high = config['production_cost_high']
        self.production_cost = round(random.uniform(low, high))
        self.max_greedy = max_greedy
        self.demand = random.randint(config['demand_low'], config['demand_high'])
        players = self.get_players()
        self.single_player = len(players) if len(players) % 2 == 1 else 0

        # Make sure all players get a Role
        for player in self.get_players():
            player.is_single = player.id_in_group == self.single_player
            if player.is_single:
                if player.round_number == 1:
                    player._role = random.choice(C.ROLES)
                else:
                    player._role = player.in_previous_rounds()[0]._role
            else:
                player._role = C.ROLES[1 - player.id_in_group % 2]


class Player(BasePlayer):
    # -1 means Bot opponent
    other_id = models.IntegerField(initial=-1)
    channel_id = models.StringField(max_length=100)
    is_single = models.BooleanField()
    comprehension_count = models.IntegerField(initial=0)
    comprehension_check = models.IntegerField(blank=True, min=-100)

    price_proposed = models.IntegerField()
    price_accepted = models.IntegerField()
    quality_proposed = models.IntegerField()
    quality_accepted = models.IntegerField()

    offers = JsonField(initial=[])
    chat_data = JsonField(initial=[])
    llm_interactions = JsonField()
    bot_vars = JsonField(initial={})

    preference = models.StringField(max_length=20, choices=C.TYPE_CHOICES)
    expected_profit = models.IntegerField()
    minimum_profit = models.IntegerField()

    time_start = models.StringField(max_length=20)
    time_end = models.StringField(max_length=20)

    final_payoff = models.FloatField(initial=0)
    total_profit_player = models.IntegerField(initial=0)
    avg_profit_player = models.FloatField(initial=0)
    total_profit_from_the_bot_attributable = models.IntegerField(initial=0)

    @property
    def is_supplier(self) -> bool:
        return self.role == C.ROLE_SUPPLIER

    @property
    def is_buyer(self) -> bool:
        return self.role == C.ROLE_BUYER

    @property
    def is_odd_session(self) -> bool:
        return self.session.id % 2 == 1

    @cached_property
    def other(self) -> Union['Player', NegotiationBot]:
        if self.other_id == -1:
            return NegotiationBot(self)
        return self.group.get_players()[self.other_id - 1]

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

    @property
    def is_idle(self) -> bool:
        if self.round_number == C.NUM_ROUNDS:
            if self.group.preference_role != self.role:
                if self.other_id == -1 and not self.is_single:
                    return True
        return False

    def process_offer(self, price: int, quality: int) -> List[Dict[str, int]]:
        """ Offer made via the interface """
        assert isinstance(self.offers, list)
        self.price_proposed = price
        self.quality_proposed = quality

        offer_user = Offer(idx=self.id_in_group, price=price, quality=quality)
        self.offers = self.offers + [offer_user]
        if not self.bot_opponent:
            self.other.offers = self.other.offers + [offer_user]
        else:
            self.other.receive_offer_from_human(price, quality)

        return self.offers

    def process_accept(self, price: int, quality: int):
        """ User accepts the opposing offer """
        if not self.bot_opponent:
            assert price == self.other.price_proposed
            assert quality == self.other.quality_proposed
        self.time_end = self.other.time_end = now_datetime()
        self.price_accepted = self.other.price_accepted = price
        self.quality_accepted = self.other.quality_accepted = quality
        profits = self.calculate_profits()
        self.payoff = Currency(profits[0])
        self.other.payoff = Currency(profits[1])

        if self.other_id == -1 and not self.is_single:
            BotProfits.update(self.subsession, self.other.role, profits[1])

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
        tmp = self.chat_data + [{'nick': f"{role}", 'body': body}]
        self.chat_data = tmp
        return {'chat': self.chat_data}

    def calculate_profits(self) -> Tuple[int, int]:
        demand=self.group.demand
        
        quantity_sold = min(self.quality_accepted, demand)
        unsold_quantity = min(demand-self.quality_accepted, 0)

        buyer_profit = (self.group.market_price - self.price_accepted) * quantity_sold
        supplier_profit = (self.price_accepted - self.group.production_cost) * (quantity_sold) + (self.group.production_cost * unsold_quantity)
        if self.role == C.ROLE_BUYER:
            return buyer_profit, supplier_profit
        elif self.role == C.ROLE_SUPPLIER:
            return supplier_profit, buyer_profit


class BotProfits(ExtraModel):
    sub_session = models.Link(Subsession)
    profit_role = models.LongStringField()
    selected_profits = models.LongStringField()

    @classmethod
    def create_new(cls, sub_session: Subsession):
        empty = json.dumps({C.ROLE_SUPPLIER: [], C.ROLE_BUYER: []})
        cls.create(sub_session=sub_session, profit_role=empty)

    @classmethod
    def update(cls, sub_session: Subsession, role: str, profit: int):
        # We are adding the profits that all bots are making # split by bot role
        # We can only know all bot profits at the last round
        idx = cls.filter(sub_session=sub_session)[0].id
        bod_profits = cls.objects_get(id=idx)
        profit_role = json.loads(bod_profits.profit_role)
        profit_role[role].append(profit)
        bod_profits.profit_role = json.dumps(profit_role)
        db.commit()

    @classmethod
    def select_profits(cls, group: Group):
        selected_dict = {C.ROLE_SUPPLIER: [], C.ROLE_BUYER: []}
        for sub_session in group.session.get_subsessions()[2:]:
            idx = cls.filter(sub_session=sub_session)[0].id
            bot_profits = cls.objects_get(id=idx)
            profit_role = json.loads(bot_profits.profit_role)
            for role in C.ROLES:
                random_profit = random.sample(profit_role[role] or [0], 1)
                selected_dict[role].append(random_profit)
        # Put the selected profits on the last sub_session
        bot_profits.selected_profits = json.dumps(selected_dict)
        db.commit()

    @classmethod
    def get_role_key_lists(cls, player: Player) -> List[List[int]]:
        bot_profits = BotProfits.filter(sub_session=player.subsession)[0]
        selected_profits = json.loads(bot_profits.selected_profits)
        return selected_profits[player.role]
