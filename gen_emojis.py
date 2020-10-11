from palette import VGA_13H, RGB_4096
import PIL.Image
import os
from color import int_to_rgb

os.chdir(os.path.abspath(os.path.dirname(__file__)))

try:
    os.mkdir('emojis')
except FileExistsError:
    if not os.path.isdir('emojis'):
        pass

for color in VGA_13H:
    img=PIL.Image.new('RGB', (256,256), int_to_rgb(color))
    img.save(f'emojis/{hex(color)[2:].lower().zfill(6)}.jpg')

for color in RGB_4096:
    img=PIL.Image.new('RGB', (256,256), int_to_rgb(color))
    h=hex(color)[2:].lower().zfill(6)
    img.save(f'emojis/{h[0]}{h[2]}{h[4]}.jpg')
