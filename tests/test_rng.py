from inkengine.rng import mulberry32, pick

# Values printed by index.html's mulberry32 function, run in Node.
JS_SEED_1 = [0.6270739405881613, 0.002735721180215478, 0.5274470399599522, 0.9810509674716741, 0.9683778982143849]
JS_SEED_BIG = [0.9966664777603, 0.6840177071280777, 0.7737663032021374]   # seed 20261117 * 7919, past 2**32


def test_matches_javascript():
    r = mulberry32(1)
    assert [r() for _ in range(5)] == JS_SEED_1


def test_large_and_negative_seeds_wrap_like_js():
    r = mulberry32(20261117 * 7919)
    assert [r() for _ in range(3)] == JS_SEED_BIG
    a, b = mulberry32(-1), mulberry32(0xFFFFFFFF)
    assert [a() for _ in range(4)] == [b() for _ in range(4)]


def test_pick_stays_in_range():
    r = mulberry32(99)
    assert {pick(r, 3) for _ in range(500)} == {0, 1, 2}
