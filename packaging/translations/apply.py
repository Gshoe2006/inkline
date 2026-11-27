#!/usr/bin/env python3
"""Puts better translations into Inkline: updates inkengine/locale/<code>.json and marks them as reviewed.

    python3 packaging/translations/apply.py suggestions.csv            apply, then say what changed
    python3 packaging/translations/apply.py sheet.csv --dry-run        only say what would change
    python3 packaging/translations/apply.py sheet.csv --all-checked    a review sheet whose every row was checked
    python3 packaging/translations/apply.py s.csv --note "issue #140"  noted beside each reviewed string

It reads either kind of CSV:

  key,language,new_text[,current_text,comment]
      What the review web page copies and the "Suggest a better translation" issue asks for. language is a code
      (fr) or a name (Français). An empty new_text means "checked, it's fine as it is".
  A review sheet from packaging/translation_sheet.py
      Where,English,<language>,Needs review,Better wording,Comment,Key. Each row with a better wording is
      applied; with --all-checked the rest of the rows count as checked too.

Each new text must keep the English's {placeholders} and, for a menu item, one & (the keyboard letter). If any
row is wrong, nothing is written. A string applied, or confirmed, is moved from "needs_review" to "reviewed" in
packaging/translations/review.json. The translation files are rewritten exactly as they're kept (sorted keys,
indent 1), so the only change in git diff is the strings themselves.

Word lists (keys starting with @, such as "@crossword: Animals") live in Python files, so they're listed for
editing by hand rather than changed here.
"""

import csv
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import review  # noqa: E402

NAMES = {"es": "Español", "fr": "Français", "pt": "Português", "de": "Deutsch", "it": "Italiano", "nl": "Nederlands"}
ENGLISH_NAMES = {"es": "Spanish", "fr": "French", "pt": "Portuguese", "de": "German", "it": "Italian", "nl": "Dutch"}


class Problem(Exception):
    pass


def language(text):
    """A language code from "fr", "Français", "French" or "Français (French)"; None if it isn't one of the six."""
    t = (text or "").strip()
    low = t.lower()
    if low in NAMES:
        return low
    for code in NAMES:
        if low.startswith(NAMES[code].lower()) or low.startswith(ENGLISH_NAMES[code].lower()):
            return code
    return None


def placeholders(s):
    return sorted(re.findall(r"\{\w+\}", s))


def has_accelerator(s):
    return bool(re.search(r"&(?!amp;)\w", s))


def check(key, new):
    """Why a new translation can't be used for an English key, or None."""
    if not new.strip():
        return "is empty"
    if new != new.strip():
        return "starts or ends with a space"
    if placeholders(key) != placeholders(new):
        return f"must keep the placeholders {' '.join(placeholders(key)) or '(none)'}"
    if has_accelerator(key) != has_accelerator(new):
        return "needs an & before a letter (a menu's keyboard letter)" if has_accelerator(key) \
            else "mustn't have an & before a letter (only menu items have one)"
    if new.count("\t") != key.count("\t"):
        return "must keep the tab before the shortcut (e.g. \\tCtrl+C)"
    return None


def read_rows(text, all_checked=False):
    """[(language, key, new_text or "", current_text or "")] from either kind of CSV."""
    text = text.lstrip("﻿")
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return []
    low = [h.strip().lower() for h in header]
    out = []
    if {"key", "language", "new_text"} <= set(low):
        k, lang, new = low.index("key"), low.index("language"), low.index("new_text")
        cur = low.index("current_text") if "current_text" in low else None
        for n, row in enumerate(reader, 2):
            if not any(c.strip() for c in row):
                continue
            row += [""] * (len(header) - len(row))
            code = language(row[lang])
            if code is None:
                raise Problem(f"line {n}: {row[lang]!r} isn't one of the languages: {', '.join(NAMES)}")
            out.append((code, row[k], row[new], row[cur] if cur is not None else ""))
        return out
    if len(low) >= 5 and low[0] == "where" and low[1] == "english":
        code = language(header[2])
        if code is None:
            raise Problem(f"the sheet's third column, {header[2]!r}, isn't one of the languages")
        better = low.index("better wording")
        key_col = low.index("key") if "key" in low else None
        for row in reader:
            if not any(c.strip() for c in row):
                continue
            row += [""] * (len(header) - len(row))
            where, en, current = row[0], row[1], row[2]
            key = row[key_col] if key_col is not None and row[key_col] else (
                en if where in review.PAGE_PLACES else "@" + where)
            new = row[better].strip()
            if new or all_checked:
                out.append((code, key, new, current))
        return out
    raise Problem("the first line must be key,language,new_text or a review sheet's headings (Where,English,...)")


def plan(rows, locale_dir=None):
    locale_dir = locale_dir or review.LOCALE
    """What to do: ({code: {key: new}}, [(code, key) confirmed as they are], [hand edits], [problems])."""
    changes, confirmed, by_hand, problems = {}, [], [], []
    catalogs = {}
    for code, key, new, current in rows:
        if key.startswith("@"):
            if new and new != current:
                by_hand.append((code, key, current, new))
            else:
                confirmed.append((code, key))
            continue
        if code not in catalogs:
            with open(os.path.join(locale_dir, f"{code}.json"), encoding="utf-8") as f:
                catalogs[code] = json.load(f)
        cat = catalogs[code]
        if key not in cat:
            problems.append(f"{code}: {key!r} isn't a string Inkline has (copy the English exactly, or the Key column)")
            continue
        if not new or new == cat[key]:
            confirmed.append((code, key))
            continue
        why = check(key, new)
        if why:
            problems.append(f"{code}: {key!r} → {new!r} {why}")
            continue
        if current and current != cat[key]:
            print(f"note: {code}: {key!r} has changed since the suggestion was made ({current!r} → {cat[key]!r})")
        changes.setdefault(code, {})[key] = new
    pending = {(code, key) for code, key, *_ in by_hand}   # a list with one entry still to edit isn't checked yet
    confirmed = [c for c in dict.fromkeys(confirmed) if c not in pending]
    return changes, confirmed, by_hand, problems


def write_catalog(path, updates):
    with open(path, encoding="utf-8") as f:
        before = f.read()
    data = json.loads(before)
    if review.dumps(data) != before:
        raise Problem(f"{path} isn't written the usual way (sorted, indent 1); not touching it")
    data.update(updates)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(review.dumps(data))


def apply(rows, locale_dir=None, review_path=None, note=None, dry_run=False):
    locale_dir = locale_dir or review.LOCALE
    changes, confirmed, by_hand, problems = plan(rows, locale_dir)
    if problems:
        raise Problem("nothing written:\n  " + "\n  ".join(problems))
    if not dry_run:
        for code, updates in changes.items():
            write_catalog(os.path.join(locale_dir, f"{code}.json"), updates)
        marks = review.load(review_path)
        import datetime
        stamp = datetime.date.today().isoformat() + (f" {note}" if note else "")
        for code, updates in changes.items():
            for key in updates:
                review.mark_reviewed(marks, code, key, stamp)
        for code, key in confirmed:
            review.mark_reviewed(marks, code, key, stamp)
        review.save(marks, review_path)
    return changes, confirmed, by_hand


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    note = None
    if "--note" in argv:
        i = argv.index("--note")
        note = argv[i + 1] if i + 1 < len(argv) else None
        if note in args:
            args.remove(note)
    if not args:
        sys.exit(__doc__)
    rows = []
    try:
        for path in args:
            with open(path, encoding="utf-8-sig") as f:
                rows += read_rows(f.read(), "--all-checked" in argv)
        changes, confirmed, by_hand = apply(rows, note=note, dry_run="--dry-run" in argv)
    except Problem as e:
        sys.exit(str(e))
    verb = "would change" if "--dry-run" in argv else "changed"
    for code, updates in sorted(changes.items()):
        for key, new in sorted(updates.items()):
            print(f"{verb} {code}: {key!r} → {new!r}")
    print(f"{sum(len(u) for u in changes.values())} {verb}, {len(confirmed)} confirmed as they are"
          + (" (dry run: nothing written)" if "--dry-run" in argv else ""))
    for code, key, current, new in by_hand:
        print(f"edit by hand ({key[1:]}, {code}): {current!r} → {new!r}")
    if by_hand:
        print("Word lists are in inkengine/patterns/*.py; after editing, mark them checked with a CSV line "
              "key,language,new_text with an empty new_text.")


if __name__ == "__main__":
    main(sys.argv)
