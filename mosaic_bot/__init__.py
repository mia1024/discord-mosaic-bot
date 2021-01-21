import pathlib
import PIL.Image

BASE_PATH = pathlib.Path(__file__).resolve().parent.parent
IMAGE_DIR = './new_images/'
__version__ = '0.1'
# versions will be numbered after the golden ratio, like how LaTeX does it


PIL.Image.MAX_IMAGE_PIXELS = 4000 ** 2

__all__ = ['BASE_PATH', 'IMAGE_DIR']
