from typing import Optional, Union


class AppTemplate:
    def __init__(
            self,
            *,
            screen_name: str = None,
            inner_templates: Optional[list["AppTemplate"]] = None,
            possible_names: list[str] = None,
            possible_icons: list[str] = None,
            possible_notification_icons: list[str] = None,
            possible_notifications: Union[list[str], dict[str, list[str]]] = None
            ):
        self.screen_name = screen_name

        self.inner_templates = inner_templates
        self.possible_names = possible_names
        self.possible_icons = possible_icons
        self.possible_notification_icons = possible_notification_icons
        self.possible_notifications = possible_notifications
