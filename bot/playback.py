from asyncio import Lock, create_task, CancelledError, run_coroutine_threadsafe
from enum import Enum
from collections import defaultdict, deque
from typing import Union, Optional
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from functools import partial
import subprocess

class Entry:
    def __init__(self):
        self._aiolocks = defaultdict(Lock)
        self._preparing_cache = False
        self._cached = False

    async def is_preparing_cache(self):
        async with self._aiolocks['preparing_cache_set']:
            return self._preparing_cache

    async def is_cached(self):
        async with self._aiolocks['cached_set']:
            return self._cached

    async def prepare_cache(self):
        async with self._aiolocks['preparing_cache_set']:
            self._preparing_cache = True

        async with self._aiolocks['preparing_cache_set']:
            async with self._aiolocks['cached_set']:
                self._preparing_cache = False
                self._cached = True

    async def get_metadata(self):
        pass

class Playlist:
    def __init__(self, *, precache = 1, persistent = False):
        self._aiolocks = defaultdict(Lock)
        self._list = deque()
        self._cache_task = deque()
        self._precache = precache

    async def __getitem__(self, item: Union[int, slice]):
        async with self._aiolocks['list']:
            if isinstance(item, slice):
                return [await entry.get_metadata() for entry in self._list[item]]
            else:
                return await self._list[item].get_metadata()

    async def _get_entry(self):
        async with self._aiolocks['list']:
            if not self._list:
                return

            entry = self._list.popleft()
            cache = self._cache_task.popleft()

        return (entry, cache)

    async def add_entry(self, entry, *, head = False):
        async with self._aiolocks['list']:
            if head:
                self._list.appendleft(entry)
            else:
                self._list.append(entry)

    async def remove_position(self, position):
        async with self._aiolocks['list']:
            del self._list[position]
            if position < self._precache:
                self._cache_task[position].cancel()
                del self._cache_task[position]
                if self._precache <= len(self._list):
                    self._cache_task.append(
                        create_task(self._list[self._precache - 1].prepare_cache())
                        )

    async def get_entry_position(self, entry):
        async with self._aiolocks['list']:
            return self._list.index(entry)


class PlayerState(Enum):
    PLAYING = 0
    PAUSE = 1
    DOWNLOADING = 2

class Player:
    def __init__(self, guild, volume = 0.15):
        self._aiolocks = defaultdict(Lock)
        self._current = None
        self._playlist = None
        self._guild = guild
        self._player = None
        self._play_task = None
        self._play_safe_task = None
        self.volume = volume
        self.state = PlayerState.PAUSE

    async def set_playlist(self, playlist: Optional[Playlist]):
        async with self._aiolocks['playlist']:
            self._playlist = playlist

    async def get_playlist(self):
        async with self._aiolocks['playlist']:
            return self._playlist

    async def _play(self):
        async with self._aiolocks['playtask']:
            async with self._aiolocks['player']:
                self.state = PlayerState.DOWNLOADING
            async with self._aiolocks['playlist']:
                entry, cache = await self._playlist._get_entry()

            def _playback_finished(error = None):
                async def _async_playback_finished():
                    async with self._aiolocks['player']:
                        self._player = None

                    if error:
                        raise error # pylint: disable=raising-bad-type

                    create_task(self._play())  

                future = run_coroutine_threadsafe(_async_playback_finished(), self._guild._bot.loop)
                future.result()

            async def _download_and_play():
                await cache

                boptions = "-nostdin"
                aoptions = "-vn"

                self._guild._bot.log.debug("Creating player with options: {} {} {}".format(boptions, aoptions, entry.filename))

                source = PCMVolumeTransformer(
                    FFmpegPCMAudio(
                        entry.filename,
                        before_options=boptions,
                        options=aoptions,
                        stderr=subprocess.PIPE
                    ),
                    self.volume
                )

                async with self._aiolocks['player']:
                    self._player = self._guild._voice_client
                    self._guild._voice_client.play(source, after=_playback_finished)
                    self.state = PlayerState.PLAYING
        
            self._play_task = create_task(_download_and_play())

        try:
            await self._play_task
        except CancelledError:
            if self.state != PlayerState.PAUSE:
                await self._play()

    async def _play_safe(self, *callback):
        async with self._aiolocks['playsafe']:
            if not self._play_safe_task:
                task = create_task(self._play())
                def clear_play_safe_task():
                    self._play_safe_task = None
                task.add_done_callback(clear_play_safe_task)
                for cb in callback:
                    task.add_done_callback(cb)
            else:
                return

    async def play(self):
        async with self._aiolocks['play']:
            async with self._aiolocks['player']:
                if self.state != PlayerState.PAUSE:
                    return

                if self._player:
                    self._player.resume()
                    return

                await self._play_safe()

    async def _pause(self):
        async with self._aiolocks['player']:
            self._player.pause()
            self.state = PlayerState.PAUSE

    async def pause(self):
        async with self._aiolocks['pause']:
            async with self._aiolocks['player']:
                if self.state == PlayerState.PAUSE:
                    return

                elif self.state == PlayerState.PLAYING:
                    self._player.stop()
                    self.state = PlayerState.PAUSE
                    return

                elif self.state == PlayerState.DOWNLOADING:
                    async with self._aiolocks['playtask']:
                        self._play_task.add_done_callback(partial(create_task, self._pause()))
                    return
        

    async def skip(self):
        async with self._aiolocks['skip']:
            async with self._aiolocks['player']:
                if self.state == PlayerState.PAUSE:
                    await self._play_safe(partial(create_task, self._pause()))
                    return

                elif self.state == PlayerState.PLAYING:
                    self._player.pause()
                    await self._play_safe()
                    return

                elif self.state == PlayerState.DOWNLOADING:
                    async with self._aiolocks['playtask']:
                        self._play_task.cancel()
                    return
