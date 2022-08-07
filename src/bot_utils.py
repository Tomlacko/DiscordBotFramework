import discord
#from smart_bot import SmartBot #circular import

from typing import Optional, Union

import os




class PathHelper:
    def __init__(self, bot):
        self.bot = bot
    
    def in_bot_dir(self, relative_path: str) -> str:
        return os.path.join(self.bot.paths.bot_dir, relative_path)
    
    def in_data_dir(self, relative_path: str) -> str:
        return os.path.join(self.bot.paths.data_dir, relative_path)
    
    def in_resources_dir(self, relative_path: str) -> str:
        return os.path.join(self.bot.paths.resources_dir, relative_path)
    
    def in_extensions_dir(self, relative_path: str) -> str:
        return os.path.join(self.bot.paths.extensions_dir, relative_path)



class ResolveHelper:    
    def __init__(self, bot):
        self.bot = bot
    
    
    async def guild(self, guild, fetch_if_not_found: bool) -> Optional[discord.Guild]:
        """Safely resolves 'guild' to a discord.Guild object.
        This will work for every guild the bot is in.
        For foreign guilds, None is returned.
        
        Using bot.get_guild is preferred in almost every case.
        This function is bloated with cases that generally
        don't need to be handled.
        
        guild:
        Passing in None will return None.
        Passing in an existing guild object will return it.
        Otherwise a guild ID will be expected.
        fetch_if_not_found: True when you want to force the bot to
        find the guild, even if it's not found in cache, which shouldn't
        happen during normal circumstances.
        """
        
        if not guild:
            return None
        
        if isinstance(guild, discord.Guild):
            return guild
        
        resolved_guild = self.bot.get_guild(guild)
        if resolved_guild:
            return resolved_guild
        
        if not fetch_if_not_found:
            return None
        
        try:
            resolved_guild = await self.bot.fetch_guild(guild)
        except:
            return None
        
        return resolved_guild
    
    
    async def user(self, user_id, convert_member_to_user: bool = False) -> Optional[discord.User]:
        """Safely resolves 'user' to a discord.User object.
        Firstly, the cache is checked, and if nothing is found,
        a fetch request is made. If a user is not found even after
        that, then None is returned.
        
        user:
        Passing in None will return None.
        Passing in an existing user object will return it.
        Passing in a member will convert it to a plain user
        if convert_member_to_user is set to True, otherwise it will just return it.
        Otherwise a user ID will be expected.
        """
        
        if not user_id:
            return None
        
        if isinstance(user_id, discord.User):
            return user_id
        if isinstance(user_id, discord.Member):
            if not convert_member_to_user:
                return user_id
            user_id = user_id.id
        
        user = self.bot.get_user(user_id)
        if user:
            return user
        
        try:
            user = await self.bot.fetch_user(user_id)
        except:
            return None
        
        return user
    
    
    async def member(self, user, guild) -> Optional[discord.Member]:
        """Safely resolves 'user' to a discord.Member object.
        Returns a member object if a user is the given guild, otherwise returns None.
        
        The function will do this as efficiently as possible.
        
        user:
        Passing in None will return None.
        Passing in an existing member will return it if it's from the passed in guild already,
        otherwise it will be treated just like a user object.
        Otherwise a user ID or a user object will be expected.
        guild: Can be either discord.Guild or a plain guild ID.
        """
        
        if not user or not guild:
            return None
        
        if not isinstance(guild, discord.Guild):
            guild = self.bot.get_guild(guild)
            if not guild:
                return None
        
        if isinstance(user, discord.Member):
            if user.guild.id == guild.id:
                return user
            user = user.id
        elif isinstance(user, discord.User):
            user = user.id
        
        member = guild.get_member(user)
        if member:
            return member
        
        try:
            member = await guild.fetch_member(user)
        except:
            return None
        
        return member
    
    
    async def member_or_user(self, user, guild) -> Optional[Union[discord.User, discord.Member]]:
        """Safely resolves 'user' to a discord.Member object if user is in the given guild,
        otherwise resolves to discord.User object. If neither is possible, returns None.
        
        The function will do this as efficiently as possible.
        
        user:
        Passing in None will return None.
        Passing in an existing member will return it if it's from the passed in guild already,
        otherwise it will be treated just like a user object.
        Otherwise a user ID or a user object will be expected.
        guild: Can be either discord.Guild or a plain guild ID. If None, then only
        a user object will be possible to be returned
        """
        
        if not user:
            return None
        
        if not guild:
            return await self.user(user, False)
        
        if not isinstance(guild, discord.Guild):
            guild = self.bot.get_guild(guild)
            if not guild:
                return None
        
        resolved_user = None
        
        if isinstance(user, discord.Member):
            if user.guild.id == guild.id:
                return user
            user = user.id
        elif isinstance(user, discord.User):
            resolved_user = user
            user = user.id
        
        member = guild.get_member(user)
        if member:
            return member
        
        try:
            member = await guild.fetch_member(user)
        except:
            pass
        else:
            if member:
                return member
        
        if resolved_user:
            return resolved_user
        
        resolved_user = self.bot.get_user(user)
        if resolved_user:
            return resolved_user
        
        try:
            resolved_user = await self.bot.fetch_user(user)
        except:
            return None
        
        return resolved_user
        
    
    async def role(self, role_id, guild, fetch_if_not_found: bool = False) -> Optional[discord.Role]:
        """Safely resolves 'role_id' to a discord.Role object.
        Returns a role object of a given guild, otherwise returns None.
        
        role_id:
        Passing in None will return None.
        Passing in an existing role object will return it.
        Otherwise a role ID will be expected.
        guild: Can be either discord.Guild or a plain guild ID.
        fetch_if_not_found: Will perform an additional roles fetch
        from the guild if the role is not found in the cache. False by default.
        """
        
        if not role_id:
            return None
        if isinstance(role_id, discord.Role):
            return role_id
        if not guild:
            return None
        
        if not isinstance(guild, discord.Guild):
            guild = self.bot.get_guild(guild)
            if not guild:
                return None
        
        role = guild.get_role(role_id)
        if role or not fetch_if_not_found:
            return role
        
        try:
            roles = await guild.fetch_roles()
            for role in roles:
                if role.id == role_id:
                    return role
        except:
            pass
        
        return None
    
    
    def is_channel(self, channel) -> bool:
        """Checks if a given object is a discord channel."""
        return channel and hasattr(channel, "type") and isinstance(channel.type, discord.ChannelType)
    
    
    async def channel(self, channel_id) -> Optional[Union[discord.abc.GuildChannel, discord.Thread, discord.abc.PrivateChannel]]:
        """Safely resolves 'channel_id' to a discord channel object.
        Returns a channel object if found, otherwise returns None.
        
        channel_id:
        Passing in None will return None.
        Passing in an existing channel object will return it.
        Otherwise a channel ID will be expected.
        """
        
        if not channel_id:
            return None
        
        if self.is_channel(channel_id):
            return channel_id
        
        resolved_channel = self.bot.get_channel(channel_id)
        if resolved_channel:
            return resolved_channel
        
        try:
            resolved_channel = await self.bot.fetch_channel(channel_id)
        except:
            return None
        
        return resolved_channel
    
    
    async def message(self, message_id, messageable, assume_channel_id_first = True) -> Optional[discord.Message]:
        """Safely resolves 'message_id' to a discord.Message object.
        Returns a message object of a given channel or user, otherwise returns None.
        
        message_id:
        Passing in None will return None.
        Passing in an existing message object will return it.
        Otherwise a message ID will be expected, and will be searched for
        in the given messageable
        messageable:
        Passing in None will return None (unless message_id is an existing message object).
        Passing in an existing messageable object (channel, user...) will use it as is.
        Passing in a plain ID will first treat it as a channel ID / user ID and automatically convert it.
        assume_channel_id_first: If true, the plain ID will be attempted to be converted to a valid channel ID first,
        and if that fails, it will treat it as a user ID and try to convert that. If false, the opposite order will apply.
        """
        
        if not message_id:
            return None
        if isinstance(message_id, discord.Message):
            return message_id
        
        #try find the message in cache
        message = self.bot._connection._get_message(message_id)
        if message:
            return message
        
        if not messageable:
            return None
        
        #if messagable is plain ID
        if not isinstance(messageable, discord.abc.Messageable):
            messageable_resolved = await (self.channel(messageable) if assume_channel_id_first else self.user(messageable))
            if not messageable_resolved:
                messageable_resolved = await (self.user(messageable) if assume_channel_id_first else self.channel(messageable))
                if not messageable_resolved:
                    return None
            messageable = messageable_resolved
        
        try:
            message = await messageable.fetch_message(message_id)
        except:
            return None
        
        return message
