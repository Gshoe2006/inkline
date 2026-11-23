"""What's new: after an update, what changed since the version used last, from CHANGELOG.md.

The first start of a newer version shows the "What's new" (and "Changed", "Fixed", "Good to know") parts of
each release since the one last seen; how to upgrade and how to report a problem are left out. Help → What's
new shows the current version's at any time. The version last seen is kept in the settings folder. A first
install (no version seen, no settings yet) shows nothing and just remembers the version.
"""

import os
import re

from PySide6.QtWidgets import QDialog, QHBoxLayout, QTextBrowser, QVBoxLayout

from inkengine.i18n import tr

from . import config, theme
from .widgets import button

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = ("upgrading", "found a problem?")     # parts of a release's notes that aren't about what changed


def changelog_text():
    """CHANGELOG.md next to inkline.py (every package installs it there), or "" if it's missing."""
    try:
        with open(os.path.join(HERE, "CHANGELOG.md"), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _version(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except (AttributeError, ValueError):
        return None


def sections(text, newer_than=None, upto=None):
    """[(version, markdown)] for the releases after newer_than, up to and including upto, newest first. Each
    keeps what changed (its ### parts, as ## headings), without how to upgrade or report a problem."""
    out, cur, body, fence, keep = [], None, [], False, True

    def done():
        if cur is not None:
            v = _version(cur)
            if v and (newer_than is None or v > newer_than) and (upto is None or v <= upto):
                md = "\n".join(body).strip()
                if md:
                    out.append((cur, md))
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"##\s+v?(\d+\.\d+\.\d+)", line)
        if m:
            done()
            cur, body, keep = m.group(1), [], True
            continue
        if cur is None:
            continue
        if not fence and re.match(r"#{3}\s", line):
            keep = line[3:].strip().lower() not in SKIP
            line = line[1:]
        if keep:
            body.append(line)
    done()
    return out


def notes(version, seen=None):
    """The markdown to show for version: every release after seen (or just this one), or "" if none."""
    v, s = _version(version), _version(seen) if seen else None
    if v is None:
        return ""
    found = sections(changelog_text(), s, v)
    if s is None:
        found = [x for x in found if x[0] == version]
    return "\n\n".join(f"# Inkline {ver}\n\n{md}" for ver, md in found)


def due(version, remember):
    """The version last seen, if this start is the first since an update and should show what's new; else None.
    Records the current version either way."""
    if not remember or _version(version) is None:
        return None
    seen = config.read("seen-version.json").get("version")
    if config.write("seen-version.json", {"version": version}, "What's new"):
        return None   # it can't be remembered (a read-only settings folder): rather nothing than every start
    if not isinstance(seen, str) or _version(seen) is None:
        # never recorded: a first install shows nothing; an update from before this note (settings already there)
        # shows this version's
        return "" if config.read("last-settings.json") else None
    return seen if _version(seen) < _version(version) else None


class WhatsNew(QDialog):
    def __init__(self, parent, version, text):
        super().__init__(parent)
        self.setWindowTitle(tr("What's new in Inkline {version}").format(version=version))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(theme.PAD_X, theme.PAD_X, theme.PAD_X, theme.PAD_X)
        lay.setSpacing(theme.SECTION_GAP)
        view = QTextBrowser()
        view.setObjectName("whatsNew")
        view.setOpenExternalLinks(True)
        view.setMarkdown(text)
        lay.addWidget(view, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        close = button("Close", "primary")
        close.clicked.connect(self.accept)
        close.setDefault(True)
        row.addWidget(close)
        lay.addLayout(row)
        self.resize(560, 520)
