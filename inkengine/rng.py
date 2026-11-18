"""Seeded random numbers that match index.html exactly.

index.html uses mulberry32 with JavaScript's 32-bit integer maths. Doing the same sums modulo 2**32
here gives the same numbers, so a seed saved by Inkline 2.x draws the same design in 3.0.
"""

_M = 0xFFFFFFFF


def _imul(a, b):
    """Math.imul: the low 32 bits of the product (signedness doesn't matter for the bits)."""
    return (a * b) & _M


def mulberry32(seed):
    """A function returning floats in [0, 1), like the JS mulberry32(seed)."""
    state = int(seed) & _M

    def rnd():
        nonlocal state
        state = (state + 0x6D2B79F5) & _M
        a = state
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & _M) ^ t
        return ((t ^ (t >> 14)) & _M) / 4294967296

    return rnd


def pick(rnd, n):
    """JavaScript's (rnd() * n) | 0 for positive n: an index in range(n)."""
    return int(rnd() * n)
