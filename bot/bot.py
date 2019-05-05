from discord.ext.commands import Bot
import asyncio
import logging
import colorlog
from importlib import import_module, reload
from collections import namedtuple
from inspect import iscoroutinefunction, isfunction
from functools import partial, wraps
import pkgutil
import sys

from . import config
from .utils import isiterable
from .rich_guild import guilds, register_bot
from .crossmodule import CrossModule
from collections import namedtuple, deque, defaultdict
import threading
import traceback

MODUBOT_MAJOR = '0'
MODUBOT_MINOR = '1'
MODUBOT_REVISION = '2'
MODUBOT_VERSIONTYPE = 'a'
MODUBOT_SUBVERSION = '20'
MODUBOT_VERSION = '{}.{}.{}-{}{}'.format(MODUBOT_MAJOR, MODUBOT_MINOR, MODUBOT_REVISION, MODUBOT_VERSIONTYPE, MODUBOT_SUBVERSION)
MODUBOT_STR = 'ModuBot {}'.format(MODUBOT_VERSION)

class ModuBot(Bot):

    ModuleTuple = namedtuple('ModuleTuple', ['name', 'module', 'module_spfc_config'])

    def __init__(self, *args, logname = "ModuBot", conf = config.ConfigDefaults, loghandlerlist = [], **kwargs):
        self.bot_version = (MODUBOT_MAJOR, MODUBOT_MINOR, MODUBOT_REVISION, MODUBOT_VERSIONTYPE, MODUBOT_SUBVERSION)
        self.bot_str = MODUBOT_STR
        self.thread = None
        self.config = conf
        self.crossmodule = CrossModule()
        self.log = logging.getLogger(logname)
        for handler in loghandlerlist:
            self.log.addHandler(handler)
        self.log.setLevel(self.config.debug_level)
        super().__init__(command_prefix = self.config.command_prefix, *args, **kwargs)
        self.help_command = None
        self.looplock = threading.Lock()
        self._init = False

        self._owner_id = None
        if self.config.owner_id.isdigit():
            self._owner_id = int(self.config.owner_id)
        elif self.config.owner_id:
            self._owner_id = self.config.owner_id

    async def _load_modules(self, modulelist):
        # TODO: change into cog pre_init, cog init and cog post_init/ deps listing inside cogs
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
        # 4: walk module again
        #     1: module after_init
        #         this means that stuff in crossmodule is safe to be retrieve. shall not fail

        load_cogs = []

        available_module = set(self.crossmodule.imported.keys())

        for moduleinfo in modulelist:
            available_module.add(moduleinfo.name)

        requirements = defaultdict(list)

        for moduleinfo in modulelist:

            if 'deps' in dir(moduleinfo.module):
                self.log.debug('resolving deps in {}'.format(moduleinfo.name))
                deps = getattr(moduleinfo.module, 'deps')
                if isiterable(deps):
                    for dep in deps:
                        requirements[dep].append(moduleinfo.name)
                else:
                    self.log.debug('deps is not an iterable')

        req_set = set(requirements.keys())

        noreq_already = req_set - available_module
        noreq = list(noreq_already)

        req_not_met = set()

        while noreq:
            current = noreq.pop()
            req_not_met.update(requirements[current])
            for module in requirements[current]:
                if module not in noreq_already:
                    noreq.append(module)
                    noreq_already.add(module)

        if req_not_met:
            self.log.warning('These following modules does not have dependencies required and will not be loaded: {}'.format(str(req_not_met)))

        modulelist = [moduleinfo for moduleinfo in modulelist if moduleinfo.name not in req_not_met]

        for moduleinfo in modulelist:
            self.crossmodule._add_module(moduleinfo.name, moduleinfo.module)

        for moduleinfo in modulelist:
            if 'deps' in dir(moduleinfo.module):
                self.log.debug('adding deps in {}'.format(moduleinfo.name))
                deps = getattr(moduleinfo.module, 'deps')
                if isiterable(deps):
                    self.crossmodule._register_dependency(moduleinfo.name, deps)
                else:
                    self.log.debug('deps is not an iterable')

        for moduleinfo in modulelist:
            if 'cogs' in dir(moduleinfo.module):
                cogs = getattr(moduleinfo.module, 'cogs')
                if isiterable(cogs):
                    for cog in cogs:
                        cg = cog()
                        if 'pre_init' in dir(cg):
                            self.log.debug('executing pre_init in {}'.format(cg.qualified_name))
                            potential = getattr(cg, 'pre_init')
                            self.log.debug(str(potential))
                            self.log.debug(str(potential.__func__))
                            try:
                                if iscoroutinefunction(potential.__func__):
                                    await potential(self, moduleinfo.module_spfc_config)
                                elif isfunction(potential.__func__):
                                    potential(self, moduleinfo.module_spfc_config)
                                else:
                                    self.log.debug('pre_init is neither funtion nor coroutine function')
                            except Exception:
                                self.log.warning('failed pre-initializing cog {} in module {}'.format(cg.qualified_name, moduleinfo.name))
                                self.log.debug(traceback.format_exc())
                        load_cogs.append((moduleinfo.name, cg))
                else:
                    self.log.debug('cogs is not an iterable')

        for moduleinfo in modulelist:
            if 'commands' in dir(moduleinfo.module):
                self.log.debug('loading commands in {}'.format(moduleinfo.name))
                commands = getattr(moduleinfo.module, 'commands')
                if isiterable(commands):
                    for command in commands:
                        cmd = command()
                        self.add_command(cmd)
                        self.crossmodule._commands[moduleinfo.name].append(cmd.name)
                        self.log.debug('loaded {}'.format(cmd.name))
                else:
                    self.log.debug('commands is not an iterable')

        for modulename, cog in load_cogs.copy():
            if 'init' in dir(cog):
                self.log.debug('executing init in {}'.format(cog.qualified_name))
                potential = getattr(cog, 'init')
                self.log.debug(str(potential))
                self.log.debug(str(potential.__func__))
                try:
                    if iscoroutinefunction(potential.__func__):
                        await potential()
                    elif isfunction(potential.__func__):
                        potential()
                    else:
                        self.log.debug('init is neither funtion nor coroutine function')
                except Exception:
                    self.log.warning('failed initializing cog {} in module {}'.format(cog.qualified_name, modulename))
                    self.log.debug(traceback.format_exc())
                    load_cogs.remove((modulename, cog))

        for modulename, cog in load_cogs:
            if 'post_init' in dir(cog):
                self.log.debug('executing post_init in {}'.format(cog.qualified_name))
                potential = getattr(cog, 'post_init')
                self.log.debug(str(potential))
                self.log.debug(str(potential.__func__))
                try:
                    if iscoroutinefunction(potential.__func__):
                        await potential()
                    elif isfunction(potential.__func__):
                        potential()
                    else:
                        self.log.debug('post_init is neither funtion nor coroutine function')
                except Exception:
                    self.log.warning('failed post-initializing cog {} in module {}'.format(cog.qualified_name, modulename))
                    self.log.debug(traceback.format_exc())
                    load_cogs.remove((modulename, cog))

        self.log.debug('loading cogs')
        for modulename, cog in load_cogs:
            self.add_cog(cog)
            self.crossmodule._cogs[modulename].append(cog)
            self.log.debug('loaded {}'.format(cog.qualified_name))

        for modulename, cog in load_cogs:
            if 'after_init' in dir(cog):
                self.log.debug('executing after_init in {}'.format(cog.qualified_name))
                potential = getattr(cog, 'after_init')
                self.log.debug(str(potential))
                self.log.debug(str(potential.__func__))
                try:
                    if iscoroutinefunction(potential.__func__):
                        await potential()
                    elif isfunction(potential.__func__):
                        potential()
                    else:
                        self.log.debug('after_init is neither funtion nor coroutine function')
                except Exception:
                    self.log.error('cog {} in module {} raised exception after initialization'.format(cog.qualified_name, modulename))
                    self.log.debug(traceback.format_exc())
                    self.remove_cog(cog)
                    self.crossmodule._cogs[modulename].remove(cog)

    async def _prepare_load_module(self, modulename):
        if modulename in self.crossmodule.modules_loaded():
            await self.unload_modules([modulename])
            try:
                reload(self.crossmodule.imported[modulename])
            except:
                pass
            module = self.crossmodule.imported[modulename]
        else:
            try:
                module = import_module('.modules.{}'.format(modulename), 'bot')
            except:
                pass
                return

        return module

    async def _gen_modulelist(self, modulesname_config):
        modules = list()
        for modulename, moduleconfig in modulesname_config:
            module = await self._prepare_load_module(modulename)
            if module:
                modules.append(self.ModuleTuple(modulename, module, moduleconfig))

        return modules

    async def load_modules(self, modulesname_config):
        modulelist = await self._gen_modulelist(modulesname_config)
        await self._load_modules(modulelist)

    async def unload_modules(self, modulenames, *, unimport = False):
        # 1: unload dependents
        # 2: unload command, cogs, ...
        # 4: remove from loaded
        # 5: module uninit
        def gendependentlist():
            deplist = list()
            considerdeque = deque(modulenames)
            considerset = set(modulenames)
            while considerdeque:
                node = considerdeque.pop()
                deplist.append(node)
                for module in self.crossmodule._module_graph[node]:
                    if module not in considerset:
                        considerdeque.append(module)
                        considerset.add(module)
            return deplist

        unloadlist = gendependentlist()
        unloadlist.reverse()

        for module in unloadlist:
            for cog in self.crossmodule._cogs[module]:
                if 'uninit' in dir(cog):
                    self.log.debug('executing uninit in {}'.format(cog.qualified_name))
                    potential = getattr(cog, 'uninit')
                    self.log.debug(str(potential))
                    self.log.debug(str(potential.__func__))
                    if iscoroutinefunction(potential.__func__):
                        await potential()
                    elif isfunction(potential.__func__):
                        potential()
                    else:
                        self.log.debug('uninit is neither funtion nor coroutine function')
                self.remove_cog(cog)
            for command in self.crossmodule._cogs[module]:
                self.remove_command(command)
            
            self.crossmodule._remove_module(module)
            self.log.debug('unloaded {}'.format(module))

            if unimport:
                def _is_submodule(parent, child):
                    return parent == child or child.startswith(parent + ".")

                for p_submodule in list(sys.modules.keys()):
                    if _is_submodule(module, p_submodule):
                        del sys.modules[p_submodule]

                self.log.debug('unimported {}'.format(module))

    async def unload_all_module(self):
        await self.unload_modules(self.crossmodule.modules_loaded())

    async def on_ready(self):
        self.log.info("Connected")
        self.log.info("Client:\n    ID: {id}\n    name: {name}#{discriminator}\n".format(
            id = self.user.id,
            name = self.user.name,
            discriminator = self.user.discriminator
            ))
        register_bot(self)

        app_info = await self.application_info()

        if self._owner_id == 'auto' or not self._owner_id:
            self.log.info('Using application\'s owner')
            self._owner_id = app_info.owner.id

        else:
            if not self.get_user(self._owner_id):
                self.log.warning('Cannot find specified owner, falling back to application\'s owner')
                self._owner_id = app_info.owner.id            

        self.log.info("Owner:\n    ID: {id}\n    name: {name}#{discriminator}\n".format(
            id = self._owner_id,
            name = self.get_user(self._owner_id).name,
            discriminator = self.get_user(self._owner_id).discriminator
            ))

        self._init = True

        for name, cog in self.cogs.items():
            if 'on_ready' in dir(cog):
                self.log.debug('executing on_ready in {}'.format(name))
                potential = getattr(cog, 'on_ready')
                self.log.debug(str(potential))
                self.log.debug(str(potential.__func__))
                if iscoroutinefunction(potential.__func__):
                    await potential()
                elif isfunction(potential.__func__):
                    potential()
                else:
                    self.log.debug('post_init is neither funtion nor coroutine function')


    def run(self):
        self.thread = threading.currentThread()
        self.log.debug('running bot on thread {}'.format(threading.get_ident()))
        self.looplock.acquire()
        self.loop.create_task(self.start(self.config.token))
        self.loop.run_forever()

    async def _logout(self):
        await super().logout()
        await self.unload_all_module()
        self.log.debug('finished cleaning up')

    def logout_loopstopped(self):
        self.log.debug('on thread {}'.format(threading.get_ident()))
        self.log.info('logging out (loopstopped)..')
        self.loop.run_until_complete(self._logout())
        self.log.info('canceling incomplete tasks...')
        gathered = asyncio.gather(*asyncio.Task.all_tasks(self.loop), loop=self.loop)
        gathered.cancel()
        self.log.info('closing loop...')
        self.loop.close()
        self.log.info('finished!')

    def logout_looprunning(self):
        async def _stop():
            self.loop.stop()
            self.looplock.release()

        self.log.debug('on thread {}'.format(threading.get_ident()))
        self.log.debug('bot\'s thread status: {}'.format(self.thread.is_alive()))
        self.log.info('logging out (looprunning)..')
        future = asyncio.run_coroutine_threadsafe(self._logout(), self.loop)
        future.result()
        self.log.debug('stopping loop...')
        future = asyncio.run_coroutine_threadsafe(_stop(), self.loop)
        self.looplock.acquire()
        self.log.info('canceling incomplete tasks...')
        gathered = asyncio.gather(*asyncio.Task.all_tasks(self.loop), loop=self.loop)
        gathered.cancel()
        self.log.info('closing loop...')
        self.loop.close()
        self.log.info('finished!')

    def logout(self):
        self.log.info('logging out...')
        if self.loop.is_running():
            self.logout_looprunning()
        else:
            self.logout_loopstopped()

    class check_online:
        def __call__(self, func):
            @wraps(func)
            async def wrapper(bot, *args, **kwargs):
                if bot._init:
                    return await func(bot, *args, **kwargs)
                else:
                    raise Exception('bot is not online')
            return wrapper

    @check_online()
    async def get_owner_id(self):
        return self._owner_id

    def online(self):
        return self._init