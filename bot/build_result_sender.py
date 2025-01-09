import logging
import os
import asyncio
import shutil
import traceback

from aiogram import types, Bot

import config
import utils
from utils import normalize_name
from models import Order
from crud.orders_crud import OrdersCRUD
from schemas.order_status import get_next_status

from .messages_deleter import MessagesDeleter
from . import order_status_observer
from .temporary_info import get_sending_apk_attempt_count, increase_sending_apk_attempt_count, \
    delete_sending_apk_attempt_count


class BuildResultSender:
    def __init__(self, bot: Bot, orders: OrdersCRUD, status_observer: 'order_status_observer.OrderStatusObserver'):
        self.bot = bot
        self.orders = orders
        self.status_observer = status_observer

    async def send_build_result(self, order: Order):
        logging.info(f"Sending build result for order #{order.id}")
        try:
            await self.try_send_build_result(order)
            order.status = get_next_status(order.status)
            self.orders.update_order(order)
            MessagesDeleter.deleter.add_message(await self.status_observer.on_status_changed(order))
            delete_sending_apk_attempt_count(order.id)
        except BaseException as e:
            from .bot import send_error
            logging.error(f"Failed to send build result: {e}")
            exception_text = traceback.format_exc()
            await send_error(f"Failed to send build result:\n\n{exception_text}")
            traceback.print_exc()
            increase_sending_apk_attempt_count(order.id)
            await self.check_attempt_count(order)

    async def check_attempt_count(self, order: Order):
        count = get_sending_apk_attempt_count(order.id)
        if count < config.APK_SEND_MAX_RETRY_COUNT:
            order.status = get_next_status(order.status, "repeat")
            self.orders.update_order(order)
            MessagesDeleter.deleter.add_message(await self.status_observer.on_status_changed(order))
        else:
            delete_sending_apk_attempt_count(order.id)
            order.status = get_next_status(order.status, "fail")
            self.orders.update_order(order)
            MessagesDeleter.deleter.add_message(await self.status_observer.on_status_changed(order))
            from .bot import send_error
            await send_error(f"Apk didn't sent after {config.APK_SEND_MAX_RETRY_COUNT} attempts")

    async def try_send_build_result(self, order: Order) -> bool:
        order.status = get_next_status(order.status, "send_result")
        await self.bot.send_chat_action(order.user_id, "upload_document")
        self.orders.update_order(order)
        MessagesDeleter.deleter.add_message(await self.status_observer.on_status_changed(order))
        filepath = os.path.join(
            utils.make_order_build_result_dir_path(order.id),
            "sources.zip" if order.sources_only else "app.apk",
        )

        if order.sources_only:
            tg_filename = 'sources.zip'
        elif order.update_tag is None:
            tg_filename = f'{normalize_name(order.app_name)}.apk'
        else:
            tg_filename = f'update-{order.update_tag}.apk'  # clients will expect a filename in this format

        future = self.bot.send_document(
            order.user_id,
            document=types.FSInputFile(path=filepath, filename=tg_filename)
        )
        sending_result = await asyncio.wait((future,), timeout=1800)
        response = next(iter(sending_result[0])).result()
        MessagesDeleter.deleter.add_message(response)
        self.delete_order_dir(order)
        return True

    @staticmethod
    def delete_order_dir(order: Order):
        shutil.rmtree(utils.make_order_build_result_dir_path(order.id))
