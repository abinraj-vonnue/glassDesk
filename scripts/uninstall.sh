#!/bin/sh
set -eu

fail() {
    printf 'GlassPanel uninstaller: %s\n' "$1" >&2
    exit 1
}

if [ -z "${HOME:-}" ] || [ ! -d "$HOME" ]; then
    fail 'HOME must name an existing user directory.'
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
bin_dir="$HOME/.local/bin"
app_dir="$data_home/glasspanel"
desktop_file="$data_home/applications/glasspanel.desktop"
autostart_file="$config_home/autostart/glasspanel.desktop"
settings_dir="$config_home/glasspanel"

if [ "$(basename -- "$0")" != glasspanel-uninstall ]; then
    if [ -x "$bin_dir/glasspanel-uninstall" ]; then
        exec "$bin_dir/glasspanel-uninstall" "$@"
    fi
    fail 'GlassPanel is not installed for this user.'
fi

purge_config=0
if [ "$#" -eq 1 ] && [ "$1" = --purge-config ]; then
    purge_config=1
elif [ "$#" -ne 0 ]; then
    fail 'Usage: glasspanel-uninstall [--purge-config]'
fi

[ -f "$app_dir/.glasspanel-install" ] || fail 'GlassPanel is not installed for this user.'

if [ -x "$bin_dir/glasspanel" ]; then
    "$bin_dir/glasspanel" stop >/dev/null 2>&1 || true
fi

[ ! -L "$app_dir" ] || fail "Refusing to remove symlinked path: $app_dir"
rm -rf "$app_dir"
rm -f "$bin_dir/glasspanel" "$bin_dir/glasspanel-uninstall"
rm -f "$desktop_file" "$autostart_file"

if [ "$purge_config" -eq 1 ]; then
    rm -rf "$settings_dir"
fi

printf '%s\n' 'GlassPanel has been uninstalled.'
if [ "$purge_config" -eq 0 ]; then
    printf 'Settings were preserved at: %s/settings.json\n' "$settings_dir"
fi
