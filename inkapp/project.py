"""Project files (.inkline): everything being made, in one file to open again later or move to another computer.

A project is JSON: the settings (a booklet's own pages included), and each photo with its crop. Photos are kept
inside the file as PNG, so a project still opens when the pictures it was made from have moved or gone.
"""

import base64
import json
import os
import threading
from dataclasses import dataclass, field, replace

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage

from inkengine.page import Settings
from inkengine.photo import Photo

EXT = "inkline"
FILTER = "Inkline projects (*.inkline)"
FORMAT = 1          # bumped only if an older Inkline would read a newer file wrongly


class ProjectError(Exception):
    """A project that can't be read: the message says why, for the status line."""


@dataclass
class Project:
    settings: Settings
    photos: list = field(default_factory=list)
    sel: int = 0          # the photo being cropped
    book_sel: int = 0     # the booklet page being edited
    skipped: int = 0      # photos in the file that couldn't be read (left out)


_PACKED = {}                  # photo id -> its PNG, base64: a photo's picture never changes (its crop is kept apart),
_PACKED_LOCK = threading.Lock()   # so saving again, or a recovery copy every minute, doesn't pack it again


def _packed(photo):
    with _PACKED_LOCK:
        text = _PACKED.get(photo.id)
    if text is None:
        text = _png(photo.image)
        with _PACKED_LOCK:
            if len(_PACKED) > 200:
                _PACKED.clear()
            _PACKED[photo.id] = text
    return text


def _png(img):
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    if not img.save(buf, "PNG"):
        raise OSError("couldn't pack a photo")
    return base64.b64encode(bytes(buf.data())).decode("ascii")


def _image(text):
    img = QImage()
    if not isinstance(text, str) or not img.loadFromData(QByteArray(base64.b64decode(text, validate=True)), "PNG"):
        raise ValueError("not a PNG")
    return img.convertToFormat(QImage.Format.Format_ARGB32)


def to_json(state, version="dev", extra=None):
    s = replace(state.settings, testpage=False)   # the printer test page is a look at the printer, not part of the work
    return {
        "app": "Inkline", "format": FORMAT, "version": version,
        "settings": s.to_dict(),
        "photos": [{"name": p.name, "png": _packed(p), "rot": p.rot, "zoom": p.zoom, "panx": p.panx, "pany": p.pany,
                    "neutral": p.neutral} for p in state.photos],
        "sel": state.sel, "bookSel": state.book_sel,
        **(extra or {}),
    }


def save(path, state, version="dev", extra=None):
    """Write the project (atomically: a crash never leaves half a file). Raises OSError. extra: more keys to
    keep in the file (a recovery copy's note of where the work came from)."""
    data = json.dumps(to_json(state, version, extra), ensure_ascii=False)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _num(v, default, lo, hi):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def from_json(data):
    try:
        return _from_json(data)
    except ProjectError:
        raise
    except Exception:   # anything else odd in the file (wrong types, absurd numbers, deep nesting): it's damaged
        raise ProjectError("isn't an Inkline project, or it's damaged") from None


def _from_json(data):
    if not isinstance(data, dict) or data.get("app") != "Inkline" or not isinstance(data.get("settings"), dict):
        raise ProjectError("isn't an Inkline project")
    try:
        fmt = int(data.get("format", 1))
    except (TypeError, ValueError):
        fmt = 0
    if fmt > FORMAT:
        raise ProjectError(f"was saved by a newer Inkline ({data.get('version', 'unknown version')}). Update Inkline to open it")
    s = Settings.from_dict({**Settings().to_dict(), **Settings.from_dict(data["settings"]).to_dict()})
    photos, skipped = [], 0
    listed = data.get("photos") or []
    for p in listed if isinstance(listed, list) else []:
        if not isinstance(p, dict):
            continue
        try:
            img = _image(p.get("png"))
        except (ValueError, TypeError):
            skipped += 1   # one damaged photo doesn't lose the rest of the project
            continue
        rot = int(_num(p.get("rot"), 0, 0, 270)) // 90 * 90
        photos.append(Photo(img, rot=rot, zoom=_num(p.get("zoom"), 100, 100, 400), panx=_num(p.get("panx"), 0, -100, 100),
                            pany=_num(p.get("pany"), 0, -100, 100), neutral=bool(p.get("neutral", False)),
                            name=str(p.get("name") or "photo")))
    sel = int(_num(data.get("sel"), 0, 0, max(0, len(photos) - 1)))
    book_sel = int(_num(data.get("bookSel"), 0, 0, max(0, len(s.page_list) - 1)))
    return Project(replace(s, testpage=False), photos, sel, book_sel, skipped)


def load(path):
    """The project in a file. Raises ProjectError with a reason fit to show (OSError if it can't be opened)."""
    return read(path)[0]


def read(path):
    """(the project, the file's JSON object), for keys beyond the project's own (a recovery copy's)."""
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except (ValueError, RecursionError):
            raise ProjectError("isn't an Inkline project, or it's damaged") from None
    return from_json(data), data


def title(path):
    """The project's name, as the window title and recent list show it."""
    name = os.path.basename(path)
    return name[:-len(EXT) - 1] if name.lower().endswith("." + EXT) else name
