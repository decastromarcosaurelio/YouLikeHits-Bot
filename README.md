# YouLikeHits Autobot

Free, open-source Python bot that automates exchange tasks on [YouLikeHits.com](https://www.youlikehits.com): website views, YouTube views and likes, SoundCloud plays and follows, and the daily bonus.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.x-green?logo=selenium&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

## What it does

| Task           | Page on YouLikeHits    | Behaviour                                                        |
|----------------|------------------------|------------------------------------------------------------------|
| Website Views  | `websites.php`         | Clicks "Visit site", waits for the page's own timer (~20 s), closes the tab |
| YouTube Views  | `youtubenew2.php`      | Clicks "View", waits for the page's timer (2-3 min), reads the result |
| YouTube Likes  | `youtubelikes.php`     | Opens the video in the site's popup, clicks Like on YouTube, confirms on YouLikeHits, reads the verification reply |
| SoundCloud Plays | `soundcloudplays.php` | Clicks "Listen", waits for the page's timer (~1 min), reads the result |
| SoundCloud Follows | `soundcloud.php`    | Opens the profile in the site's popup, clicks Follow on SoundCloud, confirms on YouLikeHits, reads the verification reply |
| Daily Bonus    | `bonuspoints.php`      | Reports today's hits toward the next milestone; claims when one is reachable |
| Master Loop    | the tasks you tick     | Bonus, then 3 sites, 2 videos, 2 likes, 2 tracks, 2 follows (all on by default); waits a random 1-3 min (adjustable); repeats |

- **GUI + CLI** — customtkinter window or a terminal menu. Both run the exact same task code.
- **Stop responds within ~1 s** — every wait is interruptible.
- **Captchas are not solved automatically.** When one appears the bot pauses 30 s and asks you to solve it in the browser.
- **Login is manual** — you log in once in the Chrome window the bot opens; the session is kept in `chrome_profile/`.
- **YouTube Likes and SoundCloud Follows act on the other site.** The bot likes the video / follows the profile inside the popup YouLikeHits opens, then confirms. That Chrome window must be signed in to YouTube and to SoundCloud (once; the profile keeps the sessions). If it is not, the bot says so and retries on its next pass.
- **Chrome version is detected** from the installed binary, so a Chrome update never breaks the driver pin.
- **Selectors verified against the live site** (September 2026). The bot waits for the site's own result message instead of sleeping a fixed time, so it credits exactly what the site credits.

## Quick Start

```bash
git clone https://github.com/techengineerworkstation/YouLikeHits-Bot.git
cd YouLikeHits-Bot
./run.sh
```

`run.sh` creates `venv/`, installs the system tkinter package if missing, detects the X `DISPLAY` (including RDP/VNC sessions) and launches the GUI.

1. Click **Setup Browser (Login)**. Chrome opens on the YouLikeHits login page.
2. Log in. **Keep that Chrome window open.** For YouTube Likes and SoundCloud Follows, also sign in to YouTube and SoundCloud in that same window.
3. Start one loop (or the Master Loop). Click it again, or **Stop**, to stop it.

Only one loop runs at a time; the bot drives a single browser.

### Master Loop: which tasks, and the wait between cycles

The panel above the activity log belongs to the Master Loop: tick the tasks to include (all six are on by default) and set the wait between cycles, in minutes. The bot picks a random wait in that range each cycle. Both are saved to `settings.json` in the project folder when you start the Master Loop, so they survive restarts. In CLI mode the Master Loop asks for the wait range and the task selection before starting (Enter keeps the saved values).

`settings.json` also holds how many items each task handles per cycle (`websites_per_cycle`, `youtube_per_cycle`, `youtube_likes_per_cycle`, `soundcloud_per_cycle`, `soundcloud_follows_per_cycle`); edit it by hand to change those. The task list is stored as `master_tasks`.

### CLI mode

```bash
./run.sh --cli
```

Option 1 opens the browser for login (close it to return to the menu). Options 2-7 run one loop until `Ctrl+C`. Option 8, the Master Loop, first asks for the wait range and which tasks to include (Enter keeps the saved values).

### Install to application menu (XFCE / KDE Plasma)

```bash
./install.sh
```

## Requirements

- Python 3.10+
- Google Chrome or Chromium (auto-detected on `PATH`)
- Linux with an X11 display (XFCE, KDE Plasma, GNOME, or an RDP/VNC session)

## Development

There is a small unit-test suite that runs against a fake driver (no browser, no network):

```bash
source venv/bin/activate
python -m unittest
```

Run it before every change to `bot_logic/`.

## Project Structure

```
YouLikeHits-Bot/
├── main.py              # Entry point (GUI by default, --cli, --install-desktop)
├── main_cli.py          # CLI menu
├── gui/app.py           # customtkinter GUI (one loop at a time, thread-safe updates)
├── bot_logic/
│   ├── utils.py         # Browser factory, Chrome version detection, waits, login/points helpers
│   ├── settings.py      # settings.json: cycle wait range and per-cycle quotas
│   ├── earn.py          # Shared View/Listen flow for YouTube views and SoundCloud plays
│   ├── engage.py        # Shared popup/confirm flow for YouTube likes and SoundCloud follows
│   ├── websites.py      # process_websites_once + loop
│   ├── youtube.py       # process_youtube_once + loop
│   ├── youtube_likes.py # process_youtube_likes_once + loop
│   ├── soundcloud.py    # process_soundcloud_once + loop
│   ├── soundcloud_follows.py  # process_soundcloud_follows_once + loop
│   ├── bonus.py         # process_bonus_once + loop
│   └── master.py        # Composes the process_*_once functions of the selected tasks
├── tests/               # unittest suite with a fake Selenium driver
├── landing/             # Next.js landing page
├── install.sh           # Installs the .desktop file
├── run.sh               # One-click launcher (venv, tkinter, DISPLAY)
└── requirements.txt
```

Each task module exposes one page-processing function (`process_*_once`) and one loop (`_run_*_task`) used by both the GUI and the CLI. Change logic in the `process_*_once` function only.

## Landing Page

`landing/` is a Next.js site. Run npm commands from inside that directory:

```bash
cd landing
npm install
npm run lint && npm run build
```

## Disclaimer

This bot is for educational purposes. Use it responsibly and at your own risk. Not affiliated with YouLikeHits.com.

## License

MIT
