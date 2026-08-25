from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_workflow_security import ROOT, setup_workflow
from workflow_runtime import approvals, assurance, compiler, contracts, denials, ownership, storage

if ROOT.as_posix() in sys.path:
    sys.path.remove(ROOT.as_posix())
sys.path.insert(0, ROOT.as_posix())
loaded_tailtrail = sys.modules.get("tailtrail")
if loaded_tailtrail is not None and not hasattr(loaded_tailtrail, "__path__"):
    del sys.modules["tailtrail"]
from tailtrail.install import InstallEngine, InstallFailure


class StrideThreatModelFixtureTests(unittest.TestCase):
    """Phase E7 (ENT-E7-002): one consolidated executable STRIDE fixture pack.

    Each test proves the mitigation named for its row in
    `aidlc-docs/phase10-threat-model.md`. Where a fixture already existed
    elsewhere in the suite it is cited in the threat-model doc rather than
    duplicated here; these are the cases that had no dedicated executable
    proof before Phase E7.
    """

    # Spoofing
    def test_spoofed_cross_workflow_approval_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _run, first = setup_workflow(root, "stride-spoof-first")
            forged = approvals.decide(
                root, first, stage_ids=["bootstrap"], action_classes=["read_local"],
                operation_kind="other-guarded", operation_ref=compiler.show(root, first)["artifact"],
                decision="approved", rationale="Only valid for the first workflow.",
            )["record"]
            _run, second = setup_workflow(root, "stride-spoof-second")
            with self.assertRaises(ValueError):
                approvals.authorize_stage(root, second, "bootstrap", forged["approval_id"])

    # Tampering
    def test_tampered_journal_hash_fails_closed_and_preserves_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _run, wid = setup_workflow(root, "stride-tamper")
            before = storage.status(root, wid)["last_valid_projection"]
            journal = storage.journal_path(root, wid)
            lines = journal.read_text(encoding="utf-8").splitlines()
            tampered = json.loads(lines[-1])
            tampered["event_hash"] = "sha256:" + "f" * 64
            lines[-1] = json.dumps(tampered)
            journal.write_text("\n".join(lines) + "\n")

            replay = storage.replay(root, wid)
            self.assertFalse(replay["valid"])
            self.assertEqual(storage.status(root, wid)["last_valid_projection"], before)

    # Repudiation
    def test_denial_audit_never_retains_the_hostile_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _run, wid = setup_workflow(root, "stride-repudiation")
            hostile = "Bearer " + "Z" * 40
            record = denials.record(root, wid, "release-gate", denials.categorize(f"privacy blocked: {hostile}"), "cli")
            encoded = json.dumps(record)
            self.assertNotIn(hostile, encoded)
            self.assertIn("reason_code", record["record"])
            self.assertTrue(record["record"]["reason_code"])  # human-readable, non-empty

    # Information disclosure
    def test_secret_shaped_value_is_never_persisted_in_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _run, wid = setup_workflow(root, "stride-disclosure")
            hostile = "AKIA" + "B" * 16
            path = ownership.binding_path(root, wid).parent / "leaked.json"
            path.write_text(json.dumps({"config": hostile}), encoding="utf-8")
            result = assurance.inspect(root, wid)
            encoded = json.dumps(result)
            self.assertEqual(result["status"], "blocked")
            self.assertNotIn(hostile, encoded)

    # Denial of service
    def test_oversized_and_traversal_shaped_artifacts_fail_closed(self) -> None:
        base = json.loads((ROOT / "tests" / "fixtures" / "workflow_runtime" / "aidlc-lite.json").read_text(encoding="utf-8"))
        oversized = {**base, "boundary": "x" * (contracts.MAX_ARTIFACT_BYTES + 1)}
        traversal = {**base, "planning_lock_ref": "../../etc/passwd"}
        self.assertTrue(contracts.validate_artifact(oversized))
        self.assertTrue(contracts.validate_artifact(traversal))

    # Elevation of privilege
    def test_symlink_escape_and_path_traversal_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            target = Path(temp)
            (target / ".codex-plugin").symlink_to(Path(outside), target_is_directory=True)
            with self.assertRaisesRegex(InstallFailure, "symlink"):
                InstallEngine(target).plan("install", "codex", "core")


if __name__ == "__main__":
    unittest.main()
