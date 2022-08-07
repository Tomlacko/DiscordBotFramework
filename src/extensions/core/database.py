import discord
from discord.ext import commands
from smart_bot import SmartBot
from smart_cogs import *

import aiosqlite

from utils.formatting import make_table_string
from utils.common import get_exception_string

"""
Config template:
{
    "database_file": str = relative path from the bot's data directory
}
"""


async def setup(bot: SmartBot):
    cog = DatabaseCog(bot)
    bot.utils.db = cog
    await bot.add_cog(cog)

async def teardown(bot: SmartBot):
    del bot.utils.db



class _UnselectedSentinel:
    """Used instead of 'None' in place of values from columns that have not been selected in a given database query."""
    
    __slots__ = ()

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __bool__(self):
        return False

    def __hash__(self):
        return 0

    def __repr__(self):
        return '<UNSELECTED>'



class InvalidQueryData(Exception):
    """
    Thrown when attempting to make a database query with invalid data.
    """
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid data given to a query: {reason}")

class UnsafeQueryParameter(Exception):
    """
    Thrown when attempting to make a database query with unsafe parameters.
    """
    def __init__(self, parameter: str) -> None:
        super().__init__(f"Parameter {parameter!r} has unsafe characters/format.")



class DatabaseCog(SmartCog):
    """Utility cog for managing a database connected to the bot."""
    
    UNSELECTED = _UnselectedSentinel()
    
    def __init__(self, bot: SmartBot):
        super().__init__(bot)
        
        self.db_path = self.bot.utils.pathhelper.in_data_dir(self.config["database_file"])
        self._db = None


    async def cog_load(self):
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await super().cog_load()


    async def cog_unload(self):
        await self._db.close()
        await super().cog_unload()
    
    
    @commands.Cog.listener("on_console_input")
    async def console_command_handler(self, input_line):
        if input_line[:4].lower() != "sql ":
            return
        print(await self.ui_query(input_line[4:]))
    
    
    @commands.command(name="sql")
    @commands.is_owner()
    async def chat_query(self, ctx: commands.Context, *, query: str):
        await ctx.reply("```\n" + await self.ui_query(query) + "```")
        
    
    
    @staticmethod
    def is_safe_parameter(param: str) -> bool:
        return isinstance(param, str) and param.isidentifier()

    @staticmethod
    def annotate_row(row):
        try:
            return dict(row)
        except:
            pass
        return None
        
    @staticmethod
    def annotate_rows(rows):
        if not rows or len(rows) == 0:
            return rows
        return [self.annotate_row(row) for row in rows]
    
    
    
    async def ui_query(self, query: str, params: tuple = None) -> str:
        """This function acts as a user interface for the database.
        Provided queries are safely executed and any results are returned.
        Errors are caught and returned as strings, results are returned as table-formatted strings.
        """
        
        rows = []
        headers = []
        lastrowid = None
        rowcount = -1
        result = ""
        
        try:
            await self._db.commit()
            async with self._db.execute(query, params) as cursor:
                rowcount = cursor.rowcount
                lastrowid = cursor.lastrowid
                if cursor.description:
                    headers = [desc[0] for desc in cursor.description]
                rows = await cursor.fetchall()
        except Exception as err:
            await self._db.rollback()
            result += f"Query failed! Exception:\n{get_exception_string(err)}\n"
        else:
            await self._db.commit()
            if rowcount < 0:
                result += f"Query successful! Rows returned: {len(rows)}\n"
                result += make_table_string(
                    rows,
                    headers=headers,
                    max_cell_content_width=32,
                    show_row_numbers=True
                )
            else:
                result += f"Success! Rows added/altered: {rowcount}, last row ID: {lastrowid}"
        
        return result
    
    
    #####
    
    
    async def _execute(self, query: str, params: tuple = None):
        """Used to run any statement that modifies the database or its data.
        Returns the inserted row's ID if possible, otherwise None.
        Does not perform commit or rollback on error."""
        async with self._db.execute(query, params) as cursor:
            return cursor.lastrowid
    
    async def execute(self, query: str, params: tuple = None):
        """Used to run any statement that modifies the database or its data.
        Returns the inserted row's ID if possible, otherwise None."""
        lastrowid = None
        try:
            await self._db.commit()
            lastrowid = await self._execute(query, params)
        except Exception as err:
            await self._db.rollback()
            raise err
        else:
            await self._db.commit()
        return lastrowid
    
    
    async def _execute_many(self, query: str, list_of_params) -> None:
        """Used to run a single statement many times with different data.
        Does not perform commit or rollback on error. No return value.
        """
        async with self._db.executemany(query, list_of_params) as cursor:
            pass
    
    async def execute_many(self, query: str, list_of_params) -> None:
        """Used to run a single statement many times with different data.
        Commits on complete success, otherwise rolls back. No return value."""
        try:
            await self._db.commit()
            await self._execute_many(query, list_of_params)
        except Exception as err:
            await self._db.rollback()
            raise err
        else:
            await self._db.commit()
    
    
    async def fetch_row(self, query: str, params: tuple = None) -> aiosqlite.Row:
        """Returns a single row from the ran query. Does not perform commit or rollback on error.
        To be used only for read-only operations."""
        async with self._db.execute(query, params) as cursor:
            return await cursor.fetchone()
    
    async def execute_and_fetch_row(self, query: str, params: tuple = None) -> aiosqlite.Row:
        """Returns a single row from the ran query. Used for modify/write operations.
        For read-only operations, use fetch_row instead."""
        row = None
        try:
            await self._db.commit()
            row = await self.fetch_row(query, params)
        except Exception as err:
            await self._db.rollback()
            raise err
        else:
            await self._db.commit()
        return row

    
    async def fetch_rows(self, query: str, params: tuple = None) -> list:
        """Returns all rows from the ran query. Does not perform commit or rollback on error.
        To be used only for read-only operations."""
        async with self._db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def execute_and_fetch_rows(self, query: str, params: tuple = None) -> list:
        """Returns all rows from the ran query. Used for modify/write operations.
        For read-only operations, use fetch_rows instead."""
        rows = []
        try:
            await self._db.commit()
            rows = await self.fetch_rows(query, params)
        except Exception as err:
            await self._db.rollback()
            raise err
        else:
            await self._db.commit()
        return rows
    
    
    async def fetch_value(self, query: str, params: tuple = None):
        """Returns a single parsed value from the ran query with a single column.
        Does not perform commit or rollback on error. To be used only for read-only operations."""
        row = await self.fetch_row(query, params)
        if row and len(row) > 0:
            return row[0]
        return None
    
    async def execute_and_fetch_value(self, query: str, params: tuple = None):
        """Returns a single parsed value from the ran query with a single column.
        Used for modify/write operations. For read-only operations, use fetch_value instead."""
        row = await self.execute_and_fetch_row(query, params)
        if row and len(row) > 0:
            return row[0]
        return None

    async def fetch_values(self, query: str, params: tuple = None) -> list:
        """Returns a list of values from the ran query with a single column.
        Does not perform commit or rollback on error. To be used only for read-only operations."""
        rows = await self.fetch_rows(query, params)
        if not rows or len(rows) == 0:
            return []
        return [row[0] for row in rows]
    
    async def execute_and_fetch_values(self, query: str, params: tuple = None) -> list:
        """Returns a list of values from the ran query with a single column.
        Used for modify/write operations. For read-only operations, use fetch_value instead."""
        rows = await self.execute_and_fetch_rows(query, params)
        if not rows or len(rows) == 0:
            return []
        return [row[0] for row in rows]
    
    
    async def insert(self, _table_name: str, _accept_unsafe: bool = False, /, **kwargs):
        """Shorthand for `INSERT INTO table_name (kwargs.keys()) VALUES (kwargs.values())`.
        Returns the inserted row's ID if possible, otherwise None."""
        if len(kwargs) == 0:
            return None
        
        #validate safe table name and column names
        if not _accept_unsafe:
            if not self.is_safe_parameter(_table_name):
                raise UnsafeQueryParameter(_table_name)
            for column in kwargs.keys():
                if not self.is_safe_parameter(column):
                    raise UnsafeQueryParameter(column)
        
        columns = "\", \"".join(kwargs.keys())
        questionmarks = "?" + (", ?"*(len(kwargs)-1))
        params = tuple(kwargs.values())
        query = f"INSERT INTO \"{_table_name}\" (\"{columns}\") VALUES ({questionmarks})"
        
        return await self.execute(query, params)
    
    
    async def insert_many(self, table_name: str, data, column_names: tuple = None, accept_unsafe: bool = False) -> None:
        """Shorthand for running the same insert query multiple times for multiple rows of data.
        column_names should be a tuple of column names. If empty or None, data will be inserted in column definition order.
        data should be a list (or similar) of tuples/lists, each containing just the data to be inserted.
        All of these need to be the same length as each other and as the column_names, if defined."""
        if len(data) == 0:
            return
        
        #validate column counts
        column_count = 0
        if column_names:
            column_count = len(column_names)
        if column_count == 0:
            column_count = len(data[0])
        for data_row in data:
            if len(data_row) != column_count:
                raise InvalidQueryData("Mismatching amount of data given.")
        
        #validate safe table name and column names
        if not accept_unsafe:
            if not self.is_safe_parameter(table_name):
                raise UnsafeQueryParameter(table_name)
            if column_names:
                for column in column_names:
                    if not self.is_safe_parameter(column):
                        raise UnsafeQueryParameter(column)
        
        columns_string = " (\"" + ("\", \"".join(column_names)) + "\")" if column_names and len(column_names) > 0 else ""
        questionmarks = "?" + (", ?"*(column_count-1))
        query = f"INSERT INTO \"{table_name}\"{columns_string} VALUES ({questionmarks})"
        
        await self.execute_many(query, data)
    
    
    async def fetch_row_by_id(self, table_name: str, rowid: int, accept_unsafe: bool = False) -> aiosqlite.Row:
        """Shorthand for fetching a row with a given rowid, usually obtained from insert operations."""
        if not accept_unsafe and not self.is_safe_parameter(table_name):
            raise UnsafeQueryParameter(table_name)
        return await self.fetch_row(f"SELECT * FROM \"{table_name}\" WHERE \"rowid\"=?", (rowid,))
    
    
    async def fetch_row_count(self, table_name: str, accept_unsafe: bool = False) -> int:
        """Returns the number of existing rows in a given table."""
        if not accept_unsafe and not self.is_safe_parameter(table_name):
            raise UnsafeQueryParameter(table_name)
        return await self.fetch_value(f"SELECT COUNT(*) FROM \"{table_name}\"")
    
    
    async def fetch_tables(self, include_internal_tables: bool = False) -> list:
        """Returns all tables and their info. Internal tables are excluded by default."""
        query = "SELECT * FROM \"sqlite_master\" WHERE \"type\"='table'"
        if not include_internal_tables:
            query += " AND \"name\" NOT LIKE 'sqlite/_%' ESCAPE '/'"
        return await self.fetch_rows(query)
    
    async def fetch_table_names(self, include_internal_tables: bool = False) -> list:
        """Returns a list of all table names contained in the database. Internal tables are excluded by default."""
        query = "SELECT \"name\" FROM \"sqlite_master\" WHERE \"type\"='table'"
        if not include_internal_tables:
            query += " AND \"name\" NOT LIKE 'sqlite/_%' ESCAPE '/'"
        return await self.fetch_values(query)
        
    
    async def fetch_table_columns(self, table_name: str, *, accept_unsafe: bool = False) -> list:
        """Returns all column info for a given table."""
        if not accept_unsafe and not self.is_safe_parameter(table_name):
            raise UnsafeQueryParameter(table_name)
        return await self.fetch_rows(f"PRAGMA table_info('{table_name}')")
    
    async def fetch_table_column_names(self, table_name: str, *, accept_unsafe: bool = False) -> list:
        """Returns a list of all column names for a given table."""
        if not accept_unsafe and not self.is_safe_parameter(table_name):
            return []
        async with self._db.execute(f"SELECT * FROM \"{table_name}\" LIMIT 0") as cursor:
            return [desc[0] for desc in cursor.description]
