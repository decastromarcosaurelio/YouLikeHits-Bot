"""Twitter (X) likes automation (shared flow in engage.py).

Live site (read 2026-09-24): `favtweets.php` lists `#listall .earn-card`
cards (`id="card<id>"`, "+N points"). The first `a.earn-btn` ("Like") opens
the tweet in a popup via `window.open('https://linkto.social/out.php?url=
<base64 of the tweet url>')` and reveals `a.earn-btn.earn-confirm`
(`id="confirm<id>"`, "I Liked"), whose onclick `favConfirm(id,hash,hash)`
asks the site to verify and writes the reply into `#txtHint`. Each card also
has a Skip link (`favSkip('<id>')`). Unlike YouTube Likes there is no second
stage: one click opens the popup directly. Empty list uses the shared
"no more" notice (engage.NO_ITEMS_RE).

On x.com (read live 2026-09-24, signed in as @marcoa6082): the tweet's Like
control is `button[data-testid="like"]` (aria "N Likes. Like"); it becomes
`data-testid="unlike"` once liked. On a `/status/<id>` page the FIRST like/
unlike button in the DOM is the main tweet's. The button flips before the
request completes, so the popup is held open a few seconds and the state
re-read before it is closed (settle_action). A login gate is a URL under
`/i/flow/login` or `/login`. X labels are localised, so never match by text.
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

PAGE = "favtweets.php"
CARDS = "#listall .earn-card"
LIKE_LINK = "a.earn-btn"                   # inside a card; the confirm one also matches
CONFIRM_BUTTON = "#listall a.earn-confirm"
SKIP_LINK = "#listall a[onclick*='favSkip']"
RESULT_BOX = "#txtHint"
LIST_BOX = "#listall"
# x.com. The main tweet's like button is the first like/unlike in the DOM.
LIKE_BUTTON = "button[data-testid='like']"
LIKED_BUTTON = "button[data-testid='unlike']"
SIGNED_IN = "[data-testid='SideNav_AccountSwitcher_Button']"
LOGIN_GATE = "a[href*='/login'], a[href*='/i/flow/login'], input[name='text'][autocomplete='username']"
PAGE_WAIT = 30
LIKE_WAIT = 10


def _describe(card):
    return (card.text or "").strip().split("\n")[0][:40] or "tweet"


def _open_popup(driver, card, is_stopped):
    """Click the card's Like link (opens the tweet popup, reveals the confirm)."""
    for link in card.find_elements(By.CSS_SELECTOR, LIKE_LINK):
        if "earn-confirm" in (link.get_attribute("class") or ""):
            continue
        link.click()
        return True
    return False


def _blocked(driver):
    """True when x.com shows a login gate instead of the tweet."""
    url = (driver.current_url or "").lower()
    if "/login" in url or "/i/flow/" in url or "/account/access" in url:
        return True
    return bool(driver.find_elements(By.CSS_SELECTOR, LOGIN_GATE)
                and not driver.find_elements(By.CSS_SELECTOR, SIGNED_IN))


def _liked(driver):
    """True once the main tweet shows the unlike (already-liked) control."""
    return first_displayed(driver, LIKED_BUTTON) is not None


def _like_control(driver):
    """The main tweet's like control, whichever state it is in."""
    return first_displayed(driver, LIKED_BUTTON) or first_displayed(driver, LIKE_BUTTON)


def _act(driver, log, is_stopped):
    """Inside the popup: like the tweet on x.com unless already liked."""
    button = wait_until(lambda: _like_control(driver), timeout=PAGE_WAIT, is_stopped=is_stopped)
    if _blocked(driver):
        return NOT_SIGNED_IN
    if not button:
        return NOT_FOUND
    if _liked(driver):
        log("Already liked on X; confirming.")
        return DONE
    button.click()
    if not wait_until(lambda: _liked(driver), timeout=LIKE_WAIT, is_stopped=is_stopped):
        if _blocked(driver):
            return NOT_SIGNED_IN
        return NOT_FOUND
    outcome = settle_action(lambda: _liked(driver), is_stopped)
    if outcome != DONE:
        log("X reverted the like (request failed or rate limited); skipping this tweet.")
    return outcome


def _skip(driver):
    """The card's Skip control (advances the item in-place), or None."""
    return first_displayed(driver, SKIP_LINK)


FLOW = Flow(
    label="Liking", target="X", page=PAGE, cards=CARDS,
    confirm=CONFIRM_BUTTON, result_box=RESULT_BOX, list_box=LIST_BOX,
    open_popup=_open_popup, act=_act, describe=_describe, skip=_skip,
)


def process_twitter_likes_once(driver, log, is_stopped, limit=None):
    """Like tweets until the list runs dry / limit / stop. Returns count credited."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)
    return process_engage_cards_once(driver, log, is_stopped, FLOW, limit=limit)


def _run_twitter_likes_task(driver, is_stopped, log_func, update_points_func):
    """Twitter likes loop (GUI and CLI share this)."""
    log_func("Starting Twitter likes...")
    navigate_to(driver, PAGE)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        update_points_func(get_points(driver))
        liked = process_twitter_likes_once(driver, log_func, is_stopped)
        update_points_func(get_points(driver))
        if is_stopped():
            break
        if liked:
            log_func(f"{liked} like(s) credited. Checking for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No tweets to like. Waiting 1 minute...")
            wait_unless_stopped(60, is_stopped)
        navigate_to(driver, PAGE)

    log_func("Twitter likes loop stopped.")


def start_twitter_likes_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("Twitter Likes", setup_browser_func, _run_twitter_likes_task)
