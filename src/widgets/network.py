import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

import sysinfo

from .base import ICE, MINT, Sparkline, Tile, every, make_label

ICONS = ("network-wireless-symbolic", "network-transmit-receive-symbolic", "network-workgroup-symbolic")
MIN_SCALE = 100 * 1024  # graphs stay flat below 100 KB/s instead of amplifying noise


class NetworkTile(Tile):
    def __init__(self, width=None):
        super().__init__("Network", ICONS, width)

        self.up_label = make_label("↑ 0 B/s", "rate")
        self.down_label = make_label("↓ 0 B/s", "rate")
        self.add_header_end(self.up_label)
        self.add_header_end(self.down_label)

        self.down_graph = Sparkline(ICE, height=40, min_scale=MIN_SCALE)
        self.up_graph = Sparkline(MINT, height=40, min_scale=MIN_SCALE)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.pack_start(self._column(self.down_graph, "Download"), True, True, 0)
        divider = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        divider.get_style_context().add_class("divider")
        row.pack_start(divider, False, False, 0)
        row.pack_start(self._column(self.up_graph, "Upload"), True, True, 0)
        self.pack_start(row, False, False, 0)

        self._sampler = sysinfo.NetSampler()
        every(1, self.update)

    @staticmethod
    def _column(graph, caption):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.pack_start(graph, False, False, 0)
        box.pack_start(make_label(caption, "tile-meta"), False, False, 0)
        return box

    def update(self):
        down, up = self._sampler.rates()
        self.down_label.set_text(f"↓ {sysinfo.fmt_rate(down)}")
        self.up_label.set_text(f"↑ {sysinfo.fmt_rate(up)}")
        self.down_graph.push(down)
        self.up_graph.push(up)
