from aiogram import types
from typing import Union
from src.localisation.localisation import Localisation

_processed_media_groups: list[tuple[int, str]] = []
_sending_apk_attempts: dict[int, int] = {}
_messages_with_buttons: dict[int, list[types.Message]] = {}

class TemporaryInfo:	
    #This method is done in a way that in case the maintainer wishes to get the language
    #	from the string, it always has a safe mechanism in terms of the message
    @staticmethod
    def get_localisation(arg: Union[types.Message, types.CallbackQuery, types.User], lang: str = None):
        lcl = Localisation()
        if lang is not None:
            if lang in lcl.get_supported_languages():
                lcl.set_language(lang)
                return lcl

        lcl.set_language_by_message(arg)
        return lcl
        

def add_media_group_token(token: tuple[int, str]) -> bool:
    global _processed_media_groups
    if not (token in _processed_media_groups):
        if len(_processed_media_groups) > 100:
            _processed_media_groups = _processed_media_groups[1:]
        _processed_media_groups.append(token)
        return True
    return False


def get_sending_apk_attempt_count(order_id: int):
    return _sending_apk_attempts.get(order_id, 0)


def increase_sending_apk_attempt_count(order_id: int):
    _sending_apk_attempts[order_id] = get_sending_apk_attempt_count(order_id) + 1


def delete_sending_apk_attempt_count(order_id: int):
    if order_id in _sending_apk_attempts:
        del _sending_apk_attempts[order_id]


def add_message_with_buttons(user_id: int, message: types.Message):
    if user_id not in _messages_with_buttons:
        _messages_with_buttons[user_id] = [message]
    else:
        _messages_with_buttons[user_id].append(message)


def get_messages_with_buttons(user_id: int) -> list[types.Message]:
    return _messages_with_buttons.get(user_id, [])


def clear_messages_with_buttons_list(user_id: int):
    if user_id in _messages_with_buttons:
        del _messages_with_buttons[user_id]
