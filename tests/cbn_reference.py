"""Colour by number's region steps as index.html wrote them, one pixel at a time: the reference that
inkengine/cbn.py's numpy versions must match exactly (tests/test_cbn_fast.py)."""

import math
from array import array

import numpy as np

SQRT2 = math.sqrt(2)


def mode_filter(val, w, h, k):
    """Majority of the 3x3 round each cell (ties keep their own value): smooths ragged region edges."""
    V = np.asarray(val, np.int64).reshape(h, w)
    out = V.copy()
    if h < 3 or w < 3:
        return out.reshape(-1)
    inner = V[1:-1, 1:-1]
    cnt = np.zeros((k,) + inner.shape, np.int64)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            q = V[1 + dy:h - 1 + dy, 1 + dx:w - 1 + dx]
            for c in range(k):
                cnt[c] += q == c
    top = cnt.max(axis=0)
    first = cnt.argmax(axis=0)                       # the first crayon with the most votes
    own = np.take_along_axis(cnt, np.clip(inner, 0, k - 1)[None], axis=0)[0]
    best = np.where(own == top, inner, first)
    out[1:-1, 1:-1] = np.where(inner < 0, inner, best)
    return out.reshape(-1)


# --- regions -------------------------------------------------------------------------------------------


def components(val, w, h):
    """Regions: 4-connected cells of equal value (-1 is nothing). (label, count); label -1 for nothing."""
    N = w * h
    label = [-1] * N
    n = 0
    for i in range(N):
        vi = val[i]
        if vi < 0 or label[i] >= 0:
            continue
        stack = [i]
        label[i] = n
        while stack:
            q = stack.pop()
            x = q % w
            if x > 0 and label[q - 1] < 0 and val[q - 1] == vi:
                label[q - 1] = n
                stack.append(q - 1)
            if x < w - 1 and label[q + 1] < 0 and val[q + 1] == vi:
                label[q + 1] = n
                stack.append(q + 1)
            if q >= w and label[q - w] < 0 and val[q - w] == vi:
                label[q - w] = n
                stack.append(q - w)
            if q < N - w and label[q + w] < 0 and val[q + w] == vi:
                label[q + w] = n
                stack.append(q + w)
        n += 1
    return label, n


def distance(label, w, h):
    """Distance from each region cell to the nearest cell outside its region (two chamfer passes),
    in 32-bit floats as index.html's Float32Array."""
    N = w * h
    d = array("f", bytes(4 * N))
    for i in range(N):
        l = label[i]
        if l < 0:
            continue
        x, y = i % w, i // w
        edge = (x == 0 or y == 0 or x == w - 1 or y == h - 1 or label[i - 1] != l or label[i + 1] != l
                or label[i - w] != l or label[i + w] != l)
        d[i] = 1 if edge else 1e9
    D = SQRT2
    for y in range(1, h):
        for i in range(y * w + 1, y * w + w - 1):
            if d[i] > 1:
                d[i] = min(d[i], d[i - 1] + 1, d[i - w] + 1, d[i - w - 1] + D, d[i - w + 1] + D)
    for y in range(h - 2, -1, -1):
        for i in range(y * w + w - 2, y * w, -1):
            if d[i] > 1:
                d[i] = min(d[i], d[i + 1] + 1, d[i + w] + 1, d[i + w + 1] + D, d[i + w - 1] + D)
    return d


def region_info(label, n, val, w, h):
    """Per region: value c, area, coordinate sums, deepest point (x, y) and its depth r, and whether it
    touches the edge."""
    d = distance(label, w, h)
    info = [{"c": -1, "area": 0, "sx": 0, "sy": 0, "x": 0, "y": 0, "r": 0.0, "edge": False} for _ in range(n)]
    for i in range(w * h):
        l = label[i]
        if l < 0:
            continue
        o, x, y = info[l], i % w, i // w
        o["c"] = val[i]
        o["area"] += 1
        o["sx"] += x
        o["sy"] += y
        if x == 0 or y == 0 or x == w - 1 or y == h - 1:
            o["edge"] = True
        if d[i] > o["r"]:
            o["r"], o["x"], o["y"] = d[i], x, y
    return info


def merge(val, w, h, min_r):
    """Each region too narrow for its number joins the neighbour it shares the most border with, until none
    are left (val is changed in place). (label, info)."""
    N = w * h
    for pas in range(13):
        label, n = components(val, w, h)
        info = region_info(label, n, val, w, h)
        small = [o["r"] < min_r for o in info]
        if pas == 12 or not any(small):
            return label, info
        border = {}
        for i in range(N):
            l = label[i]
            if l < 0 or not small[l]:
                continue
            x = i % w
            for j in ((i - 1) if x > 0 else -1, (i + 1) if x < w - 1 else -1, i - w, i + w):
                m = label[j] if 0 <= j < N else -1
                if m < 0 or m == l:
                    continue
                t = border.setdefault(l, {})
                t[m] = t.get(m, 0) + 1
        to = [-1] * n   # prefer a big neighbour, so two small ones don't just swap colours
        for l, t in border.items():
            best, score = -1, 0
            for m, k in t.items():
                sc = k * (0.3 if small[m] else 1)
                if sc > score:
                    score, best = sc, m
            if best >= 0:
                to[l] = info[best]["c"]
        changed = False
        for i in range(N):
            l = label[i]
            if l >= 0 and to[l] >= 0 and to[l] != val[i]:
                val[i] = to[l]
                changed = True
        if not changed:
            return label, info


def spots(label, info, w, h, min_r, gap):
    """Where numbers go: each region's deepest point, then more wherever it's still wide enough (ridge
    points of the distance map) and at least gap from its other numbers. [(region, x, y, depth)]."""
    d = distance(label, w, h)
    out = [[(rid, o["x"], o["y"], o["r"])] for rid, o in enumerate(info)]
    cand = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            i = y * w + x
            if label[i] < 0 or d[i] < min_r:
                continue
            if d[i] >= d[i - 1] and d[i] >= d[i + 1] and d[i] >= d[i - w] and d[i] >= d[i + w]:
                cand.append(i)
    cand.sort(key=lambda i: -d[i])   # stable, as JavaScript's sort
    g2 = gap * gap
    for i in cand:
        l, x, y = label[i], i % w, i // w
        lst = out[l]
        if all((q[1] - x) ** 2 + (q[2] - y) ** 2 >= g2 for q in lst):
            lst.append((l, x, y, d[i]))
    return [q for lst in out for q in lst]
