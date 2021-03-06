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

from asyncio import Lock, create_task, CancelledError, run_coroutine_threadsafe, sleep, Future
from enum import Enum
from collections import defaultdict, deque
from typing import Union, Optional
from discord import FFmpegPCMAudio, PCMVolumeTransformer, AudioSource
from functools import partial
from .utils import callback_dummy_future
from itertools import islice
from datetime import timedelta
import traceback
import subprocess
from random import shuffle

class Entry:
    def __init__(self, source_url, title, duration, queuer_id, metadata):
        self.source_url = source_url
        self.title = title
        self.duration = duration
        self.queuer_id = queuer_id
        self._aiolocks = defaultdict(Lock)
        self._preparing_cache = False
        self._cached = False
        self._cache_task = None # playlists set this
        self._metadata = metadata
        self._local_url = None

    async def is_preparing_cache(self):
        async with self._aiolocks['preparing_cache_set']:
            return self._preparing_cache

    async def is_cached(self):
        async with self._aiolocks['cached_set']:
            return self._cached

    async def prepare_cache(self):
        async with self._aiolocks['preparing_cache_set']:
            if self._preparing_cache:
                return
            self._preparing_cache = True

        async with self._aiolocks['preparing_cache_set']:
            async with self._aiolocks['cached_set']:
                self._preparing_cache = False
                self._cached = True

    def get_metadata(self):
        return self._metadata

    def get_duration(self):
        return timedelta(seconds=self.duration)

    async def set_local_url(self, local_url):
        self._local_url = local_url

class Playlist:
    def __init__(self, name, bot, *, precache = 1, persistent = False):
        self._bot = bot
        self._name = name
        self._aiolocks = defaultdict(Lock)
        self._list = deque()
        self._precache = precache

    async def __getitem__(self, item: Union[int, slice]):
        async with self._aiolocks['list']:
            if isinstance(item, slice):
                return [await entry.get_metadata() for entry in self._list[item]]
            else:
                return await self._list[item].get_metadata()

    async def stop(self):
        async with self._aiolocks['list']:
            for entry in self._list:
                if entry._cache_task:
                    entry._cache_task.cancel()
                    try:
                        await entry._cache_task
                    except:
                        pass
                    entry._cache_task = None
                    entry._preparing_cache = False
                    entry._cached = False

    async def shuffle(self):
        async with self._aiolocks['list']:
            shuffle(self._list)
            for entry in self._list[:self._precache]:
                if not entry._cache_task:
                    entry._cache_task = create_task(entry.prepare_cache())

    def get_name(self):
        return self._name

    async def _get_entry(self):
        async with self._aiolocks['list']:
            if not self._list:
                return

            entry = self._list.popleft()
            if not entry._cache_task:
                entry._cache_task = create_task(entry.prepare_cache())

        return (entry, entry._cache_task)

    async def add_entry(self, entry, *, head = False):
        async with self._aiolocks['list']:
            if head:
                self._list.appendleft(entry)
                position = 0
            else:
                self._list.append(entry)
                position = len(self._list) - 1
            if self._precache > position:
                entry._cache_task = create_task(entry.prepare_cache())
            return position + 1

    async def get_length(self):
        async with self._aiolocks['list']:
            return len(self._list)

    async def remove_position(self, position):
        async with self._aiolocks['list']:
            if position < self._precache:
                self._list[position]._cache_task.cancel()
                self._list[position]._cache_task = None
                if self._precache <= len(self._list):
                    consider = self._list[self._precache - 1]
                    if not consider.cache_task:
                        consider.cache_task = create_task(consider.prepare_cache())
            val = self._list[position]
            del self._list[position]
            return val

    async def get_entry_position(self, entry):
        async with self._aiolocks['list']:
            return self._list.index(entry)

    async def estimate_time_until(self, position):
        async with self._aiolocks['list']:
            estimated_time = sum(e.duration for e in islice(self._list, position - 1))
        return timedelta(seconds=estimated_time)

    async def estimate_time_until_entry(self, entry):
        estimated_time = 0
        async with self._aiolocks['list']:
            for e in self._list:
                if e is not entry:  
                    estimated_time += e.duration
                else:
                    break
        return timedelta(seconds=estimated_time)            

    async def num_entry_of(self, user_id):
        async with self._aiolocks['list']:
            return sum(1 for e in self._list if e.queuer_id == user_id)

class PlayerState(Enum):
    PLAYING = 0
    PAUSE = 1
    DOWNLOADING = 2
    WAITING = 3


class SourcePlaybackCounter(AudioSource):
    def __init__(self, source, progress = 0):
        self._source = source
        self.progress = progress

    def read(self):
        res = self._source.read()
        if res:
            self.progress += 1
        return res

    def get_progress(self):
        return self.progress * 0.02

class Player:
    def __init__(self, guild, volume = 0.15):
        self._aiolocks = defaultdict(Lock)
        self._current = None
        self._playlist = None
        self._guild = guild
        self._player = None
        self._play_task = None
        self._play_safe_task = None
        self._source = None
        self._volume = volume
        self.state = PlayerState.PAUSE

        create_task(self.play())

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, val):
        self._volume = val
        async def set_if_source():
            async with self._aiolocks['player']:
                if self._source:
                    self._source._source.volume = val
        create_task(set_if_source())

    async def status(self):
        async with self._aiolocks['player']:
            return self.state

    async def set_playlist(self, playlist: Optional[Playlist]):
        async with self._aiolocks['playlist']:
            self._playlist = playlist

    async def get_playlist(self):
        async with self._aiolocks['playlist']:
            return self._playlist

    async def _play(self, *, play_wait_cb = None, play_success_cb = None):
        async with self._aiolocks['playtask']:
            async with self._aiolocks['player']:
                self.state = PlayerState.WAITING
                self._current = None
            entry = None
            while not entry:
                try:
                    async with self._aiolocks['playlist']:
                        entry, cache = await self._playlist._get_entry()
                        async with self._aiolocks['player']:
                            self.state = PlayerState.DOWNLOADING
                            self._guild._bot.log.debug('got entry...')
                            self._guild._bot.log.debug(str(entry))
                            self._guild._bot.log.debug(str(cache))
                            self._current = entry
                except (TypeError, AttributeError):
                    if play_wait_cb:
                        play_wait_cb()
                        play_wait_cb = None
                        play_success_cb = None
                    await sleep(1)                 

            if play_success_cb:
                play_success_cb()

            def _playback_finished(error = None):
                async def _async_playback_finished():
                    async with self._aiolocks['player']:
                        self._current = None
                        self._player = None
                        self._source = None

                    if error:
                        raise error # pylint: disable=raising-bad-type

                    create_task(self._play())  

                future = run_coroutine_threadsafe(_async_playback_finished(), self._guild._bot.loop)
                future.result()

            async def _download_and_play():
                try:
                    self._guild._bot.log.debug('waiting for cache...')
                    await cache
                    self._guild._bot.log.debug('finish cache...')
                except:
                    self._guild._bot.log.error('cannot cache...')
                    self._guild._bot.log.error(traceback.format_exc())
                    async with self._aiolocks['player']:
                        if self.state != PlayerState.PAUSE:
                            await self._play()                    

                boptions = "-nostdin"
                aoptions = "-vn"

                self._guild._bot.log.debug("Creating player with options: {} {} {}".format(boptions, aoptions, entry._local_url))

                source = SourcePlaybackCounter(
                    PCMVolumeTransformer(
                        FFmpegPCMAudio(
                            entry._local_url,
                            before_options=boptions,
                            options=aoptions,
                            stderr=subprocess.PIPE
                        ),
                        self._volume
                    )
                )

                async with self._aiolocks['player']:
                    self._player = self._guild._voice_client
                    self._guild._voice_client.play(source, after=_playback_finished)
                    self._source = source
                    self.state = PlayerState.PLAYING
        
            self._play_task = create_task(_download_and_play())

        try:
            self._guild._bot.log.debug('waiting for task to play...')
            await self._play_task
        except CancelledError:
            async with self._aiolocks['player']:
                if self.state != PlayerState.PAUSE:
                    await self._play()

    async def _play_safe(self, *callback, play_wait_cb = None, play_success_cb = None):
        async with self._aiolocks['playsafe']:
            if not self._play_safe_task:
                task = create_task(self._play(play_wait_cb = play_wait_cb, play_success_cb = play_success_cb))
                def clear_play_safe_task(future):
                    self._play_safe_task = None
                task.add_done_callback(clear_play_safe_task)

                for cb in callback:
                    task.add_done_callback(callback_dummy_future(cb))
            else:
                return

    async def play(self, *, play_fail_cb = None, play_success_cb = None, play_wait_cb = None):
        async with self._aiolocks['play']:
            async with self._aiolocks['player']:
                if self.state != PlayerState.PAUSE:
                    exc = Exception('player is not paused')
                    if play_fail_cb:
                        play_fail_cb(exc)
                    else:
                        raise exc
                    return

                if self._player:
                    self.state = PlayerState.PLAYING
                    self._player.resume()
                    play_success_cb()
                    return

                await self._play_safe(play_wait_cb = play_wait_cb, play_success_cb = play_success_cb)

    async def _pause(self):
        async with self._aiolocks['player']:
            if self.state != PlayerState.PAUSE:
                if self._player:
                    self._player.pause()
                    self.state = PlayerState.PAUSE

    async def pause(self):
        async with self._aiolocks['pause']:
            async with self._aiolocks['player']:
                if self.state == PlayerState.PAUSE:
                    return

                elif self.state == PlayerState.PLAYING:
                    self._player.pause()
                    self.state = PlayerState.PAUSE
                    return

                elif self.state == PlayerState.DOWNLOADING or self.state == PlayerState.WAITING:
                    async with self._aiolocks['playtask']:
                        self._play_task.add_done_callback(
                            callback_dummy_future(
                                partial(create_task, self._pause())
                            )
                        )
                    return
        

    async def skip(self):
        async with self._aiolocks['skip']:
            async with self._aiolocks['player']:
                if self.state == PlayerState.PAUSE:
                    await self._play_safe(partial(create_task, self._pause()))
                    return

                elif self.state == PlayerState.PLAYING:
                    self._player.stop()
                    return

                elif self.state == PlayerState.DOWNLOADING:
                    async with self._aiolocks['playtask']:
                        self._play_task.cancel()
                    return

                elif self.state == PlayerState.WAITING:
                    raise Exception('nothing to skip!')
    
    async def kill(self):
        async with self._aiolocks['kill']:
            # TODO: destruct
            pass

    async def progress(self):
        async with self._aiolocks['player']:
            if self._source:
                return self._source.get_progress()
            else:
                raise Exception('not playing!')

    async def estimate_time_until(self, position):
        async with self._aiolocks['playlist']:
            future = None
            async with self._aiolocks['player']:
                if self.state == PlayerState.DOWNLOADING:
                    self._guild._bot.log.debug('scheduling estimate time after current entry is playing')
                    future = Future()
                    async def call_after_downloaded():
                        future.set_result(await self.estimate_time_until(position))
                    self._play_task.add_done_callback(
                        callback_dummy_future(
                            partial(create_task, call_after_downloaded())
                        )
                    )
                if self._current:
                    estimated_time = self._current.duration
                if self._source:
                    estimated_time -= self._source.get_progress()

            if future:
                estimated_time = await future

            estimated_time = timedelta(seconds=estimated_time)

            estimated_time += await self._playlist.estimate_time_until(position)
            return estimated_time

    async def estimate_time_until_entry(self, entry):
        async with self._aiolocks['playlist']:
            future = None
            async with self._aiolocks['player']:
                if self.state == PlayerState.DOWNLOADING:
                    self._guild._bot.log.debug('scheduling estimate time after current entry is playing')
                    future = Future()
                    async def call_after_downloaded():
                        future.set_result(await self.estimate_time_until_entry(entry))
                    self._play_task.add_done_callback(
                        callback_dummy_future(
                            partial(create_task, call_after_downloaded())
                        )
                    )
                if self._current is entry:
                    return 0
                if self._current:
                    estimated_time = self._current.duration
                    if self._source:
                        estimated_time -= self._source.get_progress()
                else:
                    estimated_time = 0

            if future:
                estimated_time = await future

            estimated_time = timedelta(seconds=estimated_time)
                
            estimated_time += await self._playlist.estimate_time_until_entry(entry)
            return estimated_time

    async def get_current_entry(self):
        async with self._aiolocks['player']:
            return self._current