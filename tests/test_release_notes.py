"""packaging/release_notes.py: picking one version's notes out of CHANGELOG.md for its release."""
import importlib.util
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "packaging", "release_notes.py")
spec = importlib.util.spec_from_file_location("release_notes", SCRIPT)
release_notes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_notes)

CHANGELOG = """# Changelog

Intro text.

## 3.5.0 - 2026-12-01

New things.

### What's new

- **Thing.** It works.

```sh
## not a heading, inside code
```

## 3.4.10

Ten.

## 3.4.1 - 2026-11-19

One.
"""


def test_picks_the_section_and_lifts_its_headings():
    notes = release_notes.notes_for("3.5.0", CHANGELOG)
    assert notes.startswith("New things.\n")
    assert "\n## What's new\n" in notes
    assert "## not a heading, inside code" in notes   # code is left alone
    assert "Ten." not in notes                          # stops at the next version


def test_version_must_match_exactly():
    assert release_notes.notes_for("3.4.1", CHANGELOG) == "One.\n"
    assert release_notes.notes_for("3.4.10", CHANGELOG) == "Ten.\n"
    assert release_notes.notes_for("3.4", CHANGELOG) is None


def test_missing_section():
    assert release_notes.notes_for("9.9.9", CHANGELOG) is None


def test_changelog_has_notes_for_the_current_version():
    """CHANGELOG.md must always cover VERSION, or the release workflow stops."""
    result = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


def test_every_heading_starts_its_own_line():
    """A release's notes run up to the next "## "; one stuck to the end of a line (6.3.0's notes ended
    "...about printing.## 6.2.0") ends up in the published notes."""
    import os
    import re
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CHANGELOG.md")
    text = open(path, encoding="utf-8").read()
    assert not re.search(r"\S#{2,3} \d", text), "a heading starts mid-line"
