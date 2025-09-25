import asyncio

import httpx

from live_bargaining.offer import (
    Offer, ACCEPT, OFFER_QUALITY, OFFER_PRICE, NOT_OFFER)
from live_bargaining.pareto import pareto_efficient_string
from live_bargaining.prompts import (
    PROMPTS, system_final_prompt,not_profitable_prompt, empty_offer_prompt,
    offer_without_price_prompt, offer_without_quality_prompt)
from .bot_utils import BotUtils
from .constants import C
from .utils import log_llm_response


class BotStrategy(BotUtils):
    async def initial(self):
        # Make the call
        messages = [{"role": "system",
                     "content": system_final_prompt(self.config)},
                    {"role": "user",
                     "content": PROMPTS[self.role]['initial']}]
        response = self.get_llm_response(messages)
        if response is None:
            return

        # Only for testing
        log_llm_response(response)

        # Process the LLM output
        llm_output = self.extract_content(response)
        self.store_send_data(llm_output=llm_output)

    async def follow_up(self):
        # loops is the count of user chats (zero-based)
        loops = sum(i['role'] == 'user' for i in self.interaction_list) - 1

        if loops == 0:
            self.constraint_initial()
            return

        if loops == 1:
            self.constraint_final()
            return

        # Extract possible offer, add to the list if valid
        try:
            self.offer_user = self.interpret_offer(self.user_message)
        except httpx.ConnectError as _:
            self.store_send_data(llm_output=C.LLM_ERROR)
            return
        if self.offer_user:
            self.offer_user.test = "from chat"
            self.offer_list.append(self.offer_user)

        self.trail += f"({str(self.offer_user.price):>4}, " \
                      f"{str(self.offer_user.quality):>4}) "

        if self.offer_user.is_valid:
            await self.evaluate()
        elif self.offer_user.price is None:
            self.trail += \
                f"I ({self.offer_user.price}, {self.offer_user.quality}) "
            self.respond_to_offer(OFFER_QUALITY)
        elif self.offer_user.quality is None:
            self.trail += \
                f"I ({self.offer_user.price}, {self.offer_user.quality}) "
            self.respond_to_offer(OFFER_PRICE)
        else:
            self.trail += \
                f"I ({self.offer_user.price}, {self.offer_user.quality}) "
            self.respond_to_offer(NOT_OFFER)

    async def interface_offer(self):
        # Offer already added to the list in Player.process_offer()
        self.offer_user = self.offer_list[-1]

        # Evaluate the profitability of user offer and respond
        await self.evaluate()

    def constraint_initial(self):
        try:
            constraint_user = self.interpret_constraints(self.user_message)
        except httpx.ConnectError as _:
            self.store_send_data(llm_output=C.LLM_ERROR)
            return

        context_constraint = PROMPTS['context_constraint'][self.role]
        if constraint_user is not None:
            params = (constraint_user, context_constraint) * 2
            message = PROMPTS['constraint_confirm'] % params
            bot_vars = {'initial_constraint': constraint_user}
            self.store_send_data(llm_output=message, bot_vars=bot_vars)
        else:
            message = PROMPTS['constraint_clarify'] % context_constraint
            self.store_send_data(llm_output=message)

    def constraint_final(self):
        try:
            constraint_user = self.interpret_constraints(self.user_message)
        except httpx.ConnectError as _:
            self.store_send_data(llm_output=C.LLM_ERROR)
            return

        message = final_constraint = None
        if constraint_user is not None:
            if self.role == C.ROLE_BUYER:
                # User is Supplier, constrain to production cost
                if self.config['production_cost_low'] <= \
                        constraint_user <= self.config['production_cost_high']:
                    message = PROMPTS['constraint_final']
                    final_constraint = constraint_user
            else:
                # User is Buyer, constrain to market price
                if self.config['market_price_low'] <= \
                        constraint_user <= self.config['market_price_high']:
                    message = PROMPTS['constraint_final']
                    final_constraint = constraint_user
        if message is None or final_constraint is None:
            message = PROMPTS['constraint_persisting']
            final_constraint = self.random_draw_constraint()

        bot_vars = {'final_constraint': final_constraint}
        self.store_send_data(llm_output=message, bot_vars=bot_vars)

    async def evaluate(self):
        # Add profits for user and bot to the offers
        for offer in self.offer_list:
            self.add_profits(offer)

        # Evaluate the profitability of user offer and respond
        greedy = self.get_greediness(self.constraint_user, self.constraint_bot)
        evaluation = self.offer_user.evaluate(self.offer_list, greedy)
        self.trail += \
            f"E ({self.offer_user.price}, {self.offer_user.quality}) " \
            f"[{self.offer_user.profit_bot}, {greedy}, {evaluation}] "

        if evaluation == ACCEPT:
            await self.accept_offer()
        else:
            self.respond_to_offer(evaluation)

    async def accept_offer(self):
        # Make the call
        follow_up_content = PROMPTS['accept'] + self.user_message
        messages = [{"role": "system",
                     "content": system_final_prompt(self.config)},
                    {"role": "user", "content": follow_up_content}]
        response = self.get_llm_response(messages)
        if response is None:
            return

        # Only for testing
        log_llm_response(response)

        # Process the LLM output
        llm_output = self.extract_content(response)
        self.store_send_data(llm_output=llm_output)

        if self.offer_user.from_chat:
            await self.accept_final_chat()
        else:
            await self.accept_final_interface()

    async def accept_final_chat(self):
        await asyncio.sleep(5)
        # Create offer matching offer for user to accept
        bot_offer = Offer(idx=-1,
                          price=self.offer_user.price,
                          quality=self.offer_user.quality,
                          test="accept_final_chat")
        self.add_profits(bot_offer)
        self.offer_list.append(bot_offer)
        self.store_send_data()

    async def accept_final_interface(self):
        await asyncio.sleep(5)
        # Accept on the model
        player, participant = self.get_player_participant()
        player.process_accept(self.offer_user.price, self.offer_user.quality)
        # Accept in the interface
        self.send_asyncio_data({'finished': True})

    def get_respond_prompt(self, evaluation: str) -> str:
        if evaluation == NOT_OFFER:
            return empty_offer_prompt(
                self.config, self.user_message,
                self.offers_pareto_efficient, str(self.interaction_list))
        elif evaluation == OFFER_QUALITY:
            return offer_without_price_prompt(
                self.config, self.user_message,
                self.offers_pareto_efficient, str(self.interaction_list))
        elif evaluation == OFFER_PRICE:
            return offer_without_quality_prompt(
                self.config, self.user_message,
                self.offers_pareto_efficient, str(self.interaction_list))
        else:
            return not_profitable_prompt(
                self.config, self.user_message,
                self.offers_pareto_efficient, str(self.interaction_list))

    def respond_to_offer(self, evaluation: str):
        last_offer = llm_output = None
        self.offers_pareto_efficient = pareto_efficient_string(
            self.constraint_user, self.constraint_bot, self.role)
        tmp = self.offers_pareto_efficient.replace('€', '') \
            .replace('Price of ', '').replace('and quality of ', '')
        self.trail += f"Pareto [ {tmp} ]\n"

        loop_count = 0
        while loop_count <= 2 and evaluation != ACCEPT:
            loop_count += 1

            content = self.get_respond_prompt(evaluation)
            messages = [{"role": "system",
                         "content": system_final_prompt(self.config)},
                        {"role": "user",
                         "content": content}]
            response = self.get_llm_response(messages)
            if response is None:
                return

            llm_output = self.extract_content(response)
            last_offer = self.interpret_offer(llm_output, -1)
            last_offer.enhance(self.offer_list, -1)
            self.add_profits(last_offer)
            greedy = self.get_greediness(
                self.constraint_user, self.constraint_bot)
            evaluation = last_offer.evaluate(self.offer_list, greedy)

            # Only for testing
            self.trail += f" L{loop_count} " \
                          f"({last_offer.price}, {last_offer.quality}) " \
                          f"[{last_offer.profit_bot}, {greedy}, {evaluation}]"
            log_llm_response(response)

        if last_offer is not None:
            last_offer.test = "from respond_to_offer"
            self.offer_list.append(last_offer)
        if llm_output is not None:
            self.store_send_data(llm_output=llm_output)
