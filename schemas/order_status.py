from enum import Enum
from typing import Optional, Union


class OrderStatus(str, Enum):
    app_masked_passcode_screen = "app_masked_passcode_screen"
    generated = "generated"
    app_name = "app_name"
    app_id = "app_id"
    app_icon = "app_icon"
    app_version_name = "app_version_name"
    app_version_code = "app_version_code"
    app_notification_icon = "app_notification_icon"
    app_notification_color = "app_notification_color"
    app_notification_text = "app_notification_text"
    app_permissions = "app_permissions"
    configured = "configured"
    confirmation = "confirmation"
    queued = "queued"
    build_started = "build-started"
    building = "building"
    built = "built"
    sending_apk = "sending-apk"
    failed = "failed"
    failed_notified = "failed-notified"

STATUSES_BUILDING = [
    OrderStatus.build_started,
    OrderStatus.building,
    OrderStatus.built,
    OrderStatus.sending_apk,
]

STATUSES_CONFIGURING = [
    OrderStatus.app_masked_passcode_screen,
    OrderStatus.generated,
    OrderStatus.app_name,
    OrderStatus.app_id,
    OrderStatus.app_icon,
    OrderStatus.app_version_name,
    OrderStatus.app_version_code,
    OrderStatus.app_notification_icon,
    OrderStatus.app_notification_color,
    OrderStatus.app_notification_text,
    OrderStatus.app_permissions,
    OrderStatus.configured,
    OrderStatus.confirmation,
]

STATUSES_FAILED = [
    OrderStatus.failed,
    OrderStatus.failed_notified
]

OptionalOrderStatus = Union[OrderStatus, None]
StatusTransition = Union[OptionalOrderStatus, dict[str, OptionalOrderStatus]]

_STATUS_TRANSITIONS: dict[OptionalOrderStatus, StatusTransition] = {
    None: OrderStatus.app_masked_passcode_screen,
    OrderStatus.app_masked_passcode_screen: OrderStatus.generated,
    OrderStatus.generated: {"confirm": OrderStatus.queued, "customize": OrderStatus.app_name},
    OrderStatus.app_name: OrderStatus.app_id,
    OrderStatus.app_id: OrderStatus.app_icon,
    OrderStatus.app_icon: OrderStatus.app_version_name,
    OrderStatus.app_version_name: OrderStatus.app_version_code,
    OrderStatus.app_notification_icon: None,
    OrderStatus.app_version_code: OrderStatus.app_notification_color,
    OrderStatus.app_notification_color: OrderStatus.app_notification_text,
    OrderStatus.app_notification_text: OrderStatus.app_permissions,
    OrderStatus.app_permissions: OrderStatus.configured,
    OrderStatus.configured: OrderStatus.confirmation,
    OrderStatus.confirmation: {"yes": OrderStatus.queued, "no": None},
    OrderStatus.queued: OrderStatus.build_started,
    OrderStatus.build_started: {"notified": OrderStatus.building, "repeat": OrderStatus.queued, "fail": OrderStatus.failed},
    OrderStatus.building: {"success": OrderStatus.built, "repeat": OrderStatus.queued, "fail": OrderStatus.failed},
    OrderStatus.built: {"send_apk": OrderStatus.sending_apk, "fail": OrderStatus.failed},
    OrderStatus.sending_apk: {"success": None, "repeat": OrderStatus.built},
    OrderStatus.failed: OrderStatus.failed_notified,
    OrderStatus.failed_notified: {"retry": OrderStatus.queued, "cancel": None}
}

def get_next_status(status: OptionalOrderStatus, transition_name: Optional[str] = None) -> OptionalOrderStatus:
    transitions = _STATUS_TRANSITIONS[status]
    if isinstance(transitions, OrderStatus):
        if transition_name is None:
            return transitions
        else:
            raise Exception(f"Can't get next status. Provided transition name {transition_name}," +
                            f" but status '{status}' doesn't require transition name.")
    elif isinstance(transitions, dict):
        if transition_name is not None:
            if transition_name in transitions:
                return transitions[transition_name]
            else:
                raise Exception(f"Can't get next status. Unknown transition {transition_name} for status '{status}'.")
        else:
            raise Exception(f"Can't get next status. No transition name provided for '{status}'.")
    else:
        raise Exception(f"Unknown transition type for '{status}'.")
