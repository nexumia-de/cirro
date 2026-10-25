import re
import xml.etree.ElementTree as ET
from pathlib import Path

import wetterblick

ROOT = Path(__file__).resolve().parent.parent
APP_ID = "de.nexumia.Wetterblick"


def test_version_matches_meson_and_metainfo():
    meson = (ROOT / "meson.build").read_text()
    assert re.search(r"version: '([^']+)'", meson).group(1) == wetterblick.VERSION
    metainfo = ET.parse(ROOT / "data" / f"{APP_ID}.metainfo.xml")
    latest = metainfo.find("releases/release").get("version")
    assert latest == wetterblick.VERSION


def test_desktop_file_is_shown_in_phosh_mobile_mode():
    desktop = (ROOT / "data" / f"{APP_ID}.desktop").read_text()
    # Phosh matches the substring "mobile;" case-insensitively.
    assert re.search(r"^X-Purism-FormFactor=.*mobile;", desktop,
                     re.IGNORECASE | re.MULTILINE)


def test_metainfo_declares_phone_support():
    root = ET.parse(ROOT / "data" / f"{APP_ID}.metainfo.xml").getroot()
    length = root.find("recommends/display_length")
    assert length.get("compare") == "ge" and length.text == "360"
    assert root.find("supports/control").text == "touch"


def test_user_agent():
    assert wetterblick.USER_AGENT == (
        f"Wetterblick/{wetterblick.VERSION} (+https://github.com/suitably/wetterblick)")
