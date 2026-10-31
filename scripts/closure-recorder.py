#!/usr/bin/env python3
"""Phase 1: persist validated execution facts as local TailTrail closure evidence.

The recorder never executes the commands in its input. It accepts only the
Phase 0 contract, requires an approved Planning Lock, and writes receipts,
checkpoint, gate, and review artifacts for that same run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, script: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = load("closure_recorder_ledger", "run-ledger.py")
CONTRACT = load("closure_recorder_contract", "closure-contract.py")
LOCK = load("closure_recorder_lock", "planning_lock.py")
CHECKPOINT = load("closure_recorder_checkpoint", "harness-checkpoint.py")
REVIEW = load("closure_recorder_review", "completion-review.py")
GATE = load("closure_recorder_gate", "requirement-completion.py")
EVIDENCE = load("closure_recorder_evidence", "execution-evidence.py")
ANCHOR = load("closure_recorder_anchor", "change-intent-anchor.py")
POLICY = load("closure_recorder_policy", "completion-policy.py")


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def receipt_rows(validated: dict[str, Any], record_id: str) -> list[dict[str, Any]]:
    return [{
        "schema_version": "2", "type": "tailtrail-validation-evidence-receipt",
        "requirement_uids": receipt["requirement_uids"],
        "tiers": receipt.get("tiers", [receipt["tier"]]),
        "scenario_ids": receipt.get("scenario_ids", []),
        "tier": receipt["tier"], "command": receipt["command"],
        "command_label": receipt["command_label"], "outcome": receipt["outcome"],
        "environment": receipt["environment"], "asserted_behavior": receipt["asserted_behavior"],
        "artifact_path": receipt.get("artifact", ""), "evidence_label": receipt["evidence_label"],
        "evidence_quality": receipt.get("evidence_quality", "declared"),
        **{key: receipt[key] for key in (
            "collector", "exit_code", "started_at", "finished_at", "duration_ms",
            "stdout_artifact", "stderr_artifact", "stdout_sha256", "stderr_sha256",
            "plan_fingerprint", "revision_overlay_uids",
        ) if key in receipt},
        "closure_record_id": record_id,
    } for receipt in validated["receipts"]]


def selected_harnesses(root: Path, run_id: str) -> list[str]:
    path = L.state_dir(root, run_id) / "planning" / "execution-handoff-v1.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    closure = payload.get("closure", {}) if isinstance(payload, dict) else {}
    return [str(item) for item in closure.get("selected_harnesses", []) if isinstance(item, str)]


def current_plan_fingerprint(root: Path, run_id: str) -> str:
    """Fingerprint the currently approved effective plan for custody checks.

    Unions the frozen anchor with the active revision overlay and accepted
    additive amendments -- the same effective contracts execution stamps on
    receipts. A receipt stamped with any other fingerprint is stale.
    """
    _, anchor = ANCHOR.latest_approved(root, run_id)
    requirements = {
        str(row.get("requirement_uid")): row
        for row in anchor.get("requirements", [])
        if isinstance(row, dict) and row.get("requirement_uid")
    }
    overlay = EVIDENCE._approved_revision_overlay(root, run_id)
    amendments, _ = approved_proof_amendments(root, run_id, requirements)
    merged = {
        uid_key: {
            "commands": sorted(
                set(overlay.get(uid_key, {}).get("commands", []))
                | {str(row.get("command", "")) for row in amendments.get(uid_key, [])
                   if str(row.get("command", "")).strip()}
            ),
            "tiers": sorted(
                set(overlay.get(uid_key, {}).get("tiers", []))
                | {str(value) for row in amendments.get(uid_key, []) for value in row.get("tiers", [])
                   if str(value).strip()}
            ),
        }
        for uid_key in set(requirements) | set(overlay) | set(amendments)
    }
    return ANCHOR.approved_plan_fingerprint(
        ANCHOR.effective_plan_contracts(requirements, merged),
        requirements_data=requirements
    )


def partition_plan_receipts(
    receipts: list[dict[str, Any]], current_fingerprint: str,
) -> dict[str, list[dict[str, Any]]]:
    """Split closure receipts by plan custody: current, legacy, or stale.

    Legacy receipts predate fingerprint stamping and keep historical
    behavior. Stale receipts (a different fingerprint) are excluded from
    pass aggregation: the plan changed under them, so their tiers need
    re-proof against the approved plan, not inheritance.
    """
    current = [r for r in receipts if isinstance(r, dict) and r.get("plan_fingerprint") == current_fingerprint]
    legacy = [r for r in receipts if isinstance(r, dict) and not r.get("plan_fingerprint")]
    stale = [r for r in receipts if isinstance(r, dict) and r.get("plan_fingerprint") and r.get("plan_fingerprint") != current_fingerprint]
    return {"current": current, "legacy": legacy, "stale": stale}


def artifact_pointer(root: Path, path: Path) -> str:
    """Keep local records portable when their input lives beneath the project."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def approved_proof_amendments(root: Path, run_id: str, requirements: dict[str, dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], str | None]:
    """Load only valid, requirement-bound additive proof amendments."""
    path = L.state_dir(root, run_id) / "execution" / "proof-amendments.jsonl"
    if not path.is_file():
        return {}, None
    accepted: dict[str, list[dict[str, Any]]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}, None
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict) or item.get("type") != "tailtrail-proof-amendment":
            continue
        uid = str(item.get("requirement_uid", ""))
        command = str(item.get("command", ""))
        tiers = [str(value) for value in item.get("tiers", []) if str(value)]
        reason = str(item.get("reason", "")).strip()
        fingerprint = str(item.get("command_fingerprint", ""))
        if (
            item.get("run_id") != run_id
            or item.get("approved") is not True
            or uid not in requirements
            or not command.strip()
            or not tiers
            or not reason
            or fingerprint != hashlib.sha256(command.encode("utf-8")).hexdigest()
        ):
            continue
        accepted.setdefault(uid, []).append(item)
    return accepted, path.relative_to(root).as_posix()


RECEIPT_FIELDS = (
    "requirement_uids", "tier", "tiers", "scenario_ids", "command_label", "command",
    "outcome", "environment", "asserted_behavior", "artifact", "evidence_label",
    "collector", "evidence_quality", "exit_code", "started_at", "finished_at",
    "duration_ms", "stdout_artifact", "stderr_artifact", "stdout_sha256", "stderr_sha256",
    "plan_fingerprint", "revision_overlay_uids",
)


def receipt_tiers(item: dict[str, Any]) -> list[str]:
    """Return the explicit tier set without inventing a missing binding."""
    values = item.get("tiers", [item.get("tier")])
    return sorted({str(value) for value in values if str(value)}) if isinstance(values, list) else []


def evidence_stream_version(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Fingerprint the append-only evidence stream for downstream freshness checks."""
    identities = [
        {
            "sequence": int(item.get("sequence", index)),
            "fingerprint": str(item.get("fingerprint", "")),
            "kind": str(item.get("kind", "")),
        }
        for index, item in enumerate(events, start=1)
        if isinstance(item, dict)
    ]
    payload = canonical(identities).encode("utf-8")
    head = identities[-1] if identities else {}
    return {
        "schema_version": "1",
        "type": "tailtrail-evidence-stream-version",
        "event_count": len(identities),
        "head_sequence": head.get("sequence"),
        "head_fingerprint": head.get("fingerprint") or None,
        "fingerprint": "sha256:" + hashlib.sha256(payload).hexdigest(),
    }


def event_identity(item: dict[str, Any], fallback_sequence: int) -> dict[str, Any]:
    sequence = item.get("sequence", fallback_sequence)
    try:
        sequence = int(sequence)
    except (TypeError, ValueError):
        sequence = fallback_sequence
    fingerprint = str(item.get("fingerprint", ""))
    return {
        "sequence": sequence,
        "fingerprint": fingerprint,
        "event_id": f"evidence-{sequence}-{fingerprint or 'unfingerprinted'}",
    }


def valid_managed_pair(
    item: dict[str, Any], requirements: dict[str, dict[str, Any]],
    amendments: dict[str, list[dict[str, Any]]],
    revision_overlay: dict[str, dict[str, list[str]]],
) -> bool:
    """Accept only approved command/tier pairs for managed command receipts."""
    if item.get("kind") != "command-result":
        return True
    command = str(item.get("command", ""))
    tiers = set(receipt_tiers(item))
    uids = [str(value) for value in item.get("requirement_uids", []) if str(value)]
    if not command or not tiers or not uids:
        return False
    for uid in uids:
        row = requirements.get(uid)
        contract = row.get("validation_contract", {}) if isinstance(row, dict) else {}
        approved_commands = {str(value) for value in contract.get("commands", []) if str(value)}
        approved_commands.update(revision_overlay.get(uid, {}).get("commands", []))
        checks = [value for value in contract.get("checks", []) if isinstance(value, dict)]
        matching = [value for value in checks if str(value.get("command", "")) == command]
        approved_tiers = {
            str(value) for check in matching for value in check.get("tiers", []) if str(value)
        } or {str(value) for value in contract.get("tiers", []) if str(value)}
        approved_tiers.update(revision_overlay.get(uid, {}).get("tiers", []))
        additive = [row for row in amendments.get(uid, []) if row.get("command") == command]
        amended_tiers = {
            str(value) for row in additive for value in row.get("tiers", []) if str(value)
        }
        allowed_commands = approved_commands | ({command} if additive else set())
        allowed_tiers = approved_tiers | amended_tiers
        if allowed_commands and (command not in allowed_commands or not tiers <= allowed_tiers):
            return False
    return True


def source_stale(item: dict[str, Any], events: list[dict[str, Any]], fallback_sequence: int) -> bool:
    """Reject a proof when a later linked source edit changed its declared paths."""
    identity = event_identity(item, fallback_sequence)
    paths = {str(path) for path in item.get("changed_paths", []) if str(path)}
    uids = {str(uid) for uid in item.get("requirement_uids", []) if str(uid)}
    if not paths or not uids:
        return False
    for index, candidate in enumerate(events, start=1):
        if not isinstance(candidate, dict) or candidate.get("kind") != "source-edit":
            continue
        if event_identity(candidate, index)["sequence"] <= identity["sequence"]:
            continue
        changed = {str(path) for path in candidate.get("changed_paths", []) if str(path)}
        changed_uids = {str(uid) for uid in candidate.get("requirement_uids", []) if str(uid)}
        if paths & changed and uids & changed_uids:
            return True
    return False


def validation_evidence_projection(root: Path, run_id: str) -> dict[str, Any]:
    """Project current proof decisions without deleting append-only attempt history.

    Selection is per requirement, command, and tier. A valid later retry wins
    only for that exact binding; a plan-stale, source-stale, or unapproved
    event remains visible as rejected history and cannot replace current proof.
    """
    events = EVIDENCE.show(root, run_id)["events"]
    _, anchor = ANCHOR.latest_approved(root, run_id)
    requirements = {
        str(row.get("requirement_uid")): row for row in anchor.get("requirements", [])
        if isinstance(row, dict) and row.get("requirement_uid")
    }
    amendments, _ = approved_proof_amendments(root, run_id, requirements)
    revision_overlay = EVIDENCE._approved_revision_overlay(root, run_id)
    current_plan = current_plan_fingerprint(root, run_id)
    attempts: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    rejected: list[dict[str, Any]] = []

    for index, item in enumerate(events, start=1):
        if not isinstance(item, dict) or item.get("kind") not in {"command-result", "ci-receipt"}:
            continue
        identity = event_identity(item, index)
        if not valid_managed_pair(item, requirements, amendments, revision_overlay):
            rejected.append({**identity, "reason": "unapproved-command-tier-binding"})
            continue
        stamped_plan = str(item.get("plan_fingerprint", ""))
        if stamped_plan and stamped_plan != current_plan:
            rejected.append({**identity, "reason": "superseded-plan-fingerprint"})
            continue
        if source_stale(item, events, index):
            rejected.append({**identity, "reason": "source-changed-after-proof"})
            continue
        command = str(item.get("command", ""))
        tiers = receipt_tiers(item)
        for uid in sorted({str(value) for value in item.get("requirement_uids", []) if str(value)}):
            for tier in tiers:
                attempts.setdefault((uid, command, tier), []).append({"item": item, "identity": identity})

    selected: dict[tuple[str, str, str], dict[str, Any]] = {}
    bindings: list[dict[str, Any]] = []
    for key in sorted(attempts):
        history = sorted(attempts[key], key=lambda row: (row["identity"]["sequence"], row["identity"]["fingerprint"]))
        winner = history[-1]
        selected[key] = winner
        winner_identity = winner["identity"]
        history_rows = [{
            **row["identity"],
            "outcome": row["item"].get("outcome"),
            "evidence_quality": row["item"].get("evidence_quality", "declared"),
            "status": "current" if row is winner else "superseded",
            **({
                "superseded_by_event_id": winner_identity["event_id"],
                "superseded_by_sequence": winner_identity["sequence"],
            } if row is not winner else {}),
        } for row in history]
        uid, command, tier = key
        binding_id = hashlib.sha256(canonical({"requirement_uid": uid, "command": command, "tier": tier, "plan_fingerprint": current_plan}).encode("utf-8")).hexdigest()[:16]
        bindings.append({
            "binding_id": f"proof-{binding_id}",
            "requirement_uid": uid,
            "command": command,
            "command_fingerprint": "sha256:" + hashlib.sha256(command.encode("utf-8")).hexdigest(),
            "tier": tier,
            "plan_fingerprint": current_plan,
            "selected_attempt": history_rows[-1],
            "attempts": history_rows,
        })

    grouped: dict[tuple[int, str], dict[str, Any]] = {}
    for (uid, _command, tier), winner in selected.items():
        item = winner["item"]
        identity = winner["identity"]
        group = grouped.setdefault((identity["sequence"], identity["fingerprint"]), {
            "item": item, "requirement_uids": set(), "tiers": set(),
        })
        group["requirement_uids"].add(uid)
        group["tiers"].add(tier)
    receipts: list[dict[str, Any]] = []
    for group_key in sorted(grouped):
        group = grouped[group_key]
        receipt = {**group["item"], "requirement_uids": sorted(group["requirement_uids"]), "tiers": sorted(group["tiers"])}
        if receipt["tiers"]:
            receipt["tier"] = receipt["tiers"][0]
        receipts.append(receipt)

    return {
        "schema_version": "1",
        "type": "tailtrail-current-validation-evidence-projection",
        "run_id": run_id,
        "plan_fingerprint": current_plan,
        "stream_version": evidence_stream_version(events),
        "bindings": bindings,
        "selected_receipts": receipts,
        "rejected_attempts": rejected,
        "boundary": "Selection is computed from append-only saved evidence; superseded and rejected attempts remain available for audit and diagnosis.",
    }


def collected_input(root: Path, run_id: str) -> dict[str, Any]:
    """Build closure-contract input from the current validation projection."""
    projection = validation_evidence_projection(root, run_id)
    receipts = [{key: item[key] for key in RECEIPT_FIELDS if key in item} for item in projection["selected_receipts"]]
    saved = EVIDENCE.show(root, run_id)["events"]
    paths = sorted({path for item in saved for path in item.get("changed_paths", [])})
    return {"schema_version": "1", "type": "tailtrail-execution-closure-input", "run_id": run_id, "changed_paths": paths, "receipts": receipts}


def record(root: Path, input_path: Path | None = None, run_id: str | None = None) -> dict[str, Any]:
    if input_path is None and not run_id:
        raise ValueError("closure record needs --input or --run-id for saved execution evidence")
    source = json.loads(input_path.read_text(encoding="utf-8")) if input_path else collected_input(root, str(run_id))
    validated = CONTRACT.validate_input(root, source)
    run_id = validated["run_id"]
    LOCK.assert_write_allowed(root, run_id)
    directory = L.state_dir(root, run_id)
    record_id = "closure-" + hashlib.sha256(canonical(validated).encode("utf-8")).hexdigest()[:16]
    records = directory / "closure-records"
    record_path = records / f"{record_id}.json"
    if record_path.is_file():
        saved = json.loads(record_path.read_text(encoding="utf-8"))
        current_policy = POLICY.evaluate(root, run_id, validated["changed_paths"])
        if saved.get("completion_policy") == current_policy:
            return {**saved, "reused": True}
        refreshed = {**saved, "completion_policy": current_policy}
        L.atomic_json(record_path, refreshed)
        L.append_event(root, run_id, "closure_policy_refreshed", {"record_id": record_id, "artifact": record_path.relative_to(root).as_posix(), "policy_status": current_policy.get("status")})
        return {**refreshed, "reused": True, "policy_refreshed": True}

    normalized_receipts = receipt_rows(validated, record_id)
    amendment_path = L.state_dir(root, run_id) / "execution" / "proof-amendments.jsonl"
    amendment_artifact = amendment_path.relative_to(root).as_posix() if amendment_path.is_file() else None
    if amendment_artifact:
        for receipt in normalized_receipts:
            receipt["proof_amendment_artifact"] = amendment_artifact
    receipts_path = records / f"{record_id}-receipts.json"
    results_path = records / f"{record_id}-results.json"
    L.atomic_json(receipts_path, {"receipts": normalized_receipts})
    L.atomic_json(results_path, {"results": [{
        key: item[key] for key in (
            "requirement_uids", "tier", "tiers", "scenario_ids", "command_label", "command",
            "outcome", "environment", "asserted_behavior", "evidence_label", "evidence_quality",
            "artifact", "collector", "exit_code", "started_at", "finished_at", "duration_ms",
            "stdout_artifact", "stderr_artifact", "stdout_sha256", "stderr_sha256",
        ) if key in item
    } for item in validated["receipts"]]})
    receipt_dir = directory / "validation-receipts"
    receipt_artifacts: list[str] = []
    for index, item in enumerate(normalized_receipts, start=1):
        path = receipt_dir / f"{record_id}-{index}.json"
        L.atomic_json(path, item)
        receipt_artifacts.append(path.relative_to(root).as_posix())
    checkpoint = CHECKPOINT.checkpoint(root, run_id, validated["changed_paths"], results_path)
    review = REVIEW.review(root, run_id)
    gate = GATE.gate(root, run_id, receipts_path)
    completion_policy = POLICY.evaluate(root, run_id, validated["changed_paths"])
    selected = selected_harnesses(root, run_id)
    outstanding = [name for name in selected if name in {"Architecture Fitness Harness", "Behaviour Harness", "Maintainability Harness"}]
    next_action = ("Run the selected harness assessments: " + ", ".join(outstanding) + "; then run tailtrail completion-report." if outstanding else "Run tailtrail completion-report for this run.")
    payload = {
        "schema_version": "1", "type": "tailtrail-closure-record", "record_id": record_id, "run_id": run_id,
        "validated_input": artifact_pointer(root, input_path) if input_path else "execution/evidence-stream.jsonl", "changed_paths": validated["changed_paths"],
        "receipt_artifacts": receipt_artifacts, "checkpoint": checkpoint["path"], "completion_review": review,
        "completion_gate": gate, "selected_harnesses": selected, "next_action": next_action,
        "completion_policy": completion_policy,
        "proof_amendment_artifact": amendment_artifact,
        "boundary": "Recorded validated evidence. Managed-command receipts were executed and captured by TailTrail; declared host receipts remain explicitly unverified.",
    }
    L.atomic_json(record_path, payload)
    L.append_event(root, run_id, "closure_recorded", {"record_id": record_id, "artifact": record_path.relative_to(root).as_posix(), "receipt_count": len(normalized_receipts), "checkpoint": checkpoint["checkpoint"], "gate_complete": gate["complete"], "review_complete": review["complete"]})
    return {**payload, "reused": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        if args.input is None and not args.run_id:
            raise ValueError("closure record needs --input or --run-id")
        print(json.dumps(record(args.root.resolve(), args.input.resolve() if args.input else None, args.run_id), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Closure recorder error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
