"""PATH self-registration for the installed command.

Run: python -m unittest tests.test_install_pathfix -v
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
if REPO.as_posix() not in sys.path:
    sys.path.insert(0, REPO.as_posix())

from tailtrail.install import pathfix  # noqa: E402


class PathValueTests(unittest.TestCase):
    def test_appends_missing_entry(self) -> None:
        sep = os.pathsep
        self.assertEqual(
            pathfix.new_path_value(f"C:{sep}D:", "E:"),
            f"C:{sep}D:{sep}E:",
        )

    def test_existing_entry_returns_none(self) -> None:
        sep = os.pathsep
        self.assertIsNone(pathfix.new_path_value(f"C:{sep}D:", "D:"))
        self.assertIsNone(pathfix.new_path_value("D:", "D:"))

    def test_empty_current(self) -> None:
        self.assertEqual(pathfix.new_path_value("", "E:"), "E:")


class EnsureCommandTests(unittest.TestCase):
    def test_already_resolvable_does_nothing(self) -> None:
        with mock.patch.object(pathfix, "command_resolvable", return_value=True):
            result = pathfix.ensure_command_on_path("C:/fake")
        self.assertEqual(result["status"], "already")
        self.assertFalse(result["restart_required"])

    def test_manual_hint_off_windows(self) -> None:
        with mock.patch.object(pathfix, "command_resolvable", return_value=False):
            with mock.patch.object(pathfix.os, "name", "posix"):
                result = pathfix.ensure_command_on_path("C:/fake")
        self.assertEqual(result["status"], "manual")
        self.assertIn("C:/fake", result["error"])

    def test_scripts_dir_targets_interpreter(self) -> None:
        self.assertEqual(
            pathfix.scripts_dir_for("/venv/bin/python").as_posix(),
            Path("/venv/bin/python").resolve().parent.as_posix(),
        )


if __name__ == "__main__":
    unittest.main()
