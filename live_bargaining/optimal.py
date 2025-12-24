from typing import Tuple, Dict, Any

from .constants import C
from .offer import (Offer, ACCEPT, OFFER_QUALITY, OFFER_PRICE,
                    NOT_OFFER, INVALID_OFFER, NOT_PROFITABLE_FIND_OTHER_QUANTITY,
                      NOT_PROFITABLE_FIND_OTHER_PRICE, TOO_UNFAVOURABLE)
from .prompts import PROMPTS

import math

def nash_bargaining_solution(constraint_bot: int, constraint_user: int) -> Dict[str, float | Tuple[float, int]]:
    
    market_price = max(constraint_bot, constraint_user)
    production_cost = min(constraint_bot, constraint_user)
    
    demand_range = C.DEMAND_MAX - C.DEMAND_MIN
    quality_continuous = demand_range * (market_price - production_cost) / market_price
    price_star = round(market_price * (market_price + 3 * production_cost) / (2 * (market_price + production_cost)), 2)
    
    # Choose between floor and ceil by maximizing total profit
    q_candidates = [math.floor(quality_continuous), math.ceil(quality_continuous)]
    
    quality_star = int(max(q_candidates, key=lambda q: 
        Offer.profit_supplier(price_star, q, production_cost, C.DEMAND_MIN, C.DEMAND_MAX) +
        Offer.profit_buyer(price_star, q, market_price, C.DEMAND_MIN, C.DEMAND_MAX)
    ))
    
    profit_supplier = Offer.profit_supplier(price_star, quality_star, production_cost, C.DEMAND_MIN, C.DEMAND_MAX)
    profit_buyer = Offer.profit_buyer(price_star, quality_star, market_price, C.DEMAND_MIN, C.DEMAND_MAX)
    
    target_profit = math.floor(profit_supplier *100)/100 if production_cost == constraint_bot else math.floor(profit_buyer *100) /100
        
    return {'profit': target_profit, 'offer': (price_star, quality_star)}


def optimal_wholesale_price_for_quality(offer: Offer, constraint_bot, constraint_user) -> Tuple[float, int]:
    
    q = float(offer.quality)
    Pm = max(constraint_bot, constraint_user)  # Market price 
    c = min(constraint_bot, constraint_user)   # Production cost 
    dmin, dmax = C.DEMAND_MIN, C.DEMAND_MAX

    E = (((q**2 - dmin**2) / 2) + q*(dmax - q)) / (dmax - dmin)
    
    # Nash bargaining solution: the minimum acceptable profit for the bot
    target = float(nash_bargaining_solution(constraint_bot, constraint_user)['profit'])
    
    bot_is_supplier = (constraint_bot == c)

    if bot_is_supplier:
        best_p = math.ceil(((target + c * q) / E) *100) /100 #rounding up to ensure reaching target profit
    else:
        best_p = math.floor((Pm - target / E) *100) /100 #rounding down to ensure reaching target profit

    if best_p > 0:
        return (best_p, q)
    else:
        return (None, None)


def optimal_quality_for_wholesale_price(offer: Offer, constraint_bot, constraint_user) -> Tuple[float, int]:
    """
    Formulas:
        buyer_profit(q)    = (market_price - price) * ES(q)
        supplier_profit(q) = price * ES(q) - production_cost * q
        ES(q) = ((q^2 - dmin^2)/2 + q*(dmax - q)) / (dmax - dmin   
    """
    
    # ========================================
    # 1. EXTRACT AND DEFINE CORE PARAMETERS
    # ========================================
    
    p = float(offer.price)
    Pm = max(constraint_bot, constraint_user)  # Market price 
    c = min(constraint_bot, constraint_user)   # Production cost 
    dmin, dmax = C.DEMAND_MIN, C.DEMAND_MAX
    
    # Nash bargaining solution: the minimum acceptable profit for the bot
    target = float(nash_bargaining_solution(constraint_bot, constraint_user)['profit'])
    
    bot_is_supplier = (constraint_bot == c)
    
    # ========================================
    # 2. ASSIGN PROFIT FUNCTIONS BY ROLE
    # ========================================
    
    def ES(q: float) -> float:
        return ((q*q - dmin*dmin)/2.0 + q*(dmax - q)) / (dmax - dmin)

    def buyer_profit(q: float) -> float:
        return (Pm - p) * ES(q)

    def supplier_profit(q: float) -> float:
        return p * ES(q) - c * q
    
    # Creating new functions for comoutng profits instead of using the ones from Offer module
    # Since all the parameters except q are fixed
    
    if bot_is_supplier:
        bot_profit = supplier_profit
        user_profit = buyer_profit
    else:
        bot_profit = buyer_profit
        user_profit = supplier_profit
    
    
    # ========================================
    # 3. DEFINE ROOT-FINDING FUNCTIONS
    # ========================================
    # These functions solve for quality values where profit exactly equals the target
    
    def buyer_roots(B: float):
        """
        Solves (Pm - p) * ES(q) = B for q (buyer profit = target).
        Returns: tuple of two roots or None if no real solution exists.
        """
        A = Pm - p
        
        # Discriminant of the quadratic equation
        rad = -(A) * (dmax - dmin) * (2*B - Pm*(dmax + dmin) + p*(dmax + dmin))
        if rad < -1e-12:  # No real roots
            return None
        
        s = math.sqrt(max(0.0, rad))
        return ((dmax*A - s)/A, (dmax*A + s)/A)
    
    
    def supplier_roots(S: float):
        """
        Solves p * ES(q) - c * q = S for q (supplier profit = target).
        Returns tuple of two roots or None if no real solution exists.
        
        This is a quadratic equation of the form: A*q^2 + Bc*q + C0 = 0
        """
        A = -p
        Bc = 2*p*dmax - 2*c*(dmax - dmin)
        C0 = p*dmin*dmin - 2*S*(dmax - dmin)
        
        # Calculate discriminant
        disc = Bc*Bc - 4*A*C0
        if disc < -1e-12:  # No real roots
            return None
        
        s = math.sqrt(max(0.0, disc))
        # Apply quadratic formula: q = (-B +- sqrt(disc)) / (2*A)
        return ((-Bc - s)/(2*A), (-Bc + s)/(2*A))
    
    
    # ========================================
    # 4. IDENTIFY VERTEX POINTS (PROFIT MAXIMA)
    # ========================================
    # These points help locate integer candidates near optimal continuous solutions
    
    buyer_vertex = dmax  # Buyer profit typically maximizes at high quality
    supplier_vertex = dmax - c*(dmax - dmin)/p if p != 0 else (dmin + dmax)/2
    
    
    # ========================================
    # 5. BUILD INTEGER CANDIDATE SET
    # ========================================
    
    def build_candidates(roots, extra_vertex=None):
        """
        Constructs a robust set of integer quality candidates by sampling:
        - Interval boundaries (dmin, dmax)
        - Integer neighbors around continuous roots
        - Integer neighbors around the profit maximum vertex
        
        Args:
            roots: Tuple of two root values or None
            extra_vertex: Optional additional point to sample around
        
        Returns:
            Sorted list of unique integer candidates
        """
        cand = set([int(dmin), int(dmax)])  # Always include boundaries
        
        # Add integers near the roots
        if roots is not None:
            for q in roots:
                q = max(min(q, dmax), dmin)  # Valid range
                b = math.floor(q)
                for k in (-2, -1, 0, 1, 2):  # Sample neighbors
                    qi = int(b + k)
                    if dmin <= qi <= dmax:
                        cand.add(qi)
        
        # Add integers near the vertex (profit maximum)
        if extra_vertex is not None:
            v = max(min(extra_vertex, dmax), dmin)  # Valid range
            b = math.floor(v)
            for k in (-3, -2, -1, 0, 1, 2, 3):  # Sample neighbors
                qi = int(b + k)
                if dmin <= qi <= dmax:
                    cand.add(qi)
        
        return sorted(cand)
    
    
    # ========================================
    # 6. SELECT OPTIMAL QUALITY
    # ========================================
    # Selection criteria (in priority order):
    #   1) bot_profit(q) >= target (Nash constraint)
    #   2) Maximize user_profit(q) (efficiency)
    #   3) Tie-break: maximize total profit (bot + user)
    
    if bot_is_supplier:
        cand = build_candidates(supplier_roots(target), extra_vertex=supplier_vertex)
    else:
        cand = build_candidates(buyer_roots(target), extra_vertex=buyer_vertex)
    
    # Filter candidates that satisfy the bot's Nash constraint
    feas = [q for q in cand if bot_profit(q) + 1e-9 >= target]
    
    if feas:
        # Maximize user profit, tie-break by total profit
        best_q = max(feas, key=lambda q: (user_profit(q), user_profit(q) + bot_profit(q)))
        return round(p, 2), int(best_q)
    
    # No feasible solution found -> should not happen
    return (None, None)


def optimal_solution_string(constraint_user: int,
                            constraint_bot: int,
                            evaluation: str,
                            offer: Offer) -> str:
    
    target = nash_bargaining_solution(constraint_bot, constraint_user)['profit'] # Debugging

    if evaluation == ACCEPT:
        return ''
    elif evaluation == OFFER_PRICE or evaluation == NOT_PROFITABLE_FIND_OTHER_QUANTITY:
        optimal_price, optimal_quality = optimal_quality_for_wholesale_price(offer, constraint_bot, constraint_user)
    elif evaluation == OFFER_QUALITY  or evaluation == NOT_PROFITABLE_FIND_OTHER_PRICE:
        optimal_price, optimal_quality = optimal_wholesale_price_for_quality(offer, constraint_bot, constraint_user)
    elif evaluation == TOO_UNFAVOURABLE or evaluation == NOT_OFFER:
        optimal_price, optimal_quality = nash_bargaining_solution(constraint_bot, constraint_user)['offer']
    elif evaluation == INVALID_OFFER:
        return (None, None)
    print(f"[DEBUG optimal_solution_string] optimal_price: {optimal_price}, optimal_quality: {optimal_quality}, target_profit: {target}")
    return PROMPTS['offer_string'] % (optimal_price, optimal_quality)