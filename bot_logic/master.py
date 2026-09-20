"""Master loop: cycles through every task with a small quota each.

Composes the process_*_once functions so there is no third copy of the logic.
"""
import random
from .utils import (
    YLH_BASE, is_logged_in, navigate_to, get_points, wait_unless_stopped, run_cli_task,
)
from .bonus import process_bonus_once, CLAIMED, PAGE as BONUS_PAGE
from .websites import process_websites_once, PAGE as WEBSITES_PAGE
from .youtube import process_youtube_once, PAGE as YOUTUBE_PAGE
from .soundcloud import process_soundcloud_once, PAGE as SOUNDCLOUD_PAGE

# How many items each task handles per cycle.
WEBSITES_PER_CYCLE = 3
YOUTUBE_PER_CYCLE = 2
SOUNDCLOUD_PER_CYCLE = 2


def _run_master_task(driver, is_stopped, log_func, update_points_func):
    """Master loop (GUI and CLI share this)."""
    log_func("Starting master loop...")
    driver.get(YLH_BASE)
    wait_unless_stopped(2, is_stopped)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    cycle = 0
    while not is_stopped():
        cycle += 1
        log_func(f"=== Master Loop Cycle {cycle} ===")

        steps = (
            ("Checking daily bonus...", BONUS_PAGE,
             lambda: process_bonus_once(driver, log_func, is_stopped) == CLAIMED),
            ("Processing website views...", WEBSITES_PAGE,
             lambda: process_websites_once(driver, log_func, is_stopped, limit=WEBSITES_PER_CYCLE)),
            ("Processing YouTube views...", YOUTUBE_PAGE,
             lambda: process_youtube_once(driver, log_func, is_stopped, limit=YOUTUBE_PER_CYCLE)),
            ("Processing SoundCloud plays...", SOUNDCLOUD_PAGE,
             lambda: process_soundcloud_once(driver, log_func, is_stopped, limit=SOUNDCLOUD_PER_CYCLE)),
        )
        for label, page, step in steps:
            if is_stopped():
                break
            log_func(label)
            try:
                navigate_to(driver, page)
                step()
            except Exception as e:
                log_func(f"{label.rstrip('.')} error: {e.__class__.__name__}: {e}")

        if is_stopped():
            break

        update_points_func(get_points(driver))

        wait_time = random.uniform(60, 180)
        log_func(f"Cycle {cycle} complete. Waiting {wait_time / 60:.1f} minutes...")
        wait_unless_stopped(wait_time, is_stopped)

    log_func("Master loop stopped.")


def start_master_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("Master Loop", setup_browser_func, _run_master_task)
