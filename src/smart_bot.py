import discord
from discord.ext import commands
from discord.ext.commands import errors

from discord.utils import MISSING
from discord.client import stream_supports_colour, _ColourFormatter


import os
import sys
import re
import asyncio
import logging
import inspect
from typing import Optional, Union



from utils.common import DummyObject, get_exception_traceback, prevent_task_garbage_collection
from custom_errors import ExtensionNotRegistered
import bot_utils





# class ConsoleContext:
#     def __init__(self, console: BotConsoleManager, input_line: str = "", intended_for: str = None):
#         self.console = console
#         self.intended_for = intended_for
#         self.handled = False
#         self.input_line = input_line


# class BotConsoleManager:
#     def __init__(self, bot: SmartBot):
#         self.bot = bot
#         self.hooked_up = False
#         self.subscriber = None
    
#     def subscribe(self, key: str) -> bool:
#         if self.subscriber:
#             return False
#         self.subscriber = key
    
#     def process_input(self, input_line):
#         pass







class SmartBot(commands.Bot):
    """
    Overrides the existing disnake bot class to introduce some minor changes.
    """

    def __init__(self, *args, main_server_id, bot_dir, data_dir, extensions_dir, resources_dir, **kwargs):
        super().__init__(*args, **kwargs)
        
        #custom attributes
        self.is_loaded = False
        self.is_quitting = False
        self.was_interrupted = False
        self.globaldata = DummyObject()
        self.paths = DummyObject()
        self.utils = DummyObject()
        self.extconfig = {}

        self._custom_quit_handler = None
        
        self._log_handlers_enabled = False
        self.log_handlers = {}
        self.discord_logger = logging.getLogger(discord.__name__)
        self.discord_logger.setLevel(logging.DEBUG)

        self.paths.bot_dir = bot_dir
        self.paths.data_dir = data_dir
        self.paths.extensions_dir = extensions_dir
        self.paths.resources_dir = resources_dir
        self.globaldata.main_server_id = main_server_id

        self.utils.pathhelper = bot_utils.PathHelper(self)
        self.utils.resolve = bot_utils.ResolveHelper(self)

        

        


    #custom
    def register_extension(self, name: str, config = None) -> bool:
        is_new = True
        if name in self.extconfig:
            print(f"Warning: extension '{name}' is already registered, existing config has been replaced.")
            is_new = False
        
        self.extconfig[name] = config

        return is_new


    #override
    async def load_extension(self, name: str, *, package: Optional[str] = None) -> None:
        if name not in self.extconfig:
            raise ExtensionNotRegistered(name)
        await super().load_extension(name, package=package)


    #custom
    def get_log_handler(self, name: str):
        """Returns existing log handler by name if it exists, otherwise None."""
        return self.log_handlers.get(name, None)

    #custom
    def add_log_handler(self, name: str, log_handler):
        """Adds a log handler to the internal dictionary.
        If the bot is running, adds it from the logger as well."""
        if name in self.log_handlers:
            return None
        self.log_handlers[name] = log_handler
        if self._log_handlers_enabled:
            self.discord_logger.addHandler(log_handler)
        return log_handler

    #custom
    def remove_log_handler(self, name: str):
        """Removes a log handler from the internal dictionary.
        If the bot is running, removes it from the logger as well."""
        log_handler = self.log_handlers.pop(name, None)
        if not log_handler:
            return None
        self.discord_logger.removeHandler(log_handler)
        return log_handler
    
    #custom
    def activate_log_handlers(self):
        for log_handler in self.log_handlers.values():
            self.discord_logger.addHandler(log_handler)
        self._log_handlers_enabled = True

    #custom
    def deactivate_log_handlers(self):
        for log_handler in self.log_handlers.values():
            self.discord_logger.removeHandler(log_handler)
        self._log_handlers_enabled = False
    
    #custom
    @staticmethod
    def get_default_log_formatter(log_handler):
        if isinstance(log_handler, logging.StreamHandler) and stream_supports_colour(log_handler.stream):
            return _ColourFormatter()
        
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        return logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

    
    #override from client
    def run(
        self,
        token: str,
        *,
        before_start_coro = None,
        before_quit_coro = None,
        console_input_coro = None,
        reconnect: bool = True
    ) -> bool:
        """Improved run function that lets you pass in your own
        functions to handle certain stages of the bot's runtime.
        This function also activates and deactivates log handlers that have been
        registered on the bot.
        Returns True if the bot succesfully ran, otherwise False.

        Optional arguments:

        before_start_coro must be an async function (coroutine passed without execution).
        This is called in async context before the bot is started, allowing you to
        load extensions and do other stuff before the bot starts.
        One argument is passed to this coroutine, which is the bot itself.
        Returning False from this function will halt the startup process.

        before_quit_coro same as above, except it's ran when the bot starts shutting down.
        Check bot.was_interrupted to see if the shutdown was caused by a keyboard interrupt.
        
        console_input_coro must be same as above. This coroutine is called whenever a line
        is entered into the console (stdin) after the bot is loaded and ready.
        Its purpose is to act like a preprocessor/filter.
        Two arguments are passed to this coroutine, first is the bot and
        the second is the string that was inputted into the console by the user.
        The returned value will be dispatched throughout the bot via a 'console_input' event.
        If None is returned, this will be prevented from happening.
        
        

        Relevant parts of the original description:
        -----------
        A blocking call that abstracts away the event loop
        initialisation from you.

        This function also sets up the logging library to make it easier
        for beginners to know what is going on with the library.

        .. warning::

            This function must be the last function to call due to the fact that it
            is blocking. That means that registration of events or anything being
            called after this function call will not execute until it returns.

        Parameters
        -----------
        token: :class:`str`
            The authentication token. Do not prefix this token with
            anything as the library will do it for you.
        reconnect: :class:`bool`
            If we should attempt reconnecting, either due to internet
            failure or a specific failure on Discord's part. Certain
            disconnects that lead to bad state will not be handled (such as
            invalid sharding payloads or bad tokens).
        """

        if before_start_coro and not inspect.iscoroutinefunction(before_start_coro):
            raise TypeError("'before_start_coro' must be a coroutine.")
        if before_quit_coro and not inspect.iscoroutinefunction(before_quit_coro):
            raise TypeError("'before_quit_coro' must be a coroutine.")
        if console_input_coro and not inspect.iscoroutinefunction(console_input_coro):
            raise TypeError("'console_input_coro' must be a coroutine.")
        
        self._custom_quit_handler = before_quit_coro


        self.activate_log_handlers()


        async def runner():
            async with self:
                setup_successfull = True
                if before_start_coro:
                    if await before_start_coro(self) is not True:
                        setup_successfull = False
                if setup_successfull:
                    await add_console_input_handler()
                    await self.start(token, reconnect=reconnect)
        

        #hook into console input, pass it through a custom handler and then send each line via an event
        async def add_console_input_handler() -> None:
            console_lock = asyncio.Lock()
            
            def relay_console_input():
                input_line = sys.stdin.readline().rstrip("\n")
                if self.is_loaded and not self.is_quitting:
                    prevent_task_garbage_collection(asyncio.create_task(async_console_relay(input_line)))
            
            async def async_console_relay(input_line: str) -> None:
                async with console_lock:
                    if not self.is_quitting:
                        result_line = input_line
                        try:
                            if console_input_coro:
                                result_line = await console_input_coro(self, input_line)
                        except Exception as e:
                            print(f"Encountered exception in custom console input handler: {e}")
                            print(get_exception_traceback(e))
                        else:
                            if result_line:
                                #dispatch a custom event for console input
                                self.dispatch("console_input", result_line)
            
            asyncio.get_running_loop().add_reader(sys.stdin, relay_console_input)


        #custom event listener to setup the bot on ready
        @self.listen("on_ready")
        async def when_ready():
            if self.is_loaded:
                return
            self.is_loaded = True

            #dispatch a custom first_ready event that is only triggered once upon the first load
            self.dispatch("first_ready")


        try:
            #blocking call, actually runs the bot
            asyncio.run(runner())
        except KeyboardInterrupt:
            # nothing to do here
            # `asyncio.run` handles the loop cleanup
            # and `self.start` closes all sockets and the HTTPClient instance.
            
            # In this case, __aexit__ + self.close() is what actually closes the bot
            pass
        finally:
            self.deactivate_log_handlers()

            return self.is_loaded


    #custom
    async def quit_handler(self):
        if self._custom_quit_handler:
            try:
                await self._custom_quit_handler(self)
            except Exception as e:
                print(f"Ignoring exception in custom quit handler: {e}")
                print(get_exception_traceback(e))


    #override from client
    async def __aexit__(self, *args) -> None:
        if not self.is_closed():
            self.was_interrupted = True
        await super().__aexit__(*args)

    #override from bot
    async def close(self):
        self.is_quitting = True
        await self.quit_handler()
        await super().close()
