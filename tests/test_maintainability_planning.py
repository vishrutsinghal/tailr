from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


task_start = load("tailtrail_maintainability_start_test", "scripts/task-start.py")
harness = load("tailtrail_maintainability_baseline_test", "scripts/maintainability-harness.py")


GOAL = (
    "Refactor duplicate payment and notification orchestration in the order service. "
    "Reuse an existing project boundary where possible, preserve all public behaviour and tests, "
    "avoid speculative abstractions, and show that the change reduces duplication without expanding unrelated scope."
)


def project(root: Path) -> None:
    files = {
        "src/order_service/service.py": "def submit():\n    return payment()\n",
        "src/order_service/payments.py": "def payment_effect(value):\n    result = normalize(value)\n    return publish(result)\n",
        "src/order_service/notifications.py": "def notification_effect(value):\n    result = normalize(value)\n    return publish(result)\n",
        "tests/integration/test_order_service.py": "def test_submit():\n    pass\n",
        "tests/behaviour/test_customer_journey.py": "def test_public_behaviour():\n    pass\n",
        "pyproject.toml": "[project]\nname='demo'\n",
    }
    for relative, body in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")


class MaintainabilityPlanningTests(unittest.TestCase):
    def test_start_segregates_requirements_and_renders_evidence_backed_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project(root)
            report = task_start.build_report(GOAL, root, [], "tailtrail")
            rendered = task_start.verbose_start_report(report)
        statements = [row["statement"] for row in report["navigator"]["requirement_matrix"]]
        self.assertEqual(7, len(statements))
        self.assertIn("Preserve all public behaviour.", statements)
        self.assertIn("Preserve tests.", statements)
        self.assertIn("Do not expand unrelated scope.", statements)
        self.assertTrue(report["maintainability_plan"]["selected"])
        self.assertIn("## Maintainability Harness Plan", rendered)
        self.assertIn("### Pre-edit baseline metrics", rendered)
        self.assertIn("MNT-01", rendered)
        self.assertNotIn("Replay or retry the logical transition that publishes a notification", rendered)
        self.assertNotIn("Exercise the existing API response", rendered)
        tiers = {tier for row in report["navigator"]["requirement_matrix"] for tier in row["validation_contract"]["tiers"]}
        self.assertNotIn("contract", tiers)

    def test_approval_captures_baseline_and_post_change_assessment_uses_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project(root)
            report = task_start.build_report(GOAL, root, [], "tailtrail")
            report["planning_lock"] = task_start.planning_lock.create(root, GOAL, "maintainability-plan")
            task_start.planning_lock.save_start_report(root, "maintainability-plan", report)
            activated = task_start.planning_lock.activate(root, "maintainability-plan", True)
            baseline_path = root / activated["execution_handoff"]["maintainability_baseline"]["artifact"]
            baseline_exists = baseline_path.is_file()
            approved = json.loads((root / activated["execution_handoff"]["anchor"]).read_text(encoding="utf-8"))
            (root / "src/order_service/notifications.py").write_text(
                "from .payments import payment_effect\n\ndef notification_effect(value):\n    return payment_effect(value)\n",
                encoding="utf-8",
            )
            result = harness.assess(root, "maintainability-plan", ["src/order_service/notifications.py"])
        self.assertTrue(baseline_exists)
        self.assertTrue(any(row["maintainability_contract"].get("rules") for row in approved["requirements"]))
        self.assertTrue(any(row["rule_id"] == "MNT-01" and row["state"] == "improved" for row in result["rule_results"]))
        self.assertEqual(-1, result["metrics"]["duplicate_function_body_groups"]["delta"])


if __name__ == "__main__":
    unittest.main()
