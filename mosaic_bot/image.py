import base64
import io

import numpy as np
from PIL import Image

from mosaic_bot.color import Color
from mosaic_bot.cv import find_scale
from mosaic_bot.emojis import get_emoji_by_rgb


def downsample(img: Image.Image, scale: int = None) -> Image.Image:
    if not scale:
        scale = find_scale(img)
    return img.resize((img.size[0] // scale, img.size[1] // scale), Image.NEAREST)


def crop(img: Image.Image) -> Image.Image:
    return img.crop(img.getbbox())


# single line emojis will be rendered small >= 28

def gen_emoji_sequence(img: Image.Image, large=False, no_space=False, light_mode=False):
    # all images passed in should be preprocessed images
    # ie. RGBA, downsampled
    res = ''
    arr = np.array(img)
    for row in arr:
        for col in row:
            r, g, b, a = col
            if a == 0:
                if light_mode:
                    emoji = get_emoji_by_rgb(255, 255, 255)
                else:
                    emoji = get_emoji_by_rgb(-1, -1, -1)
            else:
                emoji = get_emoji_by_rgb(r, g, b)
            res += emoji
            if not no_space:
                res += ' '
        if not large:
            res += '\u200b'
        res += '\n'
    return res


def gen_image_12bit_approx(img: Image.Image):
    new_image = Image.new('RGBA', img.size)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    arr = np.array(img)
    for y, row in enumerate(arr):
        for x, col in enumerate(row):
            r, g, b, a = col
            new_image.putpixel((x, y), (*Color(r, g, b).approx_12bit(), 255 if a else 0))
    return new_image


def gen_image_preview(img: Image.Image):
    preview = gen_image_12bit_approx(img)
    scale = min(1000 // img.width, 1000 // img.height)
    return preview.resize((img.width * scale, img.height * scale), Image.NEAREST)


def image_to_data(img: Image.Image, approx_12bit: bool):
    if approx_12bit:
        img = gen_image_12bit_approx(img)
    bio = io.BytesIO()
    img.save(bio, 'png')
    bio.seek(0)
    b64 = base64.b64encode(bio.read()).decode('ascii')
    return 'data:image/png;base64,' + b64


__all__ = ['gen_image_preview', 'gen_emoji_sequence', 'downsample', 'crop', 'image_to_data']
