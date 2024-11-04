from typing import Optional


class AppTemplate:
    def __init__(
            self,
            *,
            screen_name: str = None,
            inner_templates: Optional[list["AppTemplate"]] = None,
            possible_names: list[str] = None,
            possible_icons: list[str] = None,
            possible_notifications: list[str] = None
            ):
        self.screen_name = screen_name

        self.inner_templates = inner_templates
        self.possible_names = possible_names
        self.possible_icons = possible_icons
        self.possible_notifications = possible_notifications
