"""Master loop: cycles through the selected tasks with a small quota each.

Composes the process_*_once functions so there is no third copy of the logic.
Which tasks run, their order and quotas come from settings (`master_tasks`,
`*_per_cycle`); see bot_logic.settings.TASKS.
"""
import random
from .utils import (
    YLH_BASE, is_logged_in, navigate_to, get_points, wait_unless_stopped, run_cli_task,
)
from .bonus import process_bonus_once, CLAIMED, PAGE as BONUS_PAGE
from .websites import process_websites_once, PAGE as WEBSITES_PAGE
from .youtube import process_youtube_once, PAGE as YOUTUBE_PAGE
from .youtube_likes import process_youtube_likes_once, PAGE as YOUTUBE_LIKES_PAGE
from .soundcloud import process_soundcloud_once, PAGE as SOUNDCLOUD_PAGE
from .soundcloud_follows import process_soundcloud_follows_once, PAGE as SOUNDCLOUD_FOLLOWS_PAGE
from . import settings as settings_mod


def _steps(driver, log_func, is_stopped, settings):
    """(label, page, step) per task key; `step()` runs one pass with the cycle quota."""
    q = {key: settings[f"{key}_per_cycle"] for key in settings_mod.TASK_KEYS if key != "bonus"}
    return {
        "bonus": ("Checking daily bonus...", BONUS_PAGE,
                  lambda: process_bonus_once(driver, log_func, is_stopped) == CLAIMED),
        "websites": ("Processing website views...", WEBSITES_PAGE,
                     lambda: process_websites_once(driver, log_func, is_stopped, limit=q["websites"])),
        "youtube": ("Processing YouTube views...", YOUTUBE_PAGE,
                    lambda: process_youtube_once(driver, log_func, is_stopped, limit=q["youtube"])),
        "youtube_likes": ("Processing YouTube likes...", YOUTUBE_LIKES_PAGE,
                          lambda: process_youtube_likes_once(driver, log_func, is_stopped,
                                                             limit=q["youtube_likes"])),
        "soundcloud": ("Processing SoundCloud plays...", SOUNDCLOUD_PAGE,
                       lambda: process_soundcloud_once(driver, log_func, is_stopped, limit=q["soundcloud"])),
        "soundcloud_follows": ("Processing SoundCloud follows...", SOUNDCLOUD_FOLLOWS_PAGE,
                               lambda: process_soundcloud_follows_once(driver, log_func, is_stopped,
                                                                       limit=q["soundcloud_follows"])),
    }


def quota_summary(settings):
    """'3 sites, 2 videos, 2 likes, 2 tracks, 2 follows' for the enabled tasks."""
    unit = {"websites": "sites", "youtube": "videos", "youtube_likes": "likes",
            "soundcloud": "tracks", "soundcloud_follows": "follows"}
    return ", ".join(f"{settings[f'{key}_per_cycle']} {unit[key]}"
                     for key in settings_mod.enabled_tasks(settings) if key in unit)


def _run_master_task(driver, is_stopped, log_func, update_points_func, settings=None):
    """Master loop (GUI and CLI share this).

    `settings` is a dict as returned by bot_logic.settings.load(); it controls
    which tasks run, the wait between cycles and the per-cycle quotas.
    """
    settings = settings_mod.validate(settings or settings_mod.load())
    enabled = settings_mod.enabled_tasks(settings)
    if not enabled:
        log_func("No tasks selected for the master loop. Tick at least one task and start again.")
        return
    wait_min, wait_max = settings_mod.cycle_wait_seconds(settings)
    names = ", ".join(settings_mod.TASK_LABELS[key] for key in enabled)
    log_func(f"Starting master loop (tasks: {names}; "
             f"wait between cycles: {wait_min / 60:g}-{wait_max / 60:g} min; "
             f"per cycle: {quota_summary(settings) or 'bonus only'})...")
    driver.get(YLH_BASE)
    wait_unless_stopped(2, is_stopped)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    steps = _steps(driver, log_func, is_stopped, settings)
    cycle = 0
    while not is_stopped():
        cycle += 1
        log_func(f"=== Master Loop Cycle {cycle} ===")

        for key in enabled:
            if is_stopped():
                break
            label, page, step = steps[key]
            log_func(label)
            try:
                navigate_to(driver, page)
                step()
            except Exception as e:
                log_func(f"{label.rstrip('.')} error: {e.__class__.__name__}: {e}")

        if is_stopped():
            break

        update_points_func(get_points(driver))

        wait_time = random.uniform(wait_min, wait_max)
        log_func(f"Cycle {cycle} complete. Waiting {wait_time / 60:.1f} minutes...")
        wait_unless_stopped(wait_time, is_stopped)

    log_func("Master loop stopped.")


def start_master_loop(setup_browser_func, settings=None):
    """CLI entry point."""
    def task(driver, is_stopped, log_func, update_points_func):
        _run_master_task(driver, is_stopped, log_func, update_points_func, settings=settings)
    run_cli_task("Master Loop", setup_browser_func, task)
