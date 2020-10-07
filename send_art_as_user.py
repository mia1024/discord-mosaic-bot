from PIL import Image
from art import downsample, gen_emoji_preview, gen_emoji_sequence
import requests
import random
import time

API_ENDPOINT='https://discord.com/api/v8'

name=input('Image filename? ')

img=Image.open(name)
img=downsample(img.crop(img.getbbox()),int(input('Downsample scale? ')))
gen_emoji_preview(img).show()
channel=input('Channel id? ')
token=input('Auth token? ')
for line in gen_emoji_sequence(img).splitlines():
    req=requests.post(
            API_ENDPOINT+f'/channels/{channel}/messages',
            json={'content':line},
            headers={
                'Authorization':token,
                'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.123 Safari/537.36'
            }
    )
    time.sleep(random.randint(1,2)+random.random())
