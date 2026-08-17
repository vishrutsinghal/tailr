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
    if spec is None or spec.loader is None:
        raise RuntimeError(relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


failures = load("execution_failure_test_helper", "scripts/execution-failure.py")
ledger = failures.LEDGER
planning = failures.PLANNING
anchor = failures.ANCHOR


class ExecutionFailureTests(unittest.TestCase):
    def approved_run(self, root: Path) -> str:
        run_id = "run-failure"
        planning.create(root, "fix validation", run_id)
        planning.approve(root, run_id, True)
        return run_id

    def approved_requirement(self, root: Path, run_id: str) -> str:
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"goal": "fix validation", "requirements": [{"statement": "Reject invalid claim amounts", "likely_paths": ["src/claims.py"], "preserve_rules": ["Positive claim amounts remain valid"], "architecture_contract": {"required_paths": ["src/claims.py"], "protected_paths": [], "forbidden_imports": []}}]}), encoding="utf-8")
        drafted = anchor.draft(root, run_id, proposal)
        anchor.approve(root, run_id)
        return drafted["requirements"][0]["requirement_uid"]

    def test_baseline_fixture_declares_sanitized_contracts(self) -> None:
        fixture = json.loads((ROOT / "tests" / "fixtures" / "execution-failure" / "baseline-scenarios.json").read_text(encoding="utf-8"))
        self.assertEqual(fixture["type"], "tailtrail-execution-failure-baseline")
        self.assertTrue(all(scenario.get("expected_raw_persisted") is False for scenario in fixture["scenarios"] if scenario.get("expected_record")))

    def test_record_requires_approved_lock_and_stores_no_raw_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = self.approved_run(root)
            recorded = failures.record(root, run_id, "user-pasted", "TEST_FAILURE", "focused pytest", "claims validation", 1, None)
            shown = failures.show(root, run_id)
            state = ledger.projection(root, run_id)
        self.assertEqual(recorded["failure_id"], "failure-0001")
        self.assertFalse(recorded["raw_persisted"])
        self.assertEqual(shown["evidence"]["error_code"], "TEST_FAILURE")
        self.assertEqual(state["activity"]["execution_failure_recorded"], 1)

    def test_record_rejects_unapproved_runs_and_unsafe_artifact_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            planning.create(root, "fix validation", "run-unapproved")
            with self.assertRaisesRegex(ValueError, "Planning Lock"):
                failures.record(root, "run-unapproved", "agent-command", "TEST_FAILURE", "pytest", "claims", 1, None)
            run_id = self.approved_run(root)
            with self.assertRaisesRegex(ValueError, "project-relative"):
                failures.record(root, run_id, "agent-command", "TEST_FAILURE", "pytest", "claims", 1, "../outside.log")
            with self.assertRaisesRegex(ValueError, "stable identifier"):
                failures.record(root, run_id, "agent-command", "Connection timed out for token abc", "pytest", "claims", 1, None)

    def test_intake_is_visible_without_creating_or_guessing_a_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt = failures.intake(Path(temp), None, "user-pasted", "ACCESS_DENIED", "terraform plan", "backend setup", 1)
        self.assertEqual(receipt["status"], "not-attached")
        self.assertEqual(receipt["classification"]["classification"], "permission")
        self.assertFalse(receipt["raw_persisted"])

    def test_intake_and_authority_diagnosis_stay_within_the_existing_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = self.approved_run(root)
            receipt = failures.intake(root, run_id, "agent-command", "ACCESS_DENIED", "terraform plan", "backend setup", 1)
            recorded = failures.record(root, run_id, "agent-command", "ACCESS_DENIED", "terraform plan", "backend setup", 1, None)
            diagnosed = failures.diagnose(root, run_id, recorded["failure_id"], "permission", "supported-hypothesis", "The active identity lacks the required permission.", "bounded-correction")
            state = ledger.projection(root, run_id)
        self.assertEqual(receipt["status"], "attached")
        self.assertEqual(diagnosed["status"], "blocked")
        self.assertTrue(diagnosed["authority"]["approval_required"])
        self.assertEqual(state["activity"]["execution_failure_intake"], 1)
        self.assertEqual(state["activity"]["execution_failure_blocked"], 1)

    def test_requirement_mapping_fingerprints_recurrence_and_routes_one_bounded_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = self.approved_run(root)
            requirement_uid = self.approved_requirement(root, run_id)
            first = failures.record(root, run_id, "agent-command", "TEST_FAILURE", "focused pytest", "claim validation", 1, None)
            failures.diagnose(root, run_id, first["failure_id"], "code", "supported-hypothesis", "The validation branch rejects a valid amount.", "bounded-correction")
            mapped = failures.map_requirement(root, run_id, first["failure_id"], requirement_uid, "approved-path", "unchanged", "The approved validation path still fails.", ["src/claims.py"])
            routed = failures.correction_route(root, run_id, first["failure_id"], 2)
            second = failures.record(root, run_id, "agent-command", "TEST_FAILURE", "focused pytest", "claim validation", 1, None)
            repeated = failures.map_requirement(root, run_id, second["failure_id"], requirement_uid, "approved-path", "unchanged", "The same approved validation path still fails.", ["src/claims.py"])
        self.assertTrue(mapped["drift_link"]["drift_created"])
        self.assertEqual(routed["correction_route"]["action"], "bounded-correction")
        self.assertFalse(routed["correction_route"]["correction_executed"])
        self.assertEqual(repeated["correlation"]["occurrence"], 2)
        self.assertEqual(repeated["correlation"]["prior_matching_failure_id"], first["failure_id"])


if __name__ == "__main__":
    unittest.main()
