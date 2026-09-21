import time
import unittest
from unittest import mock

from bot_logic import utils
from tests.fakes import FakeDriver, FakeElement, logged_in


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
        # Chrome's popup blocker stays ON: the site's own popups come from a
        # trusted click; the flag only let advertisers flood the browser.
        self.assertNotIn("--disable-popup-blocking", chrome.call_args.kwargs["options"].arguments)


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
    def test_logged_in_requires_logout_link(self):
        self.assertFalse(utils.is_logged_in(FakeDriver(body="Welcome")))
        self.assertTrue(utils.is_logged_in(FakeDriver(elements=logged_in())))

    def test_get_points_from_span_and_body(self):
        self.assertEqual(utils.get_points(FakeDriver(elements=logged_in("1,234"))), 1234)
        self.assertEqual(utils.get_points(FakeDriver(body="You have 1,234 Points")), 1234)
        self.assertIsNone(utils.get_points(FakeDriver(body="nothing")))

    def test_seconds_from_text(self):
        self.assertEqual(utils.seconds_from_text("then wait 20 seconds. Keep", 5), 20)
        self.assertEqual(utils.seconds_from_text("Watching 0 / 124 s", 5), 124)
        self.assertEqual(utils.seconds_from_text("", 5), 5)

    def test_wait_until_returns_value_or_none(self):
        with mock.patch.object(utils.time, "sleep", lambda s: None):
            hits = iter([None, None, "ok"])
            self.assertEqual(utils.wait_until(lambda: next(hits), timeout=10), "ok")
            self.assertIsNone(utils.wait_until(lambda: None, timeout=0))

    def test_browser_alive(self):
        d = FakeDriver()
        self.assertTrue(utils.is_browser_alive(d))
        self.assertEqual(utils.browser_state(d), "alive")
        d.quit()
        self.assertFalse(utils.is_browser_alive(d))
        self.assertEqual(utils.browser_state(d), "closed")
        self.assertFalse(utils.is_browser_alive(None))

    def test_slow_browser_is_unresponsive_not_closed(self):
        """A timeout enumerating 1,000 tabs is not the user closing the browser."""
        class Slow(FakeDriver):
            def __getattribute__(self, name):
                if name == "window_handles":
                    raise TimeoutError("Read timed out. (read timeout=120)")
                return object.__getattribute__(self, name)
        d = Slow()
        self.assertEqual(utils.browser_state(d), "unresponsive")
        self.assertTrue(utils.is_browser_alive(d))

    def test_tab_level_errors_are_unresponsive(self):
        for msg in ("disconnected: not connected to DevTools",
                    "target window already closed",
                    "no such window: window was already closed"):
            class Tab(FakeDriver):
                def __getattribute__(self, name):
                    if name == "window_handles":
                        raise RuntimeError(msg)
                    return object.__getattribute__(self, name)
            self.assertEqual(utils.browser_state(Tab()), "unresponsive", msg)
        class Dead(FakeDriver):
            def __getattribute__(self, name):
                if name == "window_handles":
                    raise RuntimeError("invalid session id")
                return object.__getattribute__(self, name)
        self.assertEqual(utils.browser_state(Dead()), "closed")

    def test_dead_driver_process_is_closed(self):
        class Gone(FakeDriver):
            class service:
                class process:
                    @staticmethod
                    def poll(): return 0
            def __getattribute__(self, name):
                if name == "window_handles":
                    raise TimeoutError("Read timed out.")
                return object.__getattribute__(self, name)
        self.assertEqual(utils.browser_state(Gone()), "closed")

    def test_close_extra_windows_keeps_set_and_survives_vanishing(self):
        d = FakeDriver()
        d.window_handles += ["popup", "ad1", "ad2"]
        orig_close = d.close
        def flaky_close():
            if d.current_window_handle == "ad1":
                d.window_handles.remove("ad1"); raise RuntimeError("no such window")
            orig_close()
        d.close = flaky_close
        utils.close_extra_windows(d, keep={"main", "popup"})
        self.assertEqual(sorted(d.window_handles), ["main", "popup"])
        self.assertEqual(d.current_window_handle, "main")

    def test_window_guard_keeps_late_popup_and_prunes_ads(self):
        d = FakeDriver()
        guard = utils.WindowGuard(d, "main")          # snapshot before the click
        self.assertFalse(guard.prune())               # nothing new yet: nothing pruned
        d.window_handles.append("popup")              # the page opens its popup late
        self.assertFalse(guard.prune())
        self.assertEqual(guard.popup, "popup")
        d.window_handles += ["ad1", "ad2"]
        self.assertTrue(guard.prune())
        self.assertEqual(sorted(d.window_handles), ["main", "popup"])

    def test_window_guard_snapshot_failure_falls_back_to_main(self):
        class Flaky(FakeDriver):
            fail_once = True
            def __getattribute__(self, name):
                if name == "window_handles" and object.__getattribute__(self, "fail_once"):
                    object.__setattr__(self, "fail_once", False)
                    raise TimeoutError("Read timed out.")
                return object.__getattribute__(self, name)
        d = Flaky()
        guard = utils.WindowGuard(d, "main")
        self.assertEqual(guard.before, {"main"})
        d.window_handles.append("popup"); guard.prune()
        d.window_handles.append("ad"); self.assertTrue(guard.prune())
        self.assertEqual(sorted(d.window_handles), ["main", "popup"])

    def test_window_guard_ignores_stale_window(self):
        d = FakeDriver(); d.window_handles.append("stale")
        guard = utils.WindowGuard(d, "main")
        d.window_handles.append("popup")
        guard.prune()
        self.assertEqual(guard.popup, "popup")
        self.assertEqual(sorted(d.window_handles), ["main", "popup"])


if __name__ == "__main__":
    unittest.main()
