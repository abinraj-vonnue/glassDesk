import math
from datetime import datetime

import cairo
import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

from .base import Tile, every, make_label

ICONS = ("preferences-system-time-symbolic", "alarm-symbolic")
SECOND_HAND = (1.0, 0.62, 0.26, 1.0)


class Dial(Gtk.DrawingArea):
    """Analogue clock face drawn with cairo."""

    def __init__(self, size=132):
        super().__init__()
        self.set_size_request(size, size)
        self.set_valign(Gtk.Align.CENTER)
        self.now = datetime.now()
        self.connect("draw", self._on_draw)

    def set_time(self, now):
        self.now = now
        self.queue_draw()

    @staticmethod
    def _hand(cr, cx, cy, angle, length, width, rgba, tail=0.0):
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(width)
        cr.set_source_rgba(*rgba)
        cr.move_to(cx - tail * math.sin(angle), cy + tail * math.cos(angle))
        cr.line_to(cx + length * math.sin(angle), cy - length * math.cos(angle))
        cr.stroke()

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 2

        # Glass face
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.set_source_rgba(1, 1, 1, 0.10)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.45)
        cr.set_line_width(1.2)
        cr.stroke()

        # Ticks
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(60):
            angle = i * math.pi / 30
            major = i % 5 == 0
            inner = r - (11 if major else 6)
            outer = r - 4
            cr.move_to(cx + inner * math.sin(angle), cy - inner * math.cos(angle))
            cr.line_to(cx + outer * math.sin(angle), cy - outer * math.cos(angle))
            cr.set_source_rgba(1, 1, 1, 0.92 if major else 0.35)
            cr.set_line_width(2.0 if major else 1.0)
            cr.stroke()

        # Hands
        now = self.now
        minute = now.minute + now.second / 60
        hour = now.hour % 12 + minute / 60
        white = (1, 1, 1, 0.96)
        self._hand(cr, cx, cy, hour * math.pi / 6, r * 0.48, 4.2, white)
        self._hand(cr, cx, cy, minute * math.pi / 30, r * 0.72, 3.0, white)
        self._hand(cr, cx, cy, now.second * math.pi / 30, r * 0.80, 1.4, SECOND_HAND, tail=r * 0.16)

        # Centre cap
        cr.arc(cx, cy, 3.6, 0, 2 * math.pi)
        cr.set_source_rgba(*SECOND_HAND)
        cr.fill()
        return False


class ClockTile(Tile):
    def __init__(self, width=None):
        super().__init__(icons=ICONS, width=width)

        self.zone = make_label("", "tile-meta")
        self.add_header_end(self.zone)

        self.dial = Dial()
        self.time = make_label("", "clock-time")
        self.weekday = make_label("", "clock-weekday")
        self.date = make_label("", "clock-date")

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_valign(Gtk.Align.CENTER)
        info.pack_start(self.time, False, False, 0)
        info.pack_start(self.weekday, False, False, 0)
        info.pack_start(self.date, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        row.pack_start(self.dial, False, False, 0)
        row.pack_start(info, True, True, 0)
        self.pack_start(row, False, False, 0)

        every(1, self.update)

    def update(self):
        now = datetime.now().astimezone()
        self.dial.set_time(now)
        self.time.set_markup(f'{now:%H}<span alpha="60%">:</span>{now:%M}')
        self.weekday.set_text(now.strftime("%A"))
        self.date.set_text(now.strftime("%d %B %Y"))
        self.zone.set_text(now.strftime("%Z"))
