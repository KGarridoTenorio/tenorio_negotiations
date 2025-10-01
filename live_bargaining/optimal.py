from typing import Tuple
from scipy.optimize import root_scalar

from .constants import C
from .offer import (Offer, ACCEPT, OFFER_QUALITY, OFFER_PRICE,
                    NOT_OFFER, INVALID_OFFER, NOT_PROFITABLE)
from .prompts import PROMPTS
    
def optimal_wholesale_price_for_quality(offer: Offer, constraint_bot, constraint_user) -> Tuple[int, int]:
    quality = offer.quality
    market_price = max(constraint_bot, constraint_user)
    production_cost = min(constraint_bot, constraint_user)

    if quality <= 0:
        return (constraint_bot, quality)
    if quality <= C.DEMAND_MAX:
        E = quality - (quality**2) / (2 * (C.DEMAND_MAX - C.DEMAND_MIN))
    else:
        E = (C.DEMAND_MIN + C.DEMAND_MAX) / 2.0
    if E <= 0:
        return (constraint_bot, quality)

    optimal_price = (market_price * E + production_cost * quality) / (2 * E)
    optimal_price = max(constraint_bot, min(constraint_user, optimal_price))
    return (float(round(optimal_price, 2)), int(quality))


def optimal_quality_for_wholesale_price(offer: Offer, constraint_bot, constraint_user) -> Tuple[int, int]:
    price = offer.price
    market_price = max(constraint_bot, constraint_user)
    production_cost = min(constraint_bot, constraint_user)

    if price <= market_price / 2:
        return None
    if price < (market_price + 2 * production_cost) / 2:
        quality = 200 * (2*price - market_price - production_cost) / (2*price - market_price)
        if quality < 0 or quality > C.DEMAND_MAX:
            return None
        return (round(price, 2), int(quality))
    else:
        quality = (100 * price - 50 * market_price) / production_cost
        if quality < 0:
            return None
        if quality < C.DEMAND_MAX:
            quality = 200 * (2*price - market_price - production_cost) / (2*price - market_price)
        return (round(price, 2), int(quality))
    
def nash_bargaining_solution(o: Offer, constraint_bot: int, constraint_user: int) -> Tuple[int, int]:

     market_price = max(constraint_bot, constraint_user)
     production_cost = min(constraint_bot, constraint_user)
     demand_range = C.DEMAND_MAX - C.DEMAND_MIN
     quality_star = demand_range * (market_price - production_cost) / market_price
     price_star = market_price * (market_price + 3 * production_cost) / (2 * (market_price + production_cost))
     print(f"[DEBUG nash_bargaining_solution] price_star: {price_star}, quality_star: {quality_star}")
     return (price_star, quality_star)

def optimal_solution_string(constraint_user: int,
                            constraint_bot: int,
                            evaluation: str,
                            offer: Offer) -> str:
    
     print(f"[DEBUG optimal_solution_string] evaluation: {evaluation}, constraint_user: {constraint_user}, constraint_bot: {constraint_bot}, offer: {offer}")
     if evaluation == ACCEPT:
          return ''
     elif evaluation == OFFER_PRICE:
          optimal_price, optimal_quality = optimal_quality_for_wholesale_price(offer, constraint_bot, constraint_user)
     elif evaluation == OFFER_QUALITY:
          optimal_price, optimal_quality = optimal_wholesale_price_for_quality(offer, constraint_bot, constraint_user)
     elif evaluation == NOT_PROFITABLE:
          optimal_price, optimal_quality = optimal_wholesale_price_for_quality(offer, constraint_bot, constraint_user)
     elif evaluation in (INVALID_OFFER, NOT_OFFER):
          optimal_price, optimal_quality = nash_bargaining_solution(offer, constraint_bot, constraint_user)
     print(f"[DEBUG optimal_solution_string] optimal_price: {optimal_price}, optimal_quality: {optimal_quality}")
     return PROMPTS['offer_string'] % (optimal_price, optimal_quality)