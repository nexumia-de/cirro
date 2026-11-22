"""Type check with a ratchet (issue #43): run mypy and compare its
errors with build-aux/mypy-baseline.txt, ignoring line numbers.

- An error not in the baseline (a new one) fails.
- A baseline entry mypy no longer reports fails too, so fixed errors
  leave the baseline: run with --update and commit the smaller file.
  --update refuses to add errors.

Usage: python3 build-aux/mypy_ratchet.py [--update] [mypy command]
(default command: mypy, configured in pyproject.toml)."""

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

BASELINE = Path(__file__).with_name("mypy-baseline.txt")
_LINE = re.compile(r"^(?P<file>[^:]+):\d+(?::\d+)?: error: (?P<rest>.*)$")


def errors(output):
    """mypy output → Counter of "file: message [code]" without line numbers."""
    found = Counter()
    for line in output.splitlines():
        match = _LINE.match(line)
        if match:
            found[f"{match['file']}: {match['rest']}"] += 1
    return found


def read_baseline(path=BASELINE):
    if not path.exists():
        return Counter()
    return Counter(line for line in path.read_text().splitlines() if line.strip())


def write_baseline(found, path=BASELINE):
    path.write_text("".join(f"{line}\n" for line in sorted(found.elements())))


def main(argv):
    update = "--update" in argv
    command = [a for a in argv if a != "--update"] or ["mypy"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        print(result.stdout + result.stderr)
        return result.returncode
    found = errors(result.stdout)
    baseline = read_baseline()
    new = found - baseline
    fixed = baseline - found
    for line in sorted(new.elements()):
        print(f"new: {line}")
    if new:
        print(f"{sum(new.values())} new type error(s); fix them (the baseline only shrinks).")
        return 1
    if fixed:
        if update:
            write_baseline(found)
            print(f"Baseline shrunk by {sum(fixed.values())}; commit {BASELINE.name}.")
            return 0
        for line in sorted(fixed.elements()):
            print(f"fixed: {line}")
        print("Fixed errors are still in the baseline: run with --update and commit it.")
        return 1
    print(f"Type check: no new errors ({sum(found.values())} in the baseline).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
