import os
import asyncio
import shutil
import traceback

from aiogram import types, Bot

import config
import utils
from db import engine
from utils import normalize_name
from models import Order
from crud.orders_crud import OrdersCRUD
from schemas.order_status import OrderStatus, get_next_status

from .messages_deleter import MessagesDeleter
from .temporary_info import TemporaryInfo


async def send_apk(orders: OrdersCRUD, order: Order, bot: Bot):
    print(f"Sending apk for order #{order.id}")
    try:
        apk_sent = False
        for attempt in range(0, 3):
            apk_sent = await try_send_apk(orders, order, bot)
            if apk_sent:
                break
        if not apk_sent:
            order.status = get_next_status(order.status, "fail")
            orders.update_order(order)
            from .bot import send_error
            await send_error("Apk didn't sent after 3 attempts")
            raise Exception("Apk didn't sent after 3 attempts")

        member = await bot.get_chat_member(order.user_id, order.user_id)
        localisation = TemporaryInfo.get_localisation(member.user)
        markup = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(
                text=localisation.get_message_text("clear-bot"),
                callback_data='clear_bot'
            ),
        ]])
        MessagesDeleter.deleter.add_message(
            await bot.send_message(
                order.user_id, localisation.get_message_text("build-ended").format(config.DELETE_MESSAGES_AFTER_SEC / 60), 
                reply_markup=markup
            )
        )
        orders.remove_order(order.id)
    except BaseException as e:
        from .bot import send_error
        print("Failed to send apk:", e)
        await send_error(f"Failed to send apk: {e}")
        traceback.print_exc()


async def try_send_apk(orders: OrdersCRUD, order: Order, bot: Bot) -> bool:
    try:
        order.status = get_next_status(order.status, "send_apk")
        orders.update_order(order)
        filepath = os.path.join(
            utils.make_order_apk_dir_path(order.id),
            "app.apk",
        )

        if order.update_tag is None:
            tg_filename = f'{normalize_name(order.app_name)}.apk'
        else:
            tg_filename = f'update-{order.update_tag}.apk'  # clients will expect a filename in this format

        future = bot.send_document(
            order.user_id,
            document=types.FSInputFile(path=filepath, filename=tg_filename)
        )
        sending_result = await asyncio.wait((future,), timeout=1800)
        response = next(iter(sending_result[0])).result()
        MessagesDeleter.deleter.add_message(response)
        delete_order_dir(order)
        return True
    except BaseException as e:
        from .bot import send_error
        print("Failed to send apk:", e)
        await send_error(f"Failed to send apk:{e}")
        traceback.print_exc()
        order.status = get_next_status(order.status, "repeat")
        orders.update_order(order)
        return False


def delete_order_dir(order: Order):
    shutil.rmtree(utils.make_order_apk_dir_path(order.id))


class ApkSender:
    @staticmethod
    async def run(bot: Bot):
        print("Starting apk sender")
        orders = OrdersCRUD(engine)
        while True:
            for i in orders.get_orders_by_status(status=OrderStatus.built):
                await send_apk(orders, i, bot)
            await asyncio.sleep(1)
