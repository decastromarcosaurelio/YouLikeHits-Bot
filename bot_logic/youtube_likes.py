"""YouTube likes automation (shared flow in engage.py).

Live site (read 2026-09-21): `youtubelikes.php` lists `#listall .cards`
(`id="card<id>"`, "Points: 21") with `a.followbutton` ("Like", onclick
`viewvideo(id,'<videoid>','<t>')`), which swaps `#listall` for a second
stage: `#FBBox a.earn-btn` ("Like Video") opens the video in a popup (via
linkto.social) and replaces itself with `#ylhManualBtn` ("I'm done, check
now"). That button runs an 8 s countdown ("Hang tight, checking with
YouTube") in `#FBPoints`, then `likeyoutube.php?step=points` writes the
reply there: "You got 21 Points for liking <title>!" (seen live 2026-09-21).
`#DoesLike a` skips the video.

On youtube.com the like button is `like-button-view-model button`
(`aria-pressed="true"` once liked; three match, only one is displayed). The
button flips before the request completes, so the popup is held open for a
few seconds and the state re-read before it is closed. `ytd-masthead
#avatar-btn` ("Menu da conta") means the Chrome profile is signed in;
`a[href*='ServiceLogin']` means it is not. The watch page only renders in a
real window: a background tab stays on its skeleton (see AGENTS.md).
"""
import re
from selenium.webdriver.common.by import By
from .utils import (
    is_logged_in, navigate_to, check_service_unavailable, get_points,
    wait_unless_stopped, wait_until, wait_for_manual_captcha, run_cli_task,
)
from .engage import (
    Flow, process_engage_cards_once, first_displayed, settle_action,
    DONE, NOT_SIGNED_IN, NOT_FOUND,
)

PAGE = "youtubelikes.php"
CARDS = "#listall .cards"
LIKE_LINK = "a.followbutton"             # inside a card: loads the second stage
STAGE2_BUTTON = "#FBBox a.earn-btn"      # "Like Video": opens the popup
CONFIRM_BUTTON = "#ylhManualBtn"         # "I'm done, check now"
RESULT_BOX = "#FBPoints"
LIST_BOX = "#listall"
CAPTCHA_SELECTOR = "img[src*='captcha']"
VIDEO_ID_RE = re.compile(r"viewvideo\(\d+\s*,\s*'([^']+)'")
# youtube.com
LIKE_BUTTON = ("like-button-view-model button, #segmented-like-button button, "
               "ytd-segmented-like-dislike-button-renderer button")
SIGNED_IN = "ytd-masthead #avatar-btn"
SIGN_IN_LINK = ("ytd-masthead a[href*='ServiceLogin'], ytd-masthead a[href*='accounts.google.com'], "
                "ytd-popup-container a[href*='ServiceLogin']")
PAGE_WAIT = 30
LIKE_WAIT = 10
STAGE2_WAIT = 10


def _describe(card):
    for link in card.find_elements(By.CSS_SELECTOR, LIKE_LINK):
        m = VIDEO_ID_RE.search(link.get_attribute("onclick") or "")
        if m:
            return f"video {m.group(1)}"
    return (card.text or "").strip().split("\n")[0][:40]


def _open_popup(driver, card, is_stopped):
    """Click Like on the card (second stage), then "Like Video" (opens the popup)."""
    links = card.find_elements(By.CSS_SELECTOR, LIKE_LINK)
    if not links:
        return False
    links[0].click()
    button = wait_until(lambda: first_displayed(driver, STAGE2_BUTTON),
                        timeout=STAGE2_WAIT, is_stopped=is_stopped)
    if not button:
        return False
    button.click()
    return True


def _liked(button):
    return (button.get_attribute("aria-pressed") or "").lower() == "true"


def _act(driver, log, is_stopped):
    """Inside the popup: like the video unless already liked."""
    button = wait_until(lambda: first_displayed(driver, LIKE_BUTTON),
                        timeout=PAGE_WAIT, is_stopped=is_stopped)
    if not button:
        if driver.find_elements(By.CSS_SELECTOR, SIGN_IN_LINK) and \
                not driver.find_elements(By.CSS_SELECTOR, SIGNED_IN):
            return NOT_SIGNED_IN
        return NOT_FOUND
    if _liked(button):
        log("Already liked; confirming.")
        return DONE
    button.click()
    still_liked = lambda: _liked(first_displayed(driver, LIKE_BUTTON) or button)   # noqa: E731
    if not wait_until(still_liked, timeout=LIKE_WAIT, is_stopped=is_stopped):
        if driver.find_elements(By.CSS_SELECTOR, SIGN_IN_LINK):
            return NOT_SIGNED_IN
        return NOT_FOUND
    outcome = settle_action(still_liked, is_stopped)
    if outcome != DONE:
        log("YouTube reverted the like (request failed or sign-in needed); skipping this video.")
    return outcome


FLOW = Flow(
    label="Liking", target="YouTube", page=PAGE, cards=CARDS,
    confirm=CONFIRM_BUTTON, result_box=RESULT_BOX, list_box=LIST_BOX,
    open_popup=_open_popup, act=_act, describe=_describe,
)


def process_youtube_likes_once(driver, log, is_stopped, limit=None):
    """Like videos until the list runs dry / limit / stop. Returns count credited."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)
    if wait_for_manual_captcha(driver, log, is_stopped, selector=CAPTCHA_SELECTOR):
        return 0
    return process_engage_cards_once(driver, log, is_stopped, FLOW, limit=limit)


def _run_youtube_likes_task(driver, is_stopped, log_func, update_points_func):
    """YouTube likes loop (GUI and CLI share this)."""
    log_func("Starting YouTube likes...")
    navigate_to(driver, PAGE)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        update_points_func(get_points(driver))
        liked = process_youtube_likes_once(driver, log_func, is_stopped)
        update_points_func(get_points(driver))
        if is_stopped():
            break
        if liked:
            log_func(f"{liked} like(s) credited. Checking for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No YouTube videos to like. Waiting 1 minute...")
            wait_unless_stopped(60, is_stopped)
        navigate_to(driver, PAGE)

    log_func("YouTube likes loop stopped.")


def start_youtube_likes_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("YouTube Likes", setup_browser_func, _run_youtube_likes_task)
