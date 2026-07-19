#!/usr/bin/env bash
# YouLikeHits Autobot - Launcher
# Compatible with XFCE, KDE Plasma, GNOME, and any Linux desktop
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Ensure tkinter (system package, not pip) ──
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "[*] tkinter not found. Attempting to install via system package manager..."
    if command -v dnf &>/dev/null; then
        sudo dnf install -y python3-tkinter
    elif command -v yum &>/dev/null; then
        sudo yum install -y python3-tkinter
    elif command -v apt &>/dev/null; then
        sudo apt install -y python3-tk
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python-tk
    elif command -v zypper &>/dev/null; then
        sudo zypper install -y python3-tk
    else
        echo "[!] Could not auto-install tkinter."
        echo "[!] Please install it manually for your distro:"
        echo "    Fedora/Ultramarine:  sudo dnf install python3-tkinter"
        echo "    Ubuntu/Debian:       sudo apt install python3-tk"
        echo "    Arch:                sudo pacman -S python-tk"
        echo "    openSUSE:            sudo zypper install python3-tk"
        exit 1
    fi
    echo "[*] tkinter installed."
fi

# ── Create venv if needed ──
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi
source "$SCRIPT_DIR/venv/bin/activate"

# ── Upgrade pip silently ──
pip install -q --upgrade pip 2>/dev/null

# ── Install Python dependencies ──
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# ── Launch ──
python "$SCRIPT_DIR/main.py" "$@"
