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


revision = load("tailtrail_overlay_revision_test", "scripts/planning-revision.py")
evidence = load("tailtrail_overlay_evidence_test", "scripts/execution-evidence.py")
lock = load("tailtrail_overlay_lock_test", "scripts/planning_lock.py")
ledger = load("tailtrail_overlay_ledger_test", "scripts/run-ledger.py")


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


class ProofUpdateCommandsTests(unittest.TestCase):
    def test_proof_update_sets_commands_and_tiers(self):
        rows = [_matrix_row()]
        change = {
            "kind": "proof-update", "requirement_uid": "req-1",
            "reason": "attach late proof",
            "evidence_plan": ["Run unit proof."],
            "commands": ["python -m unittest tests.test_work -v"],
            "tiers": ["unit", "integration"],
        }
        revision._apply_change(Path("."), {"navigator": {}}, rows, change, "run-1")
        contract = rows[0]["validation_contract"]
        self.assertEqual(contract["commands"], ["python -m unittest tests.test_work -v"])
        self.assertEqual(contract["tiers"], ["unit", "integration"])

    def test_proof_update_unions_without_dropping(self):
        rows = [_matrix_row()]
        rows[0]["validation_contract"]["commands"] = ["python -m unittest tests.test_old -v"]
        change = {
            "kind": "proof-update", "requirement_uid": "req-1",
            "reason": "attach more proof",
            "evidence_plan": ["Run unit proof."],
            "commands": ["python -m unittest tests.test_new -v"],
        }
        revision._apply_change(Path("."), {"navigator": {}}, rows, change, "run-1")
        self.assertEqual(
            rows[0]["validation_contract"]["commands"],
            ["python -m unittest tests.test_old -v", "python -m unittest tests.test_new -v"],
        )

    def test_proof_update_without_command_keys_mints_nothing(self):
        rows = [_matrix_row()]
        change = {
            "kind": "proof-update", "requirement_uid": "req-1",
            "reason": "reword plan",
            "evidence_plan": ["Run unit proof, revised."],
        }
        revision._apply_change(Path("."), {"navigator": {}}, rows, change, "run-1")
        self.assertNotIn("commands", rows[0]["validation_contract"])
        self.assertEqual(rows[0]["evidence_plan"], ["Run unit proof, revised."])

    def test_proof_update_rejects_empty_commands(self):
        rows = [_matrix_row()]
        change = {
            "kind": "proof-update", "requirement_uid": "req-1",
            "reason": "bad proof",
            "evidence_plan": ["Run unit proof."],
            "commands": [],
        }
        with self.assertRaises(ValueError):
            revision._apply_change(Path("."), {"navigator": {}}, rows, change, "run-1")


class RevisionOverlayExecutionTests(unittest.TestCase):
    def _approved_run(self, root: Path, run_id: str) -> None:
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
        (anchor_dir / "approved-v1.json").write_text(json.dumps({
            "schema_version": "1", "type": "tailtrail-change-intent-anchor",
            "run_id": run_id, "status": "approved",
            "requirements": [{
                "requirement_uid": "req-1", "display_id": "REQ-01", "kind": "change",
                "statement": "Do the thing.", "acceptance_criteria": ["Done."],
                "preserve_rules": [], "likely_paths": ["src/work.py"],
                "evidence_plan": ["Run unit proof."],
                "validation_contract": {"state": "required", "tiers": ["unit"]},
                "status": "approved",
            }],
        }), encoding="utf-8")

    def _activate_overlay(self, root: Path, run_id: str, command: str) -> None:
        overlay_row = _matrix_row()
        overlay_row["validation_contract"] = {
            "state": "required", "tiers": ["unit"], "commands": [command],
        }
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

    def test_overlay_authorizes_revision_command(self):
        command = "echo tailtrail-proof"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._approved_run(root, "plan-overlay")
            self._activate_overlay(root, "plan-overlay", command)
            result = evidence.run_command(
                root, "plan-overlay", ["req-1"], ["unit"], command,
                "late-proof", [], True,
            )
        self.assertEqual(result["outcome"], "pass")

    def test_no_overlay_without_active_revision(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._approved_run(root, "plan-no-overlay")
            with self.assertRaisesRegex(ValueError, "not approved for requirement"):
                evidence.run_command(
                    root, "plan-no-overlay", ["req-1"], ["unit"],
                    "echo tailtrail-proof", "late-proof", [], True,
                )

    def test_pending_revision_grants_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._approved_run(root, "plan-pending")
            self._activate_overlay(root, "plan-pending", "echo tailtrail-proof")
            ledger.atomic_json(lock.revision_state_path(root, "plan-pending"), {
                "schema_version": "1", "type": "tailtrail-plan-revision-state",
                "run_id": "plan-pending", "active_revision": 1,
                "active_report": f".tailtrail/runs/plan-pending/planning/start-report-v1.json",
                "pending_revision": 2,
                "pending_artifact": f".tailtrail/runs/plan-pending/planning/revisions/start-report-v2.json",
            })
            with self.assertRaisesRegex(ValueError, "not approved for requirement"):
                evidence.run_command(
                    root, "plan-pending", ["req-1"], ["unit"],
                    "echo tailtrail-proof", "late-proof", [], True,
                )


class StaleCheckEntryTierUnionTests(unittest.TestCase):
    """Regression for Issue 27: a Start-time checks[] entry for the exact
    proof command must not silently discard tiers a later proof-update
    revision added to the top-level validation_contract.tiers."""

    def _approved_run_with_check(self, root: Path, run_id: str, command: str) -> None:
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
        (anchor_dir / "approved-v1.json").write_text(json.dumps({
            "schema_version": "1", "type": "tailtrail-change-intent-anchor",
            "run_id": run_id, "status": "approved",
            "requirements": [{
                "requirement_uid": "req-1", "display_id": "REQ-01", "kind": "change",
                "statement": "Do the thing.", "acceptance_criteria": ["Done."],
                "preserve_rules": [], "likely_paths": ["src/work.py"],
                "evidence_plan": ["Run unit proof."],
                "validation_contract": {
                    "state": "required", "tiers": ["unit"], "commands": [command],
                    "checks": [{"command": command, "tiers": ["unit"], "candidate_paths": [], "kind": "unit"}],
                },
                "status": "approved",
            }],
        }), encoding="utf-8")

    def _activate_overlay_tiers(self, root: Path, run_id: str, command: str, tiers: list[str]) -> None:
        overlay_row = _matrix_row()
        overlay_row["validation_contract"] = {"state": "required", "tiers": tiers, "commands": [command]}
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

    def test_revision_added_tier_survives_matching_check_entry(self):
        command = "echo tailtrail-proof"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._approved_run_with_check(root, "plan-stale-check", command)
            self._activate_overlay_tiers(root, "plan-stale-check", command, ["unit", "behaviour"])
            result = evidence.run_command(
                root, "plan-stale-check", ["req-1"], ["behaviour"], command,
                "late-proof", [], True,
            )
        self.assertEqual(result["outcome"], "pass")


if __name__ == "__main__":
    unittest.main()
