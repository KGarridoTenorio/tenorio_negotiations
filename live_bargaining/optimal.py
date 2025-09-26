from typing import Tuple
from scipy.optimize import root_scalar

from .constants import C
from .offer import (Offer, ACCEPT, OFFER_QUALITY, OFFER_PRICE,
                    NOT_OFFER, INVALID_OFFER, NOT_PROFITABLE)
from .prompts import PROMPTS
    
def optimal_wholesale_price_for_quality(offer: Offer, constraint_bot, constraint_user) -> Tuple[int, int]:

        def profit_difference(o: Offer) -> float:
            return o.profit_user - o.profit_bot
        
        sol = root_scalar(profit_difference(offer), bracket=[min(constraint_bot, constraint_user), max(constraint_bot, constraint_user)], method='bisect')
        optimal_price = sol.root

        return (optimal_price, offer.quality)
    
def optimal_quality_for_wholesale_price(offer: Offer) -> Tuple[int, int]:

        def profit_difference(o: Offer) -> float:
            return o.profit_user - o.profit_bot
        
        # Use small epsilon to avoid trivial solution at quantity=0
        eps = 1e-6
        sol = root_scalar(profit_difference(offer), bracket=[eps, C.DEMAND_MAX], method='bisect')        
        optimal_quality = sol.root

        return (offer.price, optimal_quality)
    
def nash_bargaining_solution(o: Offer, constraint_bot: int, constraint_user: int) -> Tuple[int, int]:

    # Identify market_price and production_cost regardless of bot role
    market_price = max(constraint_bot, constraint_user)
    production_cost = min(constraint_bot, constraint_user)
    demand_range = C.DEMAND_MAX - C.DEMAND_MIN
    
    # Nash optimal formulas
    quality_star = demand_range * (market_price - production_cost) / market_price
    price_star = market_price * (market_price + 3 * production_cost) / (2 * (market_price + production_cost))
    
    return (price_star, quality_star)

def optimal_solution_string(constraint_user: int,
                            constraint_bot: int,
                            evaluation: str,
                            offer: Offer) -> str:
    
    if evaluation == ACCEPT:
         return ''
    elif evaluation == OFFER_PRICE:
         optimal_price, optimal_quality = optimal_quality_for_wholesale_price(offer)
    elif evaluation == OFFER_QUALITY:
         optimal_price, optimal_quality = optimal_wholesale_price_for_quality(offer, constraint_bot, constraint_user)
    elif evaluation == NOT_PROFITABLE:
         optimal_price, optimal_quality = optimal_wholesale_price_for_quality(offer, constraint_bot, constraint_user)
    elif evaluation in (INVALID_OFFER, NOT_OFFER):
         optimal_price, optimal_quality = nash_bargaining_solution(offer, constraint_bot, constraint_user)

    return PROMPTS['offer_string'] % (optimal_price, optimal_quality)