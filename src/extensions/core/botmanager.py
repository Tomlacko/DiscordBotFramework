import discord
from discord.ext import commands
from smart_bot import SmartBot
from smart_cogs import *


"""
Config template:
{
    
}
"""


async def setup(bot: SmartBot):
    await bot.add_cog(BotManagerCog(bot))

async def teardown(bot: SmartBot):
    pass



class BotManagerCog(SmartCog):
    
    def __init__(self, bot: SmartBot):
        super().__init__(bot)
    
    
    @commands.Cog.listener("on_console_input")
    async def console_listener(self, input_line):
        if input_line == "get":
            for cmd in self.bot.tree.get_all_client_commands():
                print((cmd.name, self.bot.tree.get_command_type(cmd), self.bot.tree.get_command_locations(cmd)))
            print(".")
        elif input_line == "fetch":
            for cmd in await self.bot.tree.fetch_all_commands():
                print((cmd.name, cmd.id, cmd.guild_id))
            print(".")
        elif input_line == "sync":
            await self.bot.tree.sync_all(ignore_errors=False)
            print("Synced!")
        elif input_line == "prune":
            await self.bot.tree.sync_all(just_delete=True, ignore_errors=False)
            print("Pruned!")
        elif input_line == "test":
            print(self.bot._connection.max_messages)
            
        elif input_line.startswith("reload "):
            await self.bot.reload_extension(input_line[7:])
        elif input_line.startswith("unload "):
            await self.bot.unload_extension(input_line[7:])
        elif input_line.startswith("load "):
            await self.bot.load_extension(input_line[5:])