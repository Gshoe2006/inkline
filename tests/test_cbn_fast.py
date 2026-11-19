"""The numpy region steps in inkengine/cbn.py against the pixel-by-pixel reference (tests/cbn_reference.py):
the same regions, numbered the same way, the same 32-bit distances and the same merges, numbers and ties."""

import numpy as np
import pytest

import cbn_reference as ref
from inkengine import cbn


def grids():
    rng = np.random.default_rng(11)
    for n in range(30):
        w, h = int(rng.integers(3, 60)), int(rng.integers(3, 60))
        k = int(rng.integers(2, 7))
        blob = int(rng.integers(1, 6))
        small = rng.integers(-1 if n % 3 == 0 else 0, k, (h // blob + 1, w // blob + 1))
        g = np.repeat(np.repeat(small, blob, 0), blob, 1)[:h, :w]
        noise = rng.random((h, w)) < 0.05
        g = np.where(noise, rng.integers(0, k, (h, w)), g)
        yield pytest.param(g.reshape(-1).tolist(), w, h, k, id=f"{w}x{h}-k{k}-{n}")


GRIDS = list(grids())


@pytest.mark.parametrize("val, w, h, k", GRIDS)
def test_mode_filter(val, w, h, k):
    assert cbn.mode_filter(val, w, h, k).tolist() == ref.mode_filter(val, w, h, k).tolist()


@pytest.mark.parametrize("val, w, h, k", GRIDS)
def test_regions_and_distances(val, w, h, k):
    want, n = ref.components(val, w, h)
    got, m = cbn.components(val, w, h)
    assert (got.tolist(), m) == (want, n)
    d_want = ref.distance(want, w, h)
    d_got = cbn.distance(got, w, h)
    assert d_got.tobytes() == bytes(d_want)          # bit for bit
    assert cbn.region_info(got, m, val, w, h) == ref.region_info(want, n, val, w, h)


@pytest.mark.parametrize("val, w, h, k", GRIDS)
def test_merge_and_spots(val, w, h, k):
    for min_r in (1.5, 2.2, 3.7):
        want_label, want_info = ref.merge(list(val), w, h, min_r)
        label, info, d = cbn.merge(val, w, h, min_r)
        assert label.tolist() == want_label and info == want_info
        assert cbn.spots(label, info, w, h, min_r, 6, d) == ref.spots(want_label, want_info, w, h, min_r, 6)
