# DiscordBotFramework
A custom discord.py 2.0 based bot framework that makes developing and launching bots easier.

## Setup
Every bot you wish to run under this framework should be defined in its own launch script file. The file testbot.py is provided as an example to show how such a launch script should look like. In it, you first configure some basic but necessary things about your bot. Then, if you wish to use any extensions (cogs), you first need to register them into the bot with a cog-specific config, the format for which can be found inside every cog. If a cog doesn't need any extra config, any value (preferably None) can be put here. Every cog that you want to have available to the bot during its lifetime needs to be registered here, even if you don't intend to load it on startup. After that, you can define which cogs should be loaded on startup. The order of cogs in this list matters, because cogs can depend on other cogs in this framework. Lastly, you can add logging to your bot, which discord.py uses to show errors and info. The functions provided in this framework allow you to attach as many different log handlers as you want, including none at all (highly recommended to use one though). Then finally all that's needed is for you to call the function to run the configured bot. To run a bot, simply run its launch script file in python.

## Features
- Lots more control over the bot's lifetime, extension loading, commands, etc...
- All bot boilerplate already done for you, you can focus on making cogs and commands.
- Application command auto-syncing to Discord done in a smart way. You no longer need to care about when or how to sync. (This is configurable.)
- Custom app_commands command tree that contains a plethora of functions for more control over what commands get synced and how exactly it's done. Also includes a custom appcommand cache (similar to other discord.py caches like for messages or members) that lets you access your server-side commands without having to fetch them.
- Smarter cogs enriched with all kinds of features, including custom decorators. You can mark a function to be ran when the bot and cog are both ready, you can specify dependencies that a cog depends on and will not load without, you can get a list of commands of a specific type, etc... You can also pass your own config defined per-cog per-bot while reusing the same codebase.
- Improved hybrid commands, which now only run in the same contexts in which the belonging app command would run, and other decorators that do not work on them out of the box have been made more compatible.
- Decorators for marking an app command to be added either to the bot's main guild or all of its guilds, evaluated on runtime, which wasn't possible before.
- Custom bot events, including on_full_load and on_console_input, the latter of which is especially useful for reading the console input during async runtime.
- Lots of utilities ready for use, including a database cog (using aiosqlite) with many easy to use functions abstracting everything away from you.
- Lots more to come in the future as I work on making bots in this framework!

## Dependencies
### The bot framework relies on:
- Python 3.8+
- discord.py 2.0 (pip install git+https://github.com/Rapptz/discord.py)
  (Currently used commit: https://github.com/Rapptz/discord.py/commit/87c9c95bb87397b201e185b6e93b46dbc557d6e4)
### Optional, only necessary for using some cogs:
- aiosqlite (for the database cog)
- python-dateutil (for time_helper utils)
- jishaku (always good to have)

# Credit
- Created by Tomlacko#2976
