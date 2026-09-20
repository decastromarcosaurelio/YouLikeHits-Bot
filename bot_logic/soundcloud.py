"""SoundCloud plays automation (live flow, see earn.py)."""
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, get_points,
    wait_unless_stopped, run_cli_task,
)
from .earn import process_earn_cards_once

PAGE = "soundcloudplays.php"
BUTTON_SELECTOR = "#listall a.earn-btn"
DEFAULT_SECONDS = 60


def _reload(driver):
    navigate_to(driver, PAGE, settle=3)


def process_soundcloud_once(driver, log, is_stopped, limit=None):
    """Play tracks until the list runs dry / limit / stop. Returns count credited."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)
    return process_earn_cards_once(
        driver, log, is_stopped, page=PAGE, label="Playing track",
        default_seconds=DEFAULT_SECONDS, reload=_reload, limit=limit,
    )


def _run_soundcloud_task(driver, is_stopped, log_func, update_points_func):
    """SoundCloud plays loop (GUI and CLI share this)."""
    log_func("Starting SoundCloud plays...")
    navigate_to(driver, PAGE)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        update_points_func(get_points(driver))
        played = process_soundcloud_once(driver, log_func, is_stopped)
        update_points_func(get_points(driver))
        if is_stopped():
            break
        if played:
            log_func(f"{played} track(s) credited. Checking for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No SoundCloud tracks available. Waiting 1 minute...")
            wait_unless_stopped(60, is_stopped)
        navigate_to(driver, PAGE)

    log_func("SoundCloud plays loop stopped.")


def start_soundcloud_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("SoundCloud Plays", setup_browser_func, _run_soundcloud_task)
