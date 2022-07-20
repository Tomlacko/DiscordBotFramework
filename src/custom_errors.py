from discord.ext import commands

class ExtensionNotRegistered(commands.errors.ExtensionError):
    """
    Thrown when attempting to load an extension that has not been registered beforehand.
    """
    def __init__(self, name: str) -> None:
        msg = f"Cannot load extension {name!r} - extension not registered."
        super().__init__(msg, name=name)


class ExtensionDependencyNotLoaded(commands.errors.ExtensionError):
    """
    Thrown when attempting to load an extension that depends on another extension which has not yet been loaded.
    """
    def __init__(self, name: str, dependency: str) -> None:
        msg = f"Cannot load extension {name!r} - extension {dependency!r} is required to be loaded beforehand!"
        super().__init__(msg, name=name)