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

import json
import os
import re
from datetime import timedelta
from hashlib import md5
from typing import Any, Callable, Optional, TypeVar

import aiohttp
import discord

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
