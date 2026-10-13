import shutil
import subprocess

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gio, GLib, Gtk

from .base import Tile, every, make_icon


def _settings(schema_id, key):
    source = Gio.SettingsSchemaSource.get_default()
    schema = source.lookup(schema_id, True) if source else None
    if schema is None or not schema.has_key(key):
        return None
    return Gio.Settings.new(schema_id)


def _setting_toggle(schema_id, key, kind):
    """(read, write) pair backed by a GSettings key, or (None, None)."""
    settings = _settings(schema_id, key)
    if settings is None:
        return None, None
    if kind == "scheme":  # dark mode
        return (
            lambda: settings.get_string(key) == "prefer-dark",
            lambda on: settings.set_string(key, "prefer-dark" if on else "default"),
        )
    if kind == "inverted":  # do not disturb = banners off
        return (
            lambda: not settings.get_boolean(key),
            lambda on: settings.set_boolean(key, not on),
        )
    return (
        lambda: settings.get_boolean(key),
        lambda on: settings.set_boolean(key, on),
    )


def _mute_toggle():
    if shutil.which("pactl") is None:
        return None, None

    def read():
        out = subprocess.run(
            ["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
            capture_output=True, text=True, timeout=1, check=True,
        ).stdout
        return "yes" in out.lower()

    def write(on):
        subprocess.run(
            ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if on else "0"],
            timeout=1, check=True,
        )

    return read, write


def _specs():
    entries = (
        ("Dark mode", ("weather-clear-night-symbolic",), "☾",
         _setting_toggle("org.gnome.desktop.interface", "color-scheme", "scheme")),
        ("Mute", ("audio-volume-muted-symbolic",), "♪", _mute_toggle()),
        ("Do not disturb", ("notifications-disabled-symbolic",), "⌀",
         _setting_toggle("org.gnome.desktop.notifications", "show-banners", "inverted")),
        ("Night light", ("night-light-symbolic",), "☀",
         _setting_toggle("org.gnome.settings-daemon.plugins.color", "night-light-enabled", "plain")),
    )
    return [
        (tip, icons, fallback, read, write)
        for tip, icons, fallback, (read, write) in entries
        if read is not None
    ]


class QuickTogglesTile(Tile):
    def __init__(self, width=None):
        super().__init__("Quick Toggles", (), width)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, homogeneous=True)
        self._items = []
        for tip, icons, fallback, read, write in _specs():
            button = Gtk.ToggleButton()
            button.set_can_focus(False)
            button.set_tooltip_text(tip)
            button.set_size_request(-1, 44)
            button.get_style_context().add_class("toggle-btn")
            button.add(make_icon(icons, 20) or Gtk.Label(label=fallback))
            handler = button.connect("toggled", self._on_toggled, write)
            self._items.append((button, handler, read))
            row.pack_start(button, True, True, 0)
        self.pack_start(row, False, False, 0)

        every(3, self.refresh)

    @staticmethod
    def _on_toggled(button, write):
        try:
            write(button.get_active())
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"GlassPanel: toggle failed: {exc}")

    def refresh(self):
        for button, handler, read in self._items:
            try:
                state = read()
            except (OSError, subprocess.SubprocessError):
                continue
            if state != button.get_active():
                button.handler_block(handler)
                button.set_active(state)
                button.handler_unblock(handler)
