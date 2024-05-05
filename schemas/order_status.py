from enum import Enum


class OrderStatus(str, Enum):
    appname = "appname"
    appid = "appid"
    appicon = "appicon"
    configured = "configured"
    confirmation = "confirmation"
    queued = "queued"
    build_started = "build-started"
    building = "building"
    built = "built"
    sending_apk = "sending-apk"
    failed = "failed"
    failed_notified = "failed-notified"
    canceled = "canceled"
    completed = "completed"


STATUSES_IN_PROGRESS = [
    OrderStatus.queued,
    OrderStatus.build_started,
    OrderStatus.building,
    OrderStatus.built,
    OrderStatus.sending_apk,
]

STATUSES_BUILDING = [
    OrderStatus.build_started,
    OrderStatus.building,
    OrderStatus.built,
    OrderStatus.sending_apk,
]

STATUSES_CONFIGURING = [
    OrderStatus.appname,
    OrderStatus.appid,
    OrderStatus.appicon,
    OrderStatus.configured,
    OrderStatus.confirmation,
]

STATUSES_COMPLETED = [
    OrderStatus.failed,
    OrderStatus.failed_notified,
    OrderStatus.canceled,
    OrderStatus.completed,
]