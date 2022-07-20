import discord
from discord.ext import commands

import asyncio

from smart_bot import SmartBot
from custom_errors import ExtensionDependencyNotLoaded





class SmartCog(commands.Cog):
    """
    Special custom class attributes:
    .dependencies - list of extension import path strings required for this extension to run

    Special custom instance attributes:
    .bot - holds the bot instance
    .ready - boolean indicating whether the cog is fully loaded and the bot is ready
    .ext_name - import path of this extension
    .config - getter acting like a shortcut to the config specific to this extension saved in the bot

    Hidden attributes/functions:
    ._to_run_when_ready
    ._get_config
    ._ready_init
    """

    dependencies = [] #all cogs needed for this cog to function, written as strings in import path notation


    def __init__(self, bot: SmartBot, ext_name: str):
        self.ext_name = ext_name
        self.bot = bot
        self.ready = False #if the bot is ready and the _ready_init function ran
        
        #check dependencies
        for req_path in self.dependencies:
            if req_path not in self.bot.extensions:
                raise ExtensionDependencyNotLoaded(ext_name, req_path)

        self._to_run_when_ready = [method for method in self.__class__.__dict__.values() if getattr(method, "_run_when_ready", False)]
    

    config = property(lambda s: s.bot.extconfig[s.ext_name], None, None)


    #automatically called on initialization. if overridden, must call super().cog_load() at the end
    async def cog_load(self):
        if self.bot.is_loaded:
            asyncio.create_task(self._ready_init())


    @commands.Cog.listener("on_first_ready")
    async def _ready_init(self):
        for method in self._to_run_when_ready:
            await method(self)

        self.ready = True
        
        self.bot.dispatch("cog_ready", self)
    



#decorator for marking a cog coroutine to be executed when the cog is ready
def run_when_ready(func):
    func._run_when_ready = True
    return func


#decorator for making sure a coroutine only runs when the cog is ready
def only_while_ready(func):
    async def decorated(_self, *args, **kwargs):
        if _self.ready:
            return await func(_self, *args, **kwargs)
    return decorated


#decorator for letting a coroutine run only if a specified extension is currently loaded
def requires_extension(func, ext_import_path):
    async def decorated(_self, *args, **kwargs):
        if ext_import_path in _self.bot.extensions:
            return await func(_self, *args, **kwargs)
    return decorated


# #decorator
# def receive_console_input(func, identifier):
#     """Decorator for subscribing to console inputs."""
    
#     @commands.Cog.listener("on_console_input")
#     async def decorated(_self, console_context, *args, **kwargs):
        
#         return await func(_self, console_context, *args, **kwargs)
    
#     return decorated