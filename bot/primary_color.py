from typing import Optional

from src.localisation.localisation import Localisation


class PrimaryColor:
    def __init__(self, name: str, emoji: Optional[str], value: int):
        self.name = name
        self.emoji = emoji
        self.value = value

    def localize(self, localisation: Localisation):
        if self.emoji is not None:
            return self.emoji
        else:
            return localisation.get_message_text("system-color")

    @staticmethod
    def get_color_by_value(value: int) -> 'PrimaryColor':
        return next((color for color in predefined_primary_colors if color.value == value), None)

    @staticmethod
    def get_color_by_name(name: str) -> 'PrimaryColor':
        return next((color for color in predefined_primary_colors if color.name == name), None)

predefined_primary_colors = [
    PrimaryColor(name="red", emoji="🟥", value=0xD40000),
    PrimaryColor(name="orange", emoji="🟧", value=0xAD4A00),
    PrimaryColor(name="green", emoji="🟩", value=0x007A00),
    PrimaryColor(name="blue", emoji="🟦", value=0x0069c2),
    PrimaryColor(name="purple", emoji="🟪", value=0x8B00FF),
    PrimaryColor(name="system", emoji=None, value=-1),
]

primary_colors_with_emoji = [color for color in predefined_primary_colors if color.value != -1]
