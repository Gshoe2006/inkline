"""Calendar: a month to hang up (the days in a grid, with room to write in each), or a weekly planner (a box for each
day with lines to write on), with a picture to colour above it if you like.

The month is chosen in the sidebar, or "Next month" (worked out when the page is drawn); a month with "The next
one" as its year is the next time that month comes round, this month counting as next. The dates come from Python's
calendar module. Weeks start on Monday, or on Sunday for English on Letter paper and for Portuguese (as American and
Brazilian calendars do), unless Week starts on says otherwise. Month and day names are in the current language.

The picture is one of the colouring patterns (a mandala, woven tiles, flow lines or contours) drawn with this page's
seed and complexity. There's nothing to solve, so no answer page.
"""

import calendar
import datetime

from .. import i18n
from ..i18n import tr

KINDS = {"month": "Month calendar", "week": "Weekly planner"}
BACKGROUNDS = {"mandala": "A mandala to colour", "truchet": "Woven tiles to colour", "flow": "Flow lines to colour",
               "contour": "Contours to colour", "none": "No picture"}
WEEK_STARTS = {"auto": "As usual for the language", "mon": "Monday", "sun": "Sunday"}
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
SHORT_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
YEARS = range(2025, 2041)
AUTO_DATES = {"month": "Next month", "year": "The next one"}
MONTH_CHOICES = [(0, AUTO_DATES["month"])] + list(enumerate(MONTHS, 1))   # the sidebar's Month and Year
YEAR_CHOICES = [(0, AUTO_DATES["year"])] + [(y, str(y)) for y in YEARS]


def today():
    return datetime.date.today()


def month_shown(settings, now=None):
    """(year, month) the page shows."""
    now = now or today()
    m = int(getattr(settings, "cal_month", 0) or 0)
    y = int(getattr(settings, "cal_year", 0) or 0)
    if not 1 <= m <= 12:   # next month
        return (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
    if y in YEARS:
        return y, m
    return (now.year, m) if m >= now.month else (now.year + 1, m)


def first_weekday(settings):
    """0 when weeks start on Monday, 6 on Sunday."""
    start = getattr(settings, "cal_start", "auto")
    if start == "mon":
        return 0
    if start == "sun":
        return 6
    sunday = i18n.LANG == "pt" or (i18n.LANG == "en" and getattr(settings, "paper", "letter") == "letter")
    return 6 if sunday else 0


def weeks(year, month, first=0):
    """The month's weeks, each 7 day numbers (0 for days of the months either side)."""
    return calendar.Calendar(firstweekday=first).monthdayscalendar(year, month)


def day_names(first, short=False):
    names = SHORT_DAYS if short else WEEKDAYS
    return [tr(names[(first + k) % 7]) for k in range(7)]


def title(year, month):
    return tr("{month} {year}").format(month=tr(MONTHS[month - 1]), year=year)


def _art(ctx, box, rnd, c, settings, lw, dpi, seed, art):
    from . import GENERATORS
    ctx.save()
    ctx.stroke_style = ctx.fill_style = "#000"
    ctx.line_width = lw
    GENERATORS[art](ctx, box, rnd, c, settings, lw=lw, seed=seed, dpi=dpi)
    ctx.restore()


def _fit_text(ctx, text, w, fs, weight):
    ctx.set_font(fs, weight)
    wide = ctx.measure_text(text)
    if wide > w:
        ctx.set_font(fs * w / wide, weight)


def _month(ctx, box, settings, lw, dpi):
    year, month = month_shown(settings)
    first = first_weekday(settings)
    rows = weeks(year, month, first)
    head = min(box.h * 0.12, dpi * 0.55)
    ctx.text_align, ctx.text_baseline = "center", "middle"
    _fit_text(ctx, title(year, month), box.w, head * 0.7, 800)
    ctx.fill_text(title(year, month), box.x + box.w / 2, box.y + head * 0.45)
    cw = box.w / 7
    names_h = min(head * 0.5, dpi * 0.3)
    gy = box.y + head
    short = cw < dpi * 1.15
    names = day_names(first, short)
    size = min(names_h * 0.6, dpi * 0.16)
    longest = max(names, key=len)
    ctx.set_font(size, 700)
    if ctx.measure_text(longest) > cw * 0.9:
        size *= cw * 0.9 / ctx.measure_text(longest)
    for k, nm in enumerate(names):
        ctx.set_font(size, 700)
        ctx.fill_text(nm, box.x + (k + 0.5) * cw, gy + names_h / 2)
    gy += names_h
    rh = (box.y + box.h - gy) / len(rows)
    ctx.line_width = max(1.0, lw * 0.6)
    ctx.begin_path()
    for r in range(1, len(rows)):
        ctx.move_to(box.x, gy + r * rh)
        ctx.line_to(box.x + box.w, gy + r * rh)
    for k in range(1, 7):
        ctx.move_to(box.x + k * cw, gy)
        ctx.line_to(box.x + k * cw, gy + len(rows) * rh)
    ctx.stroke()
    ctx.line_width = max(1.5, lw * 1.2)
    ctx.stroke_rect(box.x, gy, box.w, len(rows) * rh)
    ctx.text_align, ctx.text_baseline = "left", "top"
    ctx.set_font(min(rh * 0.28, cw * 0.28, dpi * 0.2), 600)
    pad = min(rh, cw) * 0.08
    for r, week in enumerate(rows):
        for k, day in enumerate(week):
            if day:
                ctx.fill_text(str(day), box.x + k * cw + pad, gy + r * rh + pad)
    return {"year": year, "month": month, "first": first, "weeks": rows}


def _week(ctx, box, settings, lw, dpi):
    first = first_weekday(settings)
    names = day_names(first)
    head = min(box.h * 0.1, dpi * 0.5)
    ctx.text_align, ctx.text_baseline = "left", "middle"
    label = tr("Week of")
    _fit_text(ctx, label, box.w * 0.4, head * 0.55, 800)
    ctx.fill_text(label, box.x, box.y + head * 0.45)
    lx = box.x + ctx.measure_text(label) + head * 0.3
    ctx.line_width = max(1.0, lw * 0.6)
    ctx.begin_path()
    ctx.move_to(lx, box.y + head * 0.7)
    ctx.line_to(box.x + box.w * 0.7, box.y + head * 0.7)
    ctx.stroke()
    top = box.y + head
    across = box.w > box.h * 1.15   # landscape: the days side by side, lines down each
    out = {"first": first, "days": names}
    gap = dpi * 0.08
    for k, nm in enumerate(names):
        if across:
            w = (box.w - gap * 6) / 7
            x, y, h = box.x + k * (w + gap), top, box.y + box.h - top
        else:
            w = box.w
            h = (box.y + box.h - top - gap * 6) / 7
            x, y = box.x, top + k * (h + gap)
        ctx.line_width = max(1.5, lw * 1.0)
        ctx.stroke_rect(x, y, w, h)
        size = min(dpi * 0.18, h * 0.22, w * 0.16)
        ctx.text_align, ctx.text_baseline = "left", "top"
        _fit_text(ctx, nm, w - size, size, 700)
        ctx.fill_text(nm, x + size * 0.5, y + size * 0.4)
        line_gap = dpi * 0.3
        ctx.line_width = max(1.0, lw * 0.4)
        ctx.stroke_style = "#888"
        ctx.begin_path()
        ly = y + size * 1.6 + line_gap
        while ly < y + h - line_gap * 0.4:
            ctx.move_to(x + size * 0.5, ly)
            ctx.line_to(x + w - size * 0.5, ly)
            ly += line_gap
        ctx.stroke()
        ctx.stroke_style = "#000"
    return out


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, seed=0, **_opts):
    kind = getattr(settings, "cal_kind", "month")
    art = getattr(settings, "cal_art", "mandala")
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    body = box
    if art in BACKGROUNDS and art != "none":
        share = 0.36 if box.h >= box.w else 0.3
        ah = box.h * share
        from ..box import Box
        side = min(box.w, ah)
        art_box = Box(box.x + (box.w - side * (1.6 if art != "mandala" else 1)) / 2, box.y,
                      side * (1.6 if art != "mandala" else 1), ah) if box.w >= side * 1.6 else Box(box.x, box.y, box.w, ah)
        _art(ctx, art_box, rnd, c, settings, lw, dpi, seed, art)
        gap = dpi * 0.15
        body = Box(box.x, box.y + ah + gap, box.w, box.h - ah - gap)
    out = _week(ctx, body, settings, lw, dpi) if kind == "week" else _month(ctx, body, settings, lw, dpi)
    ctx.restore()
    out["kind"] = kind
    return out
