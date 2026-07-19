#!/usr/bin/env python3
"""YouLikeHits Autobot - GUI Application.

Compatible with XFCE, KDE Plasma, GNOME, and any X11/Wayland desktop.
Uses customtkinter (tkinter) which is toolkit-agnostic.
"""
import customtkinter as ctk
import threading
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot_logic.utils import setup_browser, YLH_BASE


class BotGUI:
    def __init__(self):
        # Theme - works universally on XFCE/Plasma/GNOME
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("YouLikeHits Autobot")
        self.root.geometry("960x720")
        self.root.minsize(800, 560)

        # Try to set window icon (works on XFCE + Plasma)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon.png")
        if os.path.exists(icon_path):
            try:
                self.root.iconphoto(True, ctk.CTkImage(light_image=None, dark_image=None))
            except Exception:
                pass

        self.driver = None
        self.browser_ready = False
        self.running_loops = {}
        self.log_messages = []
        self.loop_buttons = {}

        self._build_ui()
        self._set_window_manager_hints()

    def _set_window_manager_hints(self):
        """Set WM_CLASS for XFCE/Plasma taskbar grouping."""
        try:
            self.root.tk.call("wm", "class", self.root._w, "youlikehits-autobot")
        except Exception:
            pass

    def _build_ui(self):
        # ── Header ──
        header = ctk.CTkFrame(self.root, fg_color="#0f3460", corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⚡ YouLikeHits Autobot",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#e0e0e0"
        ).pack(side="left", padx=20)

        self.status_label = ctk.CTkLabel(
            header, text="● Idle",
            font=ctk.CTkFont(size=13),
            text_color="#888888"
        )
        self.status_label.pack(side="right", padx=20)

        self.points_label = ctk.CTkLabel(
            header, text="💰 -- pts",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#00ff88"
        )
        self.points_label.pack(side="right", padx=10)

        # ── Body ──
        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Left Panel: Controls ──
        left = ctk.CTkFrame(body, width=260, fg_color="#16213e", corner_radius=12)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="Controls", font=ctk.CTkFont(size=15, weight="bold"),
                      text_color="#00d4ff").pack(pady=(16, 8))

        # Browser
        self.setup_btn = ctk.CTkButton(
            left, text="🌐  Setup Browser (Login)",
            command=self._setup_browser, height=42,
            fg_color="#0f3460", hover_color="#1a5276", corner_radius=8
        )
        self.setup_btn.pack(fill="x", padx=14, pady=4)

        ctk.CTkFrame(left, height=1, fg_color="#333").pack(fill="x", padx=14, pady=10)

        # Loop toggles
        loops = [
            ("websites",   "🔗  Website Views",   "#1a5276"),
            ("youtube",    "▶  YouTube Views",     "#1a5276"),
            ("soundcloud", "🎵  SoundCloud Plays", "#1a5276"),
            ("bonus",      "🎁  Daily Bonus",      "#1a5276"),
        ]
        for key, label, color in loops:
            btn = ctk.CTkButton(
                left, text=label, height=36,
                command=lambda k=key: self._toggle_loop(k),
                fg_color=color, hover_color="#2471a3", corner_radius=8,
                state="disabled"
            )
            btn.pack(fill="x", padx=14, pady=3)
            self.loop_buttons[key] = btn

        ctk.CTkFrame(left, height=1, fg_color="#333").pack(fill="x", padx=14, pady=10)

        self.master_btn = ctk.CTkButton(
            left, text="🔄  Master Loop (All)",
            command=lambda: self._toggle_loop("master"), height=42,
            fg_color="#6c3483", hover_color="#8e44ad", corner_radius=8,
            state="disabled"
        )
        self.master_btn.pack(fill="x", padx=14, pady=4)
        self.loop_buttons["master"] = self.master_btn

        ctk.CTkFrame(left, height=1, fg_color="#333").pack(fill="x", padx=14, pady=10)

        # Stop all
        self.stop_all_btn = ctk.CTkButton(
            left, text="⏹  Stop All",
            command=self._stop_all, height=36,
            fg_color="#922b21", hover_color="#c0392b", corner_radius=8,
            state="disabled"
        )
        self.stop_all_btn.pack(fill="x", padx=14, pady=4)

        # Points card
        ctk.CTkFrame(left, height=1, fg_color="#333").pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(left, text="Points Balance", font=ctk.CTkFont(size=11),
                      text_color="#666").pack(pady=(4, 0))
        self.points_big = ctk.CTkLabel(
            left, text="--",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#00ff88"
        )
        self.points_big.pack(pady=(0, 16))

        # ── Right Panel: Log ──
        right = ctk.CTkFrame(body, fg_color="#16213e", corner_radius=12)
        right.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(right, text="Activity Log", font=ctk.CTkFont(size=15, weight="bold"),
                      text_color="#00d4ff").pack(pady=(12, 4))

        self.log_textbox = ctk.CTkTextbox(
            right, font=ctk.CTkFont(family="monospace", size=12),
            fg_color="#0d1117", text_color="#c9d1d9",
            corner_radius=8, wrap="word"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ── Footer ──
        footer = ctk.CTkFrame(self.root, fg_color="#0f3460", corner_radius=0, height=28)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        ctk.CTkLabel(footer, text="YouLikeHits Autobot  |  Use responsibly",
                      font=ctk.CTkFont(size=10), text_color="#555").pack(pady=4)

    # ── Logging ──
    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.log_messages.append(line)
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", line)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    # ── Browser ──
    def _setup_browser(self):
        self._log("Opening browser for login...")
        self._set_status("Login Mode", "#ffaa00")
        self.setup_btn.configure(state="disabled")

        def _run():
            try:
                self.driver = setup_browser()
                if self.driver:
                    self.driver.get(f"{YLH_BASE}/login.php")
                    self._log("Browser opened. Log in to YouLikeHits.")
                    self._log("Close the browser window when done.")
                    try:
                        while True:
                            _ = self.driver.window_handles
                            time.sleep(1)
                    except Exception:
                        pass
                    self.browser_ready = True
                    self._log("Login complete. Loops enabled.")
                    self._set_status("Ready", "#00ff88")
                    self._enable_buttons()
                else:
                    self._log("Failed to initialize browser.")
                    self._set_status("Browser Error", "#ff4444")
            except Exception as e:
                self._log(f"Error: {e}")
            finally:
                self.setup_btn.configure(state="normal")

        threading.Thread(target=_run, daemon=True).start()

    def _enable_buttons(self):
        for btn in self.loop_buttons.values():
            btn.configure(state="normal")
        self.stop_all_btn.configure(state="normal")

    def _set_status(self, text, color):
        self.status_label.configure(text=f"● {text}", text_color=color)

    # ── Loop control ──
    def _toggle_loop(self, name):
        if name in self.running_loops:
            self.running_loops[name]["stop"] = True
            del self.running_loops[name]
            btn = self.loop_buttons[name]
            display = name.replace("_", " ").title()
            if name == "master":
                btn.configure(text=f"🔄  Master Loop (All)", fg_color="#6c3483")
            else:
                icons = {"websites": "🔗", "youtube": "▶", "soundcloud": "🎵", "bonus": "🎁"}
                btn.configure(text=f"{icons.get(name, '')}  {display}", fg_color="#1a5276")
            self._log(f"{name} stopped.")
        else:
            self.running_loops[name] = {"stop": False}
            self._log(f"Starting {name}...")
            btn = self.loop_buttons[name]
            btn.configure(text=f"⏹  Stop {name.replace('_', ' ').title()}", fg_color="#922b21")

            threading.Thread(target=self._run_loop, args=(name,), daemon=True).start()

        any_running = len(self.running_loops) > 0
        self._set_status("Running" if any_running else "Ready",
                         "#00d4ff" if any_running else "#00ff88")

    def _run_loop(self, name):
        is_stopped = lambda: self.running_loops.get(name, {}).get("stop", True)
        try:
            if name == "websites":
                from bot_logic.websites import _run_website_task
                _run_website_task(self.driver, is_stopped, self._log, self._update_points)
            elif name == "youtube":
                from bot_logic.youtube import _run_youtube_task
                _run_youtube_task(self.driver, is_stopped, self._log, self._update_points)
            elif name == "soundcloud":
                from bot_logic.soundcloud import _run_soundcloud_task
                _run_soundcloud_task(self.driver, is_stopped, self._log, self._update_points)
            elif name == "bonus":
                from bot_logic.bonus import _run_bonus_task
                _run_bonus_task(self.driver, is_stopped, self._log, self._update_points)
            elif name == "master":
                from bot_logic.master import _run_master_task
                _run_master_task(self.driver, is_stopped, self._log, self._update_points)
        except Exception as e:
            self._log(f"[{name}] Error: {e}")

    def _update_points(self, points):
        if points is not None:
            self.points_label.configure(text=f"💰 {points} pts")
            self.points_big.configure(text=str(points))

    def _stop_all(self):
        for name in list(self.running_loops):
            self.running_loops[name]["stop"] = True
            del self.running_loops[name]
        for key, btn in self.loop_buttons.items():
            if key == "master":
                btn.configure(text="🔄  Master Loop (All)", fg_color="#6c3483")
            else:
                icons = {"websites": "🔗", "youtube": "▶", "soundcloud": "🎵", "bonus": "🎁"}
                display = key.replace("_", " ").title()
                btn.configure(text=f"{icons.get(key, '')}  {display}", fg_color="#1a5276")
        self._set_status("Ready", "#00ff88")
        self._log("All loops stopped.")

    def run(self):
        self._log("YouLikeHits Autobot ready.")
        self._log("Click 'Setup Browser' to log in first.")
        self.root.mainloop()


if __name__ == "__main__":
    app = BotGUI()
    app.run()
