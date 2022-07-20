from discord import ActivityType, Intents
import logging

from src.botloader import BotLoader, path_from_current_dir



TOKEN = "PUT_YOUR_TOKEN_HERE!"

botloader = BotLoader(
    prefix = "!",
    status_type = ActivityType.listening,
    status_message = "! prefix",
    intents = Intents.all(),
    data_dir = path_from_current_dir(__file__, "testbot_data"), 
    main_server_id = 922667089037258792, #my testing server
    owner_id = 263862604915539969, #Tomlacko | will query Application owners if set to None
    use_builtin_help_command = True
)


#all cogs that will be available to this bot over its lifetime
botloader.register_extensions({
    #"jishaku": None,
    #"testcog": {"somevalue": 1337},

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
    }
})

#all cogs that will be loaded in this bot on startup
botloader.add_extensions_to_startup([
    #"testcog",
    "core.permissions",
    "core.database",
])


#optional: add log handlers
botloader.add_console_log_handler(logging.INFO)
botloader.add_file_log_handler(logging.DEBUG, botloader.from_data_dir("botlog.log"), False)


#try load extensions and start the bot:
botloader.try_start_bot(TOKEN)
