from discord.ext.commands import Cog, command
from discord import ActivityType, Activity
from ...decorator_helper import decorate_cog_command

deps = ['permission']

class Appearance(Cog):
    def __init__(self):
        self.bot = None
        self.config = None

    async def pre_init(self, bot, config):
        self.bot = bot
        self.config = config

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