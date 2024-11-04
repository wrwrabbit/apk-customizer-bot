import io
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import utils


def make_screen_example(icon_bytes: bytes, name: str) -> bytes:
    icon_x = 587
    icon_y = 1198
    icon_width = 156
    text_x = 667
    text_y = 1406
    text_size = 36

    screen_template = Image.open('resources/screen.png').copy()
        
    mask_im = Image.new("L", screen_template.size, 0)
    draw = ImageDraw.Draw(mask_im)
    draw.ellipse((icon_x, icon_y, icon_x + icon_width, icon_y + icon_width), fill=255)

    mask_array = io.BytesIO()
    mask_im.save(mask_array, format='png')
    mask_im_blur = mask_im.filter(ImageFilter.GaussianBlur(1))

    icon = Image.open(io.BytesIO(icon_bytes))

    screen_copy2 = screen_template.copy()
    resized_icon = utils.crop_center_rectangle(icon).resize((icon_width, icon_width))
    screen_copy2.paste(resized_icon, (icon_x, icon_y))

    screen_template.paste(screen_copy2, (0, 0), mask=mask_im_blur)

    font = ImageFont.truetype("resources/Roboto-Regular.ttf", text_size)
    screen_draw = ImageDraw.Draw(screen_template)
    elipsized_name = name if len(name) <= 11 else name[:10] + '…'
    screen_draw.text((text_x, text_y), elipsized_name, (255, 255, 255), font=font, anchor='mm')

    result_array = io.BytesIO()
    screen_template.save(result_array, format='JPEG', quality=85)
    return result_array.getvalue()