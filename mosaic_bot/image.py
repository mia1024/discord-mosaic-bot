import base64
import io

import numpy as np
from scipy import fft
from PIL import Image

from mosaic_bot.color import Color
from mosaic_bot.cv import find_scale
from mosaic_bot.emojis import get_emoji_by_rgb


def downsample(img: Image.Image, scale: int = None) -> Image.Image:
    if not scale:
        scale = find_scale(img, debug=True)
    return img.resize((img.size[0] // scale, img.size[1] // scale), Image.NEAREST)


def crop(img: Image.Image) -> Image.Image:
    return img.crop(img.getbbox())


def preprocess(img: Image.Image, debug: bool = False, scale=None):
    if scale is None:
        if debug:
            scale, data = find_scale(img, True)
        else:
            scale = find_scale(img)
    img = crop(downsample(img, scale)).convert('RGBA')
    try:
        return img, data
    except NameError:
        return img


# single line emojis will be rendered small >= 28

def gen_emoji_sequence(img: Image.Image, large=False, no_space=False):
    # all images passed in should be preprocessed images
    # ie. RGBA, downsampled
    res = ''
    arr = np.array(img)
    for row in arr:
        for col in row:
            r, g, b, a = col
            if a == 0:
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


def gen_icon():
    img = Image.new("RGBA", (128, 128))
    
    for x in range(128):
        for y in range(128):
            x_eff = x // 8
            y_eff = 15 - y // 8  # flip y-axis to math mode
            
            r = x_eff
            g = 9
            b = y_eff
            
            img.putpixel((x, y), ((r << 4) + r, (g << 4) + g, (b << 4) + b, 255))
    return img


def gen_gradient(r: int = None, g: int = None, b: int = None):
    img = Image.new("RGBA", (16, 16))
    r0, g0, b0 = r, g, b
    for x in range(16):
        for y in range(16):
            x_eff = x
            y_eff = 15 - y  # flip y-axis to match math coordinate
            
            if r0 is not None:
                g = x_eff
                b = y_eff
            elif g0 is not None:
                r = x_eff
                b = y_eff
            elif b0 is not None:
                r = x_eff
                g = y_eff
            else:
                raise ValueError("At least one of the r,g,b must be specified")
            img.putpixel((x, y), ((r << 4) + r, (g << 4) + g, (b << 4) + b, 255))
    return img


def hash_image(img: Image.Image) -> int:
    # implemented based on the pHash algorithm in
    # http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    # however, since all the images here are already pixel art, no resizing is
    # necessary
    # Additional ref: https://www.phash.org/docs/pubs/thesis_zauner.pdf
    
    img = img.convert('L')
    arr = np.asarray(img)
    transformed = fft.dct(fft.dct(arr, axis=0, norm='ortho'), axis=1, norm='ortho')
    lowest_freq = transformed[1:9, 1:9]
    bits = 1 * (lowest_freq > np.average(lowest_freq)).flatten()
    return int(''.join(map(str, bits)).zfill(64), 2)


def diff_hash(h1: int, h2: int) -> int:
    return bin(h1 ^ h2).count('1')


__all__ = [
    'gen_image_preview',
    'gen_emoji_sequence',
    'downsample',
    'crop',
    'image_to_data',
    'hash_image',
    'diff_hash'
]
