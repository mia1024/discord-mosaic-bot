import pathlib
from hashlib import md5
import os
try:
    import PIL.Image
    PIL.Image.MAX_IMAGE_PIXELS = 4000 ** 2
except ImportError:
    # this file is also imported during setup.py install, which might mean
    # that none of the deps are installed yet
    pass

if p:=os.environ.get('BASE_PATH'):
    BASE_PATH=pathlib.Path(p).resolve()
else:
    BASE_PATH=pathlib.Path(__file__).resolve().parent.parent
IMAGE_DIR = BASE_PATH/'images'
__version__ = '0.1'
# versions will be numbered after the golden ratio, like how LaTeX does it

hasher = md5()
for root, dir, files in os.walk(pathlib.Path(__file__).resolve().parent):
    for fp in files:
        if fp.endswith('.py'):
            with open(BASE_PATH / root / fp, 'rb') as f:
                hasher.update(f.read())

__build__ = hasher.hexdigest()

__all__ = [
    '__version__',
    '__build__',
    'BASE_PATH',
    'IMAGE_DIR',
]
