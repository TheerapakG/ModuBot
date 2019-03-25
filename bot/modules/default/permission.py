from discord.ext.commands import Cog, command
from collections import defaultdict

perm_info = dict()

class Permission(Cog):

    @command()
    async def add_permgroup(self, ctx, groupname: str):
        """
        Usage:
            {prefix}add_permgroup groupname

        add permission group in current guild
        """
        perm_info[ctx.bot][groupname] = defaultdict(lambda: None)

    @command()
    async def remove_permgroup(self, ctx, groupname: str):
        """
        Usage:
            {prefix}remove_permgroup groupname

        remove permission group from current guild
        """
        del perm_info[ctx.bot][groupname]

    @command()
    async def set_permgroup(self, ctx, groupname: str, permname: str, *, value: str):
        """
        Usage:
            {prefix}set_permgroup groupname permname value

        set permission of a group in current guild
        """
        perm_info[ctx.bot][groupname][permname] = value

    @command()
    async def literal_displayperm(self, ctx):
        """
        Usage:
            {prefix}literal_displayperm

        display permissions in the server for the bot as dictionary (unformatted form)
        """
        await ctx.send(str(perm_info[ctx.bot]))

def init(bot, permconfig):
    perm_info[bot] = permconfig

def uninit(bot):
    del perm_info[bot]

cogs = [Permission]