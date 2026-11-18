"""Presets and remembered settings, kept as JSON in ~/.config/inkline (as 2.x kept them)."""

import json
import os


def config_dir():
    """$INKLINE_CONFIG_DIR (tests), else $XDG_CONFIG_HOME/inkline, else ~/.config/inkline."""
    return os.environ.get("INKLINE_CONFIG_DIR") or os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "inkline")


def read(name):
    """A JSON object from the config folder, or {} if it's missing or unreadable."""
    try:
        with open(os.path.join(config_dir(), name), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write(name, data, what):
    """Write a JSON object atomically (temp file and rename). None, or a message saying what went wrong."""
    try:
        os.makedirs(config_dir(), exist_ok=True)
        path = os.path.join(config_dir(), name)
        with open(path + ".tmp", "w", encoding="utf-8") as f:   # a crash never leaves half a file
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(path + ".tmp", path)
        return None
    except (OSError, ValueError):
        return f"Couldn't save {what.lower()} to {config_dir()}. Check the folder permissions."
