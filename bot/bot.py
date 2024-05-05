import asyncio
import io
import os
from functools import wraps, partial
from PIL import Image, UnidentifiedImageError
from typing import Callable, Union, List

from aiogram import Bot, Dispatcher, F
from aiogram import types
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import Command

import config
import utils
from db import engine
from orders import OrdersQueue
from schemas.order_status import OrderStatus, STATUSES_IN_PROGRESS, STATUSES_BUILDING, STATUSES_CONFIGURING, STATUSES_COMPLETED
from .generate_app_id import (
    APP_ID_PATTERN,
    normalize_app_name,
    send_app_id_options,
)
from localization import get_language, messages
from .apk_sender import ApkSender
from .status_observer import OrderStatusObserver
from .messages_deleter import MessagesDeleter
from .temporary_info import add_media_group_token, put_user_language, put_choose_id_message, get_choose_id_message

os.makedirs(config.TMP_DIR, exist_ok=True)

session = AiohttpSession(
    api=TelegramAPIServer.from_base(f'http://{config.TELEGRAM_HOST}:8081')
)
bot = Bot(config.TOKEN, default=DefaultBotProperties(parse_mode="HTML"), session=session)
dp = Dispatcher()

db = OrdersQueue(engine)

status_observer = None
apk_sender = None


def start():
    global status_observer, apk_sender
    status_observer = OrderStatusObserver()
    apk_sender = ApkSender()
    MessagesDeleter.deleter = MessagesDeleter()
    dp.startup.register(on_startup)
    asyncio.run(dp.start_polling(bot))


async def on_startup(*args, **kwargs):
    for lang in messages['help-desc'].keys():
        await bot.set_my_commands(
            [
                types.bot_command.BotCommand(command='/help', description=messages['help-desc'][lang]),
                types.bot_command.BotCommand(command='/build', description=messages['build-desc'][lang]),
                types.bot_command.BotCommand(command='/status', description=messages['status-desc'][lang]),
                types.bot_command.BotCommand(command='/cancel', description=messages['cancel-desc'][lang]),
            ],
            language_code=lang)
    if config.SKIP_UPDATES:
        await bot.delete_webhook(True)
    asyncio.create_task(status_observer.run(bot))
    asyncio.create_task(apk_sender.run(bot))
    asyncio.create_task(MessagesDeleter.deleter.run(bot))


def log_msg(fun: Callable):
    @wraps(fun)
    def wrapper(message: types.Message):
        userid = message.from_user.id
        order = db.get_order(userid)
        try:
            user = utils.mask_userid(userid)
            if order:
                user = f'{user} ({order.status})'
            print(f'{user}: {message.text}')
        except Exception as e:
            pass
        return fun(message)

    return wrapper


def auto_delete_messages(fun: Callable):
    @wraps(fun)
    async def wrapper(message: Union[types.Message, types.CallbackQuery]):
        if isinstance(message, types.Message):
            MessagesDeleter.deleter.add_message(message)
        elif isinstance(message, types.CallbackQuery):
            MessagesDeleter.deleter.add_message(message.message)
        else:
            raise Exception(f'auto_delete_messages attached to an invalid function. Invalid argument type {type(message)}')
        response_message = await fun(message)
        if response_message:
            MessagesDeleter.deleter.add_message(response_message)

    return wrapper


def on_order_status(
        queue: OrdersQueue,
        statuses: List[OrderStatus],
        message: Union[types.Message, types.CallbackQuery]
):
    """Filter function for handling
    only orders with status matching any status in `statuses`"""

    userid = message.from_user.id
    if userid not in queue.get_users():
        return False
    order = queue.get_order(userid)
    return order.status in statuses


async def send_cancelled_message(message: Union[types.Message, types.CallbackQuery]) -> types.Message:
    lang = get_language(message)
    markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(
            text=messages['clear-bot'][lang],
            callback_data='clear_bot'
        ),
    ]])
    actual_message = message if isinstance(message, types.Message) else message.message
    return await actual_message.answer(messages['canceled'][lang], reply_markup=markup)


@dp.message(Command(commands=['start']))
@auto_delete_messages
async def start_command(message: types.Message) -> types.Message:
    lang = get_language(message)
    return await message.answer(messages['welcome'][lang])


@dp.message(Command(commands=['help']))
@log_msg
@auto_delete_messages
async def get_help(message: types.Message) -> types.Message:
    lang = get_language(message)
    return await message.answer(messages['help'][lang])


@dp.message(Command(commands=['status']))
@log_msg
@auto_delete_messages
async def get_order_status(message: types.Message) -> types.Message:
    userid = message.from_user.id
    lang = get_language(message)
    if userid not in db.get_users():
        return await message.answer(messages['no-orders-yet'][lang])
    order = db.get_order(userid)
    
    if order.status in STATUSES_CONFIGURING:
        return await message.answer(messages['status-configuring'][lang])
    elif order.status == OrderStatus.queued:
        return await message.answer(messages['status-queued'][lang])
    elif order.status in STATUSES_BUILDING:
        return await message.answer(messages['status-building'][lang])
    elif order.status in STATUSES_COMPLETED:
        return await message.answer(messages['status-completed'][lang])
    else:
        return await message.answer(messages['status-unknown'][lang])


@dp.message(Command(commands=['cancel']))
@log_msg
@auto_delete_messages
async def cancel_order(message: types.Message) -> types.Message:
    userid = message.from_user.id
    lang = get_language(message)
    if userid not in db.get_users():
        return await message.answer(messages['no-orders-yet'][lang])
    order = db.get_order(userid)
    if order.status in STATUSES_IN_PROGRESS:
        return await message.answer(messages["cannot-cancel"][lang])
    db.orders.update_order_status(order.id, OrderStatus.canceled)
    result = await send_cancelled_message(message)
    await MessagesDeleter.deleter.delete_all_messages(message.chat.id)
    return result


@dp.message(Command(commands=['build']))
@log_msg
@auto_delete_messages
async def create_order(message: types.Message) -> types.Message:
    userid = message.from_user.id
    lang = get_language(message)
    if userid not in db.get_users():
        db.record_user(userid)
        result = await message.answer(messages['ask-for-app-name'][lang])
        await MessagesDeleter.deleter.delete_all_messages(message.chat.id)
        return result
    else:
        order = db.get_order(userid)
        if order.status in STATUSES_IN_PROGRESS:
            return await message.answer(messages['cannot-create'][lang])
        return await message.answer(messages['suggest-cancel'][lang])


@dp.message(
    F.text,
    partial(on_order_status, db, [OrderStatus.appname])
)
@log_msg
@auto_delete_messages
async def customize_appname(message: types.Message) -> types.Message:
    userid = message.from_user.id
    lang = get_language(message)
    order = db.get_order(userid)
    is_bad_name = len(message.text) > config.NAME_LENGTH_LIMIT \
        or len(normalize_app_name(message.text)) > config.NAME_LENGTH_LIMIT
    if is_bad_name:
        return await message.answer(messages['app-name-too-long'][lang].format(config.NAME_LENGTH_LIMIT))
    order.app_name = message.text
    order.status = OrderStatus.appid
    response = await send_app_id_options(bot, order, lang)
    db.update_order(order)
    put_choose_id_message(userid, response)
    return response


@dp.callback_query(
    partial(on_order_status, db, [OrderStatus.appid])
)
@auto_delete_messages
async def choose_app_id(call: types.CallbackQuery) -> types.Message:
    userid = call.from_user.id
    order = db.get_order(userid)
    lang = get_language(call)
    if call.data != 'custom':
        order.app_id = call.data
        await call.message.edit_reply_markup()
        await call.answer()
        response = await call.message.answer(
            '\n'.join([
                messages['app-id-is'][lang].format(order.app_id),
                messages['ask-icon'][lang],
            ])
        )
        order.status = OrderStatus.appicon
    else:
        put_choose_id_message(userid, None)
        await call.message.edit_reply_markup()
        await call.answer()
        response = await call.message.answer(messages['ask-custom-app-id'][lang].format(config.APPID_EXAMPLE))
    db.update_order(order)
    return response


@dp.message(
    F.text,
    partial(on_order_status, db, [OrderStatus.appid])
)
@log_msg
@auto_delete_messages
async def customize_appid(message: types.Message) -> types.Message:
    userid = message.from_user.id
    lang = get_language(message)
    order = db.get_order(userid)

    if not APP_ID_PATTERN.fullmatch(message.text):
        return await message.answer(
            messages['invalid-app-id'][lang].format(config.APPID_DOCS_URL)
        )
    appid = message.text.lower()
    order.app_id = appid
    order.status = OrderStatus.appicon
    response = await message.answer(
        "\n".join([
            messages['app-id-is'][lang].format(order.app_id),
            messages['ask-icon'][lang]
        ])
    )
    db.update_order(order)
    previous_message = get_choose_id_message(userid)
    if previous_message is not None:
        await previous_message.edit_reply_markup()
    return response


@dp.message(
    F.document | F.photo,
    partial(on_order_status, db, [OrderStatus.appicon])
)
@auto_delete_messages
async def customize_icon(message: types.Message) -> types.Message:
    userid = message.from_user.id
    order = db.get_order(userid)
    lang = get_language(message)

    if message.media_group_id is not None: # Groupped photos are not allowed.
        if add_media_group_token((message.chat.id, message.media_group_id)): # Answer only the first media in group.
            return await message.answer(messages['grouped-images-are-not-allowed'][lang])
        else:
            return None
    if message.document:
        media = message.document
    else:  # Compressed image received.
        # message.photo contains 3 PhotoSize items for handling different resolutions.
        # The last item corresponds to the highest resolution.
        # Let us use it:
        media = message.photo[-1]
    if media.file_size > config.FILE_SIZE_LIMIT:
        return await message.answer(messages['file-too-big'][lang].format(config.FILE_SIZE_LIMIT // 1024 ** 2))
    iconfile = await bot.get_file(media.file_id)
    with open(iconfile.file_path, 'rb') as f:
        icon_bytes = f.read()
    try:
        Image.open(io.BytesIO(icon_bytes))
    except UnidentifiedImageError:
        return await message.answer(messages['file-is-not-image'][lang])
    db.orders.update_appicon(order.id, icon_bytes)
    db.orders.update_order_status(order.id, OrderStatus.configured)


@dp.message(
    partial(on_order_status, db, [OrderStatus.appicon])
)
@auto_delete_messages
async def handle_invalid_icon(message: types.Message) -> types.Message:
    lang = get_language(message)

    if message.audio or message.video: # If message contains something like a file
        return await message.answer(messages['file-is-not-image'][lang])
    else: # If message doesn't look like a file
        return await message.answer(messages['ask-icon'][lang])


@dp.callback_query(
    partial(on_order_status, db, [OrderStatus.confirmation])
)
@auto_delete_messages
async def confirm_order(call: types.CallbackQuery) -> types.Message:
    userid = call.from_user.id
    order = db.get_order(userid)
    lang = get_language(call)
    put_user_language(userid, lang)

    if call.data == 'yes':
        db.orders.update_order_status(order.id, OrderStatus.queued)
        await call.message.edit_reply_markup()
        await call.answer()
        return await call.message.answer(messages['queued'][lang])
    elif call.data == 'no':
        db.orders.update_order_status(order.id, OrderStatus.canceled)
        await call.message.edit_reply_markup()
        await call.answer()
        return await send_cancelled_message(call)


@dp.message(
    partial(on_order_status, db, [OrderStatus.confirmation])
)
@auto_delete_messages
async def handle_confirmation_message(message: types.Message) -> types.Message:
    lang = get_language(message)

    return await message.answer(messages['request-confirmation-again'][lang])


@dp.callback_query(
    partial(on_order_status, db, [OrderStatus.failed_notified])
)
@auto_delete_messages
async def process_failure(call: types.CallbackQuery) -> types.Message:
    userid = call.from_user.id
    order = db.get_order(userid)
    lang = get_language(call)
    put_user_language(userid, lang)

    if call.data == 'retry_build':
        await call.message.edit_reply_markup()
        await call.answer()
        response = await call.message.answer(messages['queued'][lang])
        db.orders.update_order_status(order.id, OrderStatus.queued)
    else:
        await call.message.edit_reply_markup()
        await call.answer()
        response = await send_cancelled_message(call)
        db.orders.update_order_status(order.id, OrderStatus.canceled)
    return response


@dp.message(
    partial(on_order_status, db, [OrderStatus.queued])
)
@log_msg
@auto_delete_messages
async def ask_to_wait_for_build_queued(message: types.Message) -> types.Message:
    lang = get_language(message)
    return await message.answer(messages['awaiting-build'][lang])


@dp.message(
    partial(on_order_status, db, [OrderStatus.building])
)
@log_msg
@auto_delete_messages
async def ask_to_wait_for_build_building(message: types.Message) -> types.Message:
    lang = get_language(message)
    return await message.answer(messages['is-building'][lang])


@dp.callback_query(
    F.data == 'clear_bot'
)
@auto_delete_messages
async def process_failure(call: types.CallbackQuery) -> types.Message:
    message = call.message
    await asyncio.gather(MessagesDeleter.deleter.delete_all_messages(message.chat.id),
                         message.bot.delete_message(message.chat.id, message.message_id))


@dp.message(F.photo | F.audio | F.document | F.sticker | F.story | F.video | F.voice | F.contact | F.poll | F.location)
@log_msg
@auto_delete_messages
async def fallback(message: types.Message) -> types.Message:
    lang = get_language(message)
    return await message.answer(messages['media-files-are-not-allowed'][lang])


@dp.message(F.text)
@log_msg
@auto_delete_messages
async def fallback(message: types.Message) -> types.Message:
    lang = get_language(message)
    return await message.answer(messages['unknown-text-response'][lang])

