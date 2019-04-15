from discord.ext.commands import Cog, command, CommandError
from discord import Member, Role
from collections import defaultdict
from functools import wraps, partial, update_wrapper

class Permission(Cog):

    class require_perm_cog_command:
        def __init__(self, perm, value, comparer = lambda permvalue, requirevalue: permvalue == requirevalue, *, coginst = None):
            self.coginst = coginst
            self.perm = perm
            self.value = value
            self.comparer = comparer

        def __call__(self, func):
            @wraps(func)
            async def wrapper(funcself, ctx, *args, **kwargs):
                if not self.coginst:
                    self.coginst = funcself
                if await self.coginst.have_perm(ctx.author, self.perm, self.value, self.comparer):
                    return await func(funcself, ctx, *args, **kwargs)
                else:
                    raise PermError('User do not have the required permission')
            return wrapper

    def __init__(self):
        self.bot = None
        self.perms = list()
        self.perm_info = dict()
        self.perm_member = dict()
        self.perm_role = dict()
        self.perm_permissive = dict()

    async def pre_init(self, bot, config):
        self.bot = bot
        self.perm_info = config
        bot.crossmodule.register_decorator(update_wrapper(partial(self.require_perm_cog_command, coginst = self), self.require_perm_cog_command))
        bot.crossmodule.register_object('PermissivePerm', dict())

    async def after_init(self):
        self.perm_permissive = self.bot.crossmodule.get_object('PermissivePerm')

    async def on_ready(self):
        self.bot.log.debug('owner id: {}'.format(await self.bot.get_owner_id()))
    
    @command()
    @require_perm_cog_command('canModifyPermission', 'True')
    async def add_permgroup(self, ctx, groupname: str):
        """
        Usage:
            {prefix}add_permgroup groupname

        add permission group in current guild
        """
        if groupname not in self.perms:
            self.perms.append(groupname)
            self.perm_info[groupname] = dict()
            self.perm_member[groupname] = set()
            self.perm_role[groupname] = set()

    @command()
    @require_perm_cog_command('canModifyPermission', 'True')
    async def remove_permgroup(self, ctx, groupname: str):
        """
        Usage:
            {prefix}remove_permgroup groupname

        remove permission group from current guild
        """
        self.perms.remove(groupname)
        del self.perm_info[groupname]
        del self.perm_member[groupname]
        del self.perm_role[groupname]

    @command()
    @require_perm_cog_command('canModifyPermission', 'True')
    async def set_permgroup(self, ctx, groupname: str, permname: str, *, value: str):
        """
        Usage:
            {prefix}set_permgroup groupname permname value

        set permission of a group in current guild
        """
        self.perm_info[groupname][permname] = value

    @command()
    @require_perm_cog_command('canModifyPermission', 'True')
    async def add_member(self, ctx, groupname: str, member: Member):
        """
        Usage:
            {prefix}add_member groupname member

        add member to permission group
        """
        self.perm_member[groupname].add(member.id)

    @command()
    @require_perm_cog_command('canModifyPermission', 'True')
    async def remove_member(self, ctx, groupname: str, member: Member):
        """
        Usage:
            {prefix}remove_member groupname member

        remove member from permission group
        """
        self.perm_member[groupname].remove(member.id)

    @command()
    @require_perm_cog_command('canModifyPermission', 'True')
    async def add_role(self, ctx, groupname: str, role: Role):
        """
        Usage:
            {prefix}add_role groupname member

        add role to permission group
        """
        self.perm_role[groupname].add(role.id)

    @command()
    @require_perm_cog_command('canModifyPermission', 'True')
    async def remove_role(self, ctx, groupname: str, role: Role):
        """
        Usage:
            {prefix}remove_role groupname member

        remove role from permission group
        """
        self.perm_role[groupname].remove(role.id)

    @command()
    @require_perm_cog_command('canModifyPermission', 'True')
    async def literal_displayperminfo(self, ctx):
        """
        Usage:
            {prefix}literal_displayperminfo

        display permission info in the server for the bot as dictionary (unformatted form)
        """
        await ctx.send(str(self.perm_info))

    async def have_perm(self, member, perm, value, comparer):
        roles = member.roles

        # TODO: make it so owner can override this
        if member.id == await self.bot.get_owner_id():
            if comparer(self.perm_permissive[perm], value):
                return True

        for group in self.perms:
            if comparer(self.perm_info[group][perm], value):
                if member.id in self.perm_member[group]:
                    return True
                for role in roles:
                    if role.id in self.perm_role[group]:
                        return True

        return False

class PermError(CommandError):
    pass

cogs = [Permission]