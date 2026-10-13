import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gio, GLib, Gtk, Pango

from .base import Tile, every, make_icon, make_label

MPRIS_PREFIX = "org.mpris.MediaPlayer2."
PLAYER_PATH = "/org/mpris/MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
ART_ICONS = ("audio-x-generic-symbolic", "emblem-music-symbolic", "multimedia-player-symbolic")


class _Mpris:
    """Minimal asynchronous MPRIS client over the session bus."""

    def __init__(self):
        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except GLib.Error:
            self.bus = None

    def _call(self, name, path, iface, method, params, reply, callback):
        reply_type = GLib.VariantType.new(reply) if reply else None
        self.bus.call(
            name, path, iface, method, params, reply_type,
            Gio.DBusCallFlags.NONE, 1000, None,
            lambda connection, result: self._finish(connection, result, callback),
        )

    @staticmethod
    def _finish(connection, result, callback):
        try:
            reply = connection.call_finish(result)
        except GLib.Error as exc:
            callback(None, exc)
            return
        callback(reply, None)

    def current(self, callback):
        """Call back with (bus_name, status, title, artist), or None."""
        if self.bus is None:
            callback(None)
            return

        def on_names(reply, error):
            if error is not None:
                callback(None)
                return
            names = reply.unpack()[0]
            players = [name for name in names if name.startswith(MPRIS_PREFIX)]

            def inspect_next(index, best):
                if index >= len(players):
                    callback(best)
                    return
                name = players[index]

                def on_properties(reply, error):
                    if error is not None:
                        inspect_next(index + 1, best)
                        return
                    props = reply.unpack()[0]
                    meta = props.get("Metadata", {})
                    artist = meta.get("xesam:artist", [])
                    if isinstance(artist, str):
                        artist = [artist]
                    entry = (
                        name,
                        props.get("PlaybackStatus", "Stopped"),
                        meta.get("xesam:title", ""),
                        ", ".join(artist),
                    )
                    if entry[1] == "Playing":
                        callback(entry)
                    else:
                        inspect_next(index + 1, best or entry)

                self._call(
                    name, PLAYER_PATH, PROPS_IFACE, "GetAll",
                    GLib.Variant("(s)", (PLAYER_IFACE,)), "(a{sv})", on_properties,
                )

            inspect_next(0, None)

        self._call(
            "org.freedesktop.DBus", "/org/freedesktop/DBus",
            "org.freedesktop.DBus", "ListNames", None, "(as)", on_names,
        )

    def send(self, name, method):
        if self.bus is None:
            return

        def on_sent(_reply, error):
            if error is not None:
                print(f"GlassPanel: media command failed: {error.message}")

        self._call(name, PLAYER_PATH, PLAYER_IFACE, method, None, None, on_sent)


class MediaTile(Tile):
    def __init__(self, width=None):
        super().__init__("", (), width)
        self.header.set_no_show_all(True)  # no header row on this tile

        self._mpris = _Mpris()
        self._player = None
        self._querying = False

        art = Gtk.Box()
        art.get_style_context().add_class("media-art")
        art.set_size_request(48, 48)
        icon = make_icon(ART_ICONS, 22)
        if icon:
            art.pack_start(icon, True, True, 0)

        self.title = make_label("Nothing playing", "media-title")
        self.title.set_ellipsize(Pango.EllipsizeMode.END)
        self.title.set_max_width_chars(20)
        self.artist = make_label("", "media-artist")
        self.artist.set_ellipsize(Pango.EllipsizeMode.END)
        self.artist.set_max_width_chars(24)
        self.artist.set_no_show_all(True)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_valign(Gtk.Align.CENTER)
        text.pack_start(self.title, False, False, 0)
        text.pack_start(self.artist, False, False, 0)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top.pack_start(art, False, False, 0)
        top.pack_start(text, True, True, 0)

        prev_btn, _ = self._button("media-skip-backward-symbolic", "Previous")
        play_btn, self.play_image = self._button("media-playback-start-symbolic", "PlayPause")
        next_btn, _ = self._button("media-skip-forward-symbolic", "Next")
        self._buttons = (prev_btn, play_btn, next_btn)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        controls.set_halign(Gtk.Align.CENTER)
        for button in self._buttons:
            controls.pack_start(button, False, False, 0)

        self.pack_start(top, False, False, 0)
        self.pack_start(controls, False, False, 0)

        every(2, self.update)

    def _button(self, icon_name, method):
        button = Gtk.Button()
        button.set_can_focus(False)
        button.get_style_context().add_class("media-btn")
        image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        image.get_style_context().add_class("tile-icon")
        button.add(image)
        button.connect("clicked", lambda *_: self._send(method))
        return button, image

    def _send(self, method):
        if self._player:
            self._mpris.send(self._player, method)
            self.update()

    def update(self):
        if self._querying:
            return
        self._querying = True
        self._mpris.current(self._show_state)

    def _show_state(self, state):
        self._querying = False
        self._player = state[0] if state else None
        if state is None:
            title, artist, playing = "Nothing playing", "", False
        else:
            _, status, title, artist = state
            playing = status == "Playing"
            title = title or "Unknown track"

        self.title.set_text(title)
        self.artist.set_text(artist)
        self.artist.set_visible(bool(artist))
        self.play_image.set_from_icon_name(
            "media-playback-pause-symbolic" if playing else "media-playback-start-symbolic",
            Gtk.IconSize.BUTTON,
        )
        for button in self._buttons:
            button.set_sensitive(self._player is not None)
