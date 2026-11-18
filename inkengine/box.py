"""A rectangle on the page, in page pixels."""

from typing import NamedTuple


class Box(NamedTuple):
    x: float
    y: float
    w: float
    h: float

    def inset(self, p):
        return Box(self.x + p, self.y + p, self.w - 2 * p, self.h - 2 * p)
