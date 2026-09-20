"""Task loops against the fake driver. Sleeps are patched out."""
import unittest
from unittest import mock

from bot_logic import utils, websites, youtube, soundcloud, bonus, master
from tests.fakes import FakeDriver, FakeElement

LOGGED_IN = {".points": [FakeElement("50")]}


class _FakeClock:
    """Virtual clock: sleep() advances monotonic() instantly."""

    def __init__(self):
        self.now = 0.0

    def sleep(self, seconds):
        self.now += max(seconds, 0)

    def monotonic(self):
        return self.now


def _no_sleep():
    """Patch time so loops run instantly without busy-waiting."""
    clock = _FakeClock()
    return mock.patch.multiple(utils.time, sleep=clock.sleep, monotonic=clock.monotonic)


def _stop_after(n):
    """is_stopped() that turns true after n calls."""
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
                task(FakeDriver(body="not logged in"), lambda: False, logs.append, lambda p: None)
                self.assertTrue(any("Not logged in" in m for m in logs), task.__name__)

    def test_selectors_are_valid_css(self):
        # Selenium raises InvalidSelectorException on ':contains'; guard against regressions.
        for sel in (websites.BUTTON_SELECTOR, youtube.BUTTON_SELECTOR, youtube.SUBMIT_SELECTOR,
                    soundcloud.BUTTON_SELECTOR, bonus.CLAIM_SELECTOR, youtube.CAPTCHA_SELECTOR):
            self.assertNotIn(":contains", sel)


class YoutubeTests(unittest.TestCase):
    def test_clicks_submit_after_timer(self):
        submit = FakeElement()
        d = FakeDriver(elements={".followbutton": [FakeElement()], "input[value='Submit']": [submit]})
        with _no_sleep():
            watched = youtube.process_youtube_once(d, lambda m: None, lambda: False)
        self.assertEqual(watched, 1)
        self.assertEqual(submit.clicks, 1)

    def test_captcha_pauses_and_returns_zero(self):
        d = FakeDriver(elements={"img[src*='captchayt']": [FakeElement()], ".followbutton": [FakeElement()]})
        logs = []
        with _no_sleep():
            self.assertEqual(youtube.process_youtube_once(d, logs.append, lambda: False), 0)
        self.assertTrue(any("Captcha" in m for m in logs))

    def test_stop_interrupts_timer(self):
        d = FakeDriver(elements={".followbutton": [FakeElement(), FakeElement()]})
        with _no_sleep():
            watched = youtube.process_youtube_once(d, lambda m: None, _stop_after(2))
        self.assertEqual(watched, 0)


class WebsitesTests(unittest.TestCase):
    def test_opens_new_tab_views_and_returns(self):
        d = FakeDriver(elements=LOGGED_IN)
        d.elements[".viewbutton"] = [FakeElement(on_click=lambda: d.window_handles.append("popup"))]
        with _no_sleep():
            viewed = websites.process_websites_once(d, lambda m: None, lambda: False)
        self.assertEqual(viewed, 1)
        self.assertEqual(d.window_handles, ["main"])
        self.assertEqual(d.current_window_handle, "main")

    def test_no_items_marker(self):
        d = FakeDriver(body="No websites currently available", elements={".viewbutton": [FakeElement()]})
        with _no_sleep():
            self.assertEqual(websites.process_websites_once(d, lambda m: None, lambda: False), 0)

    def test_limit_respected(self):
        d = FakeDriver(elements={".viewbutton": [FakeElement() for _ in range(5)]})
        with _no_sleep():
            self.assertEqual(websites.process_websites_once(d, lambda m: None, lambda: False, limit=2), 0)
        # no popup opened in the fake, so viewed==0, but only 2 buttons were clicked
        self.assertEqual(sum(e.clicks for e in d.elements[".viewbutton"]), 2)


class BonusTests(unittest.TestCase):
    def test_states(self):
        with _no_sleep():
            self.assertEqual(bonus.process_bonus_once(
                FakeDriver(body="You have made 3 hits out of 10"), lambda m: None, lambda: False),
                bonus.ALREADY_DONE)
            btn = FakeElement()
            self.assertEqual(bonus.process_bonus_once(
                FakeDriver(elements={".buybutton": [btn]}), lambda m: None, lambda: False),
                bonus.CLAIMED)
            self.assertEqual(btn.clicks, 1)
            self.assertEqual(bonus.process_bonus_once(FakeDriver(), lambda m: None, lambda: False),
                             bonus.NOT_AVAILABLE)


class MasterTests(unittest.TestCase):
    def test_one_cycle_visits_every_page_then_stops(self):
        d = FakeDriver(elements=LOGGED_IN)
        logs = []
        # stop once the last page of the cycle has been reached
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
