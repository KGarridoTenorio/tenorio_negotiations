import time
from typing import Any, Union
from .constants import C

ACCEPT = 'accept'
NOT_PROFITABLE = 'not_profitable'
OFFER_QUALITY = 'offer_quality'
OFFER_PRICE = 'offer_price'
NOT_OFFER = 'not_offer'
INVALID_OFFER = 'invalid_offer'
TOO_UNFAVOURABLE = 'too_unfavourable'


class Offer(dict):
    def __init__(self,
                 idx: int = -1,
                 price: float = None,
                 quality: int = None,
                 stamp: int = None,
                 from_chat: bool = False,
                 enhanced: str = None,
                 profit_bot: int = None,
                 profit_user: int = None,
                 test: Any = None):
        stamp = stamp or int(time.time())
        dict.__init__(self, idx=idx, price=price, quality=quality,
                      stamp=stamp, from_chat=from_chat, enhanced=enhanced,
                      profit_bot=profit_bot, profit_user=profit_user,
                      test=test)
        self.idx = idx
        self.price = price
        self.quality = quality
        self.stamp = stamp
        self.from_chat = from_chat
        self.enhanced = enhanced
        self.profit_bot = profit_bot
        self.profit_user = profit_user

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    @property
    def specifics(self) -> str:
        return f"P+Q = {str(self.price):4} + {str(self.quality):4} ; " \
               f"PROF = {str(self.profit_bot):3} + {str(self.profit_user):3} ;"

    @property
    def is_valid(self) -> bool:
        return self.is_complete and \
               self.price_in_range and self.quality_in_range

    @property
    def is_complete(self) -> bool:
        return None not in (self.price, self.quality)

    @property
    def price_in_range(self) -> bool:
        if self.price is None:
            return False
        #return Player.group.production_cost <= self.price <= Player.group.market_price,
        return 3 <= self.price <= 12 # IT should be dynamic

    @property
    def quality_in_range(self) -> bool:
        return self.quality in C.QUALITY_RANGE

    def enhance(self, offer_list: 'OfferList', idx: int = None):
        """ Adds missing price or quality from last data
        """
        if self.price is None:
            self.price = offer_list.last_valid_price(idx)
            self.enhanced = 'price'
        if self.quality is None:
            self.quality = offer_list.last_valid_quality(idx)
            if self.enhanced is not None:
                self.enhanced += ' quality'
            else:
                self.enhanced = 'quality'

    def profits(self, bot_role: str, constraint_user: int, constraint_bot: int):
        """ This calculates the profits for the user and the bot """
        if not self.is_valid or None in (constraint_user, constraint_bot):
            self.profit_bot = -11
            self.profit_user = -10
            return

        args_bot = (self.price, self.quality, constraint_bot, C.DEMAND_MIN, C.DEMAND_MAX)
        args_user = (self.price, self.quality, constraint_user, C.DEMAND_MIN, C.DEMAND_MAX)

        if bot_role == C.ROLE_SUPPLIER:
            self.profit_bot = self.profit_supplier(*args_bot)
            self.profit_user = self.profit_buyer(*args_user)
        else:
            self.profit_bot = self.profit_buyer(*args_bot)
            self.profit_user = self.profit_supplier(*args_user)

    def is_price_feasible(self, market_price: float, production_cost: float,
                         nash_profit: float, dmin: int, dmax: int,
                         bot_is_supplier: bool) -> bool:
        """
        Checks if a given price allows the bot to achieve Nash profit.
        Returns: True / False
        """
        
        if bot_is_supplier:
            q_best = dmax - (production_cost*(dmax - dmin) / self.price)
            ES_best = (((q_best**2 - dmin**2)/2) + q_best*(dmax - q_best)) / (dmax - dmin)

            max_profit = self.price * ES_best - production_cost * q_best
            
            if max_profit < nash_profit:
                print(f"Price {self.price:.2f} too low. Bot (supplier) max profit = {max_profit:.2f} < Nash {nash_profit:.2f}")
                return False
        else:
            q_best = dmax
            ES_best = (((q_best**2 - dmin**2)/2) + q_best*(dmax - q_best)) / (dmax - dmin)

            max_profit = (market_price - self.price) * ES_best

            if max_profit < nash_profit:
                print(f"Price {self.price:.2f} too high. Bot (buyer) max profit = {max_profit:.2f} < Nash {nash_profit:.2f}")
                return False
            
        return True
    
    def is_quality_feasible(self, market_price: float, production_cost: float,
                           nash_profit: float, dmin: int, dmax: int,
                           bot_is_supplier: bool) -> bool:
        """
        Checks if a given quality allows the bot to achieve Nash profit.
        Returns: True / False
        """

        ES = (((self.quality**2 - dmin**2)/2) + self.quality*(dmax - self.quality)) / (dmax - dmin)
        
        if bot_is_supplier:
            required_price = (nash_profit + production_cost * self.quality) / ES

            if required_price < 0:
                print(f"Quality {self.quality} requires negative price for Nash profit")
                return False
            
            if required_price >= market_price:
                print(f"Quality {self.quality} requires price {required_price:.2f} >= market price {market_price:.2f}")
                return False
        else:
            max_acceptable_price = market_price - nash_profit / ES

            if max_acceptable_price < production_cost:
                print(f"Quality {self.quality} requires negative price for Nash profit")
                return False
        
        return True

    
    def validate_partial_offer(self, constraint_bot, constraint_user) -> bool:
        from live_bargaining.optimal import nash_bargaining_solution 

        nash_profit = nash_bargaining_solution(constraint_bot, constraint_user)['profit']

        production_cost = min(constraint_bot, constraint_user)
        market_price = max(constraint_bot, constraint_user)
        dmin = C.DEMAND_MIN
        dmax = C.DEMAND_MAX

        bot_is_supplier = (constraint_bot == production_cost)

        if self.quality is not None:
            is_valid = self.is_quality_feasible(
                market_price, production_cost, nash_profit,
                dmin, dmax, bot_is_supplier
            )
            if not is_valid:
                return False

        if self.price is not None:
            is_valid = self.is_price_feasible(
                market_price, production_cost, nash_profit, 
                dmin, dmax, bot_is_supplier
            )
            if not is_valid:
                return False
        
        return True

    def evaluate(self, constraint_bot, constraint_user) -> str:
        from live_bargaining.optimal import nash_bargaining_solution 
        nash_profit = nash_bargaining_solution(constraint_bot, constraint_user)['profit']

        print(f"[DEBUG Offer.evaluate] Offer: price = {self.price}, quality = {self.quality}, profit_bot = {self.profit_bot}, profit_user = {self.profit_user}, is_valid = {self.is_valid}")
        if self.profit_bot >= nash_profit:
            result = ACCEPT

        elif self.price is None and self.quality_in_range:
            if not self.validate_partial_offer(constraint_bot, constraint_user):
                result = TOO_UNFAVOURABLE
                return result
            result = OFFER_QUALITY

        elif self.quality is None and self.price_in_range:
            if not self.validate_partial_offer(constraint_bot, constraint_user):
                result = TOO_UNFAVOURABLE
                return result
            result = OFFER_PRICE

        elif self.is_valid:
            if not self.validate_partial_offer(constraint_bot, constraint_user):
                result = TOO_UNFAVOURABLE
                return result
            result = NOT_PROFITABLE

        elif self.price is not None and not self.price_in_range:
            result = INVALID_OFFER
        elif self.quality is not None and not self.quality_in_range:
            result = INVALID_OFFER
        else:
            result = NOT_OFFER

        print(f"[DEBUG Offer.evaluate] Result Evaluation: {result} \n")
        return result
        
    @staticmethod
    def expected_demand(quality: int, demand_min: int, demand_max: int) -> float:
        if quality <= demand_min:
            return quality
        if quality >= demand_max:
            return (demand_min + demand_max) / 2
        return ((quality ** 2 - demand_min * demand_min) / 2 + quality * (demand_max - quality)) / (demand_max - demand_min)

    @staticmethod
    def profit_supplier(price: int, quality: int, production_cost: int, demand_min: int, demand_max: int) -> float:
        expected_sales = Offer.expected_demand(quality, demand_min, demand_max)
        return (price * expected_sales) - (production_cost * quality)

    @staticmethod
    def profit_buyer(price: int, quality: int, market_price: int, demand_min: int, demand_max: int) -> float:
        expected_sales = Offer.expected_demand(quality, demand_min, demand_max)
        return (market_price - price) * expected_sales

class OfferList(list):
    def __init__(self, *args):
        list.__init__(self, *args)
        # Make sure this is always sorted on stamp
        self.sort(key=lambda o: o.stamp)

    def last_valid_price(self, idx: int = None) -> Union[int, float]:
        # Sort on latest timestamp
        for offer in sorted(self, key=lambda o: -o.stamp):
            # Ignore offers from other players
            if idx is not None and offer.idx != idx:
                continue
            if offer.price is not None:
                return offer.price
        return 5

    def last_valid_quality(self, idx: int = None) -> int:
        # Sort on latest timestamp
        for offer in sorted(self, key=lambda o: -o.stamp):
            # Ignore offers from other players
            if idx is not None and offer.idx != idx:
                continue
            if offer.quality is not None:
                return offer.quality
        return 2

    @property
    def max_profit(self) -> int:
        if len(self) == 0:
            return 0
        # Only check for user offers
        return max([offer.profit_bot for offer in self if offer.idx != -1])

    @property
    def min_profit(self) -> int:
        # Only check for user offers
        return min([offer.profit_bot for offer in self if offer.idx != -1])
