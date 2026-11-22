"""Report a Problem (phosh-toolkit docs/feedback.md): the action, the main
menu entry and the About dialog's issue address."""

from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import pytest

pytest.importorskip("h5py")
gi = pytest.importorskip("gi")
try:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    gi.require_version("Shumate", "1.0")
    gi.require_version("Soup", "3.0")
except ValueError:
    pytest.skip("GTK, libadwaita, libshumate or libsoup typelibs missing", allow_module_level=True)

from cirro import REPO, VERSION_LABEL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def app(monkeypatch):
    # The token never reaches the host's keyring in tests.
    monkeypatch.setenv("PHOSH_TOOLKIT_TEST_KEYRING", "memory")
    from cirro import main

    return main.Application()


def test_report_problem_action_exists(app):
    assert app.lookup_action("report-problem") is not None


def test_main_menu_has_report_a_problem_next_to_about():
    source = (ROOT / "cirro" / "window.py").read_text()
    report = '_Report a Problem…", "app.report-problem"'
    about = '"_About Weather Radar", "app.about"'
    assert report in source
    assert source.index(report) < source.index(about)


def test_about_issue_url_is_the_filled_form(app):
    from cirro import main

    with mock.patch.object(main.Adw, "AboutDialog") as dialog:
        app._on_about()
    url = dialog.call_args.kwargs["issue_url"]
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    assert f"github.com/{REPO}/issues/new" in url
    assert query["template"] == ["bug.yml"]
    assert query["version"] == [VERSION_LABEL]
    assert "device" in query
