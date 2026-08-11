from __future__ import annotations

import importlib.util
import json
import subprocess
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


ledger = load("closure_recorder_ledger_test", "scripts/run-ledger.py")
anchor = load("closure_recorder_anchor_test", "scripts/change-intent-anchor.py")
lock = load("closure_recorder_lock_test", "scripts/planning-lock.py")
recorder = load("closure_recorder_test", "scripts/closure-recorder.py")


class ClosureRecorderTests(unittest.TestCase):
    def setup_run(self, root: Path, *, approved: bool = True) -> list[str]:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "service.py").write_text("def cancel():\n    return True\n", encoding="utf-8")
        (root / "tests" / "test_service.py").write_text("# focused receipt target\n", encoding="utf-8")
        lock.create(root, "cancel an order", "run")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [
            {"statement": "Reject cancellation after shipment.", "acceptance_criteria": ["shipped order rejects"], "preserve_rules": [], "likely_paths": ["src/service.py"], "evidence_plan": [], "validation_contract": {"state": "required", "tiers": ["unit"]}},
            {"statement": "Release inventory once for eligible cancellation.", "acceptance_criteria": ["inventory returns"], "preserve_rules": [], "likely_paths": ["src/service.py"], "evidence_plan": [], "validation_contract": {"state": "required", "tiers": ["unit"]}},
        ]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        approved_anchor = anchor.approve(root, "run")
        if approved:
            lock.approve(root, "run", True)
        return [row["requirement_uid"] for row in approved_anchor["requirements"]]

    def input(self, uids: list[str]) -> dict[str, object]:
        return {
            "schema_version": "1", "type": "tailtrail-execution-closure-input", "run_id": "run",
            "changed_paths": ["src/service.py", "tests/test_service.py"],
            "receipts": [{
                "requirement_uids": uids, "tier": "unit", "command_label": "cancellation service tests",
                "command": "python -m unittest tests.test_service -v", "outcome": "pass", "environment": "local",
                "asserted_behavior": "Shipped orders reject and eligible cancellations release inventory once.",
            }],
        }

    def test_records_receipts_checkpoint_gate_and_review_from_one_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uids = self.setup_run(root)
            input_path = root / "closure-input.json"
            input_path.write_text(json.dumps(self.input(uids)), encoding="utf-8")
            result = recorder.record(root, input_path)
            checkpoint = json.loads(Path(result["checkpoint"]).read_text(encoding="utf-8"))
            activity = ledger.projection(root, "run")["activity"]
        self.assertFalse(result["reused"])
        self.assertEqual(len(result["receipt_artifacts"]), 2)
        self.assertTrue(result["completion_gate"]["complete"])
        self.assertTrue(result["completion_review"]["complete"])
        self.assertEqual([row["state"] for row in checkpoint["requirements"]], ["validated", "validated"])
        self.assertTrue(all(row["fingerprint"].startswith("sha256:") for row in checkpoint["changed_paths"]))
        self.assertEqual(activity["closure_recorded"], 1)
        self.assertIn("No listed command was executed", result["boundary"])

    def test_replaying_the_same_input_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uids = self.setup_run(root)
            input_path = root / "closure-input.json"
            input_path.write_text(json.dumps(self.input(uids)), encoding="utf-8")
            first = recorder.record(root, input_path)
            second = recorder.record(root, input_path)
            activity = ledger.projection(root, "run")["activity"]
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(first["record_id"], second["record_id"])
        self.assertEqual(activity["closure_recorded"], 1)

    def test_failed_requirement_evidence_keeps_the_closure_gate_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uids = self.setup_run(root)
            payload = self.input(uids)
            payload["receipts"][0]["outcome"] = "fail"  # type: ignore[index]
            input_path = root / "closure-input.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            result = recorder.record(root, input_path)
        self.assertFalse(result["completion_gate"]["complete"])
        self.assertFalse(result["completion_review"]["complete"])
        self.assertIn("completion-report", result["next_action"])

    def test_requires_an_approved_planning_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uids = self.setup_run(root, approved=False)
            input_path = root / "closure-input.json"
            input_path.write_text(json.dumps(self.input(uids)), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "explicit approval"):
                recorder.record(root, input_path)

    def test_public_cli_records_evidence_without_executing_the_listed_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uids = self.setup_run(root)
            payload = self.input(uids)
            payload["receipts"][0]["command"] = "tailtrail-never-execute-closure-recorder-sentinel"  # type: ignore[index]
            input_path = root / "closure-input.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "closure", "record", "--root", root.as_posix(), "--input", input_path.as_posix()],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["reused"])
