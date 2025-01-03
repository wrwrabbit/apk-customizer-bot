import asyncio
import io
import json
import logging
import os
import re
import sys
import traceback
from datetime import datetime

from functools import wraps, partial

import pytz
from PIL.Image import Resampling
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
from bot.primary_color import PrimaryColor
from bot.stats import increase_start_count, increase_configuration_start_count, increase_update_start_count, \
    increase_cancel_count, period_stats, uptime_stats
from bot.stats_sender import StatsSender
from crud.user_build_stats_crud import UserBuildStatsCRUD
from db import engine
from models import Order
from crud.orders_crud import OrdersCRUD
from schemas.android_app_permission import AndroidAppPermission
from crud.workers_crud import WorkersCRUD
from schemas.order_status import OrderStatus, STATUSES_BUILDING, STATUSES_CONFIGURING, \
    get_next_status, STATUSES_FINISHED, STATUSES_GETTING_SOURCES
from src.localisation.localisation import Localisation
from src.localisation.native_lang_translations import translations
from .order_status_observer import OrderStatusObserver
from .messages_deleter import MessagesDeleter
from .temporary_info import add_media_group_token, TemporaryInfo, \
    add_message_with_buttons, get_messages_with_buttons, clear_messages_with_buttons_list

os.makedirs(config.TMP_DIR, exist_ok=True)

session = AiohttpSession(
    api=TelegramAPIServer.from_base(f'http://{config.TELEGRAM_HOST}:8081')
)
bot = Bot(
    config.TOKEN,
    default=DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True),
    session=session
)
dp = Dispatcher()

orders = OrdersCRUD(engine)
workers = WorkersCRUD(engine)
user_build_stats_crud = UserBuildStatsCRUD(engine)

status_observer: Optional[OrderStatusObserver] = None
error_logs_observer: Optional[ErrorLogsObserver] = None
stats_sender: Optional[StatsSender] = None

password_hasher = PasswordHasher()
graceful_shutdown_in_progress = False


async def start():
    logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO, stream=sys.stdout)
    global status_observer, error_logs_observer, stats_sender
    status_observer = OrderStatusObserver(bot, orders)
    error_logs_observer = ErrorLogsObserver()
    stats_sender = StatsSender()
    MessagesDeleter.deleter = MessagesDeleter(bot, orders)
    MessagesDeleter.deleter.add_on_all_messages_deleted_listener(on_all_user_messages_deleted)
    dp.startup.register(on_startup)
    await dp.start_polling(bot)
    await MessagesDeleter.deleter.delete_all_messages()


def on_all_user_messages_deleted(user_id: int):
    clear_messages_with_buttons_list(user_id)

    order = orders.get_user_order(user_id)
    if order is not None:
        need_remove_order = order.status not in STATUSES_BUILDING and order.status != OrderStatus.queued
        if need_remove_order:
            orders.remove_order(order.id)
    if graceful_shutdown_in_progress and orders.get_orders_count() == 0:
        gracefully_stop_bot()


def gracefully_stop_bot():
    async def async_stop_bot():
        await bot.send_message(config.ADMIN_CHAT_ID, 'Bot stopped')
        sys.exit(0)

    event_loop = asyncio.get_event_loop()
    asyncio.ensure_future(async_stop_bot(), loop=event_loop)


async def on_startup(*args, **kwargs):
    for lang in Localisation.get_supported_languages():
        await bot.set_my_commands(
            [
                types.bot_command.BotCommand(command='/start', description=Localisation.get_message_text_by_language('start-desc', lang)),
                types.bot_command.BotCommand(command='/status', description=Localisation.get_message_text_by_language('status-desc', lang)),
                types.bot_command.BotCommand(command='/cancel', description=Localisation.get_message_text_by_language('cancel-desc', lang)),
            ],
            language_code=lang)
        if config.SET_BOT_NAME_AND_DESCRIPTION:
            await bot.set_my_name(Localisation.get_message_text_by_language('bot-name', lang), language_code=lang)
            await bot.set_my_description(Localisation.get_message_text_by_language('bot-description', lang), language_code=lang)
            await bot.set_my_short_description(Localisation.get_message_text_by_language('bot-short-description', lang), language_code=lang)
    if config.SKIP_UPDATES:
        await bot.delete_webhook(True)
    asyncio.create_task(status_observer.observe())
    asyncio.create_task(error_logs_observer.run(send_error))
    asyncio.create_task(stats_sender.run(send_stats))
    asyncio.create_task(MessagesDeleter.deleter.run())


def log_exceptions(fun: Callable):
    @wraps(fun)
    async def wrapper(message: Union[types.Message, types.CallbackQuery], *args):
        try:
            return await fun(message, *args)
        except Exception as e:
            user_id = message.from_user.id
            order = orders.get_user_order(user_id)

            exception_text = traceback.format_exc()
            exception_report = (f"Exception occurred in function '{fun.__name__}'.\n" +
                                f"User: {utils.mask_user_id(user_id)}\n" +
                                f"Order status: {order.status if order is not None else 'None'}\n"
                                f"{exception_text}")
            if config.ERROR_LOGS_CHAT_ID != 0:
                await send_error(exception_report)
    return wrapper


async def send_error(error_text: str):
    try:
        full_text = "Error log:\n\n" + error_text
        logging.error(error_text)
        escaped_text = formatting.Text(full_text)
        await bot.send_message(config.ERROR_LOGS_CHAT_ID, **escaped_text.as_kwargs())
    except TelegramBadRequest as e2:
        if "message is too long" in e2.message or "text is too long" in e2.message:  # Try to send logs as a document.
            await bot.send_document(config.ERROR_LOGS_CHAT_ID,
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
        response_message: types.Message = await fun(message, *args)
        if response_message:
            MessagesDeleter.deleter.add_message(response_message)
            if response_message.reply_markup:
                user_id = message.from_user.id
                add_message_with_buttons(user_id, response_message)
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
    if not config.UPDATES_ALLOWED:
        return False
    file_name = message.document.file_name
    return (file_name.startswith("update-")
            and file_name.endswith(".json")
            and message.document.file_size < config.FILE_SIZE_LIMIT)


async def send_cancelled_message(message: Union[types.Message, types.CallbackQuery]) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    clear_bot_text = localisation.get_message_text("clear-bot")
    start_configuration_again_text = localisation.get_message_text("start-configuration-again")
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text=clear_bot_text,
                callback_data='clear_bot'
            )
        ],
        [
            types.InlineKeyboardButton(
                text=start_configuration_again_text,
                callback_data='start_configuration'
            ),
        ]
    ])
    actual_message = message if isinstance(message, types.Message) else message.message
    text = localisation.get_message_text("canceled").format(start_configuration_again_text, clear_bot_text)
    return await actual_message.answer(text, reply_markup=markup)


async def send_stats(chat_id: int) -> types.Message:
    count_of_users_with_messages = MessagesDeleter.deleter.get_count_of_users_with_messages()
    count_of_orders = orders.get_orders_count()
    count_of_orders_configuring = orders.get_count_of_orders_by_status(STATUSES_CONFIGURING)
    count_of_orders_queue = orders.get_count_of_orders_by_status(OrderStatus.queued)
    count_of_orders_building = orders.get_count_of_orders_by_status(STATUSES_BUILDING + STATUSES_GETTING_SOURCES)
    count_of_orders_finished = orders.get_count_of_orders_by_status(STATUSES_FINISHED)
    current_stats_text = f"Number of users with messages: {count_of_users_with_messages}\n" + \
                         f"Number of users with orders: {count_of_orders}\n" + \
                         f"- Configuring: {count_of_orders_configuring}\n" + \
                         f"- Queue: {count_of_orders_queue}\n" + \
                         f"- Building: {count_of_orders_building}\n" + \
                         f"- Finished: {count_of_orders_finished}"
    period_stats_text = f"<b>Period Stats</b>:\n{period_stats.format()}"
    uptime_stats_text = f"<b>Uptime Stats</b>:\n{uptime_stats.format()}"
    text = "\n\n".join([current_stats_text, period_stats_text, uptime_stats_text])
    return await bot.send_message(chat_id, text)


async def clear_buttons_from_messages(user_id: int):
    messages = get_messages_with_buttons(user_id)
    for message in messages:
        try:
            await message.edit_reply_markup()
        except:
            pass
    clear_messages_with_buttons_list(user_id)


@dp.message(Command(commands=['start']))
@auto_delete_messages
async def start_command(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)
    if graceful_shutdown_in_progress:
        return await message.answer(localisation.get_message_text("bot-maintenance"))

    increase_start_count()
    remove_previous_order_if_finished(user_id)
    if orders.order_for_user_not_exists(user_id):
        await MessagesDeleter.deleter.delete_all_messages(message.chat.id)
        markup = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(
                text=localisation.get_message_text("start-configuration"),
                callback_data='start_configuration'
            ),
        ]])
        return await message.answer(localisation.get_message_text("welcome"), reply_markup=markup)
    else:
        order = orders.get_user_order(user_id)
        if order.status in STATUSES_BUILDING:
            return await message.answer(localisation.get_message_text("cannot-create"))
        return await message.answer(localisation.get_message_text("suggest-cancel"))


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
    elif order.status in STATUSES_GETTING_SOURCES:
        return await message.answer(localisation.get_message_text("status-getting-sources-code"))
    elif order.status in STATUSES_FINISHED:
        return await message.answer(localisation.get_message_text("status-finished"))
    else:
        return await message.answer(localisation.get_message_text("status-unknown"))


@dp.message(Command(commands=['status_debug']))
@log_exceptions
@auto_delete_messages
async def get_order_status_debug(message: types.Message) -> types.Message:
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
    increase_cancel_count()
    orders.remove_order(order.id)
    result = await send_cancelled_message(message)
    await MessagesDeleter.deleter.delete_all_messages(message.chat.id)
    return result


@dp.callback_query(
    partial(on_order_not_exists, orders),
    F.data == 'start_configuration'
)
@log_exceptions
@auto_delete_messages
async def create_order(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)
    await call.answer()
    await clear_buttons_from_messages(user_id)
    remove_previous_order_if_finished(user_id)

    if graceful_shutdown_in_progress:
        return await call.message.answer(localisation.get_message_text("bot-maintenance"))

    increase_configuration_start_count()
    priority = get_order_priority(user_id)
    orders.create_order(user_id, priority)
    return await status_observer.on_status_changed(orders.get_user_order(user_id), localisation)


def get_order_priority(user_id: int) -> int:
    user_id_hash = password_hasher.hash(str(user_id), salt=config.USER_ID_HASH_SALT.encode())
    stats = user_build_stats_crud.get_user_build_stats(user_id_hash)
    if stats is None:
        return 1
    successful_build_count = stats.successful_build_count
    failed_build_count = max(stats.failed_build_count - config.FAILED_BUILD_COUNT_ALLOWED, 0)
    full_build_count = max(successful_build_count + failed_build_count, 0)
    return 1 + full_build_count


def remove_previous_order_if_finished(user_id: int):
    previous_order = orders.get_user_order(user_id)
    if previous_order is not None:
        if previous_order.status in STATUSES_FINISHED:
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

    increase_update_start_count()

    file = await bot.get_file(message.document.file_id)
    with open(file.file_path, 'r') as f:
        order_str = f.read()

    order_json = json.loads(order_str)
    order = Order.create_order_from_dict(order_json)

    remove_previous_order_if_finished(user_id)
    if orders.order_for_user_exists(user_id):
        message_prefix = f"#update-request-failed-{order.update_tag}\n\n"
        order = orders.get_user_order(user_id)
        if order.status in STATUSES_BUILDING:
            return await message.answer(message_prefix + localisation.get_message_text("cannot-create"))
        return await message.answer(message_prefix + localisation.get_message_text("suggest-cancel"))

    order.app_version_code += 1
    order.priority = get_order_priority(user_id)
    orders.insert_configured_order(user_id, order)
    order = orders.get_user_order(user_id)
    return await status_observer.on_status_changed(order, localisation)


@dp.message(
    Command(commands=['add_worker']),
    F.chat.func(lambda chat: chat.id == config.ADMIN_CHAT_ID)
)
@log_exceptions
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


@dp.message(
    Command(commands=['get_config_var']),
    F.chat.func(lambda chat: chat.id == config.ADMIN_CHAT_ID)
)
@log_exceptions
async def get_config_var_command(message: types.Message) -> types.Message:
    command_args = message.text.split()[1:]
    if len(command_args) == 1:
        name = command_args[0]
    else:
        return await message.answer("Invalid usage")

    if not config.variable_exists(name):
        return await message.answer("There is no variable with this name")

    value = str(config.get_variable_by_name(name))
    return await message.answer(value)


@dp.message(
    Command(commands=['set_config_var']),
    F.chat.func(lambda chat: chat.id == config.ADMIN_CHAT_ID)
)
@log_exceptions
async def set_config_var_command(message: types.Message) -> types.Message:
    command_args = extract_command_args(message.text)
    if len(command_args) == 2:
        name = command_args[0]
        value = command_args[1]
    else:
        return await message.answer("Invalid usage")

    if not config.variable_exists(name):
        return await message.answer("There is no variable with this name")

    old_value = config.get_variable_by_name(name)
    if old_value is None or isinstance(old_value, str):
        value = value
    elif isinstance(old_value, int) and not isinstance(old_value, bool):
        value = int(value)
    elif isinstance(old_value, bool):
        value = value.lower() in ("true", "1", "t")
    else:
        return await message.answer("Unknown variable type")

    config.set_variable_by_name(name, value)
    return await message.answer("Success")


@dp.message(
    Command(commands=['get_translation']),
    F.chat.func(lambda chat: chat.id == config.ADMIN_CHAT_ID)
)
@log_exceptions
async def get_translation_command(message: types.Message) -> types.Message:
    command_args = message.text.split()[1:]
    if len(command_args) == 2:
        name = command_args[0]
        lang = command_args[1]
    else:
        return await message.answer("Invalid usage")

    if name not in translations:
        return await message.answer("There is no translation with this name")
    if lang not in translations[name]:
        return await message.answer("There is no translation with this lang")
    return await message.answer(translations[name][lang])


@dp.message(
    Command(commands=['set_translation']),
    F.chat.func(lambda chat: chat.id == config.ADMIN_CHAT_ID)
)
@log_exceptions
async def set_translation_command(message: types.Message) -> types.Message:
    command_args = extract_command_args(message.text)
    if len(command_args) == 3:
        name = command_args[0]
        lang = command_args[1]
        value = command_args[2]
    else:
        return await message.answer("Invalid usage")

    if name not in translations:
        return await message.answer("There is no translation with this name")
    if lang not in translations[name]:
        return await message.answer("There is no translation with this lang")
    translations[name][lang] = value
    return await message.answer("Success")


def extract_command_args(command: str) -> list[str]:
    raw_args = re.split(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''', command)[3::2]
    result = []
    for arg in raw_args:
        if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
            arg = arg[1:-1]
        result.append(arg)
    return result


@dp.message(
    Command(commands=['graceful_shutdown']),
    F.chat.func(lambda chat: chat.id == config.ADMIN_CHAT_ID)
)
@log_exceptions
async def graceful_shutdown_command(message: types.Message) -> types.Message:
    global graceful_shutdown_in_progress
    graceful_shutdown_in_progress = True
    await message.answer("Bot stop started")
    if orders.get_orders_count() == 0:
        gracefully_stop_bot()


@dp.message(
    Command(commands=['stats']),
    F.chat.func(lambda chat: chat.id == config.ADMIN_CHAT_ID)
)
@log_exceptions
async def stats_command(message: types.Message) -> types.Message:
    return await send_stats(message.from_user.id)


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.app_masked_passcode_screen])
)
@log_exceptions
@auto_delete_messages
async def customize_masked_passcode_screen(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)
    await call.answer()
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    if call.data is None or (not call.data.startswith("screen_") and call.data != "show_advanced_screens"):
        raise Exception("Invalid screen data")

    if call.data == "show_advanced_screens":
        orders.update_order_status(order, get_next_status(order.status, "show_advanced_screens"))
        return await status_observer.on_status_changed(order, localisation)

    masked_screen_name = call.data.replace("screen_", "")
    OrderGenerator(order, localisation).generate_order_values(masked_screen_name)
    orders.update_order(order)
    orders.update_order_status(order, get_next_status(order.status))

    return await status_observer.on_status_changed(order, localisation)


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.app_masked_passcode_screen_advanced])
)
@log_exceptions
@auto_delete_messages
async def customize_advanced_masked_passcode_screen(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    order = orders.get_user_order(user_id)
    await call.answer()
    await clear_buttons_from_messages(user_id)

    localisation = TemporaryInfo.get_localisation(call)

    if call.data is None or (not call.data.startswith("screen_") and call.data != "back"):
        raise Exception("Invalid screen data")

    if call.data == "back":
        orders.update_order_status(order, get_next_status(order.status, "back"))
        return await status_observer.on_status_changed(order, localisation)

    masked_screen_name = call.data.replace("screen_", "")
    OrderGenerator(order, localisation).generate_order_values(masked_screen_name)
    orders.update_order(order)
    orders.update_order_status(order, get_next_status(order.status))

    return await status_observer.on_status_changed(order, localisation)


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.generated, OrderStatus.confirmation])
)
@log_exceptions
@auto_delete_messages
async def confirm_order(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)
    await call.answer()
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    if call.data == 'generated_confirm':
        transition_name = "confirm"
        order.record_created = datetime.now().astimezone(pytz.utc)
    elif call.data == 'generated_customize_app_name_only':
        transition_name = "customize_app_name_only"
    elif call.data == 'generated_customize_app_icon_only':
        transition_name = "customize_app_icon_only"
    elif call.data == 'generated_customize':
        transition_name = "customize"
    else:
        return None
    order.status = get_next_status(order.status, transition_name)
    orders.update_order(order)
    return await status_observer.on_status_changed(order, localisation)


@dp.message(
    partial(on_order_status, orders, [OrderStatus.generated, OrderStatus.confirmation])
)
@log_exceptions
@auto_delete_messages
async def handle_confirmation_message(message: types.Message) -> types.Message:
    localisation = TemporaryInfo.get_localisation(message)
    return await message.answer(localisation.get_message_text("request-confirmation-again"))


@dp.callback_query(
    partial(on_order_status, orders, STATUSES_CONFIGURING),
    F.data == 'leave_current_value_and_continue'
)
@log_exceptions
@auto_delete_messages
async def confirm_order(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)
    await call.answer()
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    orders.update_order_status(order, get_next_status(order.status))
    return await status_observer.on_status_changed(order, localisation)


@dp.message(
    F.text,
    partial(on_order_status, orders, [OrderStatus.app_name, OrderStatus.app_name_only])
)
@log_exceptions
@auto_delete_messages
async def customize_app_name(message: types.Message, lang:str = None) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message, lang)
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    order.app_name = message.text
    if order.status == OrderStatus.app_name: # The next step is app id generation
        order.app_id = ''
    elif order.status == OrderStatus.app_name_only: # The next step is confirmation. Let's generate a new app id that matches the app name.
        order.app_id = OrderGenerator(order, localisation).random_app_id()
    order.status = get_next_status(order.status)
    orders.update_order(order)

    return await status_observer.on_status_changed(order, localisation)


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.app_id])
)
@log_exceptions
@auto_delete_messages
async def confirm_app_id(call: types.CallbackQuery, lang:str = None) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call, lang)
    await call.answer()
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    if call.data != 'custom_app_id':
        order.app_id = call.data
        order.status = get_next_status(order.status)
        orders.update_order(order)
        response = await status_observer.on_status_changed(order, localisation)
    else:
        response = await call.message.answer(localisation.get_message_text("ask-custom-app-id").format(config.APP_ID_EXAMPLE))
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
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    app_id_pattern = re.compile(r'^([A-Za-z]{1}[A-Za-z\d_]*\.)+[A-Za-z][A-Za-z\d_]*$')
    if not app_id_pattern.fullmatch(message.text):
        return await message.answer(
            localisation.get_message_text("invalid-app-id").format(config.APP_ID_DOCS_URL)
        )
    app_id = message.text.lower()
    order.app_id = app_id
    order.status = get_next_status(order.status)
    orders.update_order(order)
    response = await status_observer.on_status_changed(order, localisation)
    return response


@dp.message(
    F.document | F.photo,
    partial(on_order_status, orders, [OrderStatus.app_icon, OrderStatus.app_icon_only, OrderStatus.app_notification_icon])
)
@log_exceptions
@auto_delete_messages
async def customize_icon(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)

    if not validate_icon_message(message):
        return None

    media = message.document if message.document else message.photo[-1] # message.photo contains 3 PhotoSize items for handling different resolutions. The last item corresponds to the highest resolution

    if media.file_size > config.FILE_SIZE_LIMIT:
        return await message.answer(localisation.get_message_text("file-too-big").format(config.FILE_SIZE_LIMIT // 1024 ** 2))

    icon_bytes = await read_bot_file(media.file_id)
    icon_bytes = await validate_and_resize_icon(order, icon_bytes, localisation)
    if icon_bytes is None:
        return None

    if order.status == OrderStatus.app_notification_icon:
        order.app_notification_icon = icon_bytes
    else:
        order.app_icon = icon_bytes
    order.status = get_next_status(order.status)
    orders.update_order(order)
    return await status_observer.on_status_changed(order, localisation)


async def validate_icon_message(message: types.Message) -> bool:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)
    order = orders.get_user_order(user_id)

    error_message = None
    validated = True
    if message.media_group_id is not None:  # Grouped photos are not allowed.
        validated = False
        if add_media_group_token((message.chat.id, message.media_group_id)):  # Answer only the first media in group.
            error_message = await message.answer(localisation.get_message_text("grouped-images-are-not-allowed"))

    if message.document is None and order.status == OrderStatus.app_notification_icon:
        validated = False
        error_message = await message.answer(localisation.get_message_text("notification-icon-must-be-uncompressed"))

    if error_message:
        MessagesDeleter.deleter.add_message(error_message)

    return validated


async def read_bot_file(file_id: str) -> bytes:
    icon_file = await bot.get_file(file_id)
    with open(icon_file.file_path, 'rb') as f:
        icon_bytes = f.read()
    os.remove(icon_file.file_path)
    return icon_bytes


async def validate_and_resize_icon(order: Order, icon_bytes: bytes, localisation: Localisation) -> Optional[bytes]:
    error_message = None
    try:
        with Image.open(io.BytesIO(icon_bytes)) as image:
            has_transparency = utils.has_transparency(image)
            if order.status == OrderStatus.app_notification_icon and not has_transparency:
                temp_order = Order()
                OrderGenerator(temp_order, localisation).generate_order_values(order.app_masked_passcode_screen)
                error_message = await bot.send_document(
                    order.user_id,
                    document=types.BufferedInputFile(file=temp_order.app_notification_icon, filename='icon.png'),
                    caption=localisation.get_message_text("notification-icon-must-be-transparent")
                )
            else:
                cropped_image = utils.crop_center_square(image)
                if cropped_image.width > 384:
                    resized_image = cropped_image.resize((384, 384), Resampling.LANCZOS)
                else:
                    resized_image = cropped_image
                result_array = io.BytesIO()
                if not has_transparency:
                    resized_image.save(result_array, format='JPEG')
                else:
                    resized_image.save(result_array, format='PNG')
                result_bytes = result_array.getvalue()
                return result_bytes
    except UnidentifiedImageError:
        error_message = await bot.send_message(order.user_id, localisation.get_message_text("file-is-not-image"))

    if error_message:
        MessagesDeleter.deleter.add_message(error_message)
    return None


@dp.message(
    partial(on_order_status, orders, [OrderStatus.app_icon, OrderStatus.app_icon_only, OrderStatus.app_notification_icon])
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
    F.text,
    partial(on_order_status, orders, [OrderStatus.app_version_name])
)
@log_exceptions
@auto_delete_messages
async def customize_version_name(message: types.Message) -> types.Message:
    is_ascii_text = all(ord(c) < 128 for c in message.text)
    if not is_ascii_text:
        localisation = TemporaryInfo.get_localisation(message)
        return await message.answer(localisation.get_message_text("only-ascii-allowed"))
    user_id = message.from_user.id
    order = orders.get_user_order(user_id)
    await clear_buttons_from_messages(user_id)

    localisation = TemporaryInfo.get_localisation(message)
    order.app_version_name = message.text
    orders.update_order(order)
    orders.update_order_status(order, get_next_status(order.status))
    return await status_observer.on_status_changed(order, localisation)


@dp.message(
    F.text,
    partial(on_order_status, orders, [OrderStatus.app_version_code])
)
@log_exceptions
@auto_delete_messages
async def customize_version_code(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    try:
        version_code = int(message.text)
        if version_code > config.MAX_VERSION_CODE:
            raise ValueError()
        order.app_version_code = version_code
    except ValueError:
        text = localisation.get_message_text("version-code-must-be-integer").format(config.MAX_VERSION_CODE)
        return await message.answer(text)

    orders.update_order(order)
    orders.update_order_status(order, get_next_status(order.status))
    return await status_observer.on_status_changed(order, localisation)


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.app_notification_color])
)
@log_exceptions
@auto_delete_messages
async def customize_notification_color(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)
    await call.answer()
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    color_name = call.data.removeprefix("color_")
    order.app_notification_color = PrimaryColor.get_color_by_name(color_name).value

    orders.update_order(order)
    orders.update_order_status(order, get_next_status(order.status))
    return await status_observer.on_status_changed(order, localisation)


@dp.message(
    F.text,
    partial(on_order_status, orders, [OrderStatus.app_notification_text])
)
@log_exceptions
@auto_delete_messages
async def customize_notification_text(message: types.Message) -> types.Message:
    user_id = message.from_user.id
    localisation = TemporaryInfo.get_localisation(message)
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    order.app_notification_text = message.text
    orders.update_order(order)
    orders.update_order_status(order, get_next_status(order.status))

    return await status_observer.on_status_changed(order, localisation)


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.app_permissions])
)
@auto_delete_messages
async def customize_permissions(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)

    order = orders.get_user_order(user_id)
    order_permissions: list[str] = order.permissions.split(",")

    if call.data == "permission_continue":
        orders.update_order_status(order, get_next_status(order.status))
        await call.answer()
        await clear_buttons_from_messages(user_id)
        return await status_observer.on_status_changed(order, localisation)
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
    markup = types.InlineKeyboardMarkup(inline_keyboard=utils.create_permissions_keyboard(order, localisation))
    await call.answer()
    await call.message.edit_reply_markup(reply_markup=markup)
    return None


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.failed_notified])
)
@log_exceptions
@auto_delete_messages
async def process_failure(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)
    await call.answer()
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    if call.data == 'retry_build':
        order.status = get_next_status(order.status, "retry")
        order.record_created = datetime.now().astimezone(pytz.utc)
        order.priority = get_order_priority(user_id)
        orders.update_order(order)
        return await status_observer.on_status_changed(order, localisation)
    else:
        orders.remove_order(order.id)
        return await send_cancelled_message(call)


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
async def process_clear_bot(call: types.CallbackQuery) -> types.Message:
    message = call.message
    user_id = call.from_user.id
    await call.answer()
    await clear_buttons_from_messages(user_id)
    await asyncio.gather(MessagesDeleter.deleter.delete_all_messages(message.chat.id),
                         message.bot.delete_message(message.chat.id, message.message_id))
    return None


@dp.callback_query(
    partial(on_order_status, orders, [OrderStatus.successfully_finished]),
    F.data == 'get_source_code'
)
@log_exceptions
@auto_delete_messages
async def process_source_code(call: types.CallbackQuery) -> types.Message:
    user_id = call.from_user.id
    localisation = TemporaryInfo.get_localisation(call)
    await call.answer()
    await clear_buttons_from_messages(user_id)

    order = orders.get_user_order(user_id)
    order.sources_only = True
    order.status = get_next_status(order.status, "get_sources")
    orders.update_order(order)
    return await status_observer.on_status_changed(order, localisation)


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
    if orders.order_for_user_not_exists(message.from_user.id):
        return await message.answer(localisation.get_message_text("suggest-start"))
    else:
        return await message.answer(localisation.get_message_text("unknown-text-response"))


if __name__ == "__main__":
    asyncio.run(start())