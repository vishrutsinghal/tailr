#!/usr/bin/env python3
"""Create and inspect append-only TailTrail bridge identity for official AI-DLC mode.

Phase B records the relationship between one TailTrail run and a verified local
official-pack candidate. It never executes, attaches, downloads, or modifies
the external workflow engine.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_RELATIVE = Path("aidlc-official") / "bridge-v1.json"
ACTIVATION_RELATIVE = Path("aidlc-official") / "activation-v1.json"
VALID_STAGES = {"requirements", "design", "implementation", "build-and-test", "handoff", "operations"}


def _load(relative: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ledger() -> Any:
    return _load("scripts/run-ledger.py", "official_aidlc_bridge_ledger")


def detector() -> Any:
    return _load("scripts/aidlc-official-detect.py", "official_aidlc_bridge_detector")


def sanitizer() -> Any:
    return _load("scripts/official-aidlc-sanitize.py", "official_aidlc_bridge_sanitizer")


def _safe_run_id(run_id: str) -> str:
    if not run_id or Path(run_id).name != run_id:
        raise ValueError("run_id must be one local TailTrail run identifier")
    return run_id


def _digest(goal: str) -> str:
    return hashlib.sha256(goal.encode("utf-8")).hexdigest()[:12]


def preflight(root: Path, mode: str, manifest: str | None = None) -> dict[str, Any]:
    """Return the mode boundary before a Planning Lock is created."""
    if mode == "medium":
        mode = "standard"
    if mode not in {"lite", "standard", "full", "off"}:
        raise ValueError("aidlc mode must be lite, standard, full, or off")
    if mode == "off":
        return {"mode": "off", "state": "disabled", "boundary": "AIDLC lifecycle routing is disabled for this Start run."}
    if mode == "lite":
        return {"mode": "lite", "state": "local-lite", "boundary": "Use TailTrail's local AIDLC Lifecycle Lite only when the selected task requires it."}
    if mode == "standard":
        compatibility = detector().status(root.resolve(), manifest)
        if compatibility["state"] != "compatible":
            return {
                "mode": "lite", "requested_mode": "standard", "state": "official-pack-unavailable-fallback",
                "boundary": "Official AIDLC Standard is unavailable because no compatible pinned pack is installed. TailTrail Lite remains available; no local AIDLC questionnaire will be presented as official.",
                "compatibility": compatibility,
            }
        return {"mode": "standard", "state": "official-standard-ready", "boundary": "Use the verified official AI-DLC Requirements Analysis rules through the configured host. TailTrail validates the resulting stage artifact and retains its anchor, evidence, drift, recovery, and closure controls.", "compatibility": compatibility}
    compatibility = detector().status(root.resolve(), manifest)
    if compatibility["state"] != "compatible":
        return {
            "mode": "lite", "requested_mode": "full", "state": "official-pack-unavailable-fallback",
            "boundary": "Full official AIDLC is unavailable because no compatible pinned pack is installed. TailTrail Lite remains available; it does not claim to run the official lifecycle.",
            "compatibility": compatibility,
        }
    return {
        "mode": "full",
        "state": "official-bridge-ready",
        "boundary": "Phase B records bridge identity only. It does not execute or attach the official workflow engine.",
        "compatibility": compatibility,
    }


def create(
    root: Path,
    run_id: str,
    goal: str,
    *,
    manifest: str | None = None,
    official_intent_id: str | None = None,
    official_session_id: str | None = None,
    official_stage: str = "requirements",
    mode: str = "full",
) -> dict[str, Any]:
    """Persist one immutable, planning-only bridge identity for a compatible pack."""
    root = root.resolve()
    run_id = _safe_run_id(run_id)
    if mode not in {"standard", "full"}:
        raise ValueError("official bridge mode must be standard or full")
    if official_stage not in VALID_STAGES:
        raise ValueError("official_stage must be requirements, design, implementation, build-and-test, handoff, or operations")
    compatibility = detector().status(root, manifest)
    if compatibility["state"] != "compatible":
        raise ValueError("official bridge requires a compatible pinned official pack")
    L = ledger()
    path = L.state_dir(root, run_id) / BRIDGE_RELATIVE
    if path.exists():
        return {**json.loads(path.read_text(encoding="utf-8")), "artifact": path.relative_to(root).as_posix(), "status": "existing"}
    official = compatibility.get("official") or {}
    adapter = compatibility.get("host_adapter") or {}
    payload = {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-bridge",
        "phase": "B",
        "tailtrail_run_id": run_id,
        "mode": mode,
        "state": "planned-attachment",
        "official_source": official.get("source"),
        "official_revision": official.get("revision"),
        "official_intent_id": official_intent_id or f"intent-{_digest(goal)}",
        "official_session_id": official_session_id or "pending-host-session",
        "official_stage": official_stage,
        "host_adapter": adapter,
        "compatibility_manifest": compatibility.get("manifest"),
        "compatibility_state": compatibility.get("state"),
        "boundary": "Identity and provenance only. The host must load the verified official rules and create the stage artifact; TailTrail never substitutes local questions for official AIDLC.",
    }
    sanitizer().validate_artifact(root, payload, "bridge")
    L.atomic_json(path, payload)
    L.append_event(root, run_id, "official_aidlc_bridge_created", {
        "artifact": path.relative_to(root).as_posix(),
        "official_intent_id": payload["official_intent_id"],
        "official_session_id": payload["official_session_id"],
        "official_stage": payload["official_stage"],
        "official_revision": payload["official_revision"],
    })
    return {**payload, "artifact": path.relative_to(root).as_posix(), "status": "created"}


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    L = ledger()
    path = L.state_dir(root, _safe_run_id(run_id)) / BRIDGE_RELATIVE
    if not path.is_file():
        raise ValueError(f"official AIDLC bridge for run `{run_id}` does not exist")
    return {**json.loads(path.read_text(encoding="utf-8")), "artifact": path.relative_to(root).as_posix(), "read_only": True}


def activate(root: Path, run_id: str) -> dict[str, Any]:
    """Record Planning Lock approval without changing the immutable identity."""
    root = root.resolve()
    identity = show(root, run_id)
    L = ledger()
    path = L.state_dir(root, run_id) / ACTIVATION_RELATIVE
    if path.is_file():
        return {**json.loads(path.read_text(encoding="utf-8")), "artifact": path.relative_to(root).as_posix(), "status": "existing"}
    payload = {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-bridge-activation",
        "phase": "B",
        "tailtrail_run_id": run_id,
        "bridge_artifact": identity["artifact"],
        "state": "approved-awaiting-host-attachment",
        "official_intent_id": identity["official_intent_id"],
        "official_session_id": identity["official_session_id"],
        "official_stage": identity["official_stage"],
        "boundary": "The TailTrail Planning Lock is approved. Phase I may now create a separate verified runtime attachment; this immutable Phase B activation does not execute the engine.",
    }
    sanitizer().validate_artifact(root, payload, "activation")
    L.atomic_json(path, payload)
    L.append_event(root, run_id, "official_aidlc_bridge_activated", {"artifact": path.relative_to(root).as_posix(), "official_stage": payload["official_stage"]})
    return {**payload, "artifact": path.relative_to(root).as_posix(), "status": "created"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    create_parser = sub.add_parser("create")
    create_parser.add_argument("--root", type=Path, default=Path.cwd())
    create_parser.add_argument("--run-id", required=True)
    create_parser.add_argument("--goal", required=True)
    create_parser.add_argument("--manifest")
    create_parser.add_argument("--official-intent-id")
    create_parser.add_argument("--official-session-id")
    create_parser.add_argument("--official-stage", default="requirements", choices=sorted(VALID_STAGES))
    create_parser.add_argument("--mode", choices=("standard", "full"), default="full")
    show_parser = sub.add_parser("show")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    activate_parser = sub.add_parser("activate")
    activate_parser.add_argument("--root", type=Path, default=Path.cwd())
    activate_parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if args.action == "create":
            payload = create(args.root, args.run_id, args.goal, manifest=args.manifest, official_intent_id=args.official_intent_id, official_session_id=args.official_session_id, official_stage=args.official_stage, mode=args.mode)
        elif args.action == "show":
            payload = show(args.root, args.run_id)
        else:
            payload = activate(args.root, args.run_id)
    except ValueError as error:
        print(f"Official AIDLC bridge error: {error}")
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
