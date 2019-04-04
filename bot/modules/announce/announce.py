from discord.ext.commands import Cog, command
from discord import TextChannel
from typing import Optional
from ...decorator_helper import decorate_cog_command

import re

regex_parse_time = re.compile(r'^((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?$')

from datetime import timedelta

class Announce(Cog):

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
        ctx.bot.log.debug(str(delta))
        await ctx.send('WIP')

cogs = [Announce]