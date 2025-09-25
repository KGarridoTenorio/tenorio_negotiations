from otree.api import *

from live_bargaining.session_counter import SessionCounter

doc = """
Resets the session counter
"""


class Constants(BaseConstants):
    name_in_url = 'reset'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    pass


class ResetPage(Page):
    @staticmethod
    def before_next_page(player: Player, timeout_happened: bool):
        if not timeout_happened:
            SessionCounter.remove_key()


page_sequence = [
    ResetPage,
]
