"""SoundCloud plays automation.

One page-processing function, three callers (GUI loop, CLI loop, master).
"""
import random
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, random_delay,
    get_points, wait_unless_stopped, run_cli_task,
)

PAGE = "soundcloudplays.php"
BUTTON_SELECTOR = ".followbutton, a[onclick*='view'], button[onclick*='view']"


def process_soundcloud_once(driver, log, is_stopped, limit=None):
    """Do one pass over the SoundCloud page. Returns number of tracks played."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)

    buttons = driver.find_elements(By.CSS_SELECTOR, BUTTON_SELECTOR)
    if limit:
        buttons = buttons[:limit]
    if not buttons:
        return 0

    log(f"Found {len(buttons)} SoundCloud tracks to play.")
    played = 0
    for i, button in enumerate(buttons, 1):
        if is_stopped():
            break
        try:
            if not button.is_displayed():
                continue
            log(f"Playing track {i}/{len(buttons)}...")
            button.click()
            wait_unless_stopped(2, is_stopped)

            log("Waiting for track to play...")
            if not wait_unless_stopped(random.uniform(30, 60), is_stopped):
                break

            log("Track played.")
            played += 1
            random_delay(2, 5, is_stopped)
        except WebDriverException as e:
            log(f"Error playing track: {e.__class__.__name__}")
    return played


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
        if is_stopped():
            break
        if played:
            log_func("All tracks processed. Refreshing for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No SoundCloud tracks available. Waiting 1 minute...")
            wait_unless_stopped(60, is_stopped)
        navigate_to(driver, PAGE)

    log_func("SoundCloud plays loop stopped.")


def start_soundcloud_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("SoundCloud Plays", setup_browser_func, _run_soundcloud_task)
