import sys
import os


_last_written_stream = None

class InterceptedStream:
    def __init__(self, original_stream, hook, to_flush=[]):
        self.original_stream = original_stream
        self.hook = hook
        self.to_flush = to_flush

    def write(self, msg: str):
        global _last_written_stream
        altered_msg = self.hook(msg)
        if altered_msg is not None:
            if _last_written_stream is not None and _last_written_stream != self.original_stream:
                for stream in self.to_flush:
                    stream.flush()
            _last_written_stream = self.original_stream
            return self.original_stream.write(altered_msg)
    
    def __getattr__(self, attr):
        return getattr(self.original_stream, attr)


_current_print_separation = 1


def is_printing_overridden() -> bool:
    return isinstance(sys.stdout, InterceptedStream)


def enable_printing_override() -> bool:
    if is_printing_overridden():
        return False
    
    def print_hook(msg: str):
        global _current_print_separation

        if len(msg) > 0:
            new_sep = 0
            for char in reversed(msg):
                if char == "\n":
                    new_sep += 1
                elif not char.isspace() or new_sep == 0:
                    _current_print_separation = 0
                    break
            _current_print_separation += new_sep

        return msg

    
    if os.fstat(0) == os.fstat(1):
        stdout = sys.stdout
        stderr = sys.stderr
        sys.stdout = InterceptedStream(sys.stdout, print_hook, [stderr])
        sys.stderr = InterceptedStream(sys.stderr, print_hook, [stdout])
    else:
        sys.stdout = InterceptedStream(sys.stdout, print_hook)
    
    return True


def disable_printing_override() -> bool:
    success = False
    if isinstance(sys.stdout, InterceptedStream):
        sys.stdout = sys.stdout.original_stream
        success = True
    if isinstance(sys.stderr, InterceptedStream):
        sys.stderr = sys.stderr.original_stream
        success = True
    return success



def new_empty_line_if_not_already(empty_line_amount: int = 1) -> None:
    global _current_print_separation

    if not is_printing_overridden():
        raise RuntimeError("Printing override has not been enabled!")

    empty_line_amount += 1
    
    while _current_print_separation < empty_line_amount:
        last_sep = _current_print_separation
        print(end="\n")
        if _current_print_separation != last_sep+1:
            raise RuntimeError("Printing override is not working correctly! Exception raised to prevent an infinite loop.")
