from discord.ext.commands import Bot
import asyncio
import logging
import colorlog

from . import config
from .rich_guild import guilds, register_bot

MODUBOT_MAJOR = '0'
MODUBOT_MINOR = '1'
MODUBOT_REVISION = '0'
MODUBOT_VERSIONTYPE = 'a'
MODUBOT_SUBVERSION = '2'
MODUBOT_VERSION = '{}.{}.{}-{}{}'.format(MODUBOT_MAJOR, MODUBOT_MINOR, MODUBOT_REVISION, MODUBOT_VERSIONTYPE, MODUBOT_SUBVERSION)
MODUBOT_STR = 'ModuBot {}'.format(MODUBOT_VERSION)

class ModuBot(Bot):
    def __init__(self, *args, logname = "ModuBot", conf = config.ConfigDefaults, modulelist = [], loghandlerlist = [], **kwargs):
        self.config = conf
        self.log = logging.getLogger(logname)
        for handler in loghandlerlist:
            self.log.addHandler(handler)
        self.log.setLevel(self.config.debug_level)
        super().__init__(command_prefix = self.config.command_prefix, *args, **kwargs)
        self.remove_command('help')

    def load_module(self, modulename):
        pass

    def load_all_module(self):
        pass

    def unload_module(self, modulename):
        pass

    def unload_all_module(self):
        pass

    async def on_ready(self):
        self.log.info("Connected")
        self.log.info("Client:\n    ID: {id}\n    name: {name}#{discriminator}\n".format(
            id = self.user.id,
            name = self.user.name,
            discriminator = self.user.discriminator
            ))
        register_bot(self)

    def run(self):
        self.loop.run_until_complete(self.start(self.config.token))
        self.loop.run_forever()

    def logout(self):
        self.loop.run_until_complete(super().logout())
        self.unload_all_module()
        self.loop.stop()
        gathered = asyncio.gather(*asyncio.Task.all_tasks(), loop=self.loop)
        try:
            gathered.cancel()
            self.loop.run_until_complete(gathered)
            gathered.exception()
        except Exception as e:
            self.log.error(e)
        finally:
            self.log.debug('Closing Loop')
            self.loop.close()
    
