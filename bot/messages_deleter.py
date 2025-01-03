import asyncio
from typing import Optional, Callable

import config
import logging
import pytz

from aiogram import Bot
from aiogram.types import Message
from datetime import datetime

from crud.orders_crud import OrdersCRUD
from schemas.order_status import STATUSES_BUILDING, STATUSES_GETTING_SOURCES, STATUSES_FINISHED, OrderStatus


class _MessageToDelete:
    def __init__(self, id: int, sent_date: datetime = datetime.now()):
        self.id = id
        self.sent_date = sent_date

    def __key(self):
        return self.id, self.sent_date

    def __hash__(self):
        return hash(self.__key())
    
    def __eq__(self, other):
        if isinstance(other, _MessageToDelete):
            return self.__key() == other.__key()
        return NotImplemented


class MessagesDeleter:
    deleter: 'MessagesDeleter' = None

    def __init__(self, bot: Bot, orders: OrdersCRUD):
        self.messages_by_users: dict[int, list[_MessageToDelete]] = {}
        self.on_all_messages_deleted_listener: Optional[Callable[[int], None]] = None
        self.bot = bot
        self.orders = orders

    async def _delete_message(self, chat_id: int, message_id: int):
        try:
            await self.bot.delete_message(chat_id, message_id)
        except Exception as e:
            logging.exception(e)

    async def delete_all_messages(self, chat_id: int = None):
        if chat_id:
            if chat_id in self.messages_by_users:
                messages = self.messages_by_users[chat_id]
                self.messages_by_users.pop(chat_id)
                coros = [self._delete_message(chat_id, message.id) for message in messages]
                await asyncio.gather(*coros)
                if self.on_all_messages_deleted_listener:
                    self.on_all_messages_deleted_listener(chat_id)
        else:
            coros = [self.delete_all_messages(chat_id) for chat_id in self.messages_by_users.keys()]
            await asyncio.gather(*coros)

    def add_on_all_messages_deleted_listener(self, listener: Callable[[int], None]):
        self.on_all_messages_deleted_listener = listener

    def _add_message(self, chat_id: int, message_id: int, sent_date: datetime = datetime.now()) -> _MessageToDelete:
        if chat_id not in self.messages_by_users:
            self.messages_by_users[chat_id] = []
        message = _MessageToDelete(message_id, sent_date)
        self.messages_by_users[chat_id].append(message)
        return message

    def add_message(self, message: Optional[Message]):
        if message:
            self._add_message(message.chat.id, message.message_id, message.date)
    
    def remove_message(self, message: Message):
        chat_id = message.chat.id
        if chat_id in self.messages_by_users:
            new_list = [m for m in self.messages_by_users[chat_id] if m.id != message.message_id]
            if new_list:
                self.messages_by_users[chat_id] = new_list
            else:
                self.messages_by_users.pop(chat_id)
                self.on_all_messages_deleted_listener(chat_id)

    async def force_delete_message(self, message: Message):
        self.remove_message(message)
        try:
            await self.bot.delete_message(message.chat.id, message.message_id)
        except:
            pass

    async def _check_messages(self):
        chats_to_pop = []
        for chat_id in self.messages_by_users.keys():
            new_list = [m for m in self.messages_by_users[chat_id]
                        if not self.is_time_to_delete(chat_id, m)]
            to_delete_list = list(set(self.messages_by_users[chat_id]) - set(new_list))
            if new_list:
                self.messages_by_users[chat_id] = new_list
            else:
                chats_to_pop.append(chat_id)
            coros = [self._delete_message(chat_id, message.id) for message in to_delete_list]
            await asyncio.gather(*coros)
            if not new_list:
                self.on_all_messages_deleted_listener(chat_id)
        for chat_id in chats_to_pop:
            self.messages_by_users.pop(chat_id)

    def is_time_to_delete(self, user_id: int, message: _MessageToDelete) -> bool:
        now = datetime.now().astimezone(pytz.utc)
        timeout = self.get_user_timeout(user_id)
        if timeout is None:
            return False
        else:
            return (now - message.sent_date).total_seconds() > timeout

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
        try:
            while True:
                await self._check_messages()
                await asyncio.sleep(1)
        except GeneratorExit:
            await self.delete_all_messages()
            raise Exception('GeneratorExit')

    def get_users_with_not_deleted_messages(self) -> list[int]:
        return list(self.messages_by_users.keys())

    def get_count_of_users_with_messages(self) -> int:
        return len(self.messages_by_users)
