"""Frosted-glass backdrop.

GTK 3 CSS has no backdrop-filter, so the effect is rebuilt here: read the current
wallpaper (read-only, via GSettings), blur it once, and paint the matching slice
behind every tile. Falls back to a dark smoked-glass veil if no wallpaper image
can be loaded.
"""

import math

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gdk, GdkPixbuf, Gio, GLib

BLUR_DOWNSCALE = 12        # higher = softer blur
VEIL_ALPHA = 0.16          # dark layer under the white tint (keeps text readable)
FALLBACK_VEIL_ALPHA = 0.45  # used when no wallpaper could be loaded
RADIUS = 18                # must match .tile border-radius in glass.css


def _settings(schema_id):
    source = Gio.SettingsSchemaSource.get_default()
    if source is None or source.lookup(schema_id, True) is None:
        return None
    return Gio.Settings.new(schema_id)


def _has_key(settings, key):
    return settings is not None and settings.props.settings_schema.has_key(key)


def _get(settings, key):
    return settings.get_string(key) if _has_key(settings, key) else ""


def _rounded_rect(cr, w, h, r):
    cr.new_sub_path()
    cr.arc(w - r, r, r, -math.pi / 2, 0)
    cr.arc(w - r, h - r, r, 0, math.pi / 2)
    cr.arc(r, h - r, r, math.pi / 2, math.pi)
    cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


class Backdrop:
    def __init__(self):
        self._background = _settings("org.gnome.desktop.background")
        self._interface = _settings("org.gnome.desktop.interface")
        self._surface = None
        self._origin = (0, 0)  # top-left of the monitor the wallpaper covers

    def watch(self, callback):
        """Call `callback` when the wallpaper or colour scheme changes."""
        targets = (
            (self._background, ("picture-uri", "picture-uri-dark", "picture-options")),
            (self._interface, ("color-scheme",)),
        )
        for settings, keys in targets:
            for key in keys:
                if _has_key(settings, key):
                    settings.connect(f"changed::{key}", lambda *_: callback())

    def _wallpaper_path(self):
        uri = ""
        if _get(self._interface, "color-scheme") == "prefer-dark":
            uri = _get(self._background, "picture-uri-dark")
        uri = uri or _get(self._background, "picture-uri")
        if not uri:
            return None
        path = Gio.File.new_for_uri(uri).get_path()
        if not path or path.lower().endswith(".xml"):  # slideshows unsupported
            return None
        return path

    @staticmethod
    def _blur(pixbuf):
        w, h = pixbuf.get_width(), pixbuf.get_height()
        steps = (
            (max(1, w // BLUR_DOWNSCALE), max(1, h // BLUR_DOWNSCALE)),
            (max(1, w // 4), max(1, h // 4)),
            (w, h),
        )
        for step_w, step_h in steps:
            pixbuf = pixbuf.scale_simple(step_w, step_h, GdkPixbuf.InterpType.BILINEAR)
        return pixbuf

    def load(self, geometry):
        """Prepare the blurred wallpaper for the monitor `geometry`."""
        self._surface = None
        self._origin = (geometry.x, geometry.y)
        path = self._wallpaper_path()
        if path is None:
            return
        try:
            fmt, src_w, src_h = GdkPixbuf.Pixbuf.get_file_info(path)
            if fmt is None or src_w <= 0 or src_h <= 0:
                return
            width, height = geometry.width, geometry.height
            if _get(self._background, "picture-options") == "stretched":
                scaled_w, scaled_h = width, height
            else:  # "zoom" (GNOME default): cover the screen, centre-crop
                factor = max(width / src_w, height / src_h)
                scaled_w = math.ceil(src_w * factor)
                scaled_h = math.ceil(src_h * factor)
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, scaled_w, scaled_h, False)
            left = max(0, (pixbuf.get_width() - width) // 2)
            top = max(0, (pixbuf.get_height() - height) // 2)
            crop = pixbuf.new_subpixbuf(
                left,
                top,
                min(width, pixbuf.get_width() - left),
                min(height, pixbuf.get_height() - top),
            )
            self._surface = Gdk.cairo_surface_create_from_pixbuf(self._blur(crop), 1, None)
        except (GLib.Error, TypeError, ValueError) as exc:
            print(f"GlassPanel: wallpaper blur unavailable: {exc}")

    def paint(self, widget, cr):
        """'draw' handler: runs before the tile's CSS background is drawn."""
        alloc = widget.get_allocation()
        cr.save()
        _rounded_rect(cr, alloc.width, alloc.height, RADIUS)
        cr.clip()

        toplevel = widget.get_toplevel()
        gdk_window = toplevel.get_window()
        offset = widget.translate_coordinates(toplevel, 0, 0)

        if self._surface is not None and gdk_window is not None and offset is not None:
            origin = gdk_window.get_origin()
            screen_x = origin[-2] + offset[0] - self._origin[0]
            screen_y = origin[-1] + offset[1] - self._origin[1]
            cr.set_source_surface(self._surface, -screen_x, -screen_y)
            cr.paint()
            cr.set_source_rgba(0, 0, 0, VEIL_ALPHA)
        else:
            cr.set_source_rgba(0.03, 0.05, 0.09, FALLBACK_VEIL_ALPHA)
        cr.paint()
        cr.restore()
        return False  # continue with the normal CSS drawing


BACKDROP = Backdrop()
