"""Class sets: several copies of a page or a booklet, each with its own designs and, if names are given, a
name on each. Print and Save PDF (jobs.py) and the preview (render.py) build each copy the same way here.
"""

import re
from dataclasses import dataclass, field, replace

from inkengine.i18n import tr
from inkengine.page import has_answer

MAX_COPIES = 100


def copy_seed(seed, i):
    """The design of copy i (0 is the design shown): a fixed step from it, so the same set prints again alike."""
    return seed if i == 0 else (seed + i * 104729) & 0xFFFFFFFF


def copy_settings(s, i, vary):
    """The settings copy i draws with: with vary, every seed (the page's, a booklet's own pages', its swapped
    pages') stepped to copy i's; copy 0, or alike copies, as shown."""
    if not vary or i == 0:
        return s
    pages = [{**p, "seed": copy_seed(int(p.get("seed", s.seed)) & 0xFFFFFFFF, i)} for p in (s.page_list or [])]
    swapped = {k: copy_seed(int(v) & 0xFFFFFFFF, i) for k, v in (s.page_seeds or {}).items()}
    return replace(s, seed=copy_seed(s.seed, i), page_list=pages, page_seeds=swapped)


def copies_vary(s):
    """(whether copies of this single page can each have their own design, a note when some of them repeat or
    none can differ, or "")."""
    if s.mode != "make":
        return False, ""
    if s.gen == "name" and s.name_bg == "none":
        return False, "A name page with nothing underneath has no design to change, so its copies are alike."
    if s.gen == "dots":
        return True, "Dot-to-dot has only a handful of pictures, so some copies repeat."
    if s.gen == "nonogram" and s.complexity <= 1:
        return True, "The smallest nonograms sometimes repeat: raise Complexity for more variety."
    return True, ""


DIFFERENT_EVERY_COPY = {"bingo"}   # patterns whose copies are no use alike: bingo cards


def always_vary(s):
    """Whether copies get their own designs whatever "each its own design" says: bingo, where alike cards would
    all win at once."""
    if s.mode != "make":
        return False
    gens = {s.gen} | {p.get("gen") for p in (s.page_list or [])} if s.booklet else {s.gen}
    from inkengine.page import sheet_gens
    return bool((gens | set(sheet_gens(s))) & DIFFERENT_EVERY_COPY)


def copies_have_answers(s):
    """Whether copies of this single page can have answer pages: a puzzle (or colour by number) made up, or a
    sheet of several designs with one among them."""
    from inkengine.page import sheet_gens
    return s.mode == "make" and any(has_answer(gen, s) for gen in sheet_gens(s))


def parse_names(text, limit=MAX_COPIES):
    """The names typed for a class set (separated by commas, semicolons or new lines), at most limit."""
    names = [n for n in (n.strip() for n in re.split(r"[,;\n]", text or "")) if n]
    return names[:limit] if limit else names


def copy_labels(names):
    """What each named copy's answer is called: its name, or with the copy's number when a name repeats."""
    return [n if names.count(n) == 1 else f"{n} (copy {i + 1})" for i, n in enumerate(names)]


def named_pages(pages, name):
    """A booklet's pages for one child: the name on the cover and on every page's Name line, and the answer
    pages headed with it."""
    if not name:
        return pages
    out = []
    for p in pages:
        if p.kind == "answers":
            out.append(replace(p, title=f"{p.title} · {name}"))
        elif p.kind in ("cover", "design"):
            out.append(replace(p, filled_name=name))
        else:
            out.append(p)
    return out


@dataclass
class ClassSet:
    """Copies as the Paper section sets them up: how many, a new design on each, answer pages (single pages;
    a booklet has its own), and names (one copy each, written on the Name line)."""
    count: int = 1
    vary: bool = True
    answers: bool = False
    names: list = field(default_factory=list)
    answer_book: bool = False   # booklets: their answers in one teacher's book, after them all

    @property
    def active(self):
        return self.count > 1 or bool(self.names)

    def label(self, i):
        """What the preview's copy pager says: "Copy 2 of 25 · Ana"."""
        text = tr("Copy {i} of {n}").format(i=i + 1, n=self.count)
        return f"{text} · {self.names[i]}" if self.names and i < len(self.names) else text
