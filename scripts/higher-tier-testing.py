#!/usr/bin/env python3
"""Run one declared higher-tier repository command and record sanitized evidence."""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HIGHER_TIERS = {"integration", "contract", "e2e", "infrastructure", "release-smoke"}
ADAPTERS = {"integration", "contract", "e2e", "infrastructure", "release-smoke"}


def load_script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


LEDGER = load_script("run-ledger")
PROFILE = load_script("testing-profile")


def tier_from(profile_path: Path, name: str) -> dict[str, Any]:
    profile = PROFILE.load(profile_path)
    tier = next((item for item in profile["tiers"] if item["name"] == name), None)
    if tier is None:
        raise ValueError(f"tier `{name}` is not declared in the repository profile")
    if name not in HIGHER_TIERS:
        raise ValueError("higher-tier runner accepts integration, contract, e2e, infrastructure, or release-smoke only")
    adapter = str(tier.get("adapter", name))
    if adapter not in ADAPTERS:
        raise ValueError("tier adapter must be integration, contract, e2e, infrastructure, or release-smoke")
    if not tier["command"] or not all(isinstance(item, str) and item for item in tier["command"]):
        raise ValueError("declared tier command must be a non-empty argv list")
    return tier


def payload(run_id: str, requirement_uid: str, tier: dict[str, Any], asserted_behavior: str, outcome: str, exit_code: int | None, reason: str = "") -> dict[str, Any]:
    return {
        "schema_version": "1", "type": "tailtrail-validation-evidence-receipt",
        "requirement_uid": requirement_uid, "tier": tier["name"], "adapter": tier.get("adapter", tier["name"]),
        "command": " ".join(tier["command"]), "outcome": outcome, "environment": tier["environment"],
        "asserted_behavior": asserted_behavior, "prerequisites": tier.get("prerequisites", []),
        "cleanup": tier.get("cleanup", []), "remote": bool(tier.get("remote", False)),
        "safe_test_account": bool(tier.get("safe_test_account", False)), "exit_code": exit_code,
        "reason": reason, "evidence_label": "repository-declared-command",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "boundary": "receipt stores no command output, credentials, tokens, or test-account identifiers",
    }


def record(root: Path, run_id: str, item: dict[str, Any]) -> dict[str, Any]:
    directory = LEDGER.state_dir(root, run_id) / "validation-receipts"
    artifact = directory / f"{item['requirement_uid']}-{item['tier']}-{len(list(directory.glob('*.json'))) + 1}.json"
    LEDGER.atomic_json(artifact, item)
    LEDGER.append_event(root, run_id, "higher_tier_executed", {"artifact": artifact.relative_to(LEDGER.state_dir(root, run_id)).as_posix(), "requirement_uid": item["requirement_uid"], "tier": item["tier"], "adapter": item["adapter"], "outcome": item["outcome"], "exit_code": item["exit_code"]})
    return {**item, "run_artifact": artifact.as_posix()}


def plan(profile_path: Path, tier_name: str) -> dict[str, Any]:
    tier = tier_from(profile_path, tier_name)
    return {"schema_version": "1", "type": "tailtrail-higher-tier-plan", "tier": tier["name"], "adapter": tier.get("adapter", tier["name"]), "command": tier["command"], "environment": tier["environment"], "prerequisites": tier["prerequisites"], "cleanup": tier["cleanup"], "requires_approval": bool(tier["requires_approval"]), "remote": bool(tier.get("remote", False)), "safe_test_account_required": bool(tier.get("remote", False)), "boundary": "TailTrail uses only this repository-declared argv command; it never provisions an environment or invents a command"}


def execute(root: Path, run_id: str, profile_path: Path, tier_name: str, requirement_uid: str, asserted_behavior: str, approved: bool, remote_approved: bool) -> dict[str, Any]:
    tier = tier_from(profile_path, tier_name)
    if tier.get("requires_approval", False) and not approved:
        raise ValueError("declared higher-tier command requires --approved")
    if tier.get("remote", False) and (not remote_approved or not tier.get("safe_test_account", False)):
        return record(root, run_id, payload(run_id, requirement_uid, tier, asserted_behavior, "blocked", None, "remote adapter needs --remote-approved and safe_test_account: true in the profile"))
    timeout = int(tier.get("timeout_seconds", 120))
    try:
        result = subprocess.run(tier["command"], cwd=root, text=True, capture_output=True, check=False, timeout=timeout)
        outcome = "pass" if result.returncode == 0 else "fail"
        reason = "repository-declared command completed" if outcome == "pass" else "repository-declared command returned a non-zero exit code"
        return record(root, run_id, payload(run_id, requirement_uid, tier, asserted_behavior, outcome, result.returncode, reason))
    except FileNotFoundError:
        return record(root, run_id, payload(run_id, requirement_uid, tier, asserted_behavior, "unavailable", None, "declared command is unavailable on this host"))
    except subprocess.TimeoutExpired:
        return record(root, run_id, payload(run_id, requirement_uid, tier, asserted_behavior, "timed-out", None, f"declared command exceeded {timeout} seconds"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or run one repository-declared higher-tier adapter.")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("plan", "run"):
        item = sub.add_parser(action); item.add_argument("--profile", type=Path, required=True); item.add_argument("--tier", required=True)
        if action == "run":
            item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True); item.add_argument("--requirement-uid", required=True); item.add_argument("--asserted-behavior", required=True); item.add_argument("--approved", action="store_true"); item.add_argument("--remote-approved", action="store_true")
    args = parser.parse_args()
    try:
        result = plan(args.profile, args.tier) if args.action == "plan" else execute(args.root.resolve(), args.run_id, args.profile, args.tier, args.requirement_uid, args.asserted_behavior, args.approved, args.remote_approved)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Higher-tier testing error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
