from typing import Union
from aiogram import types


def get_language(arg: Union[types.Message, types.CallbackQuery, types.User]) -> str:
    if isinstance(arg, (types.Message, types.CallbackQuery)):
        lang = arg.from_user.language_code
    elif isinstance(arg, types.User):
        lang = arg.language_code
    return lang
