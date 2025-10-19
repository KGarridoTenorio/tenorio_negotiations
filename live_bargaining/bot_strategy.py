import asyncio
import random
from typing import Any, List, Union

from .bot_base import BotBase
from .offer import (Offer, ACCEPT, OFFER_QUALITY, OFFER_PRICE,
                    NOT_OFFER, INVALID_OFFER, NOT_PROFITABLE, TOO_UNFAVOURABLE)
from .constants import C
from .prompts import (PROMPTS, not_profitable_prompt, empty_offer_prompt,
                      offer_without_price_prompt, offer_without_quality_prompt,
                      offer_invalid, offer_with_single_unfavourable_term_prompt)
from .optimal import optimal_solution_string


class BotStrategy(BotBase):
    def initial(self):
        if self.role == C.ROLE_BUYER:
            message = PROMPTS['first_message_PC']
        else:
            message = PROMPTS['first_message_MP']
        self.store_send_data(llm_output=message)

    async def follow_up(self):
        # Extract possible offer, add to the list if valid
        self.offer_user = await self.interpret_offer(self.user_message)
        self.offer_list.append(self.offer_user)
        await self.evaluate()

    async def interface_offer(self):
        # Offer already added to the list in Player.process_offer()
        self.offer_user = self.offer_list[-1]

        # Evaluate the profitability of user offer and respond
        await self.evaluate()

    async def evaluate(self):
        # Add profits for user and bot to the offers
        for offer in self.offer_list:
            self.add_profits(offer)

        # Evaluate the profitability of user offer and respond
        evaluation = self.offer_user.evaluate(self.constraint_bot, self.constraint_user)

        self.optimal_offer = optimal_solution_string(
            self.constraint_user, self.constraint_bot, evaluation, self.offer_user)

        if evaluation == ACCEPT:
            await self.accept_offer()
        elif evaluation in (NOT_PROFITABLE, OFFER_PRICE, OFFER_QUALITY):
            await self.respond_to_offer(evaluation)
        elif evaluation in (INVALID_OFFER, NOT_OFFER):
            await self.respond_to_non_offer(evaluation)
        elif evaluation == TOO_UNFAVOURABLE:
            await self.respond_to_offer(evaluation)
        else:
            raise Exception

    async def accept_offer(self):
        if self.offer_user.from_chat:
            content = PROMPTS['accept_from_chat'] + self.user_message
        else:
            content = PROMPTS['accept_from_interface'] + self.user_message

        response = await self.get_llm_response(content)
        llm_output = self.extract_content(response)
        self.store_send_data(llm_output=llm_output)

        if self.offer_user.from_chat:
            await self.accept_final_chat()
        else:
            await self.accept_final_interface()

    async def accept_final_chat(self):
        await asyncio.sleep(4)
        # Create offer matching offer for user to accept
        bot_offer = Offer(idx=-1,
                          price=self.offer_user.price,
                          quality=self.offer_user.quality,
                          test="accept_final_chat")
        self.add_profits(bot_offer)
        self.offer_list.append(bot_offer)
        self.store_send_data()

    async def accept_final_interface(self):
        await asyncio.sleep(4)
        # Accept on the model
        player, participant = self.get_player_participant()
        player.process_accept(self.offer_user.price, self.offer_user.quality)
        # Accept in the interface
        self.send_asyncio_data({'finished': True})

    def get_respond_prompt(self, evaluation: str) -> str:
        if evaluation == NOT_OFFER:
            return empty_offer_prompt(
                self.config, self.user_message,
                self.optimal_offer, str(self.interaction_list))
        elif evaluation == TOO_UNFAVOURABLE:
            return offer_with_single_unfavourable_term_prompt(
                self.config, self.user_message,
                self.optimal_offer, str(self.interaction_list))
        elif evaluation == OFFER_QUALITY:
            return offer_without_price_prompt(
                self.config, self.user_message,
                self.optimal_offer, str(self.interaction_list))
        elif evaluation == OFFER_PRICE:
            return offer_without_quality_prompt(
                self.config, self.user_message,
                self.optimal_offer, str(self.interaction_list))
        elif evaluation == INVALID_OFFER:
            return offer_invalid(self.config, self.user_message)
        else:
            return not_profitable_prompt(
                self.config, self.user_message,
                self.optimal_offer, str(self.interaction_list))

    async def respond_to_offer(self, evaluation: str):
        content1 = self.get_respond_prompt(evaluation)
        content2 = self.get_respond_prompt("From_0")

        llm_offers = []
        last_offer = llm_output = None

        response = await self.get_llm_response(content1)
        print('\n [DEBUG Bot_strategy.respond_to_offer 1]', response['message'], "\n")
        llm_output = self.extract_content(response)
        print('\n [DEBUG Bot_strategy.respond_to_offer 2]', llm_output, "\n")
        last_offer = await self.interpret_offer(llm_output, -1)
        if not last_offer or not last_offer.is_complete:
            response = await self.get_llm_response(content2)
            llm_output = self.extract_content(response)
            last_offer = await self.interpret_offer(llm_output, -1)

        if last_offer.is_complete:
            self.add_profits(last_offer)
        else:
            last_offer.profit_bot = last_offer.profit_user = 0
        llm_offers.append([last_offer.profit_bot, llm_output, last_offer])
        evaluation = last_offer.evaluate(self.constraint_bot, self.constraint_user)

        self.send_response(llm_output)

    async def respond_to_non_offer(self, evaluation: str):
        content1 = self.get_respond_prompt(evaluation)
        content2 = self.get_respond_prompt("From_0")

        llm_offers = []
        last_offer = llm_output = None

        response = await self.get_llm_response(
            content1 if len(llm_offers) < 3 else content2)
        print('\n [DEBUG Bot_strategy.respond_to_non_offer 1]', response['message'], "\n")
        llm_output = self.extract_content(response)
        print('\n [DEBUG Bot_strategy.respond_to_non_offer 2]', llm_output, "\n")
        last_offer = await self.interpret_offer(llm_output, -1)

        if last_offer.is_complete:
            self.add_profits(last_offer)
        else:
            last_offer.profit_bot = last_offer.profit_user = 0
        llm_offers.append([last_offer.profit_bot, llm_output, last_offer])
        evaluation = last_offer.evaluate(self.constraint_bot, self.constraint_user)

        self.send_response(llm_output)

    def send_response(self, llm_output: str):
        if llm_output is not None:
            self.store_send_data(llm_output=llm_output)
