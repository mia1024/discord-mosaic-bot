import logging.handlers
import os
import random
import time
from asyncio import sleep
import asyncio
from dataclasses import dataclass
from typing import List, Union, Dict
import aiohttp
import discord
from PIL import Image
from discord.ext import commands
import re

from mosaic_bot.credentials import MOSAIC_BOT_TOKEN
from mosaic_bot.emojis import get_emoji_by_rgb
from mosaic_bot.image import gen_emoji_sequence, gen_gradient, image_to_data
from .utils import validate_filename
from mosaic_bot import BASE_PATH

# ---------------- logging ----------------

try:
    os.mkdir('/var/log/mosaic')
except FileExistsError:
    pass

handler = logging.handlers.TimedRotatingFileHandler(
        filename='/var/log/mosaic/mosaic-bot.discord-gateway.log',
        when='D',
        interval=7,
        backupCount=100,
        encoding='utf8',
        delay=True,
)
handler.setFormatter(
        logging.Formatter('[%(asctime)s]  %(levelname)-7s %(name)s: %(message)s'))
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.DEBUG)
discord_logger.addHandler(handler)

handler = logging.handlers.TimedRotatingFileHandler(
        filename='/var/log/mosaic/mosaic-bot.log',
        when='D',
        interval=7,
        backupCount=100,
        encoding='utf8',
        delay=True,
)
handler.setFormatter(
        logging.Formatter('[%(asctime)s]  %(levelname)-7s %(name)s: %(message)s'))
logger = logging.getLogger('mosaic-bot')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# ---------------- end logging --------------

bot = commands.Bot('|', None, max_messages=None, intents=discord.Intents(messages=True))

HELP_TEXT = """
```
|show image_name [with space] [large] [nopadding|no padding]
|minecraft image_name [with space] [large] [nopadding|no padding]
```
For a more detailed description, please visit https://mosaic.by.jerie.wang/references.
"""

ICON = (f := open(BASE_PATH / 'icon.png', 'br')).read()
f.close()


async def get_webhook(channel_id: int) -> discord.Webhook:
    channel: discord.TextChannel = await bot.fetch_channel(channel_id)
    webhooks: List[discord.Webhook] = await channel.webhooks()
    for wh in webhooks:
        if wh.user == bot.user:
            webhook = wh
            break
    else:
        webhook = await channel.create_webhook(name=bot.user.name, avatar=ICON,
                                               reason='Created webhook for sending emojis')
    return webhook


class RequestInterrupted(Exception): pass


class EmojiSequenceTooLong(Exception): pass


class MessageManager:
    channel_locks = set()
    active_managers = {}
    
    def __init__(self, ctx: commands.Context):
        self.channel = ctx.channel.id
        self.destination = ctx
        self.message_ids: List[int] = []
        self.requesting_message: int = ctx.message.id
        self.requester: discord.User = ctx.message.author.id
        self.active_managers[self.requesting_message] = self
        self.is_interrupted = False
        self._queue = []
        self.rtt = []  # round trip time
        self.show_confirmation = False
    
    async def __aenter__(self):
        while self.channel in self.channel_locks:
            await sleep(1.5)
        self.channel_locks.add(self.channel)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.show_confirmation:
            # a confirmation message used to toggle off the typing indicator,
            # if triggered
            
            if exc_type is None:
                confirmation = await self.destination.send(f'<@{self.requester}> Request completed')
            else:
                confirmation = await self.destination.send(f'<@{self.requester}> Request interrupted')
            await confirmation.delete(delay=5)
        
        self.channel_locks.remove(self.channel)
        # TODO: write sent messages to db
        del self.active_managers[self.requesting_message]
        if exc_type == RequestInterrupted:
            await delete_messages(self.channel, self.message_ids)
            return True
    
    def queue(self, *args, use_webhook=False, **kwargs):
        self._queue.append((args, {"use_webhook": use_webhook, **kwargs}))
    
    def get_embed(self, current, url):
        total = len(self._queue)
        if not self.rtt:
            rtt = 0
            avg_rtt = 0
        else:
            rtt = self.rtt[-1]
            avg_rtt = sum(self.rtt) / len(self.rtt)
        
        if total > 30:
            delay = 1.5
        else:
            delay = 1
        
        return discord.Embed.from_dict(
                {
                    'description': 'Delete the requesting message to interrupt',
                    'fields': [
                        {
                            'name': 'ETA',
                            'value': f'{round((total - current) * delay + avg_rtt, 2)}s',
                            'inline': 'true'
                        },
                        {
                            'name': 'Latency',
                            'value': f'{round(rtt, 2)}s',
                            'inline': 'true'
                        },
                        {
                            'name': 'Progress',
                            'value': f'{round(current / total * 100, 2)}%',
                            'inline': 'true'
                        },
                    ],
                }
        )
    
    async def commit_queue(self, img: Image.Image):
        if len(self._queue) <= 5:
            self.show_confirmation = False
            for msg in self._queue:
                asyncio.ensure_future(self.send(*msg[0], **msg[1]))
                # i think this shouldn't cause messages to deliver out of
                # order...i think
        else:
            self.show_confirmation = True
            start = time.time()
            status = await self.destination.send(embed=self.get_embed(0, ''))
            self.rtt.append(time.time() - start)
            # apparently webhook shares the same rate limit???
            
            if len(self._queue) > 30:
                delay = 1.5
            else:
                delay = 1
            try:
                for i, msg in enumerate(self._queue[:-1]):
                    start = time.time()
                    await self.send(*msg[0], **msg[1], trigger_typing=True)
                    
                    rtt = time.time() - start
                    self.rtt.append(rtt)
                    
                    # asyncio.ensure_future(
                    #         status.edit(embed=self.get_embed(i + 1, ''))
                    # )
                    # don't use await since this can be executed while sleeping
                    
                    await sleep(delay - rtt)
                    # while discord.py handles all the rate limits
                    # it looks better to have a uniformed speed
                
                msg = self._queue[-1]
                await self.send(*msg[0], **msg[1])
            finally:
                await status.delete()
    
    async def send(self, *args, trigger_typing=False, use_webhook=False, **kwargs):
        if use_webhook:
            wh = await get_webhook(self.channel)
            msg = await wh.send(*args, wait=True)
        else:
            msg = await self.destination.send(*args, **kwargs)
        self.message_ids.append(msg.id)
        
        if self.is_interrupted:
            # raise exception after sending a message to toggle off the typing
            # indicator. this exception will be caught by __aexit__() of this
            # class
            raise RequestInterrupted
        
        if trigger_typing:
            await self.destination.trigger_typing()
        return msg
    
    def interrupt(self):
        self.is_interrupted = True
    
    @classmethod
    def message_deleted(cls, m_id: int):
        if m_id in cls.active_managers:
            cls.active_managers[m_id].interrupt()
        
        # TODO: check db for sent messages and delete all


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


def split_minimal(seq: str, strip_end=True):
    res = []
    msg = ''
    for line in seq.splitlines():
        if len(line) > 2000:
            raise EmojiSequenceTooLong
        if strip_end:
            line = re.sub(f'({get_emoji_by_rgb(-1, -1, -1)})+\u200b?$', '\u200b', line)
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
    strip_end: bool = True


def parse_opt(s: str):
    l = s.split()
    i = 0
    opts = ShowOptions()
    while i < len(l):
        set_name = True
        if l[i] == 'large':
            opts.large = True
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
    async with MessageManager(ctx) as manager:
        if isinstance(raw_or_parsed_args, str):
            raw_args = raw_or_parsed_args
            if not raw_args:
                return
            args = raw_args.split()
            
            if args and args[0] == 'help':
                await manager.send(HELP_TEXT)
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
                m += 'image of...what?'
                await manager.send(m)
                return
        else:
            opts = raw_or_parsed_args
        
        if not validate_filename(opts.name):
            await manager.send(f"Sorry, I don't know what an image of `{opts.name}` looks like. "
                               f"The names of all the images known to me contain only "
                               f"alphanumeric characters, hyphens, and underscores")
            return
        
        if not os.path.exists(BASE_PATH / f'images/{opts.name}.png'):
            await manager.send(f"Sorry, I don't know what an image of `{opts.name}` looks like")
            return
        
        img = Image.open(BASE_PATH / f'images/{opts.name}.png')
        if opts.large and img.width > 27:
            # discord displays all lines above 27 emojis as inline
            await manager.send(
                    f"Sorry, I can't send a large image of `{opts.name}` because it's {img.width - 27} pixels too wide")
            return
        
        if img.width > 80:
            # this shouldn't happen because no image wider than 80 should be
            # uploaded but we check it anyway just to be safe
            await manager.send(
                    f"Sorry, I can't send an image of `{opts.name}` because it's {img.width - 80} pixels too wide")
            return
        
        emojis = gen_emoji_sequence(img, opts.large, opts.no_space)
        try:
            if opts.no_space and not opts.large:
                messages = split_minimal(emojis, opts.strip_end)
            else:
                messages = emojis.splitlines()
                for m in messages:
                    if len(m) > 2000: raise EmojiSequenceTooLong
        except EmojiSequenceTooLong:
            await manager.send(
                    f"Sorry, I can't send an image of `{opts.name}` because it's too wide")
            return
        for i in range(len(messages)):
            manager.queue(messages[i], use_webhook=True)
        await manager.commit_queue(img)


@bot.command()
async def minecraft(ctx, *, raw_args=''):
    opts = parse_opt(raw_args)
    if not opts.name:
        async with MessageManager(ctx) as manager:
            await manager.send('You want me to show a `minecraft` what?')
            return
    opts.name = 'minecraft_' + opts.name
    await show(ctx, raw_or_parsed_args=opts)


@bot.command()
async def gradient(ctx: commands.Context, *, raw_args=''):
    async with MessageManager(ctx) as manager:
        opts = parse_opt(raw_args)
        c = re.search(r'\b(?P<c>[rgb]|red|green|blue)=(?P<v>\d{1,2})\b', raw_args)
        if c is None:
            await manager.send("You need to specify a base color because I can't send a 3D image")
            return
        if not 0 <= int(c.group('v')) <= 15:
            await manager.send("You see, I only know 16 colors so I can't do that")
            return
        color = {c.group('c')[0]: int(c.group('v'))}
        img = gen_gradient(**color)
        emojis = gen_emoji_sequence(img, opts.large, opts.no_space)
        if opts.large:
            seq = emojis.splitlines()
            for msg in seq:
                manager.queue(msg, use_webhook=True)
        else:
            for i in range(4):
                manager.queue('\n'.join(emojis.splitlines()[i * 4:i * 4 + 4]), use_webhook=True)
        await manager.commit_queue()


@bot.event
async def on_raw_message_delete(e: discord.RawMessageDeleteEvent):
    MessageManager.message_deleted(e.message_id)


@bot.event
async def on_ready():
    print('Logged in as ' + bot.user.name + '#' + bot.user.discriminator)
    await bot.change_presence(activity=discord.Activity(name='|show help', type=discord.ActivityType.playing))
