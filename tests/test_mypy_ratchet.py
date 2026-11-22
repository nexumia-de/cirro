"""The type check ratchet (build-aux/mypy_ratchet.py, issue #43)."""

import importlib.util
from collections import Counter
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "mypy_ratchet", Path(__file__).parent.parent / "build-aux" / "mypy_ratchet.py"
)
ratchet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ratchet)


def test_errors_ignore_line_numbers():
    output = (
        'cirro/a.py:3: error: Need type annotation for "x"  [var-annotated]\n'
        'cirro/a.py:9: error: Need type annotation for "x"  [var-annotated]\n'
        "cirro/a.py:9: note: some hint\n"
        "Found 2 errors in 1 file\n"
    )
    assert ratchet.errors(output) == Counter(
        {'cirro/a.py: Need type annotation for "x"  [var-annotated]': 2}
    )


def test_baseline_round_trip(tmp_path):
    path = tmp_path / "baseline.txt"
    found = Counter({"a: e [x]": 2, "b: f [y]": 1})
    ratchet.write_baseline(found, path)
    assert ratchet.read_baseline(path) == found
    assert ratchet.read_baseline(tmp_path / "missing.txt") == Counter()
