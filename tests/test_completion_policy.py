"""Regression coverage for the shared completion policy (Issue 37)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, script: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


POLICY = _load("test_completion_policy_module", "completion-policy.py")
RUNS = _load("test_run_ledger_module", "run-ledger.py")
RUN_ID = "start-test-issue37"


class CompletionPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.artifact = self.root / "docs" / "inventory-map.md"
        self.artifact.parent.mkdir(parents=True)
        self.artifact.write_text("# Inventory map\n", encoding="utf-8")
        RUNS.init_run(self.root, RUN_ID, "issue 37 regression")
        RUNS.init_run(self.root, "start-other-run", "issue 37 other run")
        report_path = POLICY.LOCK.start_report_path(self.root, RUN_ID)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _mode(self, mode: str | None):
        payload = {"host_input_contract": {"request_mode": mode}} if mode else {}
        return mock.patch.object(POLICY.LOCK, "active_start_report", return_value={"goal": "g", "report": payload})

    def test_legacy_report_without_contract_is_not_applicable(self) -> None:
        with self._mode(None):
            policy = POLICY.evaluate(self.root, RUN_ID, [])
        self.assertEqual(policy["status"], "not-applicable")

    def test_flat_or_malformed_current_contract_fails_closed(self) -> None:
        # The pre-fix flat shape must not silently become not-applicable.
        flat = {"host_input_contract": {"request_mode": "validation-only"}}
        with mock.patch.object(POLICY.LOCK, "active_start_report", return_value=flat):
            policy = POLICY.evaluate(self.root, RUN_ID, [])
        self.assertEqual(policy["status"], "evidence-incomplete")
        self.assertEqual(policy["missing"][0]["artifact"], "host-input-contract")
        self.assertIn("tailtrail planning show", policy["recovery"])
        self.assertFalse(POLICY.passes(policy))

        empty = {"goal": "g", "report": {"host_input_contract": {"request_mode": ""}}}
        with mock.patch.object(POLICY.LOCK, "active_start_report", return_value=empty):
            policy = POLICY.evaluate(self.root, RUN_ID, [])
        self.assertEqual(policy["status"], "evidence-incomplete")

    def test_validation_only_without_delivery_stays_incomplete(self) -> None:
        # Case 1: passing managed proof alone never completes a validation-only run.
        with self._mode("validation-only"):
            policy = POLICY.evaluate(self.root, RUN_ID, [])
        self.assertEqual(policy["status"], "evidence-incomplete")
        self.assertEqual(policy["required_artifacts"], ["validation-delivery"])
        self.assertFalse(POLICY.passes(policy))
        self.assertIn("record-delivery", policy["recovery"])

    def test_validation_only_with_current_hash_bound_delivery_completes(self) -> None:
        # Case 2: a current, hash-bound delivery completes with zero changed paths.
        POLICY.record_delivery(self.root, RUN_ID, self.artifact, "phase0-inventory-map")
        with self._mode("validation-only"):
            policy = POLICY.evaluate(self.root, RUN_ID, [])
        self.assertEqual(policy["status"], "pass")
        self.assertNotIn("source-edit-receipt", policy["required_artifacts"])
        self.assertFalse(policy["implementation_applicable"])

    def test_stale_delivery_is_rejected(self) -> None:
        POLICY.record_delivery(self.root, RUN_ID, self.artifact, "phase0-inventory-map")
        self.artifact.write_text("changed after recording\n", encoding="utf-8")
        with self._mode("read-only"):
            policy = POLICY.evaluate(self.root, RUN_ID, [])
        self.assertEqual(policy["status"], "evidence-incomplete")
        self.assertIn("changed after it was recorded", policy["missing"][0]["message"])

    def test_delivery_from_another_run_is_rejected(self) -> None:
        POLICY.record_delivery(self.root, "start-other-run", self.artifact, "phase0-inventory-map")
        with self._mode("validation-only"):
            policy = POLICY.evaluate(self.root, RUN_ID, [])
        self.assertEqual(policy["status"], "evidence-incomplete")
        self.assertIn("no validation-delivery receipt", policy["missing"][0]["message"])

    def test_implementation_without_source_edit_evidence_stays_incomplete(self) -> None:
        # Case 3: passing proof with no approved source-edit evidence is incomplete.
        with self._mode("implementation"):
            missing = POLICY.evaluate(self.root, RUN_ID, [])
            present = POLICY.evaluate(self.root, RUN_ID, ["scripts/example.py"])
        self.assertEqual(missing["status"], "evidence-incomplete")
        self.assertEqual(missing["missing"][0]["artifact"], "source-edit-receipt")
        self.assertEqual(present["status"], "pass")

    def test_missing_contract_is_not_applicable_for_legacy_runs(self) -> None:
        with self._mode(None):
            policy = POLICY.evaluate(self.root, RUN_ID, [])
        self.assertEqual(policy["status"], "not-applicable")
        self.assertTrue(POLICY.passes(policy))

    def test_delivery_receipt_is_hash_bound(self) -> None:
        receipt = POLICY.record_delivery(self.root, RUN_ID, self.artifact, "phase0-inventory-map")
        expected = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.assertEqual(receipt["artifact_sha256"], expected)
        self.assertEqual(receipt["artifact_path"], "docs/inventory-map.md")


if __name__ == "__main__":
    unittest.main()
