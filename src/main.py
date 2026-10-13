import signal
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gdk, GLib, Gtk

from backdrop import BACKDROP
from widgets import (
    CalendarTile,
    ClockTile,
    CpuTile,
    NetworkTile,
    RamTile,
    StorageTile,
)

STYLE_PATH = Path(__file__).parent / "styles" / "glass.css"

LEFT_WIDTH = 360
RIGHT_WIDTH = 300
GAP = 14
MARGIN = 20  # distance from the top-right corner of the work area to the tiles
PAD = 24     # transparent room around the tiles so drop shadows aren't clipped


def load_css():
    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(str(STYLE_PATH))
    except GLib.Error as exc:
        print(f"GlassPanel: could not load stylesheet: {exc.message}", file=sys.stderr)
        return
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


class GlassPanel(Gtk.Window):
    def __init__(self):
        super().__init__(title="GlassPanel")

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_below(True)
        self.stick()
        self.set_accept_focus(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.get_style_context().add_class("glass-window")

        self._enable_transparency()
        self._refresh_backdrop()  # must happen before the tiles first draw
        BACKDROP.watch(self._refresh_backdrop)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=GAP)
        left.pack_start(ClockTile(LEFT_WIDTH), False, False, 0)
        left.pack_start(CpuTile(LEFT_WIDTH), False, False, 0)
        left.pack_start(NetworkTile(LEFT_WIDTH), False, False, 0)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=GAP)
        right.pack_start(CalendarTile(RIGHT_WIDTH), False, False, 0)
        right.pack_start(RamTile(RIGHT_WIDTH), False, False, 0)
        right.pack_start(StorageTile(RIGHT_WIDTH), False, False, 0)

        layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=GAP)
        layout.set_valign(Gtk.Align.START)
        layout.set_margin_start(PAD)
        layout.set_margin_end(PAD)
        layout.set_margin_top(PAD)
        layout.set_margin_bottom(PAD)
        layout.pack_start(left, False, False, 0)
        layout.pack_start(right, False, False, 0)
        self.add(layout)

        # The blurred slice depends on where the window sits, so redraw on moves.
        self.connect("configure-event", lambda *_: self.queue_draw())
        screen = Gdk.Screen.get_default()
        screen.connect("monitors-changed", self._on_monitors_changed)
        screen.connect("size-changed", self._on_monitors_changed)

    def _enable_transparency(self):
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

    @staticmethod
    def _monitor():
        display = Gdk.Display.get_default()
        return display.get_primary_monitor() or display.get_monitor(0)

    def _refresh_backdrop(self):
        BACKDROP.load(self._monitor().get_geometry())
        self.queue_draw()

    def _on_monitors_changed(self, *_):
        self._refresh_backdrop()
        self.place()

    def place(self):
        """Pin the tiles to the top-right of the primary monitor's work area."""
        area = self._monitor().get_workarea()
        width = self.get_preferred_width()[1]  # includes PAD on both sides
        self.move(
            area.x + area.width - width - MARGIN + PAD,
            area.y + MARGIN - PAD,
        )
        self.queue_draw()


def main():
    load_css()
    panel = GlassPanel()
    panel.connect("destroy", Gtk.main_quit)
    panel.show_all()
    panel.place()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
