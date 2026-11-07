"""Wind in words: Beaufort force, compass point and km/h, for the wind
arrows, the tap value and the wind at the selected place."""

_COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
# Upper limits of Beaufort 0 … 11 in m/s (WMO); above is 12.
_BEAUFORT = (0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7)


def compass(degrees):
    return _COMPASS[round(degrees / 22.5) % 16]


def beaufort(speed):
    """Beaufort force of a speed in m/s."""
    for force, limit in enumerate(_BEAUFORT):
        if speed < limit:
            return force
    return 12


def kmh(speed):
    return round(speed * 3.6)


def describe(speed, direction=None):
    """"4 Bft (25 km/h) from NNE"; "Calm" below 0.3 m/s."""
    force = beaufort(speed)
    if force == 0:
        return "Calm"
    text = f"{force} Bft ({kmh(speed)} km/h)"
    if direction is not None:
        text += f" from {compass(direction)}"
    return text
