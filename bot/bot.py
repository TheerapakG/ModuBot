from discord.ext.commands import Bot
import asyncio
import logging
import colorlog

from . import config
from .rich_guild import guilds, register_bot
from .crossmodule import CrossModule

MODUBOT_MAJOR = '0'
MODUBOT_MINOR = '1'
MODUBOT_REVISION = '0'
MODUBOT_VERSIONTYPE = 'a'
MODUBOT_SUBVERSION = '5'
MODUBOT_VERSION = '{}.{}.{}-{}{}'.format(MODUBOT_MAJOR, MODUBOT_MINOR, MODUBOT_REVISION, MODUBOT_VERSIONTYPE, MODUBOT_SUBVERSION)
MODUBOT_STR = 'ModuBot {}'.format(MODUBOT_VERSION)

class ModuBot(Bot):
    def __init__(self, *args, logname = "ModuBot", conf = config.ConfigDefaults, modulelist = [], loghandlerlist = [], **kwargs):
        self.config = conf
        self.crossmodule = CrossModule()
        self.log = logging.getLogger(logname)
        for handler in loghandlerlist:
            self.log.addHandler(handler)
        self.log.setLevel(self.config.debug_level)
        super().__init__(command_prefix = self.config.command_prefix, *args, **kwargs)
        self.help_command = None

    def load_module(self, modulename):
        # 1: walk submodule
        #     1: submodule pre_init
        #         this stage should be use to read up config and prepare things such as opening
        #         port to communicate with server, opening file for logging, register stuff to
        #         crossmodule object (except features), etc. pre_init must return true if it was
        #         successful else return false
        # 2: walk submodule again
        #     1: load command, group, cogs, ...
        #         even if some command, group, cogs in a module is not loaded, it will not get skip 
        #     2: submodule init
        #         this stage should be use to check commands in the module that got loaded and
        #         register features available after loaded. init must return true if it was
        #         successful else return false
        # 3: walk submodule again
        #     1: submodule post_init
        #         this stage should be use to check if dependency loaded correctly with features
        #         needed. post_init must return true if it was successful else return false
        pass

    def load_all_module(self):
        pass

    def unload_module(self, modulename):
        # 1: unload dependents
        # 2: unload command, group, cogs, ...
        # 3: remove features
        # 4: submodule uninit
        pass

    def unload_all_module(self):
        pass

    def register_dependency(self, module, deps_module_list = []):
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
    
