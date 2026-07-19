#!/usr/bin/env python3
"""YouLikeHits Autobot - Main Entry Point.

Works on XFCE, KDE Plasma, GNOME, and any X11/Wayland desktop.
"""
import os
import sys
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)


def ensure_deps():
    """Install pip dependencies if missing. tkinter is checked separately."""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("[!] tkinter is not installed. It is a system package, not a pip package.")
        print("[!] Install it for your distro:")
        print()
        print("    Fedora / Ultramarine:  sudo dnf install python3-tkinter")
        print("    Ubuntu / Debian:       sudo apt install python3-tk")
        print("    Arch:                  sudo pacman -S python-tk")
        print("    openSUSE:              sudo zypper install python3-tk")
        print()
        print("    Or just run ./run.sh which handles this automatically.")
        sys.exit(1)

    try:
        import customtkinter  # noqa: F401
        import undetected_chromedriver  # noqa: F401
    except ImportError:
        print("[*] Installing Python dependencies...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r",
            os.path.join(PROJECT_DIR, "requirements.txt")
        ])


def launch_gui():
    """Launch the customtkinter GUI."""
    from gui.app import BotGUI
    app = BotGUI()
    app.run()


def launch_cli():
    """Launch the CLI menu."""
    from main_cli import main_menu
    main_menu()


def install_desktop_file():
    """Install .desktop file for XFCE/Plasma integration."""
    home = os.path.expanduser("~")
    desktop_dir = os.path.join(home, ".local", "share", "applications")
    os.makedirs(desktop_dir, exist_ok=True)

    desktop_content = f"""[Desktop Entry]
Type=Application
Name=YouLikeHits Autobot
Comment=Automate social media exchange tasks on YouLikeHits
Exec={sys.executable} {PROJECT_DIR}/main.py
Icon={PROJECT_DIR}/icon.png
Terminal=false
Categories=Network;Utility;
StartupWMClass=youlikehits-autobot
Keywords=youlikehits;bot;automation;social;
"""
    desktop_path = os.path.join(desktop_dir, "youlikehits-autobot.desktop")
    with open(desktop_path, "w") as f:
        f.write(desktop_content)
    os.chmod(desktop_path, 0o755)

    print(f"[*] Desktop file installed: {desktop_path}")
    print("[*] You can now find 'YouLikeHits Autobot' in your application menu.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--cli":
            ensure_deps()
            launch_cli()
        elif arg == "--install-desktop":
            install_desktop_file()
        elif arg in ("--help", "-h"):
            print("Usage: python main.py [option]")
            print()
            print("Options:")
            print("  (no args)          Launch GUI")
            print("  --cli              Launch CLI menu")
            print("  --install-desktop  Install .desktop file for XFCE/Plasma")
            print("  --help, -h         Show this help")
        else:
            print(f"Unknown option: {arg}. Use --help for usage.")
    else:
        ensure_deps()
        launch_gui()
