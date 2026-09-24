"""User-adjustable bot settings, persisted to settings.json in the project dir.

Only validated values are ever returned; anything malformed falls back to the
default for that key so a bad file never stops the bot.
"""
import json
import os

from .utils import PROJECT_DIR

SETTINGS_PATH = os.path.join(PROJECT_DIR, "settings.json")

# Every task the master loop can run, in the order it runs them. The key is
# what settings.json / the GUI / the CLI use; the label is what people see.
TASKS = (
    ("bonus", "Daily Bonus"),
    ("websites", "Website Views"),
    ("youtube", "YouTube Views"),
    ("youtube_likes", "YouTube Likes"),
    ("soundcloud", "SoundCloud Plays"),
    ("soundcloud_follows", "SoundCloud Follows"),
    ("instagram", "Instagram Followers"),
    ("instagram_likes", "Instagram Likes"),
    ("twitter", "Twitter Followers"),
    ("twitter_likes", "Twitter Likes"),
)
TASK_KEYS = tuple(key for key, _ in TASKS)
TASK_LABELS = dict(TASKS)

DEFAULTS = {
    "cycle_wait_min_minutes": 1.0,   # master loop: wait between cycles, lower bound
    "cycle_wait_max_minutes": 3.0,   # master loop: wait between cycles, upper bound
    "websites_per_cycle": 3,
    "youtube_per_cycle": 2,
    "youtube_likes_per_cycle": 2,
    "soundcloud_per_cycle": 2,
    "soundcloud_follows_per_cycle": 2,
    "instagram_per_cycle": 2,
    "instagram_likes_per_cycle": 2,
    "twitter_per_cycle": 2,
    "twitter_likes_per_cycle": 2,
    "master_tasks": list(TASK_KEYS),  # tasks the master loop runs (subset of TASK_KEYS)
}
QUOTA_KEYS = tuple(key for key in DEFAULTS if key.endswith("_per_cycle"))

MAX_WAIT_MINUTES = 24 * 60


def _fresh_defaults():
    """A copy of DEFAULTS that shares no list with the module constant."""
    clean = dict(DEFAULTS)
    clean["master_tasks"] = list(TASK_KEYS)
    return clean


def validate_master_tasks(raw):
    """Return the enabled master-loop tasks from `raw`, in canonical order.

    Unknown names are dropped. Anything that is not a list of names (missing
    key, garbage) means "all tasks". An empty list is kept: the user turned
    every task off on purpose and the master loop reports that.
    """
    if not isinstance(raw, (list, tuple, set)):
        return list(TASK_KEYS)
    wanted = {item for item in raw if isinstance(item, str)}
    return [key for key in TASK_KEYS if key in wanted]


def validate(raw):
    """Return a clean settings dict built from `raw` on top of DEFAULTS.

    Invalid or missing values take the default. A min above max is swapped.
    """
    clean = _fresh_defaults()
    if not isinstance(raw, dict):
        return clean

    for key in ("cycle_wait_min_minutes", "cycle_wait_max_minutes"):
        try:
            value = float(raw.get(key, clean[key]))
            if 0 <= value <= MAX_WAIT_MINUTES:
                clean[key] = value
        except (TypeError, ValueError):
            pass
    if clean["cycle_wait_min_minutes"] > clean["cycle_wait_max_minutes"]:
        clean["cycle_wait_min_minutes"], clean["cycle_wait_max_minutes"] = (
            clean["cycle_wait_max_minutes"], clean["cycle_wait_min_minutes"])

    for key in QUOTA_KEYS:
        try:
            value = int(raw.get(key, clean[key]))
            if 0 <= value <= 100:
                clean[key] = value
        except (TypeError, ValueError):
            pass

    clean["master_tasks"] = validate_master_tasks(raw.get("master_tasks", list(TASK_KEYS)))
    return clean


def load(path=SETTINGS_PATH):
    """Load settings from disk; missing or broken file yields DEFAULTS."""
    try:
        with open(path, encoding="utf-8") as f:
            return validate(json.load(f))
    except (OSError, ValueError):
        return _fresh_defaults()


def save(settings, path=SETTINGS_PATH):
    """Validate and write settings. Returns the clean dict that was written."""
    clean = validate(settings)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)
    os.replace(tmp, path)
    return clean


def cycle_wait_seconds(settings):
    """(min, max) wait between master cycles, in seconds."""
    return (settings["cycle_wait_min_minutes"] * 60, settings["cycle_wait_max_minutes"] * 60)


def enabled_tasks(settings):
    """Master-loop task keys that are switched on, in run order."""
    return validate_master_tasks(settings.get("master_tasks"))
