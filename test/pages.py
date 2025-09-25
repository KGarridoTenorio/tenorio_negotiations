from typing import Any, Dict, Optional

from otree.api import *

from .models import Player
from live_bargaining.utils import now_datetime, get_start_time


class Test(Page):
    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        return {
            'human_role': player.role,
            'production_cost': player.group.production_cost,
            'market_price': player.group.market_price,
            'max_greedy': player.group.max_greedy,
        }

    @staticmethod
    def js_vars(player: Player) -> Dict[str, Any]:
        if player.field_maybe_none('time_start') is None:
            player.time_start = now_datetime()
        # Pass the actual start timestamp, in case the user reloads
        time_start = get_start_time(player)
        config = player.session.config
        return {
            'id_in_group': player.id_in_group,
            'bot_opponent': player.bot_opponent,
            'startTime': time_start.timestamp() * 1000,
            'messages': player.chat_data,
            'offers': player.offers,

            # Only for testing
            'production_cost_low': config['production_cost_low'],
            'production_cost_high': config['production_cost_high'],
            'market_price_low': config['market_price_low'],
            'market_price_high': config['market_price_high'],
            'max_greedy': config['max_greedy'],
        }

    @staticmethod
    def live_method(player: Player, data: Dict[str, Any]) \
            -> Optional[Dict[int, Dict[str, Any]]]:
        if data['type'] == 'reset':
            return player.reset(data)

        if data['type'] == 'initial':
            assert player.bot_opponent
            player.other.start_initial()
            return {}

        if data['type'] == 'chat':
            return player.process_chat(data)

        price = data['price']
        quality = data['quality']
        if data['type'] == 'propose':
            offers = player.process_offer(price, quality)
            return {idx: {'offers': offers} for idx in player.live_ids}
        if data['type'] == 'accept':
            player.process_accept(price, quality)
            return {idx: {'finished': True} for idx in player.live_ids}


page_sequence = [
    Test,
]
