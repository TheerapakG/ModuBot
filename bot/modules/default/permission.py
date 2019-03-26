from discord.ext.commands import Cog, command, CommandError
from collections import defaultdict
from functools import wraps

class Permission(Cog):

    def __init__(self, *args, **kwargs):
        self.bot = None
        self.perm_info = dict()
        super().__init__(self, *args, **kwargs)

    @command()
    async def add_permgroup(self, ctx, groupname: str):
        """
        Usage:
            {prefix}add_permgroup groupname

        add permission group in current guild
        """
        self.perm_info[groupname] = dict()

    @command()
    async def remove_permgroup(self, ctx, groupname: str):
        """
        Usage:
            {prefix}remove_permgroup groupname

        remove permission group from current guild
        """
        del self.perm_info[groupname]

    @command()
    async def set_permgroup(self, ctx, groupname: str, permname: str, *, value: str):
        """
        Usage:
            {prefix}set_permgroup groupname permname value

        set permission of a group in current guild
        """
        self.perm_info[groupname][permname] = value

    @command()
    async def literal_displayperm(self, ctx):
        """
        Usage:
            {prefix}literal_displayperm

        display permissions in the server for the bot as dictionary (unformatted form)
        """
        await ctx.send(str(self.perm_info))

    # THEEABRVSPF DUMMY
    @staticmethod
    def require_perm_cog(self, name, value):
        def decorate_use_name(func):
            @wraps(func)
            def wrapper(self, ctx, *args, **kwargs):
                return func(self, ctx, *args, **kwargs)
            return wrapper
        return decorate_use_name

    def pre_init(self, bot, permconfig):
        self.bot = bot
        self.perm_info = permconfig
        bot.crossmodule.register_decorator(self.require_perm_cog)

    def uninit(self, bot):
        del self.perm_info[bot]

class PermError(CommandError):
    pass

cogs = [Permission]