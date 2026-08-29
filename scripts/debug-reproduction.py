#!/usr/bin/env python3
"""Draft, approve, or reject a Debug Harness reproduction contract.

Nothing in the investigation touches source until a contract here is
approved (DEBUG-HARNESS.md Section 6, Phase 2). Domain is restricted to the
four domains this Debug Harness build actually supports."""
from __future__ import annotations

import argparse
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


def read_existing(root: Path, run_id: str) -> dict[str, Any] | None:
    path = contract_path(root, run_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def draft(root: Path, run_id: str, source: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    domain = source.get("domain")
    if domain not in SUPPORTED_DOMAINS:
        raise ValueError(f"domain `{domain}` is not supported by this Debug Harness build; supported domains: {sorted(SUPPORTED_DOMAINS)}")
    required = ("trigger", "expected", "actual", "reproduction_method", "safety_boundary")
    missing = [field for field in required if not str(source.get(field, "")).strip()]
    if missing:
        raise ValueError(f"reproduction contract is missing: {', '.join(missing)}")
    existing = read_existing(root, run_id)
    revision = (existing["revision"] + 1) if existing else 1
    contract = {
        "schema_version": "1",
        "type": "tailtrail-reproduction-contract",
        "run_id": run_id,
        "domain": domain,
        "max_achievable_confidence_state": DOMAIN_CEILINGS[domain],
        "status": "awaiting-approval",
        "trigger": str(source["trigger"]),
        "expected": str(source["expected"]),
        "actual": str(source["actual"]),
        "reproduction_method": str(source["reproduction_method"]),
        "preserve_rules": [str(item) for item in source.get("preserve_rules", [])],
        "safety_boundary": str(source["safety_boundary"]),
        "reject_reason": None,
        "revision": revision,
        "approved_at": None,
    }
    L.atomic_json(contract_path(root, run_id), contract)
    L.append_event(root, run_id, "debug_reproduction_drafted", {"revision": revision, "domain": domain})
    return contract


def ensure_investigation_prerequisites(root: Path, run_id: str, contract: dict[str, Any]) -> None:
    """Approve the run's Planning Lock and draft+approve a minimal investigation
    requirement via the existing anchor mechanism, reusing planning-lock.py and
    change-intent-anchor.py rather than parallel evidence machinery.
    execution-evidence.py requires both an approved, writes-allowed Planning
    Lock and an approved anchor before any evidence can be recorded, so both
    must exist before hypothesis testing can attach real evidence."""
    PLANNING.approve(root, run_id, True)
    if (L.state_dir(root, run_id) / "anchors" / "approved-v1.json").is_file():
        return
    source = {
        "goal": f"Investigate: {contract['trigger']}",
        "requirements": [{
            "kind": "change",
            "statement": f"Investigate and prove the root cause of: {contract['trigger']}",
            "acceptance_criteria": ["Root cause hypothesis is proven with real supporting evidence and at least one eliminated competing hypothesis"],
            "preserve_rules": contract.get("preserve_rules", []),
            "evidence_plan": ["hypothesis-ledger", "execution-evidence"],
        }],
    }
    source_path = L.state_dir(root, run_id) / "debug" / "reproduction" / "investigation-anchor-source.json"
    L.atomic_json(source_path, source)
    ANCHOR.draft(root, run_id, source_path)
    ANCHOR.approve(root, run_id)


def approve(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    contract = read_existing(root, run_id)
    if contract is None:
        raise ValueError("no reproduction contract has been drafted for this run")
    if contract["status"] == "approved":
        raise ValueError("reproduction contract is already approved")
    contract["status"] = "approved"
    contract["approved_at"] = L.utc_now()
    L.atomic_json(contract_path(root, run_id), contract)
    L.append_event(root, run_id, "debug_reproduction_approved", {"revision": contract["revision"], "domain": contract["domain"]})
    ensure_investigation_prerequisites(root, run_id, contract)
    return contract


def reject(root: Path, run_id: str, reason: str) -> dict[str, Any]:
    root = root.resolve()
    contract = read_existing(root, run_id)
    if contract is None:
        raise ValueError("no reproduction contract has been drafted for this run")
    contract["status"] = "rejected"
    contract["reject_reason"] = reason
    L.atomic_json(contract_path(root, run_id), contract)
    L.append_event(root, run_id, "debug_reproduction_rejected", {"revision": contract["revision"], "reason": reason})
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
    approve_parser = sub.add_parser("approve")
    approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    approve_parser.add_argument("--run-id", required=True)
    approve_parser.add_argument("--approved", action="store_true")
    reject_parser = sub.add_parser("reject")
    reject_parser.add_argument("--root", type=Path, default=Path.cwd())
    reject_parser.add_argument("--run-id", required=True)
    reject_parser.add_argument("--reason", required=True)
    show_parser = sub.add_parser("show")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if args.action == "draft":
            source = json.loads(args.input.read_text(encoding="utf-8"))
            result = draft(args.root, args.run_id, source)
        elif args.action == "approve":
            if not args.approved:
                raise ValueError("approving a reproduction contract requires --approved")
            result = approve(args.root, args.run_id)
        elif args.action == "reject":
            result = reject(args.root, args.run_id, args.reason)
        else:
            result = show(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Debug reproduction error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
