#!/usr/bin/env python3
"""YouLikeHits Autobot - GUI Application.

Compatible with XFCE, KDE Plasma, GNOME, and any X11/Wayland desktop.
Uses customtkinter (tkinter) which is toolkit-agnostic.

Threading model: bot tasks run in worker threads; every widget update is
marshalled onto the Tk main loop via `root.after`.
"""
import customtkinter as ctk
import threading
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot_logic.utils import setup_browser, browser_state, YLH_BASE
from bot_logic import settings as settings_mod

LOOPS = [
    # key,                  label,                icon
    ("websites",           "Website Views",      "🔗"),
    ("youtube",            "YouTube Views",      "▶"),
    ("youtube_likes",      "YouTube Likes",      "👍"),
    ("soundcloud",         "SoundCloud Plays",   "🎵"),
    ("soundcloud_follows", "SoundCloud Follows", "👥"),
    ("instagram",          "Instagram Followers", "📷"),
    ("instagram_likes",    "Instagram Likes",    "❤"),
    ("twitter",            "Twitter Followers",  "🐦"),
    ("twitter_likes",      "Twitter Likes",      "💙"),
    ("bonus",              "Daily Bonus",        "🎁"),
    ("master",             "Master Loop",        "🔄"),
]
LOOP_COLOR = {"master": "#6c3483"}
LOOP_HOVER = {"master": "#8e44ad"}
DEFAULT_COLOR = "#1a5276"
DEFAULT_HOVER = "#2471a3"
STOP_COLOR = "#922b21"

STATUS_IDLE = ("Idle", "#888888")
STATUS_LOGIN = ("Login Mode", "#ffaa00")
STATUS_READY = ("Ready", "#00ff88")
STATUS_RUNNING = ("Running", "#00d4ff")
STATUS_ERROR = ("Browser Error", "#ff4444")
STATUS_CLOSED = ("Browser Closed", "#ff4444")
STATUS_UNRESPONSIVE = ("Browser Not Responding", "#ffaa00")


def _task_for(name):
    if name == "websites":
        from bot_logic.websites import _run_website_task as task
    elif name == "youtube":
        from bot_logic.youtube import _run_youtube_task as task
    elif name == "youtube_likes":
        from bot_logic.youtube_likes import _run_youtube_likes_task as task
    elif name == "soundcloud":
        from bot_logic.soundcloud import _run_soundcloud_task as task
    elif name == "soundcloud_follows":
        from bot_logic.soundcloud_follows import _run_soundcloud_follows_task as task
    elif name == "instagram":
        from bot_logic.instagram_follows import _run_instagram_follows_task as task
    elif name == "instagram_likes":
        from bot_logic.instagram_likes import _run_instagram_likes_task as task
    elif name == "twitter":
        from bot_logic.twitter_follows import _run_twitter_follows_task as task
    elif name == "twitter_likes":
        from bot_logic.twitter_likes import _run_twitter_likes_task as task
    elif name == "bonus":
        from bot_logic.bonus import _run_bonus_task as task
    elif name == "master":
        from bot_logic.master import _run_master_task as task
    else:
        raise ValueError(f"unknown loop: {name}")
    return task


class BotGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("YouLikeHits Autobot")
        self.root.geometry("960x720")
        self.root.minsize(800, 720)   # the left column needs ~600 px of height

        self.settings = settings_mod.load()
        self.driver = None
        self.running_loop = None      # name of the single active loop, or None
        self.browser_state = "closed"  # last state seen by _watch_browser
        self._stop_flag = False
        self.loop_buttons = {}

        self._build_ui()
        self._set_window_manager_hints()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_window_manager_hints(self):
        """Set WM_CLASS for XFCE/Plasma taskbar grouping."""
        try:
            self.root.tk.call("wm", "class", self.root._w, "youlikehits-autobot")
        except Exception:
            pass

    # ── UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        header = ctk.CTkFrame(self.root, fg_color="#0f3460", corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="⚡ YouLikeHits Autobot",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#e0e0e0").pack(side="left", padx=20)

        self.status_label = ctk.CTkLabel(header, text="● Idle",
                                         font=ctk.CTkFont(size=13), text_color="#888888")
        self.status_label.pack(side="right", padx=20)

        self.points_label = ctk.CTkLabel(header, text="💰 -- pts",
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         text_color="#00ff88")
        self.points_label.pack(side="right", padx=10)

        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=10)

        left = ctk.CTkFrame(body, width=260, fg_color="#16213e", corner_radius=12)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="Controls", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#00d4ff").pack(pady=(16, 8))

        self.setup_btn = ctk.CTkButton(
            left, text="🌐  Setup Browser (Login)", command=self._setup_browser,
            height=42, fg_color="#0f3460", hover_color="#1a5276", corner_radius=8)
        self.setup_btn.pack(fill="x", padx=14, pady=4)

        self._separator(left)

        for key, label, icon in LOOPS:
            if key == "master":
                self._separator(left)
            btn = ctk.CTkButton(
                left, text=f"{icon}  {label}", height=42 if key == "master" else 36,
                command=lambda k=key: self._toggle_loop(k),
                fg_color=LOOP_COLOR.get(key, DEFAULT_COLOR),
                hover_color=LOOP_HOVER.get(key, DEFAULT_HOVER),
                corner_radius=8, state="disabled")
            btn.pack(fill="x", padx=14, pady=3)
            self.loop_buttons[key] = btn

        self._separator(left)

        self.stop_all_btn = ctk.CTkButton(
            left, text="⏹  Stop", command=self._stop_all, height=36,
            fg_color=STOP_COLOR, hover_color="#c0392b", corner_radius=8, state="disabled")
        self.stop_all_btn.pack(fill="x", padx=14, pady=4)

        self._separator(left)

        ctk.CTkLabel(left, text="Points Balance", font=ctk.CTkFont(size=11),
                     text_color="#666").pack(pady=(4, 0))
        self.points_big = ctk.CTkLabel(left, text="--",
                                       font=ctk.CTkFont(size=32, weight="bold"),
                                       text_color="#00ff88")
        self.points_big.pack(pady=(0, 16))

        right = ctk.CTkFrame(body, fg_color="#16213e", corner_radius=12)
        right.pack(side="right", fill="both", expand=True)

        self._build_master_settings(right)

        ctk.CTkLabel(right, text="Activity Log", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#00d4ff").pack(pady=(12, 4))

        self.log_textbox = ctk.CTkTextbox(
            right, font=ctk.CTkFont(family="monospace", size=12),
            fg_color="#0d1117", text_color="#c9d1d9", corner_radius=8, wrap="word")
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_textbox.configure(state="disabled")

        footer = ctk.CTkFrame(self.root, fg_color="#0f3460", corner_radius=0, height=28)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        ctk.CTkLabel(footer, text="YouLikeHits Autobot  |  Use responsibly",
                     font=ctk.CTkFont(size=10), text_color="#555").pack(pady=4)

    def _build_master_settings(self, parent):
        """Master Loop panel: which tasks run and the wait between cycles.

        Read and saved to settings.json when the Master Loop starts.
        """
        panel = ctk.CTkFrame(parent, fg_color="#1b2a4e", corner_radius=10)
        panel.pack(fill="x", padx=10, pady=(10, 0))

        ctk.CTkLabel(panel, text="🔄 Master Loop: tasks to include",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#c9d1d9").pack(anchor="w", padx=12, pady=(8, 2))

        grid = ctk.CTkFrame(panel, fg_color="transparent")
        grid.pack(fill="x", padx=8)
        self.task_vars = {}
        enabled = set(self.settings["master_tasks"])
        for i, (key, label) in enumerate(settings_mod.TASKS):
            var = ctk.BooleanVar(value=key in enabled)
            self.task_vars[key] = var
            ctk.CTkCheckBox(grid, text=label, variable=var, checkbox_width=18, checkbox_height=18,
                            font=ctk.CTkFont(size=12)).grid(
                row=i // 3, column=i % 3, sticky="w", padx=6, pady=3)
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1)

        wait_row = ctk.CTkFrame(panel, fg_color="transparent")
        wait_row.pack(fill="x", padx=12, pady=(4, 8))
        ctk.CTkLabel(wait_row, text="Wait between cycles (min):",
                     font=ctk.CTkFont(size=11), text_color="#888").pack(side="left")
        self.wait_min_var = ctk.StringVar(value=f"{self.settings['cycle_wait_min_minutes']:g}")
        self.wait_max_var = ctk.StringVar(value=f"{self.settings['cycle_wait_max_minutes']:g}")
        ctk.CTkEntry(wait_row, width=52, justify="center",
                     textvariable=self.wait_min_var).pack(side="left", padx=(8, 4))
        ctk.CTkLabel(wait_row, text="to", text_color="#888").pack(side="left")
        ctk.CTkEntry(wait_row, width=52, justify="center",
                     textvariable=self.wait_max_var).pack(side="left", padx=(4, 8))
        ctk.CTkLabel(wait_row, text="random wait in this range", font=ctk.CTkFont(size=10),
                     text_color="#555").pack(side="left")

    @staticmethod
    def _separator(parent):
        ctk.CTkFrame(parent, height=1, fg_color="#333").pack(fill="x", padx=14, pady=10)

    # ── Thread-safe UI helpers (safe to call from any thread) ─────────
    def _ui(self, fn, *args):
        """Run `fn(*args)` on the Tk main thread."""
        try:
            self.root.after(0, lambda: fn(*args))
        except RuntimeError:
            pass  # main loop already gone

    def _log(self, msg):
        self._ui(self._log_now, msg)

    def _log_now(self, msg):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n"
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", line)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _update_points(self, points):
        if points is not None:
            self._ui(self._update_points_now, points)

    def _update_points_now(self, points):
        self.points_label.configure(text=f"💰 {points} pts")
        self.points_big.configure(text=str(points))

    def _set_status(self, status):
        self._ui(self._set_status_now, status)

    def _set_status_now(self, status):
        text, color = status
        self.status_label.configure(text=f"● {text}", text_color=color)

    def _set_loop_buttons(self, enabled, except_running=None):
        """Enable/disable loop buttons. The running one (if any) stays enabled as a Stop."""
        for key, btn in self.loop_buttons.items():
            if key == except_running:
                btn.configure(state="normal")
            else:
                btn.configure(state="normal" if enabled else "disabled")
        self.stop_all_btn.configure(state="normal" if except_running else "disabled")

    def _reset_button_label(self, key):
        icon, label = next((i, l) for k, l, i in LOOPS if k == key)
        self.loop_buttons[key].configure(
            text=f"{icon}  {label}", fg_color=LOOP_COLOR.get(key, DEFAULT_COLOR))

    # ── Browser ───────────────────────────────────────────────────────
    def _setup_browser(self):
        self._log("Opening browser for login...")
        self._set_status(STATUS_LOGIN)
        self.setup_btn.configure(state="disabled")

        def _run():
            driver = setup_browser()
            if not driver:
                self._log("Failed to initialize browser. Check the terminal for details.")
                self._set_status(STATUS_ERROR)
                self._ui(lambda: self.setup_btn.configure(state="normal"))
                return
            self.driver = driver
            self.browser_state = "alive"
            try:
                driver.get(f"{YLH_BASE}/login.php")
            except Exception as e:
                self._log(f"Could not open login page: {e.__class__.__name__}")
            self._log("Browser opened. Log in to YouLikeHits, then start a loop.")
            self._log("Keep the browser window open while the bot runs.")
            self._set_status(STATUS_READY)
            self._ui(self._set_loop_buttons, True)
            self._watch_browser(driver)

        threading.Thread(target=_run, daemon=True).start()

    def _watch_browser(self, driver):
        """Block (in the worker thread) until the browser is closed, then lock the UI.

        A driver call that merely fails (timeout, crashed tab, a flood of
        pop-under tabs) is reported as "not responding" and watched further;
        only a definite dead session locks the UI.
        """
        while True:
            state = browser_state(driver)
            if state == "closed":
                break
            if state == "unresponsive" and self.browser_state != "unresponsive":
                self.browser_state = state
                self._log("Browser is not responding (still open). Waiting for it...")
                self._set_status(STATUS_UNRESPONSIVE)
            elif state == "alive" and self.browser_state == "unresponsive":
                self.browser_state = state
                self._log("Browser is responding again.")
                self._set_status(STATUS_RUNNING if self.running_loop else STATUS_READY)
            time.sleep(2)
        self.browser_state = "closed"
        if self.driver is driver:
            self.driver = None
            self._stop_flag = True
            self._log("Browser was closed. Click 'Setup Browser' to reopen it.")
            self._set_status(STATUS_CLOSED)
            self._ui(self._on_browser_gone)

    def _on_browser_gone(self):
        if self.running_loop:
            self._reset_button_label(self.running_loop)
            self.running_loop = None
        self._set_loop_buttons(False)
        self.setup_btn.configure(state="normal")

    # ── Loop control (main thread) ────────────────────────────────────
    def _toggle_loop(self, name):
        if self.running_loop == name:
            self._request_stop()
            return
        if self.running_loop:
            self._log(f"'{self.running_loop}' is still running. Stop it first.")
            return
        # Never call the driver on the Tk thread: with hundreds of tabs open a
        # window_handles call can block for the whole HTTP timeout. The watcher
        # thread keeps self.browser_state current.
        if self.driver is None or self.browser_state == "closed":
            self._log("Browser is not open. Click 'Setup Browser' first.")
            return
        if self.browser_state == "unresponsive":
            self._log("Browser is not responding. Wait for it to recover first.")
            return

        if name == "master" and not self._apply_master_settings():
            return

        self.running_loop = name
        self._stop_flag = False
        self._log(f"Starting {name}...")
        self.loop_buttons[name].configure(text=f"⏹  Stop {name}", fg_color=STOP_COLOR)
        self._set_loop_buttons(False, except_running=name)
        self._set_status_now(STATUS_RUNNING)
        threading.Thread(target=self._run_loop, args=(name,), daemon=True).start()

    def _apply_master_settings(self):
        """Read the Master Loop panel, persist it, and echo what will run. False if invalid."""
        tasks = [key for key, var in self.task_vars.items() if var.get()]
        if not tasks:
            self._log("Tick at least one task for the Master Loop.")
            return False
        try:
            lo = float(self.wait_min_var.get().replace(",", "."))
            hi = float(self.wait_max_var.get().replace(",", "."))
        except ValueError:
            self._log("Wait between cycles must be numbers (minutes), e.g. 1 and 3.")
            return False
        self.settings = settings_mod.save({**self.settings,
                                           "master_tasks": tasks,
                                           "cycle_wait_min_minutes": lo,
                                           "cycle_wait_max_minutes": hi})
        lo, hi = self.settings["cycle_wait_min_minutes"], self.settings["cycle_wait_max_minutes"]
        self.wait_min_var.set(f"{lo:g}")
        self.wait_max_var.set(f"{hi:g}")
        names = ", ".join(settings_mod.TASK_LABELS[k] for k in self.settings["master_tasks"])
        self._log(f"Master Loop: {names}; wait between cycles {lo:g}-{hi:g} min.")
        return True

    def _request_stop(self):
        if self.running_loop and not self._stop_flag:
            self._stop_flag = True
            self._log(f"Stopping {self.running_loop}...")

    def _stop_all(self):
        self._request_stop()

    def _run_loop(self, name):
        """Worker thread: run the task until it returns, then release the UI."""
        try:
            task = _task_for(name)
            kwargs = {"settings": self.settings} if name == "master" else {}
            task(self.driver, lambda: self._stop_flag, self._log, self._update_points, **kwargs)
        except Exception as e:
            self._log(f"[{name}] Error: {e.__class__.__name__}: {e}")
        finally:
            self._ui(self._on_loop_finished, name)

    def _on_loop_finished(self, name):
        if self.running_loop == name:
            self.running_loop = None
        self._reset_button_label(name)
        alive = self.driver is not None and self.browser_state != "closed"
        self._set_loop_buttons(alive)
        if not alive:
            self._set_status_now(STATUS_CLOSED)
        elif self.browser_state == "unresponsive":
            self._set_status_now(STATUS_UNRESPONSIVE)
        else:
            self._set_status_now(STATUS_READY)

    # ── Lifecycle ─────────────────────────────────────────────────────
    def _on_close(self):
        self._stop_flag = True
        driver, self.driver = self.driver, None
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self._log_now("YouLikeHits Autobot ready.")
        self._log_now("Click 'Setup Browser' to log in first.")
        self.root.mainloop()


if __name__ == "__main__":
    BotGUI().run()
