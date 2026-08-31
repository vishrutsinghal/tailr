#!/usr/bin/env python3
"""Draft, approve, or reject a Debug Harness reproduction contract.

Nothing in the investigation touches source until a contract here is
approved (DEBUG-HARNESS.md Section 6, Phase 2). Domain is restricted to the
four domains this Debug Harness build actually supports."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_DOMAINS = {"code", "architecture", "database", "api-integration"}
DOMAIN_CEILINGS = {
    "code": "behavior-restored",
    "architecture": "behavior-restored",
    "database": "regression-validated",
    "api-integration": "regression-validated",
}


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = load("debug_reproduction_ledger", "run-ledger.py")
ANCHOR = load("debug_reproduction_anchor", "change-intent-anchor.py")
PLANNING = load("debug_reproduction_planning", "planning-lock.py")


def contract_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "reproduction" / "reproduction-contract-v1.json"


def approved_contract_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "reproduction" / "approved-v1.json"


def revision_path(root: Path, run_id: str, revision: int) -> Path:
    return L.state_dir(root, run_id) / "debug" / "reproduction" / f"draft-v{revision}.json"


def stable_requirement_uid(run_id: str, trigger: str) -> str:
    return "req-" + hashlib.sha256(f"{run_id}:debug-investigation:{trigger.strip()}".encode()).hexdigest()[:12]


def read_existing(root: Path, run_id: str) -> dict[str, Any] | None:
    path = contract_path(root, run_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def draft(root: Path, run_id: str, source: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    if approved_contract_path(root, run_id).is_file():
        raise ValueError("approved reproduction contract is immutable; open a correction/replan revision instead")
    domain = source.get("domain")
    if domain not in SUPPORTED_DOMAINS:
        raise ValueError(f"domain `{domain}` is not supported by this Debug Harness build; supported domains: {sorted(SUPPORTED_DOMAINS)}")
    required = ("trigger", "expected", "actual", "reproduction_method", "safety_boundary")
    missing = [field for field in required if not str(source.get(field, "")).strip()]
    if missing:
        raise ValueError(f"reproduction contract is missing: {', '.join(missing)}")
    existing = read_existing(root, run_id)
    revision = (existing["revision"] + 1) if existing else 1
    unresolved_fields = [str(item) for item in source.get("unresolved_fields", []) if str(item).strip()]
    requirement_uid = str(source.get("requirement_uid", "")).strip() or stable_requirement_uid(run_id, str(source["trigger"]))
    contract = {
        "schema_version": "1",
        "type": "tailtrail-reproduction-contract",
        "run_id": run_id,
        "domain": domain,
        "max_achievable_confidence_state": DOMAIN_CEILINGS[domain],
        "status": "awaiting-approval",
        "requirement_uid": requirement_uid,
        "trigger": str(source["trigger"]),
        "expected": str(source["expected"]),
        "actual": str(source["actual"]),
        "reproduction_method": str(source["reproduction_method"]),
        "preserve_rules": [str(item) for item in source.get("preserve_rules", [])],
        "safety_boundary": str(source["safety_boundary"]),
        "validation_contract": source.get("validation_contract", {"state": "required", "tiers": ["reproduction", "root-cause", "regression", "behaviour"]}),
        "unresolved_fields": unresolved_fields,
        "field_feedback": source.get("field_feedback", {}),
        "reject_reason": None,
        "revision": revision,
        "approved_at": None,
    }
    L.atomic_json(revision_path(root, run_id, revision), contract)
    L.atomic_json(contract_path(root, run_id), contract)
    L.append_event(root, run_id, "debug_reproduction_drafted", {"revision": revision, "domain": domain})
    return contract


def revise(root: Path, run_id: str, expected_revision: int, source: dict[str, Any]) -> dict[str, Any]:
    """Replace one unapproved reproduction draft with an explicitly based revision."""
    root = root.resolve()
    existing = read_existing(root, run_id)
    if existing is None:
        raise ValueError("no reproduction contract has been drafted for this run")
    if existing.get("status") == "approved" or approved_contract_path(root, run_id).is_file():
        raise ValueError("approved reproduction contract is immutable; use correction/replan")
    if existing.get("revision") != expected_revision:
        raise ValueError(
            f"reproduction revision mismatch: requested {expected_revision}, current revision is {existing.get('revision')}"
        )
    revised = draft(root, run_id, source)
    L.append_event(root, run_id, "debug_reproduction_revised", {
        "from_revision": expected_revision, "to_revision": revised["revision"]
    })
    return revised


def approve_start_plan_and_draft(root: Path, run_id: str) -> dict[str, Any]:
    """Approve DI-2 planning and create a saved-only reproduction proposal."""
    root = root.resolve()
    saved = PLANNING.active_start_report(root, run_id).get("report", {})
    debug_plan = saved.get("debug_plan") if isinstance(saved, dict) else None
    if not isinstance(debug_plan, dict):
        raise ValueError("active Start report is not a canonical Debug Start Plan")
    lock = PLANNING.approve_debug_plan(root, run_id)
    existing = read_existing(root, run_id)
    if existing is None:
        trigger = str(debug_plan.get("known_symptom") or saved.get("goal") or "reported failure").strip()
        matrix = (saved.get("navigator", {}) or {}).get("requirement_matrix", [])
        first_requirement = matrix[0] if matrix and isinstance(matrix[0], dict) else {}
        contract = draft(root, run_id, {
            "domain": "code",
            "trigger": trigger,
            "expected": "Unresolved: define the observable restored behaviour before reproduction approval.",
            "actual": trigger,
            "reproduction_method": "Unresolved: provide the smallest deterministic command or bounded intermittent procedure.",
            "preserve_rules": list(first_requirement.get("preserve_rules", [])),
            "safety_boundary": "Investigation must remain local and bounded; do not call production systems or edit source before correction approval.",
            "validation_contract": {"state": "required", "tiers": list(debug_plan.get("evidence_tiers", ["reproduction", "root-cause", "regression", "behaviour"]))},
            "unresolved_fields": ["expected", "reproduction_method"],
        })
    else:
        contract = existing
    return {
        "run_id": run_id,
        "state": "reproduction-approval-required",
        "planning_lock": lock,
        "reproduction_contract": contract,
        "next": "Resolve every unresolved field, review the exact revision, then approve that reproduction revision separately.",
        "boundary": "Debug planning is approved, but investigation commands, source reads, source writes, and correction remain unauthorized.",
    }


def ensure_investigation_prerequisites(root: Path, run_id: str, contract: dict[str, Any]) -> None:
    """Approve the run's Planning Lock and draft+approve a minimal investigation
    requirement via the existing anchor mechanism, reusing planning-lock.py and
    change-intent-anchor.py rather than parallel evidence machinery.
    execution-evidence.py requires both an approved, writes-allowed Planning
    Lock and an approved anchor before any evidence can be recorded, so both
    must exist before hypothesis testing can attach real evidence."""
    approved_anchor = L.state_dir(root, run_id) / "anchors" / "approved-v1.json"
    if approved_anchor.is_file():
        validate_anchor_compatibility(root, run_id, contract)
        return
    source = {
        "goal": f"Investigate: {contract['trigger']}",
        "requirements": [{
            "requirement_uid": contract["requirement_uid"],
            "display_id": "REQ-DEBUG-01",
            "kind": "debug-investigation",
            "statement": f"Investigate and prove the root cause of: {contract['trigger']}",
            "acceptance_criteria": [
                "The approved reproduction is observed with saved evidence.",
                "Root cause is proven with supporting evidence and at least one eliminated competing hypothesis.",
                "No source correction occurs under investigation-only authority.",
            ],
            "preserve_rules": contract.get("preserve_rules", []),
            "likely_paths": [],
            "evidence_plan": ["hypothesis-ledger", "execution-evidence"],
            "validation_contract": contract["validation_contract"],
        }],
    }
    source_path = L.state_dir(root, run_id) / "debug" / "reproduction" / "investigation-anchor-source.json"
    L.atomic_json(source_path, source)
    ANCHOR.draft(root, run_id, source_path)
    ANCHOR.approve(root, run_id)


def validate_anchor_compatibility(root: Path, run_id: str, contract: dict[str, Any]) -> None:
    approved_anchor = L.state_dir(root, run_id) / "anchors" / "approved-v1.json"
    if not approved_anchor.is_file():
        return
    anchor = json.loads(approved_anchor.read_text(encoding="utf-8"))
    anchored_uids = {row.get("requirement_uid") for row in anchor.get("requirements", [])}
    if anchored_uids != {contract["requirement_uid"]}:
        raise ValueError("existing approved anchor does not match this reproduction requirement UID")


def create_investigation_handoff(root: Path, run_id: str, contract: dict[str, Any]) -> dict[str, Any]:
    runtime = PLANNING.workflow_start_integration().activate_debug(
        root, run_id, approved_contract_path(root, run_id).relative_to(root).as_posix()
    )
    payload = {
        "schema_version": "1",
        "type": "tailtrail-debug-investigation-handoff",
        "run_id": run_id,
        "state": "investigation-ready",
        "requirement_uid": contract["requirement_uid"],
        "reproduction_revision": contract["revision"],
        "reproduction_contract": approved_contract_path(root, run_id).relative_to(root).as_posix(),
        "approved_anchor": (L.state_dir(root, run_id) / "anchors" / "approved-v1.json").relative_to(root).as_posix(),
        "workflow_runtime": runtime,
        "allowed_actions": ["read approved scope", "run approved reproduction", "record exact evidence", "manage hypotheses"],
        "forbidden_actions": ["edit project source", "apply correction", "commit", "push", "deploy", "call production systems"],
        "next": "Run only the approved reproduction and record factual evidence against the investigation requirement UID.",
        "boundary": "Reproduction approval grants investigation authority only. A proven root cause and separate correction approval are required before source changes.",
    }
    path = L.state_dir(root, run_id) / "debug" / "investigation-handoff-v1.json"
    L.atomic_json(path, payload)
    L.append_event(root, run_id, "debug_investigation_handoff_created", {"artifact": path.relative_to(root).as_posix(), "requirement_uid": contract["requirement_uid"], "reproduction_revision": contract["revision"]})
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def approve(root: Path, run_id: str, expected_revision: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    contract = read_existing(root, run_id)
    if contract is None:
        raise ValueError("no reproduction contract has been drafted for this run")
    if expected_revision is not None and contract.get("revision") != expected_revision:
        raise ValueError(f"reproduction revision mismatch: requested {expected_revision}, current revision is {contract.get('revision')}")
    if contract["status"] == "approved":
        raise ValueError("reproduction contract is already approved")
    if contract.get("unresolved_fields"):
        raise ValueError("reproduction contract cannot be approved while fields are unresolved: " + ", ".join(contract["unresolved_fields"]))
    lock_before = PLANNING.show(root, run_id)
    if lock_before.get("status") == "awaiting-approval":
        # Compatibility for the explicit prototype `tailtrail debug` intake.
        # Canonical Debug Start reaches this state through separate plan activation.
        PLANNING.approve_debug_plan(root, run_id)
    validate_anchor_compatibility(root, run_id, contract)
    contract["status"] = "approved"
    contract["approved_at"] = L.utc_now()
    contract["approved_fingerprint"] = "sha256:" + hashlib.sha256(json.dumps({key: value for key, value in contract.items() if key not in {"approved_at", "approved_fingerprint"}}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    L.atomic_json(contract_path(root, run_id), contract)
    L.atomic_json(approved_contract_path(root, run_id), contract)
    L.append_event(root, run_id, "debug_reproduction_approved", {"revision": contract["revision"], "domain": contract["domain"]})
    ensure_investigation_prerequisites(root, run_id, contract)
    lock = PLANNING.approve_debug_investigation(root, run_id, contract["revision"])
    handoff = create_investigation_handoff(root, run_id, contract)
    return {**contract, "planning_lock": lock, "execution_handoff": handoff}


def reject(root: Path, run_id: str, reason: str | None = None, feedback: dict[str, str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    feedback = feedback or ({"general": reason.strip()} if isinstance(reason, str) and reason.strip() else {})
    allowed_fields = {"domain", "trigger", "expected", "actual", "reproduction_method", "preserve_rules", "safety_boundary", "validation_contract", "general"}
    if not feedback or any(key not in allowed_fields or not str(value).strip() for key, value in feedback.items()):
        raise ValueError("reproduction rejection requires non-empty field-specific feedback")
    contract = read_existing(root, run_id)
    if contract is None:
        raise ValueError("no reproduction contract has been drafted for this run")
    contract["status"] = "rejected"
    contract["reject_reason"] = str(reason).strip() if reason else None
    contract["field_feedback"] = {str(key): str(value).strip() for key, value in feedback.items()}
    L.atomic_json(contract_path(root, run_id), contract)
    L.append_event(root, run_id, "debug_reproduction_rejected", {"revision": contract["revision"], "feedback_fields": sorted(feedback)})
    return contract


def show(root: Path, run_id: str) -> dict[str, Any]:
    contract = read_existing(root.resolve(), run_id)
    if contract is None:
        raise ValueError("no reproduction contract has been drafted for this run")
    return contract


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    draft_parser = sub.add_parser("draft")
    draft_parser.add_argument("--root", type=Path, default=Path.cwd())
    draft_parser.add_argument("--run-id", required=True)
    draft_parser.add_argument("--input", type=Path, required=True, help="JSON file with domain/trigger/expected/actual/reproduction_method/preserve_rules/safety_boundary")
    revise_parser = sub.add_parser("revise")
    revise_parser.add_argument("--root", type=Path, default=Path.cwd())
    revise_parser.add_argument("--run-id", required=True)
    revise_parser.add_argument("--revision", type=int, required=True)
    revise_parser.add_argument("--input", type=Path, required=True)
    revise_parser.add_argument("--approved", action="store_true")
    approve_parser = sub.add_parser("approve")
    approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    approve_parser.add_argument("--run-id", required=True)
    approve_parser.add_argument("--approved", action="store_true")
    approve_parser.add_argument("--revision", type=int, required=True)
    reject_parser = sub.add_parser("reject")
    reject_parser.add_argument("--root", type=Path, default=Path.cwd())
    reject_parser.add_argument("--run-id", required=True)
    reject_source = reject_parser.add_mutually_exclusive_group(required=True)
    reject_source.add_argument("--reason")
    reject_source.add_argument("--feedback", help="JSON object mapping reproduction fields to concrete feedback")
    show_parser = sub.add_parser("show")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if args.action == "draft":
            source = json.loads(args.input.read_text(encoding="utf-8"))
            result = draft(args.root, args.run_id, source)
        elif args.action == "revise":
            if not args.approved: raise ValueError("revising a reproduction contract requires --approved")
            source = json.loads(args.input.read_text(encoding="utf-8"))
            result = revise(args.root, args.run_id, args.revision, source)
        elif args.action == "approve":
            if not args.approved:
                raise ValueError("approving a reproduction contract requires --approved")
            result = approve(args.root, args.run_id, args.revision)
        elif args.action == "reject":
            feedback = json.loads(args.feedback) if args.feedback else None
            if feedback is not None and not isinstance(feedback, dict):
                raise ValueError("--feedback must be a JSON object")
            result = reject(args.root, args.run_id, args.reason, feedback)
        else:
            result = show(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Debug reproduction error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
