#!/usr/bin/env python3
"""Prints the release notes for one version from CHANGELOG.md, for its GitHub Release.

    python3 packaging/release_notes.py                 the version in VERSION
    python3 packaging/release_notes.py 3.4.3           a given version

A version's notes are the section headed "## <version>" (anything after the version, such as
" - 2026-11-20", is ignored), up to the next "## " heading. Its "###" headings come out as "##",
so the notes read as a page of their own. Exits 1 with a message if the section is missing or empty.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def notes_for(version, changelog):
    """The notes for version from the changelog's text, or None if it has no such section."""
    heading = re.compile(r"^##\s+v?" + re.escape(version) + r"(?:\s|$)")
    lines, found, fence = [], False, False
    for line in changelog.replace("\r\n", "\n").split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and re.match(r"##\s", line):
            if found:
                break
            found = bool(heading.match(line))
            continue
        if found:
            if not fence and re.match(r"#{3,6}\s", line):
                line = line[1:]
            lines.append(line)
    if not found:
        return None
    return "\n".join(lines).strip("\n") + "\n"


def main(argv):
    if len(argv) > 2:
        sys.exit(__doc__)
    if len(argv) == 2:
        version = argv[1].strip()
    else:
        with open(os.path.join(ROOT, "VERSION")) as f:
            version = f.read().strip()
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        notes = notes_for(version, f.read())
    if notes is None:
        sys.exit(f"CHANGELOG.md has no section for {version}. Add one headed '## {version}'.")
    if not notes.strip():
        sys.exit(f"The '## {version}' section of CHANGELOG.md is empty. Write what changed.")
    sys.stdout.write(notes)


if __name__ == "__main__":
    main(sys.argv)
