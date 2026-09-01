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
    sys.modules[name] = module; spec.loader.exec_module(module)
    return module


discovery = load("tailtrail_requirement_discovery_test", "scripts/requirement_discovery.py")
task_start = load("tailtrail_requirement_start_test", "scripts/task-start.py")
planning_lock = task_start.planning_lock


class RequirementDiscoveryTests(unittest.TestCase):
    def test_workflow_routing_prefix_is_not_a_delivery_requirement(self) -> None:
        statements = discovery.statements(
            "using AIDLC, add delivery-address validation across the API and service. "
            "Preserve existing create-order behavior."
        )
        self.assertNotIn("Using AIDLC.", statements)
        self.assertEqual(
            statements,
            [
                "Add delivery-address validation across the API and service.",
                "Preserve existing create-order behavior.",
            ],
        )

    def test_bullets_sentences_and_semicolons_become_stable_requirement_rows(self) -> None:
        goal = """Add cancellation eligibility.
- Release inventory exactly once
- Preserve shipped-order behavior; update the API contract."""
        rows = discovery.matrix(goal, ["src/service.py"])
        self.assertEqual([row["display_id"] for row in rows], ["REQ-01", "REQ-02", "REQ-03", "REQ-04"])
        self.assertEqual(rows[2]["kind"], "preserve")
        self.assertTrue(all(row["likely_paths"] == ["src/service.py"] for row in rows))

    def test_shared_subject_action_list_splits_without_splitting_object_lists(self) -> None:
        goal = "Cancellation releases stock, refunds payment, sends one notification, retains an audit event with actor, reason, and revision, and updates the API contract and tests."
        statements = discovery.statements(goal)
        self.assertEqual(len(statements), 5)
        self.assertIn("Cancellation refunds payment.", statements)
        self.assertIn("actor, reason, and revision", statements[3])
        self.assertIn("API contract and tests", statements[4])

    def test_compact_and_verbose_start_render_the_same_segregated_matrix(self) -> None:
        goal = "Add cancellation eligibility; release inventory; preserve shipped orders; update the API contract and add integration tests."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report(goal, root, ["src/service.py"], "tailtrail")
            compact = task_start.compact_start_report(report)
            verbose = task_start.verbose_start_report(report)
        self.assertGreaterEqual(len(report["navigator"]["requirement_matrix"]), 5)
        self.assertEqual(report["guided_delivery"]["mode"], "guided-delivery")
        self.assertIn("Requirement Completion Harness", [item["name"] for item in report["guided_delivery"]["selected"]])
        for index in range(1, 6):
            label = f"REQ-{index:02d}"
            self.assertIn(label, compact); self.assertIn(label, verbose)
        self.assertIn("one approved requirement row at a time", compact)
        self.assertIn("map and implement one approved requirement at a time", verbose)

    def test_quick_guided_and_expert_are_distinct_views_of_one_plan(self) -> None:
        goal = "Add cancellation eligibility; release inventory; preserve shipped orders; add integration proof."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report(goal, root, ["src/service.py"], "tailtrail")
            report["planning_lock"] = planning_lock.create(root, goal, "presentation-run")
            quick = task_start.render_markdown(report, presentation_mode="quick")
            guided = task_start.render_markdown(report, presentation_mode="guided")
            expert = task_start.render_markdown(report, presentation_mode="expert")
            verbose = [
                task_start.render_markdown(report, presentation_mode=mode, verbose=True)
                for mode in ("quick", "guided", "expert")
            ]
        for mode, rendered in (("quick", quick), ("guided", guided), ("expert", expert)):
            self.assertIn(f"**Presentation:** `{mode}`", rendered)
            for heading in ("Planning Lock", "Requirements", "Selected TailTrail features", "Approval"):
                self.assertIn(heading, rendered)
        self.assertLess(len(quick), len(guided))
        self.assertLess(len(guided), len(expert))
        normalized = [item.replace("`quick`", "`mode`").replace("`guided`", "`mode`").replace("`expert`", "`mode`") for item in verbose]
        self.assertEqual(normalized[0], normalized[1])
        self.assertEqual(normalized[1], normalized[2])

    def test_approved_anchor_uses_the_displayed_requirement_rows(self) -> None:
        goal = "Add cancellation eligibility; release inventory; preserve shipped orders."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report(goal, root, ["src/service.py"], "tailtrail")
            report["planning_lock"] = planning_lock.create(root, goal, "segregated-run")
            planning_lock.save_start_report(root, "segregated-run", report)
            activated = planning_lock.activate(root, "segregated-run", True)
            approved = json.loads((root / activated["execution_handoff"]["anchor"]).read_text(encoding="utf-8"))
        displayed = [row["statement"] for row in report["navigator"]["requirement_matrix"]]
        self.assertEqual([row["statement"] for row in approved["requirements"]], displayed)
        self.assertEqual(len(activated["execution_handoff"]["active_requirements"]), len(displayed))


if __name__ == "__main__":
    unittest.main()
