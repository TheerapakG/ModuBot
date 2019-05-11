import json
import re
import os
import aiohttp
import discord
from typing import Optional, Callable, Any
from hashlib import md5
from datetime import timedelta

T = TypeVar('T')

def isiterable(x):
    try:
        iter(x)
    except TypeError:
        return False
    else:
        return True

def save_data(guild: discord.Guild, filename: str, data, cls: Optional[json.JSONEncoder] = None) -> None:
    with open('data/{}/{}'.format(guild.id, filename), 'w') as fp:
        json.dump(data, fp, cls = cls)

def load_data(guild: discord.Guild, filename: str, cls: Optional[json.JSONDecoder] = None, default = None, defaultencodecls: Optional[json.JSONEncoder] = None):
    os.makedirs(os.path.dirname('data/{}/{}'.format(guild.id, filename)), exist_ok=True)

    if not os.path.isfile('data/{}/{}'.format(guild.id, filename)):
        with open('data/{}/{}'.format(guild.id, filename), 'w') as fp:
            json.dump(default, fp, cls = defaultencodecls)
        return default

    with open('data/{}/{}'.format(guild.id, filename), 'r') as fp:
        data = json.load(fp, cls = cls)
    return data

def callback_dummy_future(cb: Callable[[], T]) -> T:
    def _dummy(future):
        cb()
    return _dummy

def fixg(x, dp=2):
    return ('{:.%sf}' % dp).format(x).rstrip('0').rstrip('.')

def ftimedelta(td: timedelta):
    p1, p2 = str(td).rsplit(':', 1)
    return ':'.join([p1, '{:02d}'.format(int(float(p2)))])

async def get_header(session, url, headerfield=None, *, timeout=5):
    req_timeout = aiohttp.ClientTimeout(total = timeout)
    async with session.head(url, timeout = req_timeout) as response:
        if headerfield:
            return response.headers.get(headerfield)
        else:
            return response.headers

def md5sum(filename, limit=0):
    fhash = md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            fhash.update(chunk)
    return fhash.hexdigest()[-limit:]

regex_parse_duration = re.compile(r'^((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?$')

def parse_duration(durationstr: str) -> timedelta:
    duration_parts = regex_parse_duration.match(durationstr)
    assert duration_parts is not None
    time_params = {name: float(param) for name, param in duration_parts.groupdict().items() if param}
    duration = timedelta(**time_params)
    return duration