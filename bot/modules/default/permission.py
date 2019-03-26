from discord.ext.commands import Cog, command, CommandError
from discord import Member, Role
from collections import defaultdict
from functools import wraps

class Permission(Cog):

    def __init__(self):
        self.bot = None
        self.perms = list()
        self.perm_info = dict()
        self.perm_user = dict()
        self.perm_role = dict()

    @command()
    async def add_permgroup(self, ctx, groupname: str):
        """
        Usage:
            {prefix}add_permgroup groupname

        add permission group in current guild
        """
        if groupname not in self.perms:
            self.perms.append(groupname)
            self.perm_info[groupname] = dict()
            self.perm_user[groupname] = set()
            self.perm_role[groupname] = set()

    @command()
    async def remove_permgroup(self, ctx, groupname: str):
        """
        Usage:
            {prefix}remove_permgroup groupname

        remove permission group from current guild
        """
        self.perms.remove(groupname)
        del self.perm_info[groupname]
        del self.perm_user[groupname]
        del self.perm_role[groupname]

    @command()
    async def set_permgroup(self, ctx, groupname: str, permname: str, *, value: str):
        """
        Usage:
            {prefix}set_permgroup groupname permname value

        set permission of a group in current guild
        """
        self.perm_info[groupname][permname] = value

    @command()
    async def add_user(self, ctx, groupname: str, member: Member):
        """
        Usage:
            {prefix}add_user groupname member

        add user to permission group
        """
        self.perm_user[groupname].add(member.id)

    @command()
    async def remove_user(self, ctx, groupname: str, member: Member):
        """
        Usage:
            {prefix}remove_user groupname member

        remove user from permission group
        """
        self.perm_user[groupname].remove(member.id)

    @command()
    async def add_role(self, ctx, groupname: str, role: Role):
        """
        Usage:
            {prefix}add_role groupname member

        add role to permission group
        """
        self.perm_role[groupname].add(role.id)

    @command()
    async def remove_role(self, ctx, groupname: str, role: Role):
        """
        Usage:
            {prefix}remove_role groupname member

        remove role from permission group
        """
        self.perm_role[groupname].remove(role.id)

    @command()
    async def literal_displayperminfo(self, ctx):
        """
        Usage:
            {prefix}literal_displayperminfo

        display permission info in the server for the bot as dictionary (unformatted form)
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

class PermError(CommandError):
    pass

cogs = [Permission]