"""Rain rate (mm/h) → RGBA colour scale for the radar overlay and legend."""

import numpy as np

from cirro.radar import NODATA

# Lower bound in mm/h and colour of each class; below the first bound the
# overlay is transparent. Blue → green → yellow → red → magenta, the usual
# order of radar maps, with steps a reader can tell apart on a phone.
SCALE = [
    (0.1, (0x9B, 0xD5, 0xF5)),
    (0.5, (0x4A, 0x9E, 0xE8)),
    (1.0, (0x1C, 0x5F, 0xD1)),
    (2.0, (0x2E, 0xB8, 0x4F)),
    (5.0, (0xF2, 0xD0, 0x22)),
    (10.0, (0xF2, 0x8A, 0x1C)),
    (20.0, (0xE0, 0x1B, 0x24)),
    (50.0, (0xB5, 0x1C, 0xC9)),
]
ALPHA = 0xB8


def rgba_lut(gain, offset, undetect):
    """Lookup table raw uint16 value → RGBA (65536 × 4 uint8)."""
    raw = np.arange(NODATA + 1, dtype=np.float64)
    rate = (raw * gain + offset) * 12
    lut = np.zeros((NODATA + 1, 4), dtype=np.uint8)
    for bound, rgb in SCALE:
        lut[rate >= bound] = (*rgb, ALPHA)
    lut[undetect] = 0
    lut[NODATA] = 0
    return lut


def colorize(frame, reprojection):
    """Frame → (height, width, 4) uint8 RGBA in the reprojection's grid."""
    lut = rgba_lut(frame.gain, frame.offset, frame.undetect)
    return lut[reprojection.apply(frame.raw, NODATA)]


def rgb(rate):
    """Colour (r, g, b) of the class a rain rate in mm/h falls into, None
    below the lowest class or without data (NaN)."""
    colour = None
    for bound, class_rgb in SCALE:
        if rate >= bound:
            colour = class_rgb
    return colour
