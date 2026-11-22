"""Texts about a warning for the list and the detail page. No GTK."""
from datetime import datetime


def _clock(time_, now):
    local, today = time_.astimezone(), now.astimezone()
    if local.date() == today.date():
        return local.strftime("%H:%M")
    return local.strftime("%a %H:%M")


def period(warning, now):
    """"Now until 09:00", "From Sun 22:00 until Mon 09:00", "Until further notice"."""
    start = warning.onset
    if start is None or start <= now:
        if warning.expires is None:
            return "Now, until further notice"
        return f"Now until {_clock(warning.expires, now)}"
    if warning.expires is None:
        return f"From {_clock(start, now)}, until further notice"
    return f"From {_clock(start, now)} until {_clock(warning.expires, now)}"


def level(warning):
    """Severity in words, never only as a colour: "Level 1 of 4 · Minor"."""
    if not warning.level:
        return warning.severity
    return f"Level {warning.level} of 4 · {warning.level_name}"


def heights(area):
    """"Above 1000 m", "Below 800 m", or "" for all heights."""
    low = round(area.altitude_m / 100) * 100
    if area.ceiling_m is None:
        return f"Above {low:.0f} m" if low > 0 else ""
    high = round(area.ceiling_m / 100) * 100
    if low > 0:
        return f"Between {low:.0f} and {high:.0f} m"
    return f"Below {high:.0f} m"


def now():
    return datetime.now().astimezone()
