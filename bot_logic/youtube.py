"""YouTube views automation.

One page-processing function, three callers (GUI loop, CLI loop, master).
"""
import random
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, random_delay,
    get_points, wait_unless_stopped, wait_for_manual_captcha, run_cli_task,
)

PAGE = "youtubenew2.php"
BUTTON_SELECTOR = ".followbutton, a[onclick*='view'], button[onclick*='view']"
SUBMIT_SELECTOR = "input[value='Submit'], button[type='submit']"
CAPTCHA_SELECTOR = "img[src*='captchayt']"


def process_youtube_once(driver, log, is_stopped, limit=None):
    """Do one pass over the YouTube page. Returns number of videos watched."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)

    if wait_for_manual_captcha(driver, log, is_stopped, selector=CAPTCHA_SELECTOR):
        return 0

    buttons = driver.find_elements(By.CSS_SELECTOR, BUTTON_SELECTOR)
    if limit:
        buttons = buttons[:limit]
    if not buttons:
        return 0

    log(f"Found {len(buttons)} YouTube videos to view.")
    watched = 0
    for i, button in enumerate(buttons, 1):
        if is_stopped():
            break
        try:
            if not button.is_displayed():
                continue
            log(f"Watching video {i}/{len(buttons)}...")
            button.click()
            wait_unless_stopped(2, is_stopped)

            log("Waiting for video timer (up to ~2 minutes)...")
            if not wait_unless_stopped(random.uniform(90, 135), is_stopped):
                break

            try:
                driver.find_element(By.CSS_SELECTOR, SUBMIT_SELECTOR).click()
                wait_unless_stopped(2, is_stopped)
            except NoSuchElementException:
                pass

            log("Video viewed.")
            watched += 1
            random_delay(3, 6, is_stopped)
        except WebDriverException as e:
            log(f"Error viewing video: {e.__class__.__name__}")
    return watched


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
        if is_stopped():
            break
        if watched:
            log_func("All videos processed. Refreshing for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No YouTube videos available. Waiting 1 minute...")
            wait_unless_stopped(60, is_stopped)
        navigate_to(driver, PAGE)

    log_func("YouTube views loop stopped.")


def start_youtube_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("YouTube Views", setup_browser_func, _run_youtube_task)
