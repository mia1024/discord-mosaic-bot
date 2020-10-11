from discord.ext import commands
import discord
from asyncio import sleep
from utils import validate_filename
from PIL import Image
import os
from art import gen_emoji_sequence
from credentials import MOSAIC_BOT_TOKEN
from typing import List
from emojis import get_emoji_by_rgb
import aiohttp
import re

bot = commands.Bot('|', None, max_messages=None, intents=discord.Intents(messages=True))

locks = set()
interrupted = set()
sent_msgs = {}


class lock_channel:
    def __init__(self, id):
        self.id = id
    
    async def __aenter__(self):
        while self.id in locks:
            await sleep(1.5)
        locks.add(self.id)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        locks.remove(self.id)


async def delete_messages(cid: int, msgs: List[int]):
    # the implementation in discord.py requires gateway intent
    # which makes it easier to just implement the API call myself
    if not msgs:
        return
    async with aiohttp.ClientSession() as session:
        if len(msgs) == 1:
            res = await session.delete(
                    f'https://discord.com/api/v8/channels/{cid}/messages/{msgs[0]}',
                    headers={
                        'Authorization': 'Bot ' + MOSAIC_BOT_TOKEN,
                    },
            )
            print(res.headers)
            print(res.status)
        else:
            await session.post(
                    f'https://discord.com/api/v8/channels/{cid}/messages/bulk-delete',
                    headers={
                        'Authorization': 'Bot ' + MOSAIC_BOT_TOKEN,
                    },
                    json={'messages': msgs}
            )
        # i don't actually care about the return code because
        # if MANAGE_MESSAGE permission isn't granted then whatever


def split_minimal(seq: str):
    
    res = []
    msg=''
    for line in seq.splitlines():
        line=re.sub(f'({get_emoji_by_rgb(255,255,255)}|{get_emoji_by_rgb(-1,-1,-1)})+\u200b?$','\u200b',line)
        if len(msg)+len(line)<2000:
            msg+=line+'\n'
        else:
            res.append(msg)
            msg=line+'\n'
    if msg:
        res.append(msg)
    return res


@bot.command()
async def show(ctx: commands.Context, *, raw_args: str = ''):
    async with lock_channel(ctx.channel.id):
        if ctx.message.id in interrupted:
            return
        
        if not raw_args:
            return
        args = raw_args.split()
        
        if args[0] == 'help':
            msg = await ctx.send('Please refer to https://mosaic.by.jerie.wang/reference for help')
            sent_msgs[ctx.message.id] = [msg.id]
            return
        
        large = False
        no_space = False
        light_mode = False
        try:
            if args[0] == 'large':
                large = True
                name = args[1]
            else:
                name = args[0]
            if 'nospace' in args or 'no space' in raw_args:
                no_space = True
            if 'light' in args:
                light_mode = True
        except IndexError:
            return
        
        await ctx.trigger_typing()
        if not validate_filename(name):
            msg = await ctx.send(f"Sorry, I don't know what an image of `{name}` looks like. "
                                 f"The names of all the images known to me contain only "
                                 f"alphanumeric characters, hyphens, and underscores")
            sent_msgs[ctx.message.id] = [msg.id]
            return
        
        if not os.path.exists(f'images/{name}.png'):
            msg = await ctx.send(f"Sorry, I don't know what an image of `{name}` looks like")
            sent_msgs[ctx.message.id] = [msg.id]
            return
        
        img = Image.open(f'images/{name}.png')
        if large and img.width > 27:
            # discord displays all lines above 27 emojis as inline
            msg = await ctx.send(
                f"Sorry, I can't send a large image of `{name}` because it's {img.width - 27} pixels too wide")
            sent_msgs[ctx.message.id] = [msg.id]
            return
        
        emojis = gen_emoji_sequence(img, large, no_space, light_mode)
        if no_space and img.width * img.height < 70 and not large:
            await ctx.send(emojis.strip())  # that should be exactly 2000 characters for a 69x1 image
            return
        
        if no_space and not large:
            messages = split_minimal(emojis)
        else:
            messages = emojis.splitlines()
        
        sent = []
        for i in range(len(messages)):
            if ctx.message.id in interrupted:
                break
            sent.append((await ctx.send(messages[i])).id)
            if i != len(messages) - 1:
                await ctx.trigger_typing()
                await sleep(1)
            # while discord.py handles all the rate limits
            # it looks better to have a uniformed speed
        
        if ctx.message.id in interrupted:
            interrupted.remove(ctx.message.id)
            await delete_messages(ctx.channel.id, sent)
        else:
            sent_msgs[ctx.message.id] = sent


@bot.event
async def on_raw_message_delete(e: discord.RawMessageDeleteEvent):
    if e.channel_id in locks:
        interrupted.add(e.message_id)
    elif e.message_id in sent_msgs:
        await delete_messages(e.channel_id, sent_msgs[e.message_id])


@bot.event
async def on_ready():
    print('Logged in as ' + bot.user.name + '#' + bot.user.discriminator)
    await bot.change_presence(activity=discord.Activity(name='|show help', type=discord.ActivityType.playing))

if __name__ == '__main__':
    bot.run(MOSAIC_BOT_TOKEN)
