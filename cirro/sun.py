"""Sunrise and sunset at a place, computed locally (issue #54).

NOAA's solar position equations (General Solar Position, Spencer's
series), accurate to about a minute between the polar circles; no
download. Sunrise and sunset are when the sun's centre is 0.833° below
the horizon (refraction and the sun's radius)."""
import math
from datetime import datetime, timedelta, timezone

ZENITH = math.radians(90.833)


def _equation_and_declination(day):
    """(equation of time in minutes, declination in radians) on day of
    the year `day` at noon."""
    gamma = 2 * math.pi / 365 * (day - 1)
    equation = 229.18 * (0.000075 + 0.001868 * math.cos(gamma)
                         - 0.032077 * math.sin(gamma)
                         - 0.014615 * math.cos(2 * gamma)
                         - 0.040849 * math.sin(2 * gamma))
    declination = (0.006918 - 0.399912 * math.cos(gamma)
                   + 0.070257 * math.sin(gamma)
                   - 0.006758 * math.cos(2 * gamma)
                   + 0.000907 * math.sin(2 * gamma)
                   - 0.002697 * math.cos(3 * gamma)
                   + 0.00148 * math.sin(3 * gamma))
    return equation, declination


def sun_times(latitude, longitude, day=None):
    """(sunrise, sunset) as UTC datetimes on `day` (a date, default today
    in UTC); ("day", None) in polar day, ("night", None) in polar night."""
    day = day or datetime.now(timezone.utc).date()
    equation, declination = _equation_and_declination(day.timetuple().tm_yday)
    phi = math.radians(latitude)
    cos_h = (math.cos(ZENITH) / (math.cos(phi) * math.cos(declination))
             - math.tan(phi) * math.tan(declination))
    if cos_h < -1:
        return "day", None
    if cos_h > 1:
        return "night", None
    hour_angle = math.degrees(math.acos(cos_h))
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    rise = 720 - 4 * (longitude + hour_angle) - equation
    set_ = 720 - 4 * (longitude - hour_angle) - equation
    return (midnight + timedelta(minutes=rise),
            midnight + timedelta(minutes=set_))

