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
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
while ROOT.as_posix() in sys.path:
    sys.path.remove(ROOT.as_posix())
sys.path.insert(0, ROOT.as_posix())

loaded_tailtrail = sys.modules.get("tailtrail")
if (
    loaded_tailtrail is not None
    and Path(getattr(loaded_tailtrail, "__file__", "")).resolve()
    == ROOT / "scripts" / "tailtrail.py"
):
    # Some in-process dispatcher tests load scripts/tailtrail.py under the
    # package name.  The Full resolver is package-owned, so discard only that
    # non-package alias before importing the real package.
    del sys.modules["tailtrail"]
from tailtrail import aidlc_bundle


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


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _sealed_preflight(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "preflight_fingerprint": _fingerprint(payload)}


def _valid_seal(payload: dict[str, Any], field: str) -> bool:
    unsealed = dict(payload)
    fingerprint = unsealed.pop(field, None)
    return isinstance(fingerprint, str) and fingerprint == _fingerprint(unsealed)


def _sha256(value: Any) -> bool:
    text = str(value or "")
    return text.startswith("sha256:") and len(text) == 71 and all(character in "0123456789abcdef" for character in text[7:])


def _actionable_issues(
    issues: Any,
    *,
    phase: str,
) -> list[dict[str, str]]:
    """Keep the resolver category while adding one bounded recovery action."""
    rows = issues if isinstance(issues, list) else []
    action = (
        "Restore or reinstall TailTrail's bundled official AIDLC resources for this "
        "installation, resolve the reported category, and retry Full preflight."
        if phase == "resolution"
        else "Inspect and repair only the reported .tailtrail/official-aidlc managed "
        "project state, then retry Full preflight."
    )
    result: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        category = row.get("category")
        detail = row.get("detail")
        if isinstance(category, str) and isinstance(detail, str):
            result.append({"category": category, "detail": detail, "action": action})
    if result:
        return result
    return [{
        "category": f"{phase}-unavailable",
        "detail": f"bundled Full {phase} did not return a usable ready result",
        "action": action,
    }]


def bundled_full_preflight(
    root: Path,
    host: str,
    *,
    module_path: Path | None = None,
    managed_shared_root: Path | None = None,
    managed_ownership_manifest: Path | None = None,
    artifact_identity_receipt: dict[str, Any] | Path | None = None,
    running_version: str = aidlc_bundle.__version__,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve and project the bundled pack for an explicit offline Full request.

    This is the Phase 3A bridge boundary only.  Public Start routing remains a
    later slice.  A blocked resolver receipt is never sent to the projector,
    and no blocked outcome is reclassified as Lite.
    """
    resolution = aidlc_bundle.resolve(aidlc_bundle.ResolverInputs(
        host=host,
        requested_mode="full",
        module_path=module_path,
        managed_shared_root=managed_shared_root,
        managed_ownership_manifest=managed_ownership_manifest,
        artifact_identity_receipt=artifact_identity_receipt,
        running_version=running_version,
        environment=environment,
    ))
    resolution_fingerprint = resolution.get("receipt_fingerprint")
    if (
        resolution.get("state") != "ready"
        or resolution.get("requested_mode") != "full"
        or resolution.get("effective_mode") != "full"
        or resolution.get("network_used") is not False
        or not isinstance(resolution_fingerprint, str)
    ):
        return _sealed_preflight({
            "mode": "full",
            "requested_mode": "full",
            "effective_mode": "unavailable",
            "state": "official-full-unavailable",
            "network_used": False,
            "resolution_receipt_fingerprint": resolution_fingerprint,
            "project_projection": None,
            "issues": _actionable_issues(resolution.get("issues"), phase="resolution"),
            "boundary": "Full preflight stopped before project projection; no Lite fallback or Planning Lock authority was created.",
        })

    projection = aidlc_bundle.provision(aidlc_bundle.ProjectionInputs(
        resolution_receipt=resolution,
        target_root=root.resolve(),
        running_version=running_version,
    ))
    if (
        projection.get("state") != "ready"
        or projection.get("network_used") is not False
        or projection.get("source_resolution_fingerprint") != resolution_fingerprint
    ):
        issues = list(projection.get("issues") or [])
        if (
            projection.get("state") == "ready"
            and projection.get("source_resolution_fingerprint") != resolution_fingerprint
        ):
            issues.append({
                "category": "resolution-projection-mismatch",
                "detail": "project projection does not reference the sealed Full resolution receipt",
            })
        return _sealed_preflight({
            "mode": "full",
            "requested_mode": "full",
            "effective_mode": "unavailable",
            "state": "official-full-unavailable",
            "network_used": False,
            "resolution_receipt_fingerprint": resolution_fingerprint,
            "project_projection": projection,
            "issues": _actionable_issues(issues, phase="projection"),
            "boundary": "Full preflight stopped at project projection; no Lite fallback or Planning Lock authority was created.",
        })

    return _sealed_preflight({
        "mode": "full",
        "requested_mode": "full",
        "effective_mode": "full",
        "state": "official-full-ready",
        "network_used": False,
        "resolution_receipt_fingerprint": resolution_fingerprint,
        "source_resolution_fingerprint": projection["source_resolution_fingerprint"],
        "project_projection_fingerprint": projection.get("projection_fingerprint"),
        "pack_fingerprint": projection.get("pack_fingerprint"),
        "pack_path": projection.get("pack_path"),
        "trust_posture": projection.get("trust_posture"),
        "host": host,
        "official_source": resolution.get("official_source"),
        "official_revision": resolution.get("official_revision"),
        "official_commit": resolution.get("official_commit"),
        "project_projection": projection,
        "issues": [],
        "boundary": "Bundled Full rules are resolved and projected offline; this bridge result grants no Planning Lock authority.",
    })


def create_bundled(
    root: Path,
    run_id: str,
    goal: str,
    preflight_result: dict[str, Any],
    *,
    official_intent_id: str | None = None,
    official_session_id: str | None = None,
    official_stage: str = "requirements",
) -> dict[str, Any]:
    """Persist one immutable bridge identity from a sealed Phase 3A result."""
    root = root.resolve()
    run_id = _safe_run_id(run_id)
    if official_stage not in VALID_STAGES:
        raise ValueError("official_stage must be requirements, design, implementation, build-and-test, handoff, or operations")
    if not isinstance(preflight_result, dict) or not _valid_seal(preflight_result, "preflight_fingerprint"):
        raise ValueError("bundled Full bridge requires an intact sealed Phase 3A preflight result")
    projection = preflight_result.get("project_projection")
    resolution_fingerprint = preflight_result.get("resolution_receipt_fingerprint")
    if (
        preflight_result.get("mode") != "full"
        or preflight_result.get("requested_mode") != "full"
        or preflight_result.get("effective_mode") != "full"
        or preflight_result.get("state") != "official-full-ready"
        or preflight_result.get("network_used") is not False
        or preflight_result.get("issues") != []
        or not isinstance(projection, dict)
        or projection.get("state") != "ready"
        or projection.get("network_used") is not False
        or not _valid_seal(projection, "receipt_fingerprint")
        or not _sha256(resolution_fingerprint)
        or projection.get("source_resolution_fingerprint") != resolution_fingerprint
        or preflight_result.get("source_resolution_fingerprint") != resolution_fingerprint
        or preflight_result.get("project_projection_fingerprint") != projection.get("projection_fingerprint")
        or preflight_result.get("pack_fingerprint") != projection.get("pack_fingerprint")
        or preflight_result.get("pack_path") != projection.get("pack_path")
        or preflight_result.get("trust_posture") != projection.get("trust_posture")
    ):
        raise ValueError("bundled Full bridge requires one ready offline resolution-to-project identity")
    for field in ("project_projection_fingerprint", "pack_fingerprint"):
        if not _sha256(preflight_result.get(field)):
            raise ValueError(f"bundled Full bridge requires a valid {field}")
    pack_path = str(preflight_result.get("pack_path") or "")
    pack = Path(pack_path)
    if (
        pack.is_absolute()
        or ".." in pack.parts
        or not pack_path.startswith(".tailtrail/official-aidlc/packs/")
    ):
        raise ValueError("bundled Full bridge requires a safe managed project pack path")
    for field in ("official_source", "official_revision", "official_commit", "host", "trust_posture"):
        if not isinstance(preflight_result.get(field), str) or not str(preflight_result[field]).strip():
            raise ValueError(f"bundled Full bridge requires {field}")

    compatibility_manifest = f"{pack_path}/manifest.json"
    adapter = {
        "host": str(preflight_result["host"]),
        "rules_path": "aws-aidlc-rules/core-workflow.md",
    }
    payload = {
        "schema_version": "2",
        "type": "tailtrail-official-aidlc-bridge",
        "phase": "3B",
        "tailtrail_run_id": run_id,
        "mode": "full",
        "state": "planned-attachment",
        "source_kind": "tailtrail-bundled",
        "compatibility_mode": "bundled-v2",
        "network_used": False,
        "official_source": preflight_result["official_source"],
        "official_revision": preflight_result["official_revision"],
        "official_commit": preflight_result["official_commit"],
        "official_intent_id": official_intent_id or f"intent-{_digest(goal)}",
        "official_session_id": official_session_id or "pending-host-session",
        "official_stage": official_stage,
        "host_adapter": adapter,
        "compatibility_manifest": compatibility_manifest,
        "compatibility_state": "compatible",
        "resolution_receipt_fingerprint": resolution_fingerprint,
        "project_projection_fingerprint": preflight_result["project_projection_fingerprint"],
        "pack_fingerprint": preflight_result["pack_fingerprint"],
        "pack_path": pack_path,
        "trust_posture": preflight_result["trust_posture"],
        "preflight_fingerprint": preflight_result["preflight_fingerprint"],
        "boundary": "Immutable bundled Full identity only. This bridge does not resolve, provision, execute pack content, activate a Planning Lock, or grant implementation authority.",
    }
    sanitizer().validate_artifact(root, {
        key: payload[key]
        for key in (
            "schema_version", "type", "phase", "tailtrail_run_id", "mode", "state",
            "official_source", "official_revision", "official_intent_id",
            "official_session_id", "official_stage", "host_adapter",
            "compatibility_manifest", "compatibility_state", "boundary",
        )
    }, "bridge")
    L = ledger()
    path = L.state_dir(root, run_id) / BRIDGE_RELATIVE
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise ValueError("official AIDLC bridge identity already exists with different immutable content")
        return {**existing, "artifact": path.relative_to(root).as_posix(), "status": "existing"}
    L.atomic_json(path, payload)
    L.append_event(root, run_id, "official_aidlc_bridge_created", {
        "artifact": path.relative_to(root).as_posix(),
        "official_intent_id": payload["official_intent_id"],
        "official_session_id": payload["official_session_id"],
        "official_stage": payload["official_stage"],
        "official_revision": payload["official_revision"],
        "resolution_receipt_fingerprint": payload["resolution_receipt_fingerprint"],
        "project_projection_fingerprint": payload["project_projection_fingerprint"],
        "pack_fingerprint": payload["pack_fingerprint"],
    })
    return {**payload, "artifact": path.relative_to(root).as_posix(), "status": "created"}


def preflight(
    root: Path,
    mode: str,
    manifest: str | None = None,
    *,
    host: str | None = None,
) -> dict[str, Any]:
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
    # An explicitly supplied manifest remains an advanced external-pack
    # override.  It is exact and fail-closed: a broken override must never be
    # hidden by silently selecting the bundled pack or Lite.
    if manifest:
        compatibility = detector().status(root.resolve(), manifest)
        if compatibility["state"] != "compatible":
            return {
                "mode": "full",
                "requested_mode": "full",
                "effective_mode": "unavailable",
                "state": "official-full-unavailable",
                "network_used": False,
                "boundary": "The explicitly selected external Full pack is invalid; TailTrail stopped without bundled substitution or Lite downgrade.",
                "compatibility": compatibility,
            }
        return {
            "mode": "full",
            "requested_mode": "full",
            "effective_mode": "full",
            "state": "official-bridge-ready",
            "network_used": False,
            "boundary": "The explicitly selected external Full pack is compatible. Phase B records identity only and does not execute pack content.",
            "compatibility": compatibility,
        }
    # The historical raw CLI default is Codex. Installed host launchers expose
    # their identity through TAILTRAIL_ACTIVE_HOST, while an explicit --host
    # remains authoritative for callers that supply one.
    effective_host = host or os.environ.get("TAILTRAIL_ACTIVE_HOST") or "codex"
    return bundled_full_preflight(root.resolve(), effective_host)


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
