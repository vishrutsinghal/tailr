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
task_start = load("planning_audit_task_start_test", "scripts/task-start.py")


def _revise_parser():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--run-id", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--changes")
    source.add_argument("--changes-base64")
    parser.add_argument("--approved-proposal", action="store_true")
    parser.add_argument("--supersede-pending", action="store_true")
    return parser


def _parse_correction(command: str) -> dict:
    import shlex

    tokens = shlex.split(command, posix=True)
    assert tokens[:3] == ["tailtrail", "planning", "revise"], tokens[:3]
    return vars(_revise_parser().parse_args(tokens[3:]))


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
                "requirement_id": str(row.get("display_id") or row.get("requirement_uid") or "REQ-01"),
                "tier": tier,
                "tiers": [tier],
                "candidate": candidate,
                "command": command,
                "status": "planned after approval" if command and paths else "required",
                "candidate_state": "existing" if command and paths else "unresolved",
            })
    # Coalesce rows sharing one executable proof like task-start does.
    grouped: list[dict[str, object]] = []
    by_proof: dict[tuple[str, str, str], dict[str, object]] = {}
    for source in focused:
        assert isinstance(source, dict)
        key = (
            str(source.get("requirement_id", "")),
            str(source.get("candidate", "")),
            str(source.get("command", "")),
        )
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
            "scope_evidence": {"state": "resolved"},
        },
        "focused_validation": grouped,
    }
    projection = lock.effective_plan_projection(report)  # type: ignore[attr-defined]
    registry = projection.get("command_registry", {})
    checks_by_requirement = projection.get("checks_by_requirement", {})
    for row in rows:
        assert isinstance(row, dict)
        requirement_id = str(row.get("display_id") or row.get("requirement_uid") or "")
        contract = row.get("validation_contract", {})
        assert isinstance(contract, dict)
        contract["checks"] = checks_by_requirement.get(requirement_id, [])
        contract["command_registry"] = registry
    rebuilt_focused: list[dict[str, object]] = []
    for item in projection.get("focused_validation", []):
        requirement_id = str(item.get("requirement_id", ""))
        row = next((value for value in rows if str(value.get("display_id") or value.get("requirement_uid")) == requirement_id), {})
        contract = row.get("validation_contract", {}) if isinstance(row, dict) else {}
        paths = contract.get("candidate_paths", []) if isinstance(contract, dict) else []
        rebuilt_focused.append({
            **item,
            "candidate": paths[0] if paths else "not resolved from planning evidence",
            "candidate_state": "existing" if paths else "unresolved",
            "status": "planned after approval" if paths and item.get("command_id") else "required",
        })
    report["focused_validation"] = rebuilt_focused
    report["effective_plan_fingerprint"] = projection.get("fingerprint")
    return report


def _plan(root: Path, run_id: str, requirements: list[dict[str, object]]) -> None:
    lock.create(root, "add cancellation", run_id)
    lock.save_start_report(root, run_id, _converged_report(requirements))


class PlanningAuditTests(unittest.TestCase):
    def test_already_satisfied_behavior_blocks_implementation_plan(self) -> None:
        report = _converged_report([{
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "statement": "Wire the orchestrator.",
            "acceptance_criteria": ["records through intake"],
            "likely_paths": ["scripts/question-orchestrator.py"],
            "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
        }])
        report["navigator"]["behavior_check"] = {"state": "already-satisfied", "owner_paths": ["scripts/question-orchestrator.py"], "proof_paths": ["tests/test_question_orchestrator.py"]}
        result = audit.audit_report(Path("."), "already-satisfied", report)

        finding = next(item for item in result["findings"] if item["type"] == "already-satisfied-implementation-plan")
        self.assertEqual(finding["correction_kind"], "restart-required")

    def test_unrecorded_behavior_preflight_does_not_claim_satisfaction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            owner = root / "scripts" / "owner.py"
            proof = root / "tests" / "test_owner.py"
            owner.parent.mkdir(parents=True); proof.parent.mkdir(parents=True)
            owner.write_text("def owner():\n    return True\n", encoding="utf-8")
            proof.write_text("def test_owner():\n    pass\n", encoding="utf-8")
            result = task_start.behavior_preflight(
                root,
                "Wire scripts/owner.py using scripts/dependency.py.",
                ["scripts/owner.py"],
                ["tests/test_owner.py"],
            )

        self.assertEqual(result["state"], "missing")

    def test_host_proof_boundary_rejects_inferred_higher_tiers(self) -> None:
        requirements = [{
            "display_id": "REQ-01",
            "validation_contract": {"tiers": ["unit", "behaviour", "integration"]},
        }]
        conflict = task_start.enforce_host_proof_boundary(
            requirements,
            {"behavior_surface": "internal", "allowed_tiers": ["unit"]},
        )

        self.assertEqual(conflict["state"], "inferred-tier-conflicts-host-proof-boundary")
        self.assertEqual(conflict["conflicts"][0]["inferred_tiers"], ["behaviour", "integration"])
        self.assertEqual(requirements[0]["validation_contract"]["tiers"], ["unit"])

    def test_internal_host_proof_boundary_caps_inferred_tiers(self) -> None:
        report = _converged_report([{
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "statement": "Bind positive and negative criteria for a workflow.",
            "acceptance_criteria": ["internal packet remains valid"],
            "likely_paths": ["scripts/intake_pipeline.py"],
            "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
        }])
        report["navigator"]["host_proof_boundary"] = {"behavior_surface": "internal", "allowed_tiers": ["unit"]}
        report["navigator"]["host_proof_boundary_conflict"] = {
            "state": "inferred-tier-conflicts-host-proof-boundary",
            "behavior_surface": "internal",
            "allowed_tiers": ["unit"],
            "conflicts": [{"requirement_id": "REQ-01", "inferred_tiers": ["behaviour"]}],
        }

        result = audit.audit_report(Path("."), "internal-tier-cap", report)

        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["findings"], [])

    def test_public_cli_contract_boundary_keeps_tier_enforcement(self) -> None:
        report = _converged_report([{
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "statement": "Expose a public API contract endpoint for cancellation.",
            "acceptance_criteria": ["eligible cancellation succeeds"],
            "likely_paths": ["src/service.py"],
            "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
        }])
        report["navigator"]["host_proof_boundary"] = {"behavior_surface": "cli-contract", "allowed_tiers": ["unit"]}
        report["navigator"]["host_proof_boundary_conflict"] = {
            "state": "inferred-tier-conflicts-host-proof-boundary",
            "behavior_surface": "cli-contract",
            "allowed_tiers": ["unit"],
            "conflicts": [{"requirement_id": "REQ-01", "inferred_tiers": ["contract"]}],
        }

        result = audit.audit_report(Path("."), "public-tier-boundary", report)

        self.assertTrue(any(item["type"] == "inferred-tier-conflicts-host-proof-boundary" for item in result["findings"]))
        self.assertTrue(any(item["type"] == "tier_mismatch" for item in result["findings"]))

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

    def test_inspection_only_named_dependency_is_known_but_not_editable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-inspection-dependency", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Wire scripts/question-orchestrator.py using scripts/intake_pipeline.py.",
                "acceptance_criteria": ["the orchestrator records through the intake dependency"],
                "likely_paths": ["scripts/question-orchestrator.py"],
                "validation_contract": {
                    "state": "required", "tiers": ["unit"],
                    "commands": ["python3 -m unittest discover -s tests -p test_question_orchestrator.py -v"],
                },
            }])
            report = lock.active_start_report(root, "audit-inspection-dependency")["report"]
            report["navigator"]["scope_evidence"] = {
                "implementation_owners": ["scripts/question-orchestrator.py"],
                "inspection_paths": ["scripts/intake_pipeline.py"],
                "proof_paths": ["tests/test_question_orchestrator.py"],
            }
            lock.start_report_path(root, "audit-inspection-dependency").write_text(json.dumps({
                "schema_version": "1",
                "type": "tailtrail-start-report",
                "run_id": "audit-inspection-dependency",
                "goal": report["goal"],
                "report": report,
            }), encoding="utf-8")
            result = audit.audit(root, "audit-inspection-dependency")

        findings = [item for item in result["findings"] if item.get("path") == "scripts/intake_pipeline.py"]
        self.assertEqual(findings, [])

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

    def test_requirement_scope_rejects_another_requirements_proof_command(self) -> None:
        report = _converged_report([{
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "statement": "Record a host observation.",
            "acceptance_criteria": ["the observation is recorded"],
            "likely_paths": ["scripts/intake_pipeline.py"],
            "scope_evidence": {"proof_paths": ["tests/test_intake_pipeline.py"]},
            "validation_contract": {
                "state": "required", "tiers": ["unit"],
                "commands": ["python3 -m unittest tests.test_host_question_flow_event_schema"],
                "candidate_paths": ["tests/test_host_question_flow_event_schema.py"],
            },
        }])

        result = audit.audit_report(Path("."), "cross-requirement-proof", report)
        finding_types = {finding["type"] for finding in result["findings"]}

        self.assertIn("proof-path-outside-requirement-scope", finding_types)

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

    def test_aidlc_mode_switch_audit_does_not_require_rejected_implementation_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-aidlc-mode-switch", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Expose a workflow behavior requiring behaviour proof.",
                "acceptance_criteria": ["workflow is visible"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": []},
            }])
            revision.propose_aidlc_standard(root, "audit-aidlc-mode-switch", True)
            result = audit.audit(root, "audit-aidlc-mode-switch")

        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["findings"], [])
        self.assertEqual(
            result["approval_assessment"]["approval_decision"],
            "READY FOR AIDLC MODE-SWITCH APPROVAL",
        )

    def test_audit_projects_validated_aidlc_revision_over_stale_active_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-aidlc-revision", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Render the report.",
                "acceptance_criteria": ["report is visible"],
                "likely_paths": ["src/report.py"],
                "validation_contract": {"state": "required", "tiers": []},
            }])
            run = root / ".tailtrail" / "runs" / "audit-aidlc-revision"
            revision_path = run / "planning" / "aidlc-revised-requirements-v1.json"
            revised_row = {
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Render the report.",
                "acceptance_criteria": ["report is visible"],
                "likely_paths": ["src/report.py"],
                "scope_evidence": {
                    "implementation_owners": ["src/report.py"],
                    "inspection_paths": [],
                    "proof_paths": ["tests/test_report.py"],
                },
                "validation_contract": {
                    "state": "required", "tiers": ["unit", "behaviour"],
                    "commands": ["python3 -m unittest tests.test_report -v"],
                    "candidate_paths": ["tests/test_report.py"],
                    "checks": [{
                        "kind": "proof",
                        "command": "python3 -m unittest tests.test_report -v",
                        "tiers": ["unit", "behaviour"],
                        "candidate_paths": ["tests/test_report.py"],
                    }],
                },
                "behavior_contract": {"scenarios": [{
                    "scenario_id": "BHV-REQ-01",
                    "action": "Generate the report.",
                    "expected_outcome": "The report is visible.",
                }]},
            }
            revision_path.write_text(json.dumps({
                "requirements": [revised_row],
                "aidlc_answers": {"Q3": {"choice": "B", "detail": "focused proof"}},
            }), encoding="utf-8")
            (run / "planning" / "aidlc-correction-state.json").write_text(json.dumps({
                "state": "revision-ready",
                "active_revision": revision_path.relative_to(root).as_posix(),
            }), encoding="utf-8")

            result = audit.audit(root, "audit-aidlc-revision")

        stale_types = {
            "missing-requirement-proof-binding",
            "unresolved-tier-proof",
            "tier_mismatch",
            "behaviour-scenario-generic",
        }
        self.assertFalse(stale_types.intersection(item["type"] for item in result["findings"]))

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

    def test_multiple_required_commands_same_tier_are_preserved(self) -> None:
        report = _converged_report([{
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "statement": "Wire the orchestrator.",
            "acceptance_criteria": ["records through intake"],
            "likely_paths": ["scripts/question-orchestrator.py"],
            "validation_contract": {
                "state": "required", "tiers": ["unit"],
                "commands": ["python3 -m unittest tests.test_question_orchestrator", "python3 -m unittest tests.test_phase1a"],
            },
        }])
        projection = lock.effective_plan_projection(report)
        checks = projection["checks_by_requirement"]["REQ-01"]
        registry = projection["command_registry"]

        self.assertEqual([registry[check["command_id"]]["command"] for check in checks], [
            "python3 -m unittest tests.test_question_orchestrator",
            "python3 -m unittest tests.test_phase1a",
        ])
        self.assertEqual(len(projection["focused_validation"]), 2)

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

    def test_registry_backed_revision_proof_passes_public_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "registry-proof-audit", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Cancel an eligible order.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": ["unit"]},
            }])
            revision.propose(root, "registry-proof-audit", json.dumps([{
                "kind": "proof-update", "requirement_uid": "REQ-01",
                "reason": "Bind requirement-scoped proof.",
                "evidence_plan": ["Run the planning audit regression."],
                "commands": ["python3 -m unittest tests.test_planning_audit -v"],
                "tiers": ["unit"],
                "editable_paths": ["tests/test_planning_audit.py"],
            }]), True)
            result = audit.audit(root, "registry-proof-audit")

        proof_findings = [item for item in result["findings"] if item["type"] in {
            "missing-requirement-proof-binding",
            "incomplete-requirement-proof-binding",
            "focused-validation-stale",
        }]
        self.assertEqual(proof_findings, [])


class CorrectionExecutabilityTests(unittest.TestCase):
    def test_executable_suggestions_parse_with_authority_marker(self) -> None:
        report = _converged_report([{
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "statement": "Cancel an eligible order and cover it with tests/test_cancellation.py.",
            "acceptance_criteria": ["eligible cancellation succeeds"],
            "likely_paths": ["src/service.py"],
            "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
        }])
        result = audit.audit_report(Path("."), "audit-exec", report)
        executable = [f for f in result["findings"] if f.get("correction_kind") == "executable"]
        self.assertTrue(executable)
        for finding in executable:
            parsed = _parse_correction(finding["suggested_fix"])
            self.assertTrue(parsed["approved_proposal"])
            self.assertFalse(parsed["supersede_pending"])
            changes = json.loads(parsed["changes"])
            self.assertEqual(changes, finding["correction"]["changes"])
            portable = _parse_correction(finding["suggested_fix_portable"])
            import base64

            self.assertEqual(
                json.loads(base64.b64decode(portable["changes_base64"]).decode("utf-8")),
                changes,
            )

    def test_executable_correction_applies_clean_through_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "audit-exec-apply", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Cancel an eligible order and cover it with tests/test_cancellation.py.",
                "acceptance_criteria": ["eligible cancellation succeeds"],
                "likely_paths": ["src/service.py"],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
            }])
            before = audit.audit(root, "audit-exec-apply")
            fixable = next(f for f in before["findings"] if f.get("correction_kind") == "executable")
            correction = fixable["correction"]
            revision.propose(root, "audit-exec-apply", json.dumps(correction["changes"]), True)
            after = audit.audit(root, "audit-exec-apply")

        self.assertEqual(before["status"], "gaps-found")
        self.assertNotIn(fixable["type"], {f["type"] for f in after["findings"]})

    def test_templates_name_open_fields_and_restart_needs_no_command(self) -> None:
        report = _converged_report([{
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "statement": "Cancel an eligible order.",
            "acceptance_criteria": ["eligible cancellation succeeds"],
            "likely_paths": ["src/service.py"],
            "validation_contract": {"state": "required", "tiers": ["unit"]},
        }])
        result = audit.audit_report(Path("."), "audit-template", report)
        template = next(f for f in result["findings"] if f.get("correction_kind") == "template")
        self.assertTrue(template.get("open_fields"))
        self.assertNotIn("correction", template)

    def test_missing_scope_evidence_blocks_scope_add(self) -> None:
        report = {
            "goal": "Update src/billing.py to cancel an eligible order.",
            "navigator": {
                "requirement_matrix": [{
                    "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                    "statement": "Update src/billing.py to cancel an eligible order.",
                    "acceptance_criteria": ["eligible cancellation succeeds"],
                    "likely_paths": ["src/service.py"],
                    "validation_contract": {"state": "required", "tiers": ["unit"], "commands": ["pytest"]},
                }],
            },
            "focused_validation": [],
        }
        result = audit.audit_report(Path("."), "audit-no-scope", report)
        blocking = next(f for f in result["findings"] if f["type"] == "missing-canonical-scope-evidence")
        self.assertEqual(blocking["correction_kind"], "restart-required")
        self.assertNotIn("suggested_fix", blocking)
        self.assertFalse(any(
            f.get("type") == "named_path_missing_from_scope" and "scope-add" in str(f.get("suggested_fix", ""))
            for f in result["findings"]
        ))


if __name__ == "__main__":
    unittest.main()
