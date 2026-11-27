#!/usr/bin/env python3
"""Writes a translation as a spreadsheet or web page for someone who speaks the language to check, one row per string.

    python3 packaging/translation_sheet.py es                       writes inkline-es-review.csv here
    python3 packaging/translation_sheet.py fr out.csv               or to the file named
    python3 packaging/translation_sheet.py fr --needs-review        only what no native speaker has checked yet
    python3 packaging/translation_sheet.py fr review.html           a web page with search and filters instead
    python3 packaging/translation_sheet.py all inkline-review.html  every language on one page (web page only)

Columns: where it appears (window or printed page), the English, the translation, whether it still needs a native
speaker's review (and the release it was written for: the newest first with --needs-review), then two empty
columns, "Better wording" and "Comment", for the reviewer to fill in, and the key that
packaging/translations/apply.py uses to put a better wording in. After the interface, the sheet lists the word
search themes, the crossword words and clues, the logic puzzle's names and things, the cryptogram's sayings, the
word ladder's words and the handwriting words, which are written in the language rather than translated from
English, so they're checked too. The CSV is UTF-8 with a byte order mark, so Excel, LibreOffice and Google Sheets
open the accents correctly. The web page needs nothing else (no internet either): open it in any browser, type
better wordings into it, and copy them into a "Suggest a better translation" issue.

To use a reviewed sheet: python3 packaging/translations/apply.py SHEET.csv (see docs/translating.md). The word
lists are in inkengine/patterns/words.py, crossword.py, logic.py, cryptogram.py, ladder.py and trace.py, and are
edited by hand; keep every {placeholder} and the & of a menu item.
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
    from inkengine.patterns import cryptogram, ladder, logic
    for kind, items in logic.WORDS.get(code, {}).items():   # in the grid, then in a clue
        en = logic.WORDS["en"][kind]
        if kind == "child":
            out.append(("logic puzzle: names", en, items))
        else:
            for (word, said), (en_word, en_said) in zip(items, en):
                out.append((f"logic puzzle: {logic.HEADINGS[kind]}", f"{en_word} ({en_said})", f"{word} ({said})"))
    for saying in cryptogram.SAYINGS.get(code, []):
        out.append(("cryptogram: sayings", "", saying))
    out.append(("word ladder: words", "", " ".join(ladder.WORDS.get(code, "").split())))
    from inkengine.patterns import trace
    if code in trace.DEFAULT_WORDS:
        out.append(("handwriting: words", " ".join(trace.DEFAULT_WORDS["en"]), " ".join(trace.DEFAULT_WORDS[code])))
    return out


def _review():
    sys.path.insert(0, os.path.join(ROOT, "packaging", "translations"))
    import review
    return review


def sheet(code, needs_review=False):
    """The rows to check: [{"where", "english", "text", "note", "key"}]. "note" is None once a native speaker has
    checked the row, else the release it was written for. Only the unchecked ones with needs_review, newest first."""
    review = _review()
    marks = review.load()
    out = []
    for where, en, tr in rows(code):
        key = en if where in review.PAGE_PLACES else "@" + where
        out.append({"where": where, "english": en, "text": tr, "note": review.status(marks, code, key), "key": key})
    if needs_review:
        out = [r for r in out if r["note"] is not None]
        out.sort(key=lambda r: review.version_key(r["note"]), reverse=True)   # stable: alphabetical within a release
    return out


def needs_review_text(note):
    return "" if note is None else f"yes ({note})"


def write_csv(code, path, needs_review=False):
    from inkengine import i18n
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Where", "English", i18n.LANGUAGES[code], "Needs review", "Better wording", "Comment", "Key"])
        for r in sheet(code, needs_review):
            w.writerow([r["where"], r["english"], r["text"], needs_review_text(r["note"]), "", "", r["key"]])


def write_html(codes, path, needs_review=False):
    """One web page, CSS and script inside it: search, filters, a box for a better wording on each row, and a
    button that copies the better wordings as key,language,new_text lines for an issue or apply.py."""
    from inkengine import i18n
    data = {"languages": {c: i18n.LANGUAGES[c] for c in codes}, "rows": []}
    for c in codes:
        for r in sheet(c, needs_review):
            data["rows"].append([c, r["where"], r["english"], r["text"], r["note"] or "", r["key"]])
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")   # safe inside <script>
    with open(os.path.join(ROOT, "packaging", "translations", "sheet.html"), encoding="utf-8") as f:
        page = f.read()
    title = "Inkline translations" if len(codes) > 1 else f"Inkline in {i18n.LANGUAGES[codes[0]]}"
    page = page.replace("{{TITLE}}", title).replace("{{DATA}}", blob)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)


def main(argv):
    from inkengine import i18n
    args = [a for a in argv[1:] if not a.startswith("--")]
    needs_review = "--needs-review" in argv
    codes = [c for c in i18n.LANGUAGES if c != "en"]
    if not args or (args[0] not in codes and args[0] != "all"):
        sys.exit(__doc__ + "\nLanguages: " + ", ".join(codes) + ", or all")
    code = args[0]
    path = args[1] if len(args) > 1 else ("inkline-review.html" if code == "all" else f"inkline-{code}-review.csv")
    if path.lower().endswith((".html", ".htm")):
        write_html(codes if code == "all" else [code], path, needs_review)
    elif code == "all":
        sys.exit("all languages at once is a web page: name a file ending in .html")
    else:
        write_csv(code, path, needs_review)
    print(f"wrote {path}")


if __name__ == "__main__":
    main(sys.argv)
