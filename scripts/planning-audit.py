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


def correction_command(
    run_id: str,
    changes: list[dict[str, Any]],
    *,
    pending: bool = False,
) -> dict[str, Any]:
    """Render one executable planning-revision correction (central renderer).

    Every executable suggestion carries the complete change payload, the
    required `--approved-proposal` marker, and `--supersede-pending` only
    when a pending revision actually exists. `command` is the reviewable
    form; `portable_command` is the shell-safe base64 form. Findings that
    need host-supplied values are labeled `template` with `open_fields`;
    unrecoverable states are `restart-required` with no command at all.
    """
    import base64

    payload = json.dumps(changes, separators=(",", ":"))
    tail = " --approved-proposal" + (" --supersede-pending" if pending else "")
    portable = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return {
        "command": f"tailtrail planning revise --root . --run-id {run_id} --changes '{payload}'{tail}",
        "portable_command": (
            f"tailtrail planning revise --root . --run-id {run_id} "
            f"--changes-base64 {portable}{tail}"
        ),
        "changes": changes,
        "approved_proposal": True,
        "supersede_pending": bool(pending),
    }


def _named_path_findings(
    root: Path,
    run_id: str,
    row: dict[str, Any],
    text: str,
    *,
    has_scope_evidence: bool = True,
    pending: bool = False,
) -> list[dict[str, Any]]:
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
            if not has_scope_evidence:
                findings.append({
                    "type": "missing-canonical-scope-evidence",
                    "correction_kind": "restart-required",
                    "display_id": display_id,
                    "requirement_uid": uid,
                    "path": token,
                    "role": role,
                    "detail": (
                        f"`{token}` is named in requirement `{display_id}` but the plan has no "
                        f"canonical scope evidence at all. A plain `scope-add` cannot repair this: "
                        f"re-route with resolvable scope (explicit --changed owner, scope answers, "
                        f"or a narrower goal) instead of revising."
                    ),
                })
                continue
            fix = _executable_fix(run_id, [{
                "kind": "scope-add", "requirement_uid": uid, "path": token,
                "reason": "close requirement-named scope gap",
            }], pending=pending)
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
                **fix,
            })
            continue
        fix = _executable_fix(run_id, [{
            "kind": "proof-update", "requirement_uid": uid,
            "reason": "close requirement-named scope gap",
            "evidence_plan": [f"Record proof for {token}"],
            "editable_paths": [token],
        }], pending=pending)
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
            **fix,
        })
    return findings


def _tier_findings(
    run_id: str,
    row: dict[str, Any],
    statement: str,
    *,
    pending: bool = False,
) -> list[dict[str, Any]]:
    display_id = str(row.get("display_id", "?"))
    uid = _requirement_identifier(row)
    contract = row.get("validation_contract", {})
    contract = contract if isinstance(contract, dict) else {}
    actual_tiers = {str(item) for item in contract.get("tiers", []) or []}
    expected_tiers = set(REQUIREMENTS._tiers(statement))
    missing = sorted(expected_tiers - actual_tiers)
    findings: list[dict[str, Any]] = []
    if missing:
        fix = _executable_fix(run_id, [{
            "kind": "proof-update", "requirement_uid": uid,
            "reason": "close tier gap",
            "evidence_plan": [f"Record proof for {', '.join(missing)}"],
            "tiers": missing,
        }], pending=pending)
        findings.append({
            "type": "tier_mismatch",
            "display_id": display_id,
            "requirement_uid": uid,
            "missing_tiers": missing,
            "detail": (
                f"requirement `{display_id}` wording implies tier(s) {missing} not present in "
                f"`validation_contract.tiers` {sorted(actual_tiers)}."
            ),
            **fix,
        })
    has_proof = bool(
        contract.get("commands") or contract.get("editable_paths")
        or contract.get("proposed_paths") or contract.get("candidate_paths")
    )
    if actual_tiers and not has_proof:
        findings.append({
            "type": "missing_proof_registration",
            "correction_kind": "template",
            "open_fields": ["commands"],
            "display_id": display_id,
            "requirement_uid": uid,
            "detail": (
                f"requirement `{display_id}` declares validation tiers {sorted(actual_tiers)} but no proof "
                f"command or editable/proposed/candidate path is registered on `validation_contract`."
            ),
            "suggested_fix": (
                correction_command(run_id, [{
                    "kind": "proof-update", "requirement_uid": uid,
                    "reason": "register a runnable proof command",
                    "evidence_plan": ["Run the named proof command"],
                    "commands": ["<runnable proof command>"],
                }], pending=pending)["command"]
            ),
        })
    return findings


def _normalize_check(entry: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    command = str(entry.get("command", "")).strip()
    tiers = tuple(sorted(str(value).strip() for value in (entry.get("tiers", []) or []) if str(value).strip()))
    return (command, tiers)


def _focused_covers(focused: list[dict[str, Any]], tier: str, command: str | None) -> dict[str, Any] | None:
    for item in focused:
        if not isinstance(item, dict):
            continue
        tiers = item.get("tiers") if isinstance(item.get("tiers"), list) else [item.get("tier")]
        names = {str(value).strip() for value in (tiers or []) if str(value).strip()}
        if not names and isinstance(item.get("tier"), str):
            names = {part.strip() for part in str(item.get("tier", "")).split("+") if part.strip()}
        if tier not in names:
            continue
        if command is None and not str(item.get("command", "")).strip():
            return item
        if command is not None and str(item.get("command", "")).strip() == command:
            return item
    return None


def _executable_fix(
    run_id: str,
    changes: list[dict[str, Any]],
    *,
    pending: bool = False,
) -> dict[str, Any]:
    """Executable finding fields: reviewable + portable commands and the payload.

    Tests apply `correction["changes"]` through the real revision machinery;
    hosts paste `suggested_fix` (or the shell-safe `suggested_fix_portable`).
    """
    rendered = correction_command(run_id, changes, pending=pending)
    return {
        "correction_kind": "executable",
        "suggested_fix": rendered["command"],
        "suggested_fix_portable": rendered["portable_command"],
        "correction": {
            "changes": changes,
            "approved_proposal": True,
            "supersede_pending": bool(pending),
        },
    }


def _rebuild_fix(run_id: str, uid: str, reason: str, *, pending: bool = False) -> dict[str, Any]:
    """Executable rebuild correction: re-derives checks, focused rows, fingerprint."""
    return _executable_fix(run_id, [{
        "kind": "proof-update", "requirement_uid": uid, "reason": reason,
        "evidence_plan": ["Rebuild proof projection"],
    }], pending=pending)


def _convergence_findings(
    run_id: str,
    report: dict[str, Any],
    projection: dict[str, Any],
    *,
    pending: bool = False,
) -> list[dict[str, Any]]:
    """Mandatory convergence gate: contracts, checks, focused rows, and fingerprint must agree."""
    findings: list[dict[str, Any]] = []
    expected_focused = projection.get("focused_validation", [])
    expected_by_req = projection.get("checks_by_requirement", {})
    focused = report.get("focused_validation", [])
    focused = focused if isinstance(focused, list) else []
    canonical = {item.get("display_id"): item for item in projection.get("requirements", []) if isinstance(item, dict)}

    for req_id, canonical_row in canonical.items():
        uid = str(req_id)
        # Locate the live row to read saved checks and proof paths.
        live_rows = LOCK._canonical_requirements(report) if hasattr(LOCK, "_canonical_requirements") else []
        live = next((row for row in live_rows if str(row.get("display_id") or row.get("requirement_uid")) == uid), {})
        contract = live.get("validation_contract", {}) if isinstance(live, dict) else {}
        contract = contract if isinstance(contract, dict) else {}
        saved_checks = [item for item in (contract.get("checks", []) or []) if isinstance(item, dict)]
        expected_checks = expected_by_req.get(uid, [])

        if sorted(_normalize_check(item) for item in saved_checks) != sorted(_normalize_check(item) for item in expected_checks):
            fix = _rebuild_fix(run_id, uid, "rebuild proof projection", pending=pending)
            findings.append({
                "type": "check-projection-mismatch",
                "display_id": uid,
                "requirement_uid": uid,
                "detail": (
                    f"requirement `{uid}` saved `validation_contract.checks[]` does not match "
                    f"its canonical command/tier derivation."
                ),
                "expected": expected_checks,
                "actual": saved_checks,
                **fix,
            })

        for item in expected_focused:
            if str(item.get("requirement_id")) != uid:
                continue
            tier = str(item.get("tier", ""))
            command = item.get("command")
            command_text = str(command or "").strip()
            if not command_text:
                findings.append({
                    "type": "unresolved-tier-proof",
                    "correction_kind": "template",
                    "open_fields": ["commands"],
                    "display_id": uid,
                    "requirement_uid": uid,
                    "tier": tier,
                    "detail": (
                        f"requirement `{uid}` tier `{tier}` has no positional proof command; "
                        f"adding a tier label alone must not turn the plan green."
                    ),
                    "suggested_fix": (
                        correction_command(run_id, [{
                            "kind": "proof-update", "requirement_uid": uid,
                            "reason": f"attach proof for {tier}",
                            "evidence_plan": [f"Run the {tier} proof"],
                            "commands": ["<runnable proof command>"], "tiers": [tier],
                        }], pending=pending)["command"]
                    ),
                })
                continue
            covering = _focused_covers(focused, tier, command_text)
            if covering is None:
                fix = _rebuild_fix(run_id, uid, "rebuild proof projection", pending=pending)
                findings.append({
                    "type": "focused-validation-stale",
                    "display_id": uid,
                    "requirement_uid": uid,
                    "tier": tier,
                    "detail": (
                        f"requirement `{uid}` tier `{tier}` command `{command_text}` has no matching "
                        f"`focused_validation` row; the rendered proof table is stale."
                    ),
                    "expected": {"requirement_id": uid, "tier": tier, "command": command_text, "status": "resolved"},
                    **fix,
                })
            elif str(covering.get("candidate_state", "")).strip() == "unresolved" or not str(covering.get("candidate", "")).strip() or covering.get("candidate") == "not resolved from planning evidence":
                findings.append({
                    "type": "focused-validation-unresolved",
                    "correction_kind": "template",
                    "open_fields": ["editable_paths"],
                    "display_id": uid,
                    "requirement_uid": uid,
                    "tier": tier,
                    "detail": (
                        f"requirement `{uid}` tier `{tier}` focused row has no eligible proof path."
                    ),
                    "suggested_fix": (
                        correction_command(run_id, [{
                            "kind": "proof-update", "requirement_uid": uid,
                            "reason": "register proof path",
                            "evidence_plan": ["Record proof path"],
                            "editable_paths": ["<proof path>"],
                        }], pending=pending)["command"]
                    ),
                })

    saved_fingerprint = report.get("effective_plan_fingerprint")
    if isinstance(saved_fingerprint, str) and saved_fingerprint.strip():
        if saved_fingerprint.strip() != str(projection.get("fingerprint", "")).strip():
            first_uid = next(
                (str(item.get("display_id")) for item in projection.get("requirements", []) if isinstance(item, dict)),
                "REQ-01",
            )
            fix = _rebuild_fix(run_id, first_uid, "rebuild proof projection", pending=pending)
            findings.append({
                "type": "fingerprint-mismatch",
                "detail": "saved `effective_plan_fingerprint` differs from the converged derivation; approval authorizes exactly one converged plan.",
                "expected": projection.get("fingerprint"),
                "actual": saved_fingerprint,
                **fix,
            })

    # Behaviour Harness specificity: a behaviour tier needs a
    # requirement-bound, non-generic scenario, never an ID-only link.
    behaviour_tiers = {
        str(item.get("requirement_id"))
        for item in expected_focused
        if str(item.get("tier", "")) == "behaviour" and item.get("command")
    }
    if behaviour_tiers:
        behaviour_plan = report.get("behaviour_plan", {}) if isinstance(report.get("behaviour_plan"), dict) else {}
        scenarios = behaviour_plan.get("scenarios", []) if isinstance(behaviour_plan, dict) else []
        scenarios = [item for item in scenarios] if isinstance(scenarios, list) else []
        for req_id in sorted(behaviour_tiers):
            bound = [
                item for item in scenarios
                if isinstance(item, dict) and req_id in {str(value) for value in (item.get("requirement_ids", []) or [])}
            ]
            specific = [
                item for item in bound
                if str(item.get("expected_outcome", "")).strip() and str(item.get("action", "")).strip()
            ]
            if not specific:
                findings.append({
                    "type": "behaviour-scenario-generic",
                    "correction_kind": "template",
                    "open_fields": ["behaviour scenario"],
                    "display_id": req_id,
                    "requirement_uid": req_id,
                    "detail": (
                        f"requirement `{req_id}` needs behaviour proof but has no requirement-specific "
                        f"Behaviour Harness scenario (ID link alone is insufficient). Author a scenario "
                        f"with this requirement ID, a concrete action, and an expected outcome; no "
                        f"revision command can author it for you."
                    ),
                })
    return findings


def audit_report(
    root: Path,
    run_id: str,
    report: dict[str, Any],
    *,
    pending: bool = False,
) -> dict[str, Any]:
    """Pure gap check over an in-memory Start/revision report (no file I/O)."""
    goal = str(report.get("goal", ""))
    navigator = report.get("navigator", {})
    matrix = navigator.get("requirement_matrix", []) if isinstance(navigator, dict) else []
    findings: list[dict[str, Any]] = []
    has_scope_evidence = isinstance(navigator.get("scope_evidence"), dict) if isinstance(navigator, dict) else False

    projection = LOCK.effective_plan_projection(report)
    findings.extend(_convergence_findings(run_id, report, projection, pending=pending))

    for row in matrix if isinstance(matrix, list) else []:
        if not isinstance(row, dict):
            continue
        statement = str(row.get("statement", ""))
        text = " ".join([statement, goal, " ".join(row.get("acceptance_criteria", []) or [])])
        findings.extend(_named_path_findings(root, run_id, row, text, has_scope_evidence=has_scope_evidence, pending=pending))
        findings.extend(_tier_findings(run_id, row, statement, pending=pending))
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
        return audit_report(root, run_id, report, pending=True)
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
