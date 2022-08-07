from discord import ActivityType, Intents
import logging

from src.bot_loader import BotLoader, path_from_current_dir



TOKEN = "OTIzMjg1NDUyNTQ5NjgxMjIz.GyKatw.P1KkPsBd1suA1rCFB9fYJ_V_a5-5R-Rl4SRYIs"

botloader = BotLoader(
    command_prefix = "%",
    status_type = ActivityType.listening,
    status_message = "% prefix",
    intents = Intents.all(),
    max_messages = 10000, #message cache size
    data_dir = path_from_current_dir(__file__, "testbot_data"), 
    main_server_id = 922667089037258792, #testing server
    owner_id = 263862604915539969, #Tomlacko | will query Application owners if set to None
    use_builtin_help_command = True,
    autosync_appcommands = True,
    remove_appcommands_on_unload = False,
    avoid_appcommand_deletions = False
)


#all cogs that will be available to this bot over its lifetime
botloader.register_extensions({
    "jishaku": None,
    
    "core.botmanager": None,

    "core.database": {
        "database_file": "botdb.db"
    },
    "core.permissions": {
        922667089037258792: {
            "role_levels": {
            },
            "user_levels": {
                263862604915539969: 10,
            }
        },
    },
    "moderation.cases": {},
    
    "testcog": None,
})

#all cogs that will be loaded in this bot on startup
botloader.add_extensions_to_startup([
    "jishaku",
    
    "core.botmanager",
    "core.permissions",
    "core.database",
    
    "moderation.cases",
    
    #"testcog",
])


#optional: add log handlers
botloader.add_console_log_handler(logging.INFO)
botloader.add_file_log_handler(logging.DEBUG, botloader.in_data_dir("botlog.log"), False)


#try load extensions and start the bot:
botloader.try_start_bot(TOKEN)
