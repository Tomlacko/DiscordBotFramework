# DiscordBotFramework
A custom discord.py 2.0 based bot framework that makes developing and launching bots easier.

# Setup
Every bot you wish to run under this framework should be defined in its own launch script file. The file testbot.py is provided as an example to show how such a launch script should look like. In it, you first configure some basic but necessary things about your bot. Then, if you wish to use any cogs (extensions), you first need to register them into the bot with a cog-specific config, the format for which can be found inside every cog. If a cog doesn't need any extra config, any value (preferably None) can be put here. Every cog that you want to have available to the bot during its lifetime needs to be registered here, even if you don't intend to load it on startup. After that, you can define which cogs should be loaded on startup. The order of cogs in this list matters, because cogs can depend on other cogs in this framework. Lastly, you can add logging to your bot, which discord.py uses to show errors and info. The functions provided in this framework allow you to attach as many different log handlers as you want, including none at all, although it's highly recommended. Then finally all that's needed is for you to call the function to run the bot with your configuration. To run a bot, simply run its launch script file.

## Dependencies
### The bot framework relies on:
- Python 3.8+
- discord.py 2.0 (pip install git+https://github.com/Rapptz/discord.py)
### Optional, only necessary for using some cogs:
- aiosqlite (for the database cog)
- python-dateutil (for time_helper utils)
- jishaku (always good to have)

# Credit
- Created by Tomlacko#2976
