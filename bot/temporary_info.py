from aiogram import types

from localization.messages import DEFAULT_LANG

_processed_media_groups: list[tuple[int, int]] = []
_user_languages: dict[int, str] = {}
_choose_id_messages: dict[int, types.Message] = {}


def add_media_group_token(token: tuple[int, int]) -> bool:
    global _processed_media_groups
    if not (token in _processed_media_groups):
        if len(_processed_media_groups) > 100:
            _processed_media_groups = _processed_media_groups[1:]
        _processed_media_groups.append(token)
        return True
    return False


def put_user_language(user_id: int, language: str):
    global _user_languages
    _user_languages[user_id] = language


def get_user_language(user_id: int) -> str:
    if user_id not in _user_languages:
        return DEFAULT_LANG
    else:
        return _user_languages[user_id]


def put_choose_id_message(user_id: int, message: types.Message):
    global _choose_id_messages
    _choose_id_messages[user_id] = message


def get_choose_id_message(user_id: int) -> types.Message:
    if user_id not in _choose_id_messages:
        return None
    else:
        return _choose_id_messages[user_id]

