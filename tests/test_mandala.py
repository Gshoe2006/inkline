"""The Python mandala against recordings of index.html's genMandala (tests/fixtures/mandala_js.json.gz)."""


import pytest
from recording import load_fixture, same_ops

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings
from inkengine.patterns import mandala
from inkengine.rng import mulberry32

CASES = load_fixture("mandala")


def draw(k):
    ctx = RecordingCanvas()
    ctx.line_width = k["lw"]
    info = mandala.draw(ctx, Box(**k["box"]), mulberry32(k["seed"]), k["c"], Settings(gen="mandala"), lw=k["lw"])
    return ctx, info


@pytest.mark.parametrize("k", CASES, ids=lambda k: f"seed{k['seed']}-c{k['c']}")
def test_matches_javascript(k):
    ctx, _ = draw(k)
    same_ops(ctx.ops, k["ops"])


def test_recordings_cover_every_motif():
    """So the comparison above has exercised each motif's drawing code."""
    used = set()
    for k in CASES:
        used.update(draw(k)[1]["motifs"])
    assert used == set(mandala.MOTIFS)


def test_rings_follow_complexity_and_motifs_never_repeat():
    for c in range(1, 11):
        info = mandala.draw(RecordingCanvas(), Box(0, 0, 1000, 1000), mulberry32(c * 31), c, lw=4)
        assert info["rings"] == 3 + int(c * 1.1 + 0.5)
        assert info["base"] in (6, 8, 10, 12)
        assert all(a != b for a, b in zip(info["motifs"], info["motifs"][1:]))
