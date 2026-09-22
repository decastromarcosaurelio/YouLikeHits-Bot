"""Website views automation.

Live site flow (verified 2026-09-20): the page shows ONE site at a time in
`#wh-flow`. Clicking `#wh-visit` opens the site in a new tab and starts a
JS timer on the YLH page (`#wh-elapsed / N s`). When the timer ends the page
itself calls the points endpoint, shows `.wh-result`, and loads the next site
after ~2 s. `#wh-skip` skips. Empty state: "There are no websites to visit".
"""
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, random_delay,
    get_points, body_text, wait_unless_stopped, wait_until, close_extra_windows,
    WindowGuard, why_no_item,
    seconds_from_text, run_cli_task,
)

PAGE = "websites.php"
VISIT_SELECTOR = "#wh-visit"
SKIP_SELECTOR = "#wh-skip"
STATUS_SELECTOR = ".wh-status"
RESULT_SELECTOR = ".wh-result"
NO_ITEMS_MARKERS = ("no websites to visit", "no websites currently", "no websites visitable")
DEFAULT_SECONDS = 20
MAX_EXTRA_WAIT = 25   # slack on top of the site's own timer


def _find(driver, selector):
    els = driver.find_elements(By.CSS_SELECTOR, selector)
    return els[0] if els else None


def _page_says_empty(driver):
    """True when the site itself says there is nothing to visit. Raises on driver errors."""
    text = driver.find_element(By.TAG_NAME, "body").text.lower()
    return any(m in text for m in NO_ITEMS_MARKERS)


def process_websites_once(driver, log, is_stopped, limit=None):
    """View sites until the page runs dry, `limit` is reached, or we are stopped.

    Returns the number of sites credited.
    """
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)

    viewed = 0
    while not is_stopped() and (limit is None or viewed < limit):
        if any(m in body_text(driver) for m in NO_ITEMS_MARKERS):
            break

        visit = wait_until(lambda: _find(driver, VISIT_SELECTOR), timeout=8, is_stopped=is_stopped)
        if not visit:
            if not is_stopped():
                # A bare "No websites available" from the task loop would hide the cause.
                reason = why_no_item(driver, _page_says_empty)
                if reason == "logged_out":
                    log("Websites: not logged in any more. Log in again in the browser window.")
                elif reason == "unknown":
                    log(f"No '{VISIT_SELECTOR}' on the page and no 'no websites' notice; "
                        "the site may have changed.")
            break

        status = _find(driver, STATUS_SELECTOR)
        seconds = seconds_from_text(status.text if status else "", DEFAULT_SECONDS)
        name = body_text(driver).split("\n")[0][:40]
        main_window = driver.current_window_handle
        try:
            log(f"Viewing website ({seconds}s timer)...")
            close_extra_windows(driver, keep=main_window)   # snapshot must be just the YLH tab
            guard = WindowGuard(driver, main_window)
            visit.click()

            # The site's JS credits points and swaps the card for `.wh-result`.
            # The visited site may spawn pop-unders the whole time the timer
            # runs, so they are pruned on every poll, not only afterwards.
            def _poll():
                guard.prune()
                driver.switch_to.window(main_window)
                return _find(driver, RESULT_SELECTOR)
            result = wait_until(_poll, timeout=seconds + MAX_EXTRA_WAIT,
                                is_stopped=is_stopped, step=1.0)
            close_extra_windows(driver, keep=main_window)
            if result is None:
                if is_stopped():
                    break
                log("Timer did not complete; skipping this site.")
                skip = _find(driver, SKIP_SELECTOR)
                if skip:
                    skip.click()
                continue

            text = " ".join(result.text.split())
            if "earned" in text.lower():
                viewed += 1
                log(f"Website viewed: {text}")
            else:
                log(f"Site not credited: {text or 'unknown result'}")
            # page loads the next card by itself (~2 s)
            wait_unless_stopped(3, is_stopped)
            random_delay(1, 3, is_stopped)
        except WebDriverException as e:
            log(f"Error viewing website: {e.__class__.__name__}")
            close_extra_windows(driver, keep=main_window)
            navigate_to(driver, PAGE)
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
        update_points_func(get_points(driver))
        if is_stopped():
            break
        if viewed:
            log_func(f"{viewed} website(s) viewed. Checking for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No websites available. Waiting 2 minutes...")
            wait_unless_stopped(120, is_stopped)
        navigate_to(driver, PAGE)

    log_func("Website views loop stopped.")


def start_website_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("Website Views", setup_browser_func, _run_website_task)
