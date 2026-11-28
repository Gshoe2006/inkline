#!/usr/bin/env python3
"""Writes a translation as a spreadsheet or web page for someone who speaks the language to check, one row per string.

    python3 packaging/translation_sheet.py es                       writes inkline-es-review.csv here
    python3 packaging/translation_sheet.py fr out.csv               or to the file named
    python3 packaging/translation_sheet.py fr --needs-review        only what no native speaker has checked yet
    python3 packaging/translation_sheet.py fr review.html           a web page with search and filters instead
    python3 packaging/translation_sheet.py all inkline-review.html  every language on one page (web page only)
    python3 packaging/translation_sheet.py site out/                the review site: a page per language, one with
                                                                    every language, and index.html linking them

The site is published at https://gshoe2006.github.io/inkline/ by .github/workflows/translations-site.yml whenever
main's translations, word lists or this script change, so reviewers don't need Python.

Columns: where it appears (window or printed page), the English, the translation, whether it still needs a native
speaker's review (and the release it was written for: the newest first with --needs-review), then two empty
columns, "Better wording" and "Comment", for the reviewer to fill in, and the key that
packaging/translations/apply.py uses to put a better wording in. After the interface, the sheet lists the word
search themes, the crossword words and clues, the logic puzzle's names and things, the cryptogram's sayings, the
word ladder's words, the handwriting words, the draw-what-you-read sentences and the memory cards' picture words, which are written in the language rather than translated from
English, so they're checked too. The CSV is UTF-8 with a byte order mark, so Excel, LibreOffice and Google Sheets
open the accents correctly. The web page needs nothing else (no internet either): open it in any browser, type
better wordings into it, and copy them into a "Suggest a better translation" issue.

To use a reviewed sheet: python3 packaging/translations/apply.py SHEET.csv (see docs/translating.md). The word
lists are in inkengine/patterns/words.py, crossword.py, logic.py, cryptogram.py, ladder.py, trace.py, drawread.py and inkengine/pictures.py, and are
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
    from inkengine import pictures
    from inkengine.patterns import drawread
    for level, (en_list, items) in enumerate(zip(drawread.READ_SENTENCES["en"], drawread.READ_SENTENCES.get(code, []))):
        for en, text in zip(en_list, items):
            out.append((f"draw what you read: level {level + 1}", en, text))
    for name, word in pictures.WORDS.get(code, {}).items():
        out.append(("memory cards: picture words", pictures.WORDS["en"][name], word))
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
    counts = {c: [0, 0] for c in codes}
    for row in data["rows"]:
        counts[row[0]][1] += 1
        counts[row[0]][0] += bool(row[4])
    return {c: tuple(v) for c, v in counts.items()}


# --- the review site (GitHub Pages: .github/workflows/translations-site.yml) ---------------------------------------

SITE_URL = "https://gshoe2006.github.io/inkline/"
ISSUE_URL = "https://github.com/Gshoe2006/inkline/issues/new?template=translation.yml"
GUIDE_URL = "https://github.com/Gshoe2006/inkline/blob/main/docs/translating.md"
ENGLISH_NAMES = {"es": "Spanish", "fr": "French", "pt": "Brazilian Portuguese", "de": "German", "it": "Italian",
                 "nl": "Dutch"}


def index_page(counts, names, commit=None):
    """The review site's front page: a link to each language's page ({code}.html) with how many of its strings still
    need a native speaker's review, and to the page with every language (all.html). counts is {code: (needing review,
    total)}, names {code: the language's own name}; commit, if given, says which version of Inkline it shows."""
    from html import escape
    items = []
    for code, (need, total) in counts.items():
        own = names.get(code, code)
        english = ENGLISH_NAMES.get(code)
        label = escape(own) + (f' <span class="en">({escape(english)})</span>' if english and english != own else "")
        if need:
            status = f'<span class="badge need">{need} of {total} need review</span>'
        else:
            status = f'<span class="badge ok">all {total} reviewed</span>'
        items.append(f'  <li><a href="{escape(code)}.html">{label}</a> {status}</li>')
    need_all = sum(n for n, _t in counts.values())
    total_all = sum(t for _n, t in counts.values())
    made = f"<p class=\"small\">Made from commit <code>{escape(commit[:12])}</code> of Inkline's main branch.</p>" \
        if commit else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inkline translations</title>
<!-- Written by packaging/translation_sheet.py site. -->
<style>
:root {{ --bg: #fbfaf7; --fg: #1d1b18; --muted: #6b665e; --line: #e2ddd4; --card: #ffffff; --accent: #2f6db5;
        --warn-bg: #fff2d6; --warn-fg: #7a4d00; --ok-bg: #e3f3e6; --ok-fg: #1f6b33; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg: #1a1916; --fg: #ece8e1; --muted: #a39d93; --line: #3a3732; --card: #23211d; --accent: #7fb0ec;
          --warn-bg: #4a3a12; --warn-fg: #f5d28a; --ok-bg: #1d3a24; --ok-fg: #9fd9ad; }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 720px; margin: 0 auto; padding: 28px 16px 48px; }}
h1 {{ font-size: 26px; margin: 0 0 8px; }}
p {{ margin: 8px 0; color: var(--muted); }}
a {{ color: var(--accent); }}
ul {{ list-style: none; padding: 0; margin: 20px 0; background: var(--card); border: 1px solid var(--line); border-radius: 8px; }}
li {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 12px; padding: 12px 14px; border-bottom: 1px solid var(--line); }}
li:last-child {{ border-bottom: 0; }}
li a {{ font-weight: 600; text-decoration: none; }}
.en {{ color: var(--muted); font-weight: 400; }}
.badge {{ font-size: 13px; border-radius: 10px; padding: 2px 9px; align-self: center; }}
.need {{ background: var(--warn-bg); color: var(--warn-fg); }}
.ok {{ background: var(--ok-bg); color: var(--ok-fg); }}
.small {{ font-size: 13px; }}
</style>
</head>
<body>
<main>
<h1>Inkline translations</h1>
<p>Inkline's translations were written without a native speaker. If you speak one of these languages, open its
   page, read the translations beside the English and type a better wording beside any that sound wrong or
   unnatural. Then press <b>Copy my suggestions</b> and paste them into a
   <a href="{ISSUE_URL}">Suggest a better translation</a> issue. No programming or installing needed: what you type
   stays in your browser until you send it.</p>
<ul>
{chr(10).join(items)}
  <li><a href="all.html">Every language on one page</a> <span class="badge need">{need_all} of {total_all} need review</span></li>
</ul>
<p>What to look for, and how suggestions are used: <a href="{GUIDE_URL}">the translation guide</a>.</p>
{made}
</main>
</body>
</html>
"""


def write_site(folder, commit=None):
    """The review site in folder: a page for each language, one with every language and index.html linking them."""
    from inkengine import i18n
    os.makedirs(folder, exist_ok=True)
    codes = [c for c in i18n.LANGUAGES if c != "en"]
    counts = {}
    for code in codes:
        counts.update(write_html([code], os.path.join(folder, f"{code}.html")))
    write_html(codes, os.path.join(folder, "all.html"))
    with open(os.path.join(folder, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(index_page(counts, i18n.LANGUAGES, commit))
    return counts


def main(argv):
    from inkengine import i18n
    args = [a for a in argv[1:] if not a.startswith("--")]
    needs_review = "--needs-review" in argv
    codes = [c for c in i18n.LANGUAGES if c != "en"]
    if args and args[0] == "site":
        folder = args[1] if len(args) > 1 else "translations-site"
        for code, (need, total) in write_site(folder, os.environ.get("GITHUB_SHA")).items():
            print(f"{code}: {need} of {total} need review")
        print(f"wrote {folder}/index.html")
        return
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
