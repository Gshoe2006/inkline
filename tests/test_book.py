"""Booklets against recordings of index.html's bookPages, drawPage and foldOrder
(tests/fixtures/booklet_js.json.gz)."""

import pytest
from recording import load_fixture, same_ops

from inkengine import book, output
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings, draw_page, geometry

CASES = load_fixture("booklet")


def settings(k):
    return Settings(gen=k["gen"], complexity=k["c"], pages=k["pages"] if isinstance(k["pages"], int) else len(k["pages"]),
                    ramp=k["ramp"], mix=k["mix"], cover=k["cover"], page_nums=k["pageNums"], key=k["key"],
                    title=k["title"], name_line=k["nameLine"], seed=k["seed"], page_seeds=dict(k["pageSeeds"]))


def ident(k):
    return f"{'mix' if k['mix'] else k['gen']}-{len(k['pages'])}pages" + ("-swapped" if k["pageSeeds"] else "")


@pytest.mark.parametrize("k", CASES, ids=ident)
def test_page_list_matches_javascript(k):
    want_n = len([p for p in k["pages"] if p["kind"] == "design"])
    pages = book.book_pages(settings({**k, "pages": want_n}))
    assert len(pages) == len(k["pages"])
    for got, want in zip(pages, k["pages"]):
        assert got.kind == want["kind"]
        assert got.page_no == want["pageNo"] and bool(got.header) == want["header"]
        if want["kind"] == "design":
            assert (got.gen, got.seed, got.c, got.label, got.idx) == (want["gen"], want["seed"], want["c"], want["label"], want["idx"])
            assert (got.title, got.name) == (want["title"], want["name"])
        elif want["kind"] == "cover":
            assert (got.title, got.art_seed) == (want["title"], want["artSeed"])
        else:
            assert [d.idx for d in got.items] == want["items"]


@pytest.mark.parametrize("k", [k for k in CASES if k["coverOps"] or k["answersOps"]], ids=ident)
def test_cover_and_answer_pages_match_javascript(k):
    want_n = len([p for p in k["pages"] if p["kind"] == "design"])
    s = settings({**k, "pages": want_n})
    pages, g = book.book_pages(s), geometry(s)
    for kind, want in (("cover", k["coverOps"]), ("answers", k["answersOps"])):
        if not want:
            continue
        ctx = RecordingCanvas(em_per_char=0.55)
        draw_page(ctx, g, next(p for p in pages if p.kind == kind), s)
        same_ops(ctx.ops, want)


@pytest.mark.parametrize("k", CASES, ids=ident)
def test_fold_order_matches_javascript(k):
    n = len(k["pages"]) + (-len(k["pages"]) % 4)
    assert book.fold_order(n) == [(side["left"], side["right"]) for side in k["foldOrder"]]


def test_fold_order_puts_pages_in_reading_order():
    """Stack the sheets, fold them: reading every side's pages left to right, outside in, gives 1..n."""
    for n in (4, 8, 16, 48):
        sides = book.fold_order(n)
        seen = sorted(p for side in sides for p in side)
        assert seen == list(range(n))
        assert sides[0] == (n - 1, 0) and sides[-1] == (n // 2 - 1, n // 2)   # outermost and middle spread


def test_swapping_one_page_leaves_the_others():
    s = Settings(gen="maze", pages=6)
    before = book.book_pages(s)
    after = book.book_pages(book.swap_page(s, 2, 99))
    assert [p.seed for p in after if p.kind == "design"] == [99 if p.idx == 2 else p.seed for p in before if p.kind == "design"]
    # a settings file stores the keys as strings
    assert book.book_pages(Settings(gen="maze", pages=6, page_seeds={"2": 99}))[3].seed == 99


def test_labels():
    pages = book.book_pages(Settings(gen="sudoku", pages=5))
    assert book.page_label(pages, 0) == "Page 1 of 8 · cover"
    assert book.page_label(pages, 7) == "Page 8 of 8 · answers"
    folded = book.fold_pages(pages)
    assert book.fold_side_label(folded, 0) == "Sheet 1 of 2 · front (pages 8 & 1)"
    assert book.fold_side_label(book.fold_pages(pages[:6]), 1) == "Sheet 1 of 2 · back (pages 2 & blank)"


def test_booklet_pdfs(tmp_path):
    from PySide6.QtPdf import QPdfDocument
    from inkengine.qt import ensure_app
    ensure_app()
    s = Settings(mix=True, pages=9, complexity=3, title="Rainy day")
    # cover, 9 pages, and 2 answer pages for the 5 puzzles (maze, dot-to-dot, sudoku, word search, nonogram)
    assert output.write_book_pdf(tmp_path / "b.pdf", s) == 1 + 9 + 2
    folded = Settings(mix=True, pages=9, complexity=3, fold=True)
    assert output.write_book_pdf(tmp_path / "f.pdf", folded) == 6         # 12 pages -> 3 sheets, both sides
    for name, pages, w, h in (("b.pdf", 12, 612, 792), ("f.pdf", 6, 792, 612)):
        doc = QPdfDocument()
        doc.load(str(tmp_path / name))
        size = doc.pagePointSize(0)
        assert doc.pageCount() == pages and (round(size.width()), round(size.height())) == (w, h)


PHOTO_BOOKS = load_fixture("photobook")


@pytest.mark.parametrize("k", PHOTO_BOOKS, ids=lambda k: f"{k['n']}photos{'-cover' if k['cover'] else ''}{'-numbers' if k['nums'] else ''}")
def test_photo_book_matches_javascript(k, monkeypatch):
    """The page list and the cover's and last page's text; the photos themselves aren't drawn here."""
    from inkengine import page as page_mod, photo
    monkeypatch.setattr(photo, "convert", lambda *a, **kw: None)
    s = Settings(mode="convert", style="threshold", dpi=150, pcover=k["cover"], ppage_nums=k["nums"], title=k["title"],
                 name_line=k["nameLine"])
    photos = [photo.Photo(None, name=f"p{i}") for i in range(k["n"])]
    pages = book.photo_book_pages(s, photos)
    assert [(p.kind, p.page_no, bool(p.header), p.title, p.name) for p in pages] == \
           [(q["kind"], q["pageNo"], q["header"], q["title"], q["name"]) for q in k["pages"]]
    assert [photos.index(p.photo) for p in pages] == [int(q["photo"][2:]) for q in k["pages"]]
    g = geometry(s)

    def texts(spec):
        ctx = RecordingCanvas(em_per_char=0.55)
        draw_page(ctx, g, spec, s)
        return [o for o in ctx.ops if o[0] == "text"]

    if k["coverText"]:
        same_ops(texts(pages[0]), k["coverText"])
    same_ops(texts(pages[-1]), k["firstPageText"])


def test_photo_book_pdf(tmp_path):
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtPdf import QPdfDocument
    from inkengine import photo
    from inkengine.qt import ensure_app
    ensure_app()
    photos = []
    for i in range(3):
        img = QImage(120, 90, QImage.Format.Format_ARGB32)
        img.fill(QColor(60 * i, 120, 200))
        photos.append(photo.Photo(img))
    s = Settings(mode="convert", style="threshold", dpi=150, title="Three")
    assert output.write_book_pdf(tmp_path / "b.pdf", s, photos) == 4          # cover and three photo pages
    assert output.write_book_pdf(tmp_path / "f.pdf", Settings(mode="convert", dpi=150, fold=True), photos) == 2
    doc = QPdfDocument()
    doc.load(str(tmp_path / "b.pdf"))
    assert doc.pageCount() == 4
