import unittest

import main_cli
from bot_logic import settings


class TaskSelectionTests(unittest.TestCase):
    def test_enter_keeps_current(self):
        self.assertEqual(main_cli.parse_task_selection("", ["bonus", "websites"]), ["bonus", "websites"])
        self.assertEqual(main_cli.parse_task_selection("  ", []), [])

    def test_numbers_map_to_tasks_in_menu_order(self):
        self.assertEqual(main_cli.parse_task_selection("1,3", []), ["bonus", "youtube"])
        self.assertEqual(main_cli.parse_task_selection("6 2", []), ["websites", "soundcloud_follows"])

    def test_all_and_none(self):
        self.assertEqual(main_cli.parse_task_selection("all", []), list(settings.TASK_KEYS))
        self.assertEqual(main_cli.parse_task_selection("NONE", ["bonus"]), [])

    def test_garbage_is_rejected(self):
        for answer in ("x", "0", "11", "1,x", "1;2"):
            self.assertIsNone(main_cli.parse_task_selection(answer, []), answer)


if __name__ == "__main__":
    unittest.main()
