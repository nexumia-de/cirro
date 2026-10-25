import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import cirro

ROOT = Path(__file__).resolve().parent.parent
APP_ID = "de.nexumia.Cirro"


def test_version_matches_meson_and_metainfo():
    meson = (ROOT / "meson.build").read_text()
    assert re.search(r"version: '([^']+)'", meson).group(1) == cirro.VERSION
    metainfo = ET.parse(ROOT / "data" / f"{APP_ID}.metainfo.xml")
    latest = metainfo.find("releases/release").get("version")
    assert latest == cirro.VERSION


def test_desktop_file_is_shown_in_phosh_mobile_mode():
    desktop = (ROOT / "data" / f"{APP_ID}.desktop").read_text()
    # Phosh matches the substring "mobile;" case-insensitively.
    assert re.search(r"^X-Purism-FormFactor=.*mobile;", desktop,
                     re.IGNORECASE | re.MULTILINE)


def test_metainfo_declares_phone_support():
    root = ET.parse(ROOT / "data" / f"{APP_ID}.metainfo.xml").getroot()
    length = root.find("recommends/display_length")
    assert length.get("compare") == "ge" and length.text == "360"
    # GNOME Software marks every control not listed as unsupported.
    controls = {c.text for c in root.findall("supports/control")}
    assert {"touch", "pointing", "keyboard"} <= controls


def test_metainfo_donation_url_matches_about_dialog():
    root = ET.parse(ROOT / "data" / f"{APP_ID}.metainfo.xml").getroot()
    donation = root.find("url[@type='donation']")
    assert donation is not None and donation.text == cirro.SUPPORT_URL


def test_user_agent():
    assert cirro.USER_AGENT == (
        f"Cirro/{cirro.VERSION} (+https://github.com/nexumia-de/cirro)")


def test_nightly_variant_of_desktop_file_and_metainfo():
    sys.path.insert(0, str(ROOT / "build-aux"))
    from nightly import nightly
    nightly_id = f"{APP_ID}.Devel"
    desktop = nightly((ROOT / "data" / f"{APP_ID}.desktop").read_text(),
                      nightly_id)
    assert "\nName=Cirro (Nightly)\n" in desktop
    assert f"\nIcon={nightly_id}\n" in desktop
    root = ET.fromstring(nightly(
        (ROOT / "data" / f"{APP_ID}.metainfo.xml").read_text(), nightly_id))
    assert root.findtext("id") == nightly_id
    assert root.findtext("name") == "Cirro (Nightly)"
    assert root.findtext("launchable") == f"{nightly_id}.desktop"
    # Only the stable app replaces the old Wetterblick id.
    assert root.find("replaces") is None


def test_stable_build_from_source_tree():
    assert cirro.APP_ID == APP_ID and not cirro.NIGHTLY
    assert cirro.VERSION_LABEL == cirro.VERSION
