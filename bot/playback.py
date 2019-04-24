from .utils import AsyncListView
from asyncio import Lock, create_task
from enum import Enum
from collections import defaultdict

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
        self._player = None
        self._list = list()
        self._cache_task = list()
        self._precache = precache

    async def set_player(self, player):
        async with self._aiolocks['player']:
            self._player = player

    async def add_entry(self, entry, *, head = False):
        async with self._aiolocks['list']:
            if head:
                self._list.insert(0, entry)
            else:
                self._list.append(entry)

    async def remove_position(self, position):
        async with self._aiolocks['list']:
            del self._list[position]
            if position < self._precache:
                del self._cache_task[position]
                if self._precache <= self._list.count():
                    self._cache_task.append(
                        create_task(self._list[self._precache - 1].prepare_cache())
                        )

    async def get_entry_position(self, entry):
        async with self._aiolocks['list']:
            return self._list.index(entry)

    async def get_metadata_position(self, position):
        async with self._aiolocks['list']:
            return await self._list[position].get_metadata()

    def get_metadata_view(self):
        async def acquire():
            await self._aiolocks['list'].acquire()
        async def access(position):
            return await self._list[position].get_metadata()
        async def release():
            self._aiolocks['list'].release()
        return AsyncListView(self._list, acquire, access, release)


class PlayerState(Enum):
    PLAYING = 0
    PAUSE = 1

class Player:
    pass