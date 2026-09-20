"""User-adjustable bot settings, persisted to settings.json in the project dir.

Only validated values are ever returned; anything malformed falls back to the
default for that key so a bad file never stops the bot.
"""
import json
import os

from .utils import PROJECT_DIR

SETTINGS_PATH = os.path.join(PROJECT_DIR, "settings.json")

DEFAULTS = {
    "cycle_wait_min_minutes": 1.0,   # master loop: wait between cycles, lower bound
    "cycle_wait_max_minutes": 3.0,   # master loop: wait between cycles, upper bound
    "websites_per_cycle": 3,
    "youtube_per_cycle": 2,
    "soundcloud_per_cycle": 2,
}

MAX_WAIT_MINUTES = 24 * 60


def validate(raw):
    """Return a clean settings dict built from `raw` on top of DEFAULTS.

    Invalid or missing values take the default. A min above max is swapped.
    """
    clean = dict(DEFAULTS)
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

    for key in ("websites_per_cycle", "youtube_per_cycle", "soundcloud_per_cycle"):
        try:
            value = int(raw.get(key, clean[key]))
            if 0 <= value <= 100:
                clean[key] = value
        except (TypeError, ValueError):
            pass
    return clean


def load(path=SETTINGS_PATH):
    """Load settings from disk; missing or broken file yields DEFAULTS."""
    try:
        with open(path, encoding="utf-8") as f:
            return validate(json.load(f))
    except (OSError, ValueError):
        return dict(DEFAULTS)


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
