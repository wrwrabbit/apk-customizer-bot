import asyncio
import logging

from aiogram import types, Bot

from db import engine
from models import Order
from crud.orders_crud import  OrdersCRUD
from schemas.order_status import OrderStatus, get_next_status

from .temporary_info import TemporaryInfo
from .messages_deleter import MessagesDeleter
from .screenshot_maker import make_screen_example


async def send_confirmation_request(orders: OrdersCRUD, order: Order, bot: Bot):
    member = await bot.get_chat_member(order.user_id, order.user_id)
    localisation = TemporaryInfo.get_localisation(member.user)
    yes_button = types.InlineKeyboardButton(
        text=localisation.get_message_text("yes"),
        callback_data='yes'
    )
    no_button = types.InlineKeyboardButton(
        text=localisation.get_message_text("no"),
        callback_data='no'
    )
    markup = types.InlineKeyboardMarkup(inline_keyboard=[[yes_button, no_button]])

    localized_permission_list = [localisation.get_message_text(f"permission-{permission}")
                                 for permission in order.permissions.split(",")
                                 if permission != ""]
    response = await bot.send_photo(
        order.user_id,
        photo=types.BufferedInputFile(file=make_screen_example(order.app_icon, order.app_name), filename=''),
        caption=localisation.get_message_text("request-confirmation").format(
            order.app_name, order.app_id, order.app_masked_passcode_screen, order.app_version_name,
            order.app_version_code, order.app_notification_text, ", ".join(localized_permission_list)
        ),
        reply_markup=markup,
    )
    orders.update_order_status(order.id, get_next_status(order.status))
    MessagesDeleter.deleter.add_message(response)


async def send_start_notification(orders: OrdersCRUD, order: Order, bot: Bot):
    member = await bot.get_chat_member(order.user_id, order.user_id)
    localisation = TemporaryInfo.get_localisation(member.user)
    response = await bot.send_message(order.user_id, localisation.get_message_text("build-started"))
    orders.update_order_status(order.id, get_next_status(order.status, "notified"))
    MessagesDeleter.deleter.add_message(response)


async def send_failure_notification(orders: OrdersCRUD, order: Order, bot: Bot):
    member = await bot.get_chat_member(order.user_id, order.user_id)
    localisation = TemporaryInfo.get_localisation(member.user)

    markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(
            text=localisation.get_message_text("retry-build"),
            callback_data='retry_build'
        ),
        types.InlineKeyboardButton(
            text=localisation.get_message_text("cancel-order"),
            callback_data='cancel_order'
        )
    ]])

    response = await bot.send_message(
        order.user_id,
        localisation.get_message_text("build-failed"),
        reply_markup=markup
    )
    orders.update_order_status(order.id, get_next_status(order.status))
    MessagesDeleter.deleter.add_message(response)


class OrderStatusObserver:
    @staticmethod
    async def run(bot: Bot):
        logging.info("Starting order status observer")
        orders = OrdersCRUD(engine)
        while True:
            for order in orders.get_orders_by_status(status=OrderStatus.failed):
                await send_failure_notification(orders, order, bot)
            for order in orders.get_orders_by_status(status=OrderStatus.build_started):
                await send_start_notification(orders, order, bot)
            for order in orders.get_orders_by_status(status=OrderStatus.configured):
                await send_confirmation_request(orders, order, bot)
            await asyncio.sleep(1)
