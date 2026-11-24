"""Age levels: a starting point for each pattern that suits a child's age, so nobody has to tune every slider.

Choosing an age sets the pattern's complexity, the line weight (thicker for small hands), how many colours
colour by number uses, which sums a maths drill asks and what handwriting traces. Choosing another pattern
with an age chosen sets that pattern's complexity for the age too. Anything can be changed afterwards: the age
is only where the settings start.
"""

AGES = {"any": "Any age", "4-6": "Ages 4–6", "7-9": "Ages 7–9", "10+": "Ages 10 and up"}

# complexity (1..10) for each pattern at each age
COMPLEXITY = {
    "mandala":   {"4-6": 3, "7-9": 5, "10+": 8},
    "maze":      {"4-6": 2, "7-9": 5, "10+": 8},
    "truchet":   {"4-6": 3, "7-9": 5, "10+": 8},
    "contour":   {"4-6": 2, "7-9": 5, "10+": 8},
    "flow":      {"4-6": 3, "7-9": 5, "10+": 8},
    "dots":      {"4-6": 1, "7-9": 4, "10+": 7},
    "sudoku":    {"4-6": 1, "7-9": 3, "10+": 6},
    "name":      {"4-6": 3, "7-9": 5, "10+": 7},
    "words":     {"4-6": 1, "7-9": 4, "10+": 8},
    "nonogram":  {"4-6": 1, "7-9": 3, "10+": 6},
    "spot":      {"4-6": 2, "7-9": 5, "10+": 8},
    "kakuro":    {"4-6": 1, "7-9": 3, "10+": 6},
    "maths":     {"4-6": 1, "7-9": 4, "10+": 8},
    "trace":     {"4-6": 1, "7-9": 4, "10+": 7},
    "crossword": {"4-6": 1, "7-9": 4, "10+": 8},
    "clock":     {"4-6": 2, "7-9": 5, "10+": 8},
    "scramble":  {"4-6": 1, "7-9": 4, "10+": 8},
    "spelltest": {"4-6": 1, "7-9": 4, "10+": 8},
    "fractions": {"4-6": 1, "7-9": 4, "10+": 8},
    "symmetry":  {"4-6": 1, "7-9": 4, "10+": 8},
}
# what else an age sets, whatever the pattern
EXTRAS = {
    "4-6": {"weight": 6, "cbn_colours": 4, "maths_kind": "add", "trace_source": "upper"},
    "7-9": {"weight": 4, "cbn_colours": 6, "maths_kind": "addsub", "trace_source": "lower"},
    "10+": {"weight": 3, "cbn_colours": 8, "maths_kind": "mixed", "trace_source": "words"},
}


def for_age(s, age=None):
    """The settings to change for an age (s.age unless given): {} for "any"."""
    age = s.age if age is None else age
    if age not in EXTRAS:
        return {}
    out = dict(EXTRAS[age])
    c = COMPLEXITY.get(s.gen, {}).get(age)
    if c:
        out["complexity"] = c
    return out


def for_pattern(s):
    """A new pattern chosen with an age set: just its complexity for that age (the other settings stay as the
    person left them)."""
    c = COMPLEXITY.get(s.gen, {}).get(s.age)
    return {"complexity": c} if c else {}
