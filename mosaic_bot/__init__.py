import pathlib
import os
try:
    import PIL.Image
    PIL.Image.MAX_IMAGE_PIXELS = 4000 ** 2
except ImportError:
    # this file is also imported during setup.py install, which might mean
    # that none of the deps are installed yet
    pass

if p:=os.environ.get('DATA_PATH'):
    DATA_PATH=pathlib.Path(p).resolve()
else:
    DATA_PATH=pathlib.Path(__file__).resolve().parent.parent/'data'
IMAGE_DIR = DATA_PATH / 'images'
__version__ = '1.6'
# versions will be numbered after the golden ratio, like how LaTeX does it

from .__build__ import (build_hash as __build_hash__,
                        build_type as __build_type__,
                        build_time as __build_time__)

__all__ = [
    '__version__',
    '__build_hash__',
    '__build_type__',
    'DATA_PATH',
    'IMAGE_DIR',
]
