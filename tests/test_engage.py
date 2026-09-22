"""YouTube Likes and SoundCloud Follows against fake pages that follow the
live flow read on 2026-09-21 (see the module docstrings). Time is virtual."""
import unittest

from bot_logic import youtube_likes, soundcloud_follows, engage, master, settings
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
                 signed_in=True, like_works=True, already_liked=False, popup_opens=True, revert=False):
        self.d = driver
        self.revert = revert
        self.remaining = list(videos)
        self.reply, self.signed_in, self.like_works = reply, signed_in, like_works
        self.already_liked, self.popup_opens = already_liked, popup_opens
        self.like_buttons, self.confirm_clicks, self.stage2_clicks = [], 0, 0
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

    def _verify(self, vid):
        self.confirm_clicks += 1
        if engage.CREDITED_RE.search(self.reply) and vid in self.remaining:
            self.remaining.remove(vid)
        self.d.elements["#FBPoints"] = [_Replies(["Hang tight — checking with YouTube. 8s",
                                                  "Confirming your Like…", self.reply])]


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

    def test_verification_that_never_replies_reloads(self):
        d = FakeDriver(elements=logged_in()); site = FakeLikesSite(d)
        site._verify = lambda vid: d.elements.__setitem__("#FBPoints", [FakeElement("Hang tight — checking with YouTube. 8s")])
        logs = []; clock = _FakeClock()
        with mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic):
            self.assertEqual(youtube_likes.process_youtube_likes_once(d, logs.append, lambda: False), 0)
        self.assertTrue(any(f"no verdict after {engage.VERIFY_WAIT}s" in m and "Hang tight" in m for m in logs), logs)

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
                    soundcloud_follows.LOGIN_MENU):
            self.assertNotIn(":contains", sel)

    def test_task_loops_exit_when_not_logged_in(self):
        for task in (youtube_likes._run_youtube_likes_task, soundcloud_follows._run_soundcloud_follows_task):
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
