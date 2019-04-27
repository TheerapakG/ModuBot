from discord import Guild
from asyncio import Lock
from collections import defaultdict
from .playback import Player

guilds = dict()

class RichGuild:
    def __init__(self, bot, guildid):
        self._aiolocks = defaultdict(Lock)
        self._bot = bot
        self._id = guildid
        self._voice_channel = None
        self._voice_client = None
        self._player = None

    @property
    def id(self):
        return self._id

    @property
    def guild(self):
        return self._bot.get_guild(self._id)

    async def get_connected_voice_channel(self):
        async with self._aiolocks['c_voice_channel']:
            return self._voice_channel

    async def _check_perm_connect(self, channel):
        perms = channel.permissions_for(self.guild.me)
        if not perms.connect:
            raise Exception('Cannot join channel, no permission to connect.')
        elif not perms.speak:
            raise Exception('Cannot join channel, no permission to speak.')

    async def _move_channel(self, new_channel):
        await self._check_perm_connect(new_channel)
        async with self._aiolocks['c_voice_channel']:
            await self._voice_client.move_to(new_channel)
            self._voice_channel = new_channel

    async def _disconnect_channel(self):
        async with self._aiolocks['c_voice_channel']:
            await self._voice_client.disconnect()
            self.voice_channel = None
            self._voice_client = None
            self._player = None

    async def _connect_channel(self, new_channel):
        await self._check_perm_connect(new_channel)
        async with self._aiolocks['c_voice_channel']:
            self._voice_client = await new_channel.connect()
            self.voice_channel = new_channel
            self._player = Player(self.voice_channel)

    async def set_connected_voice_channel(self, voice_channel):
        if self._voice_client:
            if voice_channel:
                await self._move_channel(voice_channel)
            else:
                await self._disconnect_channel()
        else:
            if voice_channel:
                await self._connect_channel(voice_channel)
            else:
                raise Exception("bot is not connected to any voice channel")

    async def get_connected_voice_client(self):
        async with self._aiolocks['c_voice_channel']:
            return self._voice_client

    async def get_player(self):
        async with self._aiolocks['c_voice_channel']:
            if self._player:
                return self._player
            else:
                raise Exception("bot is not connected to any voice channel")

def get_guild(bot, guild) -> RichGuild:
    return guilds[bot.user.id][guild.id]

def register_bot(bot):
    guilds[bot.user.id] = {guild.id:RichGuild(bot, guild.id) for guild in bot.guilds}

    async def on_guild_join(guild):
        if bot.is_ready():
            guilds[bot.user.id][guild.id] = RichGuild(bot, guild.id)
            bot.log.info('joined guild {}'.format(guild.name))

    bot.event(on_guild_join)

    async def on_guild_remove(guild):
        if bot.is_ready():
            del guilds[bot.user.id][guild.id]
            bot.log.info('removed guild {}'.format(guild.name))

    bot.event(on_guild_remove)

    async def on_voice_state_update(member, before, after):
        if bot.is_ready():
            c = before.channel
            c = after.channel if not c else c
            guild = c.guild

            if member == bot.user:
                async with guilds[bot.user.id][guild.id]._aiolocks['c_voice_channel']:
                    rguild = get_guild(bot, guild)
                    if not after.channel:
                        rguild._voice_client = None
                        await rguild._player.kill()
                        rguild._player = None
                    rguild._voice_channel = after.channel
            bot.log.info('member {}#{} changed voice state in guild {}'.format(member.name, member.discriminator, guild.name))

    bot.event(on_voice_state_update)