#!/usr/bin/env python3
"""Build the DI-10 Debug token/privacy/continuity governance receipt."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


L = load("debug_governance_ledger", "run-ledger.py")
TOKEN = load("debug_governance_token_harness", "token-harness.py")


def _read(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def _rel(root: Path, path: Path) -> str: return path.relative_to(root).as_posix()
def artifact_path(root: Path, run_id: str) -> Path: return L.state_dir(root.resolve(), run_id) / "debug" / "governance" / "governance-v1.json"


def build(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); directory = L.state_dir(root, run_id); debug = directory / "debug"
    intake_path = debug / "intake" / "debug-intake-v1.json"; fingerprint_path = debug / "fingerprint" / "failure-fingerprint-v1.json"
    if not intake_path.is_file() or not fingerprint_path.is_file(): raise ValueError("Debug intake and sanitized failure fingerprint are required")
    intake = _read(intake_path); fingerprint = _read(fingerprint_path)
    experiments_path = debug / "experiments" / "debug-experiments.jsonl"
    experiments = [json.loads(line) for line in experiments_path.read_text(encoding="utf-8").splitlines() if line.strip()] if experiments_path.is_file() else []
    identities = [str(row.get("experiment_fingerprint")) for row in experiments if row.get("experiment_fingerprint")]
    ledger_path = debug / "hypotheses" / "hypothesis-ledger.json"; ledger = _read(ledger_path) if ledger_path.is_file() else {"hypotheses": []}
    continuity = sorted((directory / "continuity").glob("state-*.json"))
    exact_refs = [_rel(root, intake_path)]
    if experiments_path.is_file(): exact_refs.append(_rel(root, experiments_path))
    exact_bytes = sum((root / ref).stat().st_size for ref in exact_refs)
    telemetry = root / ".tailtrail" / "token-usage.jsonl"; measured: list[int] = []
    if telemetry.is_file():
        for line in telemetry.read_text(encoding="utf-8").splitlines():
            try: row = json.loads(line)
            except json.JSONDecodeError: continue
            value = (row.get("tailtrail") or {}).get("total_tokens") if row.get("mode") == "measured" and row.get("task_id") == run_id else None
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0: measured.append(value)
    exactness, exactness_reason = TOKEN.classify_exactness("debug-diagnostic", exact_bytes, "")
    payload = {
        "schema_version":"1", "type":"tailtrail-debug-governance", "run_id":run_id,
        "privacy": {"status":"classified", "sensitive": bool((intake.get("privacy") or {}).get("sensitive")), "categories": (intake.get("privacy") or {}).get("categories", []), "exact_local_refs":exact_refs, "portable_fingerprint_ref":_rel(root, fingerprint_path), "portable_values":False},
        "token_posture": {"estimate_tokens":(exact_bytes + 3) // 4, "actual_status":"measured" if measured else "unavailable", "actual_tokens":sum(measured) if measured else None, "telemetry_records":len(measured), "exactness":[{"class":exactness, "refs":exact_refs, "reason":exactness_reason}, {"class":"reduce-safe", "refs":[], "rule":"Repeated surrounding noise may be reduced only with an exact retrieval reference."}], "boundary":"Uses the canonical Token Harness exactness classifier. Actual tokens are reported only from host/provider telemetry linked by this run ID; byte-derived context size remains an estimate."},
        "continuity": {"experiment_count":len(experiments), "unique_experiment_fingerprints":len(set(identities)), "duplicate_experiments_prevented":len(identities)-len(set(identities)), "eliminated_hypothesis_ids":[row.get("hypothesis_id") for row in ledger.get("hypotheses", []) if row.get("status") == "eliminated"], "do_not_repeat_fingerprints":sorted(set(identities)), "continuity_refs":[_rel(root, path) for path in continuity], "recovery_replan_ref":ledger.get("recovery_replan_ref")},
        "learning": {"eligible":"only-after-canonical-accepted-closure", "promotion":"candidate-only", "allowed_fields":["sanitized failure fingerprint", "proven cause class", "validation tiers", "acceptance source", "domain-capped confidence"], "forbidden_fields":["raw prompt", "raw log", "source", "repository identity", "user/customer identity", "credential", "secret"]},
        "boundary":"Run-local governance metadata only. Exact diagnostic evidence remains retrievable locally; no raw value is copied into portable fingerprint, continuity, learning, or evaluation data.",
    }
    stable = {key:value for key,value in payload.items() if key != "governance_fingerprint"}; payload["governance_fingerprint"] = "sha256:" + hashlib.sha256(json.dumps(stable,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    L.atomic_json(artifact_path(root, run_id), payload); L.append_event(root, run_id, "debug_governance_recorded", {"artifact":_rel(root,artifact_path(root,run_id)), "actual_token_status":payload["token_posture"]["actual_status"], "experiment_count":len(experiments)})
    return payload


def show(root: Path, run_id: str) -> dict[str, Any]:
    path=artifact_path(root.resolve(),run_id)
    if not path.is_file():
        return {"schema_version":"1", "type":"tailtrail-debug-governance-status", "run_id":run_id,
            "status":"not-created", "lifecycle_classification":"not-yet-expected",
            "expected_after_stage":"d-09-regression-validation",
            "reason":"Governance is finalized from saved diagnostic evidence, token posture, continuity, and correction outcomes near closure.",
            "next":"Record factual experiment and correction evidence before building governance.",
            "boundary":"Read-only absence receipt. No governance, learning, or token telemetry was inferred."}
    return _read(path)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("action",choices=("build","show")); parser.add_argument("--root",type=Path,default=Path.cwd()); parser.add_argument("--run-id",required=True); args=parser.parse_args()
    try: print(json.dumps(build(args.root,args.run_id) if args.action=="build" else show(args.root,args.run_id),indent=2,sort_keys=True)); return 0
    except (OSError,ValueError,json.JSONDecodeError) as error: print(f"Debug governance error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
