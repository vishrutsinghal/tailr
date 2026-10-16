#!/usr/bin/env python3
"""Append and inspect sanitized, requirement-linked execution evidence."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"source-edit", "command-result", "harness-result", "drift-finding", "ci-receipt"}


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module


L = load("execution_evidence_ledger", "run-ledger.py")
LOCK = load("execution_evidence_lock", "planning_lock.py")
CONTRACT = load("execution_evidence_contract", "closure-contract.py")
ANCHOR = load("execution_evidence_anchor", "change-intent-anchor.py")


def directory(root: Path, run_id: str) -> Path: return L.state_dir(root, run_id) / "execution"
def stream(root: Path, run_id: str) -> Path: return directory(root, run_id) / "evidence-stream.jsonl"
def proof_amendments(root: Path, run_id: str) -> Path: return directory(root, run_id) / "proof-amendments.jsonl"
def canonical(value: Any) -> str: return json.dumps(value, sort_keys=True, separators=(",", ":"))


def append_proof_amendment(
    root: Path,
    run_id: str,
    requirement_uid: str,
    command: str,
    tiers: list[str],
    reason: str,
) -> dict[str, Any]:
    if not isinstance(command, str) or not command.strip():
        raise ValueError("proof amendment requires a non-empty command; pass `tailtrail execution-evidence run --root . --run-id <run-id> --command \"<non-empty command>\" --amend-proof --amendment-reason \"<reason>\" --approved`")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("proof amendment requires a non-empty reason; pass `tailtrail execution-evidence run --root . --run-id <run-id> --amend-proof --amendment-reason \"<reason>\" --approved`")
    normalized = {
        "schema_version": "1",
        "type": "tailtrail-proof-amendment",
        "run_id": run_id,
        "requirement_uid": requirement_uid,
        "command": command,
        "command_fingerprint": hashlib.sha256(command.encode("utf-8")).hexdigest(),
        "tiers": sorted(set(tiers)),
        "reason": CONTRACT.short_text(reason, "proof amendment reason"),
        "approved": True,
        "created_at": L.utc_now(),
        "boundary": "Additive proof authorization only; it does not change the immutable anchor or production scope.",
    }
    path = proof_amendments(root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical(normalized) + "\n")
    return normalized


def validate(root: Path, run_id: str, event: Any) -> dict[str, Any]:
    if not isinstance(event, dict): raise ValueError("execution evidence must be a JSON object; record it with `tailtrail execution-evidence record --root . --run-id <run-id> --event '<json>' --approved`")
    allowed = {
        "kind", "requirement_uids", "changed_paths", "tier", "tiers", "scenario_ids",
        "command_label", "command", "outcome", "environment", "asserted_behavior",
        "artifact", "evidence_label", "classification", "collector", "evidence_quality",
        "exit_code", "started_at", "finished_at", "duration_ms", "stdout_artifact",
        "stderr_artifact", "stdout_sha256", "stderr_sha256", "revision_overlay_uids",
        "plan_fingerprint",
    }
    unknown = set(event) - allowed
    if unknown: raise ValueError(f"execution evidence has unsupported fields: {', '.join(sorted(unknown))}; record it with `tailtrail execution-evidence record --root . --run-id <run-id> --event '<json>' --approved`")
    kind = event.get("kind")
    if kind not in KINDS: raise ValueError("execution evidence kind is not supported; record it with `tailtrail execution-evidence record --root . --run-id <run-id> --event '<json>' --approved`")
    known = CONTRACT.approved_requirement_uids(root, run_id)
    uids = event.get("requirement_uids")
    if not isinstance(uids, list) or not uids or not all(isinstance(item, str) for item in uids): raise ValueError("requirement_uids must be a non-empty string list; record it with `tailtrail execution-evidence record --root . --run-id <run-id> --event '<json>' --approved`")
    if set(uids) - known: raise ValueError("execution evidence references unknown approved requirement UID(s); use a UID from the approved anchor (check `tailtrail planning show --root . --run-id <run-id>`)")
    changed = event.get("changed_paths", [])
    if not isinstance(changed, list) or not all(isinstance(item, str) for item in changed): raise ValueError("changed_paths must be a path list; record it with `tailtrail execution-evidence record --root . --run-id <run-id> --event '<json>' --approved`")
    normalized = {"schema_version": "2", "type": "tailtrail-execution-evidence", "run_id": run_id, "kind": kind, "requirement_uids": sorted(set(uids)), "changed_paths": sorted({CONTRACT.repository_path(item, "changed_paths item") for item in changed}), "evidence_boundary": "Host-supplied execution fact. TailTrail did not execute, reinterpret, or infer this event."}
    if kind == "source-edit" and not normalized["changed_paths"]: raise ValueError("source-edit evidence requires at least one changed path; record it with `tailtrail execution-evidence record --root . --run-id <run-id> --event '<json>' --approved`")
    if kind in {"command-result", "ci-receipt"}:
        receipt = CONTRACT.validate_receipt({key: event[key] for key in (
            "requirement_uids", "tier", "tiers", "scenario_ids", "command_label", "command",
            "outcome", "environment", "asserted_behavior", "artifact", "evidence_label",
            "collector", "evidence_quality", "exit_code", "started_at", "finished_at",
            "duration_ms", "stdout_artifact", "stderr_artifact", "stdout_sha256", "stderr_sha256",
            "plan_fingerprint",
        ) if key in event}, known, 0, root)
        normalized.update(receipt)
        if receipt.get("evidence_label") == "managed-command":
            normalized["evidence_boundary"] = "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts."
    if kind in {"harness-result", "drift-finding"}:
        normalized["classification"] = CONTRACT.short_text(event.get("classification"), "classification")
    return normalized


def _redact(value: str, limit: int = 262144) -> str:
    """Persist bounded command output while masking common credential forms."""
    bounded = value[:limit]
    patterns = (
        r"(?i)(authorization\s*:\s*(?:bearer\s+)?)[^\s]+",
        r"(?i)((?:password|passwd|secret|token|api[_-]?key)\s*[=:]\s*)[^\s]+",
    )
    for pattern in patterns:
        bounded = re.sub(pattern, r"\1[REDACTED]", bounded)
    if len(value) > limit:
        bounded += f"\n[output truncated: {len(value) - limit} additional characters]"
    return bounded


def _anchor_requirements(root: Path, run_id: str) -> dict[str, dict[str, Any]]:
    try:
        _, anchor = ANCHOR.latest_approved(root, run_id)
    except (OSError, ValueError):
        raise ValueError(f"approved anchor for run `{run_id}` does not exist; activate the run first with `tailtrail planning activate --root . --run-id {run_id} --approved`")
    return {
        str(row.get("requirement_uid")): row
        for row in anchor.get("requirements", [])
        if isinstance(row, dict) and row.get("requirement_uid")
    }


def _approved_revision_overlay(root: Path, run_id: str) -> dict[str, dict[str, list[str]]]:
    """Union approved-revision proof content over the frozen anchor.

    The anchor is immutable, so post-approval proof amendments (Shape A:
    proof-update commands recorded through an approved plan revision) would
    otherwise never reach managed execution. This overlay reads the ACTIVE
    revision snapshot only — pending proposals grant nothing — and unions
    its per-requirement commands/tiers over the anchor's. Missing state,
    missing snapshots, or malformed rows yield no overlay (never a failure):
    the anchor alone still authorizes everything it always did.
    """
    try:
        state = LOCK.revision_state(root.resolve(), run_id)
    except (OSError, ValueError):
        return {}
    try:
        active = int(state.get("active_revision", 1))
    except (TypeError, ValueError):
        return {}
    if active <= 1:
        return {}
    relative = state.get("active_report")
    if not isinstance(relative, str) or not relative:
        return {}
    snapshot_path = root.resolve() / relative
    if not snapshot_path.is_file():
        return {}
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    navigator = (snapshot.get("report", {}) or {}).get("navigator", {})
    rows = navigator.get("requirement_matrix", []) if isinstance(navigator, dict) else []
    overlay: dict[str, dict[str, list[str]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        uid = str(row.get("requirement_uid", ""))
        contract = row.get("validation_contract", {})
        if not uid or not isinstance(contract, dict):
            continue
        commands = sorted({str(value).strip() for value in contract.get("commands", []) if str(value).strip()})
        tiers = sorted({str(value).strip() for value in contract.get("tiers", []) if str(value).strip()})
        if commands or tiers:
            overlay[uid] = {"commands": commands, "tiers": tiers}
    return overlay


def run_command(
    root: Path,
    run_id: str,
    requirement_uids: list[str],
    tiers: list[str],
    command: str,
    command_label: str,
    changed_paths: list[str],
    approved: bool,
    timeout_seconds: int = 900,
    amend_proof: bool = False,
    amendment_reason: str = "",
) -> dict[str, Any]:
    """Execute one exact approved proof command and atomically capture its facts."""
    if approved is not True:
        raise ValueError(f"managed execution requires --approved; run `tailtrail execution-evidence run --approved --root . --run-id {run_id} --requirement <uid> --tier <tier> --label <label> --command <cmd>`")
    root = root.resolve()
    LOCK.assert_write_allowed(root, run_id)
    requirements = _anchor_requirements(root, run_id)
    overlay = _approved_revision_overlay(root, run_id)
    selected = []
    revision_overlaid: list[str] = []
    amended: dict[str, dict[str, set[str]]] = {}
    for uid in sorted(set(requirement_uids)):
        row = requirements.get(uid)
        if row is None:
            raise ValueError(f"managed execution references unknown approved requirement `{uid}`; use a UID from the approved anchor (check `tailtrail planning show --root . --run-id {run_id}`)")
        contract = row.get("validation_contract", {}) if isinstance(row.get("validation_contract"), dict) else {}
        approved_commands = {str(value) for value in contract.get("commands", []) if str(value)}
        approved_tiers = {str(value) for value in contract.get("tiers", []) if str(value)}
        revision_commands = set(overlay.get(uid, {}).get("commands", []))
        revision_tiers = set(overlay.get(uid, {}).get("tiers", []))
        if revision_commands or revision_tiers:
            revision_overlaid.append(uid)
        approved_commands |= revision_commands
        approved_tiers |= revision_tiers
        checks = [value for value in contract.get("checks", []) if isinstance(value, dict)]
        matching_checks = [value for value in checks if str(value.get("command", "")) == command]
        if matching_checks:
            # A checks[] entry narrows this exact command's trusted tiers (by
            # design, so one proof command can't silently cover another's tier).
            # Union only with revision-added tiers, never the full top-level set,
            # so a later proof-update revision's tiers still apply even though
            # revisions never rewrite checks[] itself (Issue 27).
            check_tiers = {
                str(value)
                for check in matching_checks
                for value in check.get("tiers", [])
                if str(value)
            }
            approved_tiers = check_tiers | revision_tiers
        missing_command = command not in approved_commands
        missing_tiers = not set(tiers) or set(tiers) - approved_tiers
        if (missing_command or missing_tiers) and amend_proof:
            if not tiers:
                raise ValueError(f"proof amendment requires at least one tier; pass `tailtrail execution-evidence run --root . --run-id {run_id} --tier <tier> --amend-proof --amendment-reason \"<reason>\" --approved`")
            append_proof_amendment(root, run_id, uid, command, tiers, amendment_reason)
            approved_commands.add(command)
            approved_tiers.update(tiers)
            amended.setdefault(uid, {"commands": set(), "tiers": set()})
            amended[uid]["commands"].add(command)
            amended[uid]["tiers"].update(tiers)
        if command not in approved_commands:
            raise ValueError(f"command is not approved for requirement `{uid}`; revise the plan with `tailtrail planning revise --root . --run-id {run_id} --changes '<json>' --approved-proposal` before execution")
        if not set(tiers) or set(tiers) - approved_tiers:
            raise ValueError(f"requested evidence tiers are not approved for requirement `{uid}`; use only approved tiers (check `tailtrail planning show --root . --run-id {run_id}`)")
        selected.append(row)
    if not selected:
        raise ValueError(f"managed execution requires at least one approved requirement; pass `--requirement <approved-uid>` from `tailtrail planning show --root . --run-id {run_id}`")
    merged_overlay = {
        uid_key: {
            "commands": sorted(set(overlay.get(uid_key, {}).get("commands", [])) | amended.get(uid_key, {}).get("commands", set())),
            "tiers": sorted(set(overlay.get(uid_key, {}).get("tiers", [])) | amended.get(uid_key, {}).get("tiers", set())),
        }
        for uid_key in set(overlay) | set(amended)
    }
    plan_fingerprint = ANCHOR.approved_plan_fingerprint(ANCHOR.effective_plan_contracts(requirements, merged_overlay))
    if not isinstance(timeout_seconds, int) or timeout_seconds < 1 or timeout_seconds > 3600:
        raise ValueError("timeout must be between 1 and 3600 seconds; pass `--timeout <1-3600>` to `tailtrail execution-evidence run --approved`")

    scenario_ids = sorted({
        str(scenario.get("scenario_id"))
        for row in selected
        for scenario in ((row.get("behavior_contract", {}) or {}).get("scenarios", []))
        if isinstance(scenario, dict) and scenario.get("scenario_id")
        and any(str(item.get("tier")) in set(tiers) for item in scenario.get("evidence", []) if isinstance(item, dict))
    })
    asserted = "; ".join(
        str(scenario.get("expected_outcome"))
        for row in selected
        for scenario in ((row.get("behavior_contract", {}) or {}).get("scenarios", []))
        if isinstance(scenario, dict) and scenario.get("scenario_id") in scenario_ids and scenario.get("expected_outcome")
    ) or "; ".join(str(row.get("statement")) for row in selected)

    started = datetime.now(timezone.utc)
    monotonic = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as error:
        timed_out = True
        exit_code = 124
        stdout = error.stdout.decode(errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
        stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
        stderr += f"\nTailTrail monitor timed out after {timeout_seconds} seconds."
    finished = datetime.now(timezone.utc)
    duration_ms = int((time.monotonic() - monotonic) * 1000)
    stdout = _redact(stdout)
    stderr = _redact(stderr)
    artifact_root = directory(root, run_id) / "command-artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256(f"{command}\0{started.isoformat()}".encode()).hexdigest()[:16]
    prefix = artifact_root / f"command-{identity}"
    stdout_path = prefix.with_suffix(".stdout.txt")
    stderr_path = prefix.with_suffix(".stderr.txt")
    result_path = prefix.with_suffix(".json")
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    outcome = "timed-out" if timed_out else ("pass" if exit_code == 0 else "fail")
    relative_stdout = stdout_path.relative_to(root).as_posix()
    relative_stderr = stderr_path.relative_to(root).as_posix()
    relative_result = result_path.relative_to(root).as_posix()
    event = {
        "kind": "command-result",
        "requirement_uids": sorted(set(requirement_uids)),
        "changed_paths": changed_paths,
        "tiers": list(dict.fromkeys(tiers)),
        "scenario_ids": scenario_ids,
        "command_label": command_label,
        "command": command,
        "outcome": outcome,
        "revision_overlay_uids": sorted(revision_overlaid),
        "plan_fingerprint": plan_fingerprint,
        "environment": f"{platform.system()} {platform.machine()} Python {platform.python_version()}",
        "asserted_behavior": asserted,
        "artifact": relative_result,
        "evidence_label": "managed-command",
        "collector": "tailtrail-managed-execution-v2",
        "evidence_quality": "trusted",
        "exit_code": exit_code,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_ms": duration_ms,
        "stdout_artifact": relative_stdout,
        "stderr_artifact": relative_stderr,
        "stdout_sha256": "sha256:" + hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": "sha256:" + hashlib.sha256(stderr.encode()).hexdigest(),
    }
    # Timeout is represented as a non-zero managed command result while the
    # monitor response retains the more specific operator-facing status.
    saved = append(root, run_id, event, True)
    result = {
        "schema_version": "2", "type": "tailtrail-managed-command-result",
        "run_id": run_id, "command": command, "command_label": command_label,
        "requirement_uids": sorted(set(requirement_uids)), "tiers": list(dict.fromkeys(tiers)),
        "scenario_ids": scenario_ids, "outcome": outcome, "exit_code": exit_code,
        "plan_fingerprint": plan_fingerprint,
        "started_at": started.isoformat(), "finished_at": finished.isoformat(),
        "duration_ms": duration_ms, "stdout_artifact": relative_stdout,
        "stderr_artifact": relative_stderr, "evidence_fingerprint": saved["fingerprint"],
        "boundary": "The command matched the approved validation contract or an explicitly approved additive amendment and was executed by TailTrail with bounded, redacted output capture.",
    }
    L.atomic_json(result_path, result)
    return result


def append(root: Path, run_id: str, event: Any, approved: bool) -> dict[str, Any]:
    if approved is not True: raise ValueError("execution evidence recording requires --approved; run `tailtrail execution-evidence record --root . --run-id <run-id> --event '<json>' --approved`")
    root = root.resolve(); LOCK.assert_write_allowed(root, run_id)
    normalized = validate(root, run_id, event); target = stream(root, run_id); target.parent.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(canonical(normalized).encode()).hexdigest()[:16]
    existing = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()] if target.is_file() else []
    prior = next((item for item in existing if item.get("fingerprint") == fingerprint), None)
    if prior: return {**prior, "reused": True, "artifact": target.relative_to(root).as_posix()}
    saved = {**normalized, "sequence": len(existing) + 1, "fingerprint": fingerprint}
    with target.open("a", encoding="utf-8", newline="\n") as handle: handle.write(canonical(saved) + "\n")
    index = {"schema_version": "1", "type": "tailtrail-execution-evidence-index", "run_id": run_id, "events": len(existing) + 1, "changed_paths": sorted({path for item in [*existing, saved] for path in item.get("changed_paths", [])}), "requirement_uids": sorted({uid for item in [*existing, saved] for uid in item.get("requirement_uids", [])}), "boundary": "Index of saved host-supplied evidence only; it does not evaluate completion."}
    L.atomic_json(target.parent / "receipt-index-v1.json", index)
    L.append_event(root, run_id, "execution_evidence_recorded", {"kind": saved["kind"], "fingerprint": fingerprint, "sequence": saved["sequence"], "artifact": target.relative_to(root).as_posix()})
    return {**saved, "reused": False, "artifact": target.relative_to(root).as_posix()}


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); target = stream(root, run_id)
    events = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()] if target.is_file() else []
    return {"schema_version": "1", "type": "tailtrail-execution-evidence-log", "run_id": run_id, "events": events, "count": len(events), "boundary": "Read-only saved host evidence. It does not run commands or assess completion."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    for command in ("record", "show", "run"):
        item = sub.add_parser(command); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if command == "record": item.add_argument("--event", required=True); item.add_argument("--approved", action="store_true")
        if command == "run":
            item.add_argument("--requirement", action="append", required=True)
            item.add_argument("--tier", action="append", required=True)
            item.add_argument("--changed", action="append", default=[])
            item.add_argument("--label", required=True)
            item.add_argument("--command", dest="proof_command", required=True)
            item.add_argument("--timeout", type=int, default=900)
            item.add_argument("--amend-proof", action="store_true", help="Append an explicit post-activation proof amendment.")
            item.add_argument("--amendment-reason", default="", help="Reason for an additive proof amendment.")
            item.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "record":
            result = append(args.root, args.run_id, json.loads(args.event), args.approved)
        elif args.command == "run":
            result = run_command(
                args.root, args.run_id, args.requirement, args.tier, args.proof_command,
                args.label, args.changed, args.approved, args.timeout,
                args.amend_proof, args.amendment_reason,
            )
        else:
            result = show(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, json.JSONDecodeError) as error: print(f"Execution evidence error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
