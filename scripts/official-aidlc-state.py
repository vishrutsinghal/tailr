#!/usr/bin/env python3
"""Project and validate one canonical TailTrail/official-AI-DLC run state."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OWNERSHIP = ROOT / "adapters" / "official-aidlc-field-ownership-v1.json"


def _load_ledger() -> Any:
    spec = importlib.util.spec_from_file_location("official_aidlc_state_ledger", ROOT / "scripts" / "run-ledger.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = _load_ledger()


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact must be a JSON object: {path.name}")
    return payload


def _run_dir(root: Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id:
        raise ValueError("run_id must be one local TailTrail run identifier")
    directory = L.state_dir(root.resolve(), run_id)
    if not (directory / "manifest.json").is_file():
        raise ValueError(f"TailTrail run `{run_id}` does not exist")
    return directory


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _latest(directory: Path, pattern: str) -> Path | None:
    files = sorted(directory.glob(pattern))
    return files[-1] if files else None


def project(root: Path, run_id: str) -> dict[str, Any]:
    """Return deterministic canonical state without writing or reconciling files."""
    root = root.resolve()
    directory = _run_dir(root, run_id)
    registry = _read(OWNERSHIP)
    if registry.get("schema_version") != "1" or registry.get("type") != "tailtrail-official-aidlc-field-ownership":
        raise ValueError("official AI-DLC field-ownership registry is incompatible")

    paths: dict[str, Path | None] = {
        "manifest": directory / "manifest.json",
        "approved-anchor": directory / "anchors" / "approved-v1.json",
        "official-bridge": directory / "aidlc-official" / "bridge-v1.json",
        "official-activation": directory / "aidlc-official" / "activation-v1.json",
        "official-runtime-session": directory / "aidlc-official" / "runtime" / "session-v1.json",
        "latest-harness-checkpoint": _latest(directory / "checkpoints", "checkpoint-*.json"),
        "official-closure-link": directory / "aidlc-official" / "closure" / "closure-link-v1.json",
        "positive-learning": _latest(directory / "positive-learning", "success-*.json"),
    }
    documents: dict[str, dict[str, Any]] = {}
    artifacts: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []

    def issue(code: str, severity: str, field: str, owner: str, artifact: str | None, message: str, recovery: str) -> None:
        issues.append({"code": code, "severity": severity, "field": field, "owner": owner, "artifact": artifact or "-", "message": message, "recovery": recovery})

    for role, path in paths.items():
        present = bool(path and path.is_file())
        row = {"role": role, "path": _relative(root, path) if present and path else None, "present": present, "schema_version": None}
        if present and path:
            try:
                documents[role] = _read(path)
                row["schema_version"] = documents[role].get("schema_version")
                if documents[role].get("schema_version") not in {None, "1"}:
                    issue("unsupported-schema-version", "error", "schema_version", role, row["path"], "Artifact schema version is not supported.", "Upgrade the adapter or restore a supported artifact version.")
            except (OSError, ValueError, json.JSONDecodeError):
                issue("invalid-artifact", "error", role, role, row["path"], "Artifact is not a readable JSON object.", "Repair or replace the artifact from its authoritative source.")
        artifacts.append(row)

    manifest = documents.get("manifest", {})
    anchor = documents.get("approved-anchor", {})
    bridge = documents.get("official-bridge", {})
    activation = documents.get("official-activation", {})
    runtime_session = documents.get("official-runtime-session", {})
    checkpoint = documents.get("latest-harness-checkpoint", {})
    closure = documents.get("official-closure-link", {})
    learning = documents.get("positive-learning", {})

    if manifest.get("run_id") != run_id:
        issue("manifest-run-id-conflict", "error", "run_id", "manifest", _relative(root, paths["manifest"]) if paths["manifest"] else None, "Manifest identity does not match the selected run directory.", "Restore the manifest and directory from the append-only run ledger.")

    projections = [
        ("approved-anchor", anchor.get("run_id")),
        ("official-bridge", bridge.get("tailtrail_run_id")),
        ("official-activation", activation.get("tailtrail_run_id")),
        ("official-runtime-session", runtime_session.get("run_id")),
        ("latest-harness-checkpoint", checkpoint.get("run_id")),
        ("official-closure-link", closure.get("run_id")),
        ("positive-learning", learning.get("run_id")),
    ]
    for role, observed in projections:
        if documents.get(role) and observed not in {None, run_id}:
            issue("run-id-conflict", "error", "run_id", "manifest", next((row["path"] for row in artifacts if row["role"] == role), None), "Projected run ID conflicts with the manifest owner.", "Restore the projection for this run; do not change the manifest identity.")

    requirements: list[dict[str, Any]] = []
    known: set[str] = set()
    for index, row in enumerate(anchor.get("requirements", []), start=1):
        uid = str(row.get("requirement_uid", ""))
        if not uid:
            issue("missing-requirement-uid", "error", "requirements", "approved-anchor", paths["approved-anchor"].as_posix() if paths["approved-anchor"] else None, f"Approved requirement row {index} has no UID.", "Create a valid approved anchor through the requirement approval flow.")
            continue
        if uid in known:
            issue("duplicate-requirement-uid", "error", "requirements", "approved-anchor", _relative(root, paths["approved-anchor"]) if paths["approved-anchor"] else None, "Approved anchor contains a duplicate requirement UID.", "Invalidate and re-approve a corrected requirement boundary.")
            continue
        known.add(uid)
        requirements.append({"requirement_uid": uid, "display_id": row.get("display_id"), "statement": row.get("statement", ""), "status": row.get("status")})

    if not anchor:
        issue("approved-anchor-missing", "warning", "requirements", "approved-anchor", None, "No immutable approved anchor exists yet.", "Complete requirement approval before implementation or closure.")

    checkpoint_rows = checkpoint.get("requirements", []) if isinstance(checkpoint.get("requirements", []), list) else []
    seen_checkpoint: set[str] = set()
    for row in checkpoint_rows:
        uid = str(row.get("requirement_uid", "")) if isinstance(row, dict) else ""
        if uid in seen_checkpoint:
            issue("duplicate-checkpoint-requirement", "error", "requirements", "approved-anchor", _relative(root, paths["latest-harness-checkpoint"]) if paths["latest-harness-checkpoint"] else None, "Latest checkpoint contains a duplicate requirement UID.", "Regenerate the checkpoint from the approved anchor.")
        seen_checkpoint.add(uid)
        if uid and known and uid not in known:
            issue("unknown-checkpoint-requirement", "error", "requirements", "approved-anchor", _relative(root, paths["latest-harness-checkpoint"]) if paths["latest-harness-checkpoint"] else None, "Latest checkpoint references a requirement outside the approved anchor.", "Remove the projection and replan any material new requirement.")
    expected_fingerprint = anchor.get("approved_fingerprint")
    observed_fingerprint = checkpoint.get("anchor_fingerprint")
    if checkpoint and expected_fingerprint and observed_fingerprint and observed_fingerprint != expected_fingerprint:
        issue("anchor-fingerprint-conflict", "error", "requirements", "approved-anchor", _relative(root, paths["latest-harness-checkpoint"]) if paths["latest-harness-checkpoint"] else None, "Latest checkpoint was produced from a different approved anchor fingerprint.", "Regenerate the checkpoint from the current immutable anchor.")
    elif checkpoint and expected_fingerprint and not observed_fingerprint:
        issue("legacy-checkpoint-fingerprint-missing", "warning", "requirements", "approved-anchor", _relative(root, paths["latest-harness-checkpoint"]) if paths["latest-harness-checkpoint"] else None, "Legacy checkpoint has no anchor fingerprint.", "Regenerate it when the next checkpoint is recorded; current evidence remains advisory.")

    official_identity: dict[str, Any] | None = None
    if bridge:
        official_identity = {key: bridge.get(key) for key in ("official_source", "official_revision", "official_intent_id", "official_session_id", "official_stage")}
        for role, document in (("official-activation", activation), ("official-closure-link", closure)):
            for field in ("official_revision", "official_intent_id", "official_session_id"):
                observed = document.get(field) if document else None
                owner_value = bridge.get(field)
                if observed is not None and observed != owner_value:
                    issue("official-identity-conflict", "error", field, "official-bridge", next((row["path"] for row in artifacts if row["role"] == role), None), f"{role} conflicts with the immutable official bridge identity.", "Restore the projection from the bridge; never rewrite bridge identity.")
        if activation.get("official_stage") is not None and activation.get("official_stage") != bridge.get("official_stage"):
            issue("official-stage-conflict", "error", "official_stage", "official-bridge", _relative(root, paths["official-activation"]) if paths["official-activation"] else None, "Official activation stage conflicts with the immutable bridge stage.", "Regenerate activation from the bridge identity.")
        if runtime_session:
            for field in ("official_source", "official_revision", "official_intent_id", "official_session_id"):
                if runtime_session.get(field) != bridge.get(field):
                    issue("official-runtime-identity-conflict", "error", field, "official-bridge", _relative(root, paths["official-runtime-session"]) if paths["official-runtime-session"] else None, "Official runtime attachment conflicts with the immutable bridge identity.", "Quarantine the attachment and reattach the matching pinned official session.")
            if anchor.get("approved_fingerprint") and runtime_session.get("approved_anchor_fingerprint") != anchor.get("approved_fingerprint"):
                issue("official-runtime-anchor-conflict", "error", "requirements", "approved-anchor", _relative(root, paths["official-runtime-session"]) if paths["official-runtime-session"] else None, "Official runtime attachment references a different approved anchor.", "Reattach only after restoring the matching immutable anchor.")

    expected_transition_sequence = 1
    current_stage = runtime_session.get("initial_stage") if runtime_session else None
    for path in sorted((directory / "aidlc-official" / "runtime" / "transitions").glob("transition-*.json")):
        try:
            transition = _read(path)
        except (OSError, ValueError, json.JSONDecodeError):
            issue("invalid-official-transition", "error", "official_transition", "official-bridge", _relative(root, path), "Official transition receipt is not a readable JSON object.", "Restore the append-only receipt from its authoritative host record.")
            continue
        artifacts.append({"role": "official-transition-receipt", "path": _relative(root, path), "present": True, "schema_version": transition.get("schema_version")})
        if transition.get("sequence") != expected_transition_sequence:
            issue("official-transition-order-conflict", "error", "sequence", "official-bridge", _relative(root, path), "Official transition receipts are not contiguous and ordered.", "Restore the missing receipt or route Recovery/Replan; never renumber history.")
        if transition.get("run_id") != run_id or (bridge and transition.get("official_session_id") != bridge.get("official_session_id")):
            issue("official-transition-identity-conflict", "error", "official_identity", "official-bridge", _relative(root, path), "Official transition receipt belongs to a different run or session.", "Quarantine the mismatched receipt and import the correct host-issued receipt.")
        if current_stage and transition.get("from_stage") != current_stage:
            issue("official-transition-stage-conflict", "error", "official_stage", "official-bridge", _relative(root, path), "Official transition does not continue from the projected current stage.", "Route Recovery/Replan using the preserved receipt history.")
        current_stage = transition.get("to_stage")
        expected_transition_sequence += 1

    official_checkpoint_paths = sorted((directory / "aidlc-official" / "checkpoints").glob("*.json"))
    for path in official_checkpoint_paths:
        try:
            document = _read(path)
        except (OSError, ValueError, json.JSONDecodeError):
            issue("invalid-official-checkpoint", "error", "official_checkpoints", "official-bridge", _relative(root, path), "Official checkpoint is not a readable JSON object.", "Repair or regenerate the checkpoint from saved evidence.")
            continue
        artifacts.append({"role": "official-checkpoint", "path": _relative(root, path), "present": True, "schema_version": document.get("schema_version")})
        if document.get("run_id") not in {None, run_id}:
            issue("run-id-conflict", "error", "run_id", "manifest", _relative(root, path), "Official checkpoint belongs to a different run.", "Remove the mismatched projection and regenerate it for this run.")
        for row in document.get("requirements", []):
            uid = row.get("requirement_uid") if isinstance(row, dict) else (row if isinstance(row, str) else None)
            if uid and known and uid not in known:
                issue("unknown-official-requirement", "error", "requirements", "approved-anchor", _relative(root, path), "Official checkpoint references a requirement outside the approved anchor.", "Regenerate the official checkpoint from canonical approved requirements.")

    evidence_results: list[dict[str, Any]] = []
    for path in sorted((directory / "validation-receipts").glob("*.json")):
        try:
            document = _read(path)
        except (OSError, ValueError, json.JSONDecodeError):
            issue("invalid-evidence-receipt", "error", "evidence_results", "validation-receipts", _relative(root, path), "Validation receipt is not a readable JSON object.", "Regenerate the receipt from honest execution evidence.")
            continue
        artifacts.append({"role": "validation-receipt", "path": _relative(root, path), "present": True, "schema_version": document.get("schema_version")})
        if document.get("run_id") not in {None, run_id}:
            issue("run-id-conflict", "error", "run_id", "manifest", _relative(root, path), "Validation receipt belongs to a different run.", "Remove the mismatched receipt and record evidence for this run.")
        receipt_uids = document.get("requirement_uids")
        if not isinstance(receipt_uids, list):
            receipt_uids = [document.get("requirement_uid")] if document.get("requirement_uid") else []
        unknown = sorted({str(uid) for uid in receipt_uids if uid and known and uid not in known})
        if unknown:
            issue("unknown-evidence-requirement", "error", "requirements", "approved-anchor", _relative(root, path), "Validation receipt references a requirement outside the approved anchor.", "Record a new receipt using only approved requirement UIDs.")
        evidence_results.append({"artifact": _relative(root, path), "requirement_uids": [str(uid) for uid in receipt_uids if uid], "tier": document.get("tier"), "outcome": document.get("outcome")})

    acceptance = closure.get("acceptance_state") if closure else None
    if learning and closure and acceptance not in {"accepted-user", "accepted-ci"}:
        issue("learning-without-acceptance", "error", "acceptance", "official-closure-link", _relative(root, paths["positive-learning"]) if paths["positive-learning"] else None, "Positive-learning projection exists without an accepted closure state.", "Quarantine the learning candidate until closure acceptance is restored.")

    errors = [row for row in issues if row["severity"] == "error"]
    warnings = [row for row in issues if row["severity"] == "warning"]
    status = "conflict" if errors else ("incomplete" if warnings else "valid")
    checkpoint_state = {str(row.get("requirement_uid")): row.get("state") for row in checkpoint_rows if isinstance(row, dict) and row.get("requirement_uid")}
    drift = checkpoint.get("drift", []) if isinstance(checkpoint.get("drift", []), list) else []
    return {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-run-state",
        "run_id": run_id,
        "status": status,
        "valid": not errors,
        "owners": {row["field"]: {"owner": row["owner"], "owner_path": row["owner_path"]} for row in registry["fields"]},
        "requirements": requirements,
        "official_identity": official_identity,
        "official_runtime": {"attached": bool(runtime_session), "current_stage": current_stage, "transition_count": expected_transition_sequence - 1},
        "delivery": {"requirement_states": checkpoint_state, "drift": drift, "evidence_results": evidence_results, "acceptance": acceptance},
        "artifacts": sorted(artifacts, key=lambda row: (row["role"], row["path"] or "")),
        "issues": issues,
        "boundary": "Read-only canonical projection. Conflicts are reported and never auto-reconciled or written back to owner artifacts.",
    }


def assert_consistent(root: Path, run_id: str) -> dict[str, Any]:
    payload = project(root, run_id)
    if not payload["valid"]:
        codes = ", ".join(sorted({row["code"] for row in payload["issues"] if row["severity"] == "error"}))
        raise ValueError(f"canonical run state has unresolved conflicts: {codes}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "validate"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        payload = project(args.root, args.run_id)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if args.action == "validate" and not payload["valid"] else 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Official AIDLC state error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
