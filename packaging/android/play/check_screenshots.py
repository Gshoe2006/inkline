"""Checks screenshots (the .png files in a folder) fit Google Play's rules: each side 320 to 3840 px, and the long
side at most twice the short one. Only the standard library, so it runs anywhere (the emulator job has no Qt).

    python3 packaging/android/play/check_screenshots.py DIR
"""

import os
import struct
import sys


def png_info(path):
    """(width, height, has_alpha) from a PNG's header."""
    with open(path, "rb") as f:
        head = f.read(26)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise ValueError(f"{path} isn't a PNG")
    w, h, _depth, color = struct.unpack(">IIBB", head[16:26])
    return w, h, color in (4, 6)


def problem(w, h):
    """Why Play would refuse a w×h screenshot, or ""."""
    if min(w, h) < 320 or max(w, h) > 3840:
        return f"{w}x{h}: each side must be 320 to 3840 px"
    if max(w, h) > 2 * min(w, h):
        return f"{w}x{h}: the long side is more than twice the short one"
    return ""


def check(folder, out=print):
    """The screenshots Play wouldn't take (or "(none)" if there are no screenshots)."""
    names = sorted(n for n in os.listdir(folder) if n.lower().endswith(".png"))
    bad = []
    for n in names:
        w, h, _alpha = png_info(os.path.join(folder, n))
        why = problem(w, h)
        out(f"{n}: {w}x{h} {why or 'ok'}")
        if why:
            bad.append(n)
    return bad if names else ["(none)"]


def main(argv):
    if len(argv) != 1:
        raise SystemExit(__doc__)
    bad = check(argv[0])
    if bad:
        raise SystemExit("check_screenshots: Play won't take " + ", ".join(bad))


if __name__ == "__main__":
    main(sys.argv[1:])
