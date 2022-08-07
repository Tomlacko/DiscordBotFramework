import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import MISSING

import asyncio
from itertools import chain

from smart_bot import SmartBot
from utils.common import prevent_task_garbage_collection










class ExtensionDependencyNotLoaded(commands.errors.ExtensionError):
    """
    Thrown when attempting to load an extension that depends on another extension which has not yet been loaded.
    """
    def __init__(self, name: str, dependency: str) -> None:
        msg = f"Cannot load extension {name!r} - extension {dependency!r} is required to be loaded beforehand!"
        super().__init__(msg, name=name)


class CommandPropertiesMismatch(commands.errors.ExtensionError):
    """
    Thrown when attempting to load an extension that contains commands with mismatching properties.
    """
    def __init__(self, name: str, command: str) -> None:
        msg = f"Cannot load extension {name!r} - command {command!r} contains mismatching values! (Check your decorators.)"
        super().__init__(msg, name=name)




class SmartCog(commands.Cog):
    """
    Special custom class attributes:
    .dependencies - list of extension import path strings required for this extension to run

    Special custom instance attributes:
    .bot - holds the bot instance
    .ready - boolean indicating whether the cog is fully loaded and the bot is ready
    .config - getter acting like a shortcut to the config specific to this extension saved in the bot
    
    Custom functions:
    .get_all_commands() -> list
    .get_hybrid_commands() -> list
    .get_app_commands_including_hybrid() -> list
    .get_app_commands_including_from_hybrid() -> list
    .get_only_classic_commands() -> list

    Hidden attributes/functions:
    ._loaded_on_startup
    ._ready_init
    """


    DEPENDENCIES = [] #all extensions (cogs) needed for this cog to function, written as strings in import path notation


    def __init__(self, bot: SmartBot):
        super().__init__()
        
        #check dependencies
        for req_path in self.DEPENDENCIES:
            if req_path not in bot.extensions:
                raise ExtensionDependencyNotLoaded(self.__module__, req_path)
        
        self.bot = bot
        self.ready = False #if the bot is ready and the _ready_init function ran
        self._loaded_on_startup = not self.bot.is_loaded
        
        
        #apply custom decorator effects to app/hybrid/classic commands
        for cmd in self.get_all_commands():
            #apply decorators even if it's not a pure app command
            if cmd.extras.get("__smartcog_command_for_all_guilds__", False):
                app_commands.guilds(*self.bot.guilds)(cmd)
            elif cmd.extras.get("__smartcog_command_for_main_guild__", False):
                app_commands.guilds(self.bot.main_server_id)(cmd)
            if cmd.extras.get("__smartcog_command_guild_only__", False):
                app_commands.guild_only(cmd)
            
            #decorate app commands inside hybrid commands
            if getattr(cmd, "__commands_is_hybrid__", False):
                appcmd = getattr(cmd, "app_command", None)
                if appcmd:
                    guild_ids = getattr(cmd, "__discord_app_commands_default_guilds__", None)
                    guild_ids_appcmd = getattr(appcmd, "_guild_ids", None)
                    if guild_ids is not None and guild_ids_appcmd is not None:
                        raise CommandPropertiesMismatch(self.__module__, cmd.name)
                    guild_ids = guild_ids or guild_ids_appcmd
                    if guild_ids:
                        #synchronize guild ids across both command types
                        cmd.__discord_app_commands_default_guilds__ = guild_ids
                        app_commands.guilds(*guild_ids)(appcmd)
                    
                    guild_only = getattr(cmd, "__discord_app_commands_guild_only__", None)
                    if guild_only is None:
                        guild_only = getattr(appcmd, "guild_only", False)
                    if guild_only:
                        cmd.__discord_app_commands_guild_only__ = guild_only
                        app_commands.guild_only(appcmd)
        
        #apply efects of previous decorators to classical/hybrid commands
        for cmd in self.get_commands():
            guild_ids = getattr(cmd, "__discord_app_commands_default_guilds__", None)
            guild_only = getattr(cmd, "__discord_app_commands_guild_only__", False)
            if guild_ids or guild_only:
                for walkedcmd in chain([cmd], cmd.walk_commands() if getattr(cmd, "walk_commands", None) else []):
                    allowed_contexts(guild_ids, guild_only)(walkedcmd)
        
        #for attribute in self.__class__.__dict__.values():
    
    
    
    @property
    def config(self):
        """Getter acting like a shortcut for the config specific to this extension saved in the bot."""
        return self.bot.extconfig[self.__module__]



    #automatically called on initialization. if overridden, must call `await super().cog_load()` at the end
    async def cog_load(self):
        #if the bot is already loaded, _ready_init needs to be called manually
        if self.bot.is_loaded:
            prevent_task_garbage_collection(asyncio.create_task(self._ready_init()))
        await super().cog_load()
    
    
    @commands.Cog.listener("on_full_ready")
    async def _ready_init(self):        
        """Triggered either automatically by the event itself, or, if the bot is already loaded,
        triggered manually by cog_load.
        Syncs app commands and runs all functions decorated to run on ready in this cog."""
        #sync guilds with appcommands from this cog
        #cannot be done on cog_load because the commands aren't registered yet
        if not self._loaded_on_startup and self.bot.autosync_appcommands:
            await self.bot.tree.sync_given(
                *self.get_app_commands_including_from_hybrid(),
                avoid_deletions=self.bot.avoid_appcommand_deletions,
                ignore_errors=True
            )
        
        #run @run_when_ready decorated functions
        for method in self.__class__.__dict__.values():
            if getattr(method, "__smartcog_func_run_when_ready__", False):
                await method(self)

        self.ready = True
        self.bot.dispatch("smart_cog_ready", self)
    
    
    
    #automatically called when unloading. if overridden, must call `await super().cog_unload()` at the end
    async def cog_unload(self):
        if self.bot.is_loaded and not self.bot.is_quitting and self.bot.remove_appcommands_on_unload and not self.bot.avoid_appcommand_deletions:
            await self.bot.tree.unsync_given(*self.get_app_commands_including_from_hybrid(), ignore_errors=True)
        await super().cog_unload()
    
    
    
    def get_all_commands(self) -> list:
        """Returns all classic, hybrid and app commands in a single list."""
        return self.get_commands() + self.get_app_commands()
    
    def get_hybrid_commands(self) -> list:
        """Returns a list of all hybrid commands defined in this cog."""
        return [cmd for cmd in self.get_commands() if getattr(cmd, "__commands_is_hybrid__", False)]
    
    def get_app_commands_including_hybrid(self) -> list:
        """Returns a list of all app commands and hybrid commands defined in this cog. Hybrid commands are kept as they are."""
        return self.get_hybrid_commands() + self.get_app_commands()
    
    def get_app_commands_including_from_hybrid(self) -> list:
        """Returns a list of app commands defined in this cog. From hybrid commands, the inner app command is returned."""
        return [cmd.app_command for cmd in self.get_hybrid_commands() if cmd.app_command] + self.get_app_commands()
    
    def get_only_classic_commands(self) -> list:
        """Returns a list of all classic commands defined in this cog. Hybrid commands are ignored."""
        return [cmd for cmd in self.get_commands() if not getattr(cmd, "__commands_is_hybrid__", False)]
    
    

##################################################



#DECORATOR for classic/hybrid commands (better to use the other ones below though)
def allowed_contexts(allowed_guilds: list, guild_only: bool = False):
    """This creates a command check for classic/hybrid commands that only lets
    the command run if it has been executed in an allowed guild/DM.
    This mimics the behavior of app_commands.guilds() decorator.
    This MUST be used ABOVE the command/group decorator!
    allowed_guilds: empty = allowed in every guild (global command)
    """
    guild_ids = [] if not allowed_guilds else [g if isinstance(g, int) else g.id for g in allowed_guilds]
    
    def allowed_guilds_check(ctx: commands.Context) -> bool:
        if not ctx.guild:
            return not guild_ids and not guild_only
        return not guild_ids or ctx.guild.id in guild_ids
    
    def decorator(cmd):
        cmd.add_check(allowed_guilds_check)
        return cmd
    
    return decorator


#DECORATOR for any function
def app_commands_Group(
    *,
    name: str = MISSING,
    description: str = MISSING,
    nsfw: bool = False,
    extras: dict = MISSING,
):
    """This is missing from the library even though it's very useful.
    Creates an application command group from any function.
    Behaves the same way as the @app_commands.command() decorator, just for groups.
    The function decorated by this will never be run, however!
    """
    def decorator(func) -> app_commands.Group:
        if description is MISSING:
            if func.__doc__ is None:
                desc = '…'
            else:
                desc = app_commands.commands._shorten(func.__doc__)
        else:
            desc = description
        
        return app_commands.Group(
            name=name if name is not MISSING else func.__name__,
            description=desc,
            parent=None,
            nsfw=nsfw,
            extras=extras,
        )
    
    return decorator


#DECORATOR for any command
def for_main_guild(cmd):
    """Decorator for marking any type of command to be assigned to the bot's main guild (instead of being global).
    This MUST be used ABOVE the command/group decorator!
    Only usable for top-level commands/groups!"""
    cmd.extras["__smartcog_command_for_main_guild__"] = True
    return cmd

#DECORATOR for any command
def for_all_guilds(cmd):
    """Decorator for marking an app command (or hybrid command) to be assigned to all guilds the bot is in (instead of being global).
    This MUST be used ABOVE the command/group decorator!
    Only usable for top-level commands/groups!"""
    cmd.extras["__smartcog_command_for_all_guilds__"] = True
    return cmd

#DECORATOR for any command
def guilds_only(cmd):
    cmd.extras["__smartcog_command_guild_only__"] = True
    return cmd


#DECORATOR for any command
def run_when_ready(func):
    """Decorator for marking a cog coroutine to be executed when the cog is fully ready."""
    func.__smartcog_func_run_when_ready__ = True
    return func

#DECORATOR for any function
def only_if_ready(func):
    """Decorator for making sure a coroutine only runs while the cog is already ready."""
    async def decorated(_self, *args, **kwargs):
        if _self.ready:
            return await func(_self, *args, **kwargs)
    return decorated

#DECORATOR for any function
def requires_extension(ext_import_path):
    """Decorator for letting a coroutine run only if a specified extension is currently loaded."""
    def decorator(func):
        async def decorated(_self, *args, **kwargs):
            if ext_import_path in _self.bot.extensions:
                return await func(_self, *args, **kwargs)
        return decorated
    return decorator
