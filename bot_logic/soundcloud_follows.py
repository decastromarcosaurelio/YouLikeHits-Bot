"""SoundCloud followers automation (shared flow in engage.py).

Live site (read 2026-09-21): `soundcloud.php` lists `#getpoints .earn-card`
cards (`id="follow<id>"`, `.who` = "@user", `.pts .num` = "+21"). The first
`a.earn-btn` ("Follow") opens `soundcloud.com/<user>` in a popup and reveals
`a.earn-btn.earn-confirm` ("I followed"), whose onclick asks the site to
verify (`soundcloudfollow.php?id=&t=&attempt=`) and writes the reply into
`#txtHint` ("Did you follow @user? Verifying..." first). Empty list: "No more
tasks at this time. Check back later for more."

Replies seen live (2026-09-21): "Success! You followed @user! You got 22
Points!"; while the site re-checks by itself: "Checking again. We couldn't
confirm that follow just yet. SoundCloud may still be updating..."; final
failure: "Uh oh. We couldn't confirm that follow yet. If you already followed
@user, give SoundCloud a moment and try again, or skip this one."

On soundcloud.com (read live, pt-BR locale, so never match by text): the
profile header button is `.userInfoBar button.sc-button-follow`; it gains
`sc-button-selected` (title "Deixar de seguir", text "Seguindo") once you
follow. The button flips BEFORE the request completes, so the popup is held
open for a few seconds and the state re-read before it is closed. A signed-in
session shows `.header__userNavUsernameButton`; a signed-out one shows
`.header__loginMenu`.
"""
from selenium.webdriver.common.by import By
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, get_points,
    wait_unless_stopped, wait_until, run_cli_task,
)
from .engage import (
    Flow, process_engage_cards_once, first_displayed, settle_action,
    DONE, NOT_SIGNED_IN, NOT_FOUND,
)

PAGE = "soundcloud.php"
CARDS = "#getpoints .earn-card"
FOLLOW_LINK = "a.earn-btn"                 # inside a card; the confirm one also matches
CONFIRM_BUTTON = "#getpoints a.earn-confirm"
RESULT_BOX = "#txtHint"
LIST_BOX = "#getpoints"
# soundcloud.com
HEADER_FOLLOW = ".userInfoBar button.sc-button-follow"   # the profile's own button
ANY_FOLLOW = "button.sc-button-follow"                   # fallback if the header markup changes
FOLLOW_BUTTON = f"{HEADER_FOLLOW}, {ANY_FOLLOW}"
FOLLOWED_CLASS = "sc-button-selected"
SIGNED_IN = ".header__userNavUsernameButton"
LOGIN_MENU = ".header__loginMenu, button.loginButton"
PAGE_WAIT = 30
FOLLOW_WAIT = 10


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


def _followed(button):
    return FOLLOWED_CLASS in (button.get_attribute("class") or "")


def _header_button(driver):
    """The profile's own Follow button (header first, any as a fallback)."""
    return first_displayed(driver, HEADER_FOLLOW) or first_displayed(driver, ANY_FOLLOW)


def _act(driver, log, is_stopped):
    """Inside the popup: follow the profile unless already following."""
    button = wait_until(lambda: _header_button(driver), timeout=PAGE_WAIT, is_stopped=is_stopped)
    if driver.find_elements(By.CSS_SELECTOR, LOGIN_MENU) and \
            not driver.find_elements(By.CSS_SELECTOR, SIGNED_IN):
        return NOT_SIGNED_IN
    if not button:
        return NOT_FOUND
    if _followed(button):
        log("Already following; confirming.")
        return DONE
    button.click()
    still_following = lambda: _followed(_header_button(driver) or button)   # noqa: E731
    if not wait_until(still_following, timeout=FOLLOW_WAIT, is_stopped=is_stopped):
        if driver.find_elements(By.CSS_SELECTOR, LOGIN_MENU):
            return NOT_SIGNED_IN
        return NOT_FOUND
    outcome = settle_action(still_following, is_stopped)
    if outcome != DONE:
        log("SoundCloud reverted the follow (request failed or rate limited); skipping this profile.")
    return outcome


FLOW = Flow(
    label="Following", target="SoundCloud", page=PAGE, cards=CARDS,
    confirm=CONFIRM_BUTTON, result_box=RESULT_BOX, list_box=LIST_BOX,
    open_popup=_open_popup, act=_act, describe=_describe,
)


def process_soundcloud_follows_once(driver, log, is_stopped, limit=None):
    """Follow profiles until the list runs dry / limit / stop. Returns count credited."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)
    return process_engage_cards_once(driver, log, is_stopped, FLOW, limit=limit)


def _run_soundcloud_follows_task(driver, is_stopped, log_func, update_points_func):
    """SoundCloud follows loop (GUI and CLI share this)."""
    log_func("Starting SoundCloud follows...")
    navigate_to(driver, PAGE)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        update_points_func(get_points(driver))
        followed = process_soundcloud_follows_once(driver, log_func, is_stopped)
        update_points_func(get_points(driver))
        if is_stopped():
            break
        if followed:
            log_func(f"{followed} follow(s) credited. Checking for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No SoundCloud profiles to follow. Waiting 1 minute...")
            wait_unless_stopped(60, is_stopped)
        navigate_to(driver, PAGE)

    log_func("SoundCloud follows loop stopped.")


def start_soundcloud_follows_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("SoundCloud Follows", setup_browser_func, _run_soundcloud_follows_task)
