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


lock = load("custody_lock_test", "scripts/planning_lock.py")
ledger = load("custody_ledger_test", "scripts/run-ledger.py")
evidence = load("custody_evidence_test", "scripts/execution-evidence.py")
anchor_mod = load("custody_anchor_test", "scripts/change-intent-anchor.py")
recorder = load("custody_recorder_test", "scripts/closure-recorder.py")


def _matrix_row(**overrides):
    row = {
        "requirement_uid": "req-1", "display_id": "REQ-01", "kind": "change",
        "statement": "Do the thing.", "acceptance_criteria": ["Done."],
        "preserve_rules": [], "likely_paths": ["src/work.py"],
        "evidence_plan": ["Run unit proof."],
        "validation_contract": {"state": "required", "tiers": ["unit"]},
    }
    row.update(overrides)
    return row


def _approved_run(root: Path, run_id: str, contract: dict | None = None) -> None:
    lock.create(root, "do the thing", run_id)
    ledger.atomic_json(lock.start_report_path(root, run_id), {"report": {
        "goal": "do the thing",
        "aidlc_mode": {"mode": "lite"},
        "guided_delivery": {"mode": "guided-delivery"},
        "navigator": {"requirement_matrix": [_matrix_row()]},
    }})
    lock.approve(root, run_id, True)
    anchor_dir = root / ".tailtrail" / "runs" / run_id / "anchors"
    anchor_dir.mkdir(parents=True, exist_ok=True)
    row = _matrix_row()
    if contract is not None:
        row["validation_contract"] = contract
    (anchor_dir / "approved-v1.json").write_text(json.dumps({
        "schema_version": "1", "type": "tailtrail-change-intent-anchor",
        "run_id": run_id, "status": "approved", "requirements": [{**row, "status": "approved"}],
    }), encoding="utf-8")


def _activate_overlay(root: Path, run_id: str, contract: dict) -> None:
    overlay_row = _matrix_row()
    overlay_row["validation_contract"] = contract
    snapshot = {
        "schema_version": "1", "type": "tailtrail-start-report",
        "run_id": run_id, "revision": 2, "goal": "do the thing",
        "report": {"navigator": {"requirement_matrix": [overlay_row]}},
    }
    revisions = root / ".tailtrail" / "runs" / run_id / "planning" / "revisions"
    revisions.mkdir(parents=True, exist_ok=True)
    (revisions / "start-report-v2.json").write_text(json.dumps(snapshot), encoding="utf-8")
    ledger.atomic_json(lock.revision_state_path(root, run_id), {
        "schema_version": "1", "type": "tailtrail-plan-revision-state",
        "run_id": run_id, "active_revision": 2,
        "active_report": f".tailtrail/runs/{run_id}/planning/revisions/start-report-v2.json",
        "pending_revision": None, "pending_artifact": None,
    })


class ApprovedPlanFingerprintTests(unittest.TestCase):
    def test_deterministic_and_sensitive_to_contracts(self) -> None:
        contracts = {"req-1": {"tiers": ["unit"], "commands": ["pytest"],
                               "checks": [{"command": "pytest", "tiers": ["unit"]}]}}
        first = anchor_mod.approved_plan_fingerprint(contracts)
        self.assertTrue(first.startswith("sha256:"))
        self.assertEqual(first, anchor_mod.approved_plan_fingerprint(contracts))
        changed = {"req-1": {"tiers": ["unit", "integration"], "commands": ["pytest"],
                             "checks": [{"command": "pytest", "tiers": ["unit"]}]}}
        self.assertNotEqual(first, anchor_mod.approved_plan_fingerprint(changed))


class ExecutionCustodyTests(unittest.TestCase):
    def test_run_stamps_plan_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _approved_run(root, "plan-custody-stamp", {
                "state": "required", "tiers": ["unit"], "commands": ["echo tailtrail-proof"],
            })
            result = evidence.run_command(
                root, "plan-custody-stamp", ["req-1"], ["unit"],
                "echo tailtrail-proof", "late-proof", [], True,
            )
            self.assertEqual(result["outcome"], "pass")
            self.assertTrue(result["plan_fingerprint"].startswith("sha256:"))

    def test_overlay_revision_changes_fingerprint(self) -> None:
        command = "echo tailtrail-proof"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _approved_run(root, "plan-custody-drift", {
                "state": "required", "tiers": ["unit"], "commands": [command],
            })
            before = evidence.run_command(
                root, "plan-custody-drift", ["req-1"], ["unit"], command, "proof", [], True,
            )
            _activate_overlay(root, "plan-custody-drift", {
                "state": "required", "tiers": ["unit", "behaviour"], "commands": [command],
            })
            after = evidence.run_command(
                root, "plan-custody-drift", ["req-1"], ["behaviour"], command, "proof", [], True,
            )
            self.assertNotEqual(before["plan_fingerprint"], after["plan_fingerprint"])


class ClosureCustodyTests(unittest.TestCase):
    def test_partition_current_legacy_stale(self) -> None:
        receipts = [
            {"command": "a", "plan_fingerprint": "sha256:current"},
            {"command": "b"},
            {"command": "c", "plan_fingerprint": "sha256:old"},
        ]
        parts = recorder.partition_plan_receipts(receipts, "sha256:current")
        self.assertEqual([r["command"] for r in parts["current"]], ["a"])
        self.assertEqual([r["command"] for r in parts["legacy"]], ["b"])
        self.assertEqual([r["command"] for r in parts["stale"]], ["c"])

    def test_current_fingerprint_matches_execution_stamp(self) -> None:
        command = "echo tailtrail-proof"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _approved_run(root, "plan-custody-current", {
                "state": "required", "tiers": ["unit"], "commands": [command],
            })
            result = evidence.run_command(
                root, "plan-custody-current", ["req-1"], ["unit"], command, "proof", [], True,
            )
            current = recorder.current_plan_fingerprint(root, "plan-custody-current")
            self.assertEqual(result["plan_fingerprint"], current)


if __name__ == "__main__":
    unittest.main()
