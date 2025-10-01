from typing import Tuple
from scipy.optimize import root_scalar

from .constants import C
from .offer import (Offer, ACCEPT, OFFER_QUALITY, OFFER_PRICE,
                    NOT_OFFER, INVALID_OFFER, NOT_PROFITABLE)
from .prompts import PROMPTS
    
def optimal_wholesale_price_for_quality(offer: Offer, constraint_bot, constraint_user) -> Tuple[int, int]:
    q = offer.quality
    print(f"[DEBUG optimal_wholesale_price_for_quality] offer: {offer}, constraint_bot: {constraint_bot}, constraint_user: {constraint_user}, q: {q}")
    if q <= 0:
        print(f"[DEBUG optimal_wholesale_price_for_quality] q <= 0, returning: ({constraint_bot}, {q})")
        return (constraint_bot, q)
    if q <= C.DEMAND_MAX:
        E = q - (q**2) / (2 * (C.DEMAND_MAX - C.DEMAND_MIN))
    else:
        E = (C.DEMAND_MIN + C.DEMAND_MAX) / 2.0
    print(f"[DEBUG optimal_wholesale_price_for_quality] E: {E}")
    if E <= 0:
        print(f"[DEBUG optimal_wholesale_price_for_quality] E <= 0, returning: ({constraint_bot}, {q})")
        return (constraint_bot, q)
    M = min(constraint_bot, constraint_user)
    Cost = max(constraint_bot, constraint_user)
    optimal_price = (M * E + Cost * q) / (2 * E)
    print(f"[DEBUG optimal_wholesale_price_for_quality] M: {M}, Cost: {Cost}, optimal_price (before clamp): {optimal_price}")
    optimal_price = max(constraint_bot, min(constraint_user, optimal_price))
    print(f"[DEBUG optimal_wholesale_price_for_quality] optimal_price (after clamp): {optimal_price}")
    result = (int(round(optimal_price)), int(q))
    print(f"[DEBUG optimal_wholesale_price_for_quality] result: {result}")
    return result


def optimal_quality_for_wholesale_price(offer: Offer, constraint_bot, constraint_user) -> Tuple[int, int]:
    p = offer.price
    M = min(constraint_bot, constraint_user)
    Cost = max(constraint_bot, constraint_user)
    print(f"[DEBUG optimal_quality_for_wholesale_price] offer: {offer}, constraint_bot: {constraint_bot}, constraint_user: {constraint_user}, p: {p}, M: {M}, Cost: {Cost}")
    if p <= M / 2:
        print(f"[DEBUG optimal_quality_for_wholesale_price] p <= M/2, returning None")
        return None
    if p < (M + 2 * Cost) / 2:
        q = 200 * (2*p - M - Cost) / (2*p - M)
        print(f"[DEBUG optimal_quality_for_wholesale_price] q (branch 1): {q}")
        if q < 0 or q > C.DEMAND_MAX:
            print(f"[DEBUG optimal_quality_for_wholesale_price] q out of range, returning None")
            return None
        result = (int(p), int(round(q)))
        print(f"[DEBUG optimal_quality_for_wholesale_price] result (branch 1): {result}")
        return result
    else:
        q = (100 * p - 50 * M) / Cost
        print(f"[DEBUG optimal_quality_for_wholesale_price] q (branch 2): {q}")
        if q < 0:
            print(f"[DEBUG optimal_quality_for_wholesale_price] q < 0, returning None")
            return None
        if q < C.DEMAND_MAX:
            q = 200 * (2*p - M - Cost) / (2*p - M)
            print(f"[DEBUG optimal_quality_for_wholesale_price] q (branch 2, recalculated): {q}")
        result = (int(p), int(round(q)))
        print(f"[DEBUG optimal_quality_for_wholesale_price] result (branch 2): {result}")
        return result
    
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