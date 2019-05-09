from discord.ext.commands import Cog, command, CommandError
from discord import Member, Role
from collections import defaultdict
from functools import wraps, partial, update_wrapper
from ...utils import save_data, load_data
from ...typing_conv import check_typing
from ast import literal_eval

permtype = {
    'canModifyPermission': bool
}

permissive = {
    'canModifyPermission': True
}

default = {
    'canModifyPermission': False
}

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
        self.guild_loaded = set()
        self.perms = dict()
        self.perm_info = dict()
        self.perm_member = dict()
        self.perm_role = dict()
        self.perm_type = dict()
        self.perm_permissive = dict()
        self.perm_default = dict()

    async def pre_init(self, bot, config):
        self.bot = bot
        self.perm_info = config
        bot.crossmodule.register_object('have_perm', self.have_perm)
        bot.crossmodule.register_decorator(update_wrapper(partial(self.require_perm_cog_command, coginst = self), self.require_perm_cog_command))
        bot.crossmodule.register_object('PermType', permtype.copy())
        bot.crossmodule.register_object('PermissivePerm', permissive.copy())
        bot.crossmodule.register_object('DefaultPerm', default.copy())

        if self.bot.online():
            for guild in self.bot.guilds:
                self.perms[guild.id] = load_data(guild, 'permission/perms.txt', default = list())
                self.perm_info[guild.id] = load_data(guild, 'permission/perm_info.txt', default = dict())
                self.perm_member[guild.id] = load_data(guild, 'permission/perm_member.txt', default = dict())
                self.perm_role[guild.id] = load_data(guild, 'permission/perm_role.txt', default = dict())
                self.guild_loaded.add(guild.id)

    async def after_init(self):
        self.perm_type = self.bot.crossmodule.get_object('PermType')
        self.perm_permissive = self.bot.crossmodule.get_object('PermissivePerm')
        self.perm_default = self.bot.crossmodule.get_object('DefaultPerm')

    async def on_ready(self):
        self.bot.log.debug('owner id: {}'.format(await self.bot.get_owner_id()))

        for guild in self.bot.guilds:
            if guild.id not in self.guild_loaded:
                self.perms[guild.id] = load_data(guild, 'permission/perms.txt', default = list())
                self.perm_info[guild.id] = load_data(guild, 'permission/perm_info.txt', default = dict())
                self.perm_member[guild.id] = load_data(guild, 'permission/perm_member.txt', default = dict())
                self.perm_role[guild.id] = load_data(guild, 'permission/perm_role.txt', default = dict())
                self.guild_loaded.add(guild.id)
    
    @command()
    @require_perm_cog_command('canModifyPermission', True)
    async def add_permgroup(self, ctx, groupname: str):
        """
        Usage:
            {prefix}add_permgroup groupname

        add permission group in current guild
        """
        if groupname not in self.perms:
            self.perms[ctx.guild.id].append(groupname)
            self.perm_info[ctx.guild.id][groupname] = dict()
            self.perm_member[ctx.guild.id][groupname] = set()
            self.perm_role[ctx.guild.id][groupname] = set()

    @command()
    @require_perm_cog_command('canModifyPermission', True)
    async def remove_permgroup(self, ctx, groupname: str):
        """
        Usage:
            {prefix}remove_permgroup groupname

        remove permission group from current guild
        """
        self.perms[ctx.guild.id].remove(groupname)
        del self.perm_info[ctx.guild.id][groupname]
        del self.perm_member[ctx.guild.id][groupname]
        del self.perm_role[ctx.guild.id][groupname]

    @command()
    @require_perm_cog_command('canModifyPermission', True)
    async def set_permgroup(self, ctx, groupname: str, permname: str, *, value: str):
        """
        Usage:
            {prefix}set_permgroup groupname permname value

        set permission of a group in current guild
        """
        passed_val = literal_eval(value)
        if permname in self.perm_type:
            ctx.bot.log.debug('perm type: {}'.format(self.perm_type[permname]))
        # TODO: user-defined conv
        if permname not in self.perm_type or check_typing(passed_val, self.perm_type[permname]):
            self.perm_info[ctx.guild.id][groupname][permname] = passed_val
        else:
            await ctx.send('check the value specified')

    @command()
    @require_perm_cog_command('canModifyPermission', True)
    async def add_member(self, ctx, groupname: str, member: Member):
        """
        Usage:
            {prefix}add_member groupname member

        add member to permission group
        """
        self.perm_member[ctx.guild.id][groupname].add(member.id)

    @command()
    @require_perm_cog_command('canModifyPermission', True)
    async def remove_member(self, ctx, groupname: str, member: Member):
        """
        Usage:
            {prefix}remove_member groupname member

        remove member from permission group
        """
        self.perm_member[ctx.guild.id][groupname].remove(member.id)

    @command()
    @require_perm_cog_command('canModifyPermission', True)
    async def add_role(self, ctx, groupname: str, role: Role):
        """
        Usage:
            {prefix}add_role groupname member

        add role to permission group
        """
        self.perm_role[ctx.guild.id][groupname].add(role.id)

    @command()
    @require_perm_cog_command('canModifyPermission', True)
    async def remove_role(self, ctx, groupname: str, role: Role):
        """
        Usage:
            {prefix}remove_role groupname member

        remove role from permission group
        """
        self.perm_role[ctx.guild.id][groupname].remove(role.id)

    @command()
    @require_perm_cog_command('canModifyPermission', True)
    async def literal_displayperminfo(self, ctx):
        """
        Usage:
            {prefix}literal_displayperminfo

        display permission info in the server for the bot as dictionary (unformatted form)
        """
        await ctx.send(str(self.perm_info[ctx.guild.id]))

    async def have_perm(self, member, perm, value, comparer = lambda permvalue, requirevalue: permvalue == requirevalue):
        roles = member.roles

        skip_owner_check = False

        for group in self.perms[member.guild.id]:
            if perm in self.perm_info[member.guild.id][group]:
                permcheck = comparer(self.perm_info[member.guild.id][group][perm], value)
                if member.id in self.perm_member[member.guild.id][group]:
                    if permcheck:
                        return True
                    skip_owner_check = True
                for role in roles:
                    if role.id in self.perm_role[member.guild.id][group]:
                        if permcheck:
                            return True
                        skip_owner_check = True

        if not skip_owner_check and member.id == await self.bot.get_owner_id():
            if comparer(self.perm_permissive[perm], value):
                return True

        return comparer(self.perm_default[perm], value)

class PermError(CommandError):
    pass

cogs = [Permission]