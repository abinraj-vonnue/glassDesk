"""Load and persist GlassPanel's per-user JSON settings."""

import copy
import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    "version": 1,
    "clock": {"format": "24h"},
    "tiles": {
        "quick_launch": True,
        "media": True,
        "quick_toggles": True,
        "system": True,
        "clock": True,
        "cpu": True,
        "network": True,
        "calendar": True,
        "ram": True,
        "storage": True,
    },
}


def settings_path():
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if not config_home or not os.path.isabs(config_home):
        config_home = str(Path.home() / ".config")
    return Path(config_home) / "glasspanel" / "settings.json"


def _write_defaults(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(DEFAULTS, indent=2) + "\n", encoding="utf-8")


def load_settings():
    """Return validated settings, falling back safely for individual values."""
    path = settings_path()
    if not path.exists():
        try:
            _write_defaults(path)
        except OSError as exc:
            print(f"GlassPanel: could not create settings file: {exc}", file=sys.stderr)
        return copy.deepcopy(DEFAULTS)

    try:
        user = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"GlassPanel: could not read settings file {path}: {exc}", file=sys.stderr)
        return copy.deepcopy(DEFAULTS)

    if (
        not isinstance(user, dict)
        or type(user.get("version")) is not int
        or user["version"] != DEFAULTS["version"]
    ):
        print(f"GlassPanel: unsupported settings format in {path}; using defaults", file=sys.stderr)
        return copy.deepcopy(DEFAULTS)

    settings = copy.deepcopy(DEFAULTS)
    clock = user.get("clock")
    if isinstance(clock, dict) and clock.get("format") in ("12h", "24h"):
        settings["clock"]["format"] = clock["format"]

    tiles = user.get("tiles")
    if isinstance(tiles, dict):
        for name in settings["tiles"]:
            value = tiles.get(name)
            if isinstance(value, bool):
                settings["tiles"][name] = value
    return settings
