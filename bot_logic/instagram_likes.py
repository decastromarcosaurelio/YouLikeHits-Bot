"""Instagram likes automation (shared flow in engage.py).

Live site (read 2026-09-24): `instagramlikes.php` shows ONE `.earn-card` at a
time inside `.iglike-wrap` ("instagram.com/p/<post>", "+N points"). The
`a#iglikebtn.earn-btn` ("Like on Instagram") opens the post in a popup via
`window.open('http://href.li/?https://instagram.com/p/<post>','FB',...)` and
reveals `a.earn-btn.earn-confirm` ("I liked this"), whose onclick
`checkDoesLike()` asks the site to verify and writes the reply into
`#FBPoints` (NOT `#txtHint` -- this page mirrors YouTube Likes' result box).
The Skip control is `FBSkip('<id>')` inside `#DoesLike`. Empty state uses the
shared "no more" notice (engage.NO_ITEMS_RE) in `#FBLike`.

IMPORTANT (verified live 2026-09-24): the connected Instagram account
(`marcoaurelio60822026`) is under a "Confirm you're human to use your account"
challenge, so the post popup redirects to `instagram.com/accounts/suspended/`.
While that holds, `_blocked` returns True and the pass ends with a hint
instead of hanging. Unblock the account in the browser before this can credit.

On instagram.com the post's like control is a `<button>` wrapping an svg
(`svg[aria-label]`); Instagram is localised (pt-BR "Curtir"/"Descurtir"), so
never match by the label text -- key off the aria-label toggling between the
liked and unliked svg. Best-effort, confirmed by settle_action re-reading it.
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

PAGE = "instagramlikes.php"
CARDS = ".iglike-wrap .earn-card"
LIKE_LINK = "a#iglikebtn.earn-btn"
CONFIRM_BUTTON = "#FBLike a.earn-confirm, .iglike-wrap a.earn-confirm"
SKIP_LINK = "#DoesLike a[onclick*='FBSkip']"
RESULT_BOX = "#FBPoints"
LIST_BOX = "#FBLike"
# instagram.com (DOM read live 2026-09-24). The post like button wraps an svg
# whose aria-label toggles: unliked "Curtir"/"Like", liked "Descurtir"/
# "Unlike". IMPORTANT: the post is NOT inside <article>, and the same "Curtir"
# label appears on every COMMENT's like (svg height 16). The POST's like is
# the one with height 24 (the action bar: Like/Comment/Repost/Share/Save all
# 24). So filter by height 24 and take the first in DOM order (the post).
LIKE_ICON = "svg[aria-label]"
POST_ICON_HEIGHT = "24"
LIKED_MARKERS = ("descurtir", "unlike")   # aria-label when already liked (lowercased)
LIKE_MARKERS = ("curtir", "like")         # aria-label when not yet liked (lowercased)
SIGNED_IN = "svg[aria-label='Página inicial'], svg[aria-label='Home'], nav a[href='/']"
BLOCKED_URL_MARKERS = ("/accounts/suspended", "/challenge", "/accounts/login", "/accounts/onetap")
PAGE_WAIT = 30
LIKE_WAIT = 10
SETTLE_BEFORE_CLICK = 3   # let the IG post finish rendering before clicking the like


def _describe(card):
    text = (card.text or "").strip()
    for line in text.split("\n"):
        if "instagram.com/p/" in line:
            return line.strip()[:60]
    return text.split("\n")[0][:40] if text else "post"


def _open_popup(driver, card, is_stopped):
    """Click "Like on Instagram" (opens the post popup, reveals the confirm)."""
    button = first_displayed(driver, LIKE_LINK)
    if not button:
        return False
    button.click()
    return True


def _blocked(driver):
    """True when Instagram shows a suspended/challenge/login gate instead of the post."""
    url = (driver.current_url or "").lower()
    return any(marker in url for marker in BLOCKED_URL_MARKERS)


def _post_like_svg(driver):
    """The POST's like/unlike svg (height 24), skipping comment likes (16).

    Returns the first matching svg in DOM order (the post sits above the
    comments), or None.
    """
    for svg in driver.find_elements(By.CSS_SELECTOR, LIKE_ICON):
        label = (svg.get_attribute("aria-label") or "").lower()
        if not any(m in label for m in LIKED_MARKERS + LIKE_MARKERS):
            continue
        if (svg.get_attribute("height") or "") != POST_ICON_HEIGHT:
            continue          # a comment's like (height 16), not the post's
        return svg
    return None


def _like_button(driver):
    """The clickable button wrapping the post's like svg, or the svg itself."""
    svg = _post_like_svg(driver)
    if svg is None:
        return None
    try:
        return svg.find_element(By.XPATH, "./ancestor::*[self::button or @role='button'][1]")
    except Exception:
        return svg


def _liked(driver):
    """True once the post's like svg reports the liked (unlike/descurtir) state."""
    svg = _post_like_svg(driver)
    if svg is None:
        return False
    return any(m in (svg.get_attribute("aria-label") or "").lower() for m in LIKED_MARKERS)


def _act(driver, log, is_stopped):
    """Inside the popup: like the post on instagram.com unless already liked.

    The connected account is currently under a human-verification challenge
    (see the module docstring); `_blocked` catches that and every other gate,
    ending the pass with a hint instead of waiting for a control that never
    appears.
    """
    button = wait_until(lambda: _like_button(driver), timeout=PAGE_WAIT, is_stopped=is_stopped)
    if _blocked(driver):
        return NOT_SIGNED_IN
    if not button:
        return NOT_FOUND
    if _liked(driver):
        log("Already liked on Instagram; confirming.")
        return DONE
    # Let the post finish rendering, then click the button wrapping the like svg.
    wait_unless_stopped(SETTLE_BEFORE_CLICK, is_stopped)
    button = _like_button(driver) or button
    button.click()
    if not wait_until(lambda: _liked(driver), timeout=LIKE_WAIT, is_stopped=is_stopped):
        if _blocked(driver):
            return NOT_SIGNED_IN
        return NOT_FOUND
    outcome = settle_action(lambda: _liked(driver), is_stopped)
    if outcome != DONE:
        log("Instagram reverted the like (request failed or rate limited); skipping this post.")
    return outcome


def _skip(driver):
    """The card's Skip control (advances the item in-place), or None."""
    return first_displayed(driver, SKIP_LINK)


FLOW = Flow(
    label="Liking", target="Instagram", page=PAGE, cards=CARDS,
    confirm=CONFIRM_BUTTON, result_box=RESULT_BOX, list_box=LIST_BOX,
    open_popup=_open_popup, act=_act, describe=_describe, skip=_skip,
)


def process_instagram_likes_once(driver, log, is_stopped, limit=None):
    """Like posts until the list runs dry / limit / stop. Returns count credited."""
    if check_service_unavailable(driver):
        navigate_to(driver, PAGE)
    return process_engage_cards_once(driver, log, is_stopped, FLOW, limit=limit)


def _run_instagram_likes_task(driver, is_stopped, log_func, update_points_func):
    """Instagram likes loop (GUI and CLI share this)."""
    log_func("Starting Instagram likes...")
    navigate_to(driver, PAGE)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        update_points_func(get_points(driver))
        liked = process_instagram_likes_once(driver, log_func, is_stopped)
        update_points_func(get_points(driver))
        if is_stopped():
            break
        if liked:
            log_func(f"{liked} like(s) credited. Checking for more...")
            wait_unless_stopped(5, is_stopped)
        else:
            log_func("No Instagram posts to like. Waiting 1 minute...")
            wait_unless_stopped(60, is_stopped)
        navigate_to(driver, PAGE)

    log_func("Instagram likes loop stopped.")


def start_instagram_likes_loop(setup_browser_func):
    """CLI entry point."""
    run_cli_task("Instagram Likes", setup_browser_func, _run_instagram_likes_task)
