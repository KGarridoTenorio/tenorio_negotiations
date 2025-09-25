from typing import Tuple

from .constants import C
from .offer import Offer, OfferList
from .prompts import PROMPTS


def pareto_efficient(offer: Offer, all_offers: OfferList) -> bool:
    # Pareto efficiency condition:
    #  no other combination should be better in both objectives

    def coll_abs(o: Offer) -> Tuple[int, int]:
        return o.profit_user + o.profit_bot, abs(o.profit_user - o.profit_bot)

    collective_profit, abs_difference = coll_abs(offer)
    for other_offer in all_offers:
        if offer == other_offer:
            continue
        other_collective_profit, other_abs_difference = coll_abs(other_offer)
        if other_collective_profit > collective_profit and \
                other_abs_difference <= abs_difference:
            return False
        if other_collective_profit >= collective_profit and \
                other_abs_difference < abs_difference:
            return False
    return True


def get_efficient_offers(constraint_user: int,
                         constraint_bot: int,
                         bot_role: str) -> OfferList:
    offer_list = OfferList()
    for price in C.PRICE_RANGE:
        for quality in C.QUALITY_RANGE:
            offer = Offer(price=price, quality=quality, idx=0)
            offer.profits(bot_role, constraint_user, constraint_bot)
            offer_list.append(offer)

    # If the offer is Pareto efficient, add to the list
    efficient_offer_list = OfferList()
    for offer in offer_list:
        is_pareto_efficient = pareto_efficient(offer, offer_list)
        if is_pareto_efficient:
            efficient_offer_list.append(offer)

    return efficient_offer_list


def pareto_efficient_offer(constraint_user: int,
                           constraint_bot: int,
                           bot_role: str,
                           max_greedy: bool) -> int:
    efficient_offers_for_bot = \
        get_efficient_offers(constraint_user, constraint_bot, bot_role)
    if max_greedy:
        return efficient_offers_for_bot.max_profit
    else:
        return efficient_offers_for_bot.min_profit


def pareto_efficient_string(constraint_user: int,
                            constraint_bot: int,
                            bot_role: str) -> str:
    efficient_offers_for_bot = get_efficient_offers(
        constraint_user, constraint_bot, bot_role)
    profits_bot = [offer.profit_bot for offer in efficient_offers_for_bot]
    max_profit_bot = max(profits_bot)
    best_offers = [o for o in efficient_offers_for_bot
                   if o.profit_bot == max_profit_bot]
    return ' | '.join(
        PROMPTS['offer_string'] % (o.price, o.quality) for o in best_offers)
