import re
from typing import Any, Dict, Union

from live_bargaining.constants import RoleConstants

Config = Dict[str, Union[int, str, bool, Dict[str, Any]]]


class C(RoleConstants):
    NAME_IN_URL = 'test'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    GROUP_NAME = "live-%s-%s-%s"

    PATTERN_CONSTRAINT = re.compile(r'\[.*?\]')
    PATTERN_OFFER = re.compile(r'\[([^\]]+)\]')

    PRICE_RANGE = (1, 13)
    QUALITY_RANGE = (0, 5)

    LLM_ERROR = 'No Connection to LLM server'
