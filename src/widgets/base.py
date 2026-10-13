import sys
from collections import deque

import gi

try:
    gi.require_foreign("cairo")
except ImportError:
    sys.exit(
        "GlassPanel needs the PyGObject-cairo bridge.\n"
        "  sudo apt install python3-gi python3-gi-cairo\n"
        "and run it with the system interpreter:\n"
        "  /usr/bin/python3 src/main.py"
    )

import cairo

gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk

from backdrop import BACKDROP

ICE = (0.72, 0.86, 1.0)
MINT = (0.58, 0.95, 0.86)


def every(seconds, callback):
    """Run callback now and then every `seconds`. Errors never kill the timer."""

    def tick():
        try:
            callback()
        except Exception as exc:  # keep the widget alive on odd /proc reads
            print(f"GlassPanel: {callback.__qualname__} failed: {exc}")
        return True

    tick()
    GLib.timeout_add_seconds(seconds, tick)


def make_icon(candidates, size=18):
    """First themed symbolic icon that exists, or None (missing icons are skipped)."""
    theme = Gtk.IconTheme.get_default()
    for name in candidates:
        if theme.has_icon(name):
            image = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.MENU)
            image.set_pixel_size(size)
            image.get_style_context().add_class("tile-icon")
            return image
    return None


def make_label(text="", css_class=None, xalign=0.0):
    label = Gtk.Label(label=text, xalign=xalign)
    if css_class:
        label.get_style_context().add_class(css_class)
    return label


class Tile(Gtk.Box):
    """A frosted-glass card with an optional icon + title header."""

    def __init__(self, title="", icons=(), width=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.get_style_context().add_class("tile")
        self.set_valign(Gtk.Align.START)
        if width:
            self.set_size_request(width, -1)

        # Connected before GTK's default handler, so the blurred wallpaper is
        # painted first and the CSS tint, border and children go on top of it.
        self.connect("draw", BACKDROP.paint)

        self.header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = make_icon(icons)
        if icon:
            self.header.pack_start(icon, False, False, 0)
        if title:
            self.header.pack_start(make_label(title, "tile-title"), False, False, 0)
        self.pack_start(self.header, False, False, 0)

    def add_header_end(self, widget):
        self.header.pack_end(widget, False, False, 0)


def make_progress():
    bar = Gtk.ProgressBar()
    bar.set_show_text(False)
    return bar


class Sparkline(Gtk.DrawingArea):
    """Small smoothed area graph over the last N samples."""

    def __init__(self, color=ICE, history=60, height=44, fixed_max=None, min_scale=1.0):
        super().__init__()
        self.color = color
        self.fixed_max = fixed_max
        self.min_scale = min_scale
        self.values = deque([0.0] * history, maxlen=history)
        self.set_size_request(-1, height)
        self.set_hexpand(True)
        self.connect("draw", self._on_draw)

    def push(self, value):
        self.values.append(value)
        self.queue_draw()

    @staticmethod
    def _trace(cr, pts):
        cr.move_to(*pts[0])
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            mx = (x0 + x1) / 2
            cr.curve_to(mx, y0, mx, y1, x1, y1)

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        if w < 2:
            return False

        values = list(self.values)
        top = self.fixed_max or max(self.min_scale, max(values))
        step = w / (len(values) - 1)
        pad = 2.0
        pts = [
            (i * step, h - pad - min(v / top, 1.0) * (h - 2 * pad))
            for i, v in enumerate(values)
        ]

        r, g, b = self.color
        self._trace(cr, pts)
        cr.line_to(w, h)
        cr.line_to(0, h)
        cr.close_path()
        fill = cairo.LinearGradient(0, 0, 0, h)
        fill.add_color_stop_rgba(0, r, g, b, 0.40)
        fill.add_color_stop_rgba(1, r, g, b, 0.0)
        cr.set_source(fill)
        cr.fill()

        self._trace(cr, pts)
        cr.set_source_rgba(r, g, b, 1.0)
        cr.set_line_width(1.8)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.stroke()
        return False
