"""Cirro: rain radar with a 2-hour forecast for Phosh phones."""

try:
    from cirro.config import APP_ID, BUILD_LABEL
except ImportError:  # run from the source tree, config.py is not built
    APP_ID = "de.nexumia.Cirro"
    BUILD_LABEL = ""
VERSION = "0.1.0"
# The nightly app is built from every push to main
# (docs/release-channels.md).
NIGHTLY = APP_ID.endswith(".Devel")
NAME = "Cirro (Nightly)" if NIGHTLY else "Cirro"
# About dialog, e.g. "0.1.0 (main · 8534d2c)" for a nightly build.
VERSION_LABEL = f"{VERSION} ({BUILD_LABEL})" if BUILD_LABEL else VERSION
REPO_URL = "https://github.com/suitably/cirro"
# Voluntary support for development (phosh-toolkit docs/support.md).
SUPPORT_URL = "https://liberapay.com/suitably"
# Sent with every HTTP request (OSM tile policy, DWD open data etiquette).
USER_AGENT = f"Cirro/{VERSION} (+{REPO_URL})"
