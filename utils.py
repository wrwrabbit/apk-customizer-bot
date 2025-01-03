import os
import re

from PIL.Image import Image
from aiogram import types
from unidecode import unidecode

import config
from models import Order
from schemas.android_app_permission import AndroidAppPermission
from src.localisation.localisation import Localisation


def mask_user_id(user_id, left_digits_count=2):
    symbols = list(str(user_id))
    for i in range(0, len(symbols) - left_digits_count):
        symbols[i] = '#'
    return "".join(symbols)


def make_order_building_dir_path(order_id: int) -> str:
    return os.path.join(config.TMP_DIR, "orders", str(order_id))


def make_order_build_result_dir_path(order_id: int) -> str:
    return os.path.join(config.TMP_DIR, "build_result", str(order_id))


def normalize_name(app_name: str, delimiter: str = '') -> str:
    ascii_app_name = unidecode(app_name)
    trimmed_ascii_app_name = re.sub(r'(^\W+)|(\W+$)', "", ascii_app_name) # remove all non-word chars from the beginning and from the end
    normalized = re.sub(r'\W+', delimiter, trimmed_ascii_app_name).lower()
    normalized = normalized[:30]
    normal_name_pattern = re.compile(r'[a-z]{1}[a-z\d_]+')
    if normal_name_pattern.match(normalized):
        return normalized
    else:
        return config.APP_NAME_REPLACEMENT_FOR_NOT_NORMALIZED


def crop_center_square(image: Image) -> Image:
    if image.width == image.height:
        return image
    elif image.width > image.height:
        left = (image.width - image.height) // 2
        top = 0
        right = (image.width + image.height) // 2
        bottom = image.height
    else:
        left = 0
        top = (image.height - image.width) // 2
        right = image.width
        bottom = (image.height + image.width) // 2
    return image.crop((left, top, right, bottom))


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

def has_transparency(image: Image):
    if image.info.get("transparency", None) is not None:
        return True
    if image.mode == "RGBA":
        extrema = image.getextrema()
        min_alpha = extrema[3][0]
        max_alpha = extrema[3][1]
        if min_alpha < max_alpha:
            return True

    return False

