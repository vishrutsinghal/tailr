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


def _converged_report(requirements: list[dict[str, object]]) -> dict[str, object]:
    """Build a converged Start report: checks[] + focused rows agree with contracts."""
    rows = json.loads(json.dumps(requirements))
    focused: list[dict[str, object]] = []
    for row in rows:
        assert isinstance(row, dict)
        contract = row.get("validation_contract", {})
        assert isinstance(contract, dict)
        tiers = [str(item) for item in (contract.get("tiers", []) or [])]
        commands = [str(item) for item in (contract.get("commands", []) or [])]
        paths = (
            [str(item) for item in (contract.get("candidate_paths", []) or [])]
            or [str(item) for item in (contract.get("editable_paths", []) or [])]
            or [str(item) for item in (contract.get("proposed_paths", []) or [])]
        )
        # Test fixtures with commands but no named proof path assume the
        # conventional unit proof; fixtures with neither keep no path so
        # missing-proof detection still fires.
        if not paths and commands:
            paths = ["tests/test_service.py"]
        if paths and "candidate_paths" not in contract:
            contract["candidate_paths"] = paths[:1]
        checks = []
        for index, tier in enumerate(tiers):
            if index >= len(commands):
                continue
            checks.append({
                "kind": "proof",
                "command": commands[index],
                "tiers": [tier],
                "candidate_paths": paths[:1],
            })
        if checks:
            contract["checks"] = checks
        for index, tier in enumerate(tiers):
            command = commands[index] if index < len(commands) else ""
            candidate = paths[0] if paths else "not resolved from planning evidence"
            focused.append({
                "tier": tier,
                "tiers": [tier],
                "candidate": candidate,
                "command": command,
                "status": "planned after approval" if command and paths else "required",
                "candidate_state": "existing" if command and paths else "unresolved",
            })
    # Coalesce rows sharing one executable proof like task-start does.
    grouped: list[dict[str, object]] = []
    by_proof: dict[tuple[str, str], dict[str, object]] = {}
    for source in focused:
        assert isinstance(source, dict)
        key = (str(source.get("candidate", "")), str(source.get("command", "")))
        existing = by_proof.get(key) if key[0] and key[1] else None
        if existing is None:
            grouped.append(source)
            if key[0] and key[1]:
                by_proof[key] = source
            continue
        assert isinstance(existing.get("tiers"), list)
        existing_tiers = existing["tiers"]
        assert isinstance(existing_tiers, list)
        existing_tiers.append(source.get("tier"))
        existing["tier"] = " + ".join(str(item) for item in existing_tiers)
    report: dict[str, object] = {
        "goal": "add cancellation",
        "navigator": {
            "likely_impacted_files": [{"path": "src/service.py", "reason": "saved orchestration path"}],
            "requirement_matrix": rows,
        },
        "focused_validation": grouped,
    }
    projection = lock.effective_plan_projection(report)  # type: ignore[attr-defined]
    report["effective_plan_fingerprint"] = projection.get("fingerprint")
    return report


def _plan(root: Path, run_id: str, requirements: list[dict[str, object]]) -> None:
    lock.create(root, "add cancellation", run_id)
    lock.save_start_report(root, run_id, _converged_report(requirements))


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

    def test_stale_projection_is_flagged(self) -> None:
        """Gap 2: a proof-update that adds a tier/command without rebuilding
        checks[] and focused_validation must audit as gaps-found."""
        report = _converged_report([{
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "statement": "Add a login endpoint.",
            "acceptance_criteria": ["login succeeds"],
            "likely_paths": ["src/auth.py"],
            "validation_contract": {
                "state": "required", "tiers": ["unit"], "commands": ["pytest tests/test_auth.py"],
                "candidate_paths": ["tests/test_auth.py"],
            },
        }])
        # Simulate a manual contract edit that adds a behaviour tier and
        # command but leaves checks[] and focused_validation stale.
        matrix = report["navigator"]["requirement_matrix"]
        assert isinstance(matrix, list)
        row = matrix[0]
        assert isinstance(row, dict)
        contract = row["validation_contract"]
        assert isinstance(contract, dict)
        contract["tiers"] = ["unit", "behaviour"]
        contract["commands"] = ["pytest tests/test_auth.py", "behave tests/test_auth.py"]
        result = audit.audit_report(Path("."), "stale-projection", report)

        self.assertEqual(result["status"], "gaps-found")
        self.assertTrue(any("mismatch" in f["type"] or "stale" in f["type"] for f in result["findings"]))

    def test_tier_without_command_stays_unresolved(self) -> None:
        """Gap 2: adding a tier label without a positional command blocks approval."""
        report = _converged_report([{
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "statement": "Add a login endpoint.",
            "acceptance_criteria": ["login succeeds"],
            "likely_paths": ["src/auth.py"],
            "validation_contract": {
                "state": "required", "tiers": ["unit", "behaviour"], "commands": ["pytest tests/test_auth.py"],
                "candidate_paths": ["tests/test_auth.py"],
            },
        }])
        result = audit.audit_report(Path("."), "tier-without-command", report)

        self.assertEqual(result["status"], "gaps-found")
        self.assertTrue(any(f["type"] == "unresolved-tier-proof" for f in result["findings"]))

    def test_proof_update_rebuilds_checks_and_focused(self) -> None:
        """Gap 2: a validated proof-update regenerates checks[], focused rows, and fingerprint atomically."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "rebuild-projection", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Cancel an eligible order.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {
                    "state": "required", "tiers": ["unit"], "commands": ["pytest tests/test_service.py"],
                    "candidate_paths": ["tests/test_service.py"],
                },
            }])
            change = json.dumps([{
                "kind": "proof-update", "requirement_uid": "REQ-01",
                "reason": "attach integration proof",
                "evidence_plan": ["Run unit and integration proof."],
                "commands": ["pytest tests/test_service.py -k integration"],
                "tiers": ["integration"],
            }])
            revision.propose(root, "rebuild-projection", change, True)
            result = audit.audit(root, "rebuild-projection")
            proposed = revision.show(root, "rebuild-projection")
            revised = proposed.get("proposed_report", {})

        contract = revised["navigator"]["requirement_matrix"][0]["validation_contract"]
        self.assertEqual(contract["tiers"], ["unit", "integration"])
        self.assertEqual(len(contract["commands"]), 2)
        self.assertEqual(len(contract["checks"]), 2)
        tiers_in_checks = sorted(tier for check in contract["checks"] for tier in check.get("tiers", []))
        self.assertEqual(tiers_in_checks, ["integration", "unit"])
        focused_tiers = sorted(
            tier
            for item in revised.get("focused_validation", [])
            for tier in (item.get("tiers", [item.get("tier")]) or [])
        )
        self.assertIn("unit", focused_tiers)
        self.assertIn("integration", focused_tiers)
        self.assertIn("effective_plan_fingerprint", revised)
        # Both new tiers have positional commands, so only the
        # requirement-named-scope style findings (none here) may remain;
        # convergence itself must not flag.
        convergence = [f for f in result["findings"] if f["type"] in {
            "check-projection-mismatch", "focused-validation-stale",
            "unresolved-tier-proof", "fingerprint-mismatch",
        }]
        self.assertEqual(convergence, [])


if __name__ == "__main__":
    unittest.main()
