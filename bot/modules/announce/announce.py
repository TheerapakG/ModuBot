from discord.ext.commands import Cog, command
from collections import namedtuple
from discord import TextChannel
from typing import Optional
from ...decorator_helper import decorate_cog_command
from asyncio import sleep, create_task, CancelledError

import re

regex_parse_time = re.compile(r'^((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?$')

from datetime import timedelta

deps = ['permission']

class Announce(Cog):

    AnnounceTask = namedtuple('AnnounceTask', ['announcestring', 'interval', 'taskobj'])

    def __init__(self):
        self.tasks = list()
        self.bot = None
        self.config = None

    async def pre_init(self, bot, config):
        self.bot = bot
        self.config = config

    async def init(self):
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canAnnounce', 'True')
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canAnnounce', 'False')

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canAnnounce', 'True')
    async def announce(self, ctx, channel: Optional[TextChannel], *, announcestring: str):
        """
        Usage:
            {prefix}announce [channel] announcestring

        make the bot say whatever pass to this command
        if not specify channel then the message will be sent in the same channel
        """
        if not channel:
            await ctx.send(announcestring) 
        else:
            await channel.send(announcestring)

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canAnnounce', 'True')
    async def interval_announce(self, ctx, channel: Optional[TextChannel], interval: str, *, announcestring: str):
        """
        Usage:
            {prefix}interval_announce [channel] interval announcestring

        make the bot say whatever pass to this command in interval
        if not specify channel then the message will be sent in the same channel
        """
        interval_parts = regex_parse_time.match(interval)
        assert interval_parts is not None
        time_params = {name: float(param) for name, param in interval_parts.groupdict().items() if param}
        delta = timedelta(**time_params)

        async def announcer():
            try:
                while True:
                    await sleep(delta.total_seconds())
                    await ctx.send(announcestring)
                    await announcer()
            except CancelledError:
                ctx.bot.log.debug('{} announce cancelled'.format(announcestring))

        task = create_task(announcer())
        self.tasks.append(self.AnnounceTask(announcestring, delta, task))

        ctx.bot.log.debug('{} is queued to be announce every {}'.format(announcestring, str(delta)))
        await ctx.send('{} is queued to be announce every {}'.format(announcestring, str(delta)))

cogs = [Announce]