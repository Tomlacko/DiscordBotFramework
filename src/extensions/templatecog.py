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
    await bot.add_cog(TemplateCog(bot))

async def teardown(bot: SmartBot):
    pass



class TemplateCog(SmartCog):
    """Template."""
    
    #DEPENDENCIES = []
    
    
    def __init__(self, bot: SmartBot):
        super().__init__(bot)
        print("Initializing template cog!")


    async def cog_load(self):
        print("Template cog is async initialized!")
        await super().cog_load()
    
    
    async def cog_unload(self):
        print("Async unloading template cog!")
        await super().cog_unload()
    
    
    @run_when_ready
    async def ready_init(self):
        print("Template cog is ready!")
    
    
    @commands.Cog.listener("on_console_input")
    async def console_listener(self, input_line):
        print(f"Template cog: Console input received: {input_line}")
