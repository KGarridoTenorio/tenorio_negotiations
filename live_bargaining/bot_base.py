from functools import cached_property
from typing import Optional, Tuple

from otree.database import db
from otree.models import Participant, Session

from .constants import C, Config
from .offer import Offer, OfferList
from .pareto import pareto_efficient_offer


class InteractionList(list):
    def add_user_message(self, user_message: Optional[str]):
        if user_message:
            self.append({"role": "user", "content": user_message})

    def add_bot_message(self, user_message: Optional[str]):
        if user_message:
            self.append({"role": "system", "content": user_message})


class BotBase:
    def __init__(self):
        self.client = None
        self.config: Optional[Config] = None
        self.role: Optional[str] = None
        self.user_message: Optional[str] = None
        self.offer_user: Optional[Offer] = None
        self.interaction_list: Optional[InteractionList] = None
        self.offer_list: Optional[OfferList] = None
        self.offers_pareto_efficient = None

        # The Player must be able to set these, but they will be ignored
        self.price_proposed = None
        self.price_accepted = None
        self.offers = None
        self.time_end = None

    @staticmethod
    def group_name(player: 'Player') -> str:
        return C.GROUP_NAME % (player.group.session.code,
                               player.participant._index_in_pages,
                               player.participant.code)

    @cached_property
    def constraint_user(self) -> int:
        return self.config['bot_vars'].get('final_constraint')

    @cached_property
    def constraint_bot(self) -> int:
        if self.role == C.ROLE_SUPPLIER:
            return self.config['production_cost']
        else:
            return self.config['market_price']

    def add_profits(self, offer: Offer):
        offer.profits(self.role, self.constraint_user, self.constraint_bot)

    def get_session(self) -> Session:
        return db.query(Session) \
            .filter_by(code=self.config['session_code']).one()

    def get_player_participant(self) -> Tuple['Player', Participant]:
        participant = db.query(
            Participant).filter_by(code=self.config['code']).one()
        return participant._get_current_player(), participant

    def get_greediness(self, constraint_user: int, constraint_bot: int) -> int:
        if constraint_user not in (0, None):
            return pareto_efficient_offer(constraint_user, constraint_bot,
                                          self.role, self.config['max_greedy'])
        else:
            return self.config['default_greedy']

    def constraint_in_range(self, constraint_user: Optional[int]) -> bool:
        if constraint_user is None:
            return False

        user_role = C.opposite(self.role)
        # User is Supplier, constrain to production cost
        if user_role == C.ROLE_SUPPLIER:
            return self.config['production_cost_low'] <= \
                   constraint_user <= self.config['production_cost_high']
        # User is Buyer, constrain to market price
        else:
            return self.config['market_price_low'] <= \
                   constraint_user <= self.config['market_price_high']

    def constant_draw_constraint(self) -> int:
        # Randomly draw constraint for the user
        user_role = C.opposite(self.role)
        if user_role == C.ROLE_SUPPLIER:
            return self.config['production_cost_low']
        else:
            return self.config['market_price_high']

    def add_debug_log(self, message: str):
        try:
            debug_log = self.get_session().debug_log
            debug_log[self.config['round_number']].append(message)
            db.commit()
        except Exception as e:
            return
