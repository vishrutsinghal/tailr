from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

import start_request  # noqa: E402


class StartRequestTests(unittest.TestCase):
    def test_same_request_always_serializes_identically(self) -> None:
        first = start_request.normalize_start_request(
            "  update delivery service behavior ",
            changed=["src/service.py"], aidlc="off")
        second = start_request.normalize_start_request(
            "update delivery service behavior",
            changed=["src/service.py"], aidlc="off")
        self.assertEqual(first, second)
        self.assertEqual(
            start_request.start_argv(first), start_request.start_argv(second))

    def test_argv_carries_only_explicit_knobs(self) -> None:
        argv = start_request.start_argv(start_request.normalize_start_request(
            "update delivery service behavior",
            changed=["src/service.py"], aidlc="off", planning_lock=False))
        self.assertEqual(argv[0], "task-start.py")
        self.assertIn("--aidlc", argv)
        self.assertIn("off", argv)
        self.assertIn("--no-planning-lock", argv)
        self.assertNotIn("--graph", argv)
        self.assertNotIn("--host", argv)
        self.assertNotIn("--verbose", argv)

    def test_argv_forwards_graph_host_and_verbose(self) -> None:
        argv = start_request.start_argv(start_request.normalize_start_request(
            "update delivery service behavior", graph="auto",
            host="codex", verbose=True))
        for flag in ("--graph", "auto", "--host", "codex", "--verbose"):
            self.assertIn(flag, argv)

    def test_rejects_empty_goal_and_bad_enums(self) -> None:
        with self.assertRaises(ValueError):
            start_request.normalize_start_request("   ")
        for kwargs in ({"aidlc": "turbo"}, {"graph": "sometimes"}, {"host": "gemini"}):
            with self.assertRaises(ValueError):
                start_request.normalize_start_request("update delivery service behavior", **kwargs)


if __name__ == "__main__":
    unittest.main()
