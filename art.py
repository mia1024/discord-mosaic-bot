from emojis import get_emoji_by_rgb, find_closest_color
from PIL import Image
import numpy as np
from utils import rgb_to_int,int_to_rgb

def downsample(img: Image.Image, scale: int = None):
    if not scale:
        for n in range(img.size[0] // 20):
            scale = img.size[0] // 20
            if (img.size[0] / scale).is_integer() and img.size[0] / scale <= 20:
                scale = 20 - n
        else:
            scale = 20
    
    return img.resize((img.size[0] // scale, img.size[1] // scale), Image.NEAREST)


bg = get_emoji_by_rgb(*int_to_rgb(0x37393f))

def gen_emoji_sequence(img:Image.Image):
    res=''
    if img.mode=='RGBA':
        arr = np.array(img)
        for row in arr:
            for col in row:
                r, g, b, a = col
                if a == 0:
                    emoji = bg
                else:
                    emoji = get_emoji_by_rgb(r,g,b)
                res+=emoji
            res+='\n'
    else:
        if img.mode!='RGB':
            arr=np.array(img.convert('RGB'))
        else:
            arr=np.array(img)
        for row in arr:
            for col in row:
                emoji = get_emoji_by_rgb(*col)
                res+=emoji
            res+='\n'
    return res

def gen_emoji_preview(img:Image.Image):
    preview=Image.new(img.mode,img.size)
    if img.mode=='RGBA':
        arr = np.array(img)
        for y,row in enumerate(arr):
            for x,col in enumerate(row):
                r, g, b, a = col
                preview.putpixel((x,y),(*find_closest_color(r,g,b),255 if a else 0))
    else:
        if img.mode!='RGB':
            arr=np.array(img.convert('RGB'))
        else:
            arr=np.array(img)
        for y,row in enumerate(arr):
            for x,col in enumerate(row):
                r, g, b = col
                preview.putpixel((x,y),find_closest_color(r,g,b))
    return preview



