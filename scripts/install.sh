#!/bin/sh
set -eu

fail() {
    printf 'GlassPanel installer: %s\n' "$1" >&2
    exit 1
}

if [ "$#" -gt 0 ]; then
    fail 'This installer takes no arguments.'
fi
if [ -z "${HOME:-}" ] || [ ! -d "$HOME" ]; then
    fail 'HOME must name an existing user directory.'
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
for required in src/main.py src/styles/glass.css scripts/glasspanel scripts/uninstall.sh; do
    [ -f "$project_dir/$required" ] || fail "Missing project file: $required"
done

python=/usr/bin/python3
[ -x "$python" ] || fail 'Cannot find /usr/bin/python3.'
if ! "$python" -c 'import gi; gi.require_version("Gtk", "3.0"); gi.require_version("Gdk", "3.0"); gi.require_foreign("cairo"); import cairo; from gi.repository import Gtk, Gdk, GdkPixbuf, Gio' >/dev/null 2>&1; then
    printf '%s\n' 'Required GTK 3, PyGObject, or Cairo bindings are missing.' >&2
    printf '%s\n' 'On Debian or Ubuntu, install them with:' >&2
    printf '%s\n' '  sudo apt install python3-gi gir1.2-gtk-3.0 python3-gi-cairo' >&2
    exit 1
fi

data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
case "$data_home" in
    /*) ;;
    *) data_home="$HOME/.local/share" ;;
esac
config_home=${XDG_CONFIG_HOME:-"$HOME/.config"}
case "$config_home" in
    /*) ;;
    *) config_home="$HOME/.config" ;;
esac
app_dir="$data_home/glasspanel"
bin_dir="$HOME/.local/bin"
desktop_dir="$data_home/applications"
autostart_file="$config_home/autostart/glasspanel.desktop"
desktop_file="$desktop_dir/glasspanel.desktop"

fresh_install=1
if [ -e "$app_dir" ] || [ -L "$app_dir" ]; then
    [ ! -L "$app_dir" ] || fail "Refusing to replace symlinked path: $app_dir"
    [ -f "$app_dir/.glasspanel-install" ] || fail "Path exists and is not a GlassPanel installation: $app_dir"
    fresh_install=0
fi

if [ "$fresh_install" -eq 1 ]; then
    for path in "$bin_dir/glasspanel" "$bin_dir/glasspanel-uninstall" "$desktop_file" "$autostart_file"; do
        if [ -e "$path" ] || [ -L "$path" ]; then
            fail "Refusing to overwrite an existing path: $path"
        fi
    done
else
    for path in "$bin_dir/glasspanel" "$bin_dir/glasspanel-uninstall"; do
        [ ! -L "$path" ] || fail "Refusing to replace symlinked path: $path"
    done
fi

autostart_was_enabled=0
[ ! -f "$autostart_file" ] || autostart_was_enabled=1

if [ "$fresh_install" -eq 0 ] && [ -x "$bin_dir/glasspanel" ]; then
    "$bin_dir/glasspanel" stop >/dev/null 2>&1 || true
fi

mkdir -p "$app_dir" "$bin_dir" "$desktop_dir"
rm -rf "$app_dir/src"
cp -R "$project_dir/src" "$app_dir/src"
: > "$app_dir/.glasspanel-install"
cp "$project_dir/scripts/glasspanel" "$bin_dir/glasspanel.tmp.$$"
cp "$project_dir/scripts/uninstall.sh" "$bin_dir/glasspanel-uninstall.tmp.$$"
chmod 755 "$bin_dir/glasspanel.tmp.$$" "$bin_dir/glasspanel-uninstall.tmp.$$"
mv -f "$bin_dir/glasspanel.tmp.$$" "$bin_dir/glasspanel"
mv -f "$bin_dir/glasspanel-uninstall.tmp.$$" "$bin_dir/glasspanel-uninstall"

# Create defaults on initial install without replacing any existing settings.
PYTHONPATH="$app_dir/src" "$python" -c 'from settings import load_settings; load_settings()'

escaped_launcher=$(printf '%s' "$bin_dir/glasspanel" | sed 's/\\/\\\\/g; s/"/\\"/g')
cat > "$desktop_file.tmp.$$" <<EOF
[Desktop Entry]
Type=Application
Name=GlassPanel
Comment=Desktop system widget panel
Exec="$escaped_launcher" start
Terminal=false
Categories=Utility;System;
StartupNotify=false
EOF
chmod 644 "$desktop_file.tmp.$$"
mv -f "$desktop_file.tmp.$$" "$desktop_file"

if [ "$fresh_install" -eq 1 ] || [ "$autostart_was_enabled" -eq 1 ]; then
    "$bin_dir/glasspanel" autostart on >/dev/null
fi

printf '%s\n' 'GlassPanel installed for this user.'
printf 'Launch it with: %s/glasspanel\n' "$bin_dir"
printf 'Control the running widget with: %s/glasspanel start|stop|status\n' "$bin_dir"
printf 'Login autostart: %s\n' "$([ -f "$autostart_file" ] && printf enabled || printf disabled)"
