from emojis import get_emoji_by_rgb
from PIL import Image
import numpy as np
from color import Color
from cv import find_scale


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


def gen_emoji_preview(img: Image.Image):
    preview = Image.new(img.mode, img.size)
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGBA')
    arr = np.array(img)
    if img.mode == 'RGBA':
        for y, row in enumerate(arr):
            for x, col in enumerate(row):
                r, g, b, a = col
                preview.putpixel((x, y), (*Color(r, g, b).approx_12bit(), 255 if a else 0))
    else:
        for y, row in enumerate(arr):
            for x, col in enumerate(row):
                r, g, b = col
                preview.putpixel((x, y), tuple(Color(r, g, b).approx_12bit()))
    return preview.resize((img.width * 40, img.height * 40), Image.NEAREST)


__all__ = ['gen_emoji_preview', 'gen_emoji_sequence', 'downsample', 'crop']
