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

from discord.ext.commands import Cog, command
from ast import literal_eval # we don't want to erase someone's drive
from ...decorator_helper import decorate_cog_command

deps = ['permission']

class ModuleManage(Cog):

    def __init__(self):
        self.bot = None

    async def pre_init(self, bot):
        self.bot = bot

    async def init(self):
        self.bot.crossmodule.assign_dict_object('PermType', 'canManageModule', bool)
        self.bot.crossmodule.assign_dict_object('PermissivePerm', 'canManageModule', True)
        self.bot.crossmodule.assign_dict_object('DefaultPerm', 'canManageModule', False)

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canManageModule', True)
    async def load_modules(self, ctx, *, moduleconfigs: str):
        """
        Usage:
            {prefix}load_modules moduleconfigs

        load modules specified by modulesconfig
        modulesconfig should be in the form of
            [(module1_name, module1_config), ...]
        where modulei_config is in the form of
            {modulei_configkey1:modulei_configval1,...}
        """
        msg = await ctx.send('loading specified modules...')
        await ctx.bot.load_modules(literal_eval(moduleconfigs))
        await msg.edit(content = 'loaded successfully!')

    @command()
    @decorate_cog_command('require_perm_cog_command', 'canManageModule', True)
    async def unload_modules(self, ctx, *modules):
        """
        Usage:
            {prefix}unload_modules modules

        unload modules specified
        """
        msg = await ctx.send('unloading specified modules...')
        await ctx.bot.unload_modules(modules)
        await msg.edit(content = 'unloaded successfully!')

cogs = [ModuleManage]