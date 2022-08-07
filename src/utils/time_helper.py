import datetime
import time
from dateutil.relativedelta import relativedelta



DISCORD_EPOCH_S = 1420070400 #unix timestamp in seconds, coresponding to 2015/1/1
DISCORD_EPOCH_MS = 1420070400000
DISCORD_EPOCH_DATETIME = datetime.datetime.fromtimestamp(DISCORD_EPOCH_S, tz=datetime.timezone.utc)


def snowflake_timestamp(snowflake: int) -> float:
    """Returns the snowflake time in seconds with floating-point precision."""
    return (snowflake >> 22)/1000 + DISCORD_EPOCH_S

def snowflake_timestamp_s(snowflake: int) -> int:
    """Returns the snowflake time in seconds as an integer."""
    return (snowflake >> 22)//1000 + DISCORD_EPOCH_S

def snowflake_timestamp_ms(snowflake: int) -> int:
    """Returns the snowflake time in milliseconds as an integer. This gives the most precise value."""
    return (snowflake >> 22) + DISCORD_EPOCH_MS

def snowflake_datetime(snowflake: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(snowflake_timestamp(snowflake), tz=datetime.timezone.utc)


def current_timestamp() -> float:
    """Returns the current time in seconds with floating-point precision."""
    return time.time()

def current_timestamp_s() -> int:
    """Returns the current time in seconds as an integer."""
    return time.time_ns()//1000000

def current_timestamp_ms() -> int:
    """Returns the current time in milliseconds as an integer."""
    return time.time_ns()//1000

def current_timestamp_ns() -> int:
    """Returns the current time in nanoseconds as an integer."""
    return time.time_ns()

def current_datetime() -> datetime.datetime:
    """Returns a timezone-aware datetime with the current time."""
    return datetime.datetime.now(datetime.timezone.utc)


def timestamp_to_datetime(timestamp: float) -> datetime.datetime:
    """Converts a numeric timestamp into a timezone-aware datetime object."""
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)

def datetime_to_timestamp(dt: datetime.datetime) -> float:
    """Converts a datetime object into a numeric timestamp."""
    return dt.timestamp()


def get_time_passed(past_date, reference_date = None) -> float:
    """Returns the amount of seconds passed since past_date."""
    if isinstance(past_date, datetime.datetime):
        if reference_date is None:
            reference_date = current_datetime()
        elif not isinstance(reference_date, datetime.datetime):
            reference_date = timestamp_to_datetime(reference_date)
        return (reference_date-past_date).total_seconds()
    if reference_date is None:
        reference_date = current_timestamp()
    elif isinstance(reference_date, datetime.datetime):
        reference_date = reference_date.timestamp()
    return reference_date-past_date

def get_time_remaining(future_date, reference_date = None) -> float:
    """Returns the amount of seconds remaining until future_date."""
    return -get_time_passed(future_date, reference_date=reference_date)


def delta_to_seconds(*, from_date = None, backwards: bool = False, delta: datetime.timedelta = None, years=0, months=0, weeks=0, days=0, hours=0, minutes=0, seconds=0) -> float:
    """Sums time delta into total seconds. If months or years are needed, calendar awareness is needed, for which you can supply the from_date (defaults to current time)."""
    if delta is not None:
        return delta.total_seconds()
    
    if years == 0 and months == 0:
        return seconds + 60*(minutes + 60*(hours + 24*(days + 7*weeks)))
    
    if from_date is None:
        from_date = current_datetime()
    rd = relativedelta(years=years, months=months, weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)
    if backwards:
        return (from_date - (from_date - rd)).total_seconds()
    return ((from_date + rd) - from_date).total_seconds()


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


def is_older_than(d, reference_date=None, *, delta: datetime.timedelta = None, years=0, months=0, weeks=0, days=0, hours=0, minutes=0, seconds=0) -> bool:
    """Checks if a given datetime/timestamp is older than the reference_date (=current time if unspecified) moved by the given delta backwards in time."""
    
    #optimization for the trivial case
    if years == 0 and months == 0:
        if isinstance(d, datetime.datetime):
            d = d.timestamp()
        if reference_date is None:
            reference_date = current_timestamp()
        elif isinstance(reference_date, datetime.datetime):
            reference_date = reference_date.timestamp()
        if delta is not None:
            delta_seconds = delta.total_seconds()
        else:
            delta_seconds = seconds + 60*(minutes + 60*(hours + 24*(days + 7*weeks)))
        return d < (reference_date - delta_seconds)
    
    #non-trivial case (needs calendar awareness, doesn't support basic timedelta)
    if not isinstance(d, datetime.datetime):
        d = timestamp_to_datetime(d)
    if reference_date is None:
        reference_date = current_datetime()
    elif not isinstance(reference_date, datetime.datetime):
        reference_date = timestamp_to_datetime(reference_date)
    return d < (reference_date - relativedelta(years=years, months=months, weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds))


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
    """Convert a time duration into a string form like '0d 0h 0m 0s'."""
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


def parse_duration_string_to_segments(val: str) -> dict:
    """Parses a string representing a duration into individual time segments."""
    
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


def parse_duration_string_to_date(val: str, reference_date = None, *, backwards: bool = False) -> datetime.datetime:
    """Parses a string representing a duration into a datetime object by applying it to a reference_date (=current time if unspecified)."""
    
    duration_segments = parse_duration_string_to_segments(val)

    if reference_date is None:
        reference_date = current_datetime()
    elif not isinstance(reference_date, datetime.datetime):
        reference_date = timestamp_to_datetime(reference_date)
    
    if backwards:
        return reference_date - relativedelta(years=duration_segments["y"], months=duration_segments["M"], weeks=duration_segments["w"], days=duration_segments["d"], hours=duration_segments["h"], minutes=duration_segments["m"], seconds=duration_segments["s"])
    else:
        return reference_date + relativedelta(years=duration_segments["y"], months=duration_segments["M"], weeks=duration_segments["w"], days=duration_segments["d"], hours=duration_segments["h"], minutes=duration_segments["m"], seconds=duration_segments["s"])


def parse_duration_string_to_seconds(val: str, reference_date = None, *, backwards: bool = False) -> float:
    """Parses a string representing a duration into the number of seconds by applying it to a reference_date (=current time if unspecified)."""
    
    if reference_date is None:
        reference_date = current_datetime()
    elif not isinstance(reference_date, datetime.datetime):
        reference_date = timestamp_to_datetime(reference_date)
    
    moved_date = parse_duration_string_to_date(val, reference_date=reference_date, backwards=backwards)

    if backwards:
        return (reference_date - moved_date).total_seconds()
    else:
        return (moved_date - reference_date).total_seconds()