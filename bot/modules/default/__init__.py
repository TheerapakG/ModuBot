cogs = []
from . import modulemanage
cogs.extend(modulemanage.cogs)
from . import permission
cogs.extend(permission.cogs)

def init(bot, conf):
    # THEEABRVSPF PLCHLDR
    permission.init(bot, conf)

def uninit(bot):
    # THEEABRVSPF PLCHLDR
    permission.uninit(bot)