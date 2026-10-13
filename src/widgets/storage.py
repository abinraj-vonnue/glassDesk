import math

import cairo
import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

import sysinfo

from .base import Tile, every, make_icon, make_label

ICONS = ("drive-harddisk-symbolic", "drive-harddisk-solid-state-symbolic")
RING_START = (1.0, 0.74, 0.36)  # amber
RING_END = (1.0, 0.42, 0.58)    # coral


class _Ring(Gtk.DrawingArea):
    def __init__(self, size):
        super().__init__()
        self.fraction = 0.0
        self.set_size_request(size, size)
        self.set_halign(Gtk.Align.CENTER)
        self.connect("draw", self._on_draw)

    def set_fraction(self, fraction):
        self.fraction = max(0.0, min(1.0, fraction))
        self.queue_draw()

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx, cy = w / 2, h / 2
        line = 9.0
        radius = min(w, h) / 2 - line

        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(line)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.set_source_rgba(1, 1, 1, 0.14)
        cr.stroke()

        if self.fraction <= 0:
            return False

        start = -math.pi / 2
        end = start + 2 * math.pi * self.fraction

        cr.arc(cx, cy, radius, start, end)  # soft glow
        cr.set_source_rgba(*RING_END, 0.25)
        cr.set_line_width(line + 6)
        cr.stroke()

        gradient = cairo.LinearGradient(0, 0, w, h)
        gradient.add_color_stop_rgb(0, *RING_START)
        gradient.add_color_stop_rgb(1, *RING_END)
        cr.arc(cx, cy, radius, start, end)
        cr.set_source(gradient)
        cr.set_line_width(line)
        cr.stroke()
        return False


class _Disk(Gtk.Box):
    def __init__(self, name, path, size):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.path = path

        self.ring = _Ring(size)
        overlay = Gtk.Overlay()
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.add(self.ring)
        icon = make_icon(ICONS, 28)
        if icon:
            icon.set_halign(Gtk.Align.CENTER)
            icon.set_valign(Gtk.Align.CENTER)
            overlay.add_overlay(icon)

        self.used = make_label("--", "disk-name", xalign=0.5)
        self.detail = make_label("", "tile-meta", xalign=0.5)

        self.pack_start(overlay, False, False, 0)
        self.pack_start(self.used, False, False, 0)
        self.pack_start(self.detail, False, False, 0)
        if name:
            self.pack_start(make_label(name, "tile-meta", xalign=0.5), False, False, 0)

    def update(self):
        usage = sysinfo.disk_usage(self.path)
        if usage is None:
            self.ring.set_fraction(0)
            self.used.set_text("unavailable")
            self.detail.set_text("")
            return
        used, total = usage
        self.ring.set_fraction(used / total)
        self.used.set_text(f"{used / total * 100:.0f}% used")
        self.detail.set_text(
            f"{sysinfo.fmt_size(total - used)} free of {sysinfo.fmt_size(total)}"
        )


class StorageTile(Tile):
    def __init__(self, width=None):
        super().__init__("Storage", ICONS, width)

        disks = [("System", "/")]
        if sysinfo.has_separate_home():
            disks.append(("Home", "/home"))

        many = len(disks) > 1
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True, spacing=8)
        self.disks = []
        for name, path in disks:
            disk = _Disk(name if many else None, path, 92 if many else 112)
            self.disks.append(disk)
            row.pack_start(disk, True, True, 0)
        self.pack_start(row, False, False, 0)

        every(30, self.update)

    def update(self):
        for disk in self.disks:
            disk.update()
