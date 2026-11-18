"""Photos to black & white, ported from index.html (conversionInput, processPixels, convert and the
drawing for each style).

A photo is cropped (rotated in 90 degree steps, zoomed, panned, fitted inside or filling the box)
into a small work image, one pixel per dot, then turned into tones and drawn in one of these styles:

  fs         smooth dither (Floyd-Steinberg)        halftone   dots that grow with the darkness
  atkinson   crisp dither (Atkinson)                engrave    wavy lines that swell where it's dark
  bayer      pattern dither (ordered)               stipple    same-size dots, packed closer where dark
  threshold  solid black & white                    nono       a nonogram puzzle that reveals the photo
  line       line drawing (difference of Gaussians, for colouring)

Colour by number comes in a later step.

From the work image on, this matches index.html exactly: tones are kept in 32-bit floats where the
JavaScript keeps them in Float32Arrays (numpy float32 and array('f') round the same way), and the
error-diffusion dithers visit pixels in the same serpentine order. tests/test_photo.py feeds the
JavaScript's own work images through and compares. The cropping itself is done by Qt's scaler, which
resamples a little differently from Chromium's, so a whole photo can differ from 2.x by the odd dot.

Dithers spread each pixel's error to the next, so they run pixel by pixel in plain Python: about
1.6 s for a Letter page at 300 dpi and the default dot size. Previews draw at screen resolution.
"""

import itertools
import math
from array import array
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter

from .patterns import nonogram
from .qt import ensure_app

STYLES = ["fs", "atkinson", "bayer", "halftone", "engrave", "stipple", "nono", "threshold", "line"]
STYLE_NAMES = {"fs": "Dither: smooth (Floyd–Steinberg)", "atkinson": "Dither: crisp (Atkinson)",
               "bayer": "Dither: pattern (ordered)", "halftone": "Halftone dots", "engrave": "Engraving lines",
               "stipple": "Stippling dots", "cbn": "Colour by number (with a crayon key)",
               "nono": "Nonogram puzzle (picture logic)", "threshold": "Solid black & white",
               "line": "Line drawing (colouring page)"}
VECTOR_STYLES = {"engrave", "stipple", "nono"}   # drawn as shapes, so they save as real vector SVG


def _js_round(x):
    return int(math.floor(x + 0.5))


def _f32(x):
    return float(np.float32(x))


# --- tables -------------------------------------------------------------------------------------------

def _bayer():
    m = [[0, 2], [3, 1]]
    b, n = m, 2
    while n < 8:
        b = [[4 * b[y % n][x % n] + m[y // n][x // n] for x in range(n * 2)] for y in range(n * 2)]
        n *= 2
    return b


BAYER = _bayer()


def _halftone_r():
    """Dot radius (in cell widths) whose inked area matches each grey level. A dot covers pi r^2 of its
    cell until it touches the edges (r = 0.5); after that the parts beyond the cell are cut off (and made
    up by the neighbours' overhang), until r = 0.707 covers the cell fully."""
    def cover(r):
        if r <= 0.5:
            return math.pi * r * r
        return math.pi * r * r - 4 * (r * r * math.acos(0.5 / r) - 0.5 * math.sqrt(r * r - 0.25))
    t = []
    for i in range(256):
        lo, hi = 0.0, math.sqrt(0.5)
        for _ in range(40):
            m = (lo + hi) / 2
            if cover(m) < i / 255:
                lo = m
            else:
                hi = m
        t.append(_f32(hi))
    return t


HALFTONE_R = _halftone_r()

ENGRAVE_PITCH, ENGRAVE_STEP = 4, 2
STIPPLE_R, STIPPLE_JITTER, STIPPLE_WOBBLE = 0.75, 0.3, 0.15
# Ink coverage measured by simulation at 0/32 .. 32/32 of sites dotted (dots overlap where it's dark).
STIPPLE_COVER = [0, .055, .11, .165, .22, .275, .329, .381, .431, .476, .517, .559, .598, .634, .672, .713, .756,
                 .767, .787, .809, .829, .848, .867, .883, .897, .91, .924, .935, .946, .958, .97, .981, .991]


def _stipple_f():
    """Darkness 0..255 -> share of sites to dot (the curve made never-falling so it inverts)."""
    c = list(itertools.accumulate(STIPPLE_COVER, max))
    n, t = len(c) - 1, []
    for i in range(256):
        d = min(i / 255, c[n])
        k = 1
        while k < n and c[k] < d:
            k += 1
        t.append(_f32((k - 1 + ((d - c[k - 1]) / (c[k] - c[k - 1]) if c[k] > c[k - 1] else 1)) / n))
    t[255] = 1.0
    return t


STIPPLE_F = _stipple_f()


def _imul(a, b):
    return (a * b) & 0xFFFFFFFF


def stipple_nudge(i, k):
    """A fixed pseudo-random number in [-1, 1) for site i, as index.html's stippleNudge."""
    h = _imul(i, 374761393) ^ _imul(k, 668265263)
    h = _imul(h ^ (h >> 13), 1274126177)
    h ^= h >> 16
    return h / 2147483648 - 1


# --- photos and cropping ------------------------------------------------------------------------------

_ids = itertools.count(1)


@dataclass
class Photo:
    """A picture and its crop. rot is 0/90/180/270; zoom 100..400 (%); panx, pany -100..100 (%) of the
    overhang. neutral pictures (the test page's grey ramps) stretch to fill and ignore tone controls."""
    image: QImage
    rot: int = 0
    zoom: float = 100
    panx: float = 0
    pany: float = 0
    neutral: bool = False
    name: str = ""
    id: int = field(default_factory=lambda: next(_ids))


def load_photo(path):
    ensure_app()
    img = QImage(str(path))
    if img.isNull():
        raise OSError(f"couldn't read {path} as a picture")
    return Photo(img.convertToFormat(QImage.Format.Format_ARGB32), name=str(path))


def grey_ramp():
    """White on the left to black on the right, as a neutral photo for the test page."""
    ensure_app()
    img = QImage(1024, 8, QImage.Format.Format_ARGB32)
    for x in range(1024):
        v = _js_round(255 * (1 - x / 1023))
        for y in range(8):
            img.setPixel(x, y, 0xFF000000 | (v << 16) | (v << 8) | v)
    return Photo(img, neutral=True, name="ramp")


def conversion_input(box, cell, style, photo, s):
    """The cropped photo drawn into a work image of (box size / cell) pixels: (ww, wh, RGBA bytes, params)."""
    ensure_app()
    ww, wh = max(1, _js_round(box.w / cell)), max(1, _js_round(box.h / cell))
    work = QImage(ww, wh, QImage.Format.Format_RGBA8888_Premultiplied)
    work.fill(Qt.GlobalColor.transparent)
    p = QPainter(work)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    img = photo.image
    iw, ih, rot = img.width(), img.height(), photo.rot % 360
    rw, rh = (ih, iw) if rot % 180 else (iw, ih)
    cover = s.fit == "cover"
    sc = (max(ww / rw, wh / rh) if cover else min(ww / rw, wh / rh)) * photo.zoom / 100
    ex, ey = max(0, rw * sc - ww) / 2, max(0, rh * sc - wh) / 2   # overhang on each side
    if photo.neutral:
        p.drawImage(QRectF(0, 0, ww, wh), img)
    else:
        p.translate(ww / 2 + photo.panx / 100 * ex, wh / 2 + photo.pany / 100 * ey)
        p.rotate(rot)
        p.drawImage(QRectF(-iw * sc / 2, -ih * sc / 2, iw * sc, ih * sc), img)
    p.end()
    work = work.convertToFormat(QImage.Format.Format_RGBA8888)
    data = np.frombuffer(work.constBits(), np.uint8, work.sizeInBytes()).reshape(wh, work.bytesPerLine())[:, :ww * 4]
    neutral = photo.neutral
    params = {"style": style, "br": 0 if neutral else s.brightness * 1.28, "ct": 1 if neutral else s.contrast / 100,
              "t": 128 if neutral else s.threshold, "inv": (not neutral) and s.invert, "k": s.pcbn_colours,
              "n": s.pnono_size}
    # copy: without padding at the row ends the slice is a view of the QImage, which Qt frees on return
    return ww, wh, data.copy().reshape(-1), params, (ex * cell, ey * cell)


# --- the pixel work -----------------------------------------------------------------------------------

def gauss_blur(src, w, h, sigma):
    """Separable Gaussian blur with clamped edges, summing in index.html's order (float32 results)."""
    r = math.ceil(sigma * 3)
    ex = [math.exp(-(i * i) / (2 * sigma * sigma)) for i in range(-r, r + 1)]
    total = 0.0
    for e in ex:
        total += e
    k = (np.array(ex, np.float32).astype(np.float64) / total).astype(np.float32).astype(np.float64)
    img = src.reshape(h, w).astype(np.float64)
    cols = np.arange(w)
    a = np.zeros((h, w))
    for n, i in enumerate(range(-r, r + 1)):
        a = a + img[:, np.clip(cols + i, 0, w - 1)] * k[n]
    tmp = a.astype(np.float32).astype(np.float64)
    rows = np.arange(h)
    a = np.zeros((h, w))
    for n, i in enumerate(range(-r, r + 1)):
        a = a + tmp[np.clip(rows + i, 0, h - 1), :] * k[n]
    return a.astype(np.float32).reshape(-1)


def despeckle(img, w, h, min_size):
    """Turn black blobs smaller than min_size pixels (8-connected) white, in place (img: bytearray)."""
    seen = bytearray(w * h)
    for i in range(w * h):
        if img[i] != 0 or seen[i]:
            continue
        stack, blob = [i], []
        seen[i] = 1
        while stack:
            q = stack.pop()
            blob.append(q)
            x, y = q % w, q // w
            for dy in (-1, 0, 1):
                Y = y + dy
                if Y < 0 or Y >= h:
                    continue
                for dx in (-1, 0, 1):
                    X = x + dx
                    if X < 0 or X >= w:
                        continue
                    j = Y * w + X
                    if img[j] == 0 and not seen[j]:
                        seen[j] = 1
                        stack.append(j)
        if len(blob) < min_size:
            for j in blob:
                img[j] = 255


def _error_diffusion(lum, mask, ww, wh, t, atkinson):
    L = array("f", lum.tobytes())   # 32-bit floats, rounding on every update as a Float32Array does
    out = bytearray(b"\xff") * (ww * wh)
    for y in range(wh):
        s = -1 if y & 1 else 1      # serpentine scan avoids directional streaks
        row = y * ww
        for k in range(ww):
            x = k if s > 0 else ww - 1 - k
            i = row + x
            if not mask[i]:         # empty space round the photo takes no part in diffusion
                continue
            v = L[i]
            o = 0 if v < t else 255
            e = v - o
            out[i] = o
            if atkinson:
                w8 = e * 0.125
                for dx, dy in ((1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)):
                    X, Y = x + dx * s, y + dy
                    if 0 <= X < ww and Y < wh:
                        j = Y * ww + X
                        if mask[j]:
                            L[j] += w8
            else:
                for dx, dy, wt in ((1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)):
                    X, Y = x + dx * s, y + dy
                    if 0 <= X < ww and Y < wh:
                        j = Y * ww + X
                        if mask[j]:
                            L[j] += e * wt
    return out


def process_pixels(D, ww, wh, p):
    """Tones, mask and the black & white result for one work image (D: RGBA bytes). Returns a dict with
    lum (float32), mask (uint8), grey (the 1-bit image as 0/255 bytes, for the dither styles) and nono."""
    N = ww * wh
    D = np.asarray(D, np.uint8).reshape(N, 4).astype(np.float64)
    a = D[:, 3] / 255
    mask = (a > 0.02).astype(np.uint8)
    y = (0.2126 * D[:, 0] + 0.7152 * D[:, 1] + 0.0722 * D[:, 2]) * a + 255 * (1 - a)
    # clamp to what paper can show: contrast can push white past 255, and error diffusion would carry it on
    lum = np.minimum(255, np.maximum(0, (y - 128) * p["ct"] + 128 + p["br"])).astype(np.float32)
    style, t, inv = p["style"], p["t"], p["inv"]
    out, nono = None, None
    if style == "threshold":
        out = bytearray(np.where(lum.astype(np.float64) < t, 0, 255).astype(np.uint8).tobytes())
    elif style == "bayer":
        b = np.array(BAYER, np.float64)
        ys, xs = np.divmod(np.arange(N), ww)
        limit = (b[ys & 7, xs & 7] + 0.5) * 4 + (t - 128)
        out = bytearray(np.where(lum.astype(np.float64) < limit, 0, 255).astype(np.uint8).tobytes())
    elif style in ("fs", "atkinson"):
        out = _error_diffusion(lum, mask, ww, wh, t, style == "atkinson")
    elif style == "line":
        # Difference of Gaussians: ink where a lightly blurred copy is darker than a heavily blurred one.
        # That traces the dark side of each edge as a stroke, while grain (gone in both blurs) stays white.
        sigma = max(0.8, min(ww, wh) / 700)
        g1, g2 = gauss_blur(lum, ww, wh, sigma), gauss_blur(lum, ww, wh, sigma * 1.6)
        thr = (260 - t) / 60
        ink = (mask == 1) & (g1.astype(np.float64) - g2.astype(np.float64) < -thr)
        out = bytearray(np.where(ink, 0, 255).astype(np.uint8).tobytes())
        despeckle(out, ww, wh, max(12, _js_round(N / 40000)))
    elif style == "nono":
        nono = _nono_picture(lum, mask, ww, wh, p)
    grey = None
    if out is not None:
        o = np.frombuffer(bytes(out), np.uint8).copy()
        o[mask == 0] = 255
        if inv:
            o[mask == 1] = 255 - o[mask == 1]
        grey = o
    return {"lum": lum, "mask": mask, "grey": grey, "nono": nono}


def _nono_picture(lum, mask, ww, wh, p):
    """The picture's extent split into exactly n squares across, each the average tone under it, shaded
    if darker than Threshold, then made solvable by from_picture()."""
    n, t, inv = p["n"], p["t"], p["inv"]
    ys, xs = np.nonzero(mask.reshape(wh, ww))
    if not len(xs):
        return None
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    bw = (x1 - x0 + 1) / n
    gw, gh = n, max(1, min(45, _js_round((y1 - y0 + 1) / bw)))
    bh = (y1 - y0 + 1) / gh
    L = lum.astype(np.float64)
    tone, pic = [0.0] * (gw * gh), [0] * (gw * gh)
    for gy in range(gh):
        for gx in range(gw):
            total, cnt = 0.0, 0
            for yy in range(math.floor(y0 + gy * bh), math.floor(y0 + (gy + 1) * bh)):
                for xx in range(math.floor(x0 + gx * bw), math.floor(x0 + (gx + 1) * bw)):
                    i = yy * ww + xx
                    if mask[i]:
                        total += 255 - L[i] if inv else L[i]
                        cnt += 1
            j = gy * gw + gx
            tone[j] = _f32(total / cnt) if cnt else 255.0
            pic[j] = 1 if tone[j] < t else 0
    return from_picture(pic, tone, gw, gh, t)


def from_picture(pic0, lum, w, h, t):
    """A black & white grid as a fair nonogram. While logic alone can't finish it, flip the undecided
    square whose tone is nearest the threshold (the least visible change), each square at most once; if
    that isn't enough, print some undecided shaded squares already filled in to start from."""
    pic, flipped = list(pic0), set()
    while True:
        rows, cols = nonogram.clues(pic, w, h)
        sol = nonogram.solve(rows, cols)
        open_ = [i for i, x in enumerate(sol) if x < 0 and i not in flipped]
        if all(x >= 0 for x in sol):
            return {"w": w, "h": h, "pic": pic, "rows": rows, "cols": cols, "givens": None, "flips": len(flipped)}
        if not open_ or len(flipped) >= 3 * max(w, h):
            start, givens = [-1] * (w * h), [0] * (w * h)
            while True:
                s2 = nonogram.solve(rows, cols, start)
                left = [i for i, x in enumerate(s2) if x < 0]
                if not left:
                    return {"w": w, "h": h, "pic": pic, "rows": rows, "cols": cols, "givens": givens, "flips": len(flipped)}
                i = next((j for j in left if pic[j]), left[0])   # an ambiguity always involves shaded squares
                start[i] = pic[i]
                if pic[i]:
                    givens[i] = 1
        best = open_[0]
        for i in open_:
            if abs(lum[i] - t) < abs(lum[best] - t):
                best = i
        pic[best] ^= 1
        flipped.add(best)


# --- a converted image, cached ------------------------------------------------------------------------

@dataclass
class Conversion:
    ww: int
    wh: int
    lum: np.ndarray
    mask: np.ndarray
    grey: object = None          # 0/255 bytes for the dither styles
    nono: dict = None
    overhang: tuple = (0, 0)     # page pixels the crop overhangs on each side (for drag-to-pan)
    stipple: dict = field(default_factory=dict)
    _image: QImage = None

    def image(self):
        """The 1-bit result as a QImage (dither styles)."""
        if self._image is None and self.grey is not None:
            buf = np.ascontiguousarray(self.grey, np.uint8).tobytes()
            self._image = QImage(buf, self.ww, self.wh, self.ww, QImage.Format.Format_Grayscale8).copy()
        return self._image


CACHE_PIXELS = 40_000_000
_cache = {}


def _cache_get(key):
    e = _cache.pop(key, None)
    if e is not None:
        _cache[key] = e          # most recently used goes last
    return e


def _cache_put(key, e):
    _cache[key] = e
    total = sum(x.ww * x.wh for x in _cache.values())
    for k in list(_cache):
        if total <= CACHE_PIXELS or len(_cache) <= 1:
            break
        total -= _cache[k].ww * _cache[k].wh
        del _cache[k]
    return e


def clear_cache():
    _cache.clear()


def conversion(box, cell, style, photo, s):
    key = (photo.id, box.w, box.h, cell, style, s.brightness, s.contrast, s.threshold, s.fit, s.invert,
           s.pnono_size if style == "nono" else "", photo.rot, photo.zoom, photo.panx, photo.pany)
    e = _cache_get(key)
    if e is None:
        ww, wh, data, params, overhang = conversion_input(box, cell, style, photo, s)
        r = process_pixels(data, ww, wh, params)
        e = _cache_put(key, Conversion(ww, wh, r["lum"], r["mask"], r["grey"], r["nono"], overhang))
    return e


# --- drawing ------------------------------------------------------------------------------------------

def cell_size(style, dot, box, s, dpi):
    if style == "halftone":
        c = dot * 5
    elif style == "stipple":
        c = dot * 2
    elif style == "nono":
        c = box.w / (s.pnono_size * 8)
    else:
        c = dot
    return max(1, c)


def convert(ctx, box, dpi, s, photo, style=None, dot=None, view=None):
    """Draw the converted photo into box. style and dot override the settings (the test page shows them
    all); view (a poster sheet's area) lets the dot and line styles skip what's off that sheet."""
    if photo is None:
        ctx.fill_style, ctx.text_align = "#888", "center"
        ctx.set_font(box.w / 28, 400)
        ctx.fill_text("Open or drop an image to convert it", box.x + box.w / 2, box.y + box.h / 2)
        return None
    style = style or s.style
    if style == "cbn":
        raise NotImplementedError("colour by number isn't ported to the Python engine yet")
    dot = (s.dot if dot is None else dot) * (dpi / s.dpi)   # dot size stays physical at preview resolution
    e = conversion(box, cell_size(style, dot, box, s, dpi), style, photo, s)
    inv = (not photo.neutral) and s.invert
    if style == "engrave":
        _draw_engraving(ctx, box, e, inv, view)
    elif style == "stipple":
        _draw_stipple(ctx, box, e, inv, view)
    elif style == "halftone":
        _draw_halftone(ctx, box, e, inv, view)
    elif style == "nono":
        if e.nono:
            nonogram.draw_nonogram(ctx, box, dpi, s.weight * dpi / 150, e.nono, s.pnono_answer)
    else:
        ctx.draw_image(e.image(), box.x, box.y, box.w, box.h)
    return e


def _darkness(lum_value, inv):
    d = 1 - min(255.0, max(0.0, lum_value)) / 255
    return 1 - d if inv else d


def _draw_halftone(ctx, box, e, inv, view):
    ww, wh, lum, mask = e.ww, e.wh, e.lum.astype(np.float64), e.mask
    sx, sy = box.w / ww, box.h / wh
    side = math.sqrt(sx * sy)
    x0, x1, y0, y1 = 0, ww, 0, wh
    if view:
        x0 = max(0, math.floor((view.x - box.x) / sx) - 1)
        x1 = min(ww, math.ceil((view.x + view.w - box.x) / sx) + 1)
        y0 = max(0, math.floor((view.y - box.y) / sy) - 1)
        y1 = min(wh, math.ceil((view.y + view.h - box.y) / sy) + 1)
    ctx.save()
    ctx.begin_path()
    ctx.rect(box.x, box.y, box.w, box.h)
    ctx.clip()
    ctx.fill_style = "#000"
    for y in range(y0, y1):
        for x in range(x0, x1):
            i = y * ww + x
            if not mask[i]:
                continue
            dark = _darkness(lum[i], inv)
            if dark < 0.03:
                continue
            ctx.begin_path()
            ctx.arc(box.x + (x + 0.5) * sx, box.y + (y + 0.5) * sy, side * HALFTONE_R[_js_round(dark * 255)], 0, math.pi * 2)
            ctx.fill()
    ctx.restore()


def _draw_engraving(ctx, box, e, inv, view):
    """Parallel wavy lines, ENGRAVE_PITCH work pixels apart, that swell where the photo is dark; each
    line's half-width is darkness x pitch / 2, so the ink covers exactly that share of its band."""
    ww, wh, lum, mask = e.ww, e.wh, e.lum.astype(np.float64), e.mask
    sx, sy, P = box.w / ww, box.h / wh, ENGRAVE_PITCH
    X = lambda x: box.x + x * sx
    Y = lambda y: box.y + y * sy
    ctx.save()
    ctx.begin_path()
    ctx.rect(box.x, box.y, box.w, box.h)
    ctx.clip()
    ctx.fill_style = "#000"

    def flush(seg):   # one stretch of line: along its top edge, back along its bottom edge
        if len(seg) < 2:
            return
        ctx.begin_path()
        ctx.move_to(X(seg[0][0]), Y(seg[0][1] - seg[0][2]))
        for x, cy, hw in seg:
            ctx.line_to(X(x), Y(cy - hw))
        for x, cy, hw in reversed(seg):
            ctx.line_to(X(x), Y(cy + hw))
        ctx.close_path()
        ctx.fill()

    band = 0
    while band * P < wh:
        y0, y1 = band * P, min(wh, band * P + P)
        mid = (y0 + y1) / 2
        if view and (Y(y1) < view.y or Y(y0) > view.y + view.h):   # poster sheets skip lines off the sheet
            band += 1
            continue
        seg = []
        for x in range(0, ww + 1, ENGRAVE_STEP):
            xi = min(ww - 1, x)
            dark, n = 0.0, 0
            for yy in range(y0, y1):
                i = yy * ww + xi
                if mask[i]:
                    dark += _darkness(lum[i], inv)
                n += 1
            hw = (dark / n) * (y1 - y0) / 2
            cy = mid + math.sin(x * 0.11 + band * 0.04) * P * 0.22   # the same phase on neighbouring lines
            if hw > 0.04:
                seg.append((x, cy, hw))
            else:
                flush(seg)
                seg = []
        flush(seg)
        band += 1
    ctx.restore()


def stipple_sites(e, inv):
    """The dotted sites (sorted work-pixel indexes), worked out once per conversion: error diffusion
    picks them, with a small wobble in its threshold to break up worms and streaks."""
    if inv in e.stipple:
        return e.stipple[inv]
    ww, wh, mask = e.ww, e.wh, e.mask
    lum = e.lum.astype(np.float64)
    L = array("f", bytes(4 * ww * wh))
    for i in np.nonzero(mask)[0].tolist():
        L[i] = STIPPLE_F[_js_round(_darkness(lum[i], inv) * 255)]
    sites = []
    for y in range(wh):
        s = -1 if y & 1 else 1
        for k in range(ww):
            x = k if s > 0 else ww - 1 - k
            i = y * ww + x
            if not mask[i]:
                continue
            o = 1 if L[i] >= 0.5 + STIPPLE_WOBBLE * stipple_nudge(i, 3) else 0
            err = L[i] - o
            if o:
                sites.append(i)
            for dx, dy, wt in ((1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)):
                X2, Y2 = x + dx * s, y + dy
                if 0 <= X2 < ww and Y2 < wh and mask[Y2 * ww + X2]:
                    L[Y2 * ww + X2] += err * wt
    sites.sort()
    e.stipple[inv] = sites
    return sites


def _draw_stipple(ctx, box, e, inv, view):
    ww, sites = e.ww, stipple_sites(e, inv)
    sx, sy = box.w / ww, box.h / e.wh
    r, J = STIPPLE_R * math.sqrt(sx * sy), STIPPLE_JITTER
    ctx.save()
    ctx.begin_path()
    ctx.rect(box.x, box.y, box.w, box.h)
    ctx.clip()
    ctx.fill_style = "#000"
    row = -1
    for i in sites:   # one filled shape per row of dots keeps the SVG small
        y, x = divmod(i, ww)
        if y != row:
            if row >= 0:
                ctx.fill()
            ctx.begin_path()
            row = y
        cx = box.x + (x + 0.5 + stipple_nudge(i, 1) * J) * sx
        cy = box.y + (y + 0.5 + stipple_nudge(i, 2) * J) * sy
        if view and (cx + r < view.x or cx - r > view.x + view.w or cy + r < view.y or cy - r > view.y + view.h):
            continue
        ctx.move_to(cx + r, cy)
        ctx.arc(cx, cy, r, 0, math.pi * 2)
    if row >= 0:
        ctx.fill()
    ctx.restore()
