# YouLikeHits Autobot

Free, open-source Python bot that automates exchange tasks on [YouLikeHits.com](https://www.youlikehits.com): website views, YouTube views, SoundCloud plays and the daily bonus.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.x-green?logo=selenium&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

## What it does

| Task           | Page on YouLikeHits    | Behaviour                                                        |
|----------------|------------------------|------------------------------------------------------------------|
| Website Views  | `websites.php`         | Opens each site in a new tab, waits out the timer, closes it     |
| YouTube Views  | `youtubenew2.php`      | Clicks each video, waits ~90-135 s, clicks Submit                |
| SoundCloud Plays | `soundcloudplays.php` | Clicks each track, waits ~30-60 s                                |
| Daily Bonus    | `bonuspoints.php`      | Claims the bonus when the button is there, re-checks periodically |
| Master Loop    | all of the above       | Bonus, then 3 sites, 2 videos, 2 tracks; waits 1-3 min; repeats   |

- **GUI + CLI** — customtkinter window or a terminal menu. Both run the exact same task code.
- **Stop responds within ~1 s** — every wait is interruptible.
- **Captchas are not solved automatically.** When one appears the bot pauses 30 s and asks you to solve it in the browser.
- **Login is manual** — you log in once in the Chrome window the bot opens; the session is kept in `chrome_profile/`.
- **Chrome version is detected** from the installed binary, so a Chrome update never breaks the driver pin.

## Quick Start

```bash
git clone https://github.com/techengineerworkstation/YouLikeHits-Bot.git
cd YouLikeHits-Bot
./run.sh
```

`run.sh` creates `venv/`, installs the system tkinter package if missing, detects the X `DISPLAY` (including RDP/VNC sessions) and launches the GUI.

1. Click **Setup Browser (Login)**. Chrome opens on the YouLikeHits login page.
2. Log in. **Keep that Chrome window open.**
3. Start one loop (or the Master Loop). Click it again, or **Stop**, to stop it.

Only one loop runs at a time; the bot drives a single browser.

### CLI mode

```bash
./run.sh --cli
```

Option 1 opens the browser for login (close it to return to the menu). Options 2-6 run a loop until `Ctrl+C`.

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
│   ├── websites.py      # process_websites_once + loop
│   ├── youtube.py       # process_youtube_once + loop
│   ├── soundcloud.py    # process_soundcloud_once + loop
│   ├── bonus.py         # process_bonus_once + loop
│   └── master.py        # Composes the process_*_once functions
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
