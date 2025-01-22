import asyncio
import logging
import traceback
from typing import Optional

from aiogram import types, Bot
from aiogram.exceptions import TelegramForbiddenError

import db
import utils
from crud.error_logs_crud import ErrorLogsCRUD
from models import Order
from crud.orders_crud import  OrdersCRUD
from schemas.android_app_permission import AndroidAppPermission
from schemas.order_status import OrderStatus, get_next_status
from src.localisation.localisation import Localisation
from . import build_result_sender
from .order_generator import OrderGenerator
from .primary_color import PrimaryColor, primary_colors_with_emoji
from .stats import increase_build_start_count, increase_queued_count, increase_successful_build_count, \
    increase_failed_build_count, increase_sources_count, increase_screen_stats, increase_queued_low_priority_count

from .temporary_info import TemporaryInfo
from .messages_deleter import MessagesDeleter
from .screenshot_maker import ScreenshotMaker


class OrderStatusObserver:
    def __init__(self, bot: Bot, orders: OrdersCRUD):
        self.bot = bot
        self.orders = orders

    async def observe(self):
        logging.info("Starting order status observer")
        statuses_for_observation = [
            OrderStatus.build_started,
            OrderStatus.built,
            OrderStatus.failed,
            OrderStatus.sources_downloaded
        ]
        while True:
            for status in statuses_for_observation:
                for order in self.orders.get_orders_by_status(status=status):
                    try:
                        response = await self.on_status_changed(order)
                        MessagesDeleter.deleter.add_message(response)
                    except TelegramForbiddenError:
                        self.orders.remove_order(order.id)
                    except Exception as e:
                        ErrorLogsCRUD(db.engine).add_log(
                            f"During OrderStatusObserver the following exception occurred:\n\n{traceback.format_exc()}")
                        logging.error("During OrderStatusObserver the following exception occurred:", e)
            await asyncio.sleep(1)

    async def on_status_changed(self, order: Optional[Order], localisation: Localisation = None) -> types.Message:
        if order is None:
            return None
        if localisation is None:
            member = await self.bot.get_chat_member(order.user_id, order.user_id)
            localisation = TemporaryInfo.get_localisation(member.user)

        status = order.status
        if status == OrderStatus.app_masked_passcode_screen:
            return await self.send_masked_screen_options(order, localisation)
        elif status == OrderStatus.app_masked_passcode_screen_advanced:
            return await self.send_advanced_masked_screen_options(order, localisation)
        elif status == OrderStatus.generated:
            return await self.send_generated(order, localisation)
        elif status == OrderStatus.app_name or status == OrderStatus.app_name_only:
            return await self.send_ask_app_name(order, localisation)
        elif status == OrderStatus.app_id:
            return await self.send_app_id_options(order, localisation)
        elif status == OrderStatus.app_icon or status == OrderStatus.app_icon_only:
            return await self.send_ask_icon(order, localisation)
        elif status == OrderStatus.app_version_name:
            return await self.send_ask_version_name(order, localisation)
        elif status == OrderStatus.app_version_code:
            return await self.send_ask_version_code(order, localisation)
        elif status == OrderStatus.app_notification_color:
            return await self.send_notification_color_options(order, localisation)
        elif status == OrderStatus.app_notification_icon:
            return await self.send_ask_notification_icon(order, localisation)
        elif status == OrderStatus.app_notification_text:
            return await self.send_ask_notification_text(order, localisation)
        elif status == OrderStatus.app_permissions:
            return await self.send_ask_permissions(order, localisation)
        elif status == OrderStatus.confirmation:
            return await self.send_order_confirmation_request(order, localisation)
        elif status == OrderStatus.update_confirmation:
            return await self.send_update_order_confirmation_request(order, localisation)
        elif status == OrderStatus.queued:
            increase_queued_count()
            if order.priority > 1:
                increase_queued_low_priority_count()
            return await self.send_order_queued_notification(order, localisation)
        elif status == OrderStatus.update_queued:
            increase_queued_count()
            if order.priority > 1:
                increase_queued_low_priority_count()
            return await self.send_order_update_queued_notification(order, localisation)
        elif status == OrderStatus.build_started:
            increase_build_start_count()
            increase_screen_stats(order.app_masked_passcode_screen)
            return await self.send_build_started_notification(order, localisation)
        elif status == OrderStatus.built:
            return await self.send_apk(order, localisation)
        elif status == OrderStatus.successfully_finished:
            increase_successful_build_count()
            return await self.send_build_finished_successfully_notification(order, localisation)
        elif status == OrderStatus.get_sources_queued:
            increase_sources_count()
            return await self.send_get_sources_queued_notification(order, localisation)
        elif status == OrderStatus.sources_downloaded:
            return await self.send_sources(order, localisation)
        elif status == OrderStatus.getting_sources_successfully_finished:
            return await self.send_getting_sources_finished_successfully_notification(order, localisation)
        elif status == OrderStatus.failed:
            increase_failed_build_count()
            return await self.send_failure_notification(order, localisation)

    async def send_masked_screen_options(self, order: Order, localisation: Localisation) -> types.Message:
        await self.bot.send_chat_action(order.user_id, "upload_photo")
        inline_keyboard = [
            [
                types.InlineKeyboardButton(
                    text="Calculator",
                    callback_data='screen_calculator'
                ),
                types.InlineKeyboardButton(
                    text="Note",
                    callback_data='screen_note'
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=localisation.get_message_text("advanced-screens"),
                    callback_data='show_advanced_screens'
                ),
            ],
        ]
        main_text = localisation.get_message_text("ask-for-masked-passcode-screen").format("\n\n".join([
            localisation.get_message_text("calculator-screen-description"),
            localisation.get_message_text("note-screen-description")
        ]))
        advanced_screens_text = localisation.get_message_text("advanced-masked-passcode-screens-description").format(
            localisation.get_message_text("advanced-screens")
        )
        text = "\n\n".join([main_text, advanced_screens_text])
        markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        screens_examples = [
            types.InputMediaPhoto(media=types.FSInputFile("resources/calculator_example.png", filename="")),
            types.InputMediaPhoto(media=types.FSInputFile("resources/note_example.png", filename="")),
        ]
        sent_messages = await self.bot.send_media_group(order.user_id, screens_examples)
        for msg in sent_messages:
            MessagesDeleter.deleter.add_message(msg)
        return await self.bot.send_message(order.user_id, text, reply_markup=markup)

    async def send_advanced_masked_screen_options(self, order: Order, localisation: Localisation) -> types.Message:
        await self.bot.send_chat_action(order.user_id, "upload_photo")
        inline_keyboard = [
            [
                types.InlineKeyboardButton(
                    text="Loading",
                    callback_data='screen_loading'
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=localisation.get_message_text("back"),
                    callback_data='back'
                ),
            ],
        ]
        text = localisation.get_message_text("ask-for-masked-passcode-screen").format(
            localisation.get_message_text("loading-screen-description")
        )
        markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        photo_message = await self.bot.send_photo(
            order.user_id,
            photo=types.FSInputFile("resources/loading_example.png", filename=""),
        )
        MessagesDeleter.deleter.add_message(photo_message)
        return await self.bot.send_message(order.user_id, text, reply_markup=markup)

    async def send_generated(self, order: Order, localisation: Localisation) -> types.Message:
        await self.bot.send_chat_action(order.user_id, "upload_photo")
        photo_message = await self.bot.send_photo(
            order.user_id,
            photo=types.BufferedInputFile(file=ScreenshotMaker(order).make_full_screen_example(), filename=''),
        )

        MessagesDeleter.deleter.add_message(photo_message)

        return await self.bot.send_message(
            order.user_id,
            "\n\n".join((
                localisation.get_message_text("request-generated"),
                self.format_current_app_settings(order, localisation),
                self.format_you_may_not_understand_settings(localisation)
            )),
            reply_markup = self.build_request_confirmation_keyboard_markup(localisation),
        )

    async def send_ask_app_name(self, order: Order, localisation: Localisation) -> types.Message:
        text = "\n\n".join((
            localisation.get_message_text("ask-for-app-name"),
            localisation.get_message_text("current-value").format(self.truncate(order.app_name, 1000)),
        ))
        reply_markup = self.create_leave_current_value_and_continue_keyboard_markup(localisation)
        return await self.bot.send_message(order.user_id, text, reply_markup=reply_markup)

    async def send_app_id_options(self, order: Order, localisation: Localisation) -> types.Message:
        suggestions = []
        buttons = []
        order_generator = OrderGenerator(order, localisation)
        while len(set(suggestions)) < 3:
            suggestion = order_generator.random_app_id()
            if suggestion not in suggestions:
                suggestions.append(suggestion)
                button = types.InlineKeyboardButton(
                    text=suggestion,
                    callback_data=suggestion
                )
                buttons.append([button])
        custom_button = types.InlineKeyboardButton(
            text=localisation.get_message_text("custom-app-id"),
            callback_data='custom_app_id')
        buttons.append([custom_button])
        buttons.append([types.InlineKeyboardButton(
                text=localisation.get_message_text("leave-current-value"),
                callback_data="leave_current_value_and_continue"
            )])
        markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)

        text = "\n\n".join((
            localisation.get_message_text("app-id-about"),
            localisation.get_message_text("current-value").format(self.truncate(order.app_id, 1000)),
        ))

        response = await self.bot.send_message(
            order.user_id,
            text,
            reply_markup=markup,
        )
        return response

    async def send_ask_icon(self, order: Order, localisation: Localisation) -> types.Message:
        await self.bot.send_chat_action(order.user_id, "upload_photo")
        text = localisation.get_message_text("ask-icon")
        reply_markup = self.create_leave_current_value_and_continue_keyboard_markup(localisation)

        return await self.bot.send_photo(
            order.user_id,
            photo=types.BufferedInputFile(file=ScreenshotMaker(order).make_shortcut_screen_example(), filename=''),
            caption=text,
            reply_markup=reply_markup,
        )

    async def send_ask_version_name(self, order: Order, localisation: Localisation) -> types.Message:
        text = "\n\n".join((
            localisation.get_message_text("ask-for-version-name"),
            localisation.get_message_text("current-value").format(self.truncate(order.app_version_name, 1000)),
        ))
        reply_markup = self.create_leave_current_value_and_continue_keyboard_markup(localisation)
        return await self.bot.send_message(order.user_id, text, reply_markup=reply_markup)

    async def send_ask_version_code(self, order: Order, localisation: Localisation) -> types.Message:
        text = "\n\n".join((
            localisation.get_message_text("ask-for-version-code"),
            localisation.get_message_text("current-value").format(order.app_version_code),
        ))
        reply_markup = self.create_leave_current_value_and_continue_keyboard_markup(localisation)
        return await self.bot.send_message(order.user_id, text, reply_markup=reply_markup)

    async def send_notification_color_options(self, order: Order, localisation: Localisation) -> types.Message:
        system_color_row = [types.InlineKeyboardButton(text=localisation.get_message_text("system-color"), callback_data=f"color_system")]
        colors_row = [types.InlineKeyboardButton(text=color.localize(localisation), callback_data=f"color_{color.name}") for color in primary_colors_with_emoji]
        leave_current_value_and_continue_row = [types.InlineKeyboardButton(
            text=localisation.get_message_text("leave-current-value"),
            callback_data="leave_current_value_and_continue"
        )]
        inline_keyboard = [system_color_row, colors_row, leave_current_value_and_continue_row]

        current_color = PrimaryColor.get_color_by_value(order.app_notification_color)
        text = "\n\n".join((
            localisation.get_message_text("ask-for-notification-color"),
            localisation.get_message_text("current-value").format(current_color.localize(localisation)),
        ))

        markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        return await self.bot.send_message(order.user_id, text, reply_markup=markup)

    async def send_ask_notification_icon(self, order: Order, localisation: Localisation) -> types.Message:
        await self.bot.send_chat_action(order.user_id, "upload_photo")
        text = localisation.get_message_text("ask-for-notification-icon")
        reply_markup = self.create_leave_current_value_and_continue_keyboard_markup(localisation)

        return await self.bot.send_photo(
            order.user_id,
            photo=types.BufferedInputFile(file=ScreenshotMaker(order).make_notification_screen_example(), filename=''),
            caption=text,
            reply_markup=reply_markup,
        )

    async def send_ask_notification_text(self, order: Order, localisation: Localisation) -> types.Message:
        text = "\n\n".join((
            localisation.get_message_text("ask-for-notification-text"),
            localisation.get_message_text("current-value").format(self.truncate(order.app_notification_text, 1000)),
        ))
        reply_markup = self.create_leave_current_value_and_continue_keyboard_markup(localisation)
        return await self.bot.send_message(order.user_id, text, reply_markup=reply_markup)

    async def send_ask_permissions(self, order: Order, localisation: Localisation) -> types.Message:
        markup = types.InlineKeyboardMarkup(inline_keyboard=utils.create_permissions_keyboard(order, localisation))
        return await self.bot.send_message(order.user_id, localisation.get_message_text("ask-for-permissions"), reply_markup=markup)

    async def send_order_confirmation_request(self, order: Order, localisation: Localisation):
        await self.bot.send_chat_action(order.user_id, "upload_photo")
        photo_message = await self.bot.send_photo(
            order.user_id,
            photo=types.BufferedInputFile(file=ScreenshotMaker(order).make_full_screen_example(), filename=''),
        )
        MessagesDeleter.deleter.add_message(photo_message)
        return await self.bot.send_message(
            order.user_id,
            "\n\n".join((
                self.format_current_app_settings(order, localisation),
                self.format_you_may_not_understand_settings(localisation)
            )),
            reply_markup = self.build_request_confirmation_keyboard_markup(localisation),
        )

    async def send_update_order_confirmation_request(self, order: Order, localisation: Localisation):
        await self.bot.send_chat_action(order.user_id, "upload_photo")
        photo_message = await self.bot.send_photo(
            order.user_id,
            photo=types.BufferedInputFile(file=ScreenshotMaker(order).make_full_screen_example(), filename=''),
        )
        MessagesDeleter.deleter.add_message(photo_message)
        inline_keyboard = [
            [
                types.InlineKeyboardButton(
                    text=localisation.get_message_text("start-build"),
                    callback_data="generated_confirm"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=localisation.get_message_text("customize-settings"),
                    callback_data="generated_customize"
                ),
            ],
        ]
        return await self.bot.send_message(
            order.user_id,
            self.format_current_app_settings(order, localisation),
            reply_markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard),
        )

    async def send_order_queued_notification(self, order: Order, localisation: Localisation) -> types.Message:
        queue_order_count = self.orders.get_order_queue_position(order)
        text = localisation.get_message_text("queued").format(queue_order_count)
        if order.priority > 1:
            text += "\n\n"
            text += localisation.get_message_text("low-priority")
        return await self.bot.send_message(order.user_id, text)

    async def send_order_update_queued_notification(self, order: Order, localisation: Localisation) -> types.Message:
        queue_order_count = self.orders.get_order_queue_position(order)
        text = localisation.get_message_text("queued").format(queue_order_count)
        if order.priority > 1:
            text += "\n\n" + localisation.get_message_text("low-priority")
        text += "\n\n" + localisation.get_message_text("you-can-change-update-order")

        return await self.bot.send_message(order.user_id, text)

    async def send_build_started_notification(self, order: Order, localisation: Localisation) -> types.Message:
        response = await self.bot.send_message(order.user_id, localisation.get_message_text("build-started"))
        self.orders.update_order_status(order, get_next_status(order, "notified"))
        return response

    async def send_apk(self, order: Order, localisation: Localisation) -> types.Message:
        await build_result_sender.BuildResultSender(self.bot, self.orders, self).send_build_result(order)
        return None

    async def send_build_finished_successfully_notification(self, order: Order, localisation: Localisation) -> types.Message:
        markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=localisation.get_message_text("clear-bot"),
                    callback_data='clear_bot'
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=localisation.get_message_text("get-source-code"),
                    callback_data='get_source_code'
                ),
            ]
        ])
        text = "\n\n".join([
            localisation.get_message_text("build-ended").format(
                localisation.get_message_text("get-source-code")
            ),
            localisation.get_message_text("chat-will-be-deleted-automatically").format(
                MessagesDeleter.deleter.get_user_timeout(order.user_id) // 60,
                localisation.get_message_text("clear-bot")
            ),
        ])
        return await self.bot.send_message(
            order.user_id,
            text,
            reply_markup=markup
        )

    async def send_get_sources_queued_notification(self, order: Order, localisation: Localisation) -> types.Message:
        queue_order_count = self.orders.get_order_queue_position(order)
        text = localisation.get_message_text("get-sources-queued").format(queue_order_count)
        return await self.bot.send_message(order.user_id, text)

    async def send_sources(self, order: Order, localisation: Localisation) -> types.Message:
        logging.info("send_sources")
        await build_result_sender.BuildResultSender(self.bot, self.orders, self).send_build_result(order)
        return None

    async def send_getting_sources_finished_successfully_notification(self, order: Order, localisation: Localisation) -> types.Message:
        markup = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(
                text=localisation.get_message_text("clear-bot"),
                callback_data='clear_bot'
            ),
        ]])
        text = "\n\n".join([
            localisation.get_message_text("sources-sent"),
            localisation.get_message_text("chat-will-be-deleted-automatically").format(
                MessagesDeleter.deleter.get_user_timeout(order.user_id) // 60,
                localisation.get_message_text("clear-bot")
            ),
        ])
        return await self.bot.send_message(
            order.user_id,
            text,
            reply_markup=markup
        )

    async def send_failure_notification(self, order: Order, localisation: Localisation) -> types.Message:
        markup = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(
                text=localisation.get_message_text("retry-build"),
                callback_data='retry_build'
            ),
            types.InlineKeyboardButton(
                text=localisation.get_message_text("cancel-order"),
                callback_data='cancel_order'
            )
        ]])

        if order and order.update_tag:
            message_prefix = f"#update-request-failed-{order.update_tag}\n\n"
        else:
            message_prefix = ""

        response = await self.bot.send_message(
            order.user_id,
            message_prefix + localisation.get_message_text("build-failed"),
            reply_markup=markup
        )
        self.orders.update_order_status(order, get_next_status(order))
        return response

    @staticmethod
    def create_leave_current_value_and_continue_keyboard_markup(localisation: Localisation) -> types.InlineKeyboardMarkup:
        inline_keyboard = [[
            types.InlineKeyboardButton(
                text=localisation.get_message_text("leave-current-value"),
                callback_data="leave_current_value_and_continue"
            ),
        ]]
        return types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    @staticmethod
    def format_current_app_settings(order: Order, localisation: Localisation) -> str:
        available_permissions = [permission
                                 for permission in order.permissions.split(",")
                                 if permission != ""]

        unavailable_permissions = [permission
                                   for permission in AndroidAppPermission
                                   if permission not in available_permissions]

        return localisation.get_message_text("current-app-settings").format(
            order.app_masked_passcode_screen,
            OrderStatusObserver.truncate(order.app_name, 100),
            OrderStatusObserver.truncate(order.app_id, 100),
            OrderStatusObserver.truncate(order.app_version_name, 100),
            order.app_version_code,
            OrderStatusObserver.truncate(order.app_notification_text, 100),
            OrderStatusObserver.format_permission_list(available_permissions, localisation),
            OrderStatusObserver.format_permission_list(unavailable_permissions, localisation),
            PrimaryColor.get_color_by_value(order.app_notification_color).localize(localisation),

            localisation.get_message_text("customize-settings"),
            localisation.get_message_text("start-build"),
        )

    @staticmethod
    def format_you_may_not_understand_settings(localisation: Localisation) -> str:
        return localisation.get_message_text("you-may-not-understand-settings").format(
            localisation.get_message_text("customize-settings"),
            localisation.get_message_text("start-build"),
        )

    @staticmethod
    def truncate(s: str, max_length: int) -> str:
        return s[:max_length] + '…' if len(s) > max_length else s

    @staticmethod
    def format_permission_list(permissions: list[str], localisation: Localisation) -> str:
        if not permissions:
            return f'<i>{localisation.get_message_text("empty")}</i>'
        localized_permissions = [localisation.get_message_text(f"permission-{permission}") for permission in permissions]
        return ", ".join(localized_permissions)

    @staticmethod
    def build_request_confirmation_keyboard_markup(localisation: Localisation) -> types.InlineKeyboardMarkup:
        inline_keyboard = [
            [
                types.InlineKeyboardButton(
                    text=localisation.get_message_text("start-build"),
                    callback_data="generated_confirm"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=localisation.get_message_text("customize-app-name-only"),
                    callback_data="generated_customize_app_name_only"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=localisation.get_message_text("customize-app-icon-only"),
                    callback_data="generated_customize_app_icon_only"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=localisation.get_message_text("customize-settings"),
                    callback_data="generated_customize"
                ),
            ],
        ]
        return types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
