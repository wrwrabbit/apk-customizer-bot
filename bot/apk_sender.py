import os
import asyncio
import traceback

from aiogram import types, Bot

import config
from db import engine
from bot.generate_app_id import normalize_app_name
from models import Order
from orders import OrdersQueue
from schemas.order_status import OrderStatus

from localization import messages
from .messages_deleter import MessagesDeleter
from .temporary_info import get_user_language


async def send_apk(db: OrdersQueue, order: Order, bot: Bot):
    filepath = os.path.join(
        os.path.abspath(config.TMP_DIR),
        str(order.id),
        "Partisan-Telegram-Android",
        "TMessagesProj",
        "build",
        "outputs",
        "apk",
        "afat",
        "release",
        "app.apk",
    )
    print(f"Sending apk for order #{order.id}")
    try:
        order.app_name
        future = bot.send_document(
            order.user_id,
            document=types.FSInputFile(path=filepath, filename=f'{normalize_app_name(order.app_name)}.apk')
        )
        db.orders.update_order_status(order.id, OrderStatus.sending_apk)
        sending_result = await asyncio.wait((future,), timeout=1800)
        response = next(iter(sending_result[0])).result()
        MessagesDeleter.deleter.add_message(response)
        lang = get_user_language(order.user_id)

        markup = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(
                text=messages['clear-bot'][lang],
                callback_data='clear_bot'
            ),
        ]])
        MessagesDeleter.deleter.add_message(
            await bot.send_message(
                order.user_id, messages['build-ended'][lang].format(config.DELETE_MESSAGES_AFTER_SEC / 60), 
                reply_markup=markup
            )
        )
    except BaseException as e:
        print("Failed to send apk. See traceback below")
        traceback.print_exc()
    else:
        db.orders.update_order_status(order.id, OrderStatus.completed)


class ApkSender:
    @staticmethod
    async def run(bot: Bot):
        print("Starting apk sender")
        db = OrdersQueue(engine)
        while True:
            for i in db.orders.get_orders(status=OrderStatus.built):
                await send_apk(db, i, bot)
            await asyncio.sleep(1)
