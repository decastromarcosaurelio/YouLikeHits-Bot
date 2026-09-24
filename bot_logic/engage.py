"""Shared flow for the pages where the points come from an action on the
OTHER site: YouTube Likes (youtubelikes.php) and SoundCloud Followers
(soundcloud.php). Read live on 2026-09-21.

Both pages list several cards. A card's button opens the target in a popup
window (the click must be trusted: Chrome's popup blocker is on) and reveals
a confirm control on the YLH page. The bot performs the action inside the
popup (like the video / follow the profile), closes the popup, clicks the
confirm control, and the page's own JS asks the site to verify the action
and writes the reply into a result box.

Replies seen live (2026-09-21, Marco's session): success is "Success! You
followed @user! You got 22 Points!" (SoundCloud) and "You got 21 Points for
liking <title>!" (YouTube). While the other site has not reported
the action yet the page shows "Checking again. We couldn't confirm that
follow just yet. SoundCloud may still be updating..." and re-checks BY
ITSELF; the bot must keep waiting for the final verdict instead of reading
that as a failure. After a YouTube success the page runs its own countdown
and loads the next video.

A card that fails is NOT removed by the site, so every card is tried at most
once per pass (tracked by its id) and the pass ends when only tried cards
are left. The task loop waits and starts a fresh pass.

Each site module describes its page with a `Flow` (selectors and the two
site-specific steps: `open_popup` on the YLH page and `act` inside the popup).
"""
import html
import re
import time
from dataclasses import dataclass
from typing import Callable

from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from .utils import (
    random_delay, wait_until, wait_unless_stopped, close_extra_windows, WindowGuard,
    why_no_item, navigate_to,
)

# Outcomes of Flow.act (what happened inside the popup).
DONE = "done"                     # the action is in place (performed now or before)
NOT_SIGNED_IN = "not_signed_in"   # the other site asks for a login: the pass stops
NOT_FOUND = "not_found"           # control not found / did not react: skip this card

ACTION_GRACE = 4         # hold the popup after the action before trusting the other site's UI
POPUP_WAIT = 15          # for the popup window to appear after the click
CONFIRM_WAIT = 10        # for the YLH confirm control to appear
VERIFY_WAIT = 90         # for the site's final verdict (it re-checks by itself a few times)
SETTLE_WAIT = 15         # unknown wording counts as final once unchanged for this long
VERIFY_AGAIN_WAIT = 5    # for a "verify again" control to appear after a failed check
MAX_VERIFY_RETRIES = 3   # how many times to click the site's own "verify again" before giving up

# Verdicts of the verification reply. Order matters: a success text may
# also say "loading the next video"; a "checking again" text also says
# "couldn't confirm". Credited wins, then pending, then failed.
CREDITED_RE = re.compile(r"\bsuccess\b|\byou got \d+|\bearned\b|\+\s*\d+\s*points?|"
                         r"\d+\s*points?\s*(added|awarded|credited)", re.I)
PENDING_RE = re.compile(r"hang tight|checking (with|again)|confirming|verifying|just yet|"
                        r"may still be|still (be )?(syncing|updating|catching)|ajax-loader|"
                        r"please wait|one moment|\b\d+\s?s\b", re.I)
FAILED_RE = re.compile(r"could ?n.t (confirm|verify)|not (be )?(confirmed|verified)|unable to|"
                       r"no longer|already|try again|failed|error|invalid|expired|skipped", re.I)
# A FAILED reply that will NEVER credit no matter how often it is retried,
# because the action is already done / the site wants the Follow link tapped
# again for a profile we already follow (Instagram/Twitter followers, seen
# live 2026-09-24: "Uh oh ... Please tap the Follow link first, then come back
# and confirm."). Reloading re-queues the profile; the only way out is to
# Skip it so the site drops it from the list. Distinct from a genuine failure
# (rate limit, revert) which we do NOT skip, to keep the slot for a retry.
ALREADY_RE = re.compile(r"tap the follow|already follow|already like|already done|"
                        r"follow link first", re.I)
# What the site says when nothing is left (SoundCloud, seen live: "No more
# tasks at this time. Check back later for more.").
NO_ITEMS_RE = re.compile(r"no more|check back later|nothing (to|left)|no (videos|users|profiles|tasks)\b", re.I)
_LIST_EMPTY = object()

CREDITED, PENDING, FAILED, UNKNOWN = "credited", "pending", "failed", "unknown"


@dataclass(frozen=True)
class Flow:
    label: str            # "Liking" / "Following"
    target: str           # "YouTube" / "SoundCloud" (for messages)
    page: str             # YLH page to reload between cards
    cards: str            # selector of the cards on the YLH page
    confirm: str          # selector of the confirm control revealed after the popup opens
    result_box: str       # where the page writes the verification reply
    list_box: str         # container whose text carries the "nothing left" notice
    open_popup: Callable  # (driver, card, is_stopped) -> bool: click(s) that open the popup
    act: Callable         # (driver, log, is_stopped) -> DONE | NOT_SIGNED_IN | NOT_FOUND, inside the popup
    describe: Callable    # (card) -> short text for the log
    # Optional: when the site offers its own "verify again" retry after a failed
    # check (YouTube Likes: "We couldn't verify your Like just yet" + "Verify My
    # Like Again", "N more attempt available"), `verify_again` returns that
    # button so the bot clicks it and re-checks, up to `max_retries` times.
    # `skip` returns the site's Skip control, clicked to advance the card
    # in-place when verification never credits (better than reloading, which can
    # bring back the same item). Each is a callable (driver) -> element | None.
    # SoundCloud has neither; leave them None.
    verify_again: Callable = None
    skip: Callable = None
    max_retries: int = MAX_VERIFY_RETRIES
    # Optional (driver) -> bool: True once the site has moved past this card on
    # its own (YouTube Likes: after the retries run out it drops the failure
    # message and re-shows the "Like Video" stage for the next video). This is
    # a terminal "not credited" signal, so the bot stops waiting for a verdict
    # that will never come and advances instead of hanging for VERIFY_WAIT.
    advanced: Callable = None
    # Whether to reload the YLH page after each card. True (default) suits
    # pages that only refresh their list on a full reload (YouTube Likes,
    # SoundCloud). The Instagram/Twitter follow pages slide the list by
    # themselves via AJAX -- they remove the finished card and shift the rest
    # up, bringing a new one in at the bottom (seen live 2026-09-24). Reloading
    # those fights that: the user sees the whole list "jump back one" and cards
    # get reshuffled. Set False so the loop just re-reads the DOM the site
    # already updated; `tried` (keyed by the stable `follow<id>`) still avoids
    # re-touching a card within the pass.
    reload_between_cards: bool = True


def _first(driver, selector):
    els = driver.find_elements(By.CSS_SELECTOR, selector)
    return els[0] if els else None


def first_displayed(driver, selector):
    """First element matching `selector` that is displayed, else None."""
    for el in driver.find_elements(By.CSS_SELECTOR, selector):
        try:
            if el.is_displayed():
                return el
        except WebDriverException:
            continue
    return None


def displayed_with_text(driver, selector, needle):
    """First displayed element matching `selector` whose text contains `needle`.

    The needle is matched case-insensitively against the element's text. Used
    to find YLH's own controls by their stable English label (e.g. "Verify My
    Like Again") when they carry no distinctive id -- the site is not
    localised, so matching by that text is safe here (unlike the YouTube /
    SoundCloud buttons, which are localised and must never be matched by text).
    """
    needle = (needle or "").lower()
    for el in driver.find_elements(By.CSS_SELECTOR, selector):
        try:
            if el.is_displayed() and needle in (el.text or "").lower():
                return el
        except WebDriverException:
            continue
    return None


def settle_action(still_done, is_stopped):
    """DONE if `still_done()` holds after ACTION_GRACE seconds, else NOT_FOUND.

    YouTube and SoundCloud flip the button as soon as it is clicked and send
    the request afterwards; closing the popup at once lost 3 of 4 follows live
    (2026-09-21). Waiting lets the request finish and shows a revert.
    """
    wait_unless_stopped(ACTION_GRACE, is_stopped)
    try:
        return DONE if still_done() else NOT_FOUND
    except WebDriverException:
        return NOT_FOUND


def one_line(text, width=160):
    """The site's reply collapsed to one line; entities decoded ("&amp;" seen live)."""
    return " ".join(html.unescape(text or "").split())[:width]


def card_points(card):
    """Points printed on a card ("Points: 21", "+21 points"), or None."""
    m = re.search(r"\+\s*(\d+)|points?\s*:\s*(\d+)|(\d+)\s*points?", card.text or "", re.I)
    return next((int(g) for g in m.groups() if g), None) if m else None


def _page_says_empty(driver, flow):
    """True when the site itself says there is nothing left. Raises on driver errors."""
    box = _first(driver, flow.list_box)
    text = box.text if box else driver.find_element(By.TAG_NAME, "body").text
    return bool(NO_ITEMS_RE.search(text or ""))


def _result(driver, flow):
    """(text, html) of the result box, ('', '') when absent."""
    box = _first(driver, flow.result_box)
    if not box:
        return "", ""
    return (box.text or "").strip(), (box.get_attribute("innerHTML") or "")


def is_credited(text, html):
    return bool(CREDITED_RE.search(text) or "data-points=" in html)


def classify(text, html=""):
    """CREDITED, PENDING, FAILED or UNKNOWN for a verification reply."""
    if is_credited(text, html):
        return CREDITED
    if PENDING_RE.search(text):
        return PENDING
    if FAILED_RE.search(text):
        return FAILED
    return UNKNOWN


def is_already_done(text):
    """True when the reply means 'already done / tap Follow first' (never credits).

    Such a card must be Skipped so the site drops it, not reloaded (a reload
    re-queues it). See ALREADY_RE.
    """
    return bool(ALREADY_RE.search(text or ""))


def process_engage_cards_once(driver, log, is_stopped, flow, limit=None):
    """Work through the cards until none are left, `limit` is hit, or stopped.

    Returns the number of actions the site credited.
    """
    done = 0
    tried = set()
    says_empty = lambda d: _page_says_empty(d, flow)   # noqa: E731

    while not is_stopped() and (limit is None or done < limit):
        def _cards_or_notice():
            cards = driver.find_elements(By.CSS_SELECTOR, flow.cards)
            return cards or (_LIST_EMPTY if says_empty(driver) else None)
        cards = wait_until(_cards_or_notice, timeout=8, is_stopped=is_stopped)
        if cards is _LIST_EMPTY:
            break   # the site says so; the task loop reports it
        if not cards:
            if not is_stopped():
                reason = why_no_item(driver, says_empty)
                if reason == "logged_out":
                    log(f"{flow.label}: not logged in any more. Log in again in the browser window.")
                elif reason == "unknown":
                    log(f"{flow.label}: no '{flow.cards}' on the page and no 'no more' notice; "
                        "the site may have changed.")
            break

        card = next((c for c in cards if c.get_attribute("id") not in tried), None)
        if card is None:
            break   # every card on the page was tried in this pass
        tried.add(card.get_attribute("id"))

        main_window = driver.current_window_handle
        try:
            what = flow.describe(card)
            points = card_points(card)
            log(f"{flow.label} {what}" + (f" ({points} points)..." if points else "..."))
            close_extra_windows(driver, keep=main_window)   # snapshot must be just the YLH tab
            guard = WindowGuard(driver, main_window)
            if not flow.open_popup(driver, card, is_stopped):
                log(f"{flow.label}: could not open this card; skipping it.")
                _advance_page(driver, flow)
                continue

            def _popup():
                guard.prune()
                return guard.popup
            popup = wait_until(_popup, timeout=POPUP_WAIT, is_stopped=is_stopped)
            if not popup:
                if is_stopped():
                    break
                log(f"{flow.label}: the {flow.target} window did not open; skipping this card.")
                _advance_page(driver, flow)
                continue

            driver.switch_to.window(popup)
            outcome = flow.act(driver, log, is_stopped)
            close_extra_windows(driver, keep=main_window)   # our popup and any ads; back to YLH
            if outcome == NOT_SIGNED_IN:
                log(f"{flow.label}: {flow.target} asks you to sign in. Log in to {flow.target} "
                    "in the bot's Chrome window, then this task continues on its next pass.")
                break
            if outcome != DONE:
                log(f"{flow.label}: the {flow.target} page did not react; skipping this card.")
                _advance_page(driver, flow)
                continue

            confirm = wait_until(lambda: first_displayed(driver, flow.confirm),
                                 timeout=CONFIRM_WAIT, is_stopped=is_stopped)
            if not confirm:
                if is_stopped():
                    break
                log(f"{flow.label}: no '{flow.confirm}' to confirm with; the site may have changed.")
                _advance_page(driver, flow)
                continue
            before, _ = _result(driver, flow)
            confirm.click()
            reply = _await_verdict(driver, flow, guard, main_window, before, is_stopped)

            # The site may offer its own "verify again" retry after a failed
            # check (YouTube Likes: "We couldn't verify your Like just yet"). If
            # the flow describes that button, click it and re-check, so a Like
            # YouTube was slow to report still lands, instead of being dropped.
            attempts = 0
            while (flow.verify_again and not is_stopped()
                   and (reply is None or reply[0] in (FAILED, UNKNOWN))
                   and attempts < flow.max_retries):
                again = wait_until(lambda: flow.verify_again(driver),
                                   timeout=VERIFY_AGAIN_WAIT, is_stopped=is_stopped)
                if not again:
                    break               # the site did not offer a retry; take the verdict as-is
                attempts += 1
                log(f"{flow.label}: like not confirmed yet; asking the site to verify again "
                    f"(attempt {attempts}).")
                before, _ = _result(driver, flow)
                again.click()
                reply = _await_verdict(driver, flow, guard, main_window, before, is_stopped)

            close_extra_windows(driver, keep=main_window)
            if is_stopped():
                break

            if reply is not None and reply[0] == CREDITED:
                done += 1
                log(f"{flow.label} credited: {one_line(reply[1])}")
                random_delay(2, 5, is_stopped)
                _advance_page(driver, flow)
                continue

            # Not credited (failed, unknown, or no verdict at all). Advance the
            # card: click the site's Skip if the flow has one (it changes the
            # item in-place; reloading can bring the same one back and stall).
            reply_text = reply[1] if reply is not None else ""
            must_skip = is_already_done(reply_text)   # never credits; only Skip clears it
            if reply is None:
                log(f"{flow.label}: no verdict after the checks; moving on.")
            elif must_skip:
                log(f"{flow.label}: already done / site wants the link tapped again "
                    f"({one_line(reply_text)}); skipping this one.")
            elif reply[0] == FAILED:
                log(f"{flow.label} not credited: {one_line(reply_text)}")
            else:
                log(f"{flow.label}: no clear verdict, counting as not credited: {one_line(reply_text)}")
            # Advance to the next card. If the site already moved on by itself
            # (its retries ran out and it re-showed the "Like Video" stage for
            # the next video), do NOT click Skip -- that would skip the fresh
            # card. For an "already done" reply Skip is mandatory (a reload just
            # re-queues the profile). Otherwise click the site's Skip in-place,
            # falling back to advancing the page.
            already_advanced = False
            if flow.advanced is not None:
                try:
                    already_advanced = bool(flow.advanced(driver))
                except WebDriverException:
                    already_advanced = False
            skipped = False if already_advanced else _skip_card(driver, flow, is_stopped)
            if not skipped and not already_advanced:
                # Could not Skip. For "already done" a reload at least clears
                # the confirm error; for the rest, advance per the flow's rule.
                _reload(driver, flow) if must_skip else _advance_page(driver, flow)
            random_delay(2, 5, is_stopped)
        except WebDriverException as e:
            log(f"Error on {flow.label.lower()}: {e.__class__.__name__}")
            close_extra_windows(driver, keep=main_window)
            _reload(driver, flow)
    return done


def _await_verdict(driver, flow, guard, main_window, before, is_stopped):
    """Poll the result box until the site gives a verdict, or VERIFY_WAIT passes.

    Returns (CREDITED|FAILED|UNKNOWN, text) or None on timeout/stop. The page
    re-checks by itself a few times ("Checking again...") before the final
    verdict; PENDING text keeps the wait alive, unknown wording settles as
    final once it stops changing. Ads are pruned on every poll.
    """
    seen = {"text": "", "since": None, "last": ""}

    def _poll():
        guard.prune()
        driver.switch_to.window(main_window)
        text, html = _result(driver, flow)
        # A "verify again" button in view is itself the verdict: the check
        # failed and the site is offering a manual retry. This must win over
        # the reply text, because YouTube's failure reads "We couldn't verify
        # your Like just yet" -- the same "just yet" the SoundCloud auto-recheck
        # uses, which would otherwise be read as PENDING forever.
        if flow.verify_again is not None:
            try:
                if flow.verify_again(driver):
                    return FAILED, (text or "We couldn't verify your Like yet.")
            except WebDriverException:
                pass
        # The site moved on to the next card by itself (no retry button, the
        # "Like Video" stage is back): a terminal "not credited", so stop
        # waiting instead of polling the result box for VERIFY_WAIT.
        if flow.advanced is not None and classify(text, html) != PENDING:
            try:
                if flow.advanced(driver):
                    return FAILED, (text or "The site moved on without crediting the Like.")
            except WebDriverException:
                pass
        if not text or text == before:
            return None
        seen["last"] = text
        verdict = classify(text, html)
        if verdict in (CREDITED, FAILED):
            return verdict, text
        if verdict == PENDING:
            seen["text"] = ""
            return None
        now = time.monotonic()      # unknown wording: final once it stops changing
        if text != seen["text"]:
            seen["text"], seen["since"] = text, now
        elif now - seen["since"] >= SETTLE_WAIT:
            return UNKNOWN, text
        return None

    return wait_until(_poll, timeout=VERIFY_WAIT, is_stopped=is_stopped, step=0.5)


def _skip_card(driver, flow, is_stopped):
    """Click the site's Skip control to advance the card in-place. Returns True if clicked."""
    if not flow.skip:
        return False
    try:
        skip = flow.skip(driver)
    except WebDriverException:
        return False
    if not skip:
        return False
    try:
        skip.click()
    except WebDriverException:
        return False
    wait_unless_stopped(2, is_stopped)   # let the site swap in the next card
    return True


def _reload(driver, flow):
    navigate_to(driver, flow.page, settle=3)


def _advance_page(driver, flow):
    """Move to a fresh card list. Reload the page unless the site slides its
    own list (see Flow.reload_between_cards), in which case the loop re-reads
    the DOM the site already updated."""
    if flow.reload_between_cards:
        _reload(driver, flow)
