from PIL import Image
from mosaic_bot.image import downsample, gen_image_preview, gen_emoji_sequence
from mosaic_bot.cv import find_scale
from mosaic_bot.credentials import MOSAIC_BOT_TOKEN
import requests
import random
import time
from mosaic_bot.emojis import get_emoji_by_rgb

API_ENDPOINT='https://discord.com/api/v8'

name='kirby.png'#input('Image filename? ')

img=Image.open(name)
scale=find_scale(img)
print(f'Downsampling at {scale}x')
img=downsample(img.crop(img.getbbox()),find_scale(img))
channel=763789293507575851#input('Channel id? ')
token='Bot '+MOSAIC_BOT_TOKEN

gen_emoji_sequence(img)

# for i in range(len(lines:=gen_emoji_sequence(img).splitlines())):
#     req=requests.post(
#             API_ENDPOINT+f'/channels/{channel}/messages',
#             json={'content':lines[i]},
#             headers={
#                 'Authorization':token,
#                 #'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.123 Safari/537.36'
#             }
#     )
#
#     req.raise_for_status()
#     time.sleep(1.5)

import random
emj=[]
for i in range(36):
    emj.append(get_emoji_by_rgb(random.randint(0,255),random.randint(0,255),random.randint(0,255)))

req=requests.post(
        API_ENDPOINT+f'/channels/{channel}/messages',
        json={'content':' '.join(emj)},
        headers={
            'Authorization':token,
            #'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.123 Safari/537.36'
        }
)
