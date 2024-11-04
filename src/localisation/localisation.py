from src.localisation.native_lang_translations import translations
from typing import Union
from aiogram import types

class Localisation:
    _supported_languages = ("en", "ru", "be", "uk") #NOTE all language codes are given according to the ISO-639-1
    _DEFAULT_LANG = "en"
    
    def __init__(self, lang=None):
        self._lang = lang

    def set_language_by_message(self, arg: Union[types.Message, types.CallbackQuery, types.User]): 
        if isinstance(arg, (types.Message, types.CallbackQuery)):
            self._lang = arg.from_user.language_code
        elif isinstance(arg, types.User):
            self._lang = arg.language_code
    
    def get_language(self):
        return self._lang
    
    def set_language(self, lang):
        self._lang = lang

    def get_message_text(self, text_type):
        return Localisation.get_message_text_by_language(text_type, self._lang)
    
    @staticmethod
    def get_supported_languages():
        return Localisation._supported_languages
    
    @staticmethod
    def get_message_text_by_language(text_type, lang):
        if lang in Localisation._supported_languages:
            return translations[text_type][lang]
        else:
            return translations[text_type][Localisation._DEFAULT_LANG]
