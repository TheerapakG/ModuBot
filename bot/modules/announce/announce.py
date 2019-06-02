"""
ModuBot: A modular discord bot with dependency management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The MIT License (MIT)

Copyright (c) 2019 TheerapakG

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from discord.ext.commands import Cog, command
from collections import namedtuple
from discord import TextChannel
from typing import Optional
from ...decorator_helper import decorate_cog_command
from asyncio import sleep, create_task, CancelledError

from ...utils import parse_duration

deps = ['permission']

class Announce(Cog):

    AnnounceTask = namedtuple('AnnounceTask', ['announcestring', 'interval', 'taskobj'])

    def __init__(self):
        self.tasks = list()
        self.bot = None

    async def pre_init(self, bot):
        self.bot = bot

    async def init(self):
        self.bot.crossmodule.assign_dict_object('PermType', 'canAnnounce', bool)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canAnnounce', True)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canAnnounce', False)

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canAnnounce', True)
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
    @decorate_cog_command('require_perm_cog_command', 'canAnnounce', True)
    async def interval_announce(self, ctx, channel: Optional[TextChannel], interval: str, *, announcestring: str):
        """
        Usage:
            {prefix}interval_announce [channel] interval announcestring

        make the bot say whatever pass to this command in interval
        if not specify channel then the message will be sent in the same channel
        """
        delta = parse_duration(interval)

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