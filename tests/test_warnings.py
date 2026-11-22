"""CAP warnings per place, with DWD's recorded status of 2026-11-22
04:38 UTC (tests/data/cap, docs/data-sources.md section 4)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cirro.warnings import cap, text

ZIP = (
    Path(__file__).parent
    / "data"
    / "cap"
    / "Z_CAP_C_EDZW_LATEST_PVW_STATUS_PREMIUMDWD_COMMUNEUNION_EN.zip"
)
NOW = datetime(2026, 11, 22, 4, 45, tzinfo=UTC)


@pytest.fixture(scope="module")
def warnings():
    return cap.parse_zip(ZIP.read_bytes())


def test_parses_every_warning(warnings):
    assert len(warnings) == 50
    assert {w.severity for w in warnings} == {"Minor"}
    assert {w.event for w in warnings} == {"icy surfaces", "fog", "frost", "near gale"}
    assert all(w.level == 1 and w.level_name == "Minor" for w in warnings)


def test_sea_warnings_have_no_polygon(warnings):
    sea = [w for w in warnings if w.event == "near gale"]
    assert len(sea) == 2
    assert all(not w.areas and w.expires is None for w in sea)
    assert sea[0].names in (("Östlich Fehmarn bis Rügen",), ("Östlich Rügen",))


def test_fields_and_times(warnings):
    warning = next(
        w
        for w in warnings
        if w.identifier.startswith("2.49.0.0.276.0.DWD.PVW.1795260780000.f33da1d1")
    )
    assert warning.event == "frost"
    assert warning.onset == datetime(2026, 11, 21, 20, 0, tzinfo=UTC)
    assert warning.expires == datetime(2026, 11, 22, 8, 0, tzinfo=UTC)
    assert warning.colour == (255, 235, 59)
    assert warning.headline == "Official WARNING of FROST"
    assert warning.description
    assert any(area.holes for area in warning.areas)


def test_point_in_area_and_hole():
    square = ((0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0), (0.0, 0.0))
    hole = ((4.0, 4.0), (4.0, 6.0), (6.0, 6.0), (6.0, 4.0), (4.0, 4.0))
    area = cap.Area(square, (hole,))
    assert area.contains(2, 2)
    assert not area.contains(5, 5)
    assert not area.contains(11, 5)


def test_warnings_at_a_place(warnings):
    # Freiburg: fog, frost and icy surfaces; Berlin Mitte: none.
    found = cap.at_point(warnings, 47.99, 7.85, NOW)
    assert cap.short(found) == "3 warnings: Fog, frost, icy surfaces"
    assert cap.at_point(warnings, 52.52, 13.40, NOW) == []


def test_expired_warnings_are_left_out(warnings):
    later = NOW + timedelta(days=2)
    assert cap.at_point(warnings, 47.99, 7.85, later) == []


def test_most_severe_first():
    def warning(severity, onset):
        return cap.Warning(
            "x",
            "Alert",
            severity.lower(),
            severity,
            "",
            "",
            "",
            "",
            "",
            "",
            onset,
            None,
            None,
            (cap.Area(((0, 0), (0, 1), (1, 1), (1, 0))),),
        )

    early, late = NOW, NOW + timedelta(hours=1)
    found = cap.at_point(
        [
            warning("Minor", early),
            warning("Severe", late),
            warning("Minor", late - timedelta(hours=2)),
        ],
        0.5,
        0.5,
        NOW,
    )
    assert [w.severity for w in found] == ["Severe", "Minor", "Minor"]
    assert found[1].onset < found[2].onset


def test_cancel_and_test_messages_are_skipped():
    alert = (
        b'<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">'
        b"<status>%s</status><msgType>%s</msgType><info/></alert>"
    )
    assert cap.parse_alert(alert % (b"Test", b"Alert")) is None
    assert cap.parse_alert(alert % (b"Actual", b"Cancel")) is None


def test_short_line():
    assert cap.short([]) == ""


def test_texts(warnings):
    warning = next(w for w in warnings if w.expires and w.onset)
    assert text.level(warning) == "Level 1 of 4 · Minor"
    assert text.period(warning, warning.onset).startswith("Now until ")
    before = warning.onset - timedelta(hours=1)
    assert text.period(warning, before).startswith("From ")
    sea = next(w for w in warnings if w.expires is None)
    assert text.period(sea, NOW) == "Now, until further notice"


def test_heights():
    assert text.heights(cap.Area((), (), 0.0, None)) == ""
    assert text.heights(cap.Area((), (), 1000.0, None)) == "Above 1000 m"
    assert text.heights(cap.Area((), (), 0.0, 800.0)) == "Below 800 m"


def test_all_heights_parse_as_no_limit(warnings):
    area = next(w for w in warnings if w.areas).areas[0]
    assert area.altitude_m == 0.0 and area.ceiling_m is None


def test_disk_cache_round_trip(tmp_path):
    from cirro.warnings.source import DiskCache

    cache = DiskCache(tmp_path / "w")
    assert cache.load() == (None, None)
    cache.save(b"zip", '"abc"')
    assert cache.load() == (b"zip", '"abc"')
