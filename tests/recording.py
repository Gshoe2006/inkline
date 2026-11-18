"""Comparing a RecordingCanvas with a recording of index.html (tests/fixtures/*_js.json.gz)."""

import gzip
import json
import os

import pytest


def load_fixture(name):
    """The recorded cases for a pattern, made by tests/fixtures/make_fixtures.js."""
    with gzip.open(os.path.join(os.path.dirname(__file__), "fixtures", f"{name}_js.json.gz"), "rt") as f:
        return json.load(f)


def same_ops(got, want):
    """Every drawing step the same, coordinates to 1/1000 of a pixel."""
    want = [tuple(o) for o in want]
    assert len(got) == len(want), f"{len(got)} drawing steps, JavaScript drew {len(want)}"
    for n, (a, b) in enumerate(zip(got, want)):
        assert a[0] == b[0] and len(a) == len(b), f"step {n}: {a} vs {b}"
        for x, y in zip(a[1:], b[1:]):
            if isinstance(y, (int, float)) and not isinstance(y, bool):
                assert x == pytest.approx(y, abs=1e-3), f"step {n}: {a} vs {b}"
            else:
                assert x == y, f"step {n}: {a} vs {b}"
