"""Booklets built page by page (Settings.page_list): each page draws with its own pattern settings."""

import json

from inkengine import book
from inkengine.canvas import RecordingCanvas
from inkengine.page import PAGE_KEYS, Settings, clean_page, draw_page, geometry, page_settings

PAGES = [
    {"gen": "maze", "seed": 11, "complexity": 3, "maze_shape": "word", "maze_word": "Maya"},
    {"gen": "words", "seed": 12, "complexity": 4, "ws_theme": "custom", "ws_words": "mum, dad, pizza"},
    {"gen": "mandala", "seed": 13, "complexity": 6, "cbn": True, "cbn_colours": 5},
    {"gen": "mandala", "seed": 14, "complexity": 2},
    {"gen": "spot", "seed": 15, "complexity": 5, "spot_base": "truchet"},
    {"gen": "kakuro", "seed": 16, "complexity": 2},
]


def _book(**kw):
    return Settings(booklet=True, page_list=[dict(p) for p in PAGES], dpi=100, **kw)


def test_each_page_brings_its_own_pattern_and_complexity():
    s = _book()
    designs = [p for p in book.book_pages(s) if p.kind == "design"]
    assert [(d.gen, d.seed, d.c) for d in designs] == [(p["gen"], p["seed"], p["complexity"]) for p in PAGES]
    assert page_settings(s, designs[0]).maze_shape == "word" and page_settings(s, designs[0]).maze_word == "Maya"
    assert page_settings(s, designs[4]).spot_base == "truchet"
    assert page_settings(s, designs[3]) is s or page_settings(s, designs[3]).cbn is False   # nothing of its own to add
    assert s.maze_shape == "rect"                                                        # the booklet's own stay put


def test_answers_cover_the_puzzles_and_colour_by_number_pages_only():
    pages = book.book_pages(_book())
    answered = [d.gen for p in pages if p.kind == "answers" for d in p.items]
    assert answered == ["maze", "words", "mandala", "spot", "kakuro"]   # the plain mandala has no answer
    cover = pages[0]
    assert cover.kind == "cover" and cover.title == "Colouring & puzzle book"
    assert book.book_pages(Settings(booklet=True, page_list=[PAGES[0], PAGES[0]]))[0].title == "Maze book"


def test_pages_ramp_and_mix_are_ignored_for_a_page_list():
    a = book.book_pages(_book(pages=30, mix=True, ramp=True))
    b = book.book_pages(_book(pages=2, mix=False, ramp=False))
    assert [(p.kind, p.gen, p.seed, p.c) for p in a] == [(p.kind, p.gen, p.seed, p.c) for p in b]


def test_every_page_draws():
    s = _book()
    g = geometry(s)
    for spec in book.book_pages(s):
        draw_page(RecordingCanvas(), g, spec, s)


def test_an_empty_list_is_the_booklet_as_before():
    s = Settings(booklet=True, pages=6, mix=True)
    assert [(p.kind, p.gen, p.seed, p.c) for p in book.book_pages(s)] == \
           [(p.kind, p.gen, p.seed, p.c) for p in book.book_pages(Settings(booklet=True, pages=6, mix=True, page_list=[]))]


def test_a_saved_list_reads_back_with_only_page_settings_of_the_right_type():
    s = _book()
    back = Settings.from_dict(json.loads(json.dumps(s.to_dict())))
    assert back.page_list == s.page_list
    messy = Settings.from_dict({"pageList": [{"gen": "maze", "complexity": "7", "cbn": "true", "frame": True, "junk": 1}, "nope"]})
    assert messy.page_list == [{"gen": "maze", "complexity": 7, "cbn": True}]   # booklet-wide keys and junk dropped
    assert set(clean_page({k: None for k in PAGE_KEYS})) <= set(PAGE_KEYS)
