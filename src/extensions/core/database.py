import discord
from discord.ext import commands
from smart_bot import SmartBot
from smart_cogs import *

import aiosqlite


"""
Config template:
{
    "database_file": str = relative path from the bot's data directory
}
"""


async def setup(bot: SmartBot):
    cog = DatabaseCog(bot, __name__)
    bot.utils.db = cog
    await bot.add_cog(cog)

async def teardown(bot: SmartBot):
    await bot.utils.db.teardown()
    del bot.utils.db



class DatabaseCog(SmartCog):
    """Utility cog for managing a database connected to the bot."""
    def __init__(self, bot: SmartBot, ext_name: str):
        super().__init__(bot, ext_name)
        
        self.db_path = self.bot.utils.pathhelper.from_data_dir(self.config["database_file"])
        self._db = None

    async def cog_load(self):
        self._db = await aiosqlite.connect(self.db_path)

    async def cog_unload(self):
        await self._db.close()

    @commands.Cog.listener("on_console_input")
    async def console_command_handler(self, input_line):
        if input_line[:4].lower() == "sql ":
            async with self._db.execute(input_line[4:]) as cursor:
                await self._db.commit()
                async for row in cursor:
                    print(row)


    async def fetch_rows(self, query: str, params: tuple = None):
        """Returns all rows from a select statement."""
        return await self._db.execute_fetchall(query, params)

    async def fetch_row(self, query: str, params: tuple = None):
        """Returns a single row from a select statement."""
        cursor = await self._db.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return row
    
    async def fetch_value(self, query: str, params: tuple = None):
        """Returns a single parsed value from a select statement."""
        cursor = await self._db.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            return row[0]
        return None

    async def execute(self, query: str, params: tuple = None):
        """Used to run any statement that modified the database or its data. No return value."""
        cursor = await self._db.execute(query, params)
        await cursor.close()
        await self._db.commit()

    async def check(self, query: str, params: tuple = None):
        cursor = self._db.execute(query, params)