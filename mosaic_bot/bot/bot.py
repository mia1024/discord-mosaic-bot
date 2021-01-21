import asyncio
import logging.handlers
import os
import random
import re
import time
from asyncio import sleep
from dataclasses import dataclass
from typing import List, Union

import aiohttp
import discord
from PIL import Image
from discord.ext import commands

from mosaic_bot import BASE_PATH, db, __version__
from mosaic_bot.credentials import MOSAIC_BOT_TOKEN
from mosaic_bot.emojis import get_emoji_by_rgb
from mosaic_bot.image import gen_emoji_sequence, gen_gradient

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

HELP_TEXT = f"""
This is mosaic bot, v{__version__}.

For a description of available commands, please visit https://mosaic.by.jerie.wang/references.

Commands:
```
|show image_name [:[large], [with space, [multiline|irc]]]
|delete (message_id|message_link)
|gradient (r|g|b|red|green|blue)=value
```
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
                                               reason='webhook is necessary for sending custom external emojis')
    return webhook


class RequestInterrupted(Exception): pass


class EmojiSequenceTooLong(Exception): pass


class MessageManager:
    channel_locks = set()
    active_managers = {}
    
    def __init__(self, ctx: commands.Context):
        self.channel = ctx.channel.id
        self.destination = ctx
        self.message_ids: list[int] = []
        self.requesting_message: int = ctx.message.id
        self.requester: int = ctx.message.author.id
        self.active_managers[self.requesting_message] = self
        self.is_interrupted = False
        self._queue = []
        self.rtt = []  # round trip time
        self.show_confirmation = False
        self.image_hash = None
    
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
                # using destination.send to avoid being added to the message id list
                confirmation = await self.destination.send(f'<@{self.requester}> Request completed')
            else:
                confirmation = await self.destination.send(f'<@{self.requester}> Request interrupted')
            await confirmation.delete(delay=5)
        
        if exc_type and exc_type != RequestInterrupted:
            await self.send('Unexpected error while processing your request, please try again later. '
                            'If this error persists, please consider submitting a bug report in my '
                            'official server (<https://discord.gg/AQJac7JN8n>).')
        
        self.channel_locks.remove(self.channel)
        
        del self.active_managers[self.requesting_message]
        if exc_type == RequestInterrupted:
            await delete_messages(self.channel, self.message_ids)
            return True
        if self.message_ids:
            db.request_completed(self.requester, self.image_hash, self.requesting_message, self.destination.channel.id,
                                 self.message_ids)
    
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
    
    async def commit_queue(self):
        if len(self._queue) < 5:
            # send messages faster as this will not trip the rate limit.
            # this shouldn't cause messages to deliver out of
            # order...i think
            self.show_confirmation = False
            fut = [self.send(f'From <@{self.requester}>:',
                             allowed_mentions=discord.AllowedMentions.none(),
                             use_webhook=self._queue[0][1]['use_webhook'])]
            for msg in self._queue:
                fut.append(self.send(*msg[0], **msg[1]))
            
            # this will send all messages at the same time
            # while not triggering __aexit__
            await asyncio.gather(*fut)
            await self.destination.message.delete()
        else:
            self.show_confirmation = True
            start = time.time()
            status = await self.destination.send(embed=self.get_embed(0, ''))
            self.rtt.append(time.time() - start)
            # apparently webhook shares the same rate limit???
            
            self._queue.insert(0, ((f'From <@{self.requester}>:',), {
                'allowed_mentions': discord.AllowedMentions.none(),
                'use_webhook': self._queue[0][1]['use_webhook']}))
            
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
                    
                    asyncio.ensure_future(
                            status.edit(embed=self.get_embed(i + 1, ''))
                    )
                    # don't use await since this can be executed while sleeping
                    
                    await sleep(delay - rtt)
                    # while discord.py handles all the rate limits
                    # it looks better to have a uniformed speed
                
                msg = self._queue[-1]
                await self.send(*msg[0], **msg[1])
                await self.destination.message.delete()
            finally:
                await status.delete()
    
    async def send(self, *args, trigger_typing=False, use_webhook=False, **kwargs):
        if use_webhook:
            wh = await get_webhook(self.channel)
            msg = await wh.send(*args, wait=True, **kwargs)
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
    def message_deleted(cls, c_id: int, m_id: int):
        if m_id in cls.active_managers:
            cls.active_managers[m_id].interrupt()
        try:
            msgs = db.get_associated_messages(m_id)
        except db.NoResultFound:
            return
        
        # keep the record in db in case of someone uploading offensive things
        asyncio.ensure_future(
                delete_messages(c_id, msgs)
        )


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
                logger.warning('Bulk delete failed. Trying to single delete')
                logger.warning(res.status)
                logger.warning(res.headers)
                logger.warning(await res.text())
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
                await sleep(1.5)


def split_minimal(seq: str):
    res = []
    msg = ''
    for line in seq.splitlines():
        if len(line) > 2000:
            raise EmojiSequenceTooLong
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
    with_space: bool = False
    multiline: bool = False


def parse_opt(s: str):
    """
    syntax:
    |show image_name [: [with space] [multiline|irc] [large]]
    """
    l = s.replace('_', ' ').split(':')
    opts = ShowOptions()
    opts.name = l[0].strip()
    if len(l) > 1:
        args = list(map(str.strip, l[1].strip().split(',')))
        opts.large = 'large' in args
        opts.with_space = 'with space' in args
        opts.multiline = 'multiline' in args or 'irc' in args
    print(l)
    print(opts)
    return opts


@bot.command()
async def show(ctx: commands.Context, *, raw_or_parsed_args: Union[str, ShowOptions] = ''):
    async with MessageManager(ctx) as manager:
        if isinstance(raw_or_parsed_args, str):
            raw_args = raw_or_parsed_args.lower().strip()
            if not raw_args:
                return
            
            if raw_args == 'help':
                await manager.send(HELP_TEXT)
                return
            
            opts = parse_opt(raw_args)
        else:
            opts = raw_or_parsed_args
        
        try:
            try:
                h = int(opts.name)
            except ValueError:
                h = db.get_image_hash(opts.name)
            path = db.get_image_path(h)
        except db.NoResultFound:
            await manager.send(f"Huh, I've never seen an image of `{opts.name}`. I wonder what it looks like")
            return
        manager.image_hash = h
        img = Image.open(BASE_PATH / path)
        if opts.large and img.width > 27:
            # discord displays all lines above 27 emojis as inline, according
            # to trial and error.
            await manager.send(
                    f"Umm it seems that an image of `{opts.name}`is {img.width - 27} pixels too wide to be sent as large")
            return
        
        if img.width > 79:
            await manager.send(
                    f"Well, it seems like an image of `{opts.name}` is {img.width - 79} pixels too wide to be sent. "
                    r"Nice job on whoever managed to upload this I guess ¯\_(ツ)_/¯")
            return
        
        emojis = gen_emoji_sequence(img, opts.large, opts.with_space)
        try:
            if opts.large or opts.multiline:
                messages = emojis.splitlines()
                for m in messages:
                    if len(m) > 2000: raise EmojiSequenceTooLong
            else:
                messages = split_minimal(emojis)
        
        except EmojiSequenceTooLong:
            await manager.send(
                    f"Well, it seems like an image of `{opts.name}` produced a really long message. "
                    r"Nice job on whoever managed to upload this I guess ¯\_(ツ)_/¯")
            return
        
        for i in range(len(messages)):
            manager.queue(messages[i], use_webhook=True)
        await manager.commit_queue()


@bot.command()
async def gradient(ctx: commands.Context, *, raw_args=''):
    async with MessageManager(ctx) as manager:
        opts = parse_opt(raw_args)
        c = re.search(r'\b(?P<c>[rgb]|red|green|blue)=(?P<v>\d{1,2})\b', raw_args)
        if c is None:
            await manager.send("You need to specify a base color because, "
                               "unfortunately, you humans can't see a message in 3D if I send one")
            return
        if not 0 <= int(c.group('v')) <= 15:
            await manager.send("You see, I only know 16 colors so I can't do that")
            return
        color = {c.group('c')[0]: int(c.group('v'))}
        img = gen_gradient(**color)
        emojis = gen_emoji_sequence(img, opts.large, opts.with_space)
        if opts.large or opts.multiline:
            seq = emojis.splitlines()
            for msg in seq:
                manager.queue(msg, use_webhook=True)
        else:
            for i in range(4):
                # custom splitting to ensure that each chunk is 4 lines
                manager.queue('\n'.join(emojis.splitlines()[i * 4:i * 4 + 4]), use_webhook=True)
        await manager.commit_queue()


@bot.command()
async def delete(ctx: commands.Context, *, raw_args=''):
    async with MessageManager(ctx) as mm:
        try:
            id = int(raw_args.strip())
        except ValueError:
            try:
                m = re.search(r'https://discord.com/channels/\d+/\d+/(\d+)', raw_args)
                id = int(m.group(1))
            except:
                await mm.send("Ugh, you sure this is a valid message id or a link to the message?")
                return
        
        try:
            req = db.get_request(id)
        except db.NoResultFound:
            await mm.send(f"Hmm, I've never seen a message with an id of {id}. "
                          f"I wonder what's inside that makes you want to delete it so badly")
            return
        
        if ctx.author.id != req.requester:
            await mm.send(f"What? Are you asking me to delete something not belonging to you? Well, you tried")
            return
        
        msgs = db.get_associated_messages(id)
        if req.channel == ctx.channel.id:
            msgs.append(ctx.message.id)
        else:
            await ctx.message.delete()
        await delete_messages(req.channel, msgs)


@bot.event
async def on_raw_message_delete(e: discord.RawMessageDeleteEvent):
    MessageManager.message_deleted(e.channel_id, e.message_id)


@bot.event
async def on_connect():
    print('Connected to Discord gateway')


@bot.event
async def on_ready():
    print('Logged in as ' + bot.user.name + '#' + bot.user.discriminator)
    await bot.change_presence(activity=discord.Activity(name='|show help', type=discord.ActivityType.playing))
