import io
import math
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import utils
from models import Order


class ScreenshotMaker:
    def __init__(self, order: Order):
        self.icon_bytes = order.app_icon
        self.notification_icon_bytes = order.app_notification_icon
        self.app_name = order.app_name
        self.notification_text = order.app_notification_text
        if order.app_notification_color != -1:
            color_int = order.app_notification_color
        else:
            color_int = 0x676769
        self.notification_icon_color = f"#{color_int:0>6x}"

        self.screen_template_path = 'resources/screen.png'
        self.font_path = "resources/Roboto-Regular.ttf"
        self.screen_template_copy: Optional[Image.Image] = None
        self.screen_draw: Optional[ImageDraw.ImageDraw] = None

    def make_full_screen_example(self) -> bytes:
        with Image.open(self.screen_template_path) as screen_template:
            self.screen_template_copy = screen_template.copy()
            self.screen_draw = ImageDraw.Draw(self.screen_template_copy)

            self._draw_app_shortcut()
            self._draw_notification()

            return self._get_result_bytes()

    def make_shortcut_screen_example(self) -> bytes:
        with Image.open(self.screen_template_path) as screen_template:
            self.screen_template_copy = screen_template.copy()
            self.screen_draw = ImageDraw.Draw(self.screen_template_copy)

            self._draw_app_shortcut()
            width = self.screen_template_copy.width
            height = self.screen_template_copy.height
            self.screen_template_copy = self.screen_template_copy.crop((0, int(height * 0.3), width, height))

            return self._get_result_bytes()

    def make_notification_screen_example(self) -> bytes:
        with Image.open(self.screen_template_path) as screen_template:
            self.screen_template_copy = screen_template.copy()
            self.screen_draw = ImageDraw.Draw(self.screen_template_copy)

            self._draw_notification()
            width = self.screen_template_copy.width
            height = self.screen_template_copy.height
            self.screen_template_copy = self.screen_template_copy.crop((0, 0, width, int(height * 0.3)))

            return self._get_result_bytes()

    def _draw_app_shortcut(self):
        self._draw_app_shortcut_icon()
        self._draw_app_shortcut_title()

    def _draw_app_shortcut_icon(self):
        icon_x = 585
        icon_y = 1208
        icon_size = 156

        with Image.open(io.BytesIO(self.icon_bytes)) as icon:
            resized_icon: Image.Image = utils.crop_center_square(icon).resize((icon_size, icon_size))
            resized_icon = resized_icon.convert('RGBA')

            round_mask = Image.new("L", (icon_size, icon_size), 0)
            ImageDraw.Draw(round_mask).ellipse((0, 0, icon_size, icon_size), fill=255)
            round_mask = round_mask.filter(ImageFilter.GaussianBlur(1))

            final_mask = Image.new("L", (icon_size, icon_size), 0)
            final_mask.paste(round_mask, mask=resized_icon) # use transparency from the icon

            self.screen_template_copy.paste(resized_icon, (icon_x, icon_y), mask=final_mask)

    def _draw_app_shortcut_title(self):
        icon_title_pos = (662, 1414)
        icon_title_text_size = 36
        icon_title_color = 0xFFFFFF
        max_title_width = 230

        font = self._create_font(icon_title_text_size)
        ellipsized_app_name = self._ellipsize_line(self.app_name, icon_title_text_size, max_title_width)
        self.screen_draw.text(icon_title_pos, ellipsized_app_name, icon_title_color, font=font, anchor='mm')

    def _draw_notification(self):
        self._draw_notification_app_name()
        self._draw_notification_title()
        self._draw_notification_icon()
        self._draw_notification_text()

    def _draw_notification_app_name(self):
        pos = (179, 224)
        font_size = 32
        max_app_name_width = 630
        text_color = 0x40434b

        ellipsized_app_name = self._ellipsize_line(self.app_name, font_size, max_app_name_width)
        notification_title = f"{ellipsized_app_name} • now"
        self.screen_draw.text(pos, notification_title, text_color, font=self._create_font(font_size), anchor='lt')

    def _draw_notification_title(self):
        pos = (179, 308)
        font_size = 41
        max_width = 630
        text_color = 0x1a1b20

        ellipsized_app_name = self._ellipsize_line(self.app_name, font_size, max_width)
        self.screen_draw.text(pos, ellipsized_app_name, text_color, font=self._create_font(font_size), anchor='lt')

    def _draw_notification_icon(self):
        notification_circle_pos = (84, 205)
        notification_circle_size = 62
        notification_circle_bounds = (
            notification_circle_pos[0],
            notification_circle_pos[1],
            notification_circle_pos[0] + notification_circle_size,
            notification_circle_pos[1] + notification_circle_size
        )
        self.screen_draw.ellipse(notification_circle_bounds, fill=self.notification_icon_color)

        notification_icon: Image.Image = Image.open(io.BytesIO(self.notification_icon_bytes))
        notification_icon = utils.crop_center_square(notification_icon)
        notification_icon_size = int(notification_circle_size * math.sin(math.radians(45)))
        notification_icon = notification_icon.resize((notification_icon_size, notification_icon_size))
        notification_icon = notification_icon.convert('RGBA')

        data = np.array(notification_icon)
        data[:, :, 0:3] = 255
        notification_icon = Image.fromarray(data, mode='RGBA')

        notification_icon_offset = int(notification_circle_size / 2 - notification_icon_size / 2)

        notification_icon_pos = (
            notification_circle_pos[0] + notification_icon_offset,
            notification_circle_pos[1] + notification_icon_offset
        )

        self.screen_template_copy.paste(notification_icon, notification_icon_pos, notification_icon)

    def _draw_notification_text(self):
        pos = (179, 372)
        max_text_width = 815
        font_size = 37
        text_spacing = 18
        text_color = 0x40434b

        font = self._create_font(font_size)
        ellipsized_notification_text = self._ellipsize_multiline_text(self.notification_text, font_size, 2, max_text_width)
        self.screen_draw.text(pos, ellipsized_notification_text, text_color, font=font, spacing=text_spacing)

    def _get_result_bytes(self):
        result_array = io.BytesIO()
        self.screen_template_copy.save(result_array, format='JPEG', quality=85)
        return result_array.getvalue()

    def _ellipsize_multiline_text(self, text: str, font_size: int, max_lines: int, max_width: int) -> str:
        src_lines = text.splitlines()[:max_lines]
        result_lines = []
        for line_num in range(0, max_lines):
            if line_num >= len(src_lines):
                break
            line = src_lines[line_num]
            ending = '…' if line_num == max_lines - 1 else ''
            trimmed_line, rest_line = self._ellipsize_line_ex(line, font_size, max_width, ending)
            result_lines.append(trimmed_line)
            if rest_line is not None:
                src_lines = src_lines[:line_num + 1] + [rest_line] + src_lines[line_num + 1:]
        return "\n".join(result_lines)

    def _ellipsize_line(self, line: str, font_size: int, max_width: int, ending='…') -> str:
        return self._ellipsize_line_ex(line, font_size, max_width, ending)[0]

    def _ellipsize_line_ex(self, line: str, font_size: int, max_width: int, ending='…') -> tuple[str, Optional[str]]:
        font = self._create_font(font_size)
        bounds = font.getbbox(line, anchor="lt")
        if bounds[2] <= max_width:
            return line, None
        min_length = 0
        max_length = len(line)
        while min_length < max_length:
            mid_length = (min_length + max_length) // 2
            trimmed_line = line[:mid_length] + ending
            bounds = font.getbbox(trimmed_line)
            if bounds[2] == max_width:
                max_length = mid_length + 1
                break
            elif bounds[2] > max_width:
                max_length = mid_length
            else:
                min_length = mid_length + 1
        trimmed_line = line[:max_length - 1] + ending
        rest_line = line[max_length - 1:]
        return trimmed_line, rest_line

    def _create_font(self, font_size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(self.font_path, font_size)
