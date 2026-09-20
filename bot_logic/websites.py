"""Website views automation.

One page-processing function, three callers (GUI loop, CLI loop, master).
"""
import random
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, random_delay,
    get_points, body_text, wait_unless_stopped, run_cli_task,
)

PAGE = "websites.php"
BUTTON_SELECTOR = ".followbutton, .viewbutton, a[onclick*='view'], button[onclick*='view']"
NO_ITEMS_MARKERS = ("no websites currently", "no websites visitable")


def _close_extra_windows(driver, keep):
    """Close every window except `keep` and switch back to it."""
    try:
        for handle in driver.window_handles:
            if handle != keep:
                driver.switch_to.window(handle)
                driver.close()
        driver.switch_to.window(keep)
    except Exception:
        try:
            driver.switch_to.window(driver.window_handles[0])
        except Exception:
            pass


def process_websites_once(driver, log, is_stopped, limit=None):
    """Do one pass over the websites page.

    Returns the number of websites viewed. 0 with nothing found means the
    caller should back off before trying again.
    """
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)

    text = body_text(driver)
    if any(marker in text for marker in NO_ITEMS_MARKERS):
        return 0

    buttons = driver.find_elements(By.CSS_SELECTOR, BUTTON_SELECTOR)
    if limit:
        buttons = buttons[:limit]
    if not buttons:
        return 0

    log(f"Found {len(buttons)} websites to view.")
    viewed = 0
    for i, button in enumerate(buttons, 1):
        if is_stopped():
            break
        original_window = driver.current_window_handle
        try:
            if not button.is_displayed():
                continue
            log(f"Viewing website {i}/{len(buttons)}...")
            button.click()
            wait_unless_stopped(1, is_stopped)

            new_windows = [w for w in driver.window_handles if w != original_window]
            if new_windows:
                driver.switch_to.window(new_windows[0])
                log("Waiting for website timer...")
                wait_unless_stopped(random.uniform(12, 35), is_stopped)
                _close_extra_windows(driver, keep=original_window)
                log("Website viewed.")
                viewed += 1
            random_delay(2, 5, is_stopped)
        except WebDriverException as e:
            log(f"Error viewing website: {e.__class__.__name__}")
            _close_extra_windows(driver, keep=original_window)
    return viewed


def _run_website_task(driver, is_stopped, log_func, update_points_func):
    """Website views loop (GUI and CLI share this)."""
    log_func("Starting website views...")
    navigate_to(driver, PAGE)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        update_points_func(get_points(driver))
        viewed = process_websites_once(driver, log_func, is_stopped)
        if is_stopped():
            break
        if viewed:
            log_func("All websites viewed. Refreshing for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No websites available. Waiting 2 minutes...")
            wait_unless_stopped(120, is_stopped)
        navigate_to(driver, PAGE)

    log_func("Website views loop stopped.")


def start_website_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("Website Views", setup_browser_func, _run_website_task)
