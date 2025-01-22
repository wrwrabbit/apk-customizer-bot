import io
import re

from PIL import Image

import config
import utils
from bot.primary_color import PrimaryColor
from models import Order
from schemas.android_app_permission import AndroidAppPermission


def validate_order(order: Order) -> bool:
    return (validate_string(order.app_name)
            and validate_app_id(order.app_id)
            and validate_icon(order.app_icon)
            and validate_version_code_for_update(order.app_version_code)
            and validate_string(order.app_version_name)
            and validate_icon(order.app_notification_icon, need_transparency=True)
            and validate_color(order.app_notification_color)
            and validate_masked_passcode_screen(order.app_masked_passcode_screen)
            and validate_string(order.app_notification_text)
            and validate_permissions(order.permissions)
            and validate_keystore(order.keystore)
            and validate_string(order.keystore_password_salt)
            and validate_update_tag(order.update_tag))


def validate_string(value) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 4096


def validate_app_id(app_id) -> bool:
    if not validate_string(app_id):
        return False
    app_id_pattern = re.compile(r'^([A-Za-z]{1}[A-Za-z\d_]*\.)+[A-Za-z][A-Za-z\d_]*$')
    if not app_id_pattern.fullmatch(app_id):
        return False
    return True

def validate_icon(icon_bytes, need_transparency = False) -> bool:
    if not isinstance(icon_bytes, bytes) or len(icon_bytes) > config.FILE_SIZE_LIMIT:
        return False
    try:
        with Image.open(io.BytesIO(icon_bytes)) as image:
            if need_transparency and not utils.has_transparency(image):
                return False
    except:
        return False
    return True

def validate_version_code_for_update(version_code) -> bool:
    return isinstance(version_code, int) and 0 < version_code <= config.MAX_VERSION_CODE * 2 # allow bigger version_code for updates

def validate_color(color) -> bool:
    try:
        return isinstance(color, int) and PrimaryColor.get_color_by_value(color)
    except:
        return False

def validate_masked_passcode_screen(screen) -> bool:
    return screen in {"calculator", "loading", "note"}

def validate_permissions(permissions) -> bool:
    return isinstance(permissions, str) and set(permissions.split(",")) <= {p.value for p in AndroidAppPermission}

def validate_keystore(keystore) -> bool:
    if not isinstance(keystore, bytes) or len(keystore) > config.FILE_SIZE_LIMIT:
        return False
    return True

def validate_update_tag(update_tag) -> bool:
    return isinstance(update_tag, str) and len(update_tag) == 32 and all([c in "0123456789ABCDEF" for c in update_tag])
