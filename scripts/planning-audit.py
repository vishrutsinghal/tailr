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
import copy
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


def _build_review_cycles_summary(root: Path, run_id: str) -> dict[str, Any]:
    """Build review cycles summary from run events and revision history.
    
    Reads the events.jsonl to reconstruct the planning lifecycle and summarize:
    - Number of audit cycles
    - What changed in each revision
    - Current gap status
    - Approval readiness
    """
    run_dir = root / ".tailtrail" / "runs" / run_id
    events_file = run_dir / "events.jsonl"
    
    # A review run starts with the initial v1 plan.  Revisions are additional
    # cycles, not the only cycles.  Keeping both counts prevents a clean first
    # audit from incorrectly rendering as "0 cycles".
    cycles: list[dict[str, Any]] = [{
        "cycle": 1,
        "revision": 1,
        "status": "initial-review",
        "actions": ["Initial v1 plan reviewed"],
    }]
    revision_events: list[dict[str, Any]] = []
    
    try:
        if events_file.exists():
            with open(events_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if event.get("event_type") in ("planning_revision_proposed", "planning_revision_superseded", "planning_revision_approved"):
                        revision_events.append(event)
    except Exception as e:
        # If we can't read events, just return empty summary
        return {
            "total_review_cycles": 1,
            "revision_cycles": 0,
            "total_cycles": 1,
            "cycles": cycles,
            "approval_readiness": "unknown",
            "review_note": f"Could not load review history: {str(e)}"
        }
    
    # Group events by revision and build cycles
    revision_map: dict[int, dict[str, Any]] = {}
    for event in revision_events:
        rev = event.get("payload", {}).get("revision")
        if rev is not None:
            if rev not in revision_map:
                revision_map[rev] = {"events": []}
            revision_map[rev]["events"].append(event)
    
    # Build cycle entries
    for rev in sorted(revision_map.keys()):
        events_for_rev = revision_map[rev]["events"]
        cycle_info = {
            "cycle": len(cycles) + 1,
            "revision": rev,
            "status": "pending",
            "actions": []
        }
        
        for event in events_for_rev:
            event_type = event.get("event_type")
            if event_type == "planning_revision_proposed":
                cycle_info["status"] = "proposed"
                payload = event.get("payload", {})
                cycle_info["actions"].append(f"Revision v{rev} proposed")
                if "requirement_uids" in payload:
                    cycle_info["actions"].append(f"Updated {len(payload.get('requirement_uids', []))} requirement(s)")
            elif event_type == "planning_revision_superseded":
                cycle_info["status"] = "superseded"
                cycle_info["actions"].append(f"Superseded by v{event.get('payload', {}).get('superseded_by')}")
            elif event_type == "planning_revision_approved":
                cycle_info["status"] = "approved"
                audit_result = event.get("payload", {}).get("audit", {})
                if audit_result.get("status") == "clean":
                    cycle_info["actions"].append("✓ Audit status: clean - READY FOR APPROVAL")
                else:
                    cycle_info["actions"].append(f"Audit status: {audit_result.get('status')}")
        
        if cycle_info.get("actions"):
            cycles.append(cycle_info)
    
    # Determine approval readiness
    approval_readiness = "awaiting-review"
    if any(c.get("status") == "approved" for c in cycles):
        approval_readiness = "ready-to-approve"
    elif any(c.get("status") == "pending" for c in cycles):
        approval_readiness = "revision-pending"
    
    return {
        "total_review_cycles": len(cycles),
        "revision_cycles": len(cycles) - 1,
        # Retained for callers that have not moved to the explicit names.
        "total_cycles": len(cycles),
        "cycles": cycles,
        "approval_readiness": approval_readiness,
        "review_note": "Cycles show planning iterations through proposed revisions until audit status reaches clean state."
    }


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
    known_scope_paths: set[str] | None = None,
    pending: bool = False,
) -> list[dict[str, Any]]:
    display_id = str(row.get("display_id", "?"))
    uid = _requirement_identifier(row)
    known = _known_scope_paths(row) | set(known_scope_paths or set())
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
    allowed_tiers: set[str] | None = None,
) -> list[dict[str, Any]]:
    display_id = str(row.get("display_id", "?"))
    uid = _requirement_identifier(row)
    contract = row.get("validation_contract", {})
    contract = contract if isinstance(contract, dict) else {}
    actual_tiers = {str(item) for item in contract.get("tiers", []) or []}
    expected_tiers = set(REQUIREMENTS._tiers(statement))
    if allowed_tiers is not None:
        expected_tiers &= allowed_tiers
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


def _internal_proof_boundary(navigator: dict[str, Any]) -> set[str] | None:
    """Return the authoritative tier cap for an internal-only host boundary.

    Tier inference is useful as a planning hint, but an accepted internal
    boundary deliberately selects focused unit or contract proof. Public
    surfaces retain ordinary inferred-tier enforcement.
    """
    boundary = navigator.get("host_proof_boundary")
    if not isinstance(boundary, dict) or boundary.get("behavior_surface") != "internal":
        return None
    return {str(tier) for tier in boundary.get("allowed_tiers", []) if str(tier)}


def _normalize_check(entry: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    """Normalize a check entry for comparison, handling both command strings and command_id refs."""
    # Support both old (embedded command) and new (command_id) formats
    command = str(entry.get("command", "")).strip()
    if not command:
        command = str(entry.get("command_id", "")).strip()
    tiers = tuple(sorted(str(value).strip() for value in (entry.get("tiers", []) or []) if str(value).strip()))
    return (command, tiers)


def _resolve_command_from_registry(command_id_or_str: str, registry: dict[str, Any]) -> str | None:
    """Resolve a command_id to actual command string, or return string if already embedded.
    
    Supports both new registry-based refs (cmd-xxxxx) and old embedded commands.
    """
    if not command_id_or_str:
        return None
    # If it looks like a command_id, resolve from registry
    if isinstance(command_id_or_str, str) and command_id_or_str.startswith("cmd-"):
        if isinstance(registry, dict) and command_id_or_str in registry:
            return str(registry[command_id_or_str].get("command", ""))
        return None  # command_id not found in registry
    # Otherwise treat as embedded command string
    return str(command_id_or_str).strip() if command_id_or_str else None


def _focused_covers(
    focused: list[dict[str, Any]],
    requirement_id: str,
    tier: str,
    command: str | None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Find a focused_validation row matching requirement, tier, and command (or command_id).
    
    Handles both old format (command string) and new format (command_id reference).
    """
    registry = registry or {}
    for item in focused:
        if not isinstance(item, dict):
            continue
        # A static command is intentionally shared; executable proof is not.
        if tier == "static" and item.get("check_kind") == "static":
            pass
        elif str(item.get("requirement_id", "")) != requirement_id:
            continue
        tiers = item.get("tiers") if isinstance(item.get("tiers"), list) else [item.get("tier")]
        names = {str(value).strip() for value in (tiers or []) if str(value).strip()}
        if not names and isinstance(item.get("tier"), str):
            names = {part.strip() for part in str(item.get("tier", "")).split("+") if part.strip()}
        if tier not in names:
            continue
        
        # Handle both command (old) and command_id (new) fields
        item_command = str(item.get("command", "")).strip() or str(item.get("command_id", "")).strip()
        if not item_command:
            if command is None:
                return item
            continue
        
        # Resolve command_id if present
        if item_command.startswith("cmd-"):
            item_command = _resolve_command_from_registry(item_command, registry) or item_command
        
        if command is None and not item_command:
            return item
        if command is not None and item_command == command:
            return item
    return None



def _command_targets_path(command: str, path: str) -> bool:
    """Whether an exact proof command names its declared proof target.

    This is deliberately a syntactic check, not a claim that a test's
    assertions exercise a particular implementation path. Navigator scope
    evidence provides that relationship. The command must at least target the
    requirement's own declared test/module instead of a same-tier test copied
    from another requirement.
    """
    normalized_command = command.replace("\\", "/")
    normalized_path = path.replace("\\", "/").strip()
    if not normalized_path or normalized_path.startswith("not resolved"):
        return False
    module = normalized_path[:-3].replace("/", ".") if normalized_path.endswith(".py") else ""
    if normalized_path in normalized_command or (module and module in normalized_command):
        return True
    basename = Path(normalized_path).name
    runner = normalized_command.lower()
    return bool(
        basename
        and basename in normalized_command
        and any(tool in runner for tool in ("pytest", "unittest", "jest", "vitest", "mocha", "cypress"))
    )


def _proof_binding_findings(
    run_id: str,
    row: dict[str, Any],
    checks: list[dict[str, Any]],
    *,
    command_registry: dict[str, Any] | None = None,
    pending: bool = False,
) -> list[dict[str, Any]]:
    """Require requirement-scoped, executable proof before approval.

    A validation contract is authoritative only when each proof check names a
    runnable command and a proof path belonging to the same requirement's
    scope evidence. This prevents a unit command for REQ-02 being presented as
    REQ-01 proof merely because both rows use the `unit` tier.
    """
    if str(row.get("kind", "")).strip() == "constraint":
        return []
    contract = row.get("validation_contract", {})
    contract = contract if isinstance(contract, dict) else {}
    if str(contract.get("state", "required")) != "required":
        return []
    display_id = str(row.get("display_id", "?"))
    uid = _requirement_identifier(row)
    proof_checks = [check for check in checks if str(check.get("kind", "proof")) == "proof"]
    findings: list[dict[str, Any]] = []
    if not proof_checks:
        findings.append({
            "type": "missing-requirement-proof-binding",
            "correction_kind": "template",
            "open_fields": ["commands", "editable_paths"],
            "display_id": display_id,
            "requirement_uid": uid,
            "detail": (
                f"proof-required requirement `{display_id}` has no requirement-linked proof check. "
                "Record an exact runnable command and its proof path before approval."
            ),
        })
        return findings
    scope = row.get("scope_evidence", {})
    scope = scope if isinstance(scope, dict) else {}
    command_registry = command_registry or {}
    scoped_proof_paths = {
        str(path) for path in (scope.get("proof_paths", []) or [])
        if str(path)
    }
    for check in proof_checks:
        command_ref = str(check.get("command", "")).strip() or str(check.get("command_id", "")).strip()
        command = _resolve_command_from_registry(command_ref, command_registry) or ""
        paths = [str(path) for path in (check.get("candidate_paths", []) or []) if str(path).strip()]
        tiers = [str(tier) for tier in (check.get("tiers", []) or []) if str(tier)]
        if not command or not paths:
            findings.append({
                "type": "incomplete-requirement-proof-binding",
                "correction_kind": "template",
                "open_fields": ["commands", "editable_paths"],
                "display_id": display_id,
                "requirement_uid": uid,
                "tiers": tiers,
                "detail": (
                    f"requirement `{display_id}` proof for {tiers or ['its declared tier']} must include both "
                    "an exact runnable command and an eligible proof path."
                ),
            })
            continue
        if scoped_proof_paths and not set(paths).intersection(scoped_proof_paths):
            findings.append({
                "type": "proof-path-outside-requirement-scope",
                "correction_kind": "template",
                "open_fields": ["editable_paths"],
                "display_id": display_id,
                "requirement_uid": uid,
                "proof_paths": paths,
                "scoped_proof_paths": sorted(scoped_proof_paths),
                "detail": (
                    f"requirement `{display_id}` uses proof path(s) {paths} that its own scope evidence did not "
                    "approve. Re-scope the path or bind a proof path from this requirement's proof evidence."
                ),
            })
        # If scope has not yet supplied a requirement-specific proof path,
        # this audit cannot honestly infer semantic relevance from a command
        # string alone. Once it has, require the command to target that exact
        # scoped proof rather than a same-tier neighbour.
        for path in paths if scoped_proof_paths else []:
            if _command_targets_path(command, path):
                continue
            findings.append({
                "type": "proof-command-does-not-target-path",
                "correction_kind": "template",
                "open_fields": ["commands"],
                "display_id": display_id,
                "requirement_uid": uid,
                "command": command,
                "proof_path": path,
                "detail": (
                    f"requirement `{display_id}` command `{command}` does not target declared proof path `{path}`. "
                    "Use a focused command for that path or change the proof binding."
                ),
            })
    return findings


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
    command_registry = projection.get("command_registry", {})
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
            # Handle both command (old) and command_id (new) fields
            command_id_or_str = item.get("command_id") or item.get("command")
            command_text = _resolve_command_from_registry(str(command_id_or_str or "").strip(), command_registry)
            if not command_id_or_str:
                command_text = None
            if command_text is None and not command_id_or_str:
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
            covering = _focused_covers(focused, uid, tier, command_text, registry=command_registry)
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
        if str(item.get("tier", "")) == "behaviour" and (item.get("command") or item.get("command_id"))
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
                scenario_change = json.dumps([{
                    "kind": "behaviour-scenario-add",
                    "requirement_uid": req_id,
                    "reason": "add requirement-specific behaviour scenario",
                    "scenario": {
                        "scenario_id": f"BHV-{req_id}",
                        "action": "<concrete action>",
                        "expected_outcome": "<observable expected outcome>",
                    },
                }], separators=(",", ":"))
                findings.append({
                    "type": "behaviour-scenario-generic",
                    "correction_kind": "template",
                    "open_fields": ["behaviour scenario"],
                    "display_id": req_id,
                    "requirement_uid": req_id,
                    "detail": (
                        f"requirement `{req_id}` needs behaviour proof but has no requirement-specific "
                        f"Behaviour Harness scenario (ID link alone is insufficient). Add a scenario "
                        f"with this requirement ID, a concrete action, and an expected outcome."
                    ),
                    "suggested_fix": (
                        "tailtrail planning revise --root . --run-id <run-id> --changes "
                        f"'{scenario_change}' "
                        "--approved-proposal"
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

    aidlc_mode = report.get("aidlc_mode", {})
    if isinstance(aidlc_mode, dict) and aidlc_mode.get("state") == "awaiting-mode-approval":
        review_cycles = _build_review_cycles_summary(root, run_id)
        return {
            "schema_version": "1",
            "type": "tailtrail-planning-audit",
            "run_id": run_id,
            "status": "clean",
            "findings": [],
            "review_cycles_summary": review_cycles,
            "approval_assessment": {
                "readiness": "ready-to-approve-mode-switch",
                "gaps_closed": True,
                "total_cycles": review_cycles.get("total_cycles", 0),
                "approval_decision": "READY FOR AIDLC MODE-SWITCH APPROVAL",
                "boundary": (
                    "This audit approves only the Lite-to-Standard planning-mode transition. "
                    "It grants no implementation authority and does not approve the rejected requirement boundary."
                ),
            },
        }

    projection = LOCK.effective_plan_projection(report)
    findings.extend(_convergence_findings(run_id, report, projection, pending=pending))

    global_scope_paths: set[str] = set()
    scope_evidence = navigator.get("scope_evidence", {}) if isinstance(navigator, dict) else {}
    if isinstance(scope_evidence, dict):
        for field in ("implementation_owners", "inspection_paths", "proof_paths"):
            global_scope_paths.update(str(item) for item in scope_evidence.get(field, []) or [])
        for requirement in scope_evidence.get("requirements", []) or []:
            if isinstance(requirement, dict):
                for field in ("implementation_owners", "inspection_paths", "proof_paths"):
                    global_scope_paths.update(str(item) for item in requirement.get(field, []) or [])
    declared_roles = navigator.get("host_declared_scope_roles", {}) if isinstance(navigator, dict) else {}
    if isinstance(declared_roles, dict):
        for field in ("implementation_owners", "inspection_paths", "proof_paths"):
            global_scope_paths.update(str(item) for item in declared_roles.get(field, []) or [])

    behavior_check = navigator.get("behavior_check", {}) if isinstance(navigator, dict) else {}
    if isinstance(behavior_check, dict) and behavior_check.get("state") == "already-satisfied":
        findings.append({
            "type": "already-satisfied-implementation-plan",
            "correction_kind": "restart-required",
            "open_fields": ["implementation decision"],
            "detail": (
                "The read-only behavior preflight found the requested behavior already present at the proposed owner "
                "and linked proof path. Re-route as validation-only or provide evidence that the requested outcome differs."
            ),
            "behavior_check": behavior_check,
        })

    internal_allowed_tiers = _internal_proof_boundary(navigator) if isinstance(navigator, dict) else None
    proof_boundary_conflict = navigator.get("host_proof_boundary_conflict") if isinstance(navigator, dict) else None
    
    if isinstance(proof_boundary_conflict, dict) and internal_allowed_tiers is None:
        findings.append({
            "type": "inferred-tier-conflicts-host-proof-boundary",
            "correction_kind": "template",
            "open_fields": ["host-approved proof boundary"],
            "detail": (
                "Inferred validation tiers exceed the host-approved proof boundary; "
                "use `planning revise` with `proof-boundary-expand` to amend the saved boundary in-place, "
                "then re-run this audit before approval."
            ),
            "proof_boundary": proof_boundary_conflict,
        })

    for row in matrix if isinstance(matrix, list) else []:
        if not isinstance(row, dict):
            continue
        statement = str(row.get("statement", ""))
        text = " ".join([statement, goal, " ".join(row.get("acceptance_criteria", []) or [])])
        findings.extend(_named_path_findings(root, run_id, row, text, has_scope_evidence=has_scope_evidence, known_scope_paths=global_scope_paths, pending=pending))
        findings.extend(
            _tier_findings(
                run_id,
                row,
                statement,
                pending=pending,
                allowed_tiers=internal_allowed_tiers,
            )
        )
        req_id = str(row.get("display_id") or row.get("requirement_uid") or "")
        checks = projection.get("checks_by_requirement", {}).get(req_id, [])
        findings.extend(_proof_binding_findings(
            run_id,
            row,
            checks,
            command_registry=projection.get("command_registry", {}),
            pending=pending,
        ))
    
    # Build review cycles summary from run history
    review_cycles = _build_review_cycles_summary(root, run_id)
    
    # Determine approval readiness based on gap status and history
    approval_readiness = "ready-to-approve" if not findings else "gaps-remain-revise-needed"
    
    return {
        "schema_version": "1",
        "type": "tailtrail-planning-audit",
        "run_id": run_id,
        "status": "clean" if not findings else "gaps-found",
        "findings": findings,
        "review_cycles_summary": review_cycles,
        "approval_assessment": {
            "readiness": approval_readiness,
            "gaps_closed": len(findings) == 0,
            "total_cycles": review_cycles.get("total_cycles", 0),
            "approval_decision": "READY FOR APPROVAL" if not findings else "REVISE PLAN AND RE-AUDIT",
        },
    }


def _validated_aidlc_revision_report(root: Path, run_id: str, report: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    state_path = root / ".tailtrail" / "runs" / run_id / "planning" / "aidlc-correction-state.json"
    if not state_path.is_file():
        return report
    state = LOCK.read(state_path)
    if state.get("state") != "revision-ready":
        return report
    revision_value = str(state.get("active_revision", ""))
    revision_path = Path(revision_value)
    if not revision_value or revision_path.is_absolute() or ".." in revision_path.parts:
        raise ValueError("validated AIDLC correction state has an unsafe active revision path")
    resolved_revision = (root / revision_path).resolve()
    run_root = (root / ".tailtrail" / "runs" / run_id).resolve()
    try:
        resolved_revision.relative_to(run_root)
    except ValueError as error:
        raise ValueError("validated AIDLC correction revision is outside its run directory") from error
    revision = LOCK.read(resolved_revision)
    requirements = revision.get("requirements", [])
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("validated AIDLC correction revision has no requirement matrix")

    projected = copy.deepcopy(report)
    navigator = projected.setdefault("navigator", {})
    if not isinstance(navigator, dict):
        raise ValueError("saved Navigator report is invalid")
    rows = copy.deepcopy([row for row in requirements if isinstance(row, dict)])
    navigator["requirement_matrix"] = rows
    projected["aidlc_answers"] = copy.deepcopy(revision.get("aidlc_answers", {}))
    projected["aidlc_revision_artifact"] = resolved_revision.relative_to(root).as_posix()

    scenarios: list[dict[str, Any]] = []
    for row in rows:
        requirement_id = str(row.get("display_id") or row.get("requirement_uid") or "")
        behavior = row.get("behavior_contract", {}) if isinstance(row.get("behavior_contract"), dict) else {}
        for scenario in behavior.get("scenarios", []) or []:
            if not isinstance(scenario, dict):
                continue
            projected_scenario = copy.deepcopy(scenario)
            projected_scenario["requirement_ids"] = list(dict.fromkeys([
                *[str(value) for value in projected_scenario.get("requirement_ids", []) if str(value)],
                requirement_id,
            ]))
            scenarios.append(projected_scenario)
    if scenarios:
        behaviour_plan = projected.get("behaviour_plan", {})
        if not isinstance(behaviour_plan, dict):
            behaviour_plan = {}
        behaviour_plan["selected"] = True
        behaviour_plan["scenarios"] = scenarios
        projected["behaviour_plan"] = behaviour_plan

    approved_tiers = sorted({
        str(tier)
        for row in rows
        for tier in ((row.get("validation_contract", {}) or {}).get("tiers", []) or [])
        if str(tier)
    })
    boundary = navigator.get("host_proof_boundary", {})
    if isinstance(boundary, dict):
        boundary["allowed_tiers"] = approved_tiers
        boundary["source"] = "validated-aidlc-correction-projection"
        navigator["host_proof_boundary"] = boundary
        navigator.pop("host_proof_boundary_conflict", None)

    REVISION._rebuild_proof_projections(projected, rows)
    return projected


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
        result = audit_report(root, run_id, report, pending=True)
    else:
        report_path = root / state["active_report"]
        payload = LOCK.read(report_path)
        report = _validated_aidlc_revision_report(root, run_id, payload["report"])
        result = audit_report(root, run_id, report)
    LOCK.L.append_event(root, run_id, "planning_audit_completed", {
        "status": result["status"],
        "finding_count": len(result.get("findings", [])),
        "total_review_cycles": result.get("review_cycles_summary", {}).get("total_review_cycles", 1),
        "revision_cycles": result.get("review_cycles_summary", {}).get("revision_cycles", 0),
    })
    return result


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
