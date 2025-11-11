import random
from typing import Any, Dict, List, Optional, Tuple

from otree.api import *

from . import Offer
from .constants import C
from .models import Player, Group, Subsession, BotProfits
from .utils import now_datetime, get_start_time

import settings

def is_class_active(session_config_details, _class) -> bool:
    return session_config_details.get(_class, False)

def initialize_negotiation_classes(config):
    negotiation_classes = {
        'Class A': {
            'market_price': 12,
            'production_cost': 3,
        },
        'Class B': {
            'market_price': 11,
            'production_cost': 3,
        },
        'Class C': {
            'market_price': 12,
            'production_cost': 4,
        },
        'Class D': {
            'market_price': 10,
            'production_cost': 3,
        },
        'Class E': {
            'market_price': 11,
            'production_cost': 4,
        },
        'Class F': {
            'market_price': 12,
            'production_cost': 5,
        },
        'Class G': {
            'market_price': 10,
            'production_cost': 4,
        },
        'Class H': {
            'market_price': 11,
            'production_cost': 5,
        },
        'Class I': {
            'market_price': 10,
            'production_cost': 5,
        },
    }

    active_classes = {}
    for class_name, params in negotiation_classes.items():
        if is_class_active(config, class_name):
            active_classes[class_name] = params
    return active_classes

class CustomWaitPage(WaitPage):
    template_name = 'live_bargaining/CustomWaitPage.html'

    @staticmethod
    def vars_for_template(player: Player) -> Dict[str, Any]:
        if player.round_number == (len(initialize_negotiation_classes(player.session.config)) + 2):
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
        player.participant.vars['price'] = random.choice(range(int(C.PRICE_MIN), int(C.PRICE_MAX)))
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

        # For the comprehension test, demand is fixed at 50
        fixed_demand = 50
        try:
            answer_float = float(answer)
        except Exception:
            answer_float = None

        if player.role == C.ROLE_BUYER:
            quantity_sold = min(quality, fixed_demand)
            profit =(market_price - price) * quantity_sold
            if answer_float is not None and abs(answer_float - profit) < 0.01:
                return None
            formula = f"({market_price} - {price}) * {fixed_demand} = {profit:.2f}"
            explanation = (
                f"Unfortunately your answer is incorrect!<br><br>"
                f"Retail Price: {market_price}<br>"
                f"Agreed Wholesale Price: {price}<br>"
                f"Agreed Quantity: {quality}<br>"
                f"The Random Demand from the market: {fixed_demand}<br>"
                f"Your profit (as a {player.role}) is calculated as:<br>"
                f"<b>Profit = (Retail Price - Wholesale Price) * Quantity Sold</b><br>"
                f"{formula}<br>"
                f"Please try again with the new combination."
            )
            player.comprehension_count += 1
            return explanation
        else:
            quantity_sold = min(quality, fixed_demand)
            unsold_quantity = min(fixed_demand, quality)
            profit = ((price - production_cost) * (quantity_sold)) + (production_cost * unsold_quantity)
            if answer_float is not None and abs(answer_float - profit) < 0.01:
                return None
            formula = f"({price} * {fixed_demand}) - ({production_cost} * {fixed_demand}) = {profit:.2f}"
            explanation = (
                f"Unfortunately your answer is incorrect!<br><br>"
                f"Production Cost: {production_cost}<br>"
                f"Agreed Wholesale Price: {price}<br>"
                f"Agreed Quantity: {quality}<br>"
                f"The Random Demand from the market: {fixed_demand}<br>"
                f"Your profit (as a {player.role}) is calculated as:<br>"
                f"<b>Profit = ((Wholesale Price - Production Cost) * (Quantity Sold)) + (Production Cost * Unsold Quantity)</b><br>"
                f"{formula}<br>"
                f"Please try again with the new combination."
            )
            player.comprehension_count += 1
            return explanation

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
        
        # Get demand range from session config
        config = player.session.config
        demand_min = config.get('demand_low', 0)  # Default fallback values
        demand_max = config.get('demand_high', 100)
        
        return {
            'id_in_group': player.id_in_group,
            'bot_opponent': player.bot_opponent,
            'startTime': time_start.timestamp() * 1000,
            'messages': player.chat_data,
            'offers': player.offers,
            # Parameters for Decision Support System
            'market_price': player.group.market_price,
            'production_cost': player.group.production_cost,
            'is_supplier': player.is_supplier,
            # Dynamic demand calculation parameters
            'demand_min': demand_min,
            'demand_max': demand_max,
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
    
    @staticmethod
    def get_params(player: Player) -> Tuple[str, str, int]:
        formatted_optimal_offer = player.group.optimal_offer
        if isinstance(formatted_optimal_offer, dict) and 'profit' in formatted_optimal_offer and 'offer' in formatted_optimal_offer:
                profit = formatted_optimal_offer['profit']
                price, quantity = formatted_optimal_offer['offer']
                formatted_optimal_offer = f"A Wholesale Price of {price:.2f}€ and {quantity} units have expected profits of {profit:.1f} (Same expected profit for you and your counterpart)."
        return formatted_optimal_offer

    @classmethod
    def vars_for_template(cls, player: Player) -> Dict[str, Any]:
        formatted_optimal_offer= \
            cls.get_params(player)
        return {
            'formatted_optimal_offer': formatted_optimal_offer
        }

class Results(Page):
    @staticmethod
    def get_params(player: Player) -> Tuple[str, str, int]:
        if player.field_maybe_none("price_accepted") is None:
            formatted_deal_price = ""
            formatted_deal_quantity = ""
            formatted_profits = "€ 0"
        else:
            formatted_deal_price = f"€ {player.price_accepted}"
            formatted_deal_quantity = f"{player.quality_accepted}"
            formatted_profits = f"€ {int(player.payoff)}"
        formatted_demand= player.group.demand
        total_score = max(0, sum(int(p.payoff) for p in player.in_all_rounds()))
        avg_score = total_score / len(initialize_negotiation_classes(player.session.config))
        player.participant.payoff = avg_score 

        return formatted_deal_price,formatted_deal_quantity, formatted_profits, total_score, formatted_demand

    @classmethod
    def vars_for_template(cls, player: Player) -> Dict[str, Any]:
        
        print(len(initialize_negotiation_classes(player.session.config)) + 2)

        
        if player.round_number >= (len(initialize_negotiation_classes(player.session.config)) + 2):
            return cls.vars_for_template_last_round(player)

        formatted_deal_price, formatted_deal_quantity, formatted_profits, total_score, formatted_demand = \
            cls.get_params(player)
        return {
            'formatted_demand': formatted_demand,
            'formatted_deal_price': formatted_deal_price,
            'formatted_profits': formatted_profits,
            'formatted_deal_quantity': formatted_deal_quantity,
            'formatted_cumulative_score': f"€ {int(total_score):.2f}",
            'formatted_AVG_human_profit': f"€ {player.participant.payoff:.2f}",
            'rounds_count': int(player.round_number-2),
            'total_rounds_selected': int((len(initialize_negotiation_classes(player.session.config)))+2),
        }

    @classmethod
    def vars_for_template_last_round(cls, player: Player) -> Dict[str, Any]:
        formatted_deal_price, formatted_deal_quantity,  formatted_profits, total_score, formatted_demand = \
            cls.get_params(player)
        num_rounds_i_played = len(initialize_negotiation_classes(player.session.config))


        # Calculating the sum and average of the randomly selected profits
        final_payoff = ((total_score) / num_rounds_i_played )/50
        if final_payoff < 0:
            final_payoff = 0
        player.final_payoff = max(0,round(final_payoff,2))
        player.total_profit_player= total_score
        player.avg_profit_player = round((total_score/num_rounds_i_played),2)
        return {
            'formatted_demand': formatted_demand,
            'formatted_deal_price': formatted_deal_price,
            'formatted_profits': formatted_profits,
            'formatted_deal_quantity': formatted_deal_quantity,
            'formatted_cumulative_score': f"€ {int(total_score):.2f}",
            'formatted_AVG_human_profit': f"€ {max(0,player.participant.payoff):.2f}",
            'formatted_final_payment': f"€ {final_payoff:.2f}",
            'total_rounds_selected': int((len(initialize_negotiation_classes(player.session.config)))+2),
        }

page_sequence = [
    Instructions,
    MatchWaitPage, 
    ComprehensionCheck,
    CustomWaitPage,
    Bargain,
    Results,
]