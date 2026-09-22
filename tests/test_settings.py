import json
import os
import tempfile
import unittest
from unittest import mock

from bot_logic import settings, master
from tests.fakes import FakeDriver, logged_in
from tests.test_tasks import _no_sleep


class ValidateTests(unittest.TestCase):
    def test_defaults_on_garbage(self):
        self.assertEqual(settings.validate(None), settings.DEFAULTS)
        self.assertEqual(settings.validate({"cycle_wait_min_minutes": "abc"}), settings.DEFAULTS)

    def test_swaps_min_max(self):
        s = settings.validate({"cycle_wait_min_minutes": 5, "cycle_wait_max_minutes": 2})
        self.assertEqual((s["cycle_wait_min_minutes"], s["cycle_wait_max_minutes"]), (2.0, 5.0))

    def test_rejects_out_of_range(self):
        s = settings.validate({"cycle_wait_max_minutes": -1, "websites_per_cycle": 999})
        self.assertEqual(s["cycle_wait_max_minutes"], settings.DEFAULTS["cycle_wait_max_minutes"])
        self.assertEqual(s["websites_per_cycle"], settings.DEFAULTS["websites_per_cycle"])

    def test_zero_wait_allowed(self):
        s = settings.validate({"cycle_wait_min_minutes": 0, "cycle_wait_max_minutes": 0})
        self.assertEqual(settings.cycle_wait_seconds(s), (0, 0))


class PersistenceTests(unittest.TestCase):
    def test_round_trip_and_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "settings.json")
            self.assertEqual(settings.load(path), settings.DEFAULTS)
            settings.save({"cycle_wait_min_minutes": 2, "cycle_wait_max_minutes": 4.5}, path)
            loaded = settings.load(path)
            self.assertEqual((loaded["cycle_wait_min_minutes"], loaded["cycle_wait_max_minutes"]), (2.0, 4.5))
            with open(path, "w") as f:
                f.write("{not json")
            self.assertEqual(settings.load(path), settings.DEFAULTS)


class MasterTasksTests(unittest.TestCase):
    def test_missing_or_garbage_means_all_tasks(self):
        self.assertEqual(settings.validate({})["master_tasks"], list(settings.TASK_KEYS))
        self.assertEqual(settings.validate({"master_tasks": "youtube"})["master_tasks"], list(settings.TASK_KEYS))
        self.assertEqual(settings.validate({"master_tasks": 7})["master_tasks"], list(settings.TASK_KEYS))

    def test_unknown_names_dropped_and_order_is_canonical(self):
        s = settings.validate({"master_tasks": ["soundcloud_follows", "tiktok", 3, "bonus", "bonus"]})
        self.assertEqual(s["master_tasks"], ["bonus", "soundcloud_follows"])
        self.assertEqual(settings.enabled_tasks(s), ["bonus", "soundcloud_follows"])

    def test_empty_selection_is_kept(self):
        self.assertEqual(settings.validate({"master_tasks": []})["master_tasks"], [])

    def test_defaults_are_not_shared(self):
        s = settings.validate({})
        s["master_tasks"].clear()
        self.assertEqual(settings.DEFAULTS["master_tasks"], list(settings.TASK_KEYS))
        self.assertEqual(settings.validate(None)["master_tasks"], list(settings.TASK_KEYS))

    def test_new_quotas_are_validated(self):
        s = settings.validate({"youtube_likes_per_cycle": 5, "soundcloud_follows_per_cycle": -1})
        self.assertEqual(s["youtube_likes_per_cycle"], 5)
        self.assertEqual(s["soundcloud_follows_per_cycle"], settings.DEFAULTS["soundcloud_follows_per_cycle"])
        self.assertIn("youtube_likes_per_cycle", settings.QUOTA_KEYS)

    def test_selection_round_trips_through_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "settings.json")
            settings.save({"master_tasks": ["youtube_likes"]}, path)
            self.assertEqual(settings.load(path)["master_tasks"], ["youtube_likes"])


class MasterUsesSettingsTests(unittest.TestCase):
    def test_wait_range_and_quota_are_applied(self):
        d = FakeDriver(elements=logged_in())
        logs = []
        cycles = {"n": 0}

        def stop():
            return cycles["n"] >= 1

        captured = {}

        def fake_uniform(lo, hi):
            captured["range"] = (lo, hi)
            cycles["n"] += 1
            return lo
        custom = {"cycle_wait_min_minutes": 2, "cycle_wait_max_minutes": 4, "websites_per_cycle": 7}
        with _no_sleep(), mock.patch.object(master.random, "uniform", fake_uniform):
            master._run_master_task(d, stop, logs.append, lambda p: None, settings=custom)
        self.assertEqual(captured["range"], (120, 240))
        self.assertTrue(any("2-4 min" in m and "7 sites" in m for m in logs))


if __name__ == "__main__":
    unittest.main()
