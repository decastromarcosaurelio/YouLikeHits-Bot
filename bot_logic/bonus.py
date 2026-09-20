"""Daily bonus claimer.

One page-processing function, three callers (GUI loop, CLI loop, master).
"""
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, random_delay,
    get_points, body_text, wait_unless_stopped, run_cli_task,
)

PAGE = "bonuspoints.php"
CLAIM_SELECTOR = ".buybutton, button[onclick*='buy'], a[onclick*='buy']"

# Page states returned by process_bonus_once
CLAIMED = "claimed"
ALREADY_DONE = "already_done"
NOT_AVAILABLE = "not_available"


def process_bonus_once(driver, log, is_stopped):
    """Check the bonus page once and claim if possible. Returns a page state."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)

    text = body_text(driver)
    if "you have made" in text and "hits out of" in text:
        return ALREADY_DONE

    try:
        claim_btn = driver.find_element(By.CSS_SELECTOR, CLAIM_SELECTOR)
        if claim_btn.is_displayed():
            log("Claim button found! Clicking...")
            claim_btn.click()
            wait_unless_stopped(3, is_stopped)
            log("Daily bonus claimed!")
            random_delay(2, 5, is_stopped)
            return CLAIMED
    except NoSuchElementException:
        pass
    except WebDriverException as e:
        log(f"Error claiming bonus: {e.__class__.__name__}")
    return NOT_AVAILABLE


def _run_bonus_task(driver, is_stopped, log_func, update_points_func):
    """Daily bonus loop (GUI and CLI share this)."""
    log_func("Starting daily bonus claimer...")
    navigate_to(driver, PAGE)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        update_points_func(get_points(driver))
        state = process_bonus_once(driver, log_func, is_stopped)
        if is_stopped():
            break
        if state == ALREADY_DONE:
            log_func("Daily bonus already claimed or not enough hits yet. Waiting 5 minutes...")
            wait_unless_stopped(300, is_stopped)
        elif state == NOT_AVAILABLE:
            log_func("No claim button available. Waiting 2 minutes...")
            wait_unless_stopped(120, is_stopped)
        navigate_to(driver, PAGE)

    log_func("Daily bonus claimer stopped.")


def start_bonus_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("Daily Bonus Claimer", setup_browser_func, _run_bonus_task)
