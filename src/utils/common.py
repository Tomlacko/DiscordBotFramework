import disnake

import traceback


class DummyObject:
    pass


def plural_suffix(val: int) -> str:
    if val!=1:
        return "s"
    return ""

def get_exception_traceback(ex: Exception) -> str:
    return "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))


#prevent asyncio tasks from getting garbage collected
__tasks_set = set()
def prevent_task_garbage_collection(task):
    __tasks_set.add(task)
    task.add_done_callback(__tasks_set.discard)