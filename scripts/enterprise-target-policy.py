#!/usr/bin/env python3
"""Evaluate local enterprise target-workspace policy and write safe receipts.

The policy is opt-in, local, and JSON-only so its enforcement is deterministic.
It is not identity authentication: an `--actor` value is a declared label that
may be checked against policy owners, not proof of a human identity.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TYPE = "tailtrail-enterprise-target-policy"


def _load(relative: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def ledger() -> Any:
    return _load("scripts/run-ledger.py", "enterprise_target_policy_ledger")


def workspace() -> Any:
    return _load("scripts/target_workspace.py", "enterprise_target_policy_workspace")


def _digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def load(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"enterprise target policy does not exist: {resolved.as_posix()}")
    raw = resolved.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"enterprise target policy must be valid JSON: {error}") from error
    if not isinstance(payload, dict) or payload.get("type") != TYPE or payload.get("schema_version") != "1":
        raise ValueError("enterprise target policy must be a v1 tailtrail-enterprise-target-policy document")
    if not isinstance(payload.get("aliases", {}), dict) or not isinstance(payload.get("allowed_target_roots", []), list) or not isinstance(payload.get("restricted_target_roots", []), list):
        raise ValueError("enterprise target policy aliases and root lists have invalid shapes")
    return {"path": resolved.as_posix(), "sha256": _digest(raw), "policy": payload}


def aliases(loaded: dict[str, Any] | None) -> dict[str, Path]:
    if not loaded:
        return {}
    result: dict[str, Path] = {}
    for name, item in loaded["policy"].get("aliases", {}).items():
        if not isinstance(name, str) or not isinstance(item, dict) or not isinstance(item.get("root"), str):
            raise ValueError("each enterprise policy alias needs a name and local root")
        result[name] = Path(item["root"]).expanduser()
    return result


def _within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.expanduser().resolve())
        return True
    except ValueError:
        return False


def evaluate(root: Path, loaded: dict[str, Any] | None, *, actor: str | None = None, selected_alias: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    if loaded is None:
        return {"status": "not-configured", "blocking": False, "root": root.as_posix(), "boundary": "No enterprise target policy was supplied; local target identity and input-role safeguards remain active."}
    policy = loaded["policy"]
    issues: list[str] = []
    allowed = [Path(str(value)).expanduser() for value in policy.get("allowed_target_roots", [])]
    restricted = [Path(str(value)).expanduser() for value in policy.get("restricted_target_roots", [])]
    if allowed and not any(_within(root, item) for item in allowed):
        issues.append("target root is outside allowed_target_roots")
    if any(_within(root, item) for item in restricted):
        issues.append("target root is inside restricted_target_roots")
    alias_record = None
    if selected_alias:
        alias_record = policy.get("aliases", {}).get(selected_alias)
        if not isinstance(alias_record, dict):
            issues.append("selected target alias is not registered in enterprise policy")
        elif Path(str(alias_record.get("root", ""))).expanduser().resolve() != root:
            issues.append("selected target alias does not match the resolved target root")
        elif alias_record.get("access", "read-write") != "read-write":
            issues.append("selected target alias is not writable")
    require_owner = bool(policy.get("require_declared_owner", False))
    owners = alias_record.get("owners", []) if isinstance(alias_record, dict) else []
    if require_owner and owners and actor not in owners:
        issues.append("declared actor is not an allowed owner for the selected target alias")
    identity = workspace().identity(root) if bool(policy.get("require_identity_verification", False)) else None
    return {
        "status": "blocked" if issues else "passed", "blocking": bool(issues),
        "root": root.as_posix(), "policy_path": loaded["path"], "policy_sha256": loaded["sha256"],
        "selected_alias": selected_alias, "actor": actor, "issues": issues,
        "identity_fingerprint": identity.get("fingerprint") if isinstance(identity, dict) else None,
        "boundary": "Local deterministic policy evaluation only. Declared actor labels are not authentication and policy does not upload workspace metadata.",
    }


def verify_bound(bound: dict[str, Any] | None, root: Path) -> dict[str, Any]:
    if not bound or bound.get("status") == "not-configured":
        return {"status": "not-configured", "blocking": False}
    loaded = load(Path(str(bound.get("policy_path", ""))))
    if not loaded or loaded["sha256"] != bound.get("policy_sha256"):
        return {"status": "changed", "blocking": True, "reason": "enterprise target policy changed after Planning Lock creation"}
    return evaluate(root, loaded, actor=bound.get("actor"), selected_alias=bound.get("selected_alias"))


def receipt(root: Path, run_id: str, *, target_identity: dict[str, Any], input_roles: dict[str, Any], policy_result: dict[str, Any], host_workspace: dict[str, Any] | None = None) -> dict[str, Any]:
    L = ledger()
    role_counts: dict[str, int] = {}
    for item in input_roles.get("inputs", []):
        if isinstance(item, dict):
            role = str(item.get("role", "unknown"))
            role_counts[role] = role_counts.get(role, 0) + 1
    payload = {
        "schema_version": "1", "type": "tailtrail-target-resolution-receipt", "run_id": run_id,
        "target": {"root": target_identity.get("root"), "fingerprint": target_identity.get("fingerprint"), "repository_kind": target_identity.get("repository_kind")},
        "policy": {key: policy_result.get(key) for key in ("status", "policy_path", "policy_sha256", "selected_alias", "issues")},
        "input_role_counts": role_counts,
        "host": {key: host_workspace.get(key) for key in ("host", "status", "workspace_kind", "mapping")} if isinstance(host_workspace, dict) else None,
        "boundary": "Sanitized receipt only: no raw prompt, source content, logs, credentials, user identity, or external reference URL is stored.",
    }
    path = L.state_dir(root.resolve(), run_id) / "planning" / "target-resolution-receipt-v1.json"
    L.atomic_json(path, payload)
    L.append_event(root.resolve(), run_id, "target_resolution_recorded", {"target_resolution_receipt": path.relative_to(root.resolve()).as_posix(), "policy_status": policy_result.get("status")})
    return {**payload, "artifact": path.relative_to(root.resolve()).as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("check")
    check.add_argument("--root", type=Path, required=True)
    check.add_argument("--policy", type=Path, required=True)
    check.add_argument("--actor")
    check.add_argument("--target-alias")
    check.add_argument("--format", choices=("markdown", "json"), default="json")
    args = parser.parse_args()
    if args.action == "check":
        payload = evaluate(args.root, load(args.policy), actor=args.actor, selected_alias=args.target_alias)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2 if payload["blocking"] else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
