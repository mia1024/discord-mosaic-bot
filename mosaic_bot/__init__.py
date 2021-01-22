import pathlib
import PIL.Image
from hashlib import md5
import os

BASE_PATH = pathlib.Path(__file__).resolve().parent.parent
IMAGE_DIR = 'new_images/'
__version__ = '0.1'
# versions will be numbered after the golden ratio, like how LaTeX does it

hasher = md5()
for root, dir, files in os.walk(BASE_PATH / 'mosaic_bot'):
    for fp in files:
        if fp.endswith('.py'):
            with open(BASE_PATH / root / fp, 'rb') as f:
                hasher.update(f.read())

__build__ = hasher.hexdigest()

PIL.Image.MAX_IMAGE_PIXELS = 4000 ** 2

__all__ = [
    '__version__',
    '__build__',
    'BASE_PATH',
    'IMAGE_DIR',
]
