from discord.ext.commands import Cog, command
from ast import literal_eval # we don't want to erase someone's drive
from ...decorator_helper import decorate_cog_command

deps = ['permission']

class ModuleManage(Cog):

    def __init__(self):
        self.bot = None
        self.config = None

    async def pre_init(self, bot, config):
        self.bot = bot
        self.config = config

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