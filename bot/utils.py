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
    