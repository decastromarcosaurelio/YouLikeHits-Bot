"""Shared flow for the YouTube-views and SoundCloud-plays pages.

Live site (verified 2026-09-20): `#listall` holds one `.earn-card` with an
`a.earn-btn` (View / Listen) whose onclick is
`imageWin(<id>, '<key>', '<seconds>', '<x>', ...)`. A native click opens a
popup window and the page's own JS runs a timer, closes the popup, calls the
points endpoint and writes the reply into `#showresult`.

Native (trusted) clicks are required: the page only credits points if the
click event had `isTrusted === true`, so never click via execute_script.
"""
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from .utils import (
    random_delay, wait_unless_stopped, wait_until, close_extra_windows,
)

EARN_BUTTON = "#listall a.earn-btn"
RESULT_BOX = "#showresult"
ONCLICK_RE = re.compile(r"imageWin\((\d+)\s*,\s*'[^']*'\s*,\s*'(\d+)'")
MAX_EXTRA_WAIT = 30   # slack on top of the site's own timer


def _first(driver, selector):
    els = driver.find_elements(By.CSS_SELECTOR, selector)
    return els[0] if els else None


def _result_text(driver):
    box = _first(driver, RESULT_BOX)
    return (box.text if box else "").strip()


def parse_earn_button(onclick, default_seconds):
    """Return (item_id, seconds) from an earn-btn onclick attribute."""
    m = ONCLICK_RE.search(onclick or "")
    if not m:
        return None, default_seconds
    return m.group(1), int(m.group(2))


def process_earn_cards_once(driver, log, is_stopped, *, page, label, default_seconds,
                            reload, limit=None):
    """Work through earn cards until none are left, `limit` is hit, or stopped.

    `reload(driver)` is called after each item to fetch the next card.
    Returns the number of items credited.
    """
    done = 0
    while not is_stopped() and (limit is None or done < limit):
        button = wait_until(lambda: _first(driver, EARN_BUTTON), timeout=8, is_stopped=is_stopped)
        if not button:
            break

        item_id, seconds = parse_earn_button(button.get_attribute("onclick"), default_seconds)
        before = _result_text(driver)
        main_window = driver.current_window_handle
        try:
            log(f"{label} ({seconds}s timer)...")
            button.click()

            # The page's JS closes the popup and writes the outcome into #showresult.
            outcome = wait_until(
                lambda: (lambda t: t if t and t != before else None)(_result_text(driver)),
                timeout=seconds + MAX_EXTRA_WAIT, is_stopped=is_stopped, step=1.0,
            )
            close_extra_windows(driver, keep=main_window)
            if outcome is None:
                if is_stopped():
                    break
                log(f"{label}: no result after {seconds + MAX_EXTRA_WAIT}s; reloading.")
                reload(driver)
                continue

            if _first(driver, "#ytviewok") or re.search(r"earned|\+\s*\d+|point", outcome, re.I):
                done += 1
                log(f"{label} credited: {outcome[:80]}")
            else:
                log(f"{label} not credited: {outcome[:80]}")
            random_delay(2, 5, is_stopped)
            reload(driver)
        except WebDriverException as e:
            log(f"Error on {label.lower()}: {e.__class__.__name__}")
            close_extra_windows(driver, keep=main_window)
            reload(driver)
    return done
