"""Shared flow for the YouTube-views and SoundCloud-plays pages.

Live site (verified 2026-09-20): `#listall` holds one `.earn-card` with an
`a.earn-btn` (View / Listen) whose onclick is
`imageWin(<id>, '<key>', '<seconds>', '<x>', ...)`. A native click opens a
popup window and the page's own JS runs a timer, closes the popup, calls the
points endpoint and writes the reply into `#showresult`. When nothing is
left, `#listall` holds only a notice ("There are no more songs to play for
points. Check back later!", seen 2026-09-21) and no button.

Native (trusted) clicks are required: the page only credits points if the
click event had `isTrusted === true`, so never click via execute_script.
"""
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from .utils import (
    random_delay, wait_unless_stopped, wait_until, close_extra_windows,
    WindowGuard, why_no_item,
)

EARN_BUTTON = "#listall a.earn-btn"
RESULT_BOX = "#showresult"
ONCLICK_RE = re.compile(r"imageWin\((\d+)\s*,\s*'[^']*'\s*,\s*'(\d+)'")
MAX_EXTRA_WAIT = 30   # slack on top of the site's own timer
LIST_BOX = "#listall"
# What the site writes into #listall when nothing is left. Seen live 2026-09-21
# on SoundCloud: "There are no more songs to play for points. Check back later!"
NO_ITEMS_RE = re.compile(r"there are no more|no more (videos|songs|tracks)|check back later", re.I)
_LIST_EMPTY = object()   # wait_until sentinel: no button, but the site says the list is empty


def _first(driver, selector):
    els = driver.find_elements(By.CSS_SELECTOR, selector)
    return els[0] if els else None


def _result_text(driver):
    box = _first(driver, RESULT_BOX)
    return (box.text if box else "").strip()


def _page_says_empty(driver):
    """True when the site itself reports that the list is empty. Raises on driver errors."""
    box = _first(driver, LIST_BOX)
    text = box.text if box else driver.find_element(By.TAG_NAME, "body").text
    return bool(NO_ITEMS_RE.search(text or ""))


def _one_line(text, width=80):
    """The site's result text collapsed to one line (it comes with newlines)."""
    return " ".join(text.split())[:width]


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
        # Every driver read here goes through wait_until / why_no_item, which
        # swallow driver errors: an unresponsive tab must not kill the loop.
        def _button_or_notice():
            return _first(driver, EARN_BUTTON) or (_LIST_EMPTY if _page_says_empty(driver) else None)
        button = wait_until(_button_or_notice, timeout=8, is_stopped=is_stopped)
        if button is _LIST_EMPTY:
            break   # the site says the list is empty; the task loop reports it
        if not button:
            if not is_stopped():
                # A bare "No ... available" from the task loop would hide the cause.
                reason = why_no_item(driver, _page_says_empty)
                if reason == "logged_out":
                    log(f"{label}: not logged in any more. Log in again in the browser window.")
                elif reason == "unknown":
                    log(f"{label}: no '{EARN_BUTTON}' on the page and no 'no more' notice; "
                        "the site may have changed.")
            break

        item_id, seconds = parse_earn_button(button.get_attribute("onclick"), default_seconds)
        before = _result_text(driver)
        main_window = driver.current_window_handle
        try:
            log(f"{label} ({seconds}s timer)...")
            close_extra_windows(driver, keep=main_window)   # snapshot must be just the YLH tab
            guard = WindowGuard(driver, main_window)
            button.click()

            # The page's JS closes the popup and writes the outcome into #showresult.
            # Pop-unders spawned meanwhile are pruned on every poll.
            def _poll():
                guard.prune()
                driver.switch_to.window(main_window)
                text = _result_text(driver)
                return text if text and text != before else None
            outcome = wait_until(_poll, timeout=seconds + MAX_EXTRA_WAIT,
                                 is_stopped=is_stopped, step=1.0)
            close_extra_windows(driver, keep=main_window)
            if outcome is None:
                if is_stopped():
                    break
                log(f"{label}: no result after {seconds + MAX_EXTRA_WAIT}s; reloading.")
                reload(driver)
                continue

            if _first(driver, "#ytviewok") or re.search(r"earned|\+\s*\d+|point", outcome, re.I):
                done += 1
                log(f"{label} credited: {_one_line(outcome)}")
            else:
                log(f"{label} not credited: {_one_line(outcome)}")
            random_delay(2, 5, is_stopped)
            reload(driver)
        except WebDriverException as e:
            log(f"Error on {label.lower()}: {e.__class__.__name__}")
            close_extra_windows(driver, keep=main_window)
            reload(driver)
    return done
