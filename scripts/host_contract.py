#!/usr/bin/env python3
"""Validated host-input-contract intake for TailTrail Start.

The `tailtrail-host-input-contract` schema already models request mode,
change intent, path roles, criteria, and proof. This module makes it a
first-class Start input: parse one transport (inline JSON, file, or
base64), validate shape + enums + path safety, check mode/authority
consistency, bind the exact goal and target, and fingerprint the result.

States: `accepted` (complete, grounded, non-contradictory),
`insufficient` (mandatory fields open), `contradicted` (claims conflict).
Only `accepted` input may progress toward an implementation Planning Lock.
Raw narration never creates authority; only this validated artifact does.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import importlib.util
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
_POLICY: Any = None


def _policy() -> Any:
    global _POLICY
    if _POLICY is None:
        spec = importlib.util.spec_from_file_location(
            "host_contract_workspace_policy", ROOT / "scripts" / "repository_path_policy.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to load scripts/repository_path_policy.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _POLICY = module
    return _POLICY


REQUEST_MODES = frozenset({"implementation", "read-only", "validation-only"})
CHANGE_INTENTS = frozenset({"correction", "new-capability", "refactor", "validation", "prose-only"})
PROFILES = frozenset({
    "documentation-only", "existing-code change", "new feature",
    "greenfield-new-project", "configuration/data", "QA/validation-only", "review/read-only",
})
BEHAVIOR_SURFACES = frozenset({"cli-contract", "workflow", "presentation", "data", "documentation", "internal"})
PATH_ROLES = frozenset({
    "existing-implementation-owner", "proposed-implementation-owner",
    "inspection-input", "existing-proof-path", "proposed-proof-path",
    "configuration", "generated", "excluded", "external",
})
OWNER_ROLES = frozenset({"existing-implementation-owner", "proposed-implementation-owner"})
PROOF_ROLES = frozenset({"existing-proof-path", "proposed-proof-path"})

_CONTRACT_VERSION = "1"
_CONTRACT_TYPE = "tailtrail-host-input-contract"


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def parse_transport(
    inline: str | None = None,
    path: str | Path | None = None,
    encoded: str | None = None,
) -> dict[str, Any]:
    """Parse exactly one contract transport into a dict. Never validates."""
    supplied = [bool(inline), bool(path), bool(encoded)]
    if sum(supplied) != 1:
        raise ValueError("supply exactly one host-contract transport: inline JSON, file, or base64")
    if inline:
        try:
            payload = json.loads(inline)
        except json.JSONDecodeError as error:
            raise ValueError(f"host contract is not valid JSON: {error}") from error
    elif encoded:
        try:
            payload = json.loads(base64.b64decode(encoded.encode("ascii"), validate=True).decode("utf-8"))
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"host contract base64 transport is invalid: {error}") from error
    else:
        candidate = Path(str(path))
        resolved = None
        if candidate.is_absolute():
            if candidate.is_file():
                resolved = candidate.resolve()
        elif ".." not in candidate.parts:
            for base in (Path.cwd(), ROOT):
                attempt = (base / candidate).resolve()
                try:
                    within = attempt.is_relative_to(base.resolve())
                except OSError:
                    continue
                if within and attempt.is_file():
                    resolved = attempt
                    break
        if resolved is None:
            raise ValueError(
                "host contract file must exist: an absolute file path or a "
                "repository-relative path without parent traversal"
            )
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"host contract file is unreadable: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("host contract must be a JSON object")
    return payload


def _normalize_path(value: Any) -> tuple[str | None, str | None]:
    text = str(value or "").replace("\\", "/").strip().strip("/")
    if not text or len(text) > 4096:
        return None, "empty-or-oversized-path"
    pure = PurePosixPath(text)
    if pure.is_absolute() or ".." in pure.parts or text in {"", "."}:
        return None, "traversal-or-absolute-path"
    return pure.as_posix(), None


def validate(contract: dict[str, Any], *, root: Path, goal: str) -> dict[str, Any]:
    """Validate a parsed contract and bind it to the exact goal and target.

    Returns `accepted` with a normalized projection, `insufficient` with
    open fields, or `contradicted` with conflicts. Never raises for
    content problems (transport errors raise in `parse_transport`).
    """
    open_fields: list[str] = []
    conflicts: list[str] = []

    def _need(field: str) -> None:
        if field not in open_fields:
            open_fields.append(field)

    if not isinstance(contract, dict):
        return {"state": "insufficient", "open_fields": ["contract-object"], "conflicts": []}
    if contract.get("schema_version") != _CONTRACT_VERSION:
        _need("schema_version")
    if contract.get("type") != _CONTRACT_TYPE:
        _need("type")
    if contract.get("private_reasoning_excluded") is not True:
        _need("private_reasoning_excluded")
    contract_id = str(contract.get("contract_id", "") or "").strip()
    if not contract_id:
        _need("contract_id")
    profile = contract.get("profile")
    if profile not in PROFILES:
        _need("profile")
    change_intent = contract.get("change_intent")
    if change_intent not in CHANGE_INTENTS:
        _need("change_intent")
    request_mode = contract.get("request_mode")
    if request_mode not in REQUEST_MODES:
        _need("request_mode")
    behavior_surface = contract.get("behavior_surface")
    if behavior_surface not in BEHAVIOR_SURFACES:
        _need("behavior_surface")

    raw_paths = contract.get("paths")
    normalized_paths: list[dict[str, Any]] = []
    if not isinstance(raw_paths, list) or not raw_paths:
        _need("paths")
    else:
        for index, entry in enumerate(raw_paths):
            if not isinstance(entry, dict):
                _need(f"paths[{index}]")
                continue
            normalized, rejection = _normalize_path(entry.get("path"))
            role = entry.get("role")
            if normalized is None:
                _need(f"paths[{index}].path")
                continue
            if role not in PATH_ROLES:
                _need(f"paths[{index}].role")
                continue
            item: dict[str, Any] = {"path": normalized, "role": role}
            if entry.get("source_answer_id") is not None:
                item["source_answer_id"] = str(entry.get("source_answer_id"))
            if isinstance(entry.get("new_file_evidence"), dict):
                item["new_file_evidence"] = dict(entry.get("new_file_evidence"))
            normalized_paths.append(item)

    criteria = contract.get("criteria")
    positives: list[str] = []
    negatives: list[str] = []
    if not isinstance(criteria, dict):
        _need("criteria")
    else:
        positives = [str(v).strip() for v in (criteria.get("positive", []) or []) if str(v).strip()]
        negatives = [str(v).strip() for v in (criteria.get("negative", []) or []) if str(v).strip()]
        if not positives:
            _need("criteria.positive")
        if not negatives:
            _need("criteria.negative")

    proof = contract.get("proof")
    proof_projection: dict[str, Any] | None = None
    if not isinstance(proof, dict):
        _need("proof")
    else:
        command = str(proof.get("command", "") or "").strip()
        tiers = [str(v).strip() for v in (proof.get("tiers", []) or []) if str(v).strip()]
        repro = str(proof.get("reproduction_binding", "") or "").strip()
        post = str(proof.get("post_change_binding", "") or "").strip()
        if command and tiers:
            proof_projection = {"command": command, "tiers": tiers}
        elif repro and post:
            proof_projection = {"reproduction_binding": repro, "post_change_binding": post}
        else:
            _need("proof")

    if change_intent == "correction" and not isinstance(contract.get("correction_premise"), dict):
        _need("correction_premise")
    if change_intent != "correction" and "correction_premise" in contract:
        conflicts.append("correction premise present for non-correction change intent")
    premise = contract.get("correction_premise")
    if (
        isinstance(premise, dict)
        and str(premise.get("state", "")) != "not-applicable"
        and "owner_hypothesis" not in contract
    ):
        _need("owner_hypothesis")

    owner_paths = sorted({p["path"] for p in normalized_paths if p["role"] in OWNER_ROLES})
    proof_paths = sorted({p["path"] for p in normalized_paths if p["role"] in PROOF_ROLES})
    both = sorted(set(owner_paths) & set(proof_paths))
    if both:
        conflicts.append(f"path claims both implementation and proof authority: {', '.join(both)}")
    if request_mode == "read-only" and owner_paths:
        conflicts.append("read-only contract carries implementation-owner paths")
    if change_intent == "prose-only" and owner_paths:
        conflicts.append("prose-only contract carries implementation-owner paths")
    if request_mode == "implementation" and not owner_paths:
        _need("paths:implementation-owner")

    if conflicts:
        return {"state": "contradicted", "open_fields": [], "conflicts": sorted(set(conflicts))}
    if open_fields:
        return {"state": "insufficient", "open_fields": sorted(set(open_fields)), "conflicts": []}

    try:
        target = root.resolve().as_posix()
    except OSError:
        target = root.as_posix()
    goal_fingerprint = _fingerprint({"goal": goal})
    artifact = {
        "schema_version": _CONTRACT_VERSION,
        "type": _CONTRACT_TYPE,
        "contract_id": contract_id,
        "request_mode": request_mode,
        "change_intent": change_intent,
        "profile": profile,
        "behavior_surface": behavior_surface,
        "paths": normalized_paths,
        "criteria": {"positive": positives, "negative": negatives},
        "proof": proof_projection,
        "goal": goal,
        "goal_fingerprint": goal_fingerprint,
        "target": target,
        "run_id_binding": str(contract.get("run_id", "") or "").strip() or "unbound",
        "private_reasoning_excluded": True,
    }
    artifact["fingerprint"] = _fingerprint({
        k: artifact[k] for k in (
            "schema_version", "type", "contract_id", "request_mode", "change_intent",
            "profile", "behavior_surface", "paths", "criteria", "proof",
            "goal_fingerprint", "target",
        )
    })
    return {"state": "accepted", "open_fields": [], "conflicts": [], "validated": artifact}
