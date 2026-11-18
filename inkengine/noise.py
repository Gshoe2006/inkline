"""Smooth value noise, matching index.html's makeNoise exactly.

Four octaves of smoothly interpolated random values on a lattice. Contours draw lines of equal
height through it; flow lines follow it as a direction field.

index.html keeps the lattice values in a Float32Array, so each value is rounded to 32-bit float
once. Doing the same rounding here (and nothing else in single precision) gives the same numbers.
"""

import math
import struct

import numpy as np

from .rng import mulberry32, pick


def _f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


class Noise:
    def __init__(self, seed):
        r = mulberry32(seed)
        perm = list(range(256))
        vals = [_f32(r()) for _ in range(256)]
        for i in range(255, 0, -1):
            j = pick(r, i + 1)
            perm[i], perm[j] = perm[j], perm[i]
        self.perm, self.vals = perm, vals
        self._perm_np = np.array(perm, dtype=np.int64)
        self._vals_np = np.array(vals, dtype=np.float64)

    # --- one point at a time (flow lines) ---------------------------------------------------------
    def _n(self, x, y):
        perm, vals = self.perm, self.vals
        xi, yi = math.floor(x), math.floor(y)
        xf, yf = x - xi, y - yi
        u = xf * xf * (3 - 2 * xf)
        v = yf * yf * (3 - 2 * yf)
        a = vals[perm[(perm[xi & 255] + yi) & 255]]
        b = vals[perm[(perm[(xi + 1) & 255] + yi) & 255]]
        c = vals[perm[(perm[xi & 255] + yi + 1) & 255]]
        d = vals[perm[(perm[(xi + 1) & 255] + yi + 1) & 255]]
        return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v

    def __call__(self, x, y):
        s, amp, f, norm = 0.0, 0.5, 1, 0.0
        for o in range(4):
            s += amp * self._n(x * f + o * 17.3, y * f - o * 9.1)
            norm += amp
            amp *= 0.5
            f *= 2
        return s / norm

    # --- a whole grid at once (contours) ------------------------------------------------------------
    def _n_grid(self, x, y):
        perm, vals = self._perm_np, self._vals_np
        xi, yi = np.floor(x), np.floor(y)
        xf, yf = x - xi, y - yi
        xi, yi = xi.astype(np.int64), yi.astype(np.int64)
        u = xf * xf * (3 - 2 * xf)
        v = yf * yf * (3 - 2 * yf)
        lat = lambda X, Y: vals[perm[(perm[X & 255] + Y) & 255]]
        a, b, c, d = lat(xi, yi), lat(xi + 1, yi), lat(xi, yi + 1), lat(xi + 1, yi + 1)
        return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v

    def grid(self, x, y):
        """Noise at arrays of x and y (float64), the same numbers __call__ gives point by point."""
        s = np.zeros(np.broadcast(x, y).shape)
        amp, f, norm = 0.5, 1, 0.0
        for o in range(4):
            s = s + amp * self._n_grid(x * f + o * 17.3, y * f - o * 9.1)
            norm += amp
            amp *= 0.5
            f *= 2
        return s / norm
