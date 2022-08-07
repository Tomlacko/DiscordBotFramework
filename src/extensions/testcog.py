import discord
from discord import app_commands
from discord.ext import commands
from smart_bot import SmartBot
from smart_cogs import *


"""
Config template:
{
    
}
"""



async def setup(bot: SmartBot):
    await bot.add_cog(TestCog(bot))

async def teardown(bot: SmartBot):
    print("Teardown testcog")



class TestCog(SmartCog):
    """Test cog."""
    
    def __init__(self, bot: SmartBot):
        print("Initializing test cog!")
        super().__init__(bot)

    async def cog_load(self):
        print("Test cog is async initialized!")
        await super().cog_load()
    
    @run_when_ready
    async def ready_init(self):
        print("Test cog is ready!")
    
    async def cog_unload(self):
        print("Async unloading test cog!")
        await super().cog_unload()
    
    
    
    
    @commands.Cog.listener("on_console_input")
    async def console_listener(self, input_line):
        return
        if input_line == "get":
            for guild in self.bot.guilds:
                cmds = self.bot.tree.get_commands(guild=guild)
                for cmd in cmds:
                    print(cmd.name)
        elif input_line == "fetch":
            for guild in self.bot.guilds:
                cmds = await self.bot.tree.fetch_commands(guild=guild)
                for cmd in cmds:
                    print(cmd.name)
        elif input_line == "sync":
            await self.bot.tree.sync_all(ignore_errors=True)
        elif input_line == "prune":
            await self.bot.tree.sync_all(just_delete=True, ignore_errors=True)
    
    
    
    
    # HYBRID GROUP
    
    @for_main_guild
    @commands.hybrid_group(name="testgroup")
    async def my_cmd_group(self, ctx: commands.Context) -> None:
        """Group description aaaa"""
        await ctx.send("Group")
    
    @my_cmd_group.command(name="testsub")
    async def my_subcommand(self, ctx: commands.Context) -> None:
        """Subcommand description bbbb"""
        await ctx.send("Subcommand")
    
    @my_cmd_group.group(name="subgroup")
    async def my_subgroup(self, ctx: commands.Context) -> None:
        """Subgroup description cccc"""
        await ctx.send("Subgroup")
    
    @my_subgroup.command(name="subsubcmd")
    async def my_subsubcommand(self, ctx: commands.Context) -> None:
        """Subsubcommand description ddddd"""
        await ctx.send("Subsubcommand")
    
    
    # HYBRID COMMAND
    #@for_main_guild
    @commands.hybrid_command(name="testcmd")
    @app_commands.guild_only()
    #@app_commands.guilds(922667089037258792)
    async def my_command(self, ctx: commands.Context) -> None:
        """Test command in guild"""
        await ctx.send("Hello from test command!", ephemeral=True)
    
    
    # CLASSIC COMMAND
    @for_main_guild
    @commands.command("pure_classic")
    async def classic_command(self, ctx: commands.Context):
        await ctx.send("Classic command")
    
    
    # APP COMMAND
    @for_main_guild
    @app_commands.command(name="pure_app")
    async def pure_app_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pure command")
    
    
    
    # APP GROUP
    
    #original method:
    #my_pure_group = app_commands.guilds(922667089037258792)(app_commands.Group(name="pure_group", description="This is a pure app group."))
    
    #new method:
    @for_main_guild
    @app_commands_Group(name="pure_group")
    async def my_pure_group(self, interaction: discord.Interaction):
        """This is a pure group made via decorator"""
        #this will never actually run
    
    @my_pure_group.command(name="subpure")
    async def pure_group_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pure group command")