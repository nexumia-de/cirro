"""Rain rate (mm/h) → RGBA colour scale for the radar overlay and legend."""
import numpy as np

from cirro.radar import NODATA

# Lower bound in mm/h and colour of each class; below the first bound the
# overlay is transparent. Blue → green → yellow → red → magenta, the usual
# order of radar maps, with steps a reader can tell apart on a phone.
SCALE = [
    (0.1, (0x9b, 0xd5, 0xf5)),
    (0.5, (0x4a, 0x9e, 0xe8)),
    (1.0, (0x1c, 0x5f, 0xd1)),
    (2.0, (0x2e, 0xb8, 0x4f)),
    (5.0, (0xf2, 0xd0, 0x22)),
    (10.0, (0xf2, 0x8a, 0x1c)),
    (20.0, (0xe0, 0x1b, 0x24)),
    (50.0, (0xb5, 0x1c, 0xc9)),
]
ALPHA = 0xb8


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
