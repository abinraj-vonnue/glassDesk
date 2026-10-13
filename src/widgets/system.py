import glob
import os

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

from .base import Tile, every, make_label

ICONS = ("computer-symbolic", "preferences-system-symbolic")


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def uptime():
    raw = _read("/proc/uptime")
    if not raw:
        return None
    seconds = int(float(raw.split()[0]))
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def load():
    try:
        one, five, fifteen = os.getloadavg()
    except OSError:
        return None
    return f"{one:.2f} · {five:.2f} · {fifteen:.2f}"


def temperature():
    fallback = None
    for zone in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
        raw = _read(f"{zone}/temp")
        if raw is None:
            continue
        try:
            value = int(raw) / 1000
        except ValueError:
            continue
        if _read(f"{zone}/type") == "x86_pkg_temp":
            return f"{value:.0f}°C"
        if fallback is None:
            fallback = value
    return None if fallback is None else f"{fallback:.0f}°C"


def battery():
    for supply in sorted(glob.glob("/sys/class/power_supply/BAT*")):
        capacity = _read(f"{supply}/capacity")
        if capacity is None:
            continue
        status = _read(f"{supply}/status") or ""
        suffix = f" · {status}" if status and status != "Unknown" else ""
        return f"{capacity}%{suffix}"
    return None


class _Row(Gtk.Box):
    def __init__(self, key, reader):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.reader = reader
        self.value = make_label("--", "stat-val", xalign=1.0)
        self.pack_start(make_label(key, "stat-key"), True, True, 0)
        self.pack_end(self.value, False, False, 0)

    def update(self):
        self.value.set_text(self.reader() or "--")


class SystemTile(Tile):
    def __init__(self, width=None):
        super().__init__("System", ICONS, width)

        self.rows = []
        for key, reader in (
            ("Uptime", uptime),
            ("Load", load),
            ("Temp", temperature),
            ("Battery", battery),
        ):
            if reader() is None:  # skip sensors this machine doesn't have
                continue
            row = _Row(key, reader)
            self.rows.append(row)
            self.pack_start(row, False, False, 0)

        every(5, self.update)

    def update(self):
        for row in self.rows:
            row.update()
