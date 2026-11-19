#!/usr/bin/env python3
"""Checks the files `inkline.py --selftest DIR` wrote: page sizes, page counts and SVG structure.

Usage: python3 packaging/check_selftest.py DIR      (needs pdfinfo, from poppler-utils)
Exits 0 when every expected file is right, 1 otherwise, listing each problem.
"""
import os
import re
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

PATTERNS = ["mandala", "maze", "truchet", "contour", "flow", "dots", "sudoku", "words", "nonogram", "spot", "kakuro", "mazeshape", "name", "cbnpattern", "nonophoto"]
PAGE_PX = (2550, 3300)                     # Letter at 300 dpi
PDF_PAGES = {**{n: 1 for n in PATTERNS + ["convert", "engrave", "stipple", "cbn", "testpage"]},
             "booklet": 9,                 # cover + 6 mazes + 2 answer pages
             "poster-mandala-2x2": 4,
             "poster-photo-3x3": 9,
             "photobook": 4,               # cover + 3 photos
             "booklet-fold": 6}            # the same booklet folded: 12 pages -> 3 sheets -> 6 sides
PDF_SIZE = {"booklet-fold": "792 x 612"}   # landscape sheets; everything else is portrait Letter
SVGS = PATTERNS + ["answers", "engrave", "stipple", "cbn"]


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    return struct.unpack(">II", head[16:24])


def pdf_info(path):
    out = subprocess.run(["pdfinfo", path], capture_output=True, text=True, check=True).stdout
    info = dict(line.split(":", 1) for line in out.splitlines() if ":" in line)
    return int(info["Pages"]), info.get("Page size", "").strip()


def main(d):
    problems = []
    if not shutil.which("pdfinfo"):
        return ["pdfinfo isn't installed (it comes with poppler-utils)"]
    for n in PATTERNS + ["convert", "engrave", "stipple", "cbn", "testpage"]:
        p = os.path.join(d, f"{n}.png")
        try:
            if png_size(p) != PAGE_PX:
                problems.append(f"{n}.png is {png_size(p)}, expected {PAGE_PX}")
        except (OSError, ValueError) as e:
            problems.append(f"{n}.png: {e}")
    for n, want in PDF_PAGES.items():
        p = os.path.join(d, f"{n}.pdf")
        try:
            pages, size = pdf_info(p)
            if pages != want:
                problems.append(f"{n}.pdf has {pages} pages, expected {want}")
            want_size = PDF_SIZE.get(n, "612 x 792")
            if not size.startswith(want_size):
                problems.append(f"{n}.pdf page size is '{size}', expected {want_size} pts")
        except (OSError, subprocess.CalledProcessError, KeyError, ValueError) as e:
            problems.append(f"{n}.pdf: couldn't read it ({e})")
    for n in SVGS:
        p = os.path.join(d, f"{n}.svg")
        try:
            root = ET.parse(p).getroot()
            if root.get("width") != "8.5in" or root.get("height") != "11in":
                problems.append(f"{n}.svg is {root.get('width')} x {root.get('height')}, expected 8.5in x 11in")
            # Count what's drawn, not <path> elements: the maze is one long path, the mandala hundreds of
            # paths, and a sudoku is 20 straight lines plus its numbers (text).
            commands = sum(len(re.findall(r"[MLHVCQA]", el.get("d", ""))) for el in root.iter("{http://www.w3.org/2000/svg}path"))
            texts = sum(1 for _ in root.iter("{http://www.w3.org/2000/svg}text"))
            if commands + texts < 60:
                problems.append(f"{n}.svg draws only {commands} path segments and {texts} labels; expected a full design")
        except (OSError, ET.ParseError) as e:
            problems.append(f"{n}.svg: {e}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    found = main(sys.argv[1])
    checked = len(PATTERNS) + 5 + len(PDF_PAGES) + len(SVGS)
    if found:
        print(f"check_selftest: {len(found)} problem(s) in {sys.argv[1]}:")
        for p in found:
            print(f"  - {p}")
        sys.exit(1)
    print(f"check_selftest: all {checked} files look right")
