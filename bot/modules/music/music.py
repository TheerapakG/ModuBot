from discord.ext.commands import Cog, command
from asyncio import create_task
from ...rich_guild import get_guild
from ...decorator_helper import decorate_cog_command
from ...playback import Entry, Playlist
from .ytdldownloader import YtdlDownloader

deps = ['permission']

class YtdlEntry(Entry):
    async def prepare_cache(self):
        async with self._aiolocks['preparing_cache_set']:
            self._preparing_cache = True

        async with self._aiolocks['preparing_cache_set']:
            async with self._aiolocks['cached_set']:
                self._preparing_cache = False
                self._cached = True

class Music(Cog):
    def __init__(self):
        self.bot = None
        self.downloader = None
        self._playlists = dict()

    async def pre_init(self, bot, config):
        self.bot = bot
        self.downloader = YtdlDownloader('audio_cache')

    async def init(self):
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canSummon', 'True')
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canDisconnect', 'True')
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canControlPlayback', 'True')
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canSummon', 'False')
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canDisconnect', 'False')
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canControlPlayback', 'False')

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
            playlist = await guild.get_playlist()
            if not playlist:
                playlistname = 'default-{}'.format(guild.id)
                if playlistname not in self._playlists:
                    self._playlists[playlistname] = Playlist(playlistname)
                await guild.set_playlist(self._playlists[playlistname])
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

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canControlPlayback', 'True')
    async def resume(self, ctx):
        """
        Usage:
            {prefix}resume

        resume playback
        """
        guild = get_guild(ctx.bot, ctx.guild)
        player = await guild.get_player()
        def fail(exc):
            async def _fail():
                await ctx.send('cannot resume: {}'.format(str(exc)))
            create_task(_fail())
        def success():
            async def _success():
                await ctx.send('successfully resumed')
            create_task(_success())
        await player.play(play_fail_cb = fail, play_success_cb = success)

cogs = [Music]