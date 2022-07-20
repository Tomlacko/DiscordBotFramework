import datetime
from time import time
from dateutil.relativedelta import relativedelta




# DISCORD_EPOCH = 1420070400 #unix timestamp in seconds, coresponding to 2015/1/1

# def snowflake_to_timestamp(snowflake: int) -> float:
#     return (snowflake >> 22)/1000 + DISCORD_EPOCH

# def snowflake_to_datetime(snowflake: int) -> datetime.datetime:
#     return datetime.datetime.fromtimestamp(snowflake_to_timestamp(snowflake), tz=datetime.timezone.utc)


def current_timestamp() -> float:
    return time()

def current_datetime() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

def timestamp_to_datetime(timestamp: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)

#datetime_to_timestamp = datetime.timestamp()

def get_time_passed(past_date, initial_date = None) -> float:
    """Returns the amount of seconds passed since past_date."""
    if isinstance(past_date, datetime.datetime):
        if initial_date is None:
            initial_date = current_datetime()
        elif not isinstance(initial_date, datetime.datetime):
            initial_date = timestamp_to_datetime(initial_date)
        return (initial_date-past_date).total_seconds()
    if initial_date is None:
        initial_date = current_timestamp()
    elif isinstance(initial_date, datetime.datetime):
        initial_date = initial_date.timestamp()
    return initial_date-past_date

def get_time_remaining(future_date, initial_date = None) -> float:
    """Returns the amount of seconds remaining until future_date."""
    return -get_time_passed(future_date, initial_date=initial_date)


def delta_to_seconds(*, initial_date = None, backwards: bool = False, delta: datetime.timedelta = None, years=0, months=0, weeks=0, days=0, hours=0, minutes=0, seconds=0) -> float:
    """Sums time delta into total seconds. If months or years are needed, calendar awareness is needed, for which you can supply the initial date (defaults to current time)."""
    if delta is not None:
        return delta.total_seconds()
    
    if years == 0 and months == 0:
        return seconds + 60*(minutes + 60*(hours + 24*(days + 7*weeks)))
    
    if initial_date is None:
        initial_date = current_datetime()
    rd = relativedelta(years=years, months=months, weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)
    if backwards:
        return (initial_date - (initial_date - rd)).total_seconds()
    return ((initial_date + rd) - initial_date).total_seconds()


def time_moved_by(d = None, *, backwards: bool = False, delta: datetime.timedelta = None, years=0, months=0, weeks=0, days=0, hours=0, minutes=0, seconds=0):
    """Moves a timestamp/datetime by the given amount. Uses current time if no argument is provided."""

    if d is None:
        d = current_datetime()

    #optimization for the trivial cases
    if years == 0 and months == 0:
        if isinstance(d, datetime.datetime):
            if delta is None:
                delta = datetime.timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)
            if backwards:
                return d - delta
            return d + delta
        else:
            delta = delta_to_seconds(delta=delta, weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)
            if backwards:
                return d - delta
            return d + delta
    
    #non-trivial case (needs calendar awareness, doesn't support basic timedelta)
    was_timestamp = False
    if not isinstance(d, datetime.datetime):
        was_timestamp = True
        d = timestamp_to_datetime(d)
    rd = relativedelta(years=years, months=months, weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)
    if backwards:
        new_date = d - rd
    else:
        new_date = d + rd
    if was_timestamp:
        new_date = new_date.timestamp()
    return new_date


def is_older_than(d, reference=None, *, delta: datetime.timedelta = None, years=0, months=0, weeks=0, days=0, hours=0, minutes=0, seconds=0) -> bool:
    """Checks if a given datetime/timestamp is older than the reference (=current time if unspecified) moved by the given delta backwards in time."""
    
    #optimization for the trivial case
    if years == 0 and months == 0:
        if isinstance(d, datetime.datetime):
            d = d.timestamp()
        if reference is None:
            reference = current_timestamp()
        elif isinstance(reference, datetime.datetime):
            reference = reference.timestamp()
        if delta is not None:
            delta_seconds = delta.total_seconds()
        else:
            delta_seconds = seconds + 60*(minutes + 60*(hours + 24*(days + 7*weeks)))
        return d < (reference - delta_seconds)
    
    #non-trivial case (needs calendar awareness, doesn't support basic timedelta)
    if not isinstance(d, datetime.datetime):
        d = timestamp_to_datetime(d)
    if reference is None:
        reference = current_datetime()
    elif not isinstance(reference, datetime.datetime):
        reference = timestamp_to_datetime(reference)
    return d < (reference - relativedelta(years=years, months=months, weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds))


def get_duration_segments(duration, *, round_seconds: bool = True):
    """Extract individual seconds, minutes, hours and days out of total seconds or timedelta object."""
    if isinstance(duration, datetime.timedelta):
        duration = duration.total_seconds()
    if round_seconds:
        duration = round(duration)
        s = int(duration % 60)
    else:
        s = duration % 60
    m = int((duration // 60) % 60)
    h = int((duration // 3600) % 24)
    d = int(duration // 86400)
    return (s, m, h, d)

def stringify_duration(duration, *, round_seconds: bool = True, ignore_zero: bool = True) -> str:
    """Convert a time duration into a string form like '0d 0h 0m 0s'"""
    (s, m, h, d) = get_duration_segments(duration, round_seconds=round_seconds)
    result = ""
    if not (ignore_zero and d==0):
        result+=f"{d}d "
    if not (ignore_zero and h==0):
        result+=f"{h}h "
    if not (ignore_zero and m==0):
        result+=f"{m}m "
    if not (ignore_zero and s==0):
        result+=f"{s}s"
    if result=="":
        return "0s"
    return result


def parse_duration_string_to_segments(val: str):
    """Parses a string representing a duration into individual time segments"""
    
    duration_segments = {
        "y": 0, #years
        "M": 0, #months
        "w": 0, #weeks
        "d": 0, #days
        "h": 0, #hours
        "m": 0, #minutes
        "s": 0  #seconds
    }

    digits = ""
    success = False
    used = set()
    for ch in val:
        if ch in "-+0123456789":
            digits += ch
            success = False
        elif ch in "yMwdhms": #end of segment
            if not digits or ch in used: #fail if multiple letters, or duplicate segment type
                success = False
                break
            #remember segment
            try:
                duration_segments[ch] = int(digits)
            except:
                success = False
                break
            used.add(ch)
            digits = ""
            success = True
        else: #invalid character
            success = False
            break
        first = False
    
    if not success:
        raise ValueError("Invalid time duration format!")
    
    return duration_segments

def parse_duration_string_to_date(val: str, initial_date = None, *, backwards: bool = False) -> datetime.datetime:
    duration_segments = parse_duration_string_to_segments(val)

    if initial_date is None:
        initial_date = current_datetime()
    elif not isinstance(initial_date, datetime.datetime):
        initial_date = timestamp_to_datetime(initial_date)
    
    if backwards:
        return initial_date - relativedelta(years=duration_segments["y"], months=duration_segments["M"], weeks=duration_segments["w"], days=duration_segments["d"], hours=duration_segments["h"], minutes=duration_segments["m"], seconds=duration_segments["s"])
    else:
        return initial_date + relativedelta(years=duration_segments["y"], months=duration_segments["M"], weeks=duration_segments["w"], days=duration_segments["d"], hours=duration_segments["h"], minutes=duration_segments["m"], seconds=duration_segments["s"])


def parse_duration_string_to_seconds(val: str, initial_date = None, *, backwards: bool = False) -> float:
    if initial_date is None:
        initial_date = current_datetime()
    elif not isinstance(initial_date, datetime.datetime):
        initial_date = timestamp_to_datetime(initial_date)
    
    moved_date = parse_duration_string_to_date(val, initial_date=initial_date, backwards=backwards)

    if backwards:
        return (initial_date - moved_date).total_seconds()
    else:
        return (moved_date - initial_date).total_seconds()