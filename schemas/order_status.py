from enum import Enum
from typing import Optional, Union


class OrderStatus(str, Enum):
    app_masked_passcode_screen = "app_masked_passcode_screen"
    app_masked_passcode_screen_advanced = "app_masked_passcode_screen_advanced"
    generated = "generated"
    app_name = "app_name"
    app_name_only = "app_name_only"
    app_id = "app_id"
    app_icon = "app_icon"
    app_icon_only = "app_icon_only"
    app_version_name = "app_version_name"
    app_version_code = "app_version_code"
    app_notification_color = "app_notification_color"
    app_notification_text = "app_notification_text"
    app_notification_icon = "app_notification_icon"
    app_permissions = "app_permissions"
    confirmation = "confirmation"
    queued = "queued"
    build_started = "build_started"
    building = "building"
    built = "built"
    sending_apk = "sending_apk"
    successfully_finished = "finished"
    get_sources_queued = "get_sources_queued"
    sources_downloaded = "sources_downloaded"
    sending_sources = "sending_sources"
    getting_sources_successfully_finished = "getting_sources_successfully_finished"
    failed = "failed"
    failed_notified = "failed_notified"

STATUSES_BUILDING = [
    OrderStatus.build_started,
    OrderStatus.building,
    OrderStatus.built,
    OrderStatus.sending_apk,
]

STATUSES_GETTING_SOURCES = [
    OrderStatus.get_sources_queued,
    OrderStatus.sources_downloaded,
    OrderStatus.sending_sources,
]

STATUSES_CONFIGURING = [
    OrderStatus.app_masked_passcode_screen,
    OrderStatus.app_masked_passcode_screen_advanced,
    OrderStatus.generated,
    OrderStatus.app_name,
    OrderStatus.app_name_only,
    OrderStatus.app_id,
    OrderStatus.app_icon,
    OrderStatus.app_icon_only,
    OrderStatus.app_version_name,
    OrderStatus.app_version_code,
    OrderStatus.app_notification_color,
    OrderStatus.app_notification_text,
    OrderStatus.app_notification_icon,
    OrderStatus.app_permissions,
    OrderStatus.confirmation,
]

STATUSES_FINISHED = [
    OrderStatus.failed,
    OrderStatus.failed_notified,
    OrderStatus.successfully_finished,
    OrderStatus.getting_sources_successfully_finished
]

OptionalOrderStatus = Union[OrderStatus, None]
StatusTransition = Union[OptionalOrderStatus, dict[str, OptionalOrderStatus]]

_STATUS_TRANSITIONS: dict[OptionalOrderStatus, StatusTransition] = {
    None: OrderStatus.app_masked_passcode_screen,
    OrderStatus.app_masked_passcode_screen: {None: OrderStatus.generated, "show_advanced_screens": OrderStatus.app_masked_passcode_screen_advanced},
    OrderStatus.app_masked_passcode_screen_advanced: {None: OrderStatus.generated, "back": OrderStatus.app_masked_passcode_screen},
    OrderStatus.generated: {"confirm": OrderStatus.queued, "customize_app_name_only": OrderStatus.app_name_only, "customize_app_icon_only": OrderStatus.app_icon_only, "customize": OrderStatus.app_name},
    OrderStatus.app_name: OrderStatus.app_id,
    OrderStatus.app_name_only: OrderStatus.confirmation,
    OrderStatus.app_id: OrderStatus.app_icon,
    OrderStatus.app_icon: OrderStatus.app_version_name,
    OrderStatus.app_icon_only: OrderStatus.confirmation,
    OrderStatus.app_version_name: OrderStatus.app_version_code,
    OrderStatus.app_version_code: OrderStatus.app_notification_color,
    OrderStatus.app_notification_color: OrderStatus.app_notification_text,
    OrderStatus.app_notification_text: OrderStatus.app_notification_icon,
    OrderStatus.app_notification_icon: OrderStatus.app_permissions,
    OrderStatus.app_permissions: OrderStatus.confirmation,
    OrderStatus.confirmation: {"confirm": OrderStatus.queued, "customize_app_name_only": OrderStatus.app_name_only, "customize_app_icon_only": OrderStatus.app_icon_only, "customize": OrderStatus.app_name},
    OrderStatus.queued: OrderStatus.build_started,
    OrderStatus.build_started: {"notified": OrderStatus.building, "repeat": OrderStatus.queued, "fail": OrderStatus.failed},
    OrderStatus.building: {"success": OrderStatus.built, "repeat": OrderStatus.queued, "fail": OrderStatus.failed},
    OrderStatus.built: {"send_result": OrderStatus.sending_apk, "fail": OrderStatus.failed},
    OrderStatus.sending_apk: {None: OrderStatus.successfully_finished, "repeat": OrderStatus.built, "fail": OrderStatus.failed},
    OrderStatus.successfully_finished: {None: None, "get_sources": OrderStatus.get_sources_queued},
    OrderStatus.get_sources_queued: OrderStatus.sources_downloaded,
    OrderStatus.sources_downloaded: {"send_result": OrderStatus.sending_sources},
    OrderStatus.sending_sources: OrderStatus.getting_sources_successfully_finished,
    OrderStatus.getting_sources_successfully_finished: None,
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
        if transition_name in transitions:
            return transitions[transition_name]
        elif transition_name is not None:
            raise Exception(f"Can't get next status. Unknown transition {transition_name} for status '{status}'.")
        else:
            raise Exception(f"Can't get next status. No transition name provided for '{status}'.")
    else:
        raise Exception(f"Unknown transition type for '{status}'.")
