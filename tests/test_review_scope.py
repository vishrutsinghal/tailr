from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "scripts").as_posix())

import navigator  # noqa: E402


class ReviewScopeTests(unittest.TestCase):
    def test_post_implementation_review_defaults_to_uncommitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide(
                "fix claim validation and review it after implementation",
                root,
                ["src/claims/validator.py"],
                "tailtrail",
            )

        plan = report["review_plan"]
        selected = {item["name"] for item in report["selected_features"]}
        commands = "\n".join(report["suggested_commands"])

        self.assertIn("Navigator-Led Review", selected)
        self.assertEqual(plan["scope"], "uncommitted")
        self.assertEqual(plan["default"], "uncommitted local changes")
        self.assertEqual(plan["detail_level"], "compact")
        self.assertIn("review --root", commands)
        self.assertIn("--scope uncommitted", commands)

    def test_standalone_branch_review_routes_to_branch_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide("review this branch before PR", root, [], "tailtrail")

        plan = report["review_plan"]

        self.assertEqual(plan["scope"], "branch")
        self.assertIn("--scope branch --base main", plan["command"])
        self.assertFalse(plan["needs_user_choice"])

    def test_ambiguous_review_asks_for_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide("review my code", root, [], "tailtrail")

        plan = report["review_plan"]

        self.assertEqual(plan["scope"], "needs_user_choice")
        self.assertTrue(plan["needs_user_choice"])
        self.assertEqual(plan["default"], "uncommitted local changes")
        self.assertIn("severity", plan["finding_fields"])


if __name__ == "__main__":
    unittest.main()
