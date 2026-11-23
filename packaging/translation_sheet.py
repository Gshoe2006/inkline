#!/usr/bin/env python3
"""Writes a translation as a spreadsheet for someone who speaks the language to check, one row per string.

    python3 packaging/translation_sheet.py es               writes inkline-es-review.csv here
    python3 packaging/translation_sheet.py fr out.csv       or to the file named

Columns: where it appears (window or printed page), the English, the translation, then two empty columns,
"Better wording" and "Comment", for the reviewer to fill in. After the interface, the sheet lists the word
search themes and the crossword words and clues, which are written in the language rather than translated
from English, so they're checked too. The file is UTF-8 with a byte order mark, so Excel, LibreOffice and
Google Sheets open the accents correctly.

To use a reviewed sheet: copy each "Better wording" into inkengine/locale/<code>.json (or the word lists in
inkengine/patterns/words.py and crossword.py), keeping every {placeholder} and the & of a menu item.
"""

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "packaging"))

PAGE_FILES = ("inkengine",)   # strings found under here are printed on pages; the rest are in the window


def _places():
    """{English string: "window" or "page"}, from where the source asks for it."""
    import ast
    import i18n_strings
    wanted = set(i18n_strings.scan())
    found = {}
    for folder in i18n_strings.FOLDERS:
        for base, _dirs, files in os.walk(os.path.join(ROOT, folder)):
            for f in files:
                if not f.endswith(".py"):
                    continue
                tree = ast.parse(open(os.path.join(base, f), encoding="utf-8").read())
                where = "page" if folder in PAGE_FILES else "window"
                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and node.value in wanted:
                        found.setdefault(node.value, set()).add(where)
    return {s: " and ".join(sorted(found.get(s, {"window"}))) for s in wanted}


def rows(code):
    from inkengine.patterns import crossword, words
    catalog = json.load(open(os.path.join(ROOT, "inkengine", "locale", f"{code}.json"), encoding="utf-8"))
    places = _places()
    out = [(places.get(en, "window"), en, catalog.get(en, "")) for en in sorted(catalog, key=str.lower)]
    for theme, text in words.THEMES_BY_LANGUAGE.get(code, {}).items():
        out.append((f"word search: {words.THEME_NAMES.get(theme, theme)}", words.THEMES[theme], text))
    for theme, text in crossword.THEMES_BY_LANGUAGE.get(code, {}).items():
        for entry in (e.strip() for e in text.split(";")):   # as written, accents and all
            if entry:
                out.append((f"crossword: {crossword.THEME_NAMES.get(theme, theme)}", "", entry))
    return out


def main(argv):
    from inkengine import i18n
    if len(argv) < 2 or argv[1] not in i18n.LANGUAGES or argv[1] == "en":
        sys.exit(__doc__ + "\nLanguages: " + ", ".join(c for c in i18n.LANGUAGES if c != "en"))
    code = argv[1]
    path = argv[2] if len(argv) > 2 else f"inkline-{code}-review.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Where", "English", i18n.LANGUAGES[code], "Better wording", "Comment"])
        for where, en, tr in rows(code):
            w.writerow([where, en, tr, "", ""])
    print(f"wrote {path}")


if __name__ == "__main__":
    main(sys.argv)
