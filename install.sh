#!/usr/bin/env bash
# Install YouLikeHits Autobot for XFCE/KDE Plasma
# Creates .desktop file in application menu
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

sed "s|INSTALL_DIR|$SCRIPT_DIR|g" "$SCRIPT_DIR/youlikehits-autobot.desktop" \
    > "$DESKTOP_DIR/youlikehits-autobot.desktop"
chmod +x "$DESKTOP_DIR/youlikehits-autobot.desktop"

echo "[*] Installed to: $DESKTOP_DIR/youlikehits-autobot.desktop"
echo "[*] Find 'YouLikeHits Autobot' in your application menu."
