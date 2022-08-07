import discord
from discord.app_commands import AppCommand, Command, Group, ContextMenu
from discord.ext.commands.hybrid import HybridAppCommand
from discord.app_commands.errors import MissingApplicationID
from discord.utils import MISSING

from typing import Optional, Union, List, Dict, Set
from collections.abc import Iterable

from itertools import chain


"""
Server-side limitations:

Global commands are available in DMs, guild commands are not

Limits per guild and for globals (individually):
total: 100 slash commands, 5 user context commands, 5 message context commands
ratelimit: max 200 new per day

String limits:
command/option name: 32
command/option description: 100
options (parameters): 25
max choice count: 25
choice name / value: 100
user input: 6000

max 100 permission overwrites (enable or disable commands for up to 100 users, roles, and channels within a guild)

"""


ClientsideAppCommand = Union[Command, HybridAppCommand, Group, ContextMenu]
AnyCommand = Union[ClientsideAppCommand, AppCommand]


#local utility function
def unpack_guild_object(guild) -> tuple:
    """Unpacks a guild object, snowflake or a guild ID into (guild_snowflake_obj, guild_id)."""
    if isinstance(guild, (discord.Guild, discord.Object)):
        return (guild, guild.id)
    if isinstance(guild, int):
        return (discord.Object(id=guild), guild)
    return (None, None)



class SmartCommandTree(discord.app_commands.CommandTree):
    def __init__(self, *args, fallback_to_global: bool = False, **kwargs):
        super().__init__(*args, fallback_to_global=fallback_to_global, **kwargs)
        
        #the cache will only be populated after syncing, unless populated explicitly
        #the only time this can de-sync is when a method on the AppCommand object itself is called, bypassing the tree
        self.app_commands_cache: Dict[int, AppCommand] = {} #command id : command
        #[type][guild id or none][command name] = command
        self.app_commands_cache_structured: Dict[discord.AppCommandType, Dict[Union[int, None], Dict[str, AppCommand]]] = {
            cmd_type: {} for cmd_type in discord.AppCommandType
        }

    
    
    #custom
    @staticmethod
    def get_command_type(cmd: AnyCommand) -> discord.AppCommandType:
        """Returns the type of the command as AppCommandType. Can be chat_input, user or message."""
        return getattr(cmd, "type", discord.AppCommandType.chat_input)
    
    
    #custom
    @staticmethod
    def get_command_locations(cmd: AnyCommand) -> List[Optional[int]]:
        """Returns a list of guild ids (or [None] for global) for which a given command is defined."""
        #server-side AppCommands
        guild_id = getattr(cmd, "guild_id", MISSING)
        if guild_id is not MISSING:
            return [guild_id]
        
        #clientside app commands
        guild_ids = getattr(cmd, "_guild_ids", None)
        if not guild_ids: #also checks empty list
            return [None]
        return guild_ids
    
    
    #custom
    @staticmethod
    def equal_commands(cmd1: AnyCommand, cmd2: AnyCommand) -> bool:
        """Checks if 2 given commands are equal. This can compare clientside and serverside commands at the same time."""
        if cmd1.name != cmd2.name:
            return False
        
        if self.get_command_type(cmd1) != self.get_command_type(cmd2):
            return False
        
        #check guild overlap
        loc1 = self.get_command_locations(cmd1)
        loc2 = self.get_command_locations(cmd2)
        for loc in loc1:
            if loc in loc2:
                return True
        
        return False
    
    
    #custom
    @staticmethod
    def get_equal_command_from(command: AnyCommand, iterable: Iterable[AnyCommand]) -> Optional[AnyCommand]:
        """Returns a matching command from the given iterable, or None if not found."""
        for cmd in iterable:
            if self.equal_commands(command, cmd):
                return cmd
        return None
    
    #custom
    @staticmethod
    def get_equal_commands_from(command: AnyCommand, iterable: Iterable[AnyCommand]) -> List[AnyCommand]:
        """Returns a list of matching commands from the given iterable."""
        results = []
        for cmd in iterable:
            if self.equal_commands(command, cmd):
                results.append(cmd)
        return results
        

    
    #custom
    def _add_app_commands_to_cache(self, *commands: AppCommand) -> None:
        """Adds AppCommands into the custom cache. If one already exists, it gets overwritten."""
        for cmd in commands:
            self.app_commands_cache[cmd.id] = cmd
            self.app_commands_cache_structured[cmd.type].setdefault(cmd.guild_id, {})[cmd.name] = cmd
    
    #custom
    def _clear_cache(self, guild_id: Optional[int] = MISSING) -> None:
        """If guild_id is provided (or None for global), that particular target is cleared from the cache.
        If not provided, the whole cache is cleared."""
        
        #clear whole cache
        if guild_id is MISSING:
            self.app_commands_cache.clear()
            for guilds_with_commands_of_type in self.app_commands_cache_structured.values():
                guilds_with_commands_of_type.clear()
            return
        
        #clear individual guild or global
        self.app_commands_cache = {
            cmd_id: cmd for cmd_id, cmd in self.app_commands_cache.items() if cmd.guild_id != guild_id
        }
        for guilds_with_commands_of_type in self.app_commands_cache_structured.values():
            guilds_with_commands_of_type.pop(guild_id, None)
        
    
    #custom
    def _overwrite_app_commands_cache(self, commands: List[AppCommand], *, guild_id: Optional[int] = MISSING) -> None:
        """Removes every existing AppCommand in cache which is from a guild (or global)
        contained in any of the newly given commands, then adds the new commands into the cache."""
        
        if guild_id is not MISSING:
            guild_ids = [guild_id]
        else:
            guild_ids = set(cmd.guild_id for cmd in commands)
            self.app_commands_cache = {
                cmd_id: cmd for cmd_id, cmd in self.app_commands_cache.items() if cmd.guild_id not in guild_ids
            }
        
        for guilds_with_commands_of_type in self.app_commands_cache_structured.values():
            for _guild_id in guild_ids:
                guilds_with_commands_of_type[_guild_id] = {}
        
        self._add_app_commands_to_cache(*commands)

    
    #custom
    def _remove_app_command_from_cache(self, cmd: AppCommand) -> Optional[AppCommand]:
        """Pops an AppCommand from the cache and returns it if found."""
        self.app_commands_cache_structured[cmd.type].get(cmd.guild_id, {}).pop(cmd.name, None)
        return self.app_commands_cache.pop(cmd.id, None)
    
    
    #custom
    def get_cached_app_command(self,
        cmd_name: str,
        guild_id: Optional[int],
        cmd_type: discord.AppCommandType = discord.AppCommandType.chat_input
    ) -> Optional[AppCommand]:
        """Returns a cached AppCommand by name, type and guild (global if None)."""
        return self.app_commands_cache_structured[cmd_type].get(guild_id, {}).get(cmd_name, None)
    
    
    #custom
    def get_cached_app_commands(self, guild_id: Optional[int]) -> List[AppCommand]:
        """Returns all cached app commands for a given guild, or global if None."""
        results = []
        for guilds_with_commands_of_type in self.app_commands_cache_structured.values():
            results.extend(guilds_with_commands_of_type.get(guild_id, {}).values())
        return results
    
    #custom
    def get_all_cached_app_commands(self) -> List[AppCommand]:
        """Returns all cached app commands, both global and from every guild."""
        return list(self.app_commands_cache.values())
    
    
    #override
    async def fetch_command(self, command_id: int, /, *, guild = None) -> AppCommand:
        """Fetches a single AppCommand from Discord from the given guild (or global if None) and caches it in the process."""
        (guild, _) = unpack_guild_object(guild)
        cmd = await super().fetch_command(command_id, guild=guild)
        self._add_app_commands_to_cache(cmd)
        return cmd
    
    #override
    async def fetch_commands(self, *, guild = None) -> List[AppCommand]:
        """Fetches AppCommands from the given guild (global if None) and caches them in the process."""
        (guild, guild_id) = unpack_guild_object(guild)
        results = await super().fetch_commands(guild=guild)
        self._overwrite_app_commands_cache(results, guild_id=guild_id)
        return results
    
    #custom
    async def fetch_all_commands(self) -> List[AppCommand]:
        """Fetches all app commands from Discord from every guild (including global) and caches them in the process."""
        results = []
        for guild in chain([None], self.client.guilds):
            results += await self.fetch_commands(guild=guild)
        return results
    
    
    #custom
    async def fetch_to_cache(self, guild = None) -> None:
        """Fetches all app commands from discord from the given guild (global if none) and caches them."""
        try:
            await self.fetch_commands(guild=guild)
        except:
            pass
    
    
    #custom
    async def fetch_all_to_cache(self) -> None:
        """Fetches all app commands from Discord from every guild (including global) and caches them.
        This function ensures that the local cache mimics all commands stored on Discord."""
        for guild in chain([None], self.client.guilds):
            await self.fetch_to_cache(guild=guild)
    
    
    
    #custom
    def get_all_client_commands(self) -> Set[ClientsideAppCommand]:
        """Returns all clientside-defined commands from the command tree.
        This includes commands from all guilds, global commands and context menus."""
        results = set(self._global_commands.values())
        results.update(self._context_menus.values())
        for guild_commands in self._guild_commands.values():
            results.update(guild_commands.values())
        return results
    
    
    #custom
    def clear_all_client_commands(self) -> None:
        """Clears all clientside app commands from the tree (global and for all guilds).
        If you want to remove the app commands from Discord as well, call .sync_all afterwards."""
        self._global_commands.clear()
        self._context_menus.clear()
        #just in case there are any references left to individual guilds elsewhere
        for guild_commands in self._guild_commands.values():
            guild_commands.clear()
        self._guild_commands.clear()
    
    
    #custom
    def get_all_command_locations(self) -> Set[Optional[int]]:
        """Returns a set of guild ids (and None for global) that have some clientside app commands defined."""
        results = set()
        if len(self._global_commands) > 0:
            results.add(None)
        results.update(guild_id for guild_id, commands in self._guild_commands.items() if len(commands) > 0)
        results.update(guild_id for (_, guild_id, _) in self._context_menus.keys())
        return results
    
    
    #custom
    def resolve_to_local(self, command: AppCommand) -> Optional[ClientsideAppCommand]:
        """Resolves a server-side AppCommand to a clientside app command, if one exists."""
        return self.get_command(command.name, guild=None if not command.guild_id else discord.Object(id=command.guild_id), type=command.type)
    
    
    #custom
    async def get_command_by_id(self, cmd_id: int, *, guild = MISSING, fetch_priority: int = 1) -> Optional[AppCommand]:
        """Resolves a server-side AppCommand id to an AppCommand. Can use cache or fetch directly.
        guild: by default, the client will try to fetch from every possible guild.
        If a guild is specified, only that guild will be checked (global if None).
        fetch_priority: can be set to speficy when/if a fetch should be made.
        0 means never fetch, only use cache
        1 means fetch if the command is not found in the cache
        2 means always fetch fresh stuff first and only then care about the cache"""
        
        if not isinstance(fetch_priority, int) or fetch_priority < 0 or fetch_priority > 2:
            raise ValueError("Invalid fetch_priority.")
        
        for priority in [2, 1]:
            if fetch_priority == priority:
                if guild is not MISSING:
                    try:
                        await self.fetch_command(cmd_id, guild=guild)
                    except:
                        pass
                else:
                    for guild in self.client.guilds:
                        try:
                            await self.fetch_command(cmd_id, guild=guild)
                        except:
                            pass
            
            appcmd = self.app_commands_cache.get(cmd_id, None)
            if appcmd or fetch_priority != 1:
                return appcmd
        
        return None
    
    
    #custom
    async def resolve_command(self, command: ClientsideAppCommand, guild, *, fetch_priority: int = 1) -> Optional[AppCommand]:
        """Retrieves the server-side AppCommand from its code-defined version.
        Commands that cannot be resolved return None.
        fetch_priority: can be set to speficy when/if a fetch should be made.
        0 means never fetch, only use cache
        1 means fetch if the command is not found in the cache
        2 means always fetch fresh stuff first and only then care about the cache"""
        
        if not command:
            return None
        
        if not isinstance(fetch_priority, int) or fetch_priority < 0 or fetch_priority > 2:
            raise ValueError("Invalid fetch_priority.")
        
        (_, guild_id) = unpack_guild_object(guild)
        
        for priority in [2, 1]:
            if fetch_priority == priority:
                await self.fetch_to_cache(guild=guild)
            
            appcmd = self.get_cached_app_command(command.name, guild_id, self.get_command_type(command))
            if appcmd or fetch_priority != 1:
                return appcmd
        
        return None
    
    
    #custom
    async def resolve_commands(self, commands: List[ClientsideAppCommand], *, fetch_priority = 1) -> List[AppCommand]:
        """Retrieves the server-side AppCommands from their code-defined versions from global and all guilds.
        Commands that cannot be resolved get skipped.
        fetch_priority: can be set to speficy when/if a fetch should be made.
        0 means never fetch, only use cache
        1 means fetch if the command is not found in the cache
        2 means always fetch fresh stuff first and only then care about the cache"""
        
        if not commands:
            return []
        
        if not isinstance(fetch_priority, int) or fetch_priority < 0 or fetch_priority > 2:
            raise ValueError("Invalid fetch_priority.")
        
        #generate a list of what should be found
        commands_to_find = []
        for cmd in commands:
            for guild_id in self.get_command_locations(cmd):
                commands_to_find.append((cmd.name, guild_id, self.get_command_type(cmd)))
        
        results = []
        
        for priority in [2, 1]:
            if fetch_priority == priority:
                #get all command locations
                guild_ids = set()
                for (_, guild_id, _) in commands_to_find:
                    guild_ids.add(None)
                
                for guild_id in guild_ids:
                    await self.fetch_to_cache(guild=guild_id)
            
            #find a matching AppCommand from cache
            unfound_commands = []
            for cmd in commands_to_find:
                appcmd = self.get_cached_app_command(cmd[0], cmd[1], cmd[2])
                if appcmd:
                    results.append(appcmd)
                else:
                    unfound_commands.append(cmd)
            
            if not unfound_commands or fetch_priority != 1:
                break
            
            commands_to_find = unfound_commands
            
        return results
    
    
    
    #custom
    async def sync_individually(self, *commands: ClientsideAppCommand, ignore_errors: bool = False) -> List[AppCommand]:
        """Only the given commands will be uploaded individually, one by one, meaning no other previously existing
        commands will get deleted (as is the case with normal bulk sync).
        Whether the command is global or belongs to some guilds will be dynamically determined."""
        
        if not commands:
            return []
        
        data = []
        for cmd in commands:
            guild_ids = getattr(cmd, '_guild_ids', None)
            if not guild_ids:
                try:
                    data.append(await self._http.upsert_global_command(self.client.application_id, payload=cmd.to_dict()))
                except Exception as err:
                    if ignore_errors:
                        print(f"Failed to sync global app command, exception: {err}")
                    else:
                        raise err
            else:
                for guild_id in guild_ids:
                    try:
                        data.append(await self._http.upsert_guild_command(self.client.application_id, guild_id, payload=cmd.to_dict()))
                    except Exception as err:
                        if ignore_errors:
                            print(f"Failed to sync app command to guild with id '{guild_id}', exception: {err}")
                        else:
                            raise err
        
        results = [AppCommand(data=d, state=self._state) for d in data]
        self._add_app_commands_to_cache(*results)
        return results
    
    
    #custom
    async def _sync(self, commands: List[ClientsideAppCommand], guild_id: Optional[int] = None) -> List[AppCommand]:
        """Low-level sync function that overwrites the given guild's commands (global if None) with only the given commands.
        This doesn't save to the cache! That is left up to the caller."""
        
        if self.client.application_id is None:
            raise MissingApplicationID
        payload = [command.to_dict() for command in commands]
        if guild_id is None:
            data = await self._http.bulk_upsert_global_commands(self.client.application_id, payload=payload)
        else:
            data = await self._http.bulk_upsert_guild_commands(self.client.application_id, guild_id, payload=payload)
        return [AppCommand(data=d, state=self._state) for d in data]
    
    
    #custom
    async def unsync(self, guild = None, ignore_errors: bool = False) -> None:
        """Completely wipes all app commands from the given guild (or global if None)."""
        
        (_, guild_id) = unpack_guild_object(guild)
        
        try:
            await self._sync([], guild_id=guild_id)
        except Exception as err:
            if ignore_errors:
                if guild_id:
                    print(f"Failed to unsync app commands from guild with id '{guild_id}', exception: {err}")
                else:
                    print(f"Failed to unsync global app commands, exception: {err}")
            else:
                raise err
        finally:
            self._clear_cache(guild_id)
    
    
    #override
    async def sync(self,
        guild = None,
        *,
        avoid_deletions: bool = False,
        just_delete: bool = False,
        ignore_errors: bool = False
    ) -> List[AppCommand]:
        """Syncs commands to the guild (or global if None) and caches the results.
        avoid_deletions: if False, performs a normal sync, which overwrites everything with what's currently defined.
        if True, uploads every new command individually and leaves other unused commands undisturbed.
        just_delete: if True, no commands will be uploaded. Instead, an empty overwrite request will be made,
        which will delete all app commands from Discord from the given guild (or global if None).
        ignore_errors: if True, sync errors will only get printed instead of raising an exception."""
        
        (guild, guild_id) = unpack_guild_object(guild)
        
        if avoid_deletions:
            if just_delete:
                return []
            return await self.sync_individually(*self._get_all_commands(guild=guild), ignore_errors=ignore_errors)
        
        if just_delete:
            await self.unsync(guild=guild, ignore_errors=ignore_errors)
            return []
        
        results = []
        try:
            results = await super().sync(guild=guild)
        except Exception as err:
            if ignore_errors:
                if guild_id:
                    print(f"Failed to sync app commands to guild with id '{guild_id}', exception: {err}")
                else:
                    print(f"Failed to sync global app commands, exception: {err}")
            else:
                raise err
        else:
            self._overwrite_app_commands_cache(results, guild_id=guild_id)
        
        return results
    
    
    #custom
    async def sync_all_defined(self, *, avoid_deletions: bool = False, just_delete: bool = False, ignore_errors: bool = False) -> List[AppCommand]:
        """Syncs the bot's app commands with Discord both for global commands and for every single guild the bot is in,
        but only if there are commands defined for that given guild/global.
        avoid_deletions: if False, performs a normal sync, which overwrites everything with what's currently defined.
        if True, uploads every new command individually and leaves other unused commands undisturbed.
        just_delete: if True, no commands will be uploaded. Instead, an empty overwrite request will be made,
        which will delete all app commands from Discord from where commands have been defined.
        ignore_errors: if True, sync errors will only get printed instead of raising an exception."""
        
        if avoid_deletions:
            if just_delete:
                return []
            return await self.sync_individually(*self.get_all_client_commands(), ignore_errors=ignore_errors)
        
        results = []
        command_targets = self.get_all_command_locations()
        
        #sync global
        if None in command_targets:
            try:
                results += await self.sync(just_delete=just_delete)
            except Exception as err:
                if ignore_errors:
                    print(f"Failed to sync global app commands, exception: {err}")
                else:
                    raise err
        
        #sync guilds
        for guild in self.client.guilds:
            if guild.id not in command_targets:
                continue
            try:
                results += await self.sync(guild=guild, just_delete=just_delete)
            except Exception as err:
                if ignore_errors:
                    print(f"Failed to sync app commands to guild '{guild.name}', exception: {err}")
                else:
                    raise err
        
        return results
    
    
    #custom
    async def sync_all_undefined(self, *, ignore_errors: bool = False) -> None:
        """Clears app commands from guilds (+global) for which there are no commands defined in the bot.
        ignore_errors: if True, sync errors will only get printed instead of raising an exception."""
        
        command_targets = self.get_all_command_locations()
        
        #sync global
        if None not in command_targets:
            try:
                await self.sync(just_delete=just_delete)
            except Exception as err:
                if ignore_errors:
                    print(f"Failed to clear global app commands, exception: {err}")
                else:
                    raise err
        
        #sync guilds
        for guild in self.client.guilds:
            if guild.id in command_targets:
                continue
            try:
                await self.sync(guild=guild, just_delete=just_delete)
            except Exception as err:
                if ignore_errors:
                    print(f"Failed to clear app commands from guild '{guild.name}', exception: {err}")
                else:
                    raise err
    
    
    #custom
    async def sync_all(self, *, avoid_deletions: bool = False, just_delete: bool = False, ignore_errors: bool = False) -> List[AppCommand]:
        """Syncs the bot's app commands with Discord both for global commands and for every single guild the bot is in.
        avoid_deletions: if False, performs a normal sync, which overwrites everything with what's currently defined.
        if True, uploads every new command individually and leaves other unused commands undisturbed.
        just_delete: if True, no commands will be uploaded. Instead, an empty overwrite request will be made,
        which will delete all app commands from Discord.
        ignore_errors: if True, sync errors will only get printed instead of raising an exception."""
        
        if avoid_deletions:
            if just_delete:
                return []
            return await self.sync_all_defined(avoid_deletions=avoid_deletions, ignore_errors=ignore_errors)
        
        results = []
        try:
            results += await self.sync(just_delete=just_delete)
        except Exception as err:
            if ignore_errors:
                print(f"Failed to sync global app commands, exception: {err}")
            else:
                raise err
            
        for guild in self.client.guilds:
            try:
                results += await self.sync(guild=guild, just_delete=just_delete)
            except Exception as err:
                if ignore_errors:
                    print(f"Failed to sync app commands to guild '{guild.name}', exception: {err}")
                else:
                    raise err
        #cache is handled automatically by .sync()
        return results
    
    
    #custom
    async def sync_given(self,
        *commands: ClientsideAppCommand,
        avoid_deletions: bool = False,
        just_delete: bool = False,
        ignore_errors: bool = False
    ) -> List[AppCommand]:
        """Syncs the tree to all guilds (or global) defined in the given commands.
        avoid_deletions: if False, performs a normal sync, which overwrites everything with what's currently defined.
        if True, uploads every new command individually and leaves other unused commands undisturbed.
        just_delete: if True, no commands will be uploaded. Instead, an empty overwrite request will be made,
        which will delete all app commands from Discord from the given targets.
        ignore_errors: if True, sync errors will only get printed instead of raising an exception."""
        
        if avoid_deletions:
            if just_delete:
                return []
            return await self.sync_individually(*commands, ignore_errors=ignore_errors)
        
        #get all command locations
        guild_ids = set()
        for cmd in commands:
            guild_ids.update(self.get_command_locations(cmd))
        
        results = []
        for guild_id in guild_ids:
            results += await self.sync(guild=guild_id, just_delete=just_delete, ignore_errors=ignore_errors)
        
        return results
    
    
    #custom
    async def unsync_given(self, *commands: AnyCommand, ignore_errors: bool = False) -> List[AppCommand]:
        """Syncs the tree to all guilds (or global) defined in the given commands, but omitting these commands.
        ignore_errors: if True, sync errors will only get printed instead of raising an exception."""
        
        #get all command locations
        guild_ids = set()
        for cmd in commands:
            guild_ids.update(self.get_command_locations(cmd))
        
        results = []
        
        for guild_id in guild_ids:
            try:
                remaining_commands = [
                    cmd for cmd in self._get_all_commands(guild=unpack_guild_object(guild_id)[0])
                    if not self.get_equal_command_from(cmd, commands)
                ]
                result = await self._sync(remaining_commands, guild_id)
            except Exception as err:
                if ignore_errors:
                    if guild_id:
                        print(f"Failed to sync app command to guild with id '{guild_id}', exception: {err}")
                    else:
                        print(f"Failed to sync global app commands, exception: {err}")
                else:
                    raise err
            else:
                self._overwrite_app_commands_cache(result, guild_id=guild_id)
                results += result
        
        return results
