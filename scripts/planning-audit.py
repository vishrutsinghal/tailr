#!/usr/bin/env python3
"""Audit an awaiting-approval TailTrail plan for requirement gaps or misfits.

Issue 28 showed that a plan can be generated, approved, and activated while
missing scope the requirement text itself already names (a proof-only test
file never joining `validation_contract.editable_paths`), and that the only
correction path (`planning revise`) is unconditionally blocked once a plan is
approved. This tool gives the host a mechanical, pre-activation check to run
between Start Report generation and presenting that report to the user, so
gaps can be closed with `planning revise` while that door is still open.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
import navigator_scope as SCOPE


def _module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(loaded)
    return loaded


LOCK = _module("planning_audit_lock", "planning_lock.py")
REVISION = _module("planning_audit_revision", "planning-revision.py")
REQUIREMENTS = _module("planning_audit_requirements", "requirement_discovery.py")

# Repository-relative path-looking tokens in free text, e.g. "tests/test_foo.py" or "src/bar.ts".
_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-./]*\.[A-Za-z0-9]{1,6}\b")
_IGNORED_ROLES = {"workspace-excluded", "unknown"}


def _candidate_paths_in_text(text: str) -> list[str]:
    found: list[str] = []
    for match in _PATH_TOKEN_RE.finditer(text or ""):
        token = match.group(0).strip(".,;:()'\"")
        if "/" not in token:
            continue
        found.append(token)
    return list(dict.fromkeys(found))


def _known_scope_paths(row: dict[str, Any]) -> set[str]:
    known: set[str] = {str(item) for item in row.get("likely_paths", []) or []}
    contract = row.get("validation_contract", {})
    if isinstance(contract, dict):
        for field in ("editable_paths", "proposed_paths", "candidate_paths"):
            known.update(str(item) for item in contract.get(field, []) or [])
    evidence = row.get("scope_evidence", {})
    if isinstance(evidence, dict):
        for field in ("implementation_owners", "inspection_paths", "proof_paths"):
            known.update(str(item) for item in evidence.get(field, []) or [])
    return known


def _requirement_identifier(row: dict[str, Any]) -> str:
    """A fresh Start Report has no `requirement_uid` yet (anchor-owned, minted
    at revision/activation time); `display_id` resolves identically in
    `planning-revision.py`'s own requirement lookup, so prefer it until then.
    """
    return str(row.get("requirement_uid") or row.get("display_id", ""))


def _named_path_findings(root: Path, run_id: str, row: dict[str, Any], text: str) -> list[dict[str, Any]]:
    display_id = str(row.get("display_id", "?"))
    uid = _requirement_identifier(row)
    known = _known_scope_paths(row)
    findings: list[dict[str, Any]] = []
    for token in _candidate_paths_in_text(text):
        if token in known:
            continue
        role, _reasons = SCOPE.classify_repository_role(root, token, allow_git_inventory=False)
        if role in _IGNORED_ROLES:
            continue
        if role == "implementation-owner":
            fix = (
                f"tailtrail planning revise --root . --run-id {run_id} --changes "
                f"'[{{\"kind\":\"scope-add\",\"requirement_uid\":\"{uid}\",\"path\":\"{token}\","
                f"\"reason\":\"close requirement-named scope gap\"}}]'"
            )
        else:
            fix = (
                f"tailtrail planning revise --root . --run-id {run_id} --changes "
                f"'[{{\"kind\":\"proof-update\",\"requirement_uid\":\"{uid}\",\"reason\":"
                f"\"close requirement-named scope gap\",\"evidence_plan\":[\"Record proof for {token}\"],"
                f"\"editable_paths\":[\"{token}\"]}}]'"
            )
        findings.append({
            "type": "named_path_missing_from_scope",
            "display_id": display_id,
            "requirement_uid": uid,
            "path": token,
            "role": role,
            "detail": (
                f"`{token}` is named in requirement `{display_id}` but is absent from `likely_paths`, "
                f"`validation_contract`, and `scope_evidence` alike (Issue 28 pattern)."
            ),
            "suggested_fix": fix,
        })
    return findings


def _tier_findings(run_id: str, row: dict[str, Any], statement: str) -> list[dict[str, Any]]:
    display_id = str(row.get("display_id", "?"))
    uid = _requirement_identifier(row)
    contract = row.get("validation_contract", {})
    contract = contract if isinstance(contract, dict) else {}
    actual_tiers = {str(item) for item in contract.get("tiers", []) or []}
    expected_tiers = set(REQUIREMENTS._tiers(statement))
    missing = sorted(expected_tiers - actual_tiers)
    findings: list[dict[str, Any]] = []
    if missing:
        findings.append({
            "type": "tier_mismatch",
            "display_id": display_id,
            "requirement_uid": uid,
            "missing_tiers": missing,
            "detail": (
                f"requirement `{display_id}` wording implies tier(s) {missing} not present in "
                f"`validation_contract.tiers` {sorted(actual_tiers)}."
            ),
            "suggested_fix": (
                f"tailtrail planning revise --root . --run-id {run_id} --changes "
                f"'[{{\"kind\":\"proof-update\",\"requirement_uid\":\"{uid}\",\"reason\":"
                f"\"close tier gap\",\"evidence_plan\":[\"Record proof for {', '.join(missing)}\"],"
                f"\"tiers\":{json.dumps(missing)}}}]'"
            ),
        })
    has_proof = bool(
        contract.get("commands") or contract.get("editable_paths")
        or contract.get("proposed_paths") or contract.get("candidate_paths")
    )
    if actual_tiers and not has_proof:
        findings.append({
            "type": "missing_proof_registration",
            "display_id": display_id,
            "requirement_uid": uid,
            "detail": (
                f"requirement `{display_id}` declares validation tiers {sorted(actual_tiers)} but no proof "
                f"command or editable/proposed/candidate path is registered on `validation_contract`."
            ),
            "suggested_fix": (
                f"tailtrail planning revise --root . --run-id {run_id} --changes "
                f"'[{{\"kind\":\"proof-update\",\"requirement_uid\":\"{uid}\",\"reason\":"
                f"\"register a runnable proof command\",\"evidence_plan\":[\"Run the named proof command\"],"
                f"\"commands\":[\"<runnable proof command>\"]}}]'"
            ),
        })
    return findings


def audit_report(root: Path, run_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """Pure gap check over an in-memory Start/revision report (no file I/O)."""
    goal = str(report.get("goal", ""))
    navigator = report.get("navigator", {})
    matrix = navigator.get("requirement_matrix", []) if isinstance(navigator, dict) else []
    findings: list[dict[str, Any]] = []
    for row in matrix if isinstance(matrix, list) else []:
        if not isinstance(row, dict):
            continue
        statement = str(row.get("statement", ""))
        text = " ".join([statement, goal, " ".join(row.get("acceptance_criteria", []) or [])])
        findings.extend(_named_path_findings(root, run_id, row, text))
        findings.extend(_tier_findings(run_id, row, statement))
    return {
        "schema_version": "1",
        "type": "tailtrail-planning-audit",
        "run_id": run_id,
        "status": "clean" if not findings else "gaps-found",
        "findings": findings,
    }


def audit(root: Path, run_id: str) -> dict[str, Any]:
    """Load the plan for `run_id` and audit it.

    While a proposed revision is still pending (proposed but not yet
    `revision-approve`d, which also activates the run), that revision's
    `proposed_report` is the correction the host is iterating on, so it is
    audited in place of the stale active report.
    """
    root = root.resolve()
    lock = LOCK.show(root, run_id)
    if lock["status"] != "awaiting-approval":
        raise ValueError(
            f"planning audit runs only while a plan is awaiting approval (status is `{lock['status']}`); "
            f"check `tailtrail planning show --root . --run-id {run_id}`"
        )
    state = LOCK.revision_state(root, run_id)
    if state.get("pending_revision") is not None:
        proposed = REVISION.show(root, run_id)
        report = proposed.get("proposed_report")
        if not isinstance(report, dict):
            raise ValueError(f"pending plan revision v{state['pending_revision']} has no proposed report")
        return audit_report(root, run_id, report)
    report_path = root / state["active_report"]
    payload = LOCK.read(report_path)
    return audit_report(root, run_id, payload["report"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        result = audit(args.root, args.run_id)
    except ValueError as error:
        print(json.dumps({"error": str(error)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "clean" else 2


if __name__ == "__main__":
    raise SystemExit(main())
