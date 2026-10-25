"""Release notes from the installed AppStream metainfo, for the About
dialog. Releases and their notes are written by the release workflow
(docs/release-channels.md); this only reads them. No GTK."""
import xml.etree.ElementTree as ET
from pathlib import Path

from gi.repository import GLib

# Running from the source tree: the stable file in data/.
_SOURCE = Path(__file__).resolve().parent.parent / "data" / "de.nexumia.Cirro.metainfo.xml"


def find(app_id):
    """Path of the installed metainfo of `app_id`, else the source tree's."""
    for directory in GLib.get_system_data_dirs():
        path = Path(directory) / "metainfo" / f"{app_id}.metainfo.xml"
        if path.is_file():
            return path
    return _SOURCE if _SOURCE.is_file() else None


def release_notes(path):
    """(version, description markup) of the newest release, or None. The
    markup is AppStream's (<p>, <ul>, <li>…), which AdwAboutDialog takes."""
    if path is None:
        return None
    try:
        release = ET.parse(path).getroot().find("releases/release")
    except (OSError, ET.ParseError):
        return None
    if release is None:
        return None
    description = release.find("description")
    if description is None:
        return None
    markup = "".join(ET.tostring(e, encoding="unicode") for e in description)
    return release.get("version"), " ".join(markup.split())
