import time
import unittest
from unittest import mock

from bot_logic import utils
from tests.fakes import FakeDriver, FakeElement


class ChromeVersionTests(unittest.TestCase):
    def test_parse_google_chrome(self):
        self.assertEqual(utils.parse_chrome_major("Google Chrome 153.0.8010.52 "), 153)

    def test_parse_chromium(self):
        self.assertEqual(utils.parse_chrome_major("Chromium 128.0.6613.84 snap"), 128)

    def test_parse_garbage(self):
        self.assertIsNone(utils.parse_chrome_major("no version here"))
        self.assertIsNone(utils.parse_chrome_major(""))

    def test_detect_uses_binary_output(self):
        fake = mock.Mock(stdout="Google Chrome 153.0.8010.52\n")
        with mock.patch.object(utils.subprocess, "run", return_value=fake):
            self.assertEqual(utils.detect_chrome_major("/opt/chrome"), 153)

    def test_detect_returns_none_when_binary_missing(self):
        with mock.patch.object(utils.uc, "find_chrome_executable", return_value=None):
            self.assertIsNone(utils.detect_chrome_major())

    def test_setup_browser_passes_detected_major(self):
        with mock.patch.object(utils, "detect_chrome_major", return_value=153), \
             mock.patch.object(utils.uc, "Chrome") as chrome:
            utils.setup_browser("/tmp/profile")
        self.assertEqual(chrome.call_args.kwargs["version_main"], 153)


class WaitTests(unittest.TestCase):
    def test_full_wait_when_never_stopped(self):
        start = time.monotonic()
        self.assertTrue(utils.wait_unless_stopped(0.2, lambda: False, step=0.05))
        self.assertGreaterEqual(time.monotonic() - start, 0.19)

    def test_returns_early_when_stopped(self):
        calls = {"n": 0}

        def stop():
            calls["n"] += 1
            return calls["n"] > 2

        start = time.monotonic()
        self.assertFalse(utils.wait_unless_stopped(10, stop, step=0.01))
        self.assertLess(time.monotonic() - start, 1)

    def test_no_callback_sleeps_plain(self):
        with mock.patch.object(utils.time, "sleep") as sleep:
            self.assertTrue(utils.wait_unless_stopped(3))
        sleep.assert_called_once_with(3)


class PageHelperTests(unittest.TestCase):
    def test_logged_in_requires_points_element(self):
        self.assertFalse(utils.is_logged_in(FakeDriver(body="Welcome")))
        self.assertTrue(utils.is_logged_in(FakeDriver(
            body="Welcome", elements={".points": [FakeElement("120")]})))

    def test_not_logged_in_text_wins(self):
        d = FakeDriver(body="You are NOT logged in", elements={".points": [FakeElement("0")]})
        self.assertFalse(utils.is_logged_in(d))

    def test_get_points_from_element_and_body(self):
        self.assertEqual(utils.get_points(FakeDriver(elements={"#points": [FakeElement("1,234")]})), 1)
        self.assertEqual(utils.get_points(FakeDriver(body="You have 1,234 Points")), 1234)
        self.assertIsNone(utils.get_points(FakeDriver(body="nothing")))

    def test_browser_alive(self):
        d = FakeDriver()
        self.assertTrue(utils.is_browser_alive(d))
        d.quit()
        self.assertFalse(utils.is_browser_alive(d))
        self.assertFalse(utils.is_browser_alive(None))


if __name__ == "__main__":
    unittest.main()
