"""YouTube views automation (live flow, see earn.py)."""
from selenium.webdriver.common.by import By
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, get_points,
    wait_unless_stopped, wait_for_manual_captcha, run_cli_task,
)
from .earn import process_earn_cards_once

PAGE = "youtubenew2.php"
BUTTON_SELECTOR = "#listall a.earn-btn"
CAPTCHA_SELECTOR = "img[src*='captchayt']"
DEFAULT_SECONDS = 120


def _reload(driver):
    navigate_to(driver, PAGE, settle=3)


def process_youtube_once(driver, log, is_stopped, limit=None):
    """Watch videos until the list runs dry / limit / stop. Returns count credited."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)
    if wait_for_manual_captcha(driver, log, is_stopped, selector=CAPTCHA_SELECTOR):
        return 0
    return process_earn_cards_once(
        driver, log, is_stopped, page=PAGE, label="Watching video",
        default_seconds=DEFAULT_SECONDS, reload=_reload, limit=limit,
    )


def _run_youtube_task(driver, is_stopped, log_func, update_points_func):
    """YouTube views loop (GUI and CLI share this)."""
    log_func("Starting YouTube views...")
    navigate_to(driver, PAGE)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        update_points_func(get_points(driver))
        watched = process_youtube_once(driver, log_func, is_stopped)
        update_points_func(get_points(driver))
        if is_stopped():
            break
        if watched:
            log_func(f"{watched} video(s) credited. Checking for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No YouTube videos available. Waiting 1 minute...")
            wait_unless_stopped(60, is_stopped)
        navigate_to(driver, PAGE)

    log_func("YouTube views loop stopped.")


def start_youtube_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("YouTube Views", setup_browser_func, _run_youtube_task)
