"""YouTube Likes and SoundCloud Follows against fake pages that follow the
live flow read on 2026-09-21 (see the module docstrings). Time is virtual."""
import unittest

from bot_logic import (
    youtube_likes, soundcloud_follows, engage, master, settings,
    twitter_follows, instagram_follows, twitter_likes, instagram_likes,
)
from tests.fakes import FakeDriver, FakeElement, logged_in
from tests.test_tasks import _no_sleep, _FakeClock, _stop_after
from unittest import mock
from bot_logic import utils


class _Replies(FakeElement):
    """A result box whose text advances on every read: pending..., then the reply."""

    def __init__(self, texts):
        super().__init__()
        self._texts = list(texts)
        self._reads = 0

    @property
    def text(self):
        value = self._texts[min(self._reads, len(self._texts) - 1)]
        self._reads += 1
        return value

    @text.setter
    def text(self, value):
        pass


class _Reverting(FakeElement):
    """Flips to the done state on click, then reverts a moment later (the request failed)."""

    def __init__(self, text, attr, before, after, revert_after=1.0, **kw):
        super().__init__(text, attrs={attr: before}, **kw)
        self._attr, self._before, self._after = attr, before, after
        self._revert_after, self._clicked_at = revert_after, None

    def click(self):
        super().click()
        self.attrs[self._attr] = self._after
        self._clicked_at = utils.time.monotonic()

    def get_attribute(self, name):
        if name == self._attr and self._clicked_at is not None and \
                utils.time.monotonic() - self._clicked_at >= self._revert_after:
            self.attrs[self._attr] = self._before
        return super().get_attribute(name)


class FakeLikesSite:
    """youtubelikes.php + the youtube.com popup, as a stateful fake."""

    def __init__(self, driver, videos=("vid1",), reply="You earned 21 points!",
                 signed_in=True, like_works=True, already_liked=False, popup_opens=True, revert=False,
                 retry_replies=None, advance_on_exhaustion=False):
        self.d = driver
        self.revert = revert
        self.remaining = list(videos)
        self.reply, self.signed_in, self.like_works = reply, signed_in, like_works
        self.already_liked, self.popup_opens = already_liked, popup_opens
        self.advance_on_exhaustion = advance_on_exhaustion
        # `retry_replies`: replies the site serves on each "Verify My Like
        # Again" click after the first check fails (live 2026-09-22). When the
        # list runs out, the retry button stops appearing (the site advances on
        # its own). None means the site never offers a retry.
        self.retry_replies = list(retry_replies) if retry_replies is not None else None
        self.like_buttons, self.confirm_clicks, self.stage2_clicks = [], 0, 0
        self.verify_again_clicks, self.skip_clicks = 0, 0
        driver.on_get = lambda url: self.reset()
        self.reset()

    def reset(self):
        d = self.d
        d.elements = {**logged_in(), "#FBPoints": [FakeElement("")]}
        d.elements["#listall .cards"] = [self._card(v) for v in self.remaining]
        d.elements["#listall"] = [FakeElement("Start Liking" if self.remaining else "There are no more videos to like right now. Check back later!")]

    def _card(self, vid):
        link = FakeElement("Like", attrs={"onclick": f"viewvideo(1,'{vid}','t');"}, on_click=lambda: self._stage2(vid))
        return FakeElement(f"Points: 21\nLike", attrs={"id": f"card_{vid}"}, children={"a.followbutton": [link]})

    def _stage2(self, vid):
        self.d.elements["#listall .cards"] = []
        self.d.elements["#FBBox a.earn-btn"] = [FakeElement("Like Video", on_click=lambda: self._open_popup(vid))]

    def _open_popup(self, vid):
        self.stage2_clicks += 1
        d = self.d
        if self.popup_opens:
            if self.revert:
                like = _Reverting("", "aria-pressed", "false", "true")
            else:
                like = FakeElement(attrs={"aria-pressed": "true" if self.already_liked else "false"})
                like._on_click = lambda: like.attrs.__setitem__("aria-pressed", "true") if self.like_works else None
            self.like_buttons.append(like)
            page = {"like-button-view-model button": [like]}
            if self.signed_in:
                page["ytd-masthead #avatar-btn"] = [FakeElement()]
            else:
                page["ytd-masthead a[href*='ServiceLogin']"] = [FakeElement("Fazer login")]
            d.open_window("popup", elements=page, url=f"https://www.youtube.com/watch?v={vid}")
        d.elements.pop("#FBBox a.earn-btn")
        d.elements["#ylhManualBtn"] = [FakeElement("I'm done", on_click=lambda: self._verify(vid))]

    def _verify(self, vid, reply=None):
        self.confirm_clicks += 1
        self._settle(vid, self.reply if reply is None else reply)

    def _verify_again(self, vid):
        """What the "Verify My Like Again" button does: re-check with the next reply.

        When the retries run out, the live site (2026-09-22) drops the retry
        button, shows "We still couldn't verify your Like... try another one",
        and re-renders the first "Like Video" stage for the NEXT video. Model
        that with `advance_on_exhaustion=True`.
        """
        self.verify_again_clicks += 1
        self._clear_retry_controls()
        if self.retry_replies:
            self._settle(vid, self.retry_replies.pop(0))
            return
        # Exhausted.
        self.d.elements["#FBPoints"] = [FakeElement(
            "We still couldn't verify your Like. Please make sure you Liked the "
            "video on YouTube, then try another one.")]
        if self.advance_on_exhaustion:
            self.remaining = self.remaining[1:]     # the site moved past this video
            self._show_next_stage()

    def _show_next_stage(self):
        """Re-render the first "Like Video" stage for the next video (site-driven advance)."""
        self.d.elements["#listall .cards"] = []
        nxt = self.remaining[0] if self.remaining else "next"
        self.d.elements["#FBBox a.earn-btn"] = [FakeElement(
            "Like Video", on_click=lambda: self._open_popup(nxt))]

    def _settle(self, vid, reply):
        d = self.d
        if engage.CREDITED_RE.search(reply) and vid in self.remaining:
            self.remaining.remove(vid)
        d.elements["#FBPoints"] = [_Replies(["Hang tight — checking with YouTube. 8s",
                                             "Confirming your Like…", reply])]
        # After a failed check the live site offers a retry button + a skip link
        # (verified 2026-09-22). The failure text is "We couldn't verify your
        # Like just yet", so the presence of the button -- not the wording -- is
        # what marks it a failure. `retry_replies` being a list (even empty)
        # means the site offers the retry; None means it never does.
        if self.retry_replies is not None and not engage.CREDITED_RE.search(reply):
            d.elements["#FBPoints button"] = [FakeElement("Verify My Like Again",
                                                          on_click=lambda: self._verify_again(vid))]
            d.elements["#FBPoints a"] = [FakeElement("[Skip this Video]", on_click=self._skip)]
        else:
            self._clear_retry_controls()

    def _clear_retry_controls(self):
        self.d.elements.pop("#FBPoints button", None)
        self.d.elements.pop("#FBPoints a", None)

    def _skip(self):
        self.skip_clicks += 1
        self._clear_retry_controls()


class FakeFollowSite:
    """soundcloud.php + the soundcloud.com popup, as a stateful fake."""

    def __init__(self, driver, users=("alice",), reply="You earned 21 points!", signed_in=True,
                 follow_works=True, already_following=False, rechecks=(), revert=False):
        self.d = driver
        self.revert = revert
        self.rechecks = list(rechecks)
        self.remaining = list(users)
        self.reply, self.signed_in = reply, signed_in
        self.follow_works, self.already_following = follow_works, already_following
        self.follow_buttons, self.confirm_clicks = [], 0
        driver.on_get = lambda url: self.reset()
        self.reset()

    def reset(self):
        d = self.d
        d.elements = {**logged_in(), "#txtHint": [FakeElement("", displayed=False)]}
        d.elements["#getpoints .earn-card"] = [self._card(u) for u in self.remaining]
        d.elements["#getpoints"] = [FakeElement("Start Following" if self.remaining
                                                else "No more tasks at this time.\nCheck back later for more.")]
        d.elements["#getpoints a.earn-confirm"] = []

    def _card(self, user):
        confirm = FakeElement("✓ I followed", displayed=False, attrs={"class": "earn-btn earn-confirm"},
                              on_click=lambda: self._verify(user))
        follow = FakeElement("Follow", attrs={"class": "earn-btn"},
                             on_click=lambda: self._open_popup(user, confirm))
        return FakeElement(f"@{user}\n+21 points", attrs={"id": f"follow_{user}"},
                           children={"a.earn-btn": [follow, confirm], ".who": [FakeElement(f"@{user}")]})

    def _open_popup(self, user, confirm):
        if self.revert:
            button = _Reverting("Seguir", "class", "sc-button-follow sc-button",
                                "sc-button-follow sc-button sc-button-selected")
        else:
            button = FakeElement("Seguir", attrs={"class": "sc-button-follow sc-button" +
                                                  (" sc-button-selected" if self.already_following else "")})
            button._on_click = lambda: button.attrs.__setitem__(
                "class", "sc-button-follow sc-button sc-button-selected") if self.follow_works else None
        self.follow_buttons.append(button)
        page = {".userInfoBar button.sc-button-follow": [button]}
        if self.signed_in:
            page[".header__userNavUsernameButton"] = [FakeElement()]
        else:
            page[".header__loginMenu"] = [FakeElement("Sign in")]
        self.d.open_window("popup", elements=page, url=f"https://soundcloud.com/{user}")
        confirm._displayed = True
        self.d.elements["#getpoints a.earn-confirm"] = [confirm]

    def _verify(self, user):
        self.confirm_clicks += 1
        if engage.CREDITED_RE.search(self.reply) and user in self.remaining:
            self.remaining.remove(user)
        self.d.elements["#txtHint"] = [_Replies(["Did you follow @%s? Verifying..." % user]
                                                + self.rechecks + [self.reply])]


class YouTubeLikesTests(unittest.TestCase):
    def test_like_is_performed_confirmed_and_credited(self):
        d = FakeDriver(elements=logged_in()); site = FakeLikesSite(d)
        logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 1)
        self.assertEqual([b.clicks for b in site.like_buttons], [1])
        self.assertEqual(site.confirm_clicks, 1)
        self.assertEqual(d.window_handles, ["main"])            # popup closed by the bot
        self.assertEqual(d.current_window_handle, "main")
        self.assertTrue(any("Liking video vid1 (21 points)" in m for m in logs), logs)
        line = next(m for m in logs if "credited" in m)
        self.assertIn("You earned 21 points", line)
        self.assertTrue(any(youtube_likes.PAGE in u for u in d.visited))   # reloaded for the next card

    def test_already_liked_video_is_confirmed_without_clicking(self):
        d = FakeDriver(elements=logged_in()); site = FakeLikesSite(d, already_liked=True)
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, lambda m: None, lambda: False), 1)
        self.assertEqual(site.like_buttons[0].clicks, 0)
        self.assertEqual(site.confirm_clicks, 1)

    def test_not_signed_in_to_youtube_ends_the_pass_with_a_hint(self):
        d = FakeDriver(elements=logged_in()); site = FakeLikesSite(d, signed_in=False, like_works=False)
        logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        self.assertEqual(site.confirm_clicks, 0)
        self.assertTrue(any("sign in" in m.lower() and "YouTube" in m for m in logs), logs)
        self.assertEqual(d.window_handles, ["main"])

    def test_like_that_does_not_register_skips_the_card(self):
        d = FakeDriver(elements=logged_in()); site = FakeLikesSite(d, like_works=True, videos=("v1", "v2"))
        site.like_works = False
        logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        self.assertEqual(site.confirm_clicks, 0)
        self.assertEqual(len(site.like_buttons), 2)              # both cards tried once, then the pass ends
        self.assertTrue(any("did not react" in m for m in logs), logs)

    def test_uncredited_card_is_not_retried_in_the_same_pass(self):
        d = FakeDriver(elements=logged_in())
        site = FakeLikesSite(d, reply="Sorry, we could not verify your like. Try again.")
        logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        self.assertEqual(site.confirm_clicks, 1)
        self.assertTrue(any("not credited" in m and "could not verify" in m for m in logs), logs)

    def test_second_card_is_tried_after_the_first_fails(self):
        d = FakeDriver(elements=logged_in())
        site = FakeLikesSite(d, videos=("v1", "v2"), reply="Could not verify.")
        replies = iter(["Could not verify.", "21 Points Added!"])
        original = site._verify

        def verify(vid):
            site.reply = next(replies)
            original(vid)
        site._verify = verify
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, lambda m: None, lambda: False), 1)
        self.assertEqual(site.confirm_clicks, 2)
        self.assertEqual(site.remaining, ["v1"])

    def test_verify_again_retry_that_finally_credits(self):
        # Live 2026-09-22: a Like YouTube was slow to report shows "We couldn't
        # verify your Like just yet" + a "Verify My Like Again" button; clicking
        # it re-checks and can then credit.
        d = FakeDriver(elements=logged_in())
        site = FakeLikesSite(d, reply="We couldn't verify your Like just yet.",
                             retry_replies=["You got 21 Points for liking the video!"])
        logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 1)
        self.assertEqual(site.confirm_clicks, 1)
        self.assertEqual(site.verify_again_clicks, 1)          # the bot asked the site to re-check once
        self.assertEqual(site.skip_clicks, 0)                  # credited, so never skipped
        self.assertTrue(any("verify again (attempt 1)" in m.lower() for m in logs), logs)
        self.assertTrue(any("credited: You got 21 Points" in m for m in logs), logs)

    def test_verify_again_exhausted_moves_on_without_stalling(self):
        # After the retries run out the like is still unconfirmed; the bot must
        # advance (skip if the site still shows one, else reload) instead of
        # retrying the same card forever.
        d = FakeDriver(elements=logged_in())
        site = FakeLikesSite(d, videos=("v1", "v2"), reply="We couldn't verify your Like just yet.",
                             retry_replies=["We still couldn't verify your Like."])
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        self.assertGreaterEqual(site.verify_again_clicks, 1)   # retried what the site offered
        self.assertTrue(any("not credited" in m for m in logs), logs)
        self.assertLess(clock.now, engage.VERIFY_WAIT)         # did not hang
        # Both cards were worked through (the pass ended), proving it did not stall.
        self.assertTrue(any(youtube_likes.PAGE in u for u in d.visited), logs)

    def test_site_advancing_on_its_own_does_not_hang_or_skip_the_next_video(self):
        # Live bug 2026-09-22: after "Verify My Like Again" ran out, the site
        # dropped the retry button, showed "We still couldn't verify your
        # Like... try another one", and re-rendered the "Like Video" stage for
        # the NEXT video. The bot hung waiting for a verdict that never came.
        # It must detect the advance, not hang, and not skip the fresh card.
        d = FakeDriver(elements=logged_in())
        site = FakeLikesSite(d, videos=("v1", "v2"), reply="We couldn't verify your Like just yet.",
                             retry_replies=[], advance_on_exhaustion=True)
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False, limit=1)
        self.assertGreaterEqual(site.verify_again_clicks, 1)   # asked the site to verify again
        self.assertEqual(site.skip_clicks, 0)                  # never clicked Skip on the fresh card
        self.assertTrue(any("not credited" in m for m in logs), logs)
        self.assertLess(clock.now, engage.VERIFY_WAIT)         # did not hang for the full timeout

    def test_verify_again_is_capped_at_max_retries(self):
        # The site keeps offering the retry, but the bot stops after MAX_VERIFY_RETRIES.
        d = FakeDriver(elements=logged_in())
        site = FakeLikesSite(d, reply="We couldn't verify your Like just yet.",
                             retry_replies=["We couldn't verify your Like just yet."] * 10)
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, lambda m: None, lambda: False, limit=1), 0)
        self.assertEqual(site.verify_again_clicks, engage.MAX_VERIFY_RETRIES)
        self.assertGreaterEqual(site.skip_clicks, 1)

    def test_success_wording_wins_over_loading_words(self):
        d = FakeDriver(elements=logged_in())
        site = FakeLikesSite(d, reply="Success! You liked the video! You got 22 Points! Loading the next video...")
        logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 1)
        self.assertEqual(site.confirm_clicks, 1)
        self.assertTrue(any("credited: Success! You liked the video! You got 22 Points!" in m for m in logs), logs)

    def test_like_that_reverts_after_the_click_is_not_confirmed(self):
        d = FakeDriver(elements=logged_in()); site = FakeLikesSite(d, revert=True)
        logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        self.assertEqual(site.confirm_clicks, 0)
        self.assertTrue(any("reverted the like" in m for m in logs), logs)

    def test_popup_stays_open_for_the_grace_period_after_the_like(self):
        d = FakeDriver(elements=logged_in()); site = FakeLikesSite(d)
        closed_at = {}
        orig_close = d.close
        clock = _FakeClock()

        def close():
            closed_at.setdefault(d.current_window_handle, clock.now); orig_close()
        d.close = close
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, lambda m: None, lambda: False), 1)
        self.assertGreaterEqual(closed_at["popup"], engage.ACTION_GRACE)
        self.assertEqual(site.like_buttons[0].clicks, 1)

    def test_popup_that_never_opens_is_reported_and_skipped(self):
        d = FakeDriver(elements=logged_in()); site = FakeLikesSite(d, popup_opens=False)
        logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        self.assertEqual(site.stage2_clicks, 1)
        self.assertTrue(any("did not open" in m for m in logs), logs)

    def test_verification_that_never_replies_moves_on(self):
        d = FakeDriver(elements=logged_in()); site = FakeLikesSite(d)
        site._verify = lambda vid, reply=None: d.elements.__setitem__(
            "#FBPoints", [FakeElement("Hang tight — checking with YouTube. 8s")])
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        # No verdict and no retry button: the bot gives up on this card (there is
        # no skip control here, so it reloads) instead of hanging.
        self.assertTrue(any("no verdict after the checks" in m for m in logs), logs)

    def test_limit_and_stop(self):
        d = FakeDriver(elements=logged_in()); FakeLikesSite(d, videos=("a", "b", "c"))
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, lambda m: None, lambda: False, limit=2), 2)
        d = FakeDriver(elements=logged_in()); FakeLikesSite(d)
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, lambda m: None, _stop_after(2)), 0)

    def test_empty_notice_is_not_a_missing_card(self):
        d = FakeDriver(elements=logged_in()); FakeLikesSite(d, videos=())
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        self.assertFalse(any("site may have changed" in m for m in logs), logs)
        self.assertLess(clock.now, 8)

    def test_missing_cards_without_notice_warns_and_dead_session_is_logged_out(self):
        d = FakeDriver(body="Start Liking\nsome layout we do not know", elements=logged_in())
        d.elements["#listall"] = [FakeElement("Some Video Title")]
        logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        self.assertTrue(any("site may have changed" in m and youtube_likes.CARDS in m for m in logs), logs)
        dead = FakeDriver(body="Username\nPassword\nLogin"); logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(dead, logs.append, lambda: False), 0)
        self.assertTrue(any("not logged in" in m.lower() for m in logs), logs)

    def test_popunders_during_verification_are_pruned(self):
        d = FakeDriver(elements=logged_in()); site = FakeLikesSite(d)
        polls = {"n": 0}
        real_verify = site._verify

        def verify(vid):
            real_verify(vid)
            box = d.elements["#FBPoints"][0]
            real_find = d.find_elements

            def spawning_find(by, value):
                if value == youtube_likes.RESULT_BOX and d.current_window_handle == "main":
                    polls["n"] += 1
                    d.window_handles.extend(f"ad{polls['n']}-{i}" for i in range(20))
                return real_find(by, value)
            d.find_elements = spawning_find
        site._verify = verify
        peak = {"tabs": 0}; orig = d.window

        def sw(h):
            peak["tabs"] = max(peak["tabs"], len(d.window_handles)); orig(h)
        d.window = sw
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, lambda m: None, lambda: False, limit=1), 1)
        self.assertEqual(d.window_handles, ["main"])
        self.assertLess(peak["tabs"], 45)

    def test_captcha_pauses(self):
        d = FakeDriver(elements={**logged_in(), "img[src*='captcha']": [FakeElement()]})
        logs = []
        with _no_sleep():
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        self.assertTrue(any("Captcha" in m for m in logs))


class SoundCloudFollowsTests(unittest.TestCase):
    def test_follow_is_performed_confirmed_and_credited(self):
        d = FakeDriver(elements=logged_in()); site = FakeFollowSite(d)
        logs = []
        with _no_sleep():
            self.assertEqual(soundcloud_follows.process_soundcloud_follows_once(d, logs.append, lambda: False), 1)
        self.assertEqual([b.clicks for b in site.follow_buttons], [1])
        self.assertEqual(site.confirm_clicks, 1)
        self.assertEqual(d.window_handles, ["main"])
        self.assertTrue(any("Following @alice (21 points)" in m for m in logs), logs)
        self.assertTrue(any("credited: You earned 21 points" in m for m in logs), logs)

    def test_already_following_confirms_without_clicking(self):
        d = FakeDriver(elements=logged_in()); site = FakeFollowSite(d, already_following=True)
        with _no_sleep():
            self.assertEqual(soundcloud_follows.process_soundcloud_follows_once(d, lambda m: None, lambda: False), 1)
        self.assertEqual(site.follow_buttons[0].clicks, 0)
        self.assertEqual(site.confirm_clicks, 1)

    def test_not_signed_in_to_soundcloud_ends_the_pass_with_a_hint(self):
        d = FakeDriver(elements=logged_in()); site = FakeFollowSite(d, signed_in=False, follow_works=False)
        logs = []
        with _no_sleep():
            self.assertEqual(soundcloud_follows.process_soundcloud_follows_once(d, logs.append, lambda: False), 0)
        self.assertEqual(site.confirm_clicks, 0)
        self.assertEqual(site.follow_buttons[0].clicks, 0)      # never clicks a Follow that would open a login modal
        self.assertTrue(any("sign in" in m.lower() and "SoundCloud" in m for m in logs), logs)

    def test_uncredited_reply_is_logged_and_the_card_is_not_retried(self):
        d = FakeDriver(elements=logged_in())
        site = FakeFollowSite(d, users=("a", "b"), reply="We could not verify your follow. Try again later.")
        logs = []
        with _no_sleep():
            self.assertEqual(soundcloud_follows.process_soundcloud_follows_once(d, logs.append, lambda: False), 0)
        self.assertEqual(site.confirm_clicks, 2)                 # each card once, then the pass ends
        self.assertEqual(sum("not credited" in m for m in logs), 2)

    def test_follow_that_reverts_after_the_click_is_not_confirmed(self):
        # Live 2026-09-21: SoundCloud flipped the button, the popup was closed at
        # once, and 3 of 4 follows never reached SoundCloud.
        d = FakeDriver(elements=logged_in()); site = FakeFollowSite(d, users=("a", "b"), revert=True)
        logs = []
        with _no_sleep():
            self.assertEqual(soundcloud_follows.process_soundcloud_follows_once(d, logs.append, lambda: False), 0)
        self.assertEqual(site.confirm_clicks, 0)
        self.assertEqual(sum("reverted the follow" in m for m in logs), 2)
        self.assertEqual(d.window_handles, ["main"])

    def test_live_success_wording_is_credited(self):
        # Seen live 2026-09-21; the first version logged this as "not credited".
        d = FakeDriver(elements=logged_in())
        site = FakeFollowSite(d, reply="Success! You followed @alice! You got 22 Points!")
        logs = []
        with _no_sleep():
            self.assertEqual(soundcloud_follows.process_soundcloud_follows_once(d, logs.append, lambda: False), 1)
        self.assertTrue(any("credited: Success! You followed @alice! You got 22 Points!" in m for m in logs), logs)
        self.assertEqual(site.remaining, [])

    def test_site_rechecking_by_itself_is_waited_for(self):
        # Seen live 2026-09-21: the page re-checks on its own; the first version
        # read the interim text as a failure, reloaded, and lost the follow.
        d = FakeDriver(elements=logged_in())
        site = FakeFollowSite(d, reply="Success! You followed @alice! You got 22 Points!",
                              rechecks=["Checking again We couldn't confirm that follow just yet. "
                                        "SoundCloud may still be updating its follower count."] * 3)
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            self.assertEqual(soundcloud_follows.process_soundcloud_follows_once(d, logs.append, lambda: False), 1)
        self.assertEqual(site.confirm_clicks, 1)                 # the site retried, not the bot
        self.assertFalse(any("not credited" in m for m in logs), logs)
        self.assertEqual(len(d.visited), 1)                      # reloaded once, after the verdict

    def test_unknown_wording_settles_as_not_credited(self):
        d = FakeDriver(elements=logged_in())
        FakeFollowSite(d, reply="Hmm. Something unexpected came back from the follow check.")
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            self.assertEqual(soundcloud_follows.process_soundcloud_follows_once(d, logs.append, lambda: False), 0)
        self.assertTrue(any("no clear verdict" in m and "Something unexpected" in m for m in logs), logs)
        self.assertGreaterEqual(clock.now, engage.SETTLE_WAIT)
        self.assertLess(clock.now, engage.VERIFY_WAIT)

    def test_empty_notice_is_not_a_missing_card(self):
        d = FakeDriver(elements=logged_in()); FakeFollowSite(d, users=())
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            self.assertEqual(soundcloud_follows.process_soundcloud_follows_once(d, logs.append, lambda: False), 0)
        self.assertFalse(any("site may have changed" in m for m in logs), logs)
        self.assertLess(clock.now, 8)

    def test_unresponsive_tab_does_not_kill_the_loop(self):
        d = FakeDriver(elements=logged_in())

        def boom(*a, **k):
            raise RuntimeError("timed out receiving message from renderer")
        d.find_elements = boom; d.find_element = boom
        logs = []
        with _no_sleep():
            self.assertEqual(soundcloud_follows.process_soundcloud_follows_once(d, logs.append, lambda: False), 0)
        self.assertFalse(any("site may have changed" in m or "not logged in" in m.lower() for m in logs), logs)


class FakeExternalFollowSite:
    """A `#getpoints` follow page (twitter2.php / instagram.php) whose popup
    lands on the external profile. `state` drives the profile button: a
    stateful fake mirroring the live flow read 2026-09-24.

    `mode` picks the site's markup:
      - "x": follow button is `button[data-testid='<id>-follow']`, becomes
        `-unfollow`; signed in shows the account-switcher.
      - "ig": header button carries a class that gains 'following'; signed in
        shows the home nav.
    `blocked_url` (e.g. an x.com login flow or instagram suspended page) makes
    the popup land on a gate so the act must return NOT_SIGNED_IN.
    """

    def __init__(self, driver, module, mode, users=("alice",), reply="You earned 21 points!",
                 blocked_url=None, follow_works=True, already_following=False, revert=False,
                 sensitive=False):
        self.d = driver
        self.module, self.mode = module, mode
        self.users, self.remaining = list(users), list(users)
        self.reply, self.blocked_url = reply, blocked_url
        self.follow_works, self.already_following, self.revert = follow_works, already_following, revert
        self.sensitive = sensitive
        self.follow_buttons, self.confirm_clicks, self.skip_clicks = [], 0, 0
        self.gate_clicks = 0
        driver.on_get = lambda url: self.reset()
        self.reset()

    def reset(self):
        d = self.d
        d.elements = {**logged_in(), "#txtHint": [FakeElement("", displayed=False)]}
        d.elements["#getpoints .earn-card"] = [self._card(u) for u in self.remaining]
        d.elements["#getpoints"] = [FakeElement("Start Following" if self.remaining
                                                else "No more tasks at this time.\nCheck back later for more.")]
        d.elements["#getpoints a.earn-confirm"] = []
        d.elements["#getpoints a[onclick*='skipuser']"] = [
            FakeElement("Skip", attrs={"onclick": f"skipuser('{u}','x');remove('{u}');"},
                        on_click=lambda u=u: self._skip(u)) for u in self.remaining]

    def _skip(self, user):
        self.skip_clicks += 1
        if user in self.remaining:
            self.remaining.remove(user)

    def _card(self, user):
        confirm = FakeElement("I followed", displayed=False, attrs={"class": "earn-btn earn-confirm"},
                              on_click=lambda: self._verify(user))
        follow = FakeElement("Follow", attrs={"class": "earn-btn"},
                             on_click=lambda: self._open_popup(user, confirm))
        return FakeElement(f"@{user}\n+21 points", attrs={"id": f"follow_{user}"},
                           children={"a.earn-btn": [follow, confirm], ".who": [FakeElement(f"@{user}")]})

    def _x_button(self):
        followed = " -unfollow" if self.already_following else ""
        tid = f"9988{'-unfollow' if self.already_following else '-follow'}"
        if self.revert:
            b = _Reverting("Seguir", "data-testid", "9988-follow", "9988-unfollow")
        else:
            b = FakeElement("Seguir", attrs={"data-testid": tid})
            b._on_click = lambda: b.attrs.__setitem__("data-testid", "9988-unfollow") if self.follow_works else None
        return b, ("button[data-testid$='-follow']" if not self.already_following
                   else "button[data-testid$='-unfollow']")

    def _ig_button(self):
        # The real code reads the button's child svg[aria-label]: the "Seguindo"
        # state carries a down-chevron svg, "Seguir" has none. Model that.
        arrow = [FakeElement(attrs={"aria-label": "Ícone de seta para baixo"})]

        def set_following():
            if self.follow_works:
                b.children["svg[aria-label]"] = arrow
        b = FakeElement("Seguir", attrs={"type": "button"},
                        children={"svg[aria-label]": (arrow if self.already_following else [])})
        b._on_click = set_following
        return b

    def _open_popup(self, user, confirm):
        d = self.d
        if self.blocked_url:
            d.open_window("popup", elements={}, url=self.blocked_url)
        elif self.mode == "x":
            button, sel = self._x_button()
            self.follow_buttons.append(button)
            page = {sel: [button], "button[data-testid$='-follow']": [button],
                    "button[data-testid$='-unfollow']": ([button] if self.already_following else [])}
            page["[data-testid='SideNav_AccountSwitcher_Button']"] = [FakeElement()]
            if self.sensitive:
                # The header (and its follow button) is hidden until the
                # "Yes, view profile" gate is dismissed.
                gate_sel = "[data-testid='emptyState'] [data-testid='empty_state_button_text']"
                hidden = dict(page)
                page = {gate_sel: [FakeElement("Yes, view profile",
                                               on_click=lambda h=hidden: self._reveal(h))],
                        "[data-testid='SideNav_AccountSwitcher_Button']": [FakeElement()]}
                self._pending_reveal = (gate_sel, hidden)
            d.open_window("popup", elements=page, url=f"https://x.com/{user}")
        else:   # ig
            button = self._ig_button()
            self.follow_buttons.append(button)
            # A bio-link button (svg "Ícone de link") comes first in the header
            # DOM order; the real code must skip it and pick the follow button.
            bio_link = FakeElement("bio link", attrs={"type": "button"},
                                   children={"svg[aria-label]": [FakeElement(attrs={"aria-label": "Ícone de link"})]})
            page = {"header button[type='button']": [bio_link, button],
                    "nav a[href='/']": [FakeElement()]}
            d.open_window("popup", elements=page, url=f"https://www.instagram.com/{user}/")
        confirm._displayed = True
        d.elements["#getpoints a.earn-confirm"] = [confirm]

    def _reveal(self, hidden):
        """Dismiss the sensitive gate: swap the popup page for the real header."""
        self.gate_clicks += 1
        gate_sel = "[data-testid='emptyState'] [data-testid='empty_state_button_text']"
        page = dict(hidden)
        page[gate_sel] = []   # gate gone
        self.d.pages["popup"]["elements"] = page

    def _verify(self, user):
        self.confirm_clicks += 1
        if engage.CREDITED_RE.search(self.reply) and user in self.remaining:
            self.remaining.remove(user)
        self.d.elements["#txtHint"] = [_Replies([f"Verifying @{user}...", self.reply])]


class FakeExternalLikeSite:
    """favtweets.php: a `#listall` like page whose popup lands on a tweet on
    x.com. Stateful; mirrors the live flow read 2026-09-24."""

    def __init__(self, driver, tweets=("t1",), reply="You earned 21 points!",
                 blocked_url=None, like_works=True, already_liked=False, popup_opens=True, revert=False):
        self.d = driver
        self.remaining = list(tweets)
        self.reply, self.blocked_url = reply, blocked_url
        self.like_works, self.already_liked = like_works, already_liked
        self.popup_opens, self.revert = popup_opens, revert
        self.like_buttons, self.confirm_clicks, self.skip_clicks = [], 0, 0
        driver.on_get = lambda url: self.reset()
        self.reset()

    def reset(self):
        d = self.d
        d.elements = {**logged_in(), "#txtHint": [FakeElement("", displayed=False)]}
        d.elements["#listall .earn-card"] = [self._card(t) for t in self.remaining]
        d.elements["#listall"] = [FakeElement("Start Liking" if self.remaining
                                              else "No more tasks at this time. Check back later for more.")]
        d.elements["#listall a.earn-confirm"] = []
        d.elements["#listall a[onclick*='favSkip']"] = [
            FakeElement("Skip", attrs={"onclick": f"favSkip('{t}');"}, on_click=lambda: self._skip(t))
            for t in self.remaining]

    def _card(self, tweet):
        confirm = FakeElement("I Liked", displayed=False, attrs={"class": "earn-btn earn-confirm"},
                              on_click=lambda: self._verify(tweet))
        like = FakeElement("Like", attrs={"class": "earn-btn"},
                           on_click=lambda: self._open_popup(tweet, confirm))
        return FakeElement("+21 points\nLike", attrs={"id": f"card_{tweet}"},
                           children={"a.earn-btn": [like, confirm]})

    def _open_popup(self, tweet, confirm):
        d = self.d
        if not self.popup_opens:
            return
        if self.blocked_url:
            d.open_window("popup", elements={}, url=self.blocked_url)
        else:
            if self.revert:
                like = _Reverting("", "data-testid", "like", "unlike")
                page = {"button[data-testid='like']": [like], "button[data-testid='unlike']": []}
            elif self.already_liked:
                like = FakeElement(attrs={"data-testid": "unlike"})
                page = {"button[data-testid='unlike']": [like], "button[data-testid='like']": []}
            else:
                like = FakeElement(attrs={"data-testid": "like"})
                page = {"button[data-testid='like']": [like], "button[data-testid='unlike']": []}
                like._on_click = lambda: (page.__setitem__("button[data-testid='unlike']", [like]),
                                          page.__setitem__("button[data-testid='like']", [])) if self.like_works else None
            self.like_buttons.append(like)
            page["[data-testid='SideNav_AccountSwitcher_Button']"] = [FakeElement()]
            d.open_window("popup", elements=page, url=f"https://x.com/user/status/{tweet}")
        confirm._displayed = True
        d.elements["#listall a.earn-confirm"] = [confirm]

    def _skip(self, tweet):
        self.skip_clicks += 1
        if tweet in self.remaining:
            self.remaining.remove(tweet)

    def _verify(self, tweet):
        self.confirm_clicks += 1
        if engage.CREDITED_RE.search(self.reply) and tweet in self.remaining:
            self.remaining.remove(tweet)
        self.d.elements["#txtHint"] = [_Replies(["Verifying...", self.reply])]


class FakeIGLikeSite:
    """instagramlikes.php: one post at a time, popup lands on instagram.com/p/.
    Result box is `#FBPoints` and the container is `#FBLike`. Stateful."""

    def __init__(self, driver, posts=("p1",), reply="You earned 14 points!",
                 blocked_url=None, like_works=True, already_liked=False):
        self.d = driver
        self.remaining = list(posts)
        self.reply, self.blocked_url = reply, blocked_url
        self.like_works, self.already_liked = like_works, already_liked
        self.like_icons, self.confirm_clicks = [], 0
        driver.on_get = lambda url: self.reset()
        self.reset()

    def reset(self):
        d = self.d
        d.elements = {**logged_in(), "#FBPoints": [FakeElement("", displayed=False)]}
        post = self.remaining[0] if self.remaining else None
        if post:
            confirm = FakeElement("I liked this", displayed=False, attrs={"class": "earn-btn earn-confirm"},
                                  on_click=lambda: self._verify(post))
            like = FakeElement("Like on Instagram", attrs={"id": "iglikebtn", "class": "earn-btn"},
                               on_click=lambda: self._open_popup(post, confirm))
            d.elements[".iglike-wrap .earn-card"] = [FakeElement(f"instagram.com/p/{post}\n+14 points")]
            d.elements["a#iglikebtn.earn-btn"] = [like]
            d.elements[".iglike-wrap a.earn-confirm"] = []
            self._confirm = confirm
            d.elements["#FBLike"] = [FakeElement("Start Liking")]
            d.elements["#DoesLike a[onclick*='FBSkip']"] = [
                FakeElement("Skip", attrs={"onclick": f"FBSkip('{post}');"}, on_click=lambda: self._skip(post))]
        else:
            d.elements[".iglike-wrap .earn-card"] = []
            d.elements["#FBLike"] = [FakeElement("No more tasks at this time. Check back later for more.")]

    def _open_popup(self, post, confirm):
        d = self.d
        if self.blocked_url:
            d.open_window("popup", elements={}, url=self.blocked_url)
        else:
            label = "Descurtir" if self.already_liked else "Curtir"
            # The POST like svg has height 24; a comment like (height 16, same
            # label) must be ignored by the real code.
            icon = FakeElement(attrs={"aria-label": label, "height": "24"})
            icon._on_click = lambda: icon.attrs.__setitem__("aria-label", "Descurtir") if self.like_works else None
            comment_like = FakeElement(attrs={"aria-label": "Curtir", "height": "16"})
            self.like_icons.append(icon)
            page = {"svg[aria-label]": [comment_like, icon],
                    "nav a[href='/']": [FakeElement()]}
            d.open_window("popup", elements=page, url=f"https://www.instagram.com/p/{post}/")
        confirm._displayed = True
        d.elements[".iglike-wrap a.earn-confirm"] = [confirm]

    def _skip(self, post):
        if post in self.remaining:
            self.remaining.remove(post)

    def _verify(self, post):
        self.confirm_clicks += 1
        if engage.CREDITED_RE.search(self.reply) and post in self.remaining:
            self.remaining.remove(post)
        self.d.elements["#FBPoints"] = [_Replies(["Hang tight, checking with Instagram...", self.reply])]


class TwitterFollowsTests(unittest.TestCase):
    def test_follow_is_performed_confirmed_and_credited(self):
        d = FakeDriver(elements=logged_in())
        site = FakeExternalFollowSite(d, twitter_follows, "x")
        logs = []
        with _no_sleep():
            n = twitter_follows.process_twitter_follows_once(d, logs.append, lambda: False)
        self.assertEqual(n, 1)
        self.assertEqual(site.confirm_clicks, 1)
        self.assertEqual(d.window_handles, ["main"])
        self.assertTrue(any("credited: You earned 21 points" in m for m in logs), logs)

    def test_already_following_confirms_without_clicking(self):
        d = FakeDriver(elements=logged_in())
        site = FakeExternalFollowSite(d, twitter_follows, "x", already_following=True)
        with _no_sleep():
            twitter_follows.process_twitter_follows_once(d, lambda m: None, lambda: False)
        self.assertEqual(site.follow_buttons[0].clicks, 0)
        self.assertEqual(site.confirm_clicks, 1)

    def test_login_gate_ends_the_pass_with_a_hint(self):
        d = FakeDriver(elements=logged_in())
        FakeExternalFollowSite(d, twitter_follows, "x", blocked_url="https://x.com/i/flow/login")
        logs = []
        with _no_sleep():
            n = twitter_follows.process_twitter_follows_once(d, logs.append, lambda: False)
        self.assertEqual(n, 0)
        self.assertTrue(any("sign in" in m.lower() and ("X" in m) for m in logs), logs)
        self.assertEqual(d.window_handles, ["main"])

    def test_reverted_follow_is_not_confirmed(self):
        d = FakeDriver(elements=logged_in())
        FakeExternalFollowSite(d, twitter_follows, "x", revert=True)
        logs = []
        with _no_sleep():
            n = twitter_follows.process_twitter_follows_once(d, logs.append, lambda: False)
        self.assertEqual(n, 0)
        self.assertTrue(any("reverted the follow" in m for m in logs), logs)

    def test_empty_notice_is_not_a_missing_card(self):
        d = FakeDriver(elements=logged_in())
        FakeExternalFollowSite(d, twitter_follows, "x", users=())
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            n = twitter_follows.process_twitter_follows_once(d, logs.append, lambda: False)
        self.assertEqual(n, 0)
        self.assertFalse(any("may have changed" in m for m in logs), logs)

    def test_does_not_reload_the_page_between_cards(self):
        # Live 2026-09-24: the follow page slides its own list via AJAX; a
        # reload after each card makes the whole list "jump back one". The flow
        # sets reload_between_cards=False so the page is never re-fetched
        # mid-pass -- only the initial navigate stays.
        self.assertFalse(twitter_follows.FLOW.reload_between_cards)
        d = FakeDriver(elements=logged_in())
        FakeExternalFollowSite(d, twitter_follows, "x", users=("a", "b"))
        with _no_sleep():
            twitter_follows.process_twitter_follows_once(d, lambda m: None, lambda: False)
        self.assertEqual(d.visited.count(f"{utils.YLH_BASE}/{twitter_follows.PAGE}"), 0)

    def test_already_followed_reply_skips_instead_of_reloading(self):
        # Live 2026-09-24: the site re-shows a profile we already follow; the
        # confirm returns "Uh oh ... Please tap the Follow link first...". Only
        # Skip clears it (a reload re-queues it).
        d = FakeDriver(elements=logged_in())
        site = FakeExternalFollowSite(
            d, twitter_follows, "x", users=("a",), already_following=True,
            reply="Uh oh Please tap the Follow link first, then come back and confirm.")
        logs = []
        with _no_sleep():
            twitter_follows.process_twitter_follows_once(d, logs.append, lambda: False)
        self.assertGreaterEqual(site.skip_clicks, 1)
        self.assertEqual(d.visited.count(f"{utils.YLH_BASE}/{twitter_follows.PAGE}"), 0)   # not reloaded
        self.assertTrue(any("already done" in m.lower() or "skipping this one" in m for m in logs), logs)

    def test_sensitive_content_gate_is_dismissed_then_follow_proceeds(self):
        # Live 2026-09-24: some profiles hide the header behind a "Caution:
        # potentially sensitive content" interstitial with "Yes, view profile".
        d = FakeDriver(elements=logged_in())
        site = FakeExternalFollowSite(d, twitter_follows, "x", sensitive=True)
        logs = []
        with _no_sleep():
            n = twitter_follows.process_twitter_follows_once(d, logs.append, lambda: False)
        self.assertEqual(site.gate_clicks, 1)
        self.assertEqual(n, 1)
        self.assertTrue(any("sensitive-content" in m for m in logs), logs)


class InstagramFollowsTests(unittest.TestCase):
    def test_follow_is_performed_confirmed_and_credited(self):
        d = FakeDriver(elements=logged_in())
        site = FakeExternalFollowSite(d, instagram_follows, "ig")
        logs = []
        with _no_sleep():
            n = instagram_follows.process_instagram_follows_once(d, logs.append, lambda: False)
        self.assertEqual(n, 1)
        self.assertEqual(site.confirm_clicks, 1)
        self.assertTrue(any("credited: You earned 21 points" in m for m in logs), logs)

    def test_suspended_account_ends_the_pass_with_a_hint(self):
        # The live case 2026-09-24: instagramrender lands on /accounts/suspended.
        d = FakeDriver(elements=logged_in())
        FakeExternalFollowSite(d, instagram_follows, "ig",
                               blocked_url="https://www.instagram.com/accounts/suspended/?next=/")
        logs = []
        with _no_sleep():
            n = instagram_follows.process_instagram_follows_once(d, logs.append, lambda: False)
        self.assertEqual(n, 0)
        self.assertTrue(any("sign in" in m.lower() and "Instagram" in m for m in logs), logs)
        self.assertEqual(d.window_handles, ["main"])

    def test_challenge_page_is_also_treated_as_blocked(self):
        d = FakeDriver(elements=logged_in())
        FakeExternalFollowSite(d, instagram_follows, "ig",
                               blocked_url="https://www.instagram.com/challenge/?next=/")
        logs = []
        with _no_sleep():
            n = instagram_follows.process_instagram_follows_once(d, logs.append, lambda: False)
        self.assertEqual(n, 0)
        self.assertTrue(any("sign in" in m.lower() for m in logs), logs)

    def test_picks_the_follow_button_not_the_bio_link(self):
        # Live 2026-09-24 bug: with a link-rich bio the header holds a bio-link
        # button (svg "Ícone de link") before the Follow button; the bot must
        # skip it and click the real Follow (credit proves the right click).
        d = FakeDriver(elements=logged_in())
        site = FakeExternalFollowSite(d, instagram_follows, "ig")
        with _no_sleep():
            n = instagram_follows.process_instagram_follows_once(d, lambda m: None, lambda: False)
        self.assertEqual(n, 1)
        self.assertEqual(site.follow_buttons[0].clicks, 1)   # the follow button, not the bio link

    def test_already_following_on_open_detected_by_arrow_svg(self):
        d = FakeDriver(elements=logged_in())
        site = FakeExternalFollowSite(d, instagram_follows, "ig", already_following=True)
        with _no_sleep():
            instagram_follows.process_instagram_follows_once(d, lambda m: None, lambda: False)
        self.assertEqual(site.follow_buttons[0].clicks, 0)   # not clicked; already following
        self.assertEqual(site.confirm_clicks, 1)


class TwitterLikesTests(unittest.TestCase):
    def test_like_is_performed_confirmed_and_credited(self):
        d = FakeDriver(elements=logged_in())
        site = FakeExternalLikeSite(d)
        logs = []
        with _no_sleep():
            n = twitter_likes.process_twitter_likes_once(d, logs.append, lambda: False)
        self.assertEqual(n, 1)
        self.assertEqual(site.confirm_clicks, 1)
        self.assertEqual(d.window_handles, ["main"])
        self.assertTrue(any("credited: You earned 21 points" in m for m in logs), logs)

    def test_already_liked_confirms_without_clicking(self):
        d = FakeDriver(elements=logged_in())
        site = FakeExternalLikeSite(d, already_liked=True)
        with _no_sleep():
            twitter_likes.process_twitter_likes_once(d, lambda m: None, lambda: False)
        self.assertEqual(site.like_buttons[0].clicks, 0)
        self.assertEqual(site.confirm_clicks, 1)

    def test_login_gate_ends_the_pass_with_a_hint(self):
        d = FakeDriver(elements=logged_in())
        FakeExternalLikeSite(d, blocked_url="https://x.com/login")
        logs = []
        with _no_sleep():
            n = twitter_likes.process_twitter_likes_once(d, logs.append, lambda: False)
        self.assertEqual(n, 0)
        self.assertTrue(any("sign in" in m.lower() for m in logs), logs)

    def test_uncredited_like_skips_the_card_in_place(self):
        d = FakeDriver(elements=logged_in())
        site = FakeExternalLikeSite(d, tweets=("a",), reply="We could not verify your like. Try again.")
        logs = []
        with _no_sleep():
            twitter_likes.process_twitter_likes_once(d, logs.append, lambda: False)
        self.assertGreaterEqual(site.skip_clicks, 1)      # advanced in-place with favSkip
        self.assertTrue(any("not credited" in m for m in logs), logs)

    def test_empty_notice_is_not_a_missing_card(self):
        d = FakeDriver(elements=logged_in())
        FakeExternalLikeSite(d, tweets=())
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            n = twitter_likes.process_twitter_likes_once(d, logs.append, lambda: False)
        self.assertEqual(n, 0)
        self.assertFalse(any("may have changed" in m for m in logs), logs)


class InstagramLikesTests(unittest.TestCase):
    def test_like_is_performed_confirmed_and_credited(self):
        d = FakeDriver(elements=logged_in())
        site = FakeIGLikeSite(d)
        logs = []
        with _no_sleep():
            n = instagram_likes.process_instagram_likes_once(d, logs.append, lambda: False)
        self.assertEqual(n, 1)
        self.assertEqual(site.confirm_clicks, 1)
        self.assertTrue(any("credited: You earned 14 points" in m for m in logs), logs)

    def test_already_liked_confirms_without_clicking(self):
        d = FakeDriver(elements=logged_in())
        site = FakeIGLikeSite(d, already_liked=True)
        with _no_sleep():
            instagram_likes.process_instagram_likes_once(d, lambda m: None, lambda: False)
        self.assertEqual(site.like_icons[0].clicks, 0)
        self.assertEqual(site.confirm_clicks, 1)

    def test_suspended_account_ends_the_pass_with_a_hint(self):
        d = FakeDriver(elements=logged_in())
        FakeIGLikeSite(d, blocked_url="https://www.instagram.com/accounts/suspended/?next=/")
        logs = []
        with _no_sleep():
            n = instagram_likes.process_instagram_likes_once(d, logs.append, lambda: False)
        self.assertEqual(n, 0)
        self.assertTrue(any("sign in" in m.lower() and "Instagram" in m for m in logs), logs)
        self.assertEqual(d.window_handles, ["main"])

    def test_result_box_is_fbpoints_not_txthint(self):
        # This page mirrors YouTube Likes' result box, unlike the follow pages.
        self.assertEqual(instagram_likes.RESULT_BOX, "#FBPoints")
        self.assertEqual(instagram_likes.FLOW.result_box, "#FBPoints")

    def test_likes_the_post_not_a_comment(self):
        # Live 2026-09-24 bug: the post is not in <article> and every comment
        # has a "Curtir" like too; the post's like is the height-24 one. The
        # fake serves a height-16 comment like first; liking must still credit.
        d = FakeDriver(elements=logged_in())
        site = FakeIGLikeSite(d)
        logs = []
        with _no_sleep():
            n = instagram_likes.process_instagram_likes_once(d, logs.append, lambda: False)
        self.assertEqual(n, 1)
        self.assertEqual(site.like_icons[0].clicks, 1)   # the post's like (height 24)

    def test_empty_notice_is_not_a_missing_card(self):
        d = FakeDriver(elements=logged_in())
        FakeIGLikeSite(d, posts=())
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            n = instagram_likes.process_instagram_likes_once(d, logs.append, lambda: False)
        self.assertEqual(n, 0)
        self.assertFalse(any("may have changed" in m for m in logs), logs)


class SharedFlowTests(unittest.TestCase):
    def test_credited_detection(self):
        for text in ("You earned 21 points!", "21 Points Added!", "+21 points credited",
                     "Success! You followed @alice! You got 22 Points!"):
            self.assertTrue(engage.is_credited(text, ""), text)
        for text in ("We could not verify your like. No points were added.", "Please try again", "",
                     "Checking again We couldn't confirm that follow just yet."):
            self.assertFalse(engage.is_credited(text, ""), text)
        self.assertTrue(engage.is_credited("", '<span id="ok" data-points="2098"></span>'))

    def test_classify_reply(self):
        self.assertEqual(engage.classify("Success! You followed @a! You got 22 Points!"), engage.CREDITED)
        self.assertEqual(engage.classify("Checking again We couldn't confirm that follow just yet. "
                                         "SoundCloud may still be updating."), engage.PENDING)
        self.assertEqual(engage.classify("Hang tight — checking with YouTube. 7s"), engage.PENDING)
        self.assertEqual(engage.classify("Did you follow @a? Verifying..."), engage.PENDING)
        self.assertEqual(engage.classify("This video is no longer available."), engage.FAILED)
        self.assertEqual(engage.classify("We could not verify your like. Try again."), engage.FAILED)
        self.assertEqual(engage.classify("Some brand new wording"), engage.UNKNOWN)

    def test_live_youtube_wording_is_credited_and_entities_are_decoded(self):
        text = "You got 21 Points for liking OFF-DAY RIDE: Mandi Manda &amp; Lepak Santai!"
        self.assertEqual(engage.classify(text), engage.CREDITED)
        self.assertEqual(engage.one_line(text), "You got 21 Points for liking OFF-DAY RIDE: Mandi Manda & Lepak Santai!")

    def test_already_done_detection(self):
        # These never credit; the loop must Skip, not reload (2026-09-24).
        for text in ("Uh oh Please tap the Follow link first, then come back and confirm.",
                     "You already follow this user.", "Already liked."):
            self.assertTrue(engage.is_already_done(text), text)
        for text in ("We couldn't confirm that follow yet. Try again.",
                     "Success! You followed @a! You got 21 Points!"):
            self.assertFalse(engage.is_already_done(text), text)

    def test_card_points(self):
        self.assertEqual(engage.card_points(FakeElement("Points: 21\nLike")), 21)
        self.assertEqual(engage.card_points(FakeElement("@alice\n+17 points")), 17)
        self.assertIsNone(engage.card_points(FakeElement("no numbers here")))

    def test_selectors_are_valid_css(self):
        for sel in (youtube_likes.CARDS, youtube_likes.LIKE_LINK, youtube_likes.STAGE2_BUTTON,
                    youtube_likes.CONFIRM_BUTTON, youtube_likes.RESULT_BOX, youtube_likes.LIKE_BUTTON,
                    youtube_likes.SIGNED_IN, youtube_likes.SIGN_IN_LINK,
                    soundcloud_follows.CARDS, soundcloud_follows.FOLLOW_LINK, soundcloud_follows.CONFIRM_BUTTON,
                    soundcloud_follows.RESULT_BOX, soundcloud_follows.FOLLOW_BUTTON, soundcloud_follows.SIGNED_IN,
                    soundcloud_follows.HEADER_FOLLOW, soundcloud_follows.ANY_FOLLOW,
                    soundcloud_follows.LOGIN_MENU,
                    twitter_follows.CARDS, twitter_follows.CONFIRM_BUTTON, twitter_follows.FOLLOW_BUTTON,
                    twitter_follows.FOLLOWED_BUTTON, twitter_follows.SIGNED_IN, twitter_follows.LOGIN_GATE,
                    instagram_follows.CARDS, instagram_follows.CONFIRM_BUTTON, instagram_follows.HEADER_BUTTONS,
                    instagram_follows.SIGNED_IN, instagram_follows.SKIP_LINK,
                    twitter_likes.CARDS, twitter_likes.CONFIRM_BUTTON, twitter_likes.SKIP_LINK,
                    twitter_likes.LIKE_BUTTON, twitter_likes.LIKED_BUTTON, twitter_likes.SIGNED_IN,
                    twitter_follows.SKIP_LINK, twitter_follows.SENSITIVE_GATE,
                    instagram_likes.CARDS, instagram_likes.CONFIRM_BUTTON, instagram_likes.SKIP_LINK,
                    instagram_likes.LIKE_ICON, instagram_likes.LIST_BOX, instagram_likes.RESULT_BOX):
            self.assertNotIn(":contains", sel)

    def test_task_loops_exit_when_not_logged_in(self):
        for task in (youtube_likes._run_youtube_likes_task, soundcloud_follows._run_soundcloud_follows_task,
                     twitter_follows._run_twitter_follows_task, instagram_follows._run_instagram_follows_task,
                     twitter_likes._run_twitter_likes_task, instagram_likes._run_instagram_likes_task):
            with self.subTest(task=task.__name__), _no_sleep():
                logs = []
                task(FakeDriver(body="Log in"), lambda: False, logs.append, lambda p: None)
                self.assertTrue(any("Not logged in" in m for m in logs), task.__name__)


class MasterSelectionTests(unittest.TestCase):
    def test_only_selected_tasks_run_in_order(self):
        d = FakeDriver(elements=logged_in())
        logs = []
        stop = lambda: any(soundcloud_follows.PAGE in url for url in d.visited)   # noqa: E731
        custom = {"master_tasks": ["soundcloud_follows", "websites"]}
        with _no_sleep():
            master._run_master_task(d, stop, logs.append, lambda p: None, settings=custom)
        pages = [u.split("/")[-1] for u in d.visited]
        self.assertIn("websites.php", pages)
        self.assertIn(soundcloud_follows.PAGE, pages)
        self.assertLess(pages.index("websites.php"), pages.index(soundcloud_follows.PAGE))   # canonical order
        for skipped in ("bonuspoints.php", "youtubenew2.php", "soundcloudplays.php", youtube_likes.PAGE):
            self.assertNotIn(skipped, pages, skipped)
        start = next(m for m in logs if m.startswith("Starting master loop"))
        self.assertIn("Website Views, SoundCloud Follows", start)
        self.assertIn("3 sites, 2 follows", start)

    def test_no_task_selected_logs_and_returns(self):
        d = FakeDriver(elements=logged_in())
        logs = []
        with _no_sleep():
            master._run_master_task(d, lambda: False, logs.append, lambda p: None, settings={"master_tasks": []})
        self.assertTrue(any("No tasks selected" in m for m in logs), logs)
        self.assertEqual(d.visited, [])

    def test_every_task_key_has_a_step(self):
        d = FakeDriver(elements=logged_in())
        steps = master._steps(d, lambda m: None, lambda: False, settings.validate({}))
        self.assertEqual(set(steps), set(settings.TASK_KEYS))


if __name__ == "__main__":
    unittest.main()
