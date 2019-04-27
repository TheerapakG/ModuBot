from discord.ext.commands import Cog, command
from ...rich_guild import get_guild
from ...decorator_helper import decorate_cog_command

deps = ['permission']

class Music(Cog):
    def __init__(self):
        self.bot = None

    async def pre_init(self, bot, config):
        self.bot = bot

    async def init(self):
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canSummon', 'True')
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canDisconnect', 'True')
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canSummon', 'False')
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canDisconnect', 'False')

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canSummon', 'True')
    async def summon(self, ctx):
        """
        Usage:
            {prefix}summon

        summon bot into voice channel that you're currently joining to
        """
        voicestate = ctx.author.voice
        voicechannel = None
        if voicestate:
            voicechannel = voicestate.channel

        if not voicechannel:
            raise Exception("not in any voice channel")

        else:
            guild = get_guild(ctx.bot, ctx.guild)
            await guild.set_connected_voice_channel(voicechannel)
            await ctx.send('successfully summoned')

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canDisconnect', 'True')
    async def disconnect(self, ctx):
        """
        Usage:
            {prefix}disconnect

        disconnect bot from voice channel
        """
        guild = get_guild(ctx.bot, ctx.guild)
        await guild.set_connected_voice_channel(None)
        await ctx.send('successfully disconnected')

cogs = [Music]