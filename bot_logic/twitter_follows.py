"""Twitter (X) followers automation (shared flow in engage.py).

Live site (read 2026-09-24): `twitter2.php` lists `#getpoints .earn-card`
cards (`id="follow<id>"`, `.who` = "@user", "+N points"). The first
`a.earn-btn` ("Follow") opens `twitterrender.php?uname=<user>` in a popup --
a YLH page that only redirects to `x.com/<user>` -- and reveals
`a.earn-btn.earn-confirm` (`id="confirm<id>"`, "I followed"), whose onclick
`followuser(id,user,'',hash)` asks the site to verify and writes the reply
into `#txtHint`. Empty list uses the same "no more tasks" notice as
SoundCloud (engage.NO_ITEMS_RE).

On x.com (read live 2026-09-24, signed in as @marcoa6082): the profile's own
Follow control is `button[data-testid$="-follow"]` (aria "Follow @user"); it
becomes `...-unfollow` once you follow. Ignore `a[data-testid=
"AppTabBar_Follow_Link"]` (the left-nav item). The button flips before the
request completes, so the popup is held open a few seconds and the state
re-read before it is closed (settle_action). A signed-in session shows
`[data-testid="SideNav_AccountSwitcher_Button"]`; a login gate is a URL under
`/i/flow/login` or `/login`, or an `a[href*='login']`. X labels are localised
(pt-BR "Seguir"/"Seguindo"), so never match by text -- key off data-testid.
"""
import time

from selenium.webdriver.common.by import By
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, get_points,
    wait_unless_stopped, wait_until, run_cli_task,
)
from .engage import (
    Flow, process_engage_cards_once, first_displayed,
    DONE, NOT_SIGNED_IN, NOT_FOUND,
)

PAGE = "twitter2.php"
CARDS = "#getpoints .earn-card"
FOLLOW_LINK = "a.earn-btn"                 # inside a card; the confirm one also matches
CONFIRM_BUTTON = "#getpoints a.earn-confirm"
RESULT_BOX = "#txtHint"
LIST_BOX = "#getpoints"
# The card's own Skip link on the YLH page (skipuser(id,user);remove(id)).
# Used when the site re-shows a profile we already follow and rejects the
# confirm ("tap the Follow link first"): only Skip drops it from the list; a
# reload re-queues it (seen live 2026-09-24).
SKIP_LINK = "#getpoints a[onclick*='skipuser']"
# x.com
FOLLOW_BUTTON = "button[data-testid$='-follow']"       # the profile's own Follow button
FOLLOWED_BUTTON = "button[data-testid$='-unfollow']"   # what it becomes once following
SIGNED_IN = "[data-testid='SideNav_AccountSwitcher_Button']"
# The "sensitive content" interstitial: the profile header (and its Follow
# button) does not render until this is dismissed. The button is not
# localised in the DOM -- it carries a stable data-testid (read live
# 2026-09-24: emptyState / empty_state_button_text "Yes, view profile").
SENSITIVE_GATE = "[data-testid='emptyState'] [data-testid='empty_state_button_text']"
# A login/interstitial gate on x.com (never reached when the profile renders).
LOGIN_GATE = "a[href*='/login'], a[href*='/i/flow/login'], input[name='text'][autocomplete='username']"
PAGE_WAIT = 30
FOLLOW_WAIT = 10
SETTLE_BEFORE_CLICK = 3   # let the X profile header finish (re)rendering before clicking
CONFIRM_HOLD = 5          # the follow must stay in place this long (X can revert late)


def _describe(card):
    for el in card.find_elements(By.CSS_SELECTOR, ".who"):
        return (el.text or "").strip()
    return (card.text or "").strip().split("\n")[0][:40]


def _open_popup(driver, card, is_stopped):
    """Click the card's Follow link (opens the profile popup, reveals the confirm)."""
    for link in card.find_elements(By.CSS_SELECTOR, FOLLOW_LINK):
        if "earn-confirm" in (link.get_attribute("class") or ""):
            continue
        link.click()
        return True
    return False


def _blocked(driver):
    """True when x.com shows a login gate instead of the profile."""
    url = (driver.current_url or "").lower()
    if "/login" in url or "/i/flow/" in url or "/account/access" in url:
        return True
    return bool(driver.find_elements(By.CSS_SELECTOR, LOGIN_GATE)
                and not driver.find_elements(By.CSS_SELECTOR, SIGNED_IN))


def _followed(button):
    return "-unfollow" in (button.get_attribute("data-testid") or "")


def _profile_button(driver):
    """The profile's own Follow/Unfollow button (whichever is showing)."""
    return (first_displayed(driver, FOLLOWED_BUTTON)
            or first_displayed(driver, FOLLOW_BUTTON))


def _dismiss_sensitive_gate(driver, log, is_stopped):
    """Click "Yes, view profile" if the sensitive-content warning is up.

    Some profiles hide the header (and the Follow button) behind a "Caution:
    this profile may include potentially sensitive content" interstitial
    (seen live 2026-09-24). Dismiss it so the profile renders."""
    gate = first_displayed(driver, SENSITIVE_GATE)
    if gate:
        log("X shows a sensitive-content warning; choosing to view the profile.")
        gate.click()
        wait_unless_stopped(2, is_stopped)


def _act(driver, log, is_stopped):
    """Inside the popup: follow the profile on x.com unless already following."""
    _dismiss_sensitive_gate(driver, log, is_stopped)
    button = wait_until(lambda: _profile_button(driver), timeout=PAGE_WAIT, is_stopped=is_stopped)
    if _blocked(driver):
        return NOT_SIGNED_IN
    if not button:
        return NOT_FOUND
    if _followed(button):
        log("Already following on X; confirming.")
        return DONE
    # X renders the profile header, then re-renders it a beat later; clicking on
    # the first paint flips the button optimistically but the request is dropped
    # when the header re-mounts, so the follow reverts once the page settles
    # (seen live 2026-09-24). Let the header settle and re-fetch the button
    # before clicking so the click lands on the final, interactive control.
    wait_unless_stopped(SETTLE_BEFORE_CLICK, is_stopped)
    button = _profile_button(driver) or button
    if _followed(button):
        log("Already following on X; confirming.")
        return DONE
    button.click()
    still_following = lambda: _followed(_profile_button(driver) or button)   # noqa: E731
    if not wait_until(still_following, timeout=FOLLOW_WAIT, is_stopped=is_stopped):
        if _blocked(driver):
            return NOT_SIGNED_IN
        return NOT_FOUND
    # Confirm the follow HELD after the request completed, not just the
    # optimistic flip: poll a little longer than engage.settle_action's fixed
    # grace, because X can revert several seconds after the click.
    if not _follow_held(driver, is_stopped):
        log("X reverted the follow (request failed or rate limited); skipping this profile.")
        return NOT_FOUND
    return DONE


def _follow_held(driver, is_stopped):
    """True if the profile still shows 'following' after the request settles.

    X flips the button before the request finishes and can revert it a few
    seconds later. Watch the state stay 'following' for CONFIRM_HOLD seconds
    of continuous polling before trusting it; any reverted read fails fast.
    """
    deadline = time.monotonic() + CONFIRM_HOLD
    while time.monotonic() < deadline:
        if is_stopped():
            return False
        button = _profile_button(driver)
        if button is None or not _followed(button):
            return False
        wait_unless_stopped(0.5, is_stopped)
    return True


def _skip(driver):
    """The card's Skip control (skipuser removes it from the list), or None."""
    return first_displayed(driver, SKIP_LINK)


FLOW = Flow(
    label="Following", target="X", page=PAGE, cards=CARDS,
    confirm=CONFIRM_BUTTON, result_box=RESULT_BOX, list_box=LIST_BOX,
    open_popup=_open_popup, act=_act, describe=_describe, skip=_skip,
    reload_between_cards=False,   # the site slides its own list via AJAX
)


def process_twitter_follows_once(driver, log, is_stopped, limit=None):
    """Follow profiles until the list runs dry / limit / stop. Returns count credited."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)
    return process_engage_cards_once(driver, log, is_stopped, FLOW, limit=limit)


def _run_twitter_follows_task(driver, is_stopped, log_func, update_points_func):
    """Twitter follows loop (GUI and CLI share this)."""
    log_func("Starting Twitter follows...")
    navigate_to(driver, PAGE)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        update_points_func(get_points(driver))
        followed = process_twitter_follows_once(driver, log_func, is_stopped)
        update_points_func(get_points(driver))
        if is_stopped():
            break
        if followed:
            log_func(f"{followed} follow(s) credited. Checking for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No Twitter profiles to follow. Waiting 1 minute...")
            wait_unless_stopped(60, is_stopped)
        navigate_to(driver, PAGE)

    log_func("Twitter follows loop stopped.")


def start_twitter_follows_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("Twitter Follows", setup_browser_func, _run_twitter_follows_task)
