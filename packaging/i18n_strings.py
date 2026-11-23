#!/usr/bin/env python3
"""Lists every English string Inkline shows or prints that a translation needs, from the source code.

    python3 packaging/i18n_strings.py            the strings, one per line (JSON strings)
    python3 packaging/i18n_strings.py es         those inkengine/locale/es.json doesn't translate yet

It finds tr("...") calls, the text given to the widget helpers that translate it themselves (label, button,
check, Hint, OptionRow, Section, the sidebar's _check/_slider/_text, the window's act, line_edit's placeholder),
the texts of drop-down options, and the option tables those come from (pattern names, themes, kinds of sum, ages,
layouts, photo styles, crayons, presets, undo step names). tests/test_i18n.py uses it to check a translation is
complete.
"""

import ast
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDERS = ("inkapp", "inkengine")
# helper: positions of its translated text arguments (and keyword names)
HELPERS = {"label": ([0], []), "button": ([0, 2], ["tip"]), "check": ([0], []), "Hint": ([0], []),
           "OptionRow": ([0], []), "Section": ([0], []), "slider_row": ([0], []), "_check": ([1], []),
           "_slider": ([1], []), "_text": ([1], []), "act": ([1], []), "line_edit": ([1], ["placeholder"]), "tr": ([0], [])}
# module-level tables whose texts are shown: their values (dicts), or each tuple's second item (lists of pairs)
TABLES = {"NAMES", "THEME_NAMES", "KINDS", "SOURCES", "AGES", "SHEETS", "STYLE_NAMES", "BACKGROUNDS", "SHAPE_NAMES",
          "BASES", "STEP_NAMES", "GEN_OPTIONS", "GRID_OPTIONS", "MARGINS", "PATTERN_COLOURS", "CRAYONS",
          "BUILTIN_PRESETS", "INSTRUCTIONS", "CBN_PATTERN_NOTE", "IMAGE_FILTER", "FILTER", "MESSAGES"}


def _name(func):
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""


def _strings(node):
    """The plain strings in a node: a constant, or each text of a list/tuple/dict of them."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _strings(node.body) + _strings(node.orelse)
    return []


def _table(node):
    out = []
    if isinstance(node, ast.Dict):
        for k, v in zip(node.keys, node.values):
            if isinstance(v, ast.Dict):   # presets: their names are the keys
                out += _strings(k)
            else:
                out += _strings(v)
    elif isinstance(node, (ast.List, ast.Tuple)):
        for e in node.elts:
            if isinstance(e, (ast.Tuple, ast.List)) and len(e.elts) >= 2:
                out += _strings(e.elts[1]) if not isinstance(e.elts[0], ast.Constant) or isinstance(e.elts[0].value, (str, float, int)) else []
                if isinstance(e.elts[0], ast.Constant) and isinstance(e.elts[0].value, str) and len(e.elts) > 2:
                    out += _strings(e.elts[0])   # CRAYONS: (name, r, g, b)
            else:
                out += _strings(e)
    else:
        out += _strings(node)
    return out


def scan():
    found = set()
    for folder in FOLDERS:
        for base, _dirs, files in os.walk(os.path.join(ROOT, folder)):
            for f in files:
                if not f.endswith(".py"):
                    continue
                tree = ast.parse(open(os.path.join(base, f), encoding="utf-8").read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        name = _name(node.func)
                        if name in HELPERS:
                            pos, kws = HELPERS[name]
                            for i in pos:
                                if i < len(node.args):
                                    found.update(_strings(node.args[i]))
                            for kw in node.keywords:
                                if kw.arg in kws:
                                    found.update(_strings(kw.value))
                        elif name in ("combo", "_combo") and node.args:
                            arg = node.args[-1] if name == "_combo" else node.args[0]
                            found.update(_table(arg))
                    elif isinstance(node, ast.Assign) and len(node.targets) == 1 and \
                            isinstance(node.targets[0], ast.Name) and node.targets[0].id in TABLES:
                        found.update(_table(node.value))
    return sorted(s for s in found if any(c.isalpha() for c in s))


def main(argv):
    strings = scan()
    if len(argv) > 1:
        from inkengine.i18n import catalog
        have = catalog(argv[1])
        strings = [s for s in strings if s not in have]
    for s in strings:
        print(json.dumps(s, ensure_ascii=False))


if __name__ == "__main__":
    sys.path.insert(0, ROOT)
    main(sys.argv)
