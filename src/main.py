import signal
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gdk, Gio, GLib, Gtk

from backdrop import BACKDROP
from widgets import (
    CalendarTile,
    ClockTile,
    CpuTile,
    MediaTile,
    NetworkTile,
    QuickLaunchTile,
    QuickTogglesTile,
    RamTile,
    StorageTile,
    SystemTile,
)
from settings import load_settings

STYLE_PATH = Path(__file__).parent / "styles" / "glass.css"

COL_A = 280  # apps / media / toggles / system
COL_B = 340  # clock / cpu / network
COL_C = 290  # calendar / ram / storage
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


def column(*tiles):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=GAP)
    box.set_valign(Gtk.Align.START)
    for tile in tiles:
        box.pack_start(tile, False, False, 0)
    return box


class GlassPanel(Gtk.ApplicationWindow):
    def __init__(self, application, settings):
        super().__init__(application=application, title="GlassPanel")

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

        layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=GAP)
        layout.set_valign(Gtk.Align.START)
        layout.set_margin_start(PAD)
        layout.set_margin_end(PAD)
        layout.set_margin_top(PAD)
        layout.set_margin_bottom(PAD)
        self._add_column(layout, settings, COL_A, (
            ("quick_launch", QuickLaunchTile),
            ("media", MediaTile),
            ("quick_toggles", QuickTogglesTile),
            ("system", SystemTile),
        ))
        self._add_column(layout, settings, COL_B, (
            ("clock", lambda width: ClockTile(width, settings["clock"]["format"])),
            ("cpu", CpuTile),
            ("network", NetworkTile),
        ))
        self._add_column(layout, settings, COL_C, (
            ("calendar", CalendarTile),
            ("ram", RamTile),
            ("storage", StorageTile),
        ))
        self.add(layout)

        # The blurred slice depends on where the window sits, so redraw on moves.
        self.connect("configure-event", lambda *_: self.queue_draw())
        screen = Gdk.Screen.get_default()
        screen.connect("monitors-changed", self._on_monitors_changed)
        screen.connect("size-changed", self._on_monitors_changed)

    @staticmethod
    def _add_column(layout, settings, width, entries):
        tiles = [factory(width) for key, factory in entries if settings["tiles"][key]]
        if tiles:
            layout.pack_start(column(*tiles), False, False, 0)

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


class GlassPanelApplication(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.glasspanel.GlassPanel",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.panel = None
        self.settings = load_settings()

    def do_activate(self):
        if self.panel is None:
            load_css()
            self.panel = GlassPanel(self, self.settings)
            self.panel.connect("destroy", self._on_panel_destroyed)
            self.panel.show_all()
            self.panel.place()
        else:
            self.panel.present()

    def _on_panel_destroyed(self, *_):
        self.panel = None

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        action = args[0] if args else "start"

        if action == "start" and len(args) <= 1:
            self.activate()
            return 0
        if action == "status" and len(args) == 1:
            if self.panel is None:
                command_line.print_literal("GlassPanel is stopped.\n")
                GLib.idle_add(self.quit)
                return 1
            command_line.print_literal("GlassPanel is running.\n")
            return 0
        if action == "stop" and len(args) == 1:
            if self.panel is None:
                command_line.print_literal("GlassPanel is stopped.\n")
                GLib.idle_add(self.quit)
                return 0
            self.panel.destroy()
            self.panel = None
            command_line.print_literal("GlassPanel stopped.\n")
            GLib.idle_add(self.quit)
            return 0

        command_line.printerr_literal(
            "Usage: glasspanel [start|stop|status]\n"
        )
        return 2


def main(argv=None):
    application = GlassPanelApplication()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, application.quit)
    return application.run(argv or sys.argv)


if __name__ == "__main__":
    main()
