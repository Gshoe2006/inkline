#!/usr/bin/env python3
"""Which translations a native speaker has checked: packaging/translations/review.json.

    python3 packaging/translations/review.py            how many strings in each language still need review
    python3 packaging/translations/review.py --sync     mark strings added since as needing review, drop vanished ones

review.json has two parts, each {language: {key: note}}:

  "needs_review"   written without a native speaker's check (by machine, or by someone who doesn't speak it).
                   The note is the release it was last written for, e.g. "6.1.0", or "unreleased"; the export
                   lists the newest first.
  "reviewed"       checked by a native speaker. The note is the date, and where the check came from if known.

A key is a string's English text (as in inkengine/locale/<code>.json), or, for the word lists written in the
language itself (word search themes, crossword words, the logic puzzle's names and things, sayings, ladder words,
handwriting words), "@" and where the review sheet lists it, e.g. "@crossword: Animals". A string in neither part
(added since review.json was last synced) counts as needing review.

The file is kept apart from the translations so that adding a string to them never touches it. It's written
like them (sorted keys, one space of indent), so changes to it merge cleanly too.
"""

import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PATH = os.path.join(HERE, "review.json")
LOCALE = os.path.join(ROOT, "inkengine", "locale")
LANGS = ("es", "fr", "pt", "de", "it", "nl")
NEW = "unreleased"   # the note for a string written since the last release
PAGE_PLACES = ("window", "page", "page and window")   # a review sheet's "Where" for a string in the JSON


def dumps(data):
    """JSON as the translation files are written: sorted keys, indent 1, accents as they are, a newline at the end."""
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def load(path=None):
    try:
        with open(path or PATH, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    return {part: {code: dict(data.get(part, {}).get(code, {})) for code in LANGS}
            for part in ("needs_review", "reviewed")}


def save(data, path=None):
    out = {part: {code: keys for code, keys in data[part].items() if keys or part == "needs_review"}
           for part in ("needs_review", "reviewed")}
    with open(path or PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps(out))


def status(data, code, key):
    """None once a native speaker has checked it, else the note of when it was written ("6.1.0", or NEW)."""
    if key in data["reviewed"].get(code, {}):
        return None
    return data["needs_review"].get(code, {}).get(key, NEW)


def mark_reviewed(data, code, key, note=None):
    data["needs_review"][code].pop(key, None)
    data["reviewed"][code][key] = note or datetime.date.today().isoformat()


def mark_needs_review(data, code, key, note=NEW):
    data["reviewed"][code].pop(key, None)
    data["needs_review"][code][key] = note


def version_key(note):
    """Sorts notes oldest first: "5.0.0" < "6.1.0" < "unreleased"."""
    try:
        return tuple(int(p) for p in note.split(".")), ""
    except (AttributeError, ValueError):
        return (10 ** 6,), str(note)


def catalog(code):
    with open(os.path.join(LOCALE, f"{code}.json"), encoding="utf-8") as f:
        return json.load(f)


def list_keys(code):
    """The "@where" keys of the word lists the review sheet lists for a language."""
    sys.path.insert(0, os.path.join(ROOT, "packaging"))
    import translation_sheet
    return {"@" + where for where, *_ in translation_sheet.rows(code) if where not in PAGE_PLACES}


def all_keys(code):
    return set(catalog(code)) | list_keys(code)


def sync(data):
    """Marks every key not in review.json as needing review, and drops keys that no longer exist."""
    changed = 0
    for code in LANGS:
        keys = all_keys(code)
        for part in ("needs_review", "reviewed"):
            for k in [k for k in data[part][code] if k not in keys]:
                del data[part][code][k]
                changed += 1
        for k in keys - set(data["needs_review"][code]) - set(data["reviewed"][code]):
            data["needs_review"][code][k] = NEW
            changed += 1
    return changed


def main(argv):
    sys.path.insert(0, ROOT)
    data = load()
    if "--sync" in argv:
        n = sync(data)
        save(data)
        print(f"{n} change(s) to {os.path.relpath(PATH)}")
    for code in LANGS:
        keys = all_keys(code)
        waiting = sum(1 for k in keys if status(data, code, k) is not None)
        print(f"{code}: {waiting} of {len(keys)} need review")


if __name__ == "__main__":
    main(sys.argv)
