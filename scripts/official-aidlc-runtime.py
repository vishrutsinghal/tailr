#!/usr/bin/env python3
"""Attach a Full TailTrail run to official AI-DLC through ordered receipts.

This adapter never executes official-pack scripts. The host executes the pinned
workflow and supplies small, sanitized transition receipts. TailTrail validates
their identity, order, integrity, approved anchor, and stage prerequisites.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_VERSION = "v1"
STAGES = ("requirements", "design", "implementation", "build-and-test", "handoff", "operations")
ACTIONS = {"advance", "resume", "redo", "jump", "recovery"}
SESSION_RELATIVE = Path("aidlc-official") / "runtime" / "session-v1.json"
TRANSITIONS_RELATIVE = Path("aidlc-official") / "runtime" / "transitions"


def load(relative: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = load("scripts/run-ledger.py", "official_runtime_ledger")
DETECT = load("scripts/aidlc-official-detect.py", "official_runtime_detect")
STATE = load("scripts/official-aidlc-state.py", "official_runtime_state")
SAN = load("scripts/official-aidlc-sanitize.py", "official_runtime_sanitize")


def read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return payload


def run_dir(root: Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id:
        raise ValueError("run_id must be one local TailTrail run identifier")
    return L.state_dir(root.resolve(), run_id)


def canonical_digest(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "integrity"}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bridge(root: Path, run_id: str) -> tuple[dict[str, Any], Path]:
    path = run_dir(root, run_id) / "aidlc-official" / "bridge-v1.json"
    if not path.is_file():
        raise ValueError("runtime attachment requires a Full-mode official bridge")
    bridge = read(path)
    if bridge.get("mode") != "full":
        raise ValueError("runtime attachment is available only for Full AIDLC mode")
    if bridge.get("official_session_id") in {None, "", "pending-host-session"}:
        raise ValueError("runtime attachment requires a real host-issued official_session_id in the Full-mode Start bridge")
    activation = path.parent / "activation-v1.json"
    if not activation.is_file():
        raise ValueError("approve the Full-mode Planning Lock before runtime attachment")
    return bridge, path


def _anchor(root: Path, run_id: str) -> tuple[dict[str, Any], Path]:
    path = run_dir(root, run_id) / "anchors" / "approved-v1.json"
    if not path.is_file():
        raise ValueError("runtime attachment requires an immutable approved anchor")
    anchor = read(path)
    fingerprint = str(anchor.get("approved_fingerprint", ""))
    if not fingerprint:
        raise ValueError("approved anchor fingerprint is missing")
    return anchor, path


def _compatible(root: Path, bridge: dict[str, Any]) -> dict[str, Any]:
    compatibility = DETECT.status(root, bridge.get("compatibility_manifest"))
    if compatibility.get("state") != "compatible":
        raise ValueError(f"official pack is not compatible: {compatibility.get('state')}")
    official = compatibility.get("official") or {}
    if official.get("source") != bridge.get("official_source") or official.get("revision") != bridge.get("official_revision"):
        raise ValueError("verified official pack identity no longer matches the immutable bridge")
    return compatibility


def attach(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    bridge, bridge_path = _bridge(root, run_id)
    anchor, _ = _anchor(root, run_id)
    compatibility = _compatible(root, bridge)
    STATE.assert_consistent(root, run_id)
    path = run_dir(root, run_id) / SESSION_RELATIVE
    payload = {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-runtime-session",
        "runtime_adapter_version": RUNTIME_VERSION,
        "run_id": run_id,
        "bridge_artifact": bridge_path.relative_to(root).as_posix(),
        "compatibility_manifest": str(bridge["compatibility_manifest"]),
        "official_source": bridge["official_source"],
        "official_revision": bridge["official_revision"],
        "official_intent_id": bridge["official_intent_id"],
        "official_session_id": bridge["official_session_id"],
        "initial_stage": bridge["official_stage"],
        "host_adapter": compatibility["host_adapter"],
        "state": "attached",
        "approved_anchor_fingerprint": anchor["approved_fingerprint"],
        "boundary": "Receipt-driven attachment only. TailTrail did not execute an official-pack script or invent a lifecycle transition.",
    }
    SAN.validate_artifact(root, payload, "runtime-session")
    if path.exists():
        existing = read(path)
        if existing != payload:
            raise ValueError("runtime session attachment is immutable and conflicts with the requested identity")
        return {**status(root, run_id), "attachment_status": "existing"}
    L.atomic_json(path, payload)
    L.append_event(root, run_id, "official_aidlc_runtime_attached", {"artifact": path.relative_to(root).as_posix(), "official_session_id": payload["official_session_id"], "stage": payload["initial_stage"], "runtime_adapter_version": RUNTIME_VERSION})
    return {**status(root, run_id), "attachment_status": "created"}


def transition_paths(root: Path, run_id: str) -> list[Path]:
    return sorted((run_dir(root, run_id) / TRANSITIONS_RELATIVE).glob("transition-*.json"))


def _session(root: Path, run_id: str) -> tuple[dict[str, Any], Path]:
    path = run_dir(root, run_id) / SESSION_RELATIVE
    if not path.is_file():
        raise ValueError("official runtime is not attached; run `tailtrail aidlc official runtime attach` first")
    return read(path), path


def status(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    session, path = _session(root, run_id)
    bridge, _ = _bridge(root, run_id)
    anchor, _ = _anchor(root, run_id)
    _compatible(root, bridge)
    SAN.validate_artifact(root, session, "runtime-session")
    if session.get("type") != "tailtrail-official-aidlc-runtime-session" or session.get("runtime_adapter_version") != RUNTIME_VERSION:
        raise ValueError("official runtime session contract is incompatible")
    if session.get("official_session_id") != bridge.get("official_session_id") or session.get("approved_anchor_fingerprint") != anchor.get("approved_fingerprint"):
        raise ValueError("official runtime session conflicts with bridge or approved anchor identity")
    receipts: list[dict[str, Any]] = []
    current = session["initial_stage"]
    for sequence, item in enumerate(transition_paths(root, run_id), start=1):
        receipt = read(item)
        SAN.validate_artifact(root, receipt, "runtime-transition")
        if receipt.get("type") != "official-aidlc-transition-receipt" or receipt.get("sequence") != sequence:
            raise ValueError("official transition journal is incompatible or out of order")
        for field, expected in (("run_id", run_id), ("official_session_id", session["official_session_id"]), ("official_revision", session["official_revision"]), ("approved_anchor_fingerprint", session["approved_anchor_fingerprint"])):
            if receipt.get(field) != expected:
                raise ValueError(f"stored transition receipt has mismatched `{field}`")
        if receipt.get("integrity", {}).get("digest") != canonical_digest(receipt):
            raise ValueError("stored transition receipt integrity digest is invalid")
        _validate_motion(current, receipt)
        current = receipt["to_stage"]
        receipts.append(receipt)
    return {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-runtime-status",
        "run_id": run_id,
        "state": "active",
        "current_stage": current,
        "transition_count": len(receipts),
        "next_sequence": len(receipts) + 1,
        "official_session_id": session["official_session_id"],
        "official_revision": session["official_revision"],
        "approved_anchor_fingerprint": session["approved_anchor_fingerprint"],
        "session_artifact": path.relative_to(root).as_posix(),
        "latest_transition": transition_paths(root, run_id)[-1].relative_to(root).as_posix() if receipts else None,
        "boundary": "Derived read-only from the immutable attachment and append-only accepted receipts.",
    }


def assert_attached(root: Path, run_id: str, *, expected_stage: str | None = None) -> dict[str, Any]:
    result = status(root, run_id)
    session, _ = _session(root.resolve(), run_id)
    bridge, _ = _bridge(root.resolve(), run_id)
    anchor, _ = _anchor(root.resolve(), run_id)
    _compatible(root.resolve(), bridge)
    STATE.assert_consistent(root.resolve(), run_id)
    if session["approved_anchor_fingerprint"] != anchor["approved_fingerprint"]:
        raise ValueError("runtime session belongs to a different approved anchor")
    if expected_stage and result["current_stage"] != expected_stage:
        raise ValueError(f"official runtime stage is `{result['current_stage']}`, expected `{expected_stage}`")
    return result


def _prerequisite(root: Path, run_id: str, target: str) -> None:
    checkpoints = run_dir(root, run_id) / "aidlc-official" / "checkpoints"
    required = {
        "implementation": checkpoints / "design-decision-v1.json",
        "build-and-test": checkpoints / "construction-checkpoint-v1.json",
        "handoff": checkpoints / "evidence-checkpoint-v1.json",
        "operations": checkpoints / "handoff-v1.json",
    }.get(target)
    if required and not required.is_file():
        raise ValueError(f"transition to `{target}` requires `{required.relative_to(root).as_posix()}`")
    if target == "handoff" and not read(required).get("complete"):
        raise ValueError("transition to handoff requires a complete evidence checkpoint")
    if target == "operations" and not read(required).get("ready"):
        raise ValueError("transition to operations requires a ready handoff checkpoint")


def _validate_motion(current: str, receipt: dict[str, Any]) -> None:
    action = receipt["action"]
    source, target = receipt["from_stage"], receipt["to_stage"]
    if source != current:
        raise ValueError(f"stale transition: from_stage `{source}` does not match current stage `{current}`")
    source_index, target_index = STAGES.index(source), STAGES.index(target)
    if action == "advance" and target_index != source_index + 1:
        raise ValueError("advance must move exactly one lifecycle stage")
    if action == "resume" and target != source:
        raise ValueError("resume must preserve the current lifecycle stage")
    if action == "redo" and target_index > source_index:
        raise ValueError("redo must return to the current or an earlier stage")
    if action == "jump" and target_index <= source_index + 1:
        raise ValueError("jump must move forward by more than one stage")
    if action == "recovery" and target_index > source_index:
        raise ValueError("recovery must preserve or return to an earlier stage")


def import_transition(root: Path, run_id: str, receipt_path: Path, *, expected_action: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    runtime = assert_attached(root, run_id)
    supplied = receipt_path.resolve() if receipt_path.is_absolute() else (root / receipt_path).resolve()
    try:
        supplied_relative = supplied.relative_to(root).as_posix()
    except ValueError as error:
        raise ValueError("transition receipt must stay inside the project root") from error
    receipt_ref = SAN.local_reference(root, supplied_relative, "runtime-transition.input")
    receipt = read(root / receipt_ref)
    SAN.validate_artifact(root, receipt, "runtime-transition")
    if receipt.get("schema_version") != "1" or receipt.get("type") != "official-aidlc-transition-receipt":
        raise ValueError("transition receipt contract is incompatible")
    if expected_action and receipt.get("action") != expected_action:
        raise ValueError(f"receipt action must be `{expected_action}`")
    if receipt.get("action") not in ACTIONS:
        raise ValueError("unsupported official transition action")
    prior = [read(path) for path in transition_paths(root, run_id)]
    if any(row.get("receipt_id") == receipt.get("receipt_id") for row in prior):
        raise ValueError("duplicate transition receipt_id")
    expected = {
        "run_id": run_id,
        "official_session_id": runtime["official_session_id"],
        "official_revision": runtime["official_revision"],
        "runtime_adapter_version": RUNTIME_VERSION,
        "approved_anchor_fingerprint": runtime["approved_anchor_fingerprint"],
        "authority": "official-ai-dlc-pack",
        "sequence": runtime["next_sequence"],
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            raise ValueError(f"transition receipt has mismatched `{field}`")
    if receipt.get("integrity", {}).get("algorithm") != "sha256" or receipt.get("integrity", {}).get("digest") != canonical_digest(receipt):
        raise ValueError("transition receipt integrity digest is invalid")
    _validate_motion(runtime["current_stage"], receipt)
    _prerequisite(root, run_id, receipt["to_stage"])
    anchor, _ = _anchor(root, run_id)
    known = {row["requirement_uid"] for row in anchor.get("requirements", [])}
    if not set(receipt.get("requirement_uids", [])).issubset(known):
        raise ValueError("transition receipt references a requirement outside the approved anchor")
    for index, reference in enumerate(receipt.get("evidence_references", [])):
        SAN.local_reference(root, reference, f"runtime-transition.evidence_references[{index}]")
    destination = run_dir(root, run_id) / TRANSITIONS_RELATIVE / f"transition-{receipt['sequence']:04d}.json"
    if destination.exists():
        raise ValueError("transition sequence already exists")
    L.atomic_json(destination, receipt)
    L.append_event(root, run_id, "official_aidlc_transition_imported", {"artifact": destination.relative_to(root).as_posix(), "receipt_id": receipt["receipt_id"], "action": receipt["action"], "from_stage": receipt["from_stage"], "to_stage": receipt["to_stage"], "sequence": receipt["sequence"]})
    if receipt["action"] in {"redo", "recovery"}:
        L.append_event(root, run_id, "official_aidlc_runtime_recovery_routed", {"artifact": destination.relative_to(root).as_posix(), "action": receipt["action"], "stage": receipt["to_stage"], "reason_code": receipt["reason_code"]})
    return {**status(root, run_id), "accepted_transition": destination.relative_to(root).as_posix(), "accepted_action": receipt["action"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("attach", "status"):
        item = sub.add_parser(action); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
    for action in ("import-transition", "resume", "redo", "jump", "recovery"):
        item = sub.add_parser(action); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True); item.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "attach":
            payload = attach(args.root, args.run_id)
        elif args.action == "status":
            payload = status(args.root, args.run_id)
        else:
            expected = None if args.action == "import-transition" else args.action
            payload = import_transition(args.root, args.run_id, args.receipt, expected_action=expected)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, SAN.SanitizationError) as error:
        print(f"Official AIDLC runtime error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
