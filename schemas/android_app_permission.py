from enum import Enum

class AndroidAppPermission(str, Enum):
    camera = "camera"
    location = "location"
    microphone = "microphone"
    notifications = "notifications"
    photos_and_video = "photos_and_video"

    contacts = "contacts"
    music_and_audio = "music_and_audio"
    call_logs = "call_logs"
    phone = "phone"
    nearby_devices = "nearby_devices"
    sms = "sms"


default_permissions = [
    AndroidAppPermission.camera,
    AndroidAppPermission.location,
    AndroidAppPermission.microphone,
    AndroidAppPermission.notifications,
    AndroidAppPermission.photos_and_video
]