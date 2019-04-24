import json
import os

def isiterable(x):
    try:
        iter(x)
    except TypeError:
        return False
    else:
        return True

def save_data(guild, filename, data, cls=None):
    with open('data/{}/{}'.format(guild.id, filename), 'w') as fp:
        json.dump(data, fp, cls = cls)

def load_data(guild, filename, cls=None, default = None, defaultdecodecls = None):
    os.makedirs(os.path.dirname('data/{}/{}'.format(guild.id, filename)), exist_ok=True)

    if not os.path.isfile('data/{}/{}'.format(guild.id, filename)):
        with open('data/{}/{}'.format(guild.id, filename), 'w') as fp:
            json.dump(default, fp, cls = defaultdecodecls)
        return default

    with open('data/{}/{}'.format(guild.id, filename), 'r') as fp:
        data = json.load(fp, cls = cls)
    return data

class AsyncListView:
    def __init__(self, li, coro_before, coro_access, coro_after):
        self._list = li
        self._bef = coro_before
        self._acc = coro_access
        self._aft = coro_after

    async def __getitem__(self, item):
        if isinstance(item, slice):
            await self._bef
            ifnone = lambda a, b: b if a is None else a
            ret = [await self._acc(i) for i in range(ifnone(item.start, 0), item.stop, ifnone(item.step, 1))]
            await self._aft
            return ret
                
        else:
            await self._bef
            ret = await self._acc(item)
            await self._aft
            return ret

    