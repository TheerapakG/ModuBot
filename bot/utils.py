import json
import os
import aiohttp
from hashlib import md5

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

def callback_dummy_future(cb):
    def _dummy(future):
        cb()
    return _dummy

def fixg(x, dp=2):
    return ('{:.%sf}' % dp).format(x).rstrip('0').rstrip('.')

def ftimedelta(td):
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