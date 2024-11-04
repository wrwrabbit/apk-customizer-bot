import asyncio
import io
import json
import logging
import os
import re
import sys
import traceback
from datetime import datetime, timedelta

from functools import wraps, partial

import pytz
from aiogram.utils import formatting
import jwt
from PIL import Image, UnidentifiedImageError
from typing import Callable, Union, List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram import types
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from argon2 import PasswordHasher

import config
import utils
from bot.error_logs_observer import ErrorLogsObserver
from bot.order_generator import OrderGenerator
from crud.user_build_stats_crud import UserBuildStatsCRUD
from db import engine
from models import Order
from crud.orders_crud import OrdersCRUD
from schemas.android_app_permission import AndroidAppPermission
from crud.workers_crud import WorkersCRUD
from schemas.order_status import OrderStatus, STATUSES_BUILDING, STATUSES_CONFIGURING, \
    STATUSES_FAILED, get_next_status
from src.localisation.localisation import Localisation
from .apk_sender import ApkSender
from .status_observer import OrderStatusObserver
from .messages_deleter import MessagesDeleter
from .screenshot_maker import make_screen_example
from .temporary_info import add_media_group_token, put_choose_id_message, get_choose_id_message, TemporaryInfo

os.makedirs(config.TMP_DIR, exist_ok=True)

session = AiohttpSession(
    api=TelegramAPIServer.from_base(f'http://{config.TELEGRAM_HOST}:8081')
)
bot = Bot(config.TOKEN, default=DefaultBotProperties(parse_mode="HTML"), session=session)
dp = Dispatcher()

orders = OrdersCRUD(engine)
workers = WorkersCRUD(engine)
user_build_stats_crud = UserBuildStatsCRUD(engine)

status_observer: Optional[OrderStatusObserver] = None
apk_sender: Optional[OrderStatusObserver] = None
error_logs_observer: Optional[ErrorLogsObserver] = None

password_hasher = PasswordHasher()


async def start():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    global status_observer, apk_sender, error_logs_observer
    status_observer = OrderStatusObserver()
    apk_sender = ApkSender()
    error_logs_observer = ErrorLogsObserver()
    MessagesDeleter.deleter = MessagesDeleter()
    dp.startup.register(on_startup)
    await dp.start_polling(bot)
    await MessagesDeleter.deleter.delete_all_messages()


async def on_startup(*args, **kwargs):
    for lang in Localisation.get_supported_languages():
        await bot.set_my_commands(
            [
                types.bot_command.BotCommand(command='/help', description=Localisation.get_message_text_by_language('help-desc', lang)),
                types.bot_command.BotCommand(command='/build', description=Localisation.get_message_text_by_language('build-desc', lang)),
                types.bot_command.BotCommand(command='/status', description=Localisation.get_message_text_by_language('status-desc', lang)),
                types.bot_command.BotCommand(command='/cancel', description=Localisation.get_message_text_by_language('cancel-desc', lang)),
            ],
            language_code=lang)
    if config.SKIP_UPDATES:
        await bot.delete_webhook(True)
    asyncio.create_task(status_observer.run(bot))
    asyncio.create_task(apk_sender.run(bot))
    asyncio.create_task(error_logs_observer.run(send_error))
    asyncio.create_task(MessagesDeleter.deleter.run(bot))


def log_exceptions(fun: Callable):
    @wraps(fun)
    async def wrapper(message: Union[types.Message, types.CallbackQuery], *args):
        try:
            return await fun(message, *args)
        except Exception as e:
            user_id = message.from_user.id
            order = orders.get_user_order(user_id)

            exception_text = traceback.format_exc()
            exception_report = (f"Exception occured in funcion '{fun.__name__}'.\n" +
                                f"User: {utils.mask_user_id(user_id)}\n" +
                                f"Order status: {order.status if order is not None else 'None'}\n"
                                f"{exception_text}")
            if config.ADMIN_CHAT_ID != 0:
                await send_error(exception_report)
    return wrapper


async def send_error(error_text: str):
    try:
        full_text = "Error log:\n\n" + error_text
        logging.error(error_text)
        escaped_text = formatting.Text(full_text)
        await bot.send_message(config.ADMIN_CHAT_ID, **escaped_text.as_kwargs())
    except TelegramBadRequest as e2:
        if "message is too long" in e2.message or "text is too long" in e2.message:  # Try to send logs as a document.
            await bot.send_document(config.ADMIN_CHAT_ID,
                                    types.BufferedInputFile(file=error_text.encode(), filename="Error log.txt")
                                    )
        else:
            traceback.print_exc()
    except Exception:
        traceback.print_exc()


def auto_delete_messages(fun: Callable):
    @wraps(fun)
    async def wrapper(message: Union[types.Message, types.CallbackQuery], *args):
        if isinstance(message, types.Message):
            MessagesDeleter.deleter.add_message(message)
        elif isinstance(message, types.CallbackQuery):
            MessagesDeleter.deleter.add_message(message.message)
        else:
            raise Exception(f'auto_delete_messages attached to an invalid function. Invalid argument type {type(message)}')
        response_message = await fun(message, *args)
        if response_message:
            MessagesDeleter.deleter.add_message(response_message)
    return wrapper


def on_order_status(
        queue: OrdersCRUD,
        statuses: List[OrderStatus],
        message: Union[types.Message, types.CallbackQuery]
):
    """Filter function for handling only orders with status matching any status in `statuses`."""

    user_id = message.from_user.id
    if queue.order_for_user_not_exists(user_id):
        return False
    order = queue.get_user_order(user_id)
    return order.status in statuses


def on_order_not_exists(
        queue: OrdersCRUD,
        message: Union[types.Message, types.CallbackQuery]
):
    """Filter function for handling only messages if the user order not exists."""

    user_id = message.from_user.id
    return queue.order_for_user_not_exists(user_id)


def validate_update_build_request(message: types.Message) -> bool:
    file_name = message.document.file_name
    return (file_name.startswith("update-")
            and file_name.endswith(".json")
            and message.document.file_size < config.FILE_SIZE_LIMIT)


async def send_cancelled_message(message: Union[types.Message, types.CallbackQuery]) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(
            text=localisation.get_message_text("clear-bot"),
            callback_data='clear_bot'
        ),
    ]])
    actual_message = message if isinstance(message, types.Message) else message.message
    return await actual_message.answer(localisation.get_message_text("canceled"), reply_markup=markup)


@dp.message(Command(commands=['start']))
@auto_delete_messages
async def start_command(message: types.Message) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    return await message.answer(localisation.get_message_text("welcome"))


@dp.message(Command(commands=['help']))
@log_exceptions
@auto_delete_messages
async def get_help(message: types.Message) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    return await message.answer(localisation.get_message_text("help"))


@dp.message(Command(commands=['status']))
@log_exceptions
@auto_delete_messages
async def get_order_status(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)
    if orders.order_for_user_not_exists(user_id):
        return await message.answer(localisation.get_message_text("no-orders-yet"))
    order = orders.get_user_order(user_id)

    if order.status in STATUSES_CONFIGURING:
        return await message.answer(localisation.get_message_text("status-configuring"))
    elif order.status == OrderStatus.queued:
        queue_order_count = orders.get_order_queue_position(order)
        return await message.answer(localisation.get_message_text("status-queued").format(queue_order_count))
    elif order.status in STATUSES_BUILDING:
        return await message.answer(localisation.get_message_text("status-building"))
    elif order.status in STATUSES_FAILED:
        return await message.answer(localisation.get_message_text("status-completed"))
    else:
        return await message.answer(localisation.get_message_text("status-unknown"))


@dp.message(Command(commands=['status_debug']))
@log_exceptions
@auto_delete_messages
async def get_order_status(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)
    if orders.order_for_user_not_exists(user_id):
        return await message.answer(localisation.get_message_text("no-orders-yet"))
    order = orders.get_user_order(user_id)
    return await message.answer(f'{order.status}')


@dp.message(Command(commands=['cancel']))
@log_exceptions
@auto_delete_messages
async def cancel_order(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)
    if orders.order_for_user_not_exists(user_id):
        return await message.answer(localisation.get_message_text("no-orders-yet"))
    order = orders.get_user_order(user_id)
    if order.status in STATUSES_BUILDING:
        return await message.answer(localisation.get_message_text("cannot-cancel"))
    orders.remove_order(order.id)
    result = await send_cancelled_message(message)
    await MessagesDeleter.deleter.delete_all_messages(message.chat.id)
    return result


@dp.message(Command(commands=['build']))
@log_exceptions
@auto_delete_messages
async def create_order(message: types.Message, lang: str = None) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message, lang)
    if not await check_user_build_stats_and_send_warning_if_need(user_id, localisation):
        return None
    remove_previous_order_if_failed(user_id)
    if orders.order_for_user_not_exists(user_id):
        orders.create_order(user_id)
        await MessagesDeleter.deleter.delete_all_messages(message.chat.id)
        inline_keyboard = [[
            types.InlineKeyboardButton(
                text="Calculator",
                callback_data='screen_calculator'
            ),
            types.InlineKeyboardButton(
                text="Loading",
                callback_data='screen_loading'
            ),
            types.InlineKeyboardButton(
                text="Note",
                callback_data='screen_note'
            )
        ]]
        text = localisation.get_message_text("ask-for-masked-passcode-screen")
        markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        screens_examples = [
            types.InputMediaPhoto(media=types.FSInputFile("resources/calculator_example.png", filename="")),
            types.InputMediaPhoto(media=types.FSInputFile("resources/loading_example.png", filename="")),
            types.InputMediaPhoto(media=types.FSInputFile("resources/note_example.png", filename="")),
        ]
        sent_messages = await bot.send_media_group(user_id, screens_examples)
        for msg in sent_messages:
            MessagesDeleter.deleter.add_message(msg)
        return await message.answer(text, reply_markup=markup)
    else:
        order = orders.get_user_order(user_id)
        if order.status in STATUSES_BUILDING:
            return await message.answer(localisation.get_message_text("cannot-create"))
        return await message.answer(localisation.get_message_text("suggest-cancel"))


async def check_user_build_stats_and_send_warning_if_need(user_id: int, localisation: Localisation) -> bool:
    user_id_hash = password_hasher.hash(str(user_id), salt=config.USER_ID_HASH_SALT.encode())
    stats = user_build_stats_crud.get_user_build_stats(user_id_hash)
    if stats is not None:
        successful_build_count = stats.successful_build_count
        failed_build_count = max(stats.failed_build_count - config.FAILED_BUILD_COUNT_ALLOWED, 0)
        full_build_count = max(successful_build_count + failed_build_count, 0)
        wait_interval_index = min(full_build_count, len(config.FLOOD_WAIT_INTERVALS_SEC) - 1)
        wait_interval = config.FLOOD_WAIT_INTERVALS_SEC[wait_interval_index]
        next_build_time = (stats.last_build_date + timedelta(seconds=wait_interval)).astimezone(pytz.utc)
        now = datetime.now().astimezone(pytz.utc)
        if next_build_time > now:
            next_build_time_str = next_build_time.strftime("%Y-%m-%d %H:%M:%S %Z")
            text = localisation.get_message_text("flood-wait").format(next_build_time_str)
            message = await bot.send_message(user_id, text)
            MessagesDeleter.deleter.add_message(message)
            return False
    return True


def remove_previous_order_if_failed(user_id: int):
    previous_order = orders.get_user_order(user_id)
    if previous_order is not None and previous_order.status in STATUSES_FAILED:
        orders.remove_order(previous_order.id)


@dp.message(
    F.document,
    validate_update_build_request
)
@log_exceptions
@auto_delete_messages
async def create_order_for_app_update_with_file(message: types.Message) -> types.Message:
    # If the validation fails by validate_update_build_request, the message will be handled by the fallback_documents.
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)

    if not await check_user_build_stats_and_send_warning_if_need(user_id, localisation):
        return None

    file = await bot.get_file(message.document.file_id)
    with open(file.file_path, 'r') as f:
        order_str = f.read()

    order_json = json.loads(order_str)
    order = Order.create_order_from_dict(order_json)

    remove_previous_order_if_failed(user_id)
    if orders.order_for_user_exists(user_id):
        message_prefix = f"#update-request-failed-{order.update_tag}\n\n"
        order = orders.get_user_order(user_id)
        if order.status in STATUSES_BUILDING:
            return await message.answer(message_prefix + localisation.get_message_text("cannot-create"))
        return await message.answer(message_prefix + localisation.get_message_text("suggest-cancel"))

    order.app_version_code += 1
    orders.insert_configured_order(user_id, order)
    order = orders.get_user_order(user_id)
    queue_order_count = orders.get_order_queue_position(order)
    return await message.answer(localisation.get_message_text("queued").format(queue_order_count))


@dp.message(
    Command(commands=['add_worker']),
    F.chat.func(lambda chat: chat.id == config.ADMIN_CHAT_ID)
)
@log_exceptions
@auto_delete_messages
async def add_worker_command(message: types.Message) -> types.Message:
    command_args = message.text.split()[1:]
    if len(command_args) == 1:
        name = command_args[0]
        ip = None
    elif len(command_args) == 2:
        name = command_args[0]
        ip = command_args[1]
    else:
        return await message.answer("Invalid usage")

    try:
        worker_id = workers.create_worker(name, ip)
    except:
        return await message.answer("Database error")

    jwt_payload = {"sub": worker_id}
    token = jwt.encode(payload=jwt_payload, key=config.JWT_SECRET_KEY)
    return await message.answer(token)


@dp.message(
    Command(commands=['del_worker']),
    F.chat.func(lambda chat: chat.id == config.ADMIN_CHAT_ID)
)
@log_exceptions
@auto_delete_messages
async def delete_worker_command(message: types.Message) -> types.Message:
    command_args = message.text.split()[1:]
    if len(command_args) != 1:
        return await message.answer("Invalid usage")

    worker_name = command_args[0]
    worker = workers.get_worker_by_name(worker_name)
    if not worker:
        return await message.answer("Not found")

    workers.remove_worker(worker.id)
    return await message.answer("Removed")


@dp.message(
    Command(commands=['reset_flood_wait']),
    F.chat.func(lambda chat: chat.id == config.ADMIN_CHAT_ID)
)
@log_exceptions
@auto_delete_messages
async def add_worker_command(message: types.Message) -> types.Message:
    command_args = message.text.split()[1:]
    if len(command_args) == 1:
        user_id = command_args[0]
    else:
        return await message.answer("Invalid usage")

    user_id_hash = password_hasher.hash(str(user_id), salt=config.USER_ID_HASH_SALT.encode())
    if user_build_stats_crud.get_user_build_stats(user_id_hash) is None:
        return await message.answer("User build stats not exist")

    user_build_stats_crud.remove_user_build_stats(user_id_hash)
    return await message.answer("User build stats removed")


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.app_masked_passcode_screen])
)
@log_exceptions
@auto_delete_messages
async def customize_masked_passcode_screen(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    order = orders.get_user_order(user_id)
    localisation = TemporaryInfo.get_localisation(call)

    if call.data is None or not call.data.startswith("screen_"):
        raise Exception("Invalid screen data")

    masked_screen_name = call.data.replace("screen_", "")
    OrderGenerator(order).generate_order_values(masked_screen_name)
    orders.update_order(order)
    orders.update_order_status(order.id, get_next_status(order.status))

    inline_keyboard = [[
        types.InlineKeyboardButton(
            text=localisation.get_message_text("start-build"),
            callback_data="generated_confirm"
        ),
        types.InlineKeyboardButton(
            text=localisation.get_message_text("customize-settings"),
            callback_data="generated_customize"
        )
    ]]
    markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    localized_permission_list = [localisation.get_message_text(f"permission-{permission}")
                                 for permission in order.permissions.split(",")
                                 if permission != ""]
    response = await bot.send_photo(
        order.user_id,
        photo=types.BufferedInputFile(file=make_screen_example(order.app_icon, order.app_name), filename=''),
        caption=localisation.get_message_text("request-confirmation").format(
            order.app_name, order.app_id, order.app_masked_passcode_screen, order.app_version_name,
            order.app_version_code, order.app_notification_text, ", ".join(localized_permission_list)
        ),
        reply_markup=markup,
    )

    await call.message.edit_reply_markup()
    await call.answer()

    return response


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.generated])
)
@log_exceptions
@auto_delete_messages
async def confirm_order(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)
    order = orders.get_user_order(user_id)

    await call.message.edit_reply_markup()
    await call.answer()
    if call.data == 'generated_confirm':
        orders.update_order_status(order.id, get_next_status(order.status, "confirm"))
        queue_order_count = orders.get_order_queue_position(order)
        return await call.message.answer(localisation.get_message_text("queued").format(queue_order_count))
    elif call.data == 'generated_customize':
        orders.update_order_status(order.id, get_next_status(order.status, "customize"))
        return await call.message.answer(localisation.get_message_text("ask-for-app-name"))


@dp.message(
    F.text,
    partial(on_order_status, orders, [OrderStatus.app_name])
)
@log_exceptions
@auto_delete_messages
async def customize_appname(message: types.Message, lang:str = None) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message, lang)
    order = orders.get_user_order(user_id)
    order.app_name = message.text
    order.app_id = ''
    order.status = get_next_status(order.status)
    orders.update_order(order)

    is_problematic_name = len(message.text) > config.NAME_LENGTH_LIMIT

    suggestions = []
    buttons = []
    order_generator = OrderGenerator(order)
    while len(set(suggestions)) < 3:
        suggestion = order_generator.generate_app_id()
        if suggestion not in suggestions:
            suggestions.append(suggestion)
            button = types.InlineKeyboardButton(
                text=suggestion,
                callback_data=suggestion
            )
            buttons.append([button])
    custom = types.InlineKeyboardButton(
        text=localisation.get_message_text("custom-app-id"),
        callback_data='custom')
    buttons.append([custom])
    markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)

    response = await bot.send_message(
        order.user_id,
        "\n".join([
            localisation.get_message_text("app-name-is").format(order.app_name, order.app_id),
            localisation.get_message_text("app-id-about"),
            localisation.get_message_text("ask-app-id")
        ]),
        reply_markup=markup,
    )
    put_choose_id_message(user_id, response)
    return response


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.app_id])
)
@log_exceptions
@auto_delete_messages
async def confirm_app_id(call: types.CallbackQuery, lang:str = None) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call, lang)
    order = orders.get_user_order(user_id)
    if call.data != 'custom':
        order.app_id = call.data
        await call.message.edit_reply_markup()
        await call.answer()
        response = await call.message.answer(
            '\n'.join([
                localisation.get_message_text("app-id-is").format(order.app_id),
                localisation.get_message_text("ask-icon"),
            ])
        )
        order.status = get_next_status(order.status)
    else:
        put_choose_id_message(user_id, None)
        await call.message.edit_reply_markup()
        await call.answer()
        response = await call.message.answer(localisation.get_message_text("ask-custom-app-id").format(config.APP_ID_EXAMPLE))
    orders.update_order(order)
    return response


@dp.message(
    F.text,
    partial(on_order_status, orders, [OrderStatus.app_id])
)
@log_exceptions
@auto_delete_messages
async def customize_app_id(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)
    order = orders.get_user_order(user_id)

    app_id_pattern = re.compile(r'^([A-Za-z]{1}[A-Za-z\d_]*\.)+[A-Za-z][A-Za-z\d_]*$')
    if not app_id_pattern.fullmatch(message.text):
        return await message.answer(
            localisation.get_message_text("invalid-app-id").format(config.APP_ID_DOCS_URL)
        )
    app_id = message.text.lower()
    order.app_id = app_id
    order.status = get_next_status(order.status)
    response = await message.answer(
        "\n".join([
            localisation.get_message_text("app-id-is").format(order.app_id),
            localisation.get_message_text("ask-icon")
        ])
    )
    orders.update_order(order)
    previous_message = get_choose_id_message(user_id)
    if previous_message is not None:
        await previous_message.edit_reply_markup()
    return response


@dp.message(
    F.document | F.photo,
    partial(on_order_status, orders, [OrderStatus.app_icon])
)
@log_exceptions
@auto_delete_messages
async def customize_icon(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)
    order = orders.get_user_order(user_id)

    if message.media_group_id is not None: # Grouped photos are not allowed.
        if add_media_group_token((message.chat.id, message.media_group_id)): # Answer only the first media in group.
            return await message.answer(localisation.get_message_text("grouped-images-are-not-allowed"))
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
        return await message.answer(localisation.get_message_text("file-too-big").format(config.FILE_SIZE_LIMIT // 1024 ** 2))
    icon_file = await bot.get_file(media.file_id)
    with open(icon_file.file_path, 'rb') as f:
        icon_bytes = f.read()
    try:
        Image.open(io.BytesIO(icon_bytes))
    except UnidentifiedImageError:
        return await message.answer(localisation.get_message_text("file-is-not-image"))
    order.app_icon = icon_bytes
    order.app_notification_icon = icon_bytes
    orders.update_order(order)
    orders.update_appicon(order.id, icon_bytes)
    orders.update_order_status(order.id, get_next_status(order.status))
    return await message.answer(localisation.get_message_text("ask-for-version-name"))


@dp.message(
    partial(on_order_status, orders, [OrderStatus.app_icon, OrderStatus.app_notification_icon])
)
@log_exceptions
@auto_delete_messages
async def handle_invalid_icon(message: types.Message) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    if message.audio or message.video: # If message contains something like a file
        return await message.answer(localisation.get_message_text("file-is-not-image"))
    else: # If message doesn't look like a file
        return await message.answer(localisation.get_message_text("ask-icon"))


@dp.message(
    partial(on_order_status, orders, [OrderStatus.app_version_name])
)
@log_exceptions
@auto_delete_messages
async def customize_version_name(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    order = orders.get_user_order(user_id)
    localisation = TemporaryInfo.get_localisation(message)

    order.app_version_name = message.text
    orders.update_order(order)
    orders.update_order_status(order.id, get_next_status(order.status))
    return await message.answer(localisation.get_message_text("ask-for-version-code"))


@dp.message(
    partial(on_order_status, orders, [OrderStatus.app_version_code])
)
@log_exceptions
@auto_delete_messages
async def customize_version_code(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    order = orders.get_user_order(user_id)
    localisation = TemporaryInfo.get_localisation(message)

    try:
        order.app_version_code = int(message.text)
    except ValueError:
        return await message.answer(localisation.get_message_text("version-code-must-be-integer"))
    orders.update_order(order)
    orders.update_order_status(order.id, get_next_status(order.status))

    buttons_info = [
        ("🟥", "red"),
        ("🟧", "orange"),
        ("🟨", "yellow"),
        ("🟩", "green"),
        ("🟦", "blue"),
        ("🟪", "purple"),
        ("🟫", "brown"),
        ("⬛️", "black"),
        ("⬜️", "white")
    ]

    inline_keyboard = []

    for row in range(0, 3):
        inline_keyboard.append([])
        for col in range(0, 3):
            text, color = buttons_info[row * 3 + col]
            inline_keyboard[row].append(types.InlineKeyboardButton(text=text, callback_data=f"color_{color}"))

    markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    return await message.answer(localisation.get_message_text("ask-for-notification-color"), reply_markup=markup)


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.app_notification_color])
)
@log_exceptions
@auto_delete_messages
async def customize_notification_color(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    order = orders.get_user_order(user_id)
    localisation = TemporaryInfo.get_localisation(call)

    if call.data == 'color_red':
        order.app_notification_color = 0xFF0000
    elif call.data == 'color_orange':
        order.app_notification_color = 0xFF8000
    elif call.data == 'color_yellow':
        order.app_notification_color = 0xFFFF00
    elif call.data == 'color_green':
        order.app_notification_color = 0x00FF00
    elif call.data == 'color_blue':
        order.app_notification_color = 0x0000FF
    elif call.data == 'color_purple':
        order.app_notification_color = 0x8B00FF
    elif call.data == 'color_brown':
        order.app_notification_color = 0x964B00
    elif call.data == 'color_black':
        order.app_notification_color = 0x000000
    elif call.data == 'color_white':
        order.app_notification_color = 0xFFFFFF

    await call.answer()
    await call.message.edit_reply_markup()
    orders.update_order(order)
    orders.update_order_status(order.id, get_next_status(order.status))
    return await call.message.answer(localisation.get_message_text("ask-for-notification-text"))


@dp.message(
    partial(on_order_status, orders, [OrderStatus.app_notification_text])
)
@log_exceptions
@auto_delete_messages
async def customize_notification_text(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    order = orders.get_user_order(user_id)
    localisation = TemporaryInfo.get_localisation(message)

    order.app_notification_text = message.text
    orders.update_order(order)
    orders.update_order_status(order.id, get_next_status(order.status))

    markup = types.InlineKeyboardMarkup(inline_keyboard=create_permissions_keyboard(order, localisation))

    return await message.answer(localisation.get_message_text("ask-for-permissions"), reply_markup=markup)


def create_permissions_keyboard(order: Order, localisation: Localisation) -> list[list[types.InlineKeyboardButton]]:
    permissions = [p.value for p in AndroidAppPermission]
    odd_permission_count = len(permissions) % 2 == 1
    if odd_permission_count:
        permission_row_count = len(permissions) // 2 + 1
    else:
        permission_row_count = len(permissions) // 2
    order_permissions = order.permissions.split(",")

    inline_keyboard = []

    for row in range(0, permission_row_count):
        inline_keyboard.append([])
        col_count = 1 if (odd_permission_count and row == 0) else 2  # Only one button on the first row.
        for col in range(0, col_count):
            permission_index = row * 2 + col
            if odd_permission_count and row != 0:
                permission_index -= 1
            permission = permissions[permission_index]
            permission_localisation = localisation.get_message_text(f"permission-{permission}")
            if permission in order_permissions:
                text = f"✅ {permission_localisation}"
            else:
                text = f"❌ {permission_localisation}"
            inline_keyboard[row].append(types.InlineKeyboardButton(text=text, callback_data=f"permission_{permission}"))

    inline_keyboard.append([
        types.InlineKeyboardButton(text=localisation.get_message_text("check-all"), callback_data="permission_check_all"),
        types.InlineKeyboardButton(text=localisation.get_message_text("clear-all"), callback_data="permission_clear_all")
    ])

    inline_keyboard.append([
        types.InlineKeyboardButton(text=localisation.get_message_text("continue"), callback_data="permission_continue")
    ])
    return inline_keyboard


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.app_permissions])
)
@auto_delete_messages
async def customize_permissions(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    order = orders.get_user_order(user_id)
    localisation = TemporaryInfo.get_localisation(call)

    order_permissions: list[str] = order.permissions.split(",")

    if call.data == "permission_continue":
        orders.update_order_status(order.id, get_next_status(order.status))
        await call.answer()
        await call.message.edit_reply_markup()
        return None
    elif call.data == "permission_clear_all":
        order_permissions = []
    elif call.data == "permission_check_all":
        order_permissions = [p.value for p in AndroidAppPermission]
    else:
        permission = call.data.replace("permission_", "")
        if permission not in order_permissions:
            order_permissions.append(permission)
        else:
            order_permissions.remove(permission)

    order.permissions = ",".join(order_permissions)
    orders.update_order(order)
    markup = types.InlineKeyboardMarkup(inline_keyboard=create_permissions_keyboard(order, localisation))
    await call.answer()
    await call.message.edit_reply_markup(reply_markup=markup)
    return None


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.confirmation])
)
@log_exceptions
@auto_delete_messages
async def confirm_order(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)
    order = orders.get_user_order(user_id)

    if call.data == 'yes':
        orders.update_order_status(order.id, get_next_status(order.status, "yes"))
        await call.message.edit_reply_markup()
        await call.answer()
        queue_order_count = orders.get_order_queue_position(order)
        return await call.message.answer(localisation.get_message_text("queued").format(queue_order_count))
    elif call.data == 'no':
        orders.remove_order(order.id)
        await call.message.edit_reply_markup()
        await call.answer()
        return await send_cancelled_message(call)


@dp.message(
    partial(on_order_status, orders, [OrderStatus.confirmation])
)
@log_exceptions
@auto_delete_messages
async def handle_confirmation_message(message: types.Message) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    return await message.answer(localisation.get_message_text("request-confirmation-again"))


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.failed_notified])
)
@log_exceptions
@auto_delete_messages
async def process_failure(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)
    order = orders.get_user_order(user_id)

    if call.data == 'retry_build':
        await call.message.edit_reply_markup()
        await call.answer()
        queue_order_count = orders.get_order_queue_position(order)
        response = await call.message.answer(localisation.get_message_text("queued").format(queue_order_count))
        orders.update_order_status(order.id, get_next_status(order.status, "retry"))
    else:
        await call.message.edit_reply_markup()
        await call.answer()
        response = await send_cancelled_message(call)
        orders.remove_order(order.id)
    return response


@dp.message(
    partial(on_order_status, orders, [OrderStatus.queued])
)
@log_exceptions
@auto_delete_messages
async def ask_to_wait_for_build_queued(message: types.Message) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    return await message.answer(localisation.get_message_text("awaiting-build"))


@dp.message(
    partial(on_order_status, orders, [OrderStatus.building])
)
@log_exceptions
@auto_delete_messages
async def ask_to_wait_for_build_building(message: types.Message) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    return await message.answer(localisation.get_message_text("is-building"))


@dp.callback_query(
    F.data == 'clear_bot'
)
@log_exceptions
@auto_delete_messages
async def process_failure(call: types.CallbackQuery) -> types.Message:
    message = call.message
    await asyncio.gather(MessagesDeleter.deleter.delete_all_messages(message.chat.id),
                         message.bot.delete_message(message.chat.id, message.message_id))
    return None


@dp.message(F.photo | F.audio | F.document | F.sticker | F.story | F.video | F.voice | F.contact | F.poll | F.location)
@log_exceptions
@auto_delete_messages
async def fallback(message: types.Message) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    return await message.answer(localisation.get_message_text("media-files-are-not-allowed"))


@dp.message(F.text)
@log_exceptions
@auto_delete_messages
async def fallback(message: types.Message) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    return await message.answer(localisation.get_message_text("unknown-text-response"))


if __name__ == "__main__":
    asyncio.run(start())