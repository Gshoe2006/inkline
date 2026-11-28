"""Translation review: the needs-review marks, the review sheet and page, applying suggestions, Help → Help translate."""

import csv
import json
import os
import re
import shutil
import sys

import pytest

from inkengine import i18n

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packaging"))
sys.path.insert(0, os.path.join(ROOT, "packaging", "translations"))

import apply  # noqa: E402
import review  # noqa: E402
import translation_sheet  # noqa: E402

LANGS = [c for c in i18n.LANGUAGES if c != "en"]
HELP_TRANSLATE = "Help t&ranslate Inkline…"


# --- review.json -------------------------------------------------------------------------------------------------

def test_review_file_names_only_the_six_languages_and_is_written_like_the_translations():
    with open(review.PATH, encoding="utf-8") as f:
        text = f.read()
    raw = json.loads(text)
    assert set(raw) == {"needs_review", "reviewed"}
    for part in raw.values():
        assert set(part) <= set(LANGS)
    assert review.dumps(raw) == text   # sorted, indent 1: merges stay clean
    assert tuple(LANGS) == review.LANGS


@pytest.mark.parametrize("code", LANGS)
def test_every_mark_is_a_string_or_word_list_that_language_has(code):
    data = review.load()
    catalog = review.catalog(code)
    lists = review.list_keys(code)
    need, done = data["needs_review"][code], data["reviewed"][code]
    assert not set(need) & set(done), "marked both needing review and reviewed"
    for key in list(need) + list(done):
        if key.startswith("@"):
            assert key in lists, f"{code}: no word list {key!r} on the review sheet"
        else:
            assert key in catalog, f"{code}: {key!r} isn't in {code}.json"
    for note in need.values():
        assert note == review.NEW or re.fullmatch(r"\d+\.\d+\.\d+", note), note
    assert need, "seeded: nothing has had a native speaker's review yet"


def test_the_help_translate_string_needs_review_in_every_language():
    data = review.load()
    for code in LANGS:
        assert review.status(data, code, HELP_TRANSLATE) == review.NEW


def test_status_and_marks(tmp_path):
    path = tmp_path / "review.json"
    data = review.load(str(path))   # no file yet: nothing marked
    assert review.status(data, "fr", "Copies") == review.NEW   # unknown counts as needing review
    review.mark_needs_review(data, "fr", "Copies", "5.1.0")
    assert review.status(data, "fr", "Copies") == "5.1.0"
    review.mark_reviewed(data, "fr", "Copies", "2026-11-27")
    review.save(data, str(path))
    again = review.load(str(path))
    assert review.status(again, "fr", "Copies") is None and "Copies" not in again["needs_review"]["fr"]
    assert sorted(["unreleased", "6.1.0", "5.10.0", "5.9.0"], key=review.version_key) == \
        ["5.9.0", "5.10.0", "6.1.0", "unreleased"]


# --- the export --------------------------------------------------------------------------------------------------

@pytest.fixture
def marks(tmp_path, monkeypatch):
    """A review.json of our own: Copies checked in French, Print… written for 5.1.0, the rest unknown."""
    path = tmp_path / "review.json"
    data = review.load(str(path))
    review.mark_reviewed(data, "fr", "Copies", "2026-11-27")
    review.mark_needs_review(data, "fr", "Paper", "5.1.0")
    review.mark_reviewed(data, "fr", "@word ladder: words", "2026-11-27")
    review.save(data, str(path))
    monkeypatch.setattr(review, "PATH", str(path))
    return path


def test_the_sheet_marks_what_needs_review_and_filters_to_it(marks):
    rows = translation_sheet.sheet("fr")
    by_key = {r["key"]: r for r in rows}
    assert by_key["Copies"]["note"] is None and by_key["Paper"]["note"] == "5.1.0"
    assert by_key["@word ladder: words"]["note"] is None
    assert by_key["@cryptogram: sayings"]["note"] == review.NEW
    only = translation_sheet.sheet("fr", needs_review=True)
    keys = [r["key"] for r in only]
    assert "Copies" not in keys and "@word ladder: words" not in keys and "Paper" in keys
    assert len(only) == len(rows) - 2
    notes = [review.version_key(r["note"]) for r in only]
    assert notes == sorted(notes, reverse=True)   # newest first


def test_the_csv_has_a_needs_review_column_and_the_flag(marks, tmp_path):
    path = tmp_path / "fr.csv"
    translation_sheet.main(["translation_sheet.py", "fr", str(path), "--needs-review"])
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))
    assert rows[0][3] == "Needs review" and rows[0][6] == "Key"
    assert all(r[3].startswith("yes (") for r in rows[1:])
    assert "Copies" not in {r[6] for r in rows[1:]}
    paper = next(r for r in rows if r[6] == "Paper")
    assert paper[3] == "yes (5.1.0)" and paper[1] == "Paper"
    everything = tmp_path / "all.csv"
    translation_sheet.main(["translation_sheet.py", "fr", str(everything)])
    full = list(csv.reader(open(everything, encoding="utf-8-sig")))
    assert next(r for r in full if r[6] == "Copies")[3] == ""
    assert any(r[0] == "handwriting: words" for r in full)


def _page_data(path):
    text = open(path, encoding="utf-8").read()
    blob = re.search(r'<script type="application/json" id="data">(.*?)</script>', text, re.S).group(1)
    return text, json.loads(blob)


def test_the_web_page_is_self_contained_and_filters(marks, tmp_path):
    path = tmp_path / "fr.html"
    translation_sheet.main(["translation_sheet.py", "fr", str(path), "--needs-review"])
    text, data = _page_data(path)
    assert data["languages"] == {"fr": "Français"}
    assert len(data["rows"]) == len(translation_sheet.sheet("fr", needs_review=True))
    assert all(r[4] for r in data["rows"]) and "Copies" not in {r[5] for r in data["rows"]}
    # no outside files: scripts and styles are in the page
    assert not re.search(r"<script[^>]+src=|<link[^>]+stylesheet|@import|url\(", text)
    assert 'id="q"' in text and 'id="needs"' in text and "Copy my suggestions" in text
    assert "{{" not in text


def test_the_web_page_for_every_language_and_strings_that_look_like_html(tmp_path):
    path = tmp_path / "all.html"
    translation_sheet.main(["translation_sheet.py", "all", str(path)])
    text, data = _page_data(path)
    assert list(data["languages"]) == LANGS
    assert {r[0] for r in data["rows"]} == set(LANGS)
    # "Black &amp; white …" and the like can't end the script early
    body = re.search(r'id="data">(.*?)</script>', text, re.S).group(1)
    assert "<" not in body and "&" not in body
    assert any("&amp;" in r[2] for r in data["rows"])
    with pytest.raises(SystemExit):
        translation_sheet.main(["translation_sheet.py", "all", str(tmp_path / "all.csv")])


# --- the review site (GitHub Pages) ------------------------------------------------------------------------------

def test_the_site_index_links_each_language_with_its_counts():
    page = translation_sheet.index_page({"fr": (12, 40), "de": (0, 38), "xx": (3, 3)},
                                        {"fr": "Français", "de": "Deutsch", "xx": "<b>X & Y</b>"}, commit="abcdef0123456789")
    assert '<a href="fr.html">Français <span class="en">(French)</span></a>' in page
    assert "12 of 40 need review" in page and "all 38 reviewed" in page and "3 of 3 need review" in page
    assert '<a href="all.html">' in page and "15 of 81 need review" in page   # every language: the totals
    assert page.index('href="fr.html"') < page.index('href="de.html"') < page.index('href="all.html"')
    assert "&lt;b&gt;X &amp; Y&lt;/b&gt;" in page and "<b>X" not in page   # names are escaped
    assert "abcdef012345" in page and "abcdef0123456" not in page
    assert "template=translation.yml" in page and "docs/translating.md" in page
    assert not re.search(r"<script[^>]+src=|<link[^>]+stylesheet|@import|url\(", page)   # nothing to fetch
    assert "prefers-color-scheme: dark" in page and 'name="viewport"' in page
    assert "Made from commit" not in translation_sheet.index_page({"fr": (1, 2)}, {"fr": "Français"})


def test_the_site_has_a_page_per_language_and_an_index(marks, tmp_path):
    out = tmp_path / "site"
    translation_sheet.main(["translation_sheet.py", "site", str(out)])
    assert sorted(os.listdir(out)) == sorted([f"{c}.html" for c in LANGS] + ["all.html", "index.html"])
    index = (out / "index.html").read_text(encoding="utf-8")
    for code in LANGS:
        _text, data = _page_data(out / f"{code}.html")
        assert list(data["languages"]) == [code]
        need = sum(1 for r in data["rows"] if r[4])
        assert f'href="{code}.html"' in index and f"{need} of {len(data['rows'])} need review" in index
    _text, data = _page_data(out / "all.html")
    assert list(data["languages"]) == LANGS


def _site_workflow():
    return open(os.path.join(ROOT, ".github", "workflows", "translations-site.yml"), encoding="utf-8").read()


def test_the_site_workflow_builds_and_deploys_with_pages():
    yaml = pytest.importorskip("yaml")
    text = _site_workflow()
    flow = yaml.safe_load(text)
    on = flow[True]   # YAML 1.1 reads the key `on` as true
    assert "workflow_dispatch" in on and on["push"]["branches"] == ["main"]
    paths = on["push"]["paths"]
    for p in ("inkengine/locale/**", "packaging/translations/**", "packaging/translation_sheet.py",
              "inkengine/patterns/**"):
        assert p in paths
    assert flow["permissions"]["pages"] == "write" and flow["permissions"]["id-token"] == "write"
    build, deploy = flow["jobs"]["build"], flow["jobs"]["deploy"]
    uses = [s.get("uses", "").split("@")[0] for s in build["steps"]]
    runs = "\n".join(s.get("run", "") for s in build["steps"])
    assert uses.index("actions/checkout") < uses.index("actions/setup-python") < uses.index("actions/configure-pages") \
        < uses.index("actions/upload-pages-artifact")
    assert "PySide6-Essentials==6.12.0" in runs and "numpy" in runs
    assert "packages.microsoft.com" in runs and "sudo rm -f" in runs   # the apt source that fails at times
    site = re.search(r"translation_sheet\.py site (\S+)", runs).group(1)
    upload = [s for s in build["steps"] if s.get("uses", "").startswith("actions/upload-pages-artifact")][0]
    assert upload["with"]["path"] == site
    assert deploy["needs"] == "build" and deploy["environment"]["name"] == "github-pages"
    assert "steps.deployment.outputs.page_url" in deploy["environment"]["url"]
    step = deploy["steps"][-1]
    assert step["uses"].startswith("actions/deploy-pages@") and step["id"] == "deployment"


def test_the_guide_and_issue_form_point_reviewers_to_the_site():
    guide = open(os.path.join(ROOT, "docs", "translating.md"), encoding="utf-8").read()
    form = open(os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "translation.yml"), encoding="utf-8").read()
    assert translation_sheet.SITE_URL == "https://gshoe2006.github.io/inkline/"
    assert translation_sheet.SITE_URL in guide and translation_sheet.SITE_URL in form
    assert "GitHub Actions" in guide and "Settings → Pages" in guide   # what the owner does once
    assert "python3" not in form   # reviewers aren't asked to run anything
    assert guide.index(translation_sheet.SITE_URL) < guide.index("python3 packaging/translation_sheet.py")


# --- apply.py ----------------------------------------------------------------------------------------------------

@pytest.fixture
def copy(tmp_path):
    """The French and German files and an empty review.json, to change without touching the real ones."""
    locale = tmp_path / "locale"
    locale.mkdir()
    for code in ("fr", "de"):
        shutil.copy(os.path.join(review.LOCALE, f"{code}.json"), locale / f"{code}.json")
    path = tmp_path / "review.json"
    data = review.load(str(path))
    review.mark_needs_review(data, "fr", "Copies", "5.1.0")
    review.mark_needs_review(data, "fr", "Paper", "5.1.0")
    review.save(data, str(path))
    return locale, path


def _changed_lines(before, after):
    a, b = before.splitlines(), after.splitlines()
    assert len(a) == len(b)
    return [(x, y) for x, y in zip(a, b) if x != y]


def test_apply_changes_one_line_and_marks_it_reviewed(copy):
    locale, path = copy
    before = (locale / "fr.json").read_text(encoding="utf-8")
    rows = apply.read_rows("key,language,new_text,current_text,comment\n"
                           "Copies,Français (French),Copies à imprimer,Exemplaires,plus clair\n"
                           "Paper,fr,,,\n")
    changes, confirmed, by_hand = apply.apply(rows, str(locale), str(path), note="issue #1")
    assert changes == {"fr": {"Copies": "Copies à imprimer"}} and confirmed == [("fr", "Paper")] and not by_hand
    after = (locale / "fr.json").read_text(encoding="utf-8")
    assert _changed_lines(before, after) == [(' "Copies": "Exemplaires",', ' "Copies": "Copies à imprimer",')]
    assert review.dumps(json.loads(after)) == after
    marks = review.load(str(path))
    assert review.status(marks, "fr", "Copies") is None and review.status(marks, "fr", "Paper") is None
    assert marks["reviewed"]["fr"]["Copies"].endswith(" issue #1")
    assert (locale / "de.json").read_text(encoding="utf-8") == open(os.path.join(review.LOCALE, "de.json"),
                                                                       encoding="utf-8").read()


@pytest.mark.parametrize("key, new", [
    ("{n} copies", "exemplaires"),                     # lost its placeholder
    ("&File", "Fichier"),                              # lost the menu letter
    ("Copies", "&Exemplaires"),                        # a menu letter where there's no menu
    ("&Copy page\tCtrl+C", "&Copier la page Ctrl+C"),  # lost the tab before the shortcut
    ("Not a string Inkline has", "Rien"),
    ("Copies", "  Exemplaires"),
])
def test_apply_refuses_a_bad_row_and_writes_nothing(copy, key, new):
    locale, path = copy
    if key == "{n} copies" and key not in review.catalog("fr"):
        key = next(k for k in review.catalog("fr") if "{n}" in k)
    before = (locale / "fr.json").read_text(encoding="utf-8")
    review_before = path.read_text(encoding="utf-8")
    good = ("fr", "Paper", "Papier à dessin", "")
    with pytest.raises(apply.Problem):
        apply.apply([good, ("fr", key, new, "")], str(locale), str(path))
    assert (locale / "fr.json").read_text(encoding="utf-8") == before
    assert path.read_text(encoding="utf-8") == review_before


def test_apply_reads_a_filled_in_review_sheet(copy, tmp_path, monkeypatch):
    locale, path = copy
    monkeypatch.setattr(review, "PATH", str(path))
    sheet = tmp_path / "fr.csv"
    translation_sheet.main(["translation_sheet.py", "fr", str(sheet)])
    rows = list(csv.reader(open(sheet, encoding="utf-8-sig")))
    for r in rows:
        if r[6] == "Copies":
            r[4] = "Copies à imprimer"
        elif r[6] == "@crossword: Animals" and not any(x[4] for x in rows if x[6] == r[6]):
            r[4] = r[2] + " (mieux)"
    with open(sheet, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    text = sheet.read_text(encoding="utf-8-sig")
    only_filled = apply.read_rows(text)
    assert {k for _c, k, _n, _cur in only_filled} == {"Copies", "@crossword: Animals"}
    every = apply.read_rows(text, all_checked=True)
    assert len(every) == len(rows) - 1
    changes, confirmed, by_hand = apply.apply(every, str(locale), str(path))
    assert changes == {"fr": {"Copies": "Copies à imprimer"}}
    assert [k for _c, k, *_ in by_hand] == ["@crossword: Animals"]   # word lists are edited by hand
    marks = review.load(str(path))
    assert review.status(marks, "fr", "Paper") is None                     # read and fine
    assert review.status(marks, "fr", "@crossword: Animals") is not None   # still to edit
    assert review.status(marks, "fr", "@crossword: Food") is None


def test_apply_command_line(copy, tmp_path, monkeypatch, capsys):
    locale, path = copy
    monkeypatch.setattr(review, "LOCALE", str(locale))
    monkeypatch.setattr(review, "PATH", str(path))
    csv_path = tmp_path / "s.csv"
    csv_path.write_text("key,language,new_text\nCopies,fr,Copies à imprimer\n", encoding="utf-8")
    before = (locale / "fr.json").read_text(encoding="utf-8")
    apply.main(["apply.py", str(csv_path), "--dry-run"])
    assert "would change fr: 'Copies'" in capsys.readouterr().out
    assert (locale / "fr.json").read_text(encoding="utf-8") == before
    apply.main(["apply.py", str(csv_path), "--note", "issue #2"])
    assert json.loads((locale / "fr.json").read_text(encoding="utf-8"))["Copies"] == "Copies à imprimer"
    assert review.load(str(path))["reviewed"]["fr"]["Copies"].endswith("issue #2")
    bad = tmp_path / "bad.csv"
    bad.write_text("key,language,new_text\nCopies,Klingon,Copies\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        apply.main(["apply.py", str(bad)])


def test_language_names():
    assert apply.language("fr") == apply.language("Français") == apply.language("Français (French)") == "fr"
    assert apply.language("German") == apply.language("Deutsch (German)") == "de"
    assert apply.language("Português (Brazilian Portuguese)") == "pt" and apply.language("en") is None


# --- Help → Help translate Inkline… ------------------------------------------------------------------------------

def test_help_translate_has_a_different_menu_letter_in_every_language():
    help_menu = ["&What's new", "T&our of the window", "Check for &updates…", "Check for updates au&tomatically",
                 HELP_TRANSLATE, "&About Inkline"]
    for code in ["en"] + LANGS:
        cat = i18n.catalog(code)
        letters = [re.search(r"&(\w)", cat.get(s, s)).group(1).lower() for s in help_menu]
        assert len(set(letters)) == len(letters), (code, letters)


def test_help_translate_opens_the_guide(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    QApplication.instance() or QApplication([])
    from inkapp import window
    opened = []

    class Desktop:
        @staticmethod
        def openUrl(url):
            opened.append(url.toString())
            return True

    monkeypatch.setattr(window, "QDesktopServices", Desktop)
    w = window.Window("5.0.0", remember=False)
    try:
        help_menu = w._top_menus[-1]
        texts = [a.text() for a in help_menu.actions()]
        assert HELP_TRANSLATE in texts and texts.index(HELP_TRANSLATE) == texts.index("&About Inkline") - 1
        w.act_translate.trigger()
        assert opened == [window.TRANSLATE_URL]
        assert window.TRANSLATE_URL.endswith("/blob/main/docs/translating.md")
        assert os.path.isfile(os.path.join(ROOT, "docs", "translating.md"))
    finally:
        w.close()
        w.deleteLater()


def test_the_issue_form_and_guide_are_linked():
    form = open(os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "translation.yml"), encoding="utf-8").read()
    assert "name: Suggest a better translation" in form
    for name in ("Español", "Français", "Português", "Deutsch", "Italiano", "Nederlands"):
        assert f"- {name} (" in form
        assert apply.language(re.search(rf"- ({name} \([^)]*\))", form).group(1)) is not None
    assert "type: dropdown" in form and form.count("type: textarea") >= 4
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    assert "docs/translating.md" in readme
