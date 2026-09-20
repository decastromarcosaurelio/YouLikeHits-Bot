"""Task loops against the fake driver, following the live-site flow. Time is virtual."""
import unittest
from unittest import mock

from bot_logic import utils, websites, youtube, soundcloud, bonus, master, earn
from tests.fakes import FakeDriver, FakeElement, logged_in


class _FakeClock:
    """Virtual clock: sleep() advances monotonic() instantly."""

    def __init__(self):
        self.now = 0.0

    def sleep(self, seconds):
        self.now += max(seconds, 0)

    def monotonic(self):
        return self.now


def _no_sleep():
    clock = _FakeClock()
    return mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic)


def _stop_after(n):
    counter = {"n": 0}

    def stop():
        counter["n"] += 1
        return counter["n"] > n
    return stop


class SharedBehaviourTests(unittest.TestCase):
    def test_every_task_exits_when_not_logged_in(self):
        for task in (websites._run_website_task, youtube._run_youtube_task,
                     soundcloud._run_soundcloud_task, bonus._run_bonus_task,
                     master._run_master_task):
            with self.subTest(task=task.__name__), _no_sleep():
                logs = []
                task(FakeDriver(body="Log in"), lambda: False, logs.append, lambda p: None)
                self.assertTrue(any("Not logged in" in m for m in logs), task.__name__)

    def test_logged_in_requires_logout_link(self):
        self.assertFalse(utils.is_logged_in(FakeDriver()))
        self.assertTrue(utils.is_logged_in(FakeDriver(elements=logged_in())))
        dead = logged_in(); dead["#ylhloggedout"] = [FakeElement()]
        self.assertFalse(utils.is_logged_in(FakeDriver(elements=dead)))

    def test_points_from_header_span(self):
        self.assertEqual(utils.get_points(FakeDriver(elements=logged_in("1,234"))), 1234)
        self.assertEqual(utils.get_points(FakeDriver(body="You have 99 Points")), 99)
        self.assertIsNone(utils.get_points(FakeDriver()))

    def test_selectors_are_valid_css(self):
        for sel in (websites.VISIT_SELECTOR, websites.SKIP_SELECTOR, earn.EARN_BUTTON,
                    youtube.BUTTON_SELECTOR, soundcloud.BUTTON_SELECTOR, bonus.CLAIM_CANDIDATES,
                    youtube.CAPTCHA_SELECTOR, utils.LOGOUT_LINK, utils.POINTS_SPAN):
            self.assertNotIn(":contains", sel)


class WebsitesTests(unittest.TestCase):
    def _page(self, seconds=20):
        d = FakeDriver(body="LION SHARE\nClick to open the site in a new tab, then wait %d seconds." % seconds,
                       elements=logged_in())
        d.elements[".wh-status"] = [FakeElement("Click to open the site in a new tab, then wait %d seconds." % seconds)]

        def on_visit():
            d.window_handles.append("popup")
            # the site's JS credits the view once the timer ends
            d.elements[".wh-result"] = [FakeElement("You earned 7 points!")]
            d.elements.pop("#wh-visit")
        d.elements["#wh-visit"] = [FakeElement("Visit site", on_click=on_visit)]
        return d

    def test_visit_credits_and_closes_popup(self):
        d = self._page()
        logs = []
        with _no_sleep():
            viewed = websites.process_websites_once(d, logs.append, lambda: False)
        self.assertEqual(viewed, 1)
        self.assertEqual(d.window_handles, ["main"])
        self.assertTrue(any("20s timer" in m for m in logs))

    def test_empty_state(self):
        d = FakeDriver(body="There are no websites to visit right now.", elements=logged_in())
        with _no_sleep():
            self.assertEqual(websites.process_websites_once(d, lambda m: None, lambda: False), 0)

    def test_timeout_skips(self):
        d = self._page()
        d.elements["#wh-visit"][0]._on_click = None       # timer never completes
        skip = FakeElement("Skip"); d.elements["#wh-skip"] = [skip]
        with _no_sleep():
            viewed = websites.process_websites_once(d, lambda m: None, _stop_after(80), limit=1)
        self.assertEqual(viewed, 0)
        self.assertGreaterEqual(skip.clicks + 1, 1)


class EarnCardTests(unittest.TestCase):
    def test_parse_onclick(self):
        self.assertEqual(earn.parse_earn_button(
            "imageWin(2724633,'FGOU6G0Dsuc','124','b53f',0,event);", 60), ("2724633", 124))
        self.assertEqual(earn.parse_earn_button("garbage", 60), (None, 60))

    def _page(self, onclick, credited=True):
        d = FakeDriver(elements=logged_in())
        d.elements["#showresult"] = [FakeElement("")]

        def on_click():
            d.window_handles.append("popup")
            d.elements["#showresult"] = [FakeElement("You earned 7 points!" if credited else "Video no longer available")]
            d.elements.pop("#listall a.earn-btn")
        d.elements["#listall a.earn-btn"] = [FakeElement("View", on_click=on_click, attrs={"onclick": onclick})]
        return d

    def test_youtube_credits(self):
        d = self._page("imageWin(1,'abc','124','x',0,event);")
        logs = []
        with _no_sleep():
            n = youtube.process_youtube_once(d, logs.append, lambda: False)
        self.assertEqual(n, 1)
        self.assertEqual(d.window_handles, ["main"])
        self.assertTrue(any("124s timer" in m for m in logs))
        self.assertTrue(any("youtubenew2.php" in u for u in d.visited))   # reloaded for next card

    def test_soundcloud_not_credited(self):
        d = self._page("imageWin(213182,'2402576103','69','k',event);", credited=False)
        with _no_sleep():
            self.assertEqual(soundcloud.process_soundcloud_once(d, lambda m: None, lambda: False), 0)

    def test_captcha_pauses(self):
        d = FakeDriver(elements={**logged_in(), "img[src*='captchayt']": [FakeElement()]})
        logs = []
        with _no_sleep():
            self.assertEqual(youtube.process_youtube_once(d, logs.append, lambda: False), 0)
        self.assertTrue(any("Captcha" in m for m in logs))

    def test_stop_interrupts_timer(self):
        d = self._page("imageWin(1,'abc','124','x',0,event);")
        d.elements["#listall a.earn-btn"][0]._on_click = None   # result never arrives
        with _no_sleep():
            self.assertEqual(youtube.process_youtube_once(d, lambda m: None, _stop_after(3)), 0)


class BonusTests(unittest.TestCase):
    def test_hits_progress(self):
        self.assertEqual(bonus.hits_progress("10 / 25 hits"), (10, 25))
        self.assertEqual(bonus.hits_progress("nothing"), (None, None))

    def test_states(self):
        with _no_sleep():
            waiting = FakeDriver(body="10 / 25 hits\nno bonus to claim yet", elements=logged_in())
            self.assertEqual(bonus.process_bonus_once(waiting, lambda m: None, lambda: False), bonus.ALREADY_DONE)

            # exact markup observed live on 2026-09-20
            btn = FakeElement("Claim 10 Points Now", attrs={"href": "?step=get"})
            ready = FakeDriver(body="12 / 25 hits\nUnclaimed Points: +10",
                               elements={**logged_in(), "a.buybutton": [btn]})
            self.assertEqual(bonus.process_bonus_once(ready, lambda m: None, lambda: False), bonus.CLAIMED)
            self.assertEqual(btn.clicks, 1)

            pill = FakeElement("No bonus to claim yet")
            not_a_button = FakeDriver(body="10 / 25 hits", elements={**logged_in(), ".bonus-pill a": [pill]})
            self.assertEqual(bonus.process_bonus_once(not_a_button, lambda m: None, lambda: False), bonus.ALREADY_DONE)
            self.assertEqual(pill.clicks, 0)


class MasterTests(unittest.TestCase):
    def test_one_cycle_visits_every_page_then_stops(self):
        d = FakeDriver(elements=logged_in())
        logs = []
        stop = lambda: any(soundcloud.PAGE in url for url in d.visited)
        with _no_sleep():
            master._run_master_task(d, stop, logs.append, lambda p: None)
        for page in (bonus.PAGE, websites.PAGE, youtube.PAGE, soundcloud.PAGE):
            self.assertTrue(any(page in url for url in d.visited), page)
        self.assertIn("Master loop stopped.", logs)


class CliRunnerTests(unittest.TestCase):
    def test_run_cli_task_quits_driver_and_handles_failed_setup(self):
        d = FakeDriver()
        called = []
        utils.run_cli_task("T", lambda: d, lambda *a: called.append(a))
        self.assertEqual(len(called), 1)
        self.assertFalse(d.alive)
        utils.run_cli_task("T", lambda: None, lambda *a: called.append(a))
        self.assertEqual(len(called), 1)


if __name__ == "__main__":
    unittest.main()
