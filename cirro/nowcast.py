"""Point nowcast: the rain rate at one place over the radar timeline and
a sentence about it (docs/nowcast.md). No GTK, unit-tested with the
recorded frames in tests/data/demo."""
import math
from dataclasses import dataclass
from datetime import datetime

from cirro import radar
from cirro.colors import SCALE

# Rain from the colour scale's lowest class on (0.1 mm/h): what the map
# shows as rain is what the sentence calls rain.
RAIN = SCALE[0][0]
# Rain "stops" only when it stays dry this many frames (10 min) or until
# the end of the forecast, so one dry frame inside a shower is no stop.
DRY_FRAMES = 2
# Bar heights: logarithmic between these rates, so drizzle stays visible
# next to a downpour.
_LOW, _HIGH = 0.05, 50.0
MIN_HEIGHT = 0.1


@dataclass(frozen=True)
class Value:
    valid_time: datetime    # UTC, end of the 5-min interval
    minutes: int            # valid time relative to the analysis time
    forecast: bool
    rate: float             # mm/h, NaN outside the radar coverage


def series(entries, analysis_time, latitude, longitude, cache=None,
           cancelled=lambda: False, sample=radar.sample):
    """Rain rate at the point for every FrameStore entry, in their order.
    `cache` (a dict) keeps values per member and point between calls;
    returns None as soon as `cancelled()` is true."""
    values = []
    for entry in entries:
        if cancelled():
            return None
        key = (entry.name, latitude, longitude)
        rate = cache.get(key) if cache is not None else None
        if rate is None:
            rate = sample(entry.data, latitude, longitude)
            if cache is not None:
                cache[key] = rate
        minutes = round((entry.valid_time - analysis_time).total_seconds() / 60)
        values.append(Value(entry.valid_time, minutes, entry.forecast, rate))
    return values


def is_rain(rate):
    return rate >= RAIN     # False for NaN


def duration(minutes):
    """35 → "35 min", 60 → "1 h", 85 → "1 h 25 min"."""
    hours, rest = divmod(minutes, 60)
    if not hours:
        return f"{rest} min"
    return f"{hours} h {rest} min" if rest else f"{hours} h"


def _span(minutes):
    """Length of the forecast in words: "2 hours", "1 hour", "1 h 55 min"."""
    hours, rest = divmod(minutes, 60)
    if hours and not rest:
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    return duration(minutes)


def summary(values):
    """One sentence about rain from now on, or None without any data."""
    ahead = [v for v in values if v.minutes >= 0]
    if not ahead or math.isnan(ahead[0].rate):
        return None
    horizon = ahead[-1].minutes
    if is_rain(ahead[0].rate):
        for i, value in enumerate(ahead):
            dry = ahead[i:i + DRY_FRAMES]
            if not any(is_rain(v.rate) for v in dry) \
                    and (len(dry) == DRY_FRAMES or i + len(dry) == len(ahead)):
                return f"Rain stops in {duration(value.minutes)}"
        if horizon < 5:
            return "Raining now"
        return f"Rain for the next {_span(horizon)}"
    for value in ahead:
        if is_rain(value.rate):
            return f"Rain starts in {duration(value.minutes)}"
    if horizon < 5:
        return "No rain now"
    return f"No rain expected in the next {_span(horizon)}"


def bar_height(rate):
    """Height of a bar as a fraction of the chart, 0 for no rain."""
    if not is_rain(rate):
        return 0.0
    fraction = math.log(rate / _LOW) / math.log(_HIGH / _LOW)
    return min(max(fraction, MIN_HEIGHT), 1.0)
