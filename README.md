# YouLikeHits Autobot

Free, open-source Python bot that automates social media exchange tasks on [YouLikeHits.com](https://www.youlikehits.com). Earn YouTube views, TikTok followers, SoundCloud plays, and more — automatically.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.x-green?logo=selenium&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Website Views** — Auto-visit websites, handle timers and tabs
- **YouTube Views** — Watch videos with captcha support and auto-submit
- **SoundCloud Plays** — Play tracks with random delays
- **Daily Bonus** — Auto-claim bonus points when available
- **Master Loop** — Cycles through all tasks automatically
- **GUI + CLI** — Modern customtkinter GUI or traditional CLI menu
- **XFCE & Plasma** — Works on any Linux desktop environment

## Quick Start

```bash
git clone https://github.com/YOUR_USER/YouLikeHits-Bot.git
cd YouLikeHits-Bot
./run.sh
```

### Install to application menu (XFCE / KDE Plasma)

```bash
./install.sh
```

### CLI mode

```bash
python main.py --cli
```

## Supported Platforms

| Platform     | Tasks                    |
|--------------|--------------------------|
| YouTube      | Views, Likes, Subscribers|
| TikTok       | Followers, Likes         |
| Twitter / X  | Followers, Retweets, Likes|
| SoundCloud   | Followers, Plays, Likes  |
| Websites     | Traffic                  |
| Pinterest    | Followers                |
| Twitch       | Followers                |

## Requirements

- Python 3.10+
- Google Chrome (auto-detected)
- Linux (XFCE, KDE Plasma, GNOME, or any X11/Wayland desktop)

## Project Structure

```
YouLikeHits-Bot/
├── main.py              # Entry point (GUI + CLI launcher)
├── main_cli.py          # CLI menu
├── gui/
│   └── app.py           # Customtkinter GUI
├── bot_logic/
│   ├── utils.py         # Browser setup, login, captcha, points
│   ├── websites.py      # Website views automation
│   ├── youtube.py       # YouTube views automation
│   ├── soundcloud.py    # SoundCloud plays automation
│   ├── bonus.py         # Daily bonus claimer
│   └── master.py        # Master loop orchestrator
├── landing/             # Vercel landing page (Next.js)
├── install.sh           # Install .desktop file
├── run.sh               # One-click launcher
└── requirements.txt     # Python dependencies
```

## Deploy Landing Page

The `landing/` directory contains a Next.js static site for Vercel:

```bash
cd landing
vercel deploy
```

## Disclaimer

This bot is for educational purposes. Use it responsibly and at your own risk. Not affiliated with YouLikeHits.com.

## License

MIT
