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


lock = load("planning_audit_lock_test", "scripts/planning_lock.py")
revision = load("planning_audit_revision_test", "scripts/planning-revision.py")
audit = load("planning_audit_test", "scripts/planning-audit.py")


def _plan(root: Path, run_id: str, requirements: list[dict[str, object]]) -> None:
    lock.create(root, "add cancellation", run_id)
    lock.save_start_report(root, run_id, {
        "goal": "add cancellation",
        "navigator": {
            "likely_impacted_files": [{"path": "src/service.py", "reason": "saved orchestration path"}],
            "requirement_matrix": requirements,
        },
    })


class PlanningAuditTests(unittest.TestCase):
    def test_clean_plan_reports_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-clean", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Cancel an eligible order.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest tests/test_service.py"]},
            }])
            result = audit.audit(root, "audit-clean")

        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["findings"], [])

    def test_named_test_path_missing_from_scope_is_flagged(self) -> None:
        """Issue 28 pattern: a proof-only path named in the requirement text
        is absent from likely_paths/validation_contract/scope_evidence."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-named-path", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Cancel an eligible order and cover it with tests/test_cancellation.py.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
            }])
            result = audit.audit(root, "audit-named-path")

        self.assertEqual(result["status"], "gaps-found")
        finding = next(f for f in result["findings"] if f["type"] == "named_path_missing_from_scope")
        self.assertEqual(finding["path"], "tests/test_cancellation.py")
        self.assertEqual(finding["role"], "test")
        self.assertIn("proof-update", finding["suggested_fix"])

    def test_named_implementation_path_missing_from_scope_suggests_scope_add(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-named-impl", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Update src/billing.py to cancel an eligible order.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
            }])
            result = audit.audit(root, "audit-named-impl")

        finding = next(f for f in result["findings"] if f["type"] == "named_path_missing_from_scope")
        self.assertEqual(finding["path"], "src/billing.py")
        self.assertEqual(finding["role"], "implementation-owner")
        self.assertIn("scope-add", finding["suggested_fix"])

    def test_suggested_fix_falls_back_to_display_id_when_requirement_uid_unminted(self) -> None:
        """A fresh Start Report has no `requirement_uid` yet (anchor-owned,
        minted at revision/activation time); the suggested fix must still
        reference a requirement `planning revise` can resolve."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-no-uid", [{
                "display_id": "REQ-01", "kind": "change",
                "statement": "Cancel an eligible order and cover it with tests/test_cancellation.py.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
            }])
            result = audit.audit(root, "audit-no-uid")

        finding = next(f for f in result["findings"] if f["type"] == "named_path_missing_from_scope")
        self.assertEqual(finding["requirement_uid"], "REQ-01")
        self.assertIn('"requirement_uid":"REQ-01"', finding["suggested_fix"])

    def test_tier_mismatch_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-tier", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Expose a new API contract endpoint for cancellation.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
            }])
            result = audit.audit(root, "audit-tier")

        finding = next(f for f in result["findings"] if f["type"] == "tier_mismatch")
        self.assertIn("contract", finding["missing_tiers"])

    def test_missing_proof_registration_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-no-proof", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Cancel an eligible order.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": ["unit"]},
            }])
            result = audit.audit(root, "audit-no-proof")

        self.assertTrue(any(f["type"] == "missing_proof_registration" for f in result["findings"]))

    def test_pending_revision_is_audited_and_can_reach_clean_before_approval(self) -> None:
        """The mandated host loop: audit v1, propose a correcting revision,
        then re-audit the still-pending (unapproved) proposal directly —
        the run must stay `awaiting-approval` throughout."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-pending-fix", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Cancel an eligible order and cover it with tests/test_cancellation.py.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
            }])
            before = audit.audit(root, "audit-pending-fix")
            change = json.dumps([{
                "kind": "proof-update", "requirement_uid": "REQ-01",
                "reason": "close requirement-named scope gap",
                "evidence_plan": ["Record proof for tests/test_cancellation.py"],
                "editable_paths": ["tests/test_cancellation.py"],
            }])
            revision.propose(root, "audit-pending-fix", change, True)
            after = audit.audit(root, "audit-pending-fix")
            status = lock.show(root, "audit-pending-fix")["status"]

        self.assertEqual(before["status"], "gaps-found")
        self.assertEqual(after["status"], "clean")
        self.assertEqual(status, "awaiting-approval")

    def test_audit_refuses_once_plan_is_no_longer_awaiting_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-approved", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Cancel an eligible order.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
            }])
            lock.activate(root, "audit-approved", True)
            with self.assertRaisesRegex(ValueError, "awaiting approval"):
                audit.audit(root, "audit-approved")


if __name__ == "__main__":
    unittest.main()
