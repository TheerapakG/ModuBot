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
from discord import ActivityType, Activity
from ...decorator_helper import decorate_cog_command

deps = ['permission']

class Appearance(Cog):
    def __init__(self):
        self.bot = None

    async def pre_init(self, bot):
        self.bot = bot

    async def init(self):
        self.bot.crossmodule.assign_dict_object('PermType', 'canManageAppearance', bool)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canManageAppearance', True)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canManageAppearance', False)

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canManageAppearance', True)
    async def change_activity(self, ctx, activity_type: str, *, name: str):
        """
        Usage:
            {prefix}change_activity activity name

        change activity shown in presence
        """
        bot = ctx.bot
        current_activity, current_status = await bot.get_presence()

        if activity_type in ['play', 'playing']:
            activity_type = ActivityType.playing
        elif activity_type in ['stream', 'streaming']:
            activity_type = ActivityType.streaming
        elif activity_type in ['listen', 'listening']:
            activity_type = ActivityType.listening
        elif activity_type in ['watch', 'watching']:
            activity_type = ActivityType.watching
        else:
            raise Exception('not known activity')

        if not current_activity:
            current_activity = Activity(type = activity_type, name = name)
        else:
            current_activity.type = activity_type
            current_activity.name = name
        await bot.set_presence(activity = current_activity, status = current_status)

cogs = [Appearance]