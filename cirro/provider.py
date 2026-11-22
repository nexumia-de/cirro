"""Which radar covers a place: DWD's RV composite, or DMI's for Denmark
north of RV's coverage (issue #11, docs/decisions/dmi-radar.md: DWD wins
where both cover)."""

# Northern edge of RV's coverage, from the recorded RV composite
# (tests/data/composite_rv_20261024_2110_000-hd5): (longitude, latitude).
RV_NORTH = (
    (7.5, 54.84), (8.0, 54.70), (8.5, 55.00), (9.0, 55.22), (9.5, 55.32),
    (10.0, 55.34), (10.5, 55.32), (11.0, 55.38), (11.5, 55.48), (12.0, 55.52),
    (12.5, 55.50), (13.0, 55.40), (13.5, 55.24), (14.0, 54.94), (14.5, 53.94),
    (15.0, 53.82), (15.5, 53.58),
)  # fmt: skip
# Denmark with Bornholm, inside DMI's composite.
DENMARK = (54.4, 7.5, 58.0, 15.5)  # south, west, north, east


def rv_north(longitude):
    """Interpolated northern edge of RV's coverage at a longitude."""
    points = RV_NORTH
    if longitude <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        if longitude <= x1:
            return y0 + (y1 - y0) * (longitude - x0) / (x1 - x0)
    return points[-1][1]


def for_point(latitude, longitude):
    """`dmi` in Denmark outside RV's coverage, else `dwd`."""
    south, west, north, east = DENMARK
    inside = south <= latitude <= north and west <= longitude <= east
    return "dmi" if inside and latitude > rv_north(longitude) else "dwd"
