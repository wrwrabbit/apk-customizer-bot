import asyncio
import traceback
from typing import Optional, Callable

from aiogram.exceptions import TelegramBadRequest

import config
import pytz

from aiogram import Bot
from aiogram.types import Message
from datetime import datetime, timedelta

import db
from crud.error_logs_crud import ErrorLogsCRUD
from crud.messages_to_delete_crud import MessagesToDeleteCRUD
from crud.orders_crud import OrdersCRUD
from db import engine
from models.message_to_delete import MessageToDelete
from schemas.order_status import STATUSES_BUILDING, STATUSES_GETTING_SOURCES, STATUSES_FINISHED, OrderStatus


class MessagesDeleter:
    deleter: 'MessagesDeleter' = None

    def __init__(self, bot: Bot, orders: OrdersCRUD):
        self.messages_to_delete_crud = MessagesToDeleteCRUD(engine)
        self.on_all_messages_deleted_listener: Optional[Callable[[int], None]] = None
        self.bot = bot
        self.orders = orders

    async def _delete_message(self, message_to_delete: MessageToDelete):
        try:
            await self.bot.delete_message(message_to_delete.user_id, message_to_delete.message_id)
        except Exception as e:
            self._log_exception_if_needed(e)


    @staticmethod
    def _log_exception_if_needed(exception: Exception):
        if isinstance(exception, TelegramBadRequest) and "message to delete not found" in exception.message:
            return
        ErrorLogsCRUD(db.engine).add_log(
            f"During MessagesDeleter the following exception occurred:\n\n{traceback.format_exc()}")

    async def delete_all_messages(self, user_id: int = None):
        if user_id:
            coros = [self._delete_message(message) for message in self.messages_to_delete_crud.get_user_messages(user_id)]
            await asyncio.gather(*coros)
            self.messages_to_delete_crud.remove_user_messages(user_id)
            if self.on_all_messages_deleted_listener:
                self.on_all_messages_deleted_listener(user_id)
        else:
            coros = [self.delete_all_messages(user_id) for user_id in self.messages_to_delete_crud.get_users()]
            await asyncio.gather(*coros)

    def add_on_all_messages_deleted_listener(self, listener: Callable[[int], None]):
        self.on_all_messages_deleted_listener = listener

    def _add_message(self, user_id: int, message_id: int, sent_date: datetime = datetime.now().astimezone(pytz.utc)):
        message_to_delete = MessageToDelete()
        message_to_delete.user_id = user_id
        message_to_delete.message_id = message_id
        message_to_delete.sent_date = sent_date
        self.messages_to_delete_crud.add_message_to_delete(message_to_delete)

    def add_message(self, message: Optional[Message]):
        if message:
            self._add_message(message.chat.id, message.message_id, message.date.astimezone(pytz.utc))
    
    def remove_message(self, message: Message):
        user_id = message.chat.id
        self.messages_to_delete_crud.remove_message(user_id, message.message_id)
        if self.on_all_messages_deleted_listener and self.messages_to_delete_crud.get_user_messages_count(user_id) == 0:
            self.on_all_messages_deleted_listener(user_id)

    async def force_delete_message(self, message: Message):
        self.remove_message(message)
        try:
            await self.bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            self._log_exception_if_needed(e)

    async def _check_messages(self):
        for user_id in self.messages_to_delete_crud.get_users():
            timeout = self.get_user_timeout(user_id)
            if timeout is None:
                continue
            max_date = datetime.now().astimezone(pytz.utc) - timedelta(seconds=timeout)
            coros = [self._delete_message(message) for message in self.messages_to_delete_crud.get_user_messages(user_id, max_date)]
            await asyncio.gather(*coros)
            self.messages_to_delete_crud.remove_user_messages(user_id, max_date)
            if self.on_all_messages_deleted_listener and self.messages_to_delete_crud.get_user_messages_count(user_id) == 0:
                self.on_all_messages_deleted_listener(user_id)

    def get_user_timeout(self, user_id: int) -> Optional[int]:
        order = self.orders.get_user_order(user_id)
        if order is None:
            return config.DELETE_MESSAGES_WITHOUT_ORDERS_AFTER_SEC
        elif order.status in (STATUSES_BUILDING + STATUSES_GETTING_SOURCES + [OrderStatus.queued]):
            return None
        elif order.status in STATUSES_FINISHED:
            return config.DELETE_MESSAGES_WITH_FINISHED_ORDERS_AFTER_SEC
        else:
            return config.DELETE_MESSAGES_AFTER_SEC

    async def run(self):
        while True:
            await self._check_messages()
            await asyncio.sleep(10)

    def get_count_of_users_with_messages(self) -> int:
        return self.messages_to_delete_crud.get_count_of_users()
