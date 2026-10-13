import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gio, GLib, Gtk

from .base import Tile, make_label

MAX_APPS = 8
COLUMNS = 4
FALLBACK_APPS = (
    "firefox.desktop",
    "org.gnome.Nautilus.desktop",
    "org.gnome.Terminal.desktop",
    "code.desktop",
)


def _favorite_ids():
    """App ids pinned in the GNOME dock (read-only), else a short default list."""
    source = Gio.SettingsSchemaSource.get_default()
    schema = source.lookup("org.gnome.shell", True) if source else None
    if schema is not None and schema.has_key("favorite-apps"):
        ids = Gio.Settings.new("org.gnome.shell").get_strv("favorite-apps")
        if ids:
            return ids
    return FALLBACK_APPS


class QuickLaunchTile(Tile):
    def __init__(self, width=None):
        super().__init__("Quick Launch", (), width)

        grid = Gtk.Grid(column_spacing=10, row_spacing=10, column_homogeneous=True)
        count = 0
        for app_id in _favorite_ids():
            try:
                info = Gio.DesktopAppInfo.new(app_id)
            except TypeError:
                # GI exposes a NULL return from this constructor as TypeError.
                continue
            if info is None:
                continue
            grid.attach(self._button(info), count % COLUMNS, count // COLUMNS, 1, 1)
            count += 1
            if count >= MAX_APPS:
                break

        if count:
            self.pack_start(grid, False, False, 0)
        else:
            self.pack_start(make_label("No apps found", "tile-meta"), False, False, 0)

    @staticmethod
    def _button(info):
        button = Gtk.Button()
        button.set_can_focus(False)
        button.set_tooltip_text(info.get_name())
        button.get_style_context().add_class("launch-btn")

        icon = info.get_icon()
        if icon is not None:
            image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DND)
        else:
            image = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DND)
        image.set_pixel_size(34)
        button.add(image)

        def launch(_button):
            try:
                info.launch([], None)
            except GLib.Error as exc:
                print(f"GlassPanel: could not launch {info.get_name()}: {exc.message}")

        button.connect("clicked", launch)
        return button
