import discord
from discord.ext import commands
from smart_bot import SmartBot
from smart_cogs import *


"""
Config template:
{
    server_id: {
        "role_levels": {
            role_id: perm_level,
        },
        "user_levels": {
            user_id: perm_level,
        }
    },
}
"""
# perm_level must be >= 0
# 0 is the default value for everyone and is returned by all functions if they don't find any level
# actual perm_level = maximum of all applicable for a given user
# each config component is optional



async def setup(bot: SmartBot):
    cog = PermissionsCog(bot, __name__)
    bot.utils.perms = cog
    await bot.add_cog(cog)

async def teardown(bot: SmartBot):
    del bot.utils.perms



class PermissionsCog(SmartCog):
    """Utility cog implementing permission levels."""

    def __init__(self, bot: SmartBot, ext_name: str):
        super().__init__(bot, ext_name)


    def _get_level(self, server_id: int, user_id: int, role_ids: list) -> int:
        level = 0

        server_config = self.config.get(server_id, None)
        if not server_config:
            return level
        
        user_levels = server_config.get("user_levels", None)
        if user_levels:
            level = max(level, user_levels.get(user_id, 0))

        role_levels = server_config.get("role_levels", None)
        if role_levels:
            for role_id in role_ids:
                level = max(level, role_levels.get(role_id, 0))
        
        return level
    
    
    def _get_user_level(self, server_id: int, user_id: int) -> int:
        server_config = self.config.get(server_id, None)
        if not server_config:
            return 0
        
        user_levels = server_config.get("user_levels", None)
        if not user_levels:
            return 0
        
        return user_levels.get(user_id, 0)
    
    
    def _get_role_level(self, server_id: int, role_id: int) -> int:
        server_config = self.config.get(server_id, None)
        if not server_config:
            return 0

        role_levels = server_config.get("role_levels", None)
        if not role_levels:
            return 0
        
        return role_levels.get(role_id, 0)
    
    
    #######
    

    def get_role_level(self, role, server=None) -> int:
        """Get the permission level corresponding to this role.
        
        role: Can be either a role object or a role ID.
        server: When passing a plain role ID, the lookup can
        be made more efficient by passing the role's server as well.
        Can be either a guild object or a guild ID.
        """
        
        if isinstance(role, discord.Role):
            server = role.guild.id
            role = role.id
        elif not isinstance(role, int):
            raise ValueError("Provided 'role' is neither a 'discord.Role' object nor an ID!")
        elif isinstance(server, discord.Guild):
            server = server.id
        
        if server:
            return self._get_role_level(server, role)
        
        for server_config in self.config.values():
            role_levels = server_config.get("role_levels", None)
            if role_levels:
                level = role_levels.get(role, None)
                if level is not None:
                    return level
        
        return 0


    def get_member_level(self, member: discord.Member) -> int:
        """Get the highest permission level of a server member.
        
        member: Must be discord.Member object.
        """

        # if not isinstance(member, discord.Member):
        #    raise ValueError("Argument 'member' must be of type discord.Member!")

        return self._get_level(member.guild.id, member.id, [role.id for role in member.roles])
    

    async def get_user_level(self, user, server) -> int:
        """Get the highest permission level of a user in a given server.
        
        user: Can be either discord.Member, discord.User or a plain user ID.
        Even if it's a discord.Member, the server argument will override in which
        server will the lookup be made.
        server: Can be either discord.Guild or a plain guild ID.
        """
        
        # if not user:
        #     raise ValueError("Argument 'user' is required!")
        
        user_id = user
        if isinstance(user, discord.Member):
            if not server or user.guild.id == (server.id if isinstance(server, discord.Guild) else server):
                return self.get_member_level(user)
            user_id = user.id
        elif not server:
            raise ValueError("Argument 'server' is required when argument 'user' is not of type discord.Member!")
        elif isinstance(user, discord.User):
            user_id = user.id
        
        if not isinstance(server, discord.Guild):
            server_id = server
            server = self.bot.get_guild(server_id)
            if not server:
                raise ValueError(f"Server with ID {server_id!r} not found!")
        
        resolved_member = await self.bot.utils.resolve.member(user_id, server)
        if not resolved_member:
            return 0 #if not in the server, no levels apply
            # previously:
            # user not found in the server, can't check roles, check only user_levels
            # return self._get_user_level(server.id, user_id)
        
        return self.get_member_level(resolved_member)
    
    
    async def get_user_level_global(self, user) -> int:
        """Get the highest possible level this user has in all
        the servers combined. This lookup can be expensive.
        
        user: can be either discord.Member, discord.User or
        a plain user ID. The former two will get reduced to an ID and
        the user will be fetched again anyways, to bypass the often-faulty cache.
        """
        
        if isinstance(user, discord.User) or isinstance(user, discord.Member):
            user = user.id
        
        # do not use cache, because it's often missing mutual servers
        try:
            user = await self.bot.fetch_user(user)
        except:
            return 0
        
        level = 0
        
        for guild in user.mutual_guilds:
            resolved_member = await self.bot.utils.resolve.member(user, guild)
            if resolved_member:
                level = max(level, self._get_level(guild.id, user, [role.id for role in resolved_member.roles]))
        
        return level
    
    
    async def get_level(self, user_or_member) -> int:
        """Finds the applicable level based on what is passed in.
        
        user_or_member: If member, then the permission level for that member
        in the particular guild is returned. Otherwise all guilds are checked
        for the highest level applicable to this user (useful for DM commands).
        """
        
        if isinstance(user_or_member, discord.Member):
            return self.get_member_level(user_or_member)
        
        return await self.get_user_level_global(user_or_member)


    #############################
    
    
    @commands.command(name="level")
    async def level_cmd(self, ctx: commands.Context):
        level = await self.get_level(ctx.author)
        await ctx.reply(f"Your level in this channel is: {level}")