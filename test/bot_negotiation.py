import asyncio
import copy

from live_bargaining.offer import Offer, OfferList
from live_bargaining.prompts import PROMPTS
from .bot_strategy import BotStrategy
from .bot_utils import InteractionList
from .constants import C


class NegotiationBot(BotStrategy):
    def __init__(self, player: 'Player'):
        super().__init__()
        self.id_in_group = -1
        self.player = player
        self.role = C.opposite(player.role)

        # Async functions loose self.player, copy what is needed
        self.config = copy.deepcopy(player.session.config)
        self.config.update({
            'idx': player.id_in_group,
            'code': player.participant.code,
            'session_code': player.session.code,
            'roles': {'human_role': player.role, 'bot_role': self.role},

            'production_cost': player.group.production_cost,
            'market_price': player.group.market_price,
            'max_greedy': player.group.max_greedy,

            'bot_vars': player.bot_vars,
        })

    @property
    def proposal(self) -> str:
        if not self.offer_list:
            return '(none)<br> '
        last_offer = self.offer_list[-1]
        return f"€ {last_offer['price']}<br>{last_offer['quality']}"

    @staticmethod
    def field_maybe_none(_: str) -> None:
        return None

    def start_initial(self):
        if self.player.field_maybe_none("llm_interactions") is None:
            self.player.llm_interactions = []
            self._offers_interactions()
            asyncio.ensure_future(self.initial())

    def receive_chat_from_human(self, user_message: str):
        # Received via the chat
        self.user_message = user_message
        self._offers_interactions()
        asyncio.ensure_future(self.follow_up())

    def receive_offer_from_human(self, price: int, quality: int):
        # Received via the interface
        self.user_message = PROMPTS['offer_string'] % (price, quality)
        self._offers_interactions()
        asyncio.ensure_future(self.interface_offer())

    def _offers_interactions(self):
        # Create offer list, new offer not added yet
        self.offer_list = OfferList(
            Offer(**offer) for offer in self.player.offers)
        # Create interactions list, add user message if needed
        assert isinstance(self.player.llm_interactions, list)
        self.interaction_list = InteractionList(self.player.llm_interactions)
        self.interaction_list.add_user_message(self.user_message)
        self.player.llm_interactions = self.interaction_list
