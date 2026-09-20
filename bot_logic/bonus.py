"""Daily bonus claimer.

Live site (verified 2026-09-20): `bonuspoints.php` shows "N / M hits" and a
milestone list (10, 25, 50, 100 hits). `.bonus-pill` reads "No bonus to claim
yet" while nothing is claimable; once a milestone is reached it becomes
`.bonus-pill--active` ("Unclaimed Points: +10") and an `a.buybutton` link
("Claim 10 Points Now", href="?step=get") appears. Both states verified live.
"""
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, random_delay,
    get_points, body_text, wait_unless_stopped, run_cli_task,
)

PAGE = "bonuspoints.php"
PILL_SELECTOR = ".bonus-pill"
CLAIM_CANDIDATES = "a.buybutton, a[href*='step=get'], .bonus-row a, .bonus-row button"
HITS_RE = re.compile(r"(\d+)\s*/\s*(\d+)\s*hits", re.I)

# Page states returned by process_bonus_once
CLAIMED = "claimed"
ALREADY_DONE = "already_done"
NOT_AVAILABLE = "not_available"


def hits_progress(text):
    """Return (hits, next_milestone) from 'N / M hits', or (None, None)."""
    m = HITS_RE.search(text or "")
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def _claim_control(driver):
    for el in driver.find_elements(By.CSS_SELECTOR, CLAIM_CANDIDATES):
        try:
            text = (el.text or "").strip().lower()
            if "claim" in text and "no bonus" not in text and el.is_displayed():
                return el
        except WebDriverException:
            continue
    return None


def process_bonus_once(driver, log, is_stopped):
    """Check the bonus page once and claim if possible. Returns a page state."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)

    text = body_text(driver)
    hits, goal = hits_progress(text)
    if hits is not None:
        log(f"Daily hits: {hits}/{goal}.")

    try:
        control = _claim_control(driver)
        if control:
            log("Bonus available! Claiming...")
            control.click()
            wait_unless_stopped(3, is_stopped)
            log("Daily bonus claimed!")
            random_delay(2, 5, is_stopped)
            return CLAIMED
    except WebDriverException as e:
        log(f"Error claiming bonus: {e.__class__.__name__}")

    if "no bonus to claim" in text or (hits is not None and goal and hits < goal):
        return ALREADY_DONE
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
            log_func("No bonus to claim yet (earn more hits). Checking again in 5 minutes...")
            wait_unless_stopped(300, is_stopped)
        elif state == NOT_AVAILABLE:
            log_func("No claim control found. Checking again in 2 minutes...")
            wait_unless_stopped(120, is_stopped)
        navigate_to(driver, PAGE)

    log_func("Daily bonus claimer stopped.")


def start_bonus_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("Daily Bonus Claimer", setup_browser_func, _run_bonus_task)
