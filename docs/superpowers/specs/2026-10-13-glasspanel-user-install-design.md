# GlassPanel per-user installation design

## Goal

Make GlassPanel straightforward to install, launch, control during the current
session, start automatically at login, configure, and uninstall for one Linux
user. The workflow must not require administrator privileges and must preserve
the user's settings during upgrades and normal uninstall.

## User experience

The repository will provide `scripts/install.sh` and `scripts/uninstall.sh`.
Installation copies the runnable app into the user's data directory and adds a
launcher command and desktop menu entry. The first installation enables login
autostart by default. Re-running the installer updates app files while
preserving the user's current autostart choice and settings.

The installed `glasspanel` command will support:

| Command | Behavior |
| --- | --- |
| `glasspanel` or `glasspanel start` | Start the widget, or activate the existing instance |
| `glasspanel stop` | Close the running widget without uninstalling it |
| `glasspanel status` | Report whether the widget is running |
| `glasspanel autostart on` | Enable launch at the next login |
| `glasspanel autostart off` | Disable launch at the next login |
| `glasspanel autostart status` | Report the saved login-start setting |
| `glasspanel-uninstall` | Remove the application and its launch entries |
| `glasspanel-uninstall --purge-config` | Also remove the user's settings file |

Stopping the widget does not change the login autostart setting. Disabling
autostart does not stop an already running widget. Starting the widget remains
available regardless of the autostart setting.

## Installation layout

The installer will use these user-owned locations:

- Application code and styles: `${XDG_DATA_HOME:-~/.local/share}/glasspanel/`
- Launcher and uninstaller commands: `~/.local/bin/`
- Desktop menu entry: `${XDG_DATA_HOME:-~/.local/share}/applications/`
- Login autostart entry: `${XDG_CONFIG_HOME:-~/.config}/autostart/`
- Settings: `${XDG_CONFIG_HOME:-~/.config}/glasspanel/settings.json`

The installer will validate that `/usr/bin/python3` can import PyGObject, GTK
3, and Cairo. It will not install OS packages or invoke `sudo`; if dependencies
are missing it will print the existing Debian/Ubuntu package guidance. The
desktop entry and autostart entry will invoke the installed launcher using
proper desktop-file quoting for user paths.

The installer will be idempotent. On a fresh install it creates the default
settings file and enables autostart. On an upgrade it replaces only installed
application files, retains user settings, and retains the current autostart
state. The settings file is not stored inside the application directory.

## Runtime command handling

The launcher will execute the system Python with the installed `src/main.py`
and pass through runtime commands. The GTK application will use a unique
`Gtk.Application` identity and command-line handling so secondary invocations
can communicate `start`, `stop`, and `status` to the existing process rather
than creating additional windows. A stop command will close the GTK main loop;
a start command will activate or create the single panel window.

Autostart commands will be handled by the installed launcher and will create,
remove, or inspect only GlassPanel's own XDG autostart desktop file. Enabling
autostart writes a desktop entry that runs `glasspanel start`. Disabling it
removes that entry and leaves the application installed.

## Settings

Settings use JSON from the Python standard library. Version 1 contains:

```json
{
  "version": 1,
  "clock": {
    "format": "24h"
  },
  "tiles": {
    "quick_launch": true,
    "media": true,
    "quick_toggles": true,
    "system": true,
    "clock": true,
    "cpu": true,
    "network": true,
    "calendar": true,
    "ram": true,
    "storage": true
  }
}
```

All tiles are enabled by default, and the clock defaults to the current 24-hour
display. Users can hide individual tiles by setting their value to `false`, or
set the clock format to `12h`. Hidden tiles will not be constructed, and empty
columns will be omitted from the panel. The app will ignore unknown keys, validate
known values independently, and fall back to defaults for missing or invalid
values. Invalid JSON will produce a warning and use defaults without
overwriting the user's file.

On first application launch, if no settings file exists, GlassPanel will write
the default file. Installation may create the same default as part of initial
setup; the runtime behavior also supports direct source-tree launches. Normal
uninstall preserves settings; `--purge-config` explicitly removes them.

## Uninstallation

The installed `glasspanel-uninstall` command will first request the running
instance to stop, then remove GlassPanel's app directory, launcher commands,
desktop menu entry, and autostart entry. It will preserve the settings file
unless `--purge-config` is supplied. The repository's `scripts/uninstall.sh`
will delegate to the installed uninstaller when available, so a user can
remove the installation without manually deleting directories.

The uninstaller will not remove GTK/PyGObject packages, user application data,
or any files outside the paths owned by GlassPanel.

## Compatibility and scope

The first implementation targets Linux desktop sessions with GTK 3, PyGObject,
and XDG user directories. GNOME-specific tiles remain optional and continue to
hide unavailable controls. Debian/Ubuntu dependency instructions will be
provided; package installation remains the user's responsibility.

This work does not include a graphical settings editor, distribution packages
such as `.deb` or Flatpak, or automatic dependency installation. Automated
tests are deferred as requested; installation and runtime flows will need
manual verification before considering them validated.
