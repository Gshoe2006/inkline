"""Themes: Inkline's light and dark, High contrast, Warm paper and Slate, chosen in Edit → Settings or
View → Theme, with the extras offered only once turned on."""

import dataclasses

import pytest
from PySide6.QtWidgets import QApplication

from inkapp import config, settings, theme


@pytest.fixture(autouse=True)
def app():
    a = QApplication.instance() or QApplication([])
    yield a
    theme.CHOSEN["name"] = "system"
    theme.apply(a, dark=False)


def lum(h):
    r, g, b = (int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name", list(theme.THEMES))
def test_every_theme_is_readable(name):
    """Text on its background at least 4.5:1 (WCAG AA); High contrast at least 10:1."""
    t = theme.THEMES[name]
    need = 10 if name == "contrast" else 4.5
    for fg, bgs in ((t.ink, (t.panel, t.field, t.bg)), (t.muted, (t.panel, t.field, t.bg)), (t.accent_ink, (t.accent,))):
        for bg in bgs:
            assert ratio(fg, bg) >= need, (name, fg, bg, ratio(fg, bg))
    assert ratio(t.accent, t.panel) >= 3                    # the focus ring and sliders stand out (non-text, 3:1)
    assert set(dataclasses.asdict(t)) == set(dataclasses.asdict(theme.LIGHT))


def test_choosing_and_offering():
    assert theme.offered() == ["system", "light", "dark"]
    assert theme.offered(["slate", "contrast", "nope"]) == ["system", "light", "dark", "contrast", "slate"]
    theme.CHOSEN["name"] = "warm"
    assert theme.tokens() is theme.WARM and theme.tokens(dark=True) is theme.DARK   # the self-test asks for one
    theme.restore({"theme": "warm", "themes_offered": ["warm"]})
    assert theme.CHOSEN["name"] == "warm"
    theme.restore({"theme": "warm", "themes_offered": []})  # turned off since: back to the system's
    assert theme.CHOSEN["name"] == "system"
    theme.restore({"theme": "dark"})
    assert theme.CHOSEN["name"] == "dark"


def test_a_theme_restyles_the_app(app):
    theme.use_theme(app, "slate")
    assert theme.SLATE.panel in app.styleSheet() and app.palette().window().color().name() == theme.SLATE.bg
    theme.use_theme(app, "nonsense")
    assert theme.CHOSEN["name"] == "system"


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    return Window("6.0.0", remember=True)


def test_view_theme_menu_and_settings(win, app):
    view = next(a.menu() for a in win.menuBar().actions() if a.text() == "&View")
    assert win.theme_menu.menuAction() in view.actions()
    assert list(win.theme_actions) == ["system", "light", "dark"] and win.theme_actions["system"].isChecked()
    d = settings.SettingsDialog(win)
    assert [d.theme.itemData(i) for i in range(d.theme.count())] == ["system", "light", "dark"]
    d.extra["warm"].setChecked(True)                         # offer Warm paper
    assert config.read("preferences.json")["themes_offered"] == ["warm"]
    assert [d.theme.itemData(i) for i in range(d.theme.count())][-1] == "warm"
    win._fill_theme_menu()
    assert "warm" in win.theme_actions
    d.theme.set_value("warm")                                # use it
    assert theme.CHOSEN["name"] == "warm" and config.read("preferences.json")["theme"] == "warm"
    assert theme.WARM.panel in app.styleSheet()
    win.theme_actions["dark"].trigger()                      # the menu switches too
    assert theme.CHOSEN["name"] == "dark" and config.read("preferences.json")["theme"] == "dark"
    win.set_theme("warm")
    d.extra["warm"].setChecked(False)                        # turning off the one in use: the system's again
    assert theme.CHOSEN["name"] == "system" and "warm" not in win.theme_actions
    assert [d.theme.itemData(i) for i in range(d.theme.count())] == ["system", "light", "dark"]
    assert d.theme.value() == "system"


def test_the_desktop_style_switch_in_settings(win, monkeypatch):
    monkeypatch.setattr(theme, "PLAIN", set())   # Qt's own "Windows" style stands in for the desktop's
    monkeypatch.setitem(theme.DESKTOP, "style", "Windows")
    monkeypatch.setitem(theme.DESKTOP, "palette", None)
    monkeypatch.setitem(theme.DESKTOP, "on", False)
    from inkapp.window import Window
    w = Window("6.0.0", remember=True)
    d = settings.SettingsDialog(w)
    assert d.desktop.isEnabled() and not d.desktop.isChecked()
    d.desktop.setChecked(True)
    assert w.act_desktop.isChecked() and theme.DESKTOP["on"]
    d.desktop.setChecked(False)
    assert not w.act_desktop.isChecked() and not theme.DESKTOP["on"]
    QApplication.instance().setStyle("Fusion")


def test_without_remembering_the_extras_cant_be_turned_on(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    d = settings.SettingsDialog(Window("6.0.0", remember=False))
    assert not any(c.isEnabled() for c in d.extra.values()) and d.theme.isEnabled()
