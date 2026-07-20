#!/usr/bin/env bash
# YouLikeHits Autobot - Launcher
# Compatible with XFCE, KDE Plasma, GNOME, and any Linux desktop
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Debug: show current display state ──
echo "[*] Current DISPLAY='$DISPLAY'"
echo "[*] X11 sockets: $(ls /tmp/.X11-unix/ 2>/dev/null || echo 'none')"

# ── Ensure DISPLAY is set ──
if [ -z "$DISPLAY" ]; then
    # Detect from X11 sockets (matches :10 -> :10.0, :0 -> :0.0)
    for sock in /tmp/.X11-unix/X*; do
        if [ -S "$sock" ]; then
            num=$(basename "$sock" | sed 's/^X//')
            export DISPLAY=":${num}.0"
            echo "[*] DISPLAY was empty. Found X socket. Set DISPLAY=$DISPLAY"
            break
        fi
    done
fi

# If still empty, default to :0.0
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0.0
    echo "[*] No X sockets found. Defaulting DISPLAY=$DISPLAY"
fi

echo "[*] Using DISPLAY=$DISPLAY"

# ── Verify display is reachable ──
if command -v xdpyinfo &>/dev/null; then
    if xdpyinfo -display "$DISPLAY" &>/dev/null; then
        echo "[*] Display $DISPLAY is reachable."
    else
        echo "[!] WARNING: Display $DISPLAY is not responding."
        echo "[!] Trying to find active display from running X processes..."
        # Try to find DISPLAY from xfce4-session or Xorg
        FOUND_DISPLAY=$(xdotool get-displaygeometry 2>/dev/null | head -1 || true)
        RUNNING=$(pgrep -a "Xorg|Xrdp|Xvnc|xfce4-session" 2>/dev/null || true)
        echo "[!] Running X processes: $RUNNING"
        echo "[!]"
        echo "[!] Try running this first in your terminal:"
        echo "    export DISPLAY=:10.0"
        echo "    ./run.sh"
    fi
fi

# ── Ensure tkinter (system package, not pip) ──
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "[*] tkinter not found. Attempting to install..."
    if command -v dnf &>/dev/null; then
        sudo dnf install -y python3-tkinter
    elif command -v apt &>/dev/null; then
        sudo apt install -y python3-tk
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python-tk
    else
        echo "[!] Install tkinter manually: sudo dnf install python3-tkinter"
        exit 1
    fi
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

# ── Export DISPLAY so Python sees it ──
export DISPLAY

# ── Launch ──
echo "[*] Launching with DISPLAY=$DISPLAY ..."
python "$SCRIPT_DIR/main.py" "$@"
