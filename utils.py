import os
import re

from PIL.Image import Image
from unidecode import unidecode

import config


def mask_user_id(user_id, left_digits_count=2):
    symbols = list(str(user_id))
    for i in range(0, len(symbols) - left_digits_count):
        symbols[i] = '#'
    return "".join(symbols)


def make_order_building_dir_path(order_id: int) -> str:
    return os.path.join(config.TMP_DIR, "orders", str(order_id))


def make_order_apk_dir_path(order_id: int) -> str:
    return os.path.join(config.TMP_DIR, "apk", str(order_id))


def normalize_name(app_name: str, delimiter: str = '') -> str:
    ascii_app_name = unidecode(app_name)
    normalized = re.sub(r'\W+', delimiter, ascii_app_name).lower()
    normal_name_pattern = re.compile(r'[a-z]{1}[a-z\d_]+')
    if normal_name_pattern.match(normalized):
        return normalized
    else:
        return config.APP_NAME_REPLACEMENT_FOR_NOT_NORMALIZED


def crop_center_rectangle(image: Image) -> Image:
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
