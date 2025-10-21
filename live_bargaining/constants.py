import re
from typing import Any, Dict, Union

from otree.api import *

Config = Dict[str, Union[int, str, bool, Dict[str, Any]]]

# TODO Not used?
ORDINALS = ['zeroth', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth',
            'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth']


class RoleConstants(BaseConstants):
    ROLE_SUPPLIER = 'Supplier'
    ROLE_BUYER = 'Buyer'
    ROLES = [ROLE_SUPPLIER, ROLE_BUYER]

    @classmethod
    def opposite(cls, role: str) -> str:
        return list(set(cls.ROLES) - {role})[0]


class C(RoleConstants):
    NAME_IN_URL = 'live_bargaining'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 10
    PRACTICE_ROUNDS = 2
    ACTUAL_ROUNDS = NUM_ROUNDS - PRACTICE_ROUNDS
    TOTAL_NEGOTIATIONS = 13
    BOT_NEGOTIATIONS = 4
    HUMAN_NEGOTIATIONS = TOTAL_NEGOTIATIONS - BOT_NEGOTIATIONS

    TYPE_CHOICES = [
        ['preference_human', 'HUMAN'],
        ['preference_bot', 'BOT'],
    ]

    GROUP_NAME = "live-%s-%s-%s"

    PATTERN_CONSTRAINT = re.compile(r'\[.*?\]')
    PATTERN_OFFER = re.compile(r'\[([^\]]+)\]')

    PRICE_MIN = 1.0
    PRICE_MAX = 12.0
    PRICE_RANGE = [x * 0.01 for x in range(300, 1201)]  # Generates 3.00 to 12.00 with a step of 0.01
    QUALITY_RANGE = range(0, 101)
    DEMAND_MIN = 0
    DEMAND_MAX = max(QUALITY_RANGE)

    LLM_ERROR = 'No Connection to LLM server'
