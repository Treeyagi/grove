#!/bin/sh
# Grove installer. One line:
#   curl -fsSL https://raw.githubusercontent.com/Treeyagi/grove/main/install.sh | sh
# Options (after `sh -s --` when piped): --no-launch, --uninstall
set -e

BASE="${GROVE_BASE:-https://raw.githubusercontent.com/Treeyagi/grove/main}"
DEST="$HOME/.local/share/grove"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
ICON_NAME="io.github.grove.Launcher"
BIN="$HOME/.local/bin"

if [ "$1" = "--uninstall" ]; then
  rm -rf "$DEST" "$APPS/grove.desktop" "$ICONS/$ICON_NAME.svg" "$BIN/grove"
  echo "Grove removed. Your projects list (~/.config/grove) was left alone."
  exit 0
fi

command -v python3 >/dev/null || { echo "python3 is required." >&2; exit 1; }
if ! python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" 2>/dev/null; then
  echo "Missing GTK4 / libadwaita Python bindings. Install them first:" >&2
  echo "  Arch/CachyOS:  sudo pacman -S --needed python-gobject gtk4 libadwaita" >&2
  echo "  Debian/Ubuntu: sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1" >&2
  echo "  Fedora:        sudo dnf install python3-gobject gtk4 libadwaita" >&2
  exit 1
fi

mkdir -p "$DEST" "$APPS" "$ICONS" "$BIN"
here=$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)
if [ -n "$here" ] && [ -f "$here/grove.py" ]; then
  cp "$here/grove.py" "$DEST/grove.py"
  cp "$here/grove.svg" "$ICONS/$ICON_NAME.svg" 2>/dev/null || true
else
  command -v curl >/dev/null || { echo "curl is required." >&2; exit 1; }
  curl -fsSL "$BASE/grove.py?t=$(date +%s)" -o "$DEST/grove.py.tmp" && mv "$DEST/grove.py.tmp" "$DEST/grove.py"
  curl -fsSL "$BASE/grove.svg" -o "$ICONS/$ICON_NAME.svg" 2>/dev/null || true
fi
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
chmod +x "$DEST/grove.py"

cat > "$APPS/grove.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Grove
Comment=GitHub project tree launcher
Exec=python3 $DEST/grove.py
Icon=$ICON_NAME
Categories=Development;
Terminal=false
Actions=quick;

[Desktop Action quick]
Name=Quick launcher
Exec=python3 $DEST/grove.py --quick
DESK

# the `grove` command: `grove run <name>`, `grove list`, `grove --quick`
printf '#!/bin/sh\nexec python3 "%s/grove.py" "$@"\n' "$DEST" > "$BIN/grove"
chmod +x "$BIN/grove"

echo "Grove installed to $DEST (also in your app menu, and as the 'grove' command if $BIN is on your PATH)."
case " $* " in
  *" --no-launch "*) ;;
  *) nohup python3 "$DEST/grove.py" >/dev/null 2>&1 & ;;
esac
