"""Languages: Inkline's words in the language chosen, for the window and for what's printed on pages.

tr(text) gives text in the current language: the English text is the key, looked up in locale/<code>.json, and
comes back unchanged when there's no translation (English, or a string not translated yet). Text with numbers
in it is translated with its placeholders and filled in after: tr("{n} copies").format(n=3).

The language is chosen once at start (View → Language, else the system's), before any window is built: the
engine and the window both read it. Each string looked up and not found is noted in MISSING, so a test can say
what still needs translating.
"""

import json
import os

LANGUAGES = {"en": "English", "es": "Español"}
HERE = os.path.dirname(os.path.abspath(__file__))
LANG = "en"
MISSING = set()
_catalog = {}


def catalog(code):
    """The translations for a language: {English: translation}; {} for English or a missing file."""
    if code == "en":
        return {}
    try:
        with open(os.path.join(HERE, "locale", f"{code}.json"), encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str) and v}
    except (OSError, ValueError):
        return {}


def set_language(code):
    """Use a language from now on (an unknown one means English)."""
    global LANG, _catalog
    LANG = code if code in LANGUAGES else "en"
    _catalog = catalog(LANG)
    MISSING.clear()


def system_language(name):
    """The language for a locale name such as "es_ES" or "en-GB": one Inkline has, else English."""
    code = (name or "").replace("-", "_").split("_")[0].lower()
    return code if code in LANGUAGES else "en"


def tr(text):
    if LANG == "en" or not text:
        return text
    out = _catalog.get(text)
    if out is None:
        MISSING.add(text)
        return text
    return out
