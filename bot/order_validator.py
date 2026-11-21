import io
import re
from typing import Callable

from PIL import Image

import config
import utils
from bot.primary_color import PrimaryColor
from models import Order
from schemas.android_app_permission import AndroidAppPermission


UPDATE_FIXABLE_FIELDS = ("app_name", "app_version_name", "app_notification_text")


def validate_icon(icon_bytes, need_transparency = False) -> bool:
    if not isinstance(icon_bytes, bytes) or len(icon_bytes) > config.FILE_SIZE_LIMIT:
        return False
    try:
        with Image.open(io.BytesIO(icon_bytes), formats=["PNG", "JPEG", "WEBP"]) as image:
            if need_transparency and not utils.has_transparency(image):
                return False
    except:
        return False
    return True

def validate_notification_icon(icon_bytes) -> bool:
    return validate_icon(icon_bytes, need_transparency=True)

def validate_version_code_for_update(version_code) -> bool:
    return type(version_code) is int and 0 < version_code <= config.MAX_VERSION_CODE * 2 # allow bigger version_code for updates

def validate_color(color) -> bool:
    return type(color) is int and PrimaryColor.get_color_by_value(color) is not None

def validate_masked_passcode_screen(screen) -> bool:
    return isinstance(screen, str) and screen in {"calculator", "loading", "note"}

def validate_permissions(permissions) -> bool:
    return (isinstance(permissions, str)
            and set(filter(None, permissions.split(","))) <= {p.value for p in AndroidAppPermission})

def validate_keystore(keystore) -> bool:
    return isinstance(keystore, bytes) and len(keystore) <= config.FILE_SIZE_LIMIT

def validate_keystore_password_salt(salt) -> bool:
    return isinstance(salt, str) and re.fullmatch(r'[A-Za-z]{1,64}', salt) is not None

def validate_update_tag(update_tag) -> bool:
    return isinstance(update_tag, str) and len(update_tag) == 32 and all([c in "0123456789ABCDEF" for c in update_tag])

def validate_order_id(order_id) -> bool:
    return type(order_id) is int and order_id > 0

def validate_sources_only(sources_only) -> bool:
    return type(sources_only) is bool


FIELD_VALIDATORS: dict[str, Callable[[object], bool]] = {
    "app_name": utils.is_valid_display_text,
    "app_id": utils.is_valid_app_id,
    "app_icon": validate_icon,
    "app_version_code": validate_version_code_for_update,
    "app_version_name": utils.is_valid_version_name,
    "app_notification_icon": validate_notification_icon,
    "app_notification_color": validate_color,
    "app_masked_passcode_screen": validate_masked_passcode_screen,
    "app_notification_text": utils.is_valid_display_text,
    "permissions": validate_permissions,
    "keystore": validate_keystore,
    "keystore_password_salt": validate_keystore_password_salt,
}

UPDATE_VALIDATORS = FIELD_VALIDATORS | {"update_tag": validate_update_tag}

WORKER_VALIDATORS = FIELD_VALIDATORS | {"id": validate_order_id, "sources_only": validate_sources_only}


def is_valid_field(validator: Callable[[object], bool], value) -> bool:
    try:
        return bool(validator(value))
    except Exception:
        return False

def get_invalid_fields(order: Order, validators: dict[str, Callable[[object], bool]]) -> list[str]:
    return [field for field, validator in validators.items() if not is_valid_field(validator, getattr(order, field, None))]

def get_invalid_update_fields(order: Order) -> list[str]:
    return get_invalid_fields(order, UPDATE_VALIDATORS)

def are_all_invalid_update_fields_fixable(order: Order) -> bool:
    return all(field in UPDATE_FIXABLE_FIELDS for field in get_invalid_update_fields(order))

def get_invalid_worker_fields(order: Order) -> list[str]:
    return get_invalid_fields(order, WORKER_VALIDATORS)
