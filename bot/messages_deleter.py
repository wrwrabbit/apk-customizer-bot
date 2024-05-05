import asyncio
import config
import logging
import pytz

from aiogram import Bot
from aiogram.types import Message
from datetime import datetime


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


def _is_time_to_delete(message: _MessageToDelete) -> bool:
    now = datetime.now().astimezone(pytz.utc)
    return (now - message.sent_date).total_seconds() > config.DELETE_MESSAGES_AFTER_SEC


class MessagesDeleter:
    deleter = None

    def __init__(self):
        self.messages_by_users: dict[int, list[_MessageToDelete]] = {}

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
        else:
            coros = [self.delete_all_messages(chat_id) for chat_id in self.messages_by_users.keys()]
            await asyncio.gather(*coros)

    def _add_message(self, chat_id: int, message_id: int, sent_date: datetime = datetime.now()) -> _MessageToDelete:
        if chat_id not in self.messages_by_users:
            self.messages_by_users[chat_id] = []
        message = _MessageToDelete(message_id, sent_date)
        self.messages_by_users[chat_id].append(message)
        return message

    def add_message(self, message: Message):
        if message:
            msg = self._add_message(message.chat.id, message.message_id, message.date)
    
    def remove_message(self, message: Message):
        if message.chat.id in self.messages_by_users:
            new_list = [m for m in self.messages_by_users[message.chat.id] if m.id != message.message_id]
            if new_list:
                self.messages_by_users[message.chat.id] = new_list
            else:
                self.messages_by_users.pop(message.chat.id)

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
                        if not _is_time_to_delete(m)]
            to_delete_list = list(set(self.messages_by_users[chat_id]) - set(new_list))
            if new_list:
                self.messages_by_users[chat_id] = new_list
            else:
                chats_to_pop.append(chat_id)
            coros = [self._delete_message(chat_id, message.id) for message in to_delete_list]
            await asyncio.gather(*coros)
        for chat_id in chats_to_pop:
            self.messages_by_users.pop(chat_id)

    async def run(self, bot: Bot):
        self.bot = bot
        try:
            while True:
                await self._check_messages()
                await asyncio.sleep(1)
        except GeneratorExit:
            await self.delete_all_messages()
            raise Exception('GeneratorExit')
