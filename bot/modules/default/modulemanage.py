from discord.ext.commands import Cog, command
from ast import literal_eval # we don't want to erase someone's drive

class ModuleManage(Cog):
    @command()
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

cogs = [ModuleManage]