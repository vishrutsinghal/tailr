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


ledger = load("official_state_ledger_test", "scripts/run-ledger.py")
anchor = load("official_state_anchor_test", "scripts/change-intent-anchor.py")
state = load("official_state_test", "scripts/official-aidlc-state.py")


class OfficialAidlcStateTests(unittest.TestCase):
    def setup_run(self, root: Path) -> tuple[Path, str]:
        ledger.init_run(root, "run", "reject zero quantities")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"goal": "reject zero quantities", "requirements": [{
            "statement": "reject zero quantities",
            "acceptance_criteria": ["zero is rejected"],
            "preserve_rules": ["positive quantities remain valid"],
            "likely_paths": ["src/validation.py"],
            "evidence_plan": ["focused unit test"],
        }]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        approved = anchor.approve(root, "run")
        return ledger.state_dir(root, "run"), approved["requirements"][0]["requirement_uid"]

    def checkpoint(self, directory: Path, uid: str, fingerprint: str | None) -> Path:
        path = directory / "checkpoints" / "checkpoint-1.json"
        path.parent.mkdir(parents=True)
        payload = {
            "schema_version": "1",
            "type": "tailtrail-harness-checkpoint",
            "run_id": "run",
            "checkpoint": 1,
            "requirements": [{"requirement_uid": uid, "state": "validated", "evidence": []}],
            "drift": [],
        }
        if fingerprint is not None:
            payload["anchor_fingerprint"] = fingerprint
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_valid_projection_uses_manifest_anchor_and_latest_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, uid = self.setup_run(root)
            approved = json.loads((directory / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
            self.checkpoint(directory, uid, approved["approved_fingerprint"])
            result = state.project(root, "run")
        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["requirements"][0]["requirement_uid"], uid)
        self.assertEqual(result["delivery"]["requirement_states"][uid], "validated")

    def test_legacy_checkpoint_without_fingerprint_is_warning_not_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, uid = self.setup_run(root)
            self.checkpoint(directory, uid, None)
            result = state.project(root, "run")
        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("legacy-checkpoint-fingerprint-missing", {row["code"] for row in result["issues"]})

    def test_checkpoint_from_another_anchor_is_blocking_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, uid = self.setup_run(root)
            self.checkpoint(directory, uid, "sha256:wrong")
            result = state.project(root, "run")
            with self.assertRaisesRegex(ValueError, "anchor-fingerprint-conflict"):
                state.assert_consistent(root, "run")
        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], "conflict")

    def test_unknown_requirement_and_mismatched_run_are_reported_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, uid = self.setup_run(root)
            approved = json.loads((directory / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
            checkpoint = self.checkpoint(directory, uid, approved["approved_fingerprint"])
            payload = json.loads(checkpoint.read_text(encoding="utf-8"))
            payload["run_id"] = "other"
            payload["requirements"].append({"requirement_uid": "req-not-approved", "state": "validated"})
            checkpoint.write_text(json.dumps(payload), encoding="utf-8")
            before = checkpoint.read_bytes()
            result = state.project(root, "run")
            self.assertEqual(before, checkpoint.read_bytes())
        self.assertTrue({"run-id-conflict", "unknown-checkpoint-requirement"}.issubset({row["code"] for row in result["issues"]}))

    def test_official_identity_projection_cannot_override_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, _ = self.setup_run(root)
            official = directory / "aidlc-official"
            official.mkdir()
            (official / "bridge-v1.json").write_text(json.dumps({
                "schema_version": "1", "type": "tailtrail-official-aidlc-bridge",
                "tailtrail_run_id": "run", "official_revision": "v2.0.0",
                "official_intent_id": "intent-1", "official_session_id": "session-1",
                "official_source": "https://github.com/awslabs/aidlc-workflows", "official_stage": "requirements",
            }), encoding="utf-8")
            (official / "activation-v1.json").write_text(json.dumps({
                "schema_version": "1", "tailtrail_run_id": "run", "official_revision": "v9",
                "official_intent_id": "intent-1", "official_session_id": "session-1",
            }), encoding="utf-8")
            result = state.project(root, "run")
        self.assertFalse(result["valid"])
        self.assertIn("official-identity-conflict", {row["code"] for row in result["issues"]})

    def test_evidence_receipt_must_belong_to_run_and_approved_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, _ = self.setup_run(root)
            receipts = directory / "validation-receipts"
            receipts.mkdir()
            (receipts / "unit.json").write_text(json.dumps({
                "schema_version": "1", "run_id": "other", "requirement_uid": "req-not-approved",
                "tier": "unit", "outcome": "pass",
            }), encoding="utf-8")
            result = state.project(root, "run")
        self.assertFalse(result["valid"])
        self.assertTrue({"run-id-conflict", "unknown-evidence-requirement"}.issubset({row["code"] for row in result["issues"]}))

    def test_cli_validate_returns_nonzero_for_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, uid = self.setup_run(root)
            self.checkpoint(directory, uid, "sha256:wrong")
            result = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "aidlc", "official", "state", "validate", "--root", root.as_posix(), "--run-id", "run"], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "conflict")


if __name__ == "__main__":
    unittest.main()
