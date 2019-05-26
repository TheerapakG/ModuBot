from discord.ext.commands import Cog, command
from asyncio import create_task, Lock
import traceback
from ...rich_guild import get_guild
from ...decorator_helper import decorate_cog_command
from ...playback import Entry, Playlist
from ...utils import fixg, ftimedelta
from .ytdldownloader import YtdlDownloader, YtdlStreamEntry, get_entry, get_stream_entry, get_entry_list_from_playlist_url
from collections import defaultdict
from ...playback import PlayerState
from datetime import timedelta
import time
import re

from typing import Optional, Union, Set

deps = ['permission']

class Music(Cog):
    def __init__(self):
        self._aiolocks = defaultdict(Lock)
        self.bot = None
        self.downloader = None
        self.lockdowntier = 0
        self._playlists = dict()

    async def pre_init(self, bot):
        self.bot = bot
        self.downloader = YtdlDownloader(self.bot, 'audio_cache')

    async def init(self):
        self.bot.crossmodule.assign_dict_object('PermType', 'canSummon', bool)
        self.bot.crossmodule.assign_dict_object('PermType', 'canDisconnect', bool)
        self.bot.crossmodule.assign_dict_object('PermType', 'canControlPlayback', bool)
        self.bot.crossmodule.assign_dict_object('PermType', 'canRemoveEntryYourself', bool)
        self.bot.crossmodule.assign_dict_object('PermType', 'canAddEntry', bool)
        self.bot.crossmodule.assign_dict_object('PermType', 'canAddStream', bool)
        self.bot.crossmodule.assign_dict_object('PermType', 'usableYtdlExtractor', Optional[Set[str]])
        self.bot.crossmodule.assign_dict_object('PermType', 'allowPlaylists', bool)
        self.bot.crossmodule.assign_dict_object('PermType', 'maxPlaylistsLength', Optional[int])
        self.bot.crossmodule.assign_dict_object('PermType', 'maxSongCount', Optional[int])
        self.bot.crossmodule.assign_dict_object('PermType', 'maxEntryLength', Optional[timedelta])
        self.bot.crossmodule.assign_dict_object('PermType', 'lockdownTier', Optional[int])
        self.bot.crossmodule.assign_dict_object('PermComparer', 'maxPlaylistsLength', lambda a, b: a >= b if a else True)
        self.bot.crossmodule.assign_dict_object('PermComparer', 'maxSongCount', lambda a, b: a >= b if a else True)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canSummon', True)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canDisconnect', True)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canControlPlayback', True)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canRemoveEntryYourself', True)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canAddEntry', True)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canAddStream', True)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'usableYtdlExtractor', None)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'allowPlaylists', True)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'maxPlaylistsLength', None)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'maxSongCount', None)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'maxEntryLength', None)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'lockdownTier', None)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canSummon', False)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canDisconnect', False)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canControlPlayback', False)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canRemoveEntryYourself', True)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canAddEntry', False)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canAddStream', False)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'usableYtdlExtractor', {'youtube'})
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'allowPlaylists', True)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'maxPlaylistsLength', 1)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'maxSongCount', 1)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'maxEntryLength', timedelta(minutes=60))
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'lockdownTier', 0)

    async def uninit(self):
        self.bot.log.debug('stopping downloader...')
        self.downloader.shutdown()
        self.bot.log.debug('stopping playlists...')
        for pl in self._playlists.values():
            await pl.stop()

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canSummon', True)
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
            async with self._aiolocks['summon']:
                try:
                    before_player = await guild.get_player()
                except:
                    before_player = None
                await guild.set_connected_voice_channel(voicechannel)
                if not before_player:
                    playlistname = 'default-{}'.format(guild.id)
                    if playlistname not in self._playlists:
                        self._playlists[playlistname] = Playlist(ctx.bot, playlistname)
                    await guild.set_playlist(self._playlists[playlistname])
            await ctx.send('successfully summoned')

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canDisconnect', True)
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
    @decorate_cog_command('require_perm_cog_command', 'canControlPlayback', True)
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
                exceptionstr = 'Cannot resume! {}'.format(str(exc))
                ctx.bot.log.error(exceptionstr)
                await ctx.send(exceptionstr)
            create_task(_fail())
        def success():
            async def _success():
                await ctx.send('successfully resumed')
            create_task(_success())
        def wait():
            async def _wait():
                await ctx.send('successfully resumed, waiting for entries to be added')
            create_task(_wait())
        await player.play(play_fail_cb = fail, play_success_cb = success, play_wait_cb = wait)

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canControlPlayback', True)
    async def pause(self, ctx):
        """
        Usage:
            {prefix}pause

        pause playback
        """
        guild = get_guild(ctx.bot, ctx.guild)
        player = await guild.get_player()
        await player.pause()
        await ctx.send('successfully paused')

    @command()
    async def skip(self, ctx):
        """
        Usage:
            {prefix}skip

        skip playback
        """
        ctrlplayback_permission =  await ctx.bot.crossmodule.async_call_object(
            'have_perm', 
            ctx.author, 
            'canControlPlayback', 
            True
        )
        authorremove_permission =  await ctx.bot.crossmodule.async_call_object(
            'have_perm', 
            ctx.author, 
            'canRemoveEntryYourself', 
            True
        )

        guild = get_guild(ctx.bot, ctx.guild)
        player = await guild.get_player()
        current = await player.get_current_entry()

        if ctrlplayback_permission or (authorremove_permission and current.queuer_id == ctx.author.id):
            await player.skip()
            await ctx.send('successfully skipped')

    @command()
    async def remove(self, ctx, position: Optional[int] = None):
        """
        Usage:
            {prefix}remove [# in queue]

        remove entry from queue
        """
        ctrlplayback_permission =  await ctx.bot.crossmodule.async_call_object(
            'have_perm', 
            ctx.author, 
            'canControlPlayback', 
            True
        )
        authorremove_permission =  await ctx.bot.crossmodule.async_call_object(
            'have_perm', 
            ctx.author, 
            'canRemoveEntryYourself', 
            True
        )

        guild = get_guild(ctx.bot, ctx.guild)
        player = await guild.get_player()
        playlist = await player.get_playlist()
        if not position:
            position = (await playlist.get_length()) - 1
        entry = await playlist[position]

        if ctrlplayback_permission or (authorremove_permission and entry.queuer_id == ctx.author.id):
            await playlist.remove_position(position)
            await ctx.send('successfully removed')

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canAddEntry', True)
    async def play(self, ctx, *, song_url: str):
        """
        Usage:
            {command_prefix}play song_link
            {command_prefix}play text to search for

        Adds the song to the current playlist.
        """

        bypass_lockdown_permission =  await ctx.bot.crossmodule.async_call_object(
            'have_perm', 
            ctx.author, 
            'lockdownTier', 
            self.lockdowntier,
        )

        if not bypass_lockdown_permission:
            await ctx.send("You do not have permission to interact with the bot due to lockdown.")
            return

        guild = get_guild(ctx.bot, ctx.guild)
        player = await guild.get_player()

        song_url = song_url.strip('<>')
            
        # Make sure forward slashes work properly in search queries
        linksRegex = '((http(s)*:[/][/]|www.)([a-z]|[A-Z]|[0-9]|[/.]|[~])*)'
        pattern = re.compile(linksRegex)
        matchUrl = pattern.match(song_url)
        song_url = song_url.replace('/', '%2F') if matchUrl is None else song_url

        # Rewrite YouTube playlist URLs if the wrong URL type is given
        playlistRegex = r'watch\?v=.+&(list=[^&]+)'
        matches = re.search(playlistRegex, song_url)
        groups = matches.groups() if matches is not None else []
        song_url = "https://www.youtube.com/playlist?" + groups[0] if len(groups) > 0 else song_url

        # Try to determine entry type, if _type is playlist then there should be entries
        info, song_url = await self.downloader.process_url_to_info(
            song_url,
            on_search_error = lambda e: create_task(
                ctx.send("```\n%s\n```" % e)
            )
        )

        if not info:
            await ctx.send("That video cannot be played. Try using the stream command.")
            return

        extractor_permission =  await ctx.bot.crossmodule.async_call_object(
            'have_perm', 
            ctx.author, 
            'usableYtdlExtractor', 
            info.get('extractor', '')
        )

        if not extractor_permission:
            await ctx.send("You do not have permission to play media from this service.")
            return

        # This lock prevent spamming play command to add entries that exceeds time limit/ maximum song limit
        async with self._aiolocks['play_{}'.format(ctx.author.id)]:
            async with ctx.typing():
                # If it's playlist
                if 'entries' in info:
                    num_songs = sum(1 for _ in info['entries'])

                    allow_playlists_permission =  await ctx.bot.crossmodule.async_call_object(
                        'have_perm', 
                        ctx.author, 
                        'allowPlaylists', 
                        True,
                    )

                    if not allow_playlists_permission:
                        await ctx.send("You are not allowed to request playlists")

                    max_playlists_length_permission =  await ctx.bot.crossmodule.async_call_object(
                        'have_perm', 
                        ctx.author, 
                        'maxPlaylistsLength', 
                        num_songs
                    )

                    if not max_playlists_length_permission:
                        await ctx.send("Playlist has too many entries ({1})".format(num_songs))

                    playlist = await player.get_playlist()

                    num_songs_playlist = await playlist.num_entry_of(ctx.author)
                    total_songs = num_songs + num_songs_playlist

                    max_song_count_permission =  await ctx.bot.crossmodule.async_call_object(
                        'have_perm', 
                        ctx.author, 
                        'maxSongCount', 
                        total_songs
                    )

                    if not max_song_count_permission:
                        await ctx.send("cannot queue because song count will exceed ({1})".format(total_songs))

                    t0 = time.time()

                    # My test was 1.2 seconds per song, but we maybe should fudge it a bit, unless we can
                    # monitor it and edit the message with the estimated time, but that's some ADVANCED SHIT
                    # I don't think we can hook into it anyways, so this will have to do.
                    # It would probably be a thread to check a few playlists and get the speed from that
                    # Different playlists might download at different speeds though
                    wait_per_song = 1.2
                    drop_count = 0

                    procmesg = await ctx.send(
                        'Gathering playlist information for {0} songs{1}'.format(
                            num_songs,
                            ', ETA: {0} seconds'.format(
                                fixg(num_songs * wait_per_song)
                            ) if num_songs >= 10 else '.'
                        )
                    )

                    # TODO: I can create an event emitter object instead, add event functions, and every play list might be asyncified
                    #       Also have a "verify_entry" hook with the entry as an arg and returns the entry if its ok

                    entry_list = await get_entry_list_from_playlist_url(song_url, ctx.author.id, self.downloader, {'channel':ctx.channel})
                    entry = None
                    position = None
                    for entry_proc in entry_list:
                        duration = entry_proc.get_duration()
                        max_entry_length_permission =  await ctx.bot.crossmodule.async_call_object(
                            'have_perm', 
                            ctx.author, 
                            'maxEntryLength', 
                            duration
                        )
                        if not max_entry_length_permission:
                            drop_count += 1
                            continue
                        position_potent = await playlist.add_entry(entry_proc)
                        if not position:
                            entry = entry_proc
                            position = position_potent

                    tnow = time.time()
                    ttime = tnow - t0
                    listlen = len(entry_list)

                    ctx.bot.log.info("Processed {} songs in {} seconds at {:.2f}s/song, {:+.2g}/song from expected ({}s)".format(
                        listlen,
                        fixg(ttime),
                        ttime / listlen if listlen else 0,
                        ttime / listlen - wait_per_song if listlen - wait_per_song else 0,
                        fixg(wait_per_song * num_songs))
                    )

                    await procmesg.delete()

                    reply_text = "Enqueued **%s** songs to be played. Position of the first entry in queue: %s"
                    btext = str(listlen - drop_count)

                # If it's an entry
                else:
                    playlist = await player.get_playlist()

                    num_songs_playlist = await playlist.num_entry_of(ctx.author)
                    total_songs = 1 + num_songs_playlist

                    max_song_count_permission =  await ctx.bot.crossmodule.async_call_object(
                        'have_perm', 
                        ctx.author, 
                        'maxSongCount', 
                        total_songs
                    )

                    if not max_song_count_permission:
                        await ctx.send("cannot queue because song count will exceed ({1})".format(total_songs))

                    entry = await get_entry(song_url, ctx.author.id, self.downloader, {'channel':ctx.channel})
                    duration = entry.get_duration()
                    max_entry_length_permission =  await ctx.bot.crossmodule.async_call_object(
                        'have_perm', 
                        ctx.author, 
                        'maxEntryLength', 
                        duration
                    )
                    if not max_entry_length_permission:
                        await ctx.send("cannot queue because song exceed length ({1})".format(duration))
                    position = await playlist.add_entry(entry)

                    reply_text = "Enqueued `%s` to be played. Position in queue: %s"
                    btext = entry.title

                # Position msgs
                time_until = await player.estimate_time_until_entry(entry)
                if time_until == timedelta(seconds=0):
                    position = 'Up next!'
                    reply_text %= (btext, position)

                else:                    
                    reply_text += ' - estimated time until playing: %s'
                    reply_text %= (btext, position, ftimedelta(time_until))

        await ctx.send(reply_text)

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canAddEntry', True)
    @decorate_cog_command('require_perm_cog_command', 'canAddStream', True)
    async def stream(self, ctx, song_url):
        """
        Usage:
            {command_prefix}stream song_link

        Enqueue a media stream.
        This could mean an actual stream like Twitch or shoutcast, or simply streaming
        media without predownloading it.  Note: FFmpeg is notoriously bad at handling
        streams, especially on poor connections.  You have been warned.
        """

        bypass_lockdown_permission =  await ctx.bot.crossmodule.async_call_object(
            'have_perm', 
            ctx.author, 
            'lockdownTier', 
            self.lockdowntier,
        )

        if not bypass_lockdown_permission:
            await ctx.send("You do not have permission to interact with the bot due to lockdown.")
            return

        guild = get_guild(ctx.bot, ctx.guild)
        player = await guild.get_player()

        song_url = song_url.strip('<>')

        playlist = await player.get_playlist()
        async with ctx.typing():
            async with self._aiolocks['play_{}'.format(ctx.author.id)]:
                num_songs_playlist = await playlist.num_entry_of(ctx.author)
                total_songs = 1 + num_songs_playlist

                max_song_count_permission =  await ctx.bot.crossmodule.async_call_object(
                    'have_perm', 
                    ctx.author, 
                    'maxSongCount', 
                    total_songs
                )

                if not max_song_count_permission:
                    await ctx.send("cannot queue because song count will exceed ({1})".format(total_songs))

                entry = await get_stream_entry(song_url, ctx.author.id, self.downloader, {'channel':ctx.channel})
                position = await playlist.add_entry(entry)

            reply_text = "Enqueued `%s` to be streamed. Position in queue: %s"
            btext = entry.title

            # Position msgs
            time_until = await player.estimate_time_until_entry(entry)
            if time_until == timedelta(seconds=0):
                position = 'Up next!'
                reply_text %= (btext, position)

            else:                    
                reply_text += ' - estimated time until streaming: %s'
                reply_text %= (btext, position, ftimedelta(time_until))

        await ctx.send(reply_text)

    @command
    @decorate_cog_command('require_perm_cog_command', 'canLockdown', True)
    async def lockdown(self, ctx, tier: Optional[str] = None):
        """
        Usage:
            {command_prefix}lockdown

        Limit users who can add entries temporarily based on tier settable via permission.
        """
        if tier:
            tier = int(tier)
            if tier == 0:
                self.lockdowntier = 0
                reply = 'successfully remove lockdown limit'
            elif tier < 0:
                reply = 'invalid lockdown limit!'
            else:
                self.lockdowntier = tier
                reply = 'successfully set lockdown limit to tier {}'.format(self.lockdowntier)
        else:
            if self.lockdowntier:
                self.lockdowntier = 0
                reply = 'successfully remove lockdown limit'
            else:
                self.lockdowntier = 1
                reply = 'successfully set lockdown limit to tier 1'
                
        await ctx.send(reply)

    @command()
    async def np(self, ctx):
        """
        Usage:
            {command_prefix}np

        Displays the current song in chat.
        """
        guild = get_guild(ctx.bot, ctx.guild)
        player = await guild.get_player()

        try:
            progress = await player.progress()
            current_entry = await player.get_current_entry()
        except:
            await ctx.send('There is no current song.')
            return

        # TODO: Fix timedelta garbage with util function
        song_progress = ftimedelta(timedelta(seconds=progress))
        song_total = ftimedelta(timedelta(seconds=current_entry.duration))

        streaming = isinstance(current_entry, YtdlStreamEntry)
        prog_str = ('`[{progress}]`' if streaming else '`[{progress}/{total}]`').format(
            progress=song_progress, total=song_total
        )
        prog_bar_str = ''

        # percentage shows how much of the current song has already been played
        percentage = 0.0
        if current_entry.duration > 0:
            percentage = progress / current_entry.duration

        # create the actual bar
        progress_bar_length = 30
        for i in range(progress_bar_length):
            if (percentage < 1 / progress_bar_length * i):
                prog_bar_str += '□'
            else:
                prog_bar_str += '■'

        action_text = 'Streaming' if streaming else 'Playing'

        if current_entry.queuer_id:
            np_text = "Now {action}: **{title}** added by **{author}**\nProgress: {progress_bar} {progress}\n\N{WHITE RIGHT POINTING BACKHAND INDEX} <{url}>".format(
                action = action_text,
                title = current_entry.title,
                author = ctx.guild.get_member(current_entry.queuer_id),
                progress_bar = prog_bar_str,
                progress = prog_str,
                url = current_entry.source_url
            )
        else:

            np_text = "Now {action}: **{title}**\nProgress: {progress_bar} {progress}\n\N{WHITE RIGHT POINTING BACKHAND INDEX} <{url}>".format(
                action = action_text,
                title = current_entry.title,
                progress_bar = prog_bar_str,
                progress = prog_str,
                url = current_entry.source_url
            )

        await ctx.send(np_text)

    @command()
    async def volume(self, ctx, new_volume:Optional[str] = None):
        """
        Usage:
            {command_prefix}volume (+/-)[volume]
        Sets the playback volume. Accepted values are from 1 to 100.
        Putting + or - before the volume will make the volume change relative to the current volume.
        """

        guild = get_guild(ctx.bot, ctx.guild)
        player = await guild.get_player()

        if not new_volume:
            await ctx.send(('Current volume: `%s%%`') % int(player.volume * 100))
            return

        relative = False
        if new_volume[0] in '+-':
            relative = True

        try:
            new_volume = int(new_volume)

        except ValueError:
            raise Exception(('`{0}` is not a valid number').format(new_volume))

        vol_change = None
        if relative:
            vol_change = new_volume
            new_volume += (player.volume * 100)

        old_volume = int(player.volume * 100)

        if 0 < new_volume <= 100:
            player.volume = new_volume / 100.0

            await ctx.send(('Updated volume from **%d** to **%d**') % (old_volume, new_volume))
            return

        else:
            if relative:
                raise Exception(
                    'Unreasonable volume change provided: {}{:+} -> {}%.  Provide a change between {} and {:+}.'.format(
                        old_volume, vol_change, old_volume + vol_change, 1 - old_volume, 100 - old_volume
                    )
                )
            else:
                raise Exception(
                    'Unreasonable volume provided: {}%. Provide a value between 1 and 100.'.format(new_volume)
                )

cogs = [Music]