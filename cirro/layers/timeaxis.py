"""The time dimension of a WMS layer: which `TIME` values it accepts.

GeoServer advertises them as ISO 8601 text, a list of instants, of
`start/end/period` intervals, or both. `TIME` must be one of these
exact values (docs/data-sources.md, section 11), so the app picks the
nearest one."""
import bisect
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

_DURATION = re.compile(
    r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?)?$")
# More steps are never offered on the time bar.
MAX_STEPS = 400


def parse_time(text):
    """ISO 8601 UTC instant → aware datetime."""
    text = text.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def format_time(time_):
    """The form GeoServer advertises: 2026-11-07T12:00:00.000Z."""
    return time_.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse_duration(text):
    """`PT5M`, `PT1H`, `P1D` … → timedelta. Months and years have no
    fixed length and are rejected (ValueError)."""
    match = _DURATION.match(text.strip())
    if not match or text.strip() in ("P", "PT"):
        raise ValueError(f"unsupported duration {text!r}")
    parts = {key: int(value) for key, value in match.groupdict().items() if value}
    duration = timedelta(**parts)
    if not duration:
        raise ValueError(f"zero duration {text!r}")
    return duration


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime
    step: timedelta

    def times(self, first, last):
        """The interval's instants within [first, last]."""
        if last < self.start or first > self.end:
            return []
        skip = max(0, -(-(first - self.start) // self.step))
        time_ = self.start + skip * self.step
        out = []
        while time_ <= min(last, self.end):
            out.append(time_)
            time_ += self.step
        return out


@dataclass(frozen=True)
class TimeAxis:
    instants: tuple = ()
    intervals: tuple = ()

    @classmethod
    def parse(cls, text):
        instants, intervals = [], []
        for part in (p.strip() for p in text.split(",")):
            if not part:
                continue
            if "/" in part:
                start, end, step = part.split("/")
                if not step:
                    # "start/end/" without a period: GeoServer means
                    # "continuous"; the period is unknown.
                    raise ValueError(f"interval without period {part!r}")
                intervals.append(Interval(parse_time(start), parse_time(end),
                                          parse_duration(step)))
            else:
                instants.append(parse_time(part))
        return cls(tuple(sorted(instants)), tuple(intervals))

    @property
    def step(self):
        """Typical distance between two instants, for labels and marks."""
        if self.intervals:
            return min(i.step for i in self.intervals)
        if len(self.instants) > 1:
            gaps = [b - a for a, b in zip(self.instants, self.instants[1:])]
            return sorted(gaps)[len(gaps) // 2]
        return timedelta(hours=1)

    @property
    def last(self):
        ends = [i.end for i in self.intervals] + list(self.instants[-1:])
        return max(ends) if ends else None

    def times(self, first, last):
        """All instants within [first, last], sorted, at most MAX_STEPS
        (the ones closest to `first` are kept)."""
        found = {t for t in self.instants if first <= t <= last}
        for interval in self.intervals:
            found.update(interval.times(first, last))
        return sorted(found)[:MAX_STEPS]

    def nearest(self, time_, tolerance=None):
        """The valid instant closest to `time_`, or None if there is none
        within `tolerance`."""
        candidates = list(self.instants)
        for interval in self.intervals:
            if time_ <= interval.start:
                candidates.append(interval.start)
            elif time_ >= interval.end:
                candidates.append(interval.end)
            else:
                n = (time_ - interval.start) // interval.step
                below = interval.start + n * interval.step
                candidates += [below, min(below + interval.step, interval.end)]
        if not candidates:
            return None
        best = min(candidates, key=lambda t: abs(t - time_))
        if tolerance is not None and abs(best - time_) > tolerance:
            return None
        return best


def latest_at(times, now):
    """Index of the last time not after `now` (0 if all are later)."""
    return max(0, bisect.bisect_right(times, now) - 1)


def usable(steps, reference_time, lead, every=None):
    """Steps a forecast sum has data for: `lead` after the model run
    `reference_time` (ISO text), then every `every`
    (docs/data-sources.md, section 11)."""
    if not reference_time or (not lead and not every):
        return steps
    run = parse_time(reference_time)
    out = []
    for time_ in steps:
        since = time_ - run
        if since < lead or (every and since % every):
            continue
        out.append(time_)
    return out
