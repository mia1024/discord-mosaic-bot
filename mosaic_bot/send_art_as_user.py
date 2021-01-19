from PIL import Image
from mosaic_bot.image import downsample, gen_emoji_sequence
from mosaic_bot.cv import find_scale
from mosaic_bot.credentials import MOSAIC_BOT_TOKEN
import requests
from mosaic_bot.emojis import get_emoji_by_rgb
from mosaic_bot import BASE_PATH

API_ENDPOINT = 'https://discord.com/api/v8'

name = input('Image filename? ')

img = Image.open(BASE_PATH / 'images' / name)
scale = find_scale(img)
print(f'Downsampling at {scale}x')
img = downsample(img.crop(img.getbbox()), find_scale(img))
channel = input('Channel id? ')
token = 'Bot ' + MOSAIC_BOT_TOKEN

gen_emoji_sequence(img)

import random

emj = []
for i in range(36):
    emj.append(get_emoji_by_rgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

req = requests.post(
        API_ENDPOINT + f'/channels/{channel}/messages',
        json={'content': ' '.join(emj)},
        headers={
            'Authorization': token,
        }
)
