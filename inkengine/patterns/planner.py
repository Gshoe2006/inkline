"""Calendar: a month to hang up (the days in a grid, with room to write in each), or a weekly planner (a box for each
day with lines to write on), with a picture to colour above it if you like.

The month is chosen in the sidebar, or "Next month" (worked out when the page is drawn); a month with "The next
one" as its year is the next time that month comes round, this month counting as next. The dates come from Python's
calendar module. Weeks start on Monday, or on Sunday for English on Letter paper and for Portuguese (as American and
Brazilian calendars do), unless Week starts on says otherwise. Month and day names are in the current language.

The picture is one of the colouring patterns (a mandala, woven tiles, flow lines or contours) drawn with this page's
seed. It takes about a third of the page, so it's drawn at about a third of the page's complexity: a picture that small
at full detail would be too dense to colour. There's nothing to solve, so no answer page.

In a booklet, each page is the next month (a twelve-page booklet is a year): book.py gives each page its month.
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
FIRST_YEAR, LAST_YEAR = 1900, 2100   # a year outside these (0 among them) means "the next one"
AUTO_DATES = {"month": "Next month", "year": "The next one"}
MONTH_CHOICES = [(0, AUTO_DATES["month"])] + list(enumerate(MONTHS, 1))   # the sidebar's Month and Year


def today():
    return datetime.date.today()


def year_choices(now=None, keep=0):
    """The sidebar's years: "The next one", then this year and the ten after it, and keep (a year saved in a project
    or preset) if it isn't among them."""
    this = (now or today()).year
    years = list(range(this, this + 11))
    if FIRST_YEAR <= keep <= LAST_YEAR and keep not in years:
        years = sorted(years + [keep])
    return [(0, AUTO_DATES["year"])] + [(y, str(y)) for y in years]


def month_after(year, month, k):
    """The month k months after (year, month), as (year, month)."""
    n = year * 12 + month - 1 + k
    return n // 12, n % 12 + 1


def month_shown(settings, now=None):
    """(year, month) the page shows."""
    now = now or today()
    m = int(getattr(settings, "cal_month", 0) or 0)
    y = int(getattr(settings, "cal_year", 0) or 0)
    if not 1 <= m <= 12:   # next month
        return (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
    if FIRST_YEAR <= y <= LAST_YEAR:
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


def art_complexity(c):
    """The picture's complexity for the page's: about a third (1 to 3), as it's drawn so much smaller than a whole
    page: at a whole page's detail it would be too dense to colour."""
    return max(1, round(c * 0.3))


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
    out = {"first": first, "days": names, "lines": []}
    gap = dpi * 0.08
    spacing = dpi * 0.3   # about the lines of a school exercise book
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
        size = min(dpi * 0.18, w * 0.16) if across else min(dpi * 0.18, h * 0.3)
        pad = size * 0.5
        ctx.text_align, ctx.text_baseline = "left", "top"
        if across:   # the day's name across the top, the lines under it
            _fit_text(ctx, nm, w - size, size, 700)
            ctx.fill_text(nm, x + pad, y + pad * 0.8)
            lx0, lx1, ly0 = x + pad, x + w - pad, y + size * 1.6
        else:        # the day's name on the left, the lines filling the rest of the box
            label_w = min(w * 0.22, dpi * 1.4)
            _fit_text(ctx, nm, label_w - pad, size, 700)
            ctx.fill_text(nm, x + pad, y + pad * 0.8)
            lx0, lx1, ly0 = x + label_w, x + w - pad, y
        count = max(1, round((y + h - ly0) / spacing))
        step = (y + h - ly0) / (count + 0.35)   # evenly down the whole box, the last just above its bottom
        ctx.line_width = max(1.0, lw * 0.4)
        ctx.stroke_style = "#888"
        ctx.begin_path()
        for n in range(1, count + 1):
            ctx.move_to(lx0, ly0 + n * step)
            ctx.line_to(lx1, ly0 + n * step)
        ctx.stroke()
        ctx.stroke_style = "#000"
        out["lines"].append(count)
    return out


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, seed=0, **_opts):
    kind = getattr(settings, "cal_kind", "month")
    art = getattr(settings, "cal_art", "mandala")
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    body, art_box = box, None
    if art in BACKGROUNDS and art != "none":
        share = (0.36 if box.h >= box.w else 0.3) * (0.75 if kind == "week" else 1)
        ah = box.h * share
        from ..box import Box
        side = min(box.w, ah)
        art_box = Box(box.x + (box.w - side * (1.6 if art != "mandala" else 1)) / 2, box.y,
                      side * (1.6 if art != "mandala" else 1), ah) if box.w >= side * 1.6 else Box(box.x, box.y, box.w, ah)
        # a smaller picture: less detail, and its lines a little finer, so it stays open enough to colour
        _art(ctx, art_box, rnd, art_complexity(c), settings, lw * 0.8, dpi, seed, art)
        gap = dpi * 0.15
        body = Box(box.x, box.y + ah + gap, box.w, box.h - ah - gap)
    out = _week(ctx, body, settings, lw, dpi) if kind == "week" else _month(ctx, body, settings, lw, dpi)
    ctx.restore()
    out["kind"], out["art_box"] = kind, art_box
    return out
