import asyncio
import io
import logging

from aiogram import types, Bot

from db import engine
from models import Order
from orders import OrdersQueue
from schemas.order_status import OrderStatus

from localization import messages, get_language
from .messages_deleter import MessagesDeleter
from .screenshot_maker import make_screen_example


async def send_confirmation_request(db: OrdersQueue, order: Order, bot: Bot):
    member = await bot.get_chat_member(order.user_id, order.user_id)
    lang = get_language(member.user)
    yesbutton = types.InlineKeyboardButton(
        text=messages['yes'][lang],
        callback_data='yes'
    )
    nobutton = types.InlineKeyboardButton(
        text=messages['no'][lang],
        callback_data='no'
    )
    markup = types.InlineKeyboardMarkup(inline_keyboard=[[yesbutton, nobutton]])

    response = await bot.send_photo(
        order.user_id,
        photo=types.BufferedInputFile(file=make_screen_example(order.app_icon, order.app_name), filename=''),
        caption=messages['request-confirmation'][lang].format(
            order.app_name, order.app_id
        ),
        reply_markup=markup,
    )
    db.orders.update_order_status(order.id, OrderStatus.confirmation)
    MessagesDeleter.deleter.add_message(response)


async def send_start_notification(db: OrdersQueue, order: Order, bot: Bot):
    member = await bot.get_chat_member(order.user_id, order.user_id)
    lang = get_language(member.user)
    response = await bot.send_message(order.user_id, messages['build-started'][lang])
    db.orders.update_order_status(order.id, OrderStatus.building)
    MessagesDeleter.deleter.add_message(response)


async def send_failure_notification(db: OrdersQueue, order: Order, bot: Bot):
    member = await bot.get_chat_member(order.user_id, order.user_id)
    lang = get_language(member.user)

    markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(
            text=messages['retry-build'][lang],
            callback_data='retry_build'
        ),
        types.InlineKeyboardButton(
            text=messages['cancel-order'][lang],
            callback_data='cancel_order'
        )
    ]])

    response = await bot.send_message(
        order.user_id,
        messages['build-failed'][lang],
        reply_markup=markup
    )
    db.orders.update_order_status(order.id, OrderStatus.failed_notified)
    MessagesDeleter.deleter.add_message(response)


class OrderStatusObserver:
    @staticmethod
    async def run(bot: Bot):
        logging.info("Starting order status observer")
        db = OrdersQueue(engine)
        while True:
            for order in db.orders.get_orders(status=OrderStatus.failed):
                await send_failure_notification(db, order, bot)
            for order in db.orders.get_orders(status=OrderStatus.build_started):
                await send_start_notification(db, order, bot)
            for order in db.orders.get_orders(status=OrderStatus.configured):
                await send_confirmation_request(db, order, bot)
            await asyncio.sleep(1)
