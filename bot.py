import logging.handlers
import os
import random
import re
from asyncio import sleep
from dataclasses import dataclass
from typing import List, Union

import aiohttp
import discord
from PIL import Image
from discord.ext import commands

from image import gen_emoji_sequence
from credentials import MOSAIC_BOT_TOKEN
from emojis import get_emoji_by_rgb
from utils import validate_filename

# ---------------- logging ----------------

try:
    os.mkdir('/var/log/mosaic')
except FileExistsError:
    pass

handler = logging.handlers.TimedRotatingFileHandler(
        filename='/var/log/mosaic/bot.log',
        when='D',
        interval=7,
        backupCount=100,
        encoding='utf8',
        delay=True,
)
handler.setFormatter(
        logging.Formatter('[%(asctime)s]  %(levelname)-7s %(name)s: %(message)s'))
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# ---------------- logging --------------

bot = commands.Bot('|', None, max_messages=None, intents=discord.Intents(messages=True))

locks = set()
interrupted = set()
sent_msgs = {}

HELP_TEXT = """
```
|show image_name [with space] [large] [nopadding|no padding]
|minecraft image_name [with space] [large] [nopadding|no padding]
```
For a more detailed description, please visit https://mosaic.by.jerie.wang/references.
"""


class lock_channel:
    def __init__(self, id):
        self.id = id
    
    async def __aenter__(self):
        while self.id in locks:
            await sleep(1.5)
        locks.add(self.id)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        locks.remove(self.id)


async def delete_messages(cid: int, msgs: List[int], bulk=True):
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
        elif bulk:
            res = await session.post(
                    f'https://discord.com/api/v8/channels/{cid}/messages/bulk-delete',
                    headers={
                        'Authorization': 'Bot ' + MOSAIC_BOT_TOKEN,
                    },
                    json={'messages': msgs}
            )
            if res.status != 204:
                await delete_messages(cid, msgs, bulk=False)
                # try again using the other end point
                # because MANAGE_MESSAGES permission
                # may not present
        else:
            random.shuffle(msgs)
            for mid in msgs:
                await session.delete(
                        f'https://discord.com/api/v8/channels/{cid}/messages/{mid}',
                        headers={
                            'Authorization': 'Bot ' + MOSAIC_BOT_TOKEN,
                        },
                )
                await sleep(0.5)


class EmojiSequenceTooLong(Exception): pass


def split_minimal(seq: str, strip_end=True):
    res = []
    msg = ''
    for line in seq.splitlines():
        if len(line) > 2000:
            raise EmojiSequenceTooLong
        if strip_end:
            line = re.sub(f'({get_emoji_by_rgb(255, 255, 255)}|{get_emoji_by_rgb(-1, -1, -1)})+\u200b?$', '\u200b',
                          line)
        if len(msg) + len(line) < 2000:
            msg += line + '\n'
        else:
            res.append(msg)
            msg = line + '\n'
    if msg:
        res.append(msg)
    return res


@dataclass
class ShowOptions:
    name: str = None
    large: bool = False
    no_space: bool = True
    strip_end: bool = False
    light_mode: bool = False


def parse_opt(s: str):
    l = s.split()
    i = 0
    opts = ShowOptions()
    while i < len(l):
        set_name = True
        if l[i] == 'large':
            opts.large = True
            set_name = False
        if l[i] == 'light':
            opts.light_mode = True
            set_name = False
        if l[i] == 'nopadding':
            opts.strip_end = True
            set_name = False
        if l[i] == 'no':
            if i < len(l) - 1 and l[i + 1] == 'padding':
                opts.strip_end = True
                i += 1
                set_name = False
        if l[i] == 'with':
            if i < len(l) - 1 and l[i + 1] == 'space':
                opts.no_space = False
                i += 1
                set_name = False
        if opts.name is None and set_name:
            opts.name = l[i]
        i += 1
    return opts


@bot.command()
async def show(ctx: commands.Context, *, raw_or_parsed_args: Union[str, ShowOptions] = ''):
    async with lock_channel(ctx.channel.id):
        if ctx.message.id in interrupted:
            return
        if isinstance(raw_or_parsed_args, str):
            raw_args = raw_or_parsed_args
            if not raw_args:
                return
            args = raw_args.split()
            
            if args and args[0] == 'help':
                msg = await ctx.send(HELP_TEXT)
                sent_msgs[ctx.message.id] = [msg.id]
                return
            
            opts = parse_opt(raw_args)
            if not opts.name:
                m = 'You want me to show a '
                if opts.large:
                    m += 'large '
                if not opts.no_space:
                    m += 'with space '
                    if not opts.strip_end:
                        m += 'no padding '
                if opts.light_mode:
                    m += 'light mode '
                m += 'image of...what?'
                msg = await ctx.send(m)
                sent_msgs[ctx.message.id] = [msg.id]
                return
        else:
            opts = raw_or_parsed_args
        
        await ctx.trigger_typing()
        if not validate_filename(opts.name):
            msg = await ctx.send(f"Sorry, I don't know what an image of `{opts.name}` looks like. "
                                 f"The names of all the images known to me contain only "
                                 f"alphanumeric characters, hyphens, and underscores")
            sent_msgs[ctx.message.id] = [msg.id]
            return
        
        if not os.path.exists(f'images/{opts.name}.png'):
            msg = await ctx.send(f"Sorry, I don't know what an image of `{opts.name}` looks like")
            sent_msgs[ctx.message.id] = [msg.id]
            return
        
        img = Image.open(f'images/{opts.name}.png')
        if opts.large and img.width > 27:
            # discord displays all lines above 27 emojis as inline
            msg = await ctx.send(
                    f"Sorry, I can't send a large image of `{opts.name}` because it's {img.width - 27} pixels too wide")
            sent_msgs[ctx.message.id] = [msg.id]
            return
        
        if img.width > 80:
            # this shouldn't happen because no image wider than 80 should be
            # uploaded but we check it anyway just to be safe
            msg = await ctx.send(
                    f"Sorry, I can't send an image of `{opts.name}` because it's {img.width - 80} pixels too wide")
            sent_msgs[ctx.message.id] = [msg.id]
            return
        
        emojis = gen_emoji_sequence(img, opts.large, opts.no_space, opts.light_mode)
        try:
            if opts.no_space and not opts.large:
                messages = split_minimal(emojis, opts.strip_end)
            else:
                messages = emojis.splitlines()
                for m in messages:
                    if len(m) > 2000: raise EmojiSequenceTooLong
        except EmojiSequenceTooLong:
            msg = await ctx.send(
                    f"Sorry, I can't send an image of `{opts.name}` because it's too wide")
            sent_msgs[ctx.message.id] = [msg.id]
            return
        
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


@bot.command()
async def minecraft(ctx, *, raw_args=''):
    opts = parse_opt(raw_args)
    if not opts.name:
        msg = await ctx.send('You want me to show a `minecraft` what?')
        sent_msgs[ctx.message.id] = [msg.id]
        return
    opts.name = 'minecraft_' + opts.name
    await show(ctx, raw_or_parsed_args=opts)


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
