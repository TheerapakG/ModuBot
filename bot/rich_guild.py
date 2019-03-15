from discord import Guild
from asyncio import Lock
from collections import defaultdict

guilds = dict()

class RichGuild:
    def __init__(self, bot, guildid):
        self._aiolocks = defaultdict(Lock)
        self._bot = bot
        self._id = guildid
        self._voice_channel = None
        self._voice_client = None

    @property
    def id(self):
        return self._id

    @property
    def guild(self):
        return self._bot.get_guild(self._id)

    @property
    def connected_voice_channel(self):
        async with self._aiolocks['c_voice_channel']:
            return self._voice_channel

    async def _move_channel(self, new_channel):
        async with self._aiolocks['c_voice_channel']:
            await self._voice_client.move_to(new_channel)
            self._voice_channel = new_channel

    async def _disconnect_channel(self):
        async with self._aiolocks['c_voice_channel']:
            await self._voice_client.disconnect()
            self.voice_channel = None
            self._voice_client = None

    async def _connect_channel(self, new_channel):
        async with self._aiolocks['c_voice_channel']:
            self._voice_client = await new_channel.connect()
            self.voice_channel = new_channel

    @connected_voice_channel.setter
    def connected_voice_channel(self, voice_channel):
        if self._voice_client:
            if voice_channel:
                self._bot.loop.run_until_complete(self._move_channel(voice_channel))
            else:
                self._bot.loop.run_until_complete(self._disconnect_channel())
        else:
            if voice_channel:
                self._bot.loop.run_until_complete(self._connect_channel(voice_channel))
            else:
                return # @TheerapakG: TODO: raise exc

    @property
    def connected_voice_client(self):
        async with self._aiolocks['c_voice_channel']:
            return self._voice_client

def register_bot(bot):
    guilds[bot.user.id] = {guild.id:RichGuild(bot, guild.id) for guild in bot.guilds}

    async def on_guild_join(guild):
        if bot.is_ready():
            guilds[bot.user.id][guild.id] = RichGuild(bot, guild.id)

    bot.event(on_guild_join)

    async def on_guild_remove(guild):
        if bot.is_ready():
            del guilds[bot.user.id][guild.id]

    bot.event(on_guild_remove)

    async def on_voice_state_update(member, before, after):
        if bot.is_ready():
            c = before.channel
            c = after.channel if not c else c
            guild = c.guild

            if member == bot.user:
                async with guilds[bot.user.id][guild.id]._aiolocks['c_voice_channel']:
                    if not after.channel:
                        guilds[bot.user.id][guild.id]._voice_client = None
                    guilds[bot.user.id][guild.id]._voice_channel = after.channel

    bot.event(on_voice_state_update)