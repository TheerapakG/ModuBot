from discord.ext.commands import Bot
import asyncio
import logging
import colorlog
from importlib import import_module, reload
from collections import namedtuple
from inspect import iscoroutinefunction, isfunction
import pkgutil

from . import config
from .utils import isiterable
from .rich_guild import guilds, register_bot
from .crossmodule import CrossModule
from collections import namedtuple

MODUBOT_MAJOR = '0'
MODUBOT_MINOR = '1'
MODUBOT_REVISION = '0'
MODUBOT_VERSIONTYPE = 'b'
MODUBOT_SUBVERSION = '1'
MODUBOT_VERSION = '{}.{}.{}-{}{}'.format(MODUBOT_MAJOR, MODUBOT_MINOR, MODUBOT_REVISION, MODUBOT_VERSIONTYPE, MODUBOT_SUBVERSION)
MODUBOT_STR = 'ModuBot {}'.format(MODUBOT_VERSION)

class ModuBot(Bot):

    ModuleTuple = namedtuple('ModuleTuple', ['name', 'module', 'module_spfc_config'])

    def __init__(self, *args, logname = "ModuBot", conf = config.ConfigDefaults, loghandlerlist = [], **kwargs):
        self.config = conf
        self.crossmodule = CrossModule()
        self.log = logging.getLogger(logname)
        for handler in loghandlerlist:
            self.log.addHandler(handler)
        self.log.setLevel(self.config.debug_level)
        super().__init__(command_prefix = self.config.command_prefix, *args, **kwargs)
        self.help_command = None

    async def _load_modules(self, modulelist):
        # 1: walk module
        #     1: module pre_init
        #         this stage should be use to read up config and prepare things such as opening
        #         port to communicate with server, opening file for logging, register stuff to
        #         crossmodule object (except features), etc. pre_init must throw if not successful
        # 2: walk module again
        #     1: load command, cogs, ...
        #         even if some command, cogs in a module is not loaded, it will not get skip 
        #     2: module init
        #         this stage should be use to check commands in the module that got loaded and
        #         register features available after loaded. init must throw if not successful
        # 3: walk module again
        #     1: module post_init
        #         this stage should be use to check if dependency loaded correctly with features
        #         needed and register dependencies needed. post_init must throw if not successful
        #     2: add to loaded
        for moduleinfo in modulelist:
            if 'pre_init' in dir(moduleinfo.module):
                self.log.debug('executing pre_init in {}'.format(moduleinfo.name))
                potential = getattr(moduleinfo.module, 'pre_init')
                if iscoroutinefunction(potential):
                    await potential(moduleinfo.module_spfc_config)
                elif isfunction(potential):
                    potential(moduleinfo.module_spfc_config)
                else:
                    self.log.debug('pre_init is neither funtion nor coroutine function')

        for moduleinfo in modulelist:
            if 'commands' in dir(moduleinfo.module):
                self.log.debug('loading commands in {}'.format(moduleinfo.name))
                commands = getattr(moduleinfo.module, 'commands')
                if isiterable(commands):
                    for command in commands:
                        self.add_command(command())
                else:
                    self.log.debug('commands is not an iterable')

            if 'cogs' in dir(moduleinfo.module):
                self.log.debug('loading cogs in {}'.format(moduleinfo.name))
                cogs = getattr(moduleinfo.module, 'cogs')
                if isiterable(cogs):
                    for cog in cogs:
                        self.add_cog(cog())
                else:
                    self.log.debug('cogs is not an iterable')


            if 'init' in dir(moduleinfo.module):
                self.log.debug('executing init in {}'.format(moduleinfo.name))
                potential = getattr(moduleinfo.module, 'init')
                if iscoroutinefunction(potential):
                    await potential(moduleinfo.module_spfc_config)
                elif isfunction(potential):
                    potential(moduleinfo.module_spfc_config)
                else:
                    self.log.debug('init is neither funtion nor coroutine function')

        for moduleinfo in modulelist:
            if 'post_init' in dir(moduleinfo.module):
                self.log.debug('executing post_init in {}'.format(moduleinfo.name))
                potential = getattr(moduleinfo.module, 'post_init')
                if iscoroutinefunction(potential):
                    await potential(moduleinfo.module_spfc_config)
                elif isfunction(potential):
                    potential(moduleinfo.module_spfc_config)
                else:
                    self.log.debug('post_init is neither funtion nor coroutine function')
            self.crossmodule._add_module(moduleinfo.name, moduleinfo.module)

    def _prepare_load_module(self, modulename):
        if modulename in self.crossmodule.modules_loaded():
            self._unload_module(modulename)
            reload(self.crossmodule.imported[modulename])
            module = self.crossmodule.imported[modulename]
        else:
            module = import_module('.modules.{}'.format(modulename), 'bot')

        return module

    def _gen_modulelist(self, modulesname_config):
        modules = list()
        for modulename, moduleconfig in modulesname_config:
            modules.append(self.ModuleTuple(modulename, self._prepare_load_module(modulename), moduleconfig))

        return modules

    async def load_modules(self, modulesname_config):
        modulelist = self._gen_modulelist(modulesname_config)
        await self._load_modules(modulelist)

    async def _unload_module(self, module):
        # 1: unload dependents
        # 2: unload command, cogs, ...
        # 3: remove features
        # 4: remove from loaded
        # 5: module uninit
        pass

    async def unload_module(self, modulename):
        pass

    async def unload_all_module(self):
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
        self.loop.run_until_complete(self.unload_all_module())
        self.loop.stop()
        gathered = asyncio.gather(*asyncio.Task.all_tasks(), loop=self.loop)
        gathered.cancel()
        self.log.debug('Closing Loop')
        self.loop.close()
    
