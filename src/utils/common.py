import disnake

import traceback


class DummyObject:
    pass

    

def get_exception_traceback(ex: Exception) -> str:
    return "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))


#https://stackoverflow.com/questions/2020014/get-fully-qualified-class-name-of-an-object-in-python/13653312#13653312
def get_full_class_name(obj) -> str:
    module = obj.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return obj.__class__.__name__
    return module + '.' + obj.__class__.__name__


def get_exception_string(err) -> str:
    return f"{get_full_class_name(err)}: {err}"


#prevent asyncio tasks from getting garbage collected
__tasks_set = set()
def prevent_task_garbage_collection(task):
    __tasks_set.add(task)
    task.add_done_callback(__tasks_set.discard)