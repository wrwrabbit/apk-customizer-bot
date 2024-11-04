from aiogram import types
from typing import Union
from src.localisation.localisation import Localisation

_processed_media_groups: list[tuple[int, int]] = []
_choose_id_messages: dict[int, types.Message] = {} #tobe cleaned

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
        

def add_media_group_token(token: tuple[int, int]) -> bool:
    global _processed_media_groups
    if not (token in _processed_media_groups):
        if len(_processed_media_groups) > 100:
            _processed_media_groups = _processed_media_groups[1:]
        _processed_media_groups.append(token)
        return True
    return False

def put_choose_id_message(user_id: int, message: types.Message):
    global _choose_id_messages
    _choose_id_messages[user_id] = message


def get_choose_id_message(user_id: int) -> types.Message:
    if user_id not in _choose_id_messages:
        return None
    else:
        return _choose_id_messages[user_id]

