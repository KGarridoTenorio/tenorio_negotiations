import random
from typing import Any, Dict, List, Optional, Tuple

from otree.api import *

from . import Offer
from .constants import C
from .models import Player, Group, Subsession, BotProfits
from .utils import now_datetime, get_start_time


class CustomWaitPage(WaitPage):
    template_name = 'live_bargaining/CustomWaitPage.html'

    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        if player.round_number == C.NUM_ROUNDS:
            return {
                'round_of': "",
                'this_is': "This is the last negotiation round."
            }

        actual = player.round_number - 2
        actual_4 = (actual - 1) % 4 + 1
        return {
            'round_of': f"Round {actual_4} (of 4).",
            'this_is': f"{C.NUM_ROUNDS-player.round_number} negotiation rounds left.",
        }


class MatchWaitPage(CustomWaitPage):
    wait_for_all_groups = True

    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        subsession.match_players()


class IdleWaitPage(WaitPage):
    title_text = "You are idle..."
    body_text = "Wait until your bot is done negotiating " \
                "to know your final payout."

    @staticmethod
    def is_displayed(player: Player) -> bool:
        return player.is_idle


class BotProfitWaitPage(WaitPage):
    @staticmethod
    def is_displayed(player: Player) -> bool:
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def after_all_players_arrive(group: Group):
        BotProfits.select_profits(group)


class Instructions(Page):
    form_model = 'player'

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number < 2

    @staticmethod
    def get_form_fields(player: Player) -> List[str]:
        if player.round_number >= 3:
            return ['expected_profit', 'minimum_profit']
        return []

    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        config = player.session.config
        return {
            'timeout_minutes': config['timeout_bargain'] // 60,
        }


class ComprehensionCheck(Page):
    form_model = 'player'
    form_fields = ['comprehension_check']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        config = player.session.config
        player.participant.vars['market_price'] = random.randint(
            config['market_price_low'], config['market_price_high'])
        player.participant.vars['production_cost'] = random.randint(
            config['production_cost_low'], config['production_cost_high'])
        player.participant.vars['demand'] = random.randint(
            config['demand_low'], config['demand_high'])
        player.participant.vars['price'] = random.choice(C.PRICE_RANGE)
        player.participant.vars['quality'] = random.choice(C.QUALITY_RANGE)

        return {
            'market_price': player.participant.vars['market_price'],
            'production_cost': player.participant.vars['production_cost'],
            'price': player.participant.vars['price'],
            'quality': player.participant.vars['quality'],
        }

    @staticmethod
    def error_message(player: Player, values):
        answer = values['comprehension_check']
        market_price = player.participant.vars['market_price']
        production_cost = player.participant.vars['production_cost']
        price = player.participant.vars['price']
        quality = player.participant.vars['quality']

        if player.role == C.ROLE_BUYER:
            profit = Offer.profit_buyer(price, quality, market_price)
            constraint = f"{market_price} "
            final_market_price = market_price + quality
        else:
            profit = Offer.profit_supplier(price, quality, production_cost)
            constraint = f"{production_cost}"
            final_production_cost = production_cost + quality

        if answer != profit:
            player.comprehension_count += 1
            if player.role == C.ROLE_BUYER:
                return \
                    fr"Unfortunately your answer is incorrect!<br><br>" \
                    f"Base Market Selling Price to Consumer of {constraint}" \
                    f"<br>"\
                    f"With an agreed quality of {quality}, " \
                    f"the Market Selling Price to Consumer becomes {quality} " \
                    f"+ {constraint} = {final_market_price} <br>"\
                    f"Your profit (as a {player.role}) would be calculated " \
                    f"as {constraint} + {quality} - {price} = {profit}<br>" \
                    f"Please try again with the new combination"
            else:
                return \
                    fr"Unfortunately your answer is incorrect!<br><br>" \
                    f"Base Production Cost of {constraint} <br>"\
                    f"With an agreed quality of {quality}, the Production " \
                    f"Cost becomes {quality} + {constraint} = " \
                    f"{final_production_cost} <br>"\
                    f"Your profit (as a {player.role}) would be calculated " \
                    f"as {price} - {quality} - {constraint} = {profit}<br>" \
                    f"Please try again with the new combination"


class Bargain(Page):
    @staticmethod
    def is_displayed(player: Player) -> bool:
        return not player.is_idle

    @staticmethod
    def get_timeout_seconds(player: Player) -> int:
        if player.round_number == 1:
            return player.session.config['timeout_bargain_round1']
        return player.session.config['timeout_bargain']

    @staticmethod
    def js_vars(player: Player) -> Dict[str, Any]:
        if player.field_maybe_none('time_start') is None:
            player.time_start = now_datetime()
        # Pass the actual start timestamp, in case the user reloads
        time_start = get_start_time(player)
        return {
            'id_in_group': player.id_in_group,
            'bot_opponent': player.bot_opponent,
            'startTime': time_start.timestamp() * 1000,
            'messages': player.chat_data,
            'offers': player.offers,
        }

    @staticmethod
    def live_method(player: Player, data: Dict[str, Any]) \
            -> Optional[Dict[int, Dict[str, Any]]]:
        if data['type'] == 'ping':
            return {}

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


class Results(Page):
    @staticmethod
    def get_params(player: Player) -> Tuple[str, str, int]:
        if player.field_maybe_none("price_accepted") is None:
            formatted_deal_price = ""
            formatted_profits = "€ 0"
        else:
            formatted_deal_price = f"€ {player.price_accepted}"
            formatted_profits = f"€ {int(player.payoff)}"

        total_score = max(0, sum(int(p.payoff) for p in player.in_all_rounds()))
        player.participant.payoff = total_score / 9

        return formatted_deal_price, formatted_profits, total_score

    @classmethod
    def vars_for_template(cls, player: Player) -> Dict[str, Any]:
        if player.round_number == C.NUM_ROUNDS:
            return cls.vars_for_template_last_round(player)

        formatted_deal_price, formatted_profits, total_score = \
            cls.get_params(player)
        return {
            'formatted_deal_price': formatted_deal_price,
            'formatted_profits': formatted_profits,
            'formatted_cumulative_score': f"€ {int(total_score):.2f}",
            'formatted_AVG_human_profit': f"€ {player.participant.payoff:.2f}",
            'rounds_count': int(player.round_number-2),
        }

    @classmethod
    def vars_for_template_last_round(cls, player: Player) -> Dict[str, Any]:
        formatted_deal_price, formatted_profits, total_score = \
            cls.get_params(player)

        selected_profits = BotProfits.get_role_key_lists(player)

        num_rounds_i_played = 9
        num_rounds_bot_played = 4
        if player.other_id == -1:
            # I don't have the preference
            if player.group.preference_role != player.role and \
                    not player.is_single:
                num_rounds_i_played = 8
                num_rounds_bot_played = 5
            # I have the preference
            elif player.group.preference_role == player.role:
                # Don't count the last one bc is going to be 0 idle
                selected_profits = selected_profits[:-1]

        # Calculating the sum and average of the randomly selected profits
        total_bot_profits = sum([sum(profits) for profits in selected_profits])
        average_bot_profit = total_bot_profits / num_rounds_bot_played
        final_payoff = (total_bot_profits + total_score) / (
                num_rounds_bot_played + num_rounds_i_played)
        if final_payoff < 0:
            final_payoff = 0
        player.final_payoff = max(0,round(final_payoff,2))
        player.total_profit_player= total_score
        player.avg_profit_player = round((total_score/num_rounds_i_played),5)
        player.total_profit_from_the_bot_attributable = total_bot_profits
        return {
            'formatted_deal_price': formatted_deal_price,
            'formatted_profits': formatted_profits,
            'formatted_cumulative_score': f"€ {int(total_score):.2f}",
            'formatted_AVG_human_profit': f"€ {max(0,player.participant.payoff):.2f}",
            'formatted_bot_payment': f"€ {average_bot_profit:.2f}",
            'formatted_final_payment': f"€ {final_payoff:.2f}",
        }


page_sequence = [
    Instructions,
    MatchWaitPage, 
    ComprehensionCheck,
    CustomWaitPage,
    Bargain,
    Results,
]
