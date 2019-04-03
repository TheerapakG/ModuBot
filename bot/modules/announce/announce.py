from discord.ext.commands import Cog, command
from discord import TextChannel
from typing import Optional
from ...decorator_helper import decorate_cog_command

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

    @command
    @decorate_cog_command('require_perm_cog_command', 'canAnnounce', 'True')
    async def interval_announce(self, ctx, channel: Optional[TextChannel], interval: timedelta, *, announcestring: str):
        """
        Usage:
            {prefix}interval_announce [channel] interval announcestring

        make the bot say whatever pass to this command in interval
        if not specify channel then the message will be sent in the same channel
        """
        await ctx.send('WIP')

cogs = [Announce]