import re
from random import randint
from unidecode import unidecode
from aiogram import Bot, types

import config
from models import Order
from localization import messages


PREFIXES = ['com', 'org', 'net', 'us', 'co.uk']
POSTFIXES = ['app', 'android']
DELIMITERS = ['', '_']
NORMAL_NAME_PATTERN = re.compile(r'[a-z]{1}[a-z\d_]+')
APP_ID_PATTERN = re.compile(r'^([A-Za-z]{1}[A-Za-z\d_]*\.)+[A-Za-z][A-Za-z\d_]*$')


def normalize_app_name(appname, delim=''):
    normalized = re.sub(r'[\W]', delim, unidecode(appname)).lower()
    if NORMAL_NAME_PATTERN.match(normalized):
        return normalized
    else:
        return config.APP_NAME_REPLACEMENT_FOR_NOT_NORMALIZED


def generate_app_id(appname):
    prefix = PREFIXES[randint(0, len(PREFIXES) - 1)]
    postfix = POSTFIXES[randint(0, len(POSTFIXES) - 1)]
    delim = DELIMITERS[randint(0, len(DELIMITERS) - 1)]
    normalized = normalize_app_name(appname, delim)
    normalized = NORMAL_NAME_PATTERN.findall(normalized)[0]
    return f'{prefix}.{normalized}.{postfix}'


async def send_app_id_options(bot: Bot, order: Order, lang: str) -> types.Message:
    suggestions = []
    while len(set(suggestions)) < 3:
        suggestion = generate_app_id(normalize_app_name(order.app_name))
        if suggestion not in suggestions:
            suggestions.append(suggestion)
    buttons = []
    for suggestion in suggestions:
        button = types.InlineKeyboardButton(
            text=suggestion,
            callback_data=suggestion
        )
        buttons.append([button])
    custom = types.InlineKeyboardButton(
        text=messages['custom-app-id'][lang],
        callback_data='custom'
    )
    buttons.append([custom])
    markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return await bot.send_message(
        order.user_id,
        "\n".join([
            messages['app-name-is'][lang].format(
                order.app_name, order.app_id
            ),
            messages['app-id-about'][lang],
            messages['ask-app-id'][lang]
        ]),
        reply_markup=markup,
    )

