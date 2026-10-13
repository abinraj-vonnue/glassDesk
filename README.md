# GlassPanel

GlassPanel is a GTK 3 desktop overlay for Linux. It displays the clock,
calendar, CPU, memory, network, storage, media controls, quick app launch,
desktop toggles, and available system details over a blurred wallpaper.

## Requirements

- Linux with an **X11 session** (tested on Ubuntu GNOME on Xorg) and a
  compositing window manager (GNOME's Mutter provides one). Wayland sessions
  are not supported: window placement and keeping the panel behind other
  windows rely on X11.
- Python 3.8 or newer, run with the system interpreter (`/usr/bin/python3`).
  No pip packages are needed; the rest of the code uses the standard library.
- GTK 3.24, PyGObject, and the PyGObject–Cairo bridge.
- A session D-Bus (present in any normal desktop login), used by the media
  controls.
- Live stats come from `/proc` and `/sys`, so GlassPanel is Linux-only. It
  does not use `psutil` or Conky.

### Required packages

On Debian or Ubuntu:

```sh
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
    gir1.2-gdkpixbuf-2.0 gir1.2-pango-1.0
```

The last two are normally pulled in by `gir1.2-gtk-3.0` and are listed for
minimal installs. Other distributions: Fedora uses
`python3-gobject gtk3 python3-cairo`, and Arch uses
`python-gobject gtk3 python-cairo` (only Ubuntu GNOME on X11 has been tested).

Check the install:

```sh
/usr/bin/python3 -c "import gi; gi.require_version('Gtk','3.0'); gi.require_foreign('cairo'); from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, Gio; print('OK')"
```

### Optional packages

Nothing below is required to start GlassPanel. Features degrade gracefully.

| Feature | Needs | Without it |
|---|---|---|
| Blurred wallpaper glass | `gsettings-desktop-schemas` (preinstalled with GNOME) and a single JPEG or PNG wallpaper. WebP needs `webp-pixbuf-loader`, SVG needs `librsvg2-common`. | Tiles use a dark smoked-glass tint. Slideshow (XML) wallpapers are not blurred. |
| Mute toggle | `pulseaudio-utils` (provides `pactl`; with PipeWire it talks to `pipewire-pulse`, the Ubuntu default) | Toggle is hidden. |
| Dark mode, do-not-disturb and night-light toggles | GNOME schemas (`gsettings-desktop-schemas`, `gnome-settings-daemon`) | Each missing toggle is hidden. |
| Quick Launch from dock favourites | GNOME Shell | Falls back to a short default app list. |
| Symbolic icons | An icon theme such as `adwaita-icon-theme` or Yaru | Text glyphs are shown instead. |
| Inter font | `fonts-inter` | Falls back to Ubuntu or Cantarell. |
| CPU temperature and battery rows | Hardware that exposes them in `/sys` | Rows are hidden. |

## Install for the current user

After installing the requirements above, run:

```sh
./scripts/install.sh
```

The installer copies GlassPanel under `~/.local/share/glasspanel`, installs
commands in `~/.local/bin`, and adds an application menu entry. It enables
autostart on a fresh install. It does not use `sudo` or install system
packages. Make sure `~/.local/bin` is in your `PATH` to use the commands from
a terminal. After pulling or editing a newer version, rerun
`./scripts/install.sh` to update the installed app and launcher; `glasspanel`
runs the installed copy, not the files in the checkout.

Use the `glasspanel` command to manage the widget during the current session:
`glasspanel` and `glasspanel start` detach to the background, so the terminal
can be closed after launching. Runtime output is written to
`${XDG_STATE_HOME:-~/.local/state}/glasspanel/glasspanel.log`.

```sh
glasspanel start
glasspanel stop
glasspanel status
```

Login autostart is separate from whether the widget is currently running:

```sh
glasspanel autostart on
glasspanel autostart off
glasspanel autostart status
```

Uninstall while preserving settings with `glasspanel-uninstall`. To also
remove the settings file, run `glasspanel-uninstall --purge-config`. From a
checkout, `./scripts/uninstall.sh` invokes the installed uninstaller.

## Settings

GlassPanel reads `${XDG_CONFIG_HOME:-~/.config}/glasspanel/settings.json`.
The first run creates a default file. Set individual values under `tiles` to
`false` to hide those tiles, or change `clock.format` from `24h` to `12h`.
Settings survive application upgrades and normal uninstall.

Running `/usr/bin/python3 src/main.py` directly keeps the process attached to
that terminal; use the installed `glasspanel start` command for background
launching.

Media controls use MPRIS players available on the session D-Bus. GNOME settings
enable the matching quick toggles and favorite-app list when available. The
mute toggle additionally uses `pactl` (package `pulseaudio-utils`, which also
works with PipeWire through `pipewire-pulse`); it is omitted when `pactl` is
not installed.
