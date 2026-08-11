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
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("closure_finalizer_ledger_test", "scripts/run-ledger.py")
anchor = load("closure_finalizer_anchor_test", "scripts/change-intent-anchor.py")
lock = load("closure_finalizer_lock_test", "scripts/planning-lock.py")
recorder = load("closure_finalizer_recorder_test", "scripts/closure-recorder.py")
finalizer = load("closure_finalizer_test", "scripts/closure-finalizer.py")


class ClosureFinalizerTests(unittest.TestCase):
    def setup_run(self, root: Path, *, behavior_scenario: bool = True) -> tuple[str, Path]:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "service.py").write_text("def cancel():\n    return True\n", encoding="utf-8")
        (root / "tests" / "test_service.py").write_text("# focused test\n", encoding="utf-8")
        lock.create(root, "cancel an order", "run")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{
            "statement": "Cancel an eligible order exactly once.", "acceptance_criteria": ["cancelled once"],
            "preserve_rules": ["shipped orders remain rejected"],
            "likely_paths": ["src/service.py", "tests/test_service.py"], "evidence_plan": [],
            "validation_contract": {"state": "required", "tiers": ["unit"]},
            "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []},
            "behavior_contract": {"scenarios": ([{
                "scenario_id": "eligible-cancellation", "preconditions": ["eligible order"],
                "action": "cancel order", "expected_outcome": "one cancellation", "preservation": ["shipped orders reject"],
                "evidence": [{"tier": "unit", "asserted_behavior": "Eligible order cancellation is idempotent."}],
            }] if behavior_scenario else [])},
        }]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        uid = anchor.approve(root, "run")["requirements"][0]["requirement_uid"]
        lock.approve(root, "run", True)
        run = ledger.state_dir(root, "run")
        (run / "planning").mkdir(exist_ok=True)
        (run / "planning" / "execution-handoff-v1.json").write_text(json.dumps({"closure": {"selected_harnesses": [
            "Architecture Fitness Harness", "Behaviour Harness", "Maintainability Harness",
        ]}}), encoding="utf-8")
        input_path = root / "closure-input.json"
        input_path.write_text(json.dumps({
            "schema_version": "1", "type": "tailtrail-execution-closure-input", "run_id": "run",
            "changed_paths": ["src/service.py", "tests/test_service.py"],
            "receipts": [{"requirement_uids": [uid], "tier": "unit", "command_label": "cancellation unit proof",
                "command": "tailtrail-never-execute-finalizer-sentinel", "outcome": "pass", "environment": "local",
                "asserted_behavior": "Eligible order cancellation is idempotent."}],
        }), encoding="utf-8")
        recorder.record(root, input_path)
        return uid, input_path

    def test_finalizes_selected_local_harnesses_and_completion_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            result = finalizer.finalize(root, "run")
            activity = ledger.projection(root, "run")["activity"]
        self.assertFalse(result["reused"])
        self.assertEqual(result["overall_status"], "complete")
        self.assertEqual(set(result["assessments"]), {"Architecture Fitness Harness", "Behaviour Harness", "Maintainability Harness"})
        self.assertTrue(all(item["complete"] for item in result["assessments"].values()))
        self.assertEqual(result["higher_tier_evidence"]["status"], "pass")
        self.assertEqual(result["recovery"]["status"], "not-needed")
        self.assertEqual(result["context_continuity"]["status"], "none")
        self.assertEqual(activity["closure_finalized"], 1)

    def test_replay_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            first = finalizer.finalize(root, "run")
            second = finalizer.finalize(root, "run")
            activity = ledger.projection(root, "run")["activity"]
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(first["finalizer_id"], second["finalizer_id"])
        self.assertEqual(activity["closure_finalized"], 1)

    def test_selected_behavior_without_a_declared_scenario_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root, behavior_scenario=False)
            result = finalizer.finalize(root, "run")
        self.assertEqual(result["overall_status"], "evidence-incomplete")
        self.assertFalse(result["assessments"]["Behaviour Harness"]["complete"])
        self.assertIn("No receipt command", result["boundary"])

    def test_rejects_mismatched_input_before_recording_anything(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, input_path = self.setup_run(root)
            payload = json.loads(input_path.read_text(encoding="utf-8"))
            payload["run_id"] = "other-run"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must match"):
                finalizer.finalize(root, "run", input_path)
            other_run = ledger.state_dir(root, "other-run")
        self.assertFalse(other_run.exists())


if __name__ == "__main__":
    unittest.main()
