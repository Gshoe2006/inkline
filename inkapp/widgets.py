"""The sidebar's shared pieces, styled only through inkapp/theme (by the "role" property).

Section     an uppercase heading over a column of rows (2.x's fieldset and legend)
OptionRow   a label with a live value on the right, above its control (2.x's .row)
SubOptions  indented options with a line on their left, shown while their parent applies (2.x's .sub)
Pair        two rows side by side (2.x's .pair)
Hint        small muted help text (2.x's .hint)
Pager       ‹ Page 3 of 14 › (2.x's .pager)

own_look() and paint_frame() give a floating card (the tour's, the preview's "rendering…") its own background and
border when Inkline's stylesheet is off (View → Use my desktop's style), where it would otherwise be see-through.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSlider, QVBoxLayout, QWidget)

from inkengine.i18n import tr

from . import theme


def _role(widget, role):
    widget.setProperty("role", role)
    return widget


def own_look():
    """True when Inkline's stylesheet is off (View → Use my desktop's style): a floating card then draws its own
    background and border in the desktop's colours, or its text would sit straight on what's under it."""
    return not QApplication.instance().styleSheet()


def paint_frame(widget, fill, radius=10, width=None):
    """A rounded border in the palette's highlight colour round the widget, filled with its window colour (fill),
    or an outline only."""
    from PySide6.QtGui import QPainter, QPalette, QPen
    pal = widget.palette()
    p = QPainter(widget)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    width = width or (1.5 if fill else 3.0)
    p.setPen(QPen(pal.color(QPalette.ColorRole.Highlight), width))
    p.setBrush(pal.color(QPalette.ColorRole.Window) if fill else Qt.BrushStyle.NoBrush)
    half = width / 2
    p.drawRoundedRect(widget.rect().toRectF().adjusted(half, half, -half, -half), radius, radius)
    p.end()


def label(text, role="label"):
    return _role(QLabel(tr(text)), role)


def label_as(text, role="label"):
    """A label for text that's already in the person's language (built from translated pieces)."""
    return _role(QLabel(text), role)


def button(text, role=None, tip=None):
    b = QPushButton(tr(text))
    if role:
        _role(b, role)
    if tip:
        b.setToolTip(tr(tip))
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


class Check(QWidget):
    """A checkbox whose label wraps (a plain QCheckBox can't, and long labels would widen the sidebar).
    Clicking the label toggles it, as clicking 2.x's label did."""

    toggled = Signal(bool)

    def __init__(self, text, checked=False):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.PAIR_GAP)
        self.box = QCheckBox()
        self.box.setChecked(checked)
        self.box.setAccessibleName(tr(text))
        self.box.setCursor(Qt.CursorShape.PointingHandCursor)
        self.text = label(text)
        self.text.setWordWrap(True)
        self.text.setCursor(Qt.CursorShape.PointingHandCursor)
        self.text.mousePressEvent = lambda _e: self.box.toggle() if self.box.isEnabled() else None
        lay.addWidget(self.box, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self.text, 1)
        self.box.toggled.connect(self.toggled)

    def isChecked(self):
        return self.box.isChecked()

    def setChecked(self, on):
        self.box.setChecked(bool(on))


def check(text, checked=False):
    return Check(text, checked)   # Check's label translates it


def combo(options, current=None):
    """A list of (value, text); .value() gives the chosen value."""
    c = QComboBox()
    c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    c.setMinimumContentsLength(6)   # don't widen to the longest entry: the sidebar has a fixed width
    for value, text in options:
        c.addItem(tr(text), value)
    if current is not None:
        c.setCurrentIndex(max(0, c.findData(current)))
    c.value = lambda: c.currentData()
    c.set_value = lambda v: c.setCurrentIndex(max(0, c.findData(v)))
    return c


def line_edit(text="", placeholder="", max_length=None):
    e = QLineEdit(text)
    e.setMinimumWidth(60)
    e.setPlaceholderText(tr(placeholder))
    if max_length:
        e.setMaxLength(max_length)
    return e


class Section(QWidget):
    def __init__(self, title):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(theme.HEADING_GAP)
        title = tr(title)
        heading = _role(QLabel(title.upper()), "legend")   # stylesheets can't uppercase, so the text is
        heading.setAccessibleName(title)
        outer.addWidget(heading)
        lay = QVBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.ROW_GAP)
        outer.addLayout(lay)
        self._lay = lay

    def add(self, *widgets):
        for w in widgets:
            self._lay.addWidget(w)
        return widgets[0] if len(widgets) == 1 else widgets


class OptionRow(QWidget):
    """A label (and optionally its live value) above a control."""

    def __init__(self, text, control, value_text=None):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.LABEL_GAP)
        top = QHBoxLayout()
        top.setSpacing(theme.PAIR_GAP)
        self.label = label(text)
        self.label.setWordWrap(True)   # a long label (another language, half a Pair) wraps rather than widen the sidebar
        self.label.setBuddy(control)
        if not control.accessibleName():   # a screen reader names a list by its label, not its current entry
            control.setAccessibleName(self.label.text())
        top.addWidget(self.label, 1)
        self.value = label("", "value")
        top.addWidget(self.value)
        self.value.setVisible(value_text is not None)
        lay.addLayout(top)
        lay.addWidget(control)
        self.control = control
        if value_text is not None:
            self.value_text = value_text
            self.update_value()

    def update_value(self):
        if hasattr(self, "value_text"):
            self.value.setText(self.value_text(self.control))


def slider(lo, hi, value, step=1):
    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(lo, hi)
    s.setSingleStep(step)
    s.setPageStep(max(step, (hi - lo) // 10))
    s.setValue(value)
    return s


def slider_row(text, lo, hi, value, fmt=str):
    """An OptionRow with a slider whose live value is fmt(value)."""
    s = slider(lo, hi, value)
    row = OptionRow(text, s, lambda c: fmt(c.value()))
    s.valueChanged.connect(lambda _v: row.update_value())
    return row, s


class SubOptions(QFrame):
    def __init__(self):
        super().__init__()
        _role(self, "sub")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(theme.SUB_INDENT, 0, 0, 0)
        self._lay.setSpacing(theme.ROW_GAP)

    def add(self, *widgets):
        for w in widgets:
            self._lay.addWidget(w)
        return widgets[0] if len(widgets) == 1 else widgets


class Pair(QWidget):
    def __init__(self, left, right):
        super().__init__()
        lay = QGridLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setHorizontalSpacing(theme.PAIR_GAP)
        lay.addWidget(left, 0, 0)
        lay.addWidget(right, 0, 1)
        lay.setColumnStretch(0, 1)
        lay.setColumnStretch(1, 1)


class Hint(QLabel):
    def __init__(self, text=""):
        super().__init__(tr(text))
        _role(self, "hint")
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)


class Pager(QWidget):
    prev = Signal()
    next = Signal()

    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.PAIR_GAP)
        self.back = button("‹")
        self.back.setAccessibleName(tr("Previous page"))
        self.forward = button("›")
        self.forward.setAccessibleName(tr("Next page"))
        self.text = label("", "pager")
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text.setWordWrap(True)   # a long page name (or a longer language) wraps rather than widening the sidebar
        lay.addWidget(self.back)
        lay.addWidget(self.text, 1)
        lay.addWidget(self.forward)
        self.back.clicked.connect(self.prev)
        self.forward.clicked.connect(self.next)

    def set_text(self, text):
        self.text.setText(text)
