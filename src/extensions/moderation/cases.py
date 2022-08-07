import discord
from discord.ext import commands
from smart_bot import SmartBot
from smart_cogs import *


from utils.time_helper import current_timestamp, stringify_duration
from utils.formatting import informative_user_mention

"""
Config template:
{
    case_logs_channel_id: int
}
"""



async def setup(bot: SmartBot):
    cog = CasesCog(bot)
    bot.utils.cases = cog
    await bot.add_cog(cog)

async def teardown(bot: SmartBot):
    del bot.utils.cases




class CasesCog(SmartCog):
    """Utility cog implementing moderation cases."""
    
    DEPENDENCIES = ["core.database"]
    
    
    def __init__(self, bot: SmartBot):
        super().__init__(bot)
    
    
    async def cog_load(self):
        await self.bot.utils.db.execute("""
            CREATE TABLE IF NOT EXISTS "cases" (
                "case_id"	INTEGER NOT NULL UNIQUE,
                "type_id"	INTEGER NOT NULL,
                "user_id"	INTEGER NOT NULL,
                "mod_id"	INTEGER NOT NULL,
                "flags"	INTEGER NOT NULL,
                "timestamp"	REAL NOT NULL,
                "timestamp_expire"	REAL,
                "source_link"	TEXT,
                "text"	TEXT,
                PRIMARY KEY("case_id" AUTOINCREMENT)
            )
        """)
        await super().cog_load()
    
    
    CASE_TYPES = ["Unknown", "Note", "Warning", "Mute", "Mute update", "Unmute", "Kick", "Ban", "Ban update", "Unban"]
    CASE_TYPE_COLORS = [0x000000, 0x0077FF, 0xFFDD00, 0x808080, 0x888888, 0xFFFFFF, 0xFF5500, 0xF00000, 0xE03333, 0x00EE00]
    
    
    @classmethod
    def get_case_type(cls, case_type_id: int) -> str:
        if case_type_id >= len(cls.CASE_TYPES):
            return cls.CASE_TYPES[0]
        return cls.CASE_TYPES[case_type_id]
    
    @classmethod
    def get_case_type_id(cls, case_type: str) -> int:
        try:
            return cls.CASE_TYPES.index(case_type)
        except:
            pass
        return 0
    
    @classmethod
    def get_case_type_color(cls, case_type_id: int) -> str:
        if case_type_id >= len(cls.CASE_TYPES):
            return cls.CASE_TYPE_COLORS[0]
        return cls.CASE_TYPE_COLORS[case_type_id]
    
    
    class Case:
        def __init__(self,
            case_id: int,
            case_type_id: int,
            user_id: int,
            mod_id: int,
            flags: int,
            timestamp: float,
            timestamp_expire: float = None,
            source_link: str = None,
            text: str = None
        ):
            self.case_id = case_id
            self.case_type_id = case_type_id
            self.case_type = CasesCog.get_case_type(case_type_id)
            self.case_type_color = CasesCog.get_case_type_color(case_type_id)
            self.user_id = user_id
            self.mod_id = mod_id
            self.flags = flags
            self.timestamp = timestamp
            self.timestamp_expire = timestamp_expire
            self.duration = None if timestamp_expire is None else timestamp_expire-timestamp
            self.source_link = source_link
            self.text = text
            self.reason = text
            
            parsed_flags = CasesCog.parse_flags(flags)
            self.through_bot = parsed_flags["through_bot"]
            self.was_user_in_server = parsed_flags["was_user_in_server"]
            self.dm_attempted = parsed_flags["dm_attempted"]
            self.dm_succeeded = parsed_flags["dm_succeeded"]
    
    
    
    
    @staticmethod
    def make_flag(*, through_bot: bool, was_user_in_server: bool, dm_attempted: bool, dm_succeeded: bool) -> int:
        return through_bot | (was_user_in_server << 1) | (dm_attempted << 2) | (dm_succeeded << 3)
    
    @staticmethod
    def parse_flags(flag: int) -> dict:
        return {
            "through_bot": bool(flag & 1),
            "was_user_in_server": bool((flag >> 1) & 1),
            "dm_attempted": bool((flag >> 2) & 1),
            "dm_succeeded": bool((flag >> 3) & 1)
        }
    
    
    ######
    
    
    async def add_case(self, *,
        case_type_id: int,
        user_id: int,
        mod_id: int,
        flags: int,
        timestamp: float = current_timestamp(),
        timestamp_expire: float = None,
        source_link: str = None,
        text: str = None,
    ) -> None:
        """Generic method to add a case in the database."""
        await self.bot.utils.db.insert("cases",
            type_id = case_type_id,
            user_id = user_id,
            mod_id = mod_id,
            flags = flags,
            timestamp = timestamp,
            timestamp_expire = timestamp_expire,
            source_link = source_link,
            text = text
        )
    
    
    async def add_note(self, *,
        user_id: int,
        mod_id: int,
        timestamp: float = current_timestamp(),
        source_link: str = None,
        note: str = None,
        was_user_in_server: bool,
        dm_attempted: bool,
        dm_succeeded: bool
    ) -> None:
        """Logs a user note in the database."""
        await self.add_case(
            case_type_id = 1,
            user_id = user_id,
            mod_id = mod_id,
            flags = self.make_flag(through_bot = True, was_user_in_server = was_user_in_server, dm_attempted = dm_attempted, dm_succeeded = dm_succeeded),
            timestamp = timestamp,
            source_link = source_link,
            text = note
        )
    
    
    async def add_warn(self, *,
        user_id: int,
        mod_id: int,
        timestamp: float = current_timestamp(),
        source_link: str = None,
        reason: str = None,
        was_user_in_server: bool,
        dm_attempted: bool,
        dm_succeeded: bool
    ) -> None:
        """Logs a user warning in the database."""
        await self.add_case(
            case_type_id = 2,
            user_id = user_id,
            mod_id = mod_id,
            flags = self.make_flag(through_bot = True, was_user_in_server = was_user_in_server, dm_attempted = dm_attempted, dm_succeeded = dm_succeeded),
            timestamp = timestamp,
            source_link = source_link,
            text = reason
        )
    
    
    async def add_mute(self, *,
        user_id: int,
        mod_id: int,
        timestamp: float = current_timestamp(),
        duration: int = None,
        source_link: str = None,
        reason: str = None,
        through_bot: bool,
        was_user_in_server: bool,
        dm_attempted: bool,
        dm_succeeded: bool
    ) -> None:
        """Logs a user mute in the database."""
        await self.add_case(
            case_type_id = 3,
            user_id = user_id,
            mod_id = mod_id,
            flags = self.make_flag(through_bot = through_bot, was_user_in_server = was_user_in_server, dm_attempted = dm_attempted, dm_succeeded = dm_succeeded),
            timestamp = timestamp,
            timestamp_expire = None if duration is None else timestamp+duration,
            source_link = source_link,
            text = reason
        )
    
    
    async def add_mute_update(self, *,
        user_id: int,
        mod_id: int,
        timestamp: float = current_timestamp(),
        timestamp_expire: float = None,
        source_link: str = None,
        reason: str = None,
        through_bot: bool,
        was_user_in_server: bool,
        dm_attempted: bool,
        dm_succeeded: bool
    ) -> None:
        """Logs a user mute update in the database."""
        await self.add_case(
            case_type_id = 4,
            user_id = user_id,
            mod_id = mod_id,
            flags = self.make_flag(through_bot = through_bot, was_user_in_server = was_user_in_server, dm_attempted = dm_attempted, dm_succeeded = dm_succeeded),
            timestamp = timestamp,
            timestamp_expire = timestamp_expire,
            source_link = source_link,
            text = reason
        )
    
    
    async def add_unmute(self, *,
        user_id: int,
        mod_id: int,
        timestamp: float = current_timestamp(),
        source_link: str = None,
        reason: str = None,
        through_bot: bool,
        was_user_in_server: bool,
        dm_attempted: bool,
        dm_succeeded: bool
    ) -> None:
        """Logs a user unmute in the database."""
        await self.add_case(
            case_type_id = 5,
            user_id = user_id,
            mod_id = mod_id,
            flags = self.make_flag(through_bot = through_bot, was_user_in_server = was_user_in_server, dm_attempted = dm_attempted, dm_succeeded = dm_succeeded),
            timestamp = timestamp,
            source_link = source_link,
            text = reason
        )
    
    
    async def add_kick(self, *,
        user_id: int,
        mod_id: int,
        timestamp: float = current_timestamp(),
        source_link: str = None,
        reason: str = None,
        through_bot: bool,
        was_user_in_server: bool,
        dm_attempted: bool,
        dm_succeeded: bool
    ) -> None:
        """Logs a user kick in the database."""
        await self.add_case(
            case_type_id = 6,
            user_id = user_id,
            mod_id = mod_id,
            flags = self.make_flag(through_bot = through_bot, was_user_in_server = was_user_in_server, dm_attempted = dm_attempted, dm_succeeded = dm_succeeded),
            timestamp = timestamp,
            source_link = source_link,
            text = reason
        )
    
    
    async def add_ban(self, *,
        user_id: int,
        mod_id: int,
        timestamp: float = current_timestamp(),
        duration: int = None,
        source_link: str = None,
        reason: str = None,
        through_bot: bool,
        was_user_in_server: bool,
        dm_attempted: bool,
        dm_succeeded: bool
    ) -> None:
        """Logs a user ban in the database."""
        await self.add_case(
            case_type_id = 7,
            user_id = user_id,
            mod_id = mod_id,
            flags = self.make_flag(through_bot = through_bot, was_user_in_server = was_user_in_server, dm_attempted = dm_attempted, dm_succeeded = dm_succeeded),
            timestamp = timestamp,
            timestamp_expire = None if duration is None else timestamp+duration,
            source_link = source_link,
            text = reason
        )
    
    
    async def add_ban_update(self, *,
        user_id: int,
        mod_id: int,
        timestamp: float = current_timestamp(),
        timestamp_expire: float = None,
        source_link: str = None,
        reason: str = None,
        through_bot: bool,
        was_user_in_server: bool,
        dm_attempted: bool,
        dm_succeeded: bool
    ) -> None:
        """Logs a user ban update in the database."""
        await self.add_case(
            case_type_id = 8,
            user_id = user_id,
            mod_id = mod_id,
            flags = self.make_flag(through_bot = through_bot, was_user_in_server = was_user_in_server, dm_attempted = dm_attempted, dm_succeeded = dm_succeeded),
            timestamp = timestamp,
            timestamp_expire = timestamp_expire,
            source_link = source_link,
            text = reason
        )
    
    
    async def add_unban(self, *,
        user_id: int,
        mod_id: int,
        timestamp: float = current_timestamp(),
        source_link: str = None,
        reason: str = None,
        through_bot: bool,
        was_user_in_server: bool,
        dm_attempted: bool,
        dm_succeeded: bool
    ) -> None:
        """Logs a user unban in the database."""
        await self.add_case(
            case_type_id = 9,
            user_id = user_id,
            mod_id = mod_id,
            flags = self.make_flag(through_bot = through_bot, was_user_in_server = was_user_in_server, dm_attempted = dm_attempted, dm_succeeded = dm_succeeded),
            timestamp = timestamp,
            source_link = source_link,
            text = reason
        )
    
    
    ######
    
    
    def _row_to_case_object(self, row):
        if not row:
            return row
        row = dict(row)
        UNSELECTED = self.bot.utils.db.UNSELECTED
        return cls.Case(
            case_id = row.get("case_id", UNSELECTED),
            case_type_id = row.get("type_id", UNSELECTED),
            user_id = row.get("user_id", UNSELECTED),
            mod_id = row.get("mod_id", UNSELECTED),
            flags = row.get("flags", UNSELECTED),
            timestamp = row.get("timestamp", UNSELECTED),
            timestamp_expire = row.get("timestamp_expire", UNSELECTED),
            source_link = row.get("source_link", UNSELECTED),
            text = row.get("text", UNSELECTED)
        )
    
    def _rows_to_case_objects(self, rows):
        return [self._row_to_case_object(row) for row in rows]
    
    
    async def get_case(self, case_id: int):
        """Returns a case with the given case_id as a Case object."""
        return self._row_to_case_object(
            await self.bot.utils.db.fetch_row("SELECT * FROM \"cases\" WHERE \"case_id\"=?", (case_id,))
        )
    
    async def get_user_cases(self, user_id: int, limit: int = None, sort_by_newest: bool = True):
        """Returns all cases for a given user as Case objects."""
        return self._rows_to_case_objects(
            await self.bot.utils.db.fetch_rows(
                f"SELECT * FROM \"cases\" WHERE \"user_id\"=? ORDER BY \"case_id\" {'DESC' if sort_by_newest else 'ASC'}{f' LIMIT {limit}' if limit else ''}",
                (user_id,)
            )
        )
    
    
    async def make_case_embed(self, case) -> discord.Embed:
        """Creates and returns a full embed for displaying the given case object."""
        
        user = await self.bot.utils.resolve.user_or_member(case.user_id, self.bot.main_server_id)
        moderator = await self.bot.utils.resolve.user_or_member(case.mod_id, self.bot.main_server_id)
        timestamp = int(case.timestamp) if case.timestamp else None
        
        embed = discord.Embed(
            title = case.case_type.upper(),
            color = case.case_type_color,
            description = f"Created on <t:{timestamp}:f> (<t:{timestamp}:R>) [`{timestamp}`]" if timestamp else None
        )
        embed.set_author(
            name = f"Case #{case.case_id if isinstance(case.case_id, int) else '<?>'}",
            url = case.source_link if case.source_link else None,
            icon_url = moderator.display_avatar.url if moderator else None
        )
        
        if user:
            embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(
            name="User:",
            value=informative_user_mention(user, case.user_id),
            inline=True
        )
        embed.add_field(
            name="Moderator:",
            value=informative_user_mention(moderator, case.mod_id),
            inline=True
        )
        
        embed.add_field(name="Reason:", value=case.reason if case.reason else "<None given>", inline=False)
        
        if case.flags:
            decide_emoji = lambda b: "✅" if b else "❌"
            flagtext = f"""{
                decide_emoji(case.through_bot)} Issued through the bot
{               decide_emoji(case.was_user_in_server)} User was in the server
{               decide_emoji(case.dm_attempted)} Attempted to DM the user
{               decide_emoji(case.dm_succeeded)} User received the DM"""
            embed.add_field(
                name = "Flags:",
                value = flagtext,
                inline = True
            )
        
        if case.duration:
            timestamp_end = int(case.timestamp_expire)
            embed.add_field(
                name = "Duration:",
                value = f"{stringify_duration(case.duration)}\nUntil <t:{timestamp_end}:f>\n(<t:{timestamp_end}:R>)\n[`{timestamp_end}`]",
                inline = True
            )
        elif case.case_type_id in [3,4,7,8]:
            embed.add_field(
                name = "Duration:",
                value = "<Indefinitely>",
                inline = True
            )
        
        #embed.set_footer(text="")
        
        return embed
