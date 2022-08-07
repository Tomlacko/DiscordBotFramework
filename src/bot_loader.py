import discord
from discord.ext import commands

import asyncio

import os
import sys
import logging

from datetime import datetime


BOT_DIR = os.path.dirname(__file__)
EXTENSIONS_DIR = os.path.join(BOT_DIR, "extensions")
STATIC_RESOURCES_DIR = os.path.join(BOT_DIR, "static_resources")

#make it so that scripts can be loaded directly from this directory
sys.path.append(BOT_DIR)
#make it so that extensions can be loaded directly by their name instead of going through the folder
sys.path.append(EXTENSIONS_DIR)


from custom_errors import ExtensionNotRegistered

from smart_bot import SmartBot
from utils.common import get_exception_traceback
from utils.formatting import plural_suffix
from utils.printing_override import new_empty_line_if_not_already, enable_printing_override, disable_printing_override





class BotLoader:
    """Helps prepare and load a custom discord.py 2.0+ bot with extensions.


    The loaded bot has the following changes compared to vanilla bots:

    Custom attributes:
    - bot.is_loaded - False if the bot isn't logged in yet, True after an on_ready event has been received
    - bot.is_quitting - True if the bot is currently shutting down
    - bot.was_interrupted - True if the shutdown was caused by keyboard interruption
    - bot.globaldata - holds custom global variables accessible from everywhere
    - bot.main_server_id - holds the id of the main guild that the bot is intended to operate in
    - bot.paths - holds paths to important bot directories or files
        .bot_dir, .data_dir, .extensions_dir, .resources_dir
    - bot.utils - extensions can implement bot utilities that get appened here
        - bot.utils.pathhelper - functions to more easily access paths leading from bot.paths
        - bot.utils.resolve - functions to help with getting/fetching discord IDs into objects
    - bot.extconfig - dictionary containing custom settings for each extension
    - bot.logger - discord library logger from the logging module
    - bot.log_handlers - dictionary of log handlers for the logging module

    Custom events:
    - on_full_ready() - fired only the first time the bot gets fully ready. in cogs, use a special decorator instead though
    - on_console_input(str_line) - fired when a line is entered into the console
    - on_cog_ready(cog_instance) - fired when a cog gets completely loaded

    Other:
    - attemts to run nonexistent commands won't spam the console with errors
    - if an exception is raised inside an event handler,
      which is then handled with an exception handler,
      adding ".handled = true" to the exception will prevent it from also spamming the console
    """

    def __init__(self, *args,
        status_type: discord.ActivityType,
        status_message: str,
        owner_id: int = None,
        data_dir: str,
        use_builtin_help_command: bool = True,
        allowed_mentions = discord.AllowedMentions(
            users=True,
            replied_user=True,
            roles=False,
            everyone=False
        ),
    **kwargs):
        enable_printing_override()

        new_empty_line_if_not_already()
        print("--------------------------")
        print("--- Setting up the bot ---")
        new_empty_line_if_not_already()

        self.exts_registered = []
        self.exts_to_load = []
        self.exts_loaded = []

        #ensure path is absolute and exists
        #converting a relative path to absolute can cause unwanted behavior when the cwd is not the one the script is in
        if not os.path.isabs(data_dir):
            raise ValueError("Provided 'data_dir' path is relative, it needs to be absolute to prevent unwanted behavior.")
        if not os.path.isdir(data_dir):
            raise ValueError("Provided 'data_dir' path doesn't lead to a valid directory!")

        self.data_dir = data_dir
        self.bot_dir = BOT_DIR
        self.extensions_dir = EXTENSIONS_DIR
        self.resources_dir = STATIC_RESOURCES_DIR
        
        bot_args = {
            "activity": discord.Activity(
                type=status_type,
                name=status_message
            ),
            "allowed_mentions": allowed_mentions,
            "bot_dir": self.bot_dir,
            "data_dir": self.data_dir,
            "extensions_dir": self.extensions_dir,
            "resources_dir": self.resources_dir
        }

        if owner_id:
            bot_args["owner_id"] = owner_id
        if not use_builtin_help_command:
            bot_args["help_command"] = None
        
        kwargs.update(bot_args)
        
        #INSTANTIATE THE BOT
        self.bot = SmartBot(*args, **kwargs)
    
        


    def in_bot_dir(self, relative_path):
        return os.path.join(self.bot_dir, relative_path)
    def in_data_dir(self, relative_path):
        return os.path.join(self.data_dir, relative_path)
    def in_extensions_dir(self, relative_path):
        return os.path.join(self.extensions_dir, relative_path)
    def in_resources_dir(self, relative_path):
        return os.path.join(self.resources_dir, relative_path)


    def _prepare_and_register_log_handler(self, name, log_handler, log_level: int, log_formatter = None):
        if not log_formatter:
            log_formatter = SmartBot.get_default_log_formatter(log_handler)
            
        log_handler.setFormatter(log_formatter)
        log_handler.setLevel(log_level)

        return self.bot.add_log_handler(name, log_handler)


    def add_console_log_handler(self, log_level: int, custom_formatter = None):
        if self.bot.get_log_handler(""):
            return None
        
        print(f"Added '{logging.getLevelName(log_level)}' level logging output to the console.")
        
        return self._prepare_and_register_log_handler(
            "",
            logging.StreamHandler(),
            log_level,
            custom_formatter
        )


    def add_file_log_handler(self, log_level: int, output_file_path: str, overwrite: bool, custom_formatter = None):
        if not os.path.isabs(output_file_path):
            raise ValueError("Provided 'output_file_path' path is relative, it needs to be absolute to prevent unwanted behavior.")
        
        if self.bot.get_log_handler(output_file_path):
            return None
        
        print(f"Added '{logging.getLevelName(log_level)}' level logging output to file: {output_file_path}")

        if not overwrite:
            #ensure that two logging sessions are always separated
            with open(output_file_path, "a", encoding="utf-8") as file:
                file.write(f"\n\n------------------------------------------------------\n--- New session --- {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S (UTC%z)')} ---\n------------------------------------------------------\n\n")
        
        return self._prepare_and_register_log_handler(
            output_file_path,
            logging.FileHandler(filename=output_file_path, encoding="utf-8", mode=("w" if overwrite else "a")),
            log_level,
            custom_formatter
        )



    def register_extensions(self, extensions: dict) -> int:
        new_empty_line_if_not_already()
        print("Registering extensions...")
        
        reg_count = 0
        
        for ext, config in extensions.items():
            if self.bot.register_extension(ext, config):
                self.exts_registered.append(ext)
                reg_count += 1

        if reg_count < len(self.exts_registered):
            print(f"Done, registered {reg_count} more extension{plural_suffix(reg_count)} ({len(self.exts_registered)} in total).")
        else:
            print(f"Done, registered {reg_count} extension{plural_suffix(reg_count)}.")
        new_empty_line_if_not_already()

        return reg_count
    

    def add_extensions_to_startup(self, extensions: list) -> int:
        new_empty_line_if_not_already()
        print("Adding extensions to startup...")
        
        added_count = 0

        for ext in extensions:
            if ext not in self.exts_registered:
                raise ExtensionNotRegistered(ext)
            
            if ext in self.exts_to_load:
                print(f"Warning: extension '{ext}' is already added! Don't add the same extension twice!")
            else:
                self.exts_to_load.append(ext)
                added_count += 1

        if added_count < len(self.exts_to_load):
            print(f"Done, {added_count} more extension{plural_suffix(added_count)} added to be loaded on startup ({len(self.exts_to_load)} in total, out of {len(self.exts_registered)} registered).")
        else:
            print(f"Done, {added_count} extension{plural_suffix(added_count)} added to be loaded on startup (out of {len(self.exts_registered)} registered).")
        new_empty_line_if_not_already()

        return added_count



    async def try_load_extensions(self, extensions: list):
        ext_count = len(extensions)

        new_empty_line_if_not_already()
        print("Loading extensions...")

        for i, ext in enumerate(extensions, 1):
            if ext in self.exts_loaded:
                print(f"~ [{i}/{ext_count}] '{ext}' already loaded! Skipping...")
                continue

            try:
                await self.bot.load_extension(ext)
            except Exception as e:
                #EXTENSION FAIL
                new_empty_line_if_not_already()
                print(f"Exception: {e}")
                if hasattr(e, "original"):
                    print(get_exception_traceback(e.original))
                else:
                    print(get_exception_traceback(e))
                
                new_empty_line_if_not_already()
                print(f"x [{i}/{ext_count}] Extension '{ext}' failed to load!")
                new_empty_line_if_not_already()
                print("Do you wish to continue starting the bot without this extension?")
                if input("(y/N): ").lower() != "y":
                    #STOP BOT
                    return False
                #CONTINUE BOT
                print("Continuing...")
                new_empty_line_if_not_already()

            else:
                #EXTENSION SUCCESS
                self.exts_loaded.append(ext)
                print(f"+ [{i}/{ext_count}] '{ext}' loaded successfully.")
        
        new_empty_line_if_not_already()
        print(f"Successfully loaded {len(self.exts_loaded)}/{ext_count} extensions (out of {len(self.exts_registered)} registered).")
        new_empty_line_if_not_already()

        return True



    def try_start_bot(self, token: str, *, reconnect: bool = True) -> bool:
        enable_printing_override()


        async def bot_setup_handler(bot: SmartBot) -> bool:
            #load extensions
            if (len(self.exts_to_load) > 0) and (not await self.try_load_extensions(self.exts_to_load)):
                return False

            new_empty_line_if_not_already()
            print("--------------------------")
            print("Bot is connecting... (waiting for an 'on_ready' event)")
            new_empty_line_if_not_already()

            return True
        
        
        async def bot_before_full_ready(bot: SmartBot) -> None:
            if bot.should_sync_commands_on_start():
                new_empty_line_if_not_already()
                print("Syncing AppCommands... (this might take a while)")


        @self.bot.event
        async def on_full_ready():
            if self.bot.should_sync_commands_on_start():
                print(f"Combined total of {len(self.bot.tree.app_commands_cache.values())} AppCommands have been uploaded to Discord.")
            new_empty_line_if_not_already()
            print("--- Done, bot fully loaded! (Type 'q', 'quit' or 'exit' to stop it.) ---")
            new_empty_line_if_not_already()
        

        async def bot_shutdown_hook(bot: SmartBot) -> None:
            #move onto another line and write this after interuption signal is received in the console
            
            if bot.was_interrupted:
                await asyncio.sleep(0.2) #make sure that ^C shows up first in the console
                print(" [Interrupt signal received]")
                print("Gracefully shutting down the bot...")
            elif bot.is_loaded:
                print("Stopping the bot...")
            else:
                print("Bot startup cancelled.")
            
            if bot.should_sync_commands_on_quit():
                print("(Un)syncing commands... (this might take a while)")
            new_empty_line_if_not_already()
        

        async def console_handler(bot: SmartBot, input_line: str) -> str:
            if input_line.lower() in ("q", "quit", "exit"):
                await self.bot.close()
                return None
            return input_line
        

        new_empty_line_if_not_already()

        #blocking run call
        success = self.bot.run(
            token,
            before_start_coro=bot_setup_handler,
            before_quit_coro=bot_shutdown_hook,
            before_full_ready_coro=bot_before_full_ready,
            console_input_coro=console_handler,
            reconnect=reconnect
        )

        new_empty_line_if_not_already()
        print("--------------------------")
        print("Bot has been stopped.")
        new_empty_line_if_not_already()
        
        disable_printing_override()
        return success


def path_from_current_dir(current_file: str, relative_path: str) -> str:
    return os.path.join(os.path.dirname(current_file), relative_path)