"""Instagram followers automation (shared flow in engage.py).

Live site (read 2026-09-24): `instagram.php` lists `#getpoints .earn-card`
cards (`id="follow<id>"`, `.who` = "@user", "+N points"). The first
`a.earn-btn` ("Follow") opens `instagramrender.php?uname=<user>` in a popup --
a YLH page that only redirects to `instagram.com/<user>` -- and reveals
`a.earn-btn.earn-confirm` (`id="confirm<id>"`, "I followed"), whose onclick
`followuser(id,user,hash,hash)` asks the site to verify and writes the reply
into `#txtHint`. Empty list uses the same "no more tasks" notice as
SoundCloud (engage.NO_ITEMS_RE). The page is a twin of twitter2.php /
soundcloud.php; only the popup URL and the target site differ.

IMPORTANT (verified live 2026-09-24): the connected Instagram account
(`marcoaurelio60822026`) is under a "Confirm you're human to use your account"
challenge -- `instagramrender.php` redirects to
`instagram.com/accounts/suspended/`. While that holds, `_blocked` returns
True and every card ends the pass with a "sign in / unlock" hint instead of
hanging. Unblock the account in the browser before this task can credit.

On instagram.com the profile header's Follow control is a `<button>` inside
`header`/`main`. Instagram is localised (pt-BR "Seguir"/"Seguindo"), so never
match by text: key off the button that is NOT the "following/message" state.
Following is detected structurally (aria-disabled / the presence of the
message row), best-effort, and confirmed by settle_action re-reading it.
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

PAGE = "instagram.php"
CARDS = "#getpoints .earn-card"
FOLLOW_LINK = "a.earn-btn"                 # inside a card; the confirm one also matches
CONFIRM_BUTTON = "#getpoints a.earn-confirm"
RESULT_BOX = "#txtHint"
LIST_BOX = "#getpoints"
# The card's own Skip link (skipuser(id,user);remove(id)). Used when the site
# re-shows a profile we already follow and rejects the confirm: only Skip
# drops it from the list; a reload re-queues it.
SKIP_LINK = "#getpoints a[onclick*='skipuser']"
# instagram.com (DOM read live 2026-09-24). The header holds several
# `button[type=button]`: the Follow/Following control, the bio-link button
# (svg aria "Ícone de link" / "Link icon") and others. The Follow control is
# the one that is NOT an icon-only button:
#   - not yet following: a button with TEXT and NO svg child ("Seguir"/"Follow")
#   - already following: a button with a dropdown-arrow svg
#     (aria "Ícone de seta para baixo" / "Down chevron icon") and TEXT
# `_profile_button` picks it structurally; `_followed` reads the arrow svg.
# Never match by the localised button text itself.
HEADER_BUTTONS = "header button[type='button'], header section button[type='button']"
# svg aria-labels that mark a header button we must NOT treat as Follow.
NON_FOLLOW_ICONS = ("link", "mensage", "message", "opç", "option", "compartil", "share")
# svg aria-label of the "Following" dropdown arrow (locale variants).
FOLLOWING_ARROW = ("seta para baixo", "down chevron", "chevron", "seta")
SIGNED_IN = "svg[aria-label='Página inicial'], svg[aria-label='Home'], nav a[href='/']"
# A blocked/suspended/challenge/login state: the account cannot act.
BLOCKED_URL_MARKERS = ("/accounts/suspended", "/challenge", "/accounts/login", "/accounts/onetap")
PAGE_WAIT = 30
FOLLOW_WAIT = 10
SETTLE_BEFORE_CLICK = 3   # let the IG profile header finish rendering before clicking
CONFIRM_HOLD = 5          # the follow must stay in place this long (IG flips optimistically)


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
    """True when Instagram shows a suspended/challenge/login gate instead of the profile."""
    url = (driver.current_url or "").lower()
    return any(marker in url for marker in BLOCKED_URL_MARKERS)


def _button_svg_label(button):
    """aria-label (lowercased) of the button's svg child, or '' if none."""
    for svg in button.find_elements(By.CSS_SELECTOR, "svg[aria-label]"):
        return (svg.get_attribute("aria-label") or "").lower()
    return ""


def _profile_button(driver):
    """The profile header's Follow/Following control (not the bio-link button).

    Among the header's `button[type=button]`, the follow control either has no
    svg (the "Seguir" state) or carries the down-chevron svg (the "Seguindo"
    state). Buttons whose svg is a link/message/options/share icon are skipped.
    Returns the element or None.
    """
    for button in driver.find_elements(By.CSS_SELECTOR, HEADER_BUTTONS):
        try:
            if not button.is_displayed():
                continue
        except Exception:
            continue
        label = _button_svg_label(button)
        if any(icon in label for icon in NON_FOLLOW_ICONS):
            continue          # bio-link / message / options / share button
        if not label or any(a in label for a in FOLLOWING_ARROW):
            return button     # no svg (Follow) or the down-chevron (Following)
    return None


def _followed(button):
    """True when the header control shows the 'Following' state (arrow svg)."""
    if button is None:
        return False
    return any(a in _button_svg_label(button) for a in FOLLOWING_ARROW)


def _act(driver, log, is_stopped):
    """Inside the popup: follow the profile on instagram.com unless already following.

    Uses the same guard as the X follow (settle before clicking, confirm the
    follow held) since Instagram also flips the button optimistically. If the
    account is blocked/challenged, `_blocked` ends the pass with a hint.
    """
    button = wait_until(lambda: _profile_button(driver), timeout=PAGE_WAIT, is_stopped=is_stopped)
    if _blocked(driver):
        return NOT_SIGNED_IN
    if not button:
        return NOT_FOUND
    if _followed(button):
        log("Already following on Instagram; confirming.")
        return DONE
    # Let the header settle and re-fetch the button before clicking, so the
    # click lands on the real Follow control and not a bio link mid-render.
    wait_unless_stopped(SETTLE_BEFORE_CLICK, is_stopped)
    button = _profile_button(driver) or button
    if _followed(button):
        log("Already following on Instagram; confirming.")
        return DONE
    button.click()
    still_following = lambda: _followed(_profile_button(driver))   # noqa: E731
    if not wait_until(still_following, timeout=FOLLOW_WAIT, is_stopped=is_stopped):
        if _blocked(driver):
            return NOT_SIGNED_IN
        return NOT_FOUND
    if not _follow_held(driver, is_stopped):
        log("Instagram reverted the follow (request failed or rate limited); skipping this profile.")
        return NOT_FOUND
    return DONE


def _follow_held(driver, is_stopped):
    """True if the profile still shows 'Following' after the request settles.

    Instagram flips the button optimistically like X; watch it stay for
    CONFIRM_HOLD seconds before trusting it.
    """
    deadline = time.monotonic() + CONFIRM_HOLD
    while time.monotonic() < deadline:
        if is_stopped():
            return False
        if not _followed(_profile_button(driver)):
            return False
        wait_unless_stopped(0.5, is_stopped)
    return True


def _skip(driver):
    """The card's Skip control (skipuser removes it from the list), or None."""
    return first_displayed(driver, SKIP_LINK)


FLOW = Flow(
    label="Following", target="Instagram", page=PAGE, cards=CARDS,
    confirm=CONFIRM_BUTTON, result_box=RESULT_BOX, list_box=LIST_BOX,
    open_popup=_open_popup, act=_act, describe=_describe, skip=_skip,
    reload_between_cards=False,   # the site slides its own list via AJAX
)


def process_instagram_follows_once(driver, log, is_stopped, limit=None):
    """Follow profiles until the list runs dry / limit / stop. Returns count credited."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)
    return process_engage_cards_once(driver, log, is_stopped, FLOW, limit=limit)


def _run_instagram_follows_task(driver, is_stopped, log_func, update_points_func):
    """Instagram follows loop (GUI and CLI share this)."""
    log_func("Starting Instagram follows...")
    navigate_to(driver, PAGE)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        update_points_func(get_points(driver))
        followed = process_instagram_follows_once(driver, log_func, is_stopped)
        update_points_func(get_points(driver))
        if is_stopped():
            break
        if followed:
            log_func(f"{followed} follow(s) credited. Checking for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No Instagram profiles to follow. Waiting 1 minute...")
            wait_unless_stopped(60, is_stopped)
        navigate_to(driver, PAGE)

    log_func("Instagram follows loop stopped.")


def start_instagram_follows_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("Instagram Follows", setup_browser_func, _run_instagram_follows_task)
