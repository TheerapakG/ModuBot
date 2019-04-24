from .utils import AsyncListView
from asyncio import Lock

class Entry:
    async def get_metadata(self):
        pass

class Playlist:
    def __init__(self, predownload = 1):
        self._list = list()
        self._lock = Lock()
        self._predownload = predownload

    async def add_entry(self, entry, *, head = False):
        async with self._lock:
            if head:
                self._list.insert(0, entry)
            else:
                self._list.append(entry)

    async def remove_position(self, position):
        async with self._lock:
            del self._list[position]

    async def remove_entry(self, entry):
        async with self._lock:
            self._list.remove(entry)

    async def get_metadata_position(self, position):
        async with self._lock:
            return await self._list[position].get_metadata()

    def get_metadata_view(self):
        async def acquire():
            await self._lock.acquire()
        async def access(position):
            return await self._list[position].get_metadata()
        async def release():
            self._lock.release()
        return AsyncListView(self._list, acquire, access, release)


class PlayerState:
    pass

class Player:
    pass