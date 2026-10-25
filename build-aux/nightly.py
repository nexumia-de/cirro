"""Writes the nightly variant of the desktop file or the metainfo.

    nightly.py <stable file> <output file> <nightly app id>

The stable files in data/ stay the only source; meson calls this for
-Dprofile=development (docs/release-channels.md).
"""
import re
import sys

BASE_ID = "de.nexumia.Cirro"


def nightly(text, app_id):
    text = text.replace(BASE_ID, app_id)
    text = text.replace("\nName=Cirro\n", "\nName=Cirro (Nightly)\n")
    text = text.replace("<name>Cirro</name>", "<name>Cirro (Nightly)</name>")
    # Only the stable app replaces the old Wetterblick id.
    text = re.sub(r"\n\s*<replaces>.*?</replaces>", "", text, flags=re.S)
    if "Cirro (Nightly)" not in text:
        raise ValueError("no Name= line or <name> element to rename")
    return text


if __name__ == "__main__":
    src, dst, app_id = sys.argv[1:]
    with open(src, encoding="utf-8") as f:
        text = nightly(f.read(), app_id)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)
