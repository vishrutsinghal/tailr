from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader
    sys.modules[name] = module; spec.loader.exec_module(module); return module


lock = load("expert_controls_lock_test", "scripts/planning-lock.py")
controls = load("expert_controls_test", "scripts/planning-feature-controls.py")
ledger = load("expert_controls_ledger_test", "scripts/run-ledger.py")


class ExpertPlanCustomizationTests(unittest.TestCase):
    def plan(self, root: Path, run_id: str) -> None:
        lock.create(root, "add API behavior", run_id)
        lock.save_start_report(root, run_id, {
            "goal": "add API behavior",
            "aidlc_mode": {"mode": "lite", "selection": "default", "state": "planning", "boundary": "planning only"},
            "navigator": {"selected_features": [{"name": "Navigator", "why": "required"}, {"name": "Evidence-Aware Testing", "why": "required"}], "skipped_features": [{"name": "Behaviour Harness", "why": "no journey declared"}], "requirement_matrix": [{"display_id": "REQ-01", "statement": "Add API behavior."}]},
            "guided_delivery": {"selected": [{"name": "Evidence-Aware Testing", "why": "required"}], "activated_later": [{"name": "Context Continuity Harness", "when": "after drift"}]},
        })

    def test_catalog_applies_optional_feature_with_same_run_and_activates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root, "controls")
            shown = controls.show(root, "controls")
            proposal = controls.propose(root, "controls", [{"feature": "Behaviour Harness", "value": "selected", "reason": "Customer journey proof is required."}], True)
            result = controls.approve(root, "controls", 2, True)
            report = lock.active_start_report(root, "controls")["report"]
            events = ledger.projection(root, "controls")["activity"]

        self.assertIn("Behaviour Harness", {row["name"] for row in shown["controls"]})
        self.assertEqual(proposal["changes"][0]["value"], "selected")
        self.assertEqual(result["state"], "execution-ready")
        self.assertIn("Behaviour Harness", {row["name"] for row in report["guided_delivery"]["selected"]})
        self.assertEqual(events["planning_feature_controls_proposed"], 1)
        self.assertEqual(events["planning_feature_controls_approved"], 1)

    def test_locked_controls_and_unknown_features_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root, "locked")
            with self.assertRaisesRegex(ValueError, "locked core safeguard"):
                controls.propose(root, "locked", [{"feature": "Navigator", "value": "disabled", "reason": "skip"}], True)
            with self.assertRaisesRegex(ValueError, "unknown TailTrail feature"):
                controls.propose(root, "locked", [{"feature": "Made Up Harness", "value": "selected", "reason": "skip"}], True)

    def test_aidlc_standard_uses_the_generic_control_but_keeps_execution_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root, "standard")
            controls.propose(root, "standard", [{"feature": "AIDLC", "value": "standard", "reason": "Need structured clarification."}], True)
            result = controls.approve(root, "standard", 2, True)
            report = lock.active_start_report(root, "standard")["report"]
            status = lock.show(root, "standard")["status"]

        self.assertEqual(result["state"], "aidlc-requirements-gathering")
        self.assertEqual(status, "awaiting-approval")
        self.assertEqual(report["aidlc_mode"]["mode"], "standard")
        self.assertIn("aidlc_stage", report["aidlc_requirements"])


if __name__ == "__main__": unittest.main()
