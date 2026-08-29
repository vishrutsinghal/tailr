#!/usr/bin/env python3
"""Debug Harness hypothesis ledger, bounded experiment loop, and replan gate.

Enforces the harness's central rule: every experiment must reference a real,
already-recorded `execution-evidence` event (never an agent-asserted string),
and a hypothesis can only be marked `proven` once it has real supporting
evidence *and* at least one competing hypothesis was actually eliminated
(DEBUG-HARNESS.md Section 12, "confusing correlation with causation")."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_DOMAINS = {"code", "architecture", "database", "api-integration"}
DEFAULT_CYCLE_LIMIT = 5


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = load("debug_hypothesis_ledger", "run-ledger.py")
REPRO = load("debug_hypothesis_reproduction", "debug-reproduction.py")
EVIDENCE = load("debug_hypothesis_evidence", "execution-evidence.py")


def ledger_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "hypotheses" / "hypothesis-ledger.json"


def experiments_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "experiments" / "debug-experiments.jsonl"


def read_ledger(root: Path, run_id: str) -> dict[str, Any]:
    path = ledger_path(root, run_id)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": "1", "type": "tailtrail-hypothesis-ledger", "run_id": run_id, "cycle_limit": DEFAULT_CYCLE_LIMIT, "experiments_since_reset": 0, "investigation_blocked": False, "hypotheses": [], "sequence": 0}


def require_reproduction_approved(root: Path, run_id: str) -> None:
    contract = REPRO.read_existing(root, run_id)
    if contract is None or contract.get("status") != "approved":
        raise ValueError("no approved reproduction contract for this run; approve one before opening the hypothesis ledger")


def domain_evidence_status(domain: str) -> dict[str, Any]:
    """Honest, read-only disclosure of what deeper evidence is actually reachable per domain (Section 7.6/7.7)."""
    if domain == "database":
        available = bool(os.environ.get("TAILTRAIL_DEBUG_DB_URL"))
        return {"domain": domain, "live_evidence_available": available, "reason": None if available else "No local database connection configured (set TAILTRAIL_DEBUG_DB_URL) to enable EXPLAIN-based experiments; falling back to Code Graph Mapper's cached schema/table hints only."}
    if domain == "api-integration":
        return {"domain": domain, "live_evidence_available": False, "reason": "API experiments in this build run only against recorded fixtures/contract tests, never live third-party endpoints."}
    return {"domain": domain, "live_evidence_available": True, "reason": None}


def add_hypothesis(root: Path, run_id: str, domain: str, statement: str, rank: int) -> dict[str, Any]:
    root = root.resolve()
    if domain not in SUPPORTED_DOMAINS:
        raise ValueError(f"domain `{domain}` is not supported by this Debug Harness build; supported domains: {sorted(SUPPORTED_DOMAINS)}")
    require_reproduction_approved(root, run_id)
    ledger = read_ledger(root, run_id)
    hypothesis_id = "h-" + hashlib.sha256(f"{run_id}:{statement.strip()}".encode("utf-8")).hexdigest()[:12]
    if any(row["hypothesis_id"] == hypothesis_id for row in ledger["hypotheses"]):
        raise ValueError("an identical hypothesis already exists for this run")
    ledger["hypotheses"].append({"hypothesis_id": hypothesis_id, "domain": domain, "statement": statement.strip(), "rank": rank, "supporting_evidence": [], "contradicting_evidence": [], "next_experiment": None, "status": "open"})
    L.atomic_json(ledger_path(root, run_id), ledger)
    L.append_event(root, run_id, "debug_hypothesis_added", {"hypothesis_id": hypothesis_id, "domain": domain})
    return ledger


def _find(ledger: dict[str, Any], hypothesis_id: str) -> dict[str, Any]:
    for row in ledger["hypotheses"]:
        if row["hypothesis_id"] == hypothesis_id:
            return row
    raise ValueError(f"hypothesis `{hypothesis_id}` does not exist on this run's ledger")


def record_experiment(root: Path, run_id: str, hypothesis_id: str, action: str, outcome: str, evidence_event_id: str, deterministic: bool) -> dict[str, Any]:
    root = root.resolve()
    if not deterministic:
        raise ValueError("experiments must be deterministic; non-deterministic actions are rejected")
    require_reproduction_approved(root, run_id)
    ledger = read_ledger(root, run_id)
    if ledger["investigation_blocked"]:
        raise ValueError("investigation is blocked by the cycle limit; run `replan --approved` before recording another experiment")
    row = _find(ledger, hypothesis_id)
    evidence_log = EVIDENCE.show(root, run_id)
    matched = next((event for event in evidence_log["events"] if event.get("fingerprint") == evidence_event_id), None)
    if matched is None:
        raise ValueError("evidence_event_id does not match a recorded execution-evidence event for this run; record real command/harness evidence first")
    experiments_file = experiments_path(root, run_id)
    existing = [json.loads(line) for line in experiments_file.read_text(encoding="utf-8").splitlines() if line.strip()] if experiments_file.is_file() else []
    sequence = len(existing) + 1
    experiment = {"schema_version": "1", "type": "tailtrail-debug-experiment", "run_id": run_id, "sequence": sequence, "hypothesis_id": hypothesis_id, "action": action, "deterministic": True, "outcome": outcome, "evidence_event_id": evidence_event_id, "evidence_boundary": f"Backed by execution-evidence fingerprint {evidence_event_id}."}
    experiments_file.parent.mkdir(parents=True, exist_ok=True)
    with experiments_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(experiment, sort_keys=True, separators=(",", ":")) + "\n")
    note = f"{action} (evidence:{evidence_event_id})"
    if outcome == "eliminates":
        row["status"] = "eliminated"
        row["contradicting_evidence"].append(note)
    elif outcome == "strengthens" and row["status"] == "open":
        row["supporting_evidence"].append(note)
    ledger["experiments_since_reset"] += 1
    ledger["sequence"] = sequence
    if ledger["experiments_since_reset"] >= ledger["cycle_limit"]:
        ledger["investigation_blocked"] = True
    L.atomic_json(ledger_path(root, run_id), ledger)
    L.append_event(root, run_id, "debug_experiment_recorded", {"hypothesis_id": hypothesis_id, "sequence": sequence, "outcome": outcome})
    if ledger["investigation_blocked"]:
        L.append_event(root, run_id, "debug_investigation_blocked", {"cycle_limit": ledger["cycle_limit"], "experiments_since_reset": ledger["experiments_since_reset"]})
    return ledger


def replan(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    root = root.resolve()
    ledger = read_ledger(root, run_id)
    if not ledger["investigation_blocked"]:
        raise ValueError("investigation is not currently blocked")
    if not approved:
        raise ValueError("resuming a blocked investigation requires --approved")
    ledger["investigation_blocked"] = False
    ledger["experiments_since_reset"] = 0
    L.atomic_json(ledger_path(root, run_id), ledger)
    L.append_event(root, run_id, "debug_replan_approved", {})
    return ledger


def prove(root: Path, run_id: str, hypothesis_id: str) -> dict[str, Any]:
    root = root.resolve()
    ledger = read_ledger(root, run_id)
    row = _find(ledger, hypothesis_id)
    if row["status"] != "open":
        raise ValueError(f"hypothesis `{hypothesis_id}` is `{row['status']}`, not open; only an open hypothesis can be proven")
    if not row["supporting_evidence"]:
        raise ValueError("hypothesis has no recorded supporting evidence; run a `strengthens` experiment first")
    if not any(other["status"] == "eliminated" for other in ledger["hypotheses"] if other["hypothesis_id"] != hypothesis_id):
        raise ValueError("no competing hypothesis has been eliminated yet; root cause proof requires ruling out at least one alternative")
    row["status"] = "proven"
    L.atomic_json(ledger_path(root, run_id), ledger)
    L.append_event(root, run_id, "debug_root_cause_proven", {"hypothesis_id": hypothesis_id, "domain": row["domain"]})
    return ledger


def show(root: Path, run_id: str) -> dict[str, Any]:
    return read_ledger(root.resolve(), run_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    add_parser = sub.add_parser("add")
    add_parser.add_argument("--root", type=Path, default=Path.cwd())
    add_parser.add_argument("--run-id", required=True)
    add_parser.add_argument("--domain", required=True)
    add_parser.add_argument("--statement", required=True)
    add_parser.add_argument("--rank", type=int, default=1)

    experiment_parser = sub.add_parser("experiment")
    experiment_parser.add_argument("--root", type=Path, default=Path.cwd())
    experiment_parser.add_argument("--run-id", required=True)
    experiment_parser.add_argument("--hypothesis-id", required=True)
    experiment_parser.add_argument("--experiment-action", required=True)
    experiment_parser.add_argument("--outcome", required=True, choices=["eliminates", "strengthens", "inconclusive"])
    experiment_parser.add_argument("--evidence-event-id", required=True)
    experiment_parser.add_argument("--deterministic", action="store_true")

    replan_parser = sub.add_parser("replan")
    replan_parser.add_argument("--root", type=Path, default=Path.cwd())
    replan_parser.add_argument("--run-id", required=True)
    replan_parser.add_argument("--approved", action="store_true")

    prove_parser = sub.add_parser("prove")
    prove_parser.add_argument("--root", type=Path, default=Path.cwd())
    prove_parser.add_argument("--run-id", required=True)
    prove_parser.add_argument("--hypothesis-id", required=True)

    domain_status_parser = sub.add_parser("domain-status")
    domain_status_parser.add_argument("--domain", required=True)

    show_parser = sub.add_parser("show")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)

    args = parser.parse_args()
    try:
        if args.action == "add":
            result = add_hypothesis(args.root, args.run_id, args.domain, args.statement, args.rank)
        elif args.action == "experiment":
            result = record_experiment(args.root, args.run_id, args.hypothesis_id, args.experiment_action, args.outcome, args.evidence_event_id, args.deterministic)
        elif args.action == "replan":
            result = replan(args.root, args.run_id, args.approved)
        elif args.action == "prove":
            result = prove(args.root, args.run_id, args.hypothesis_id)
        elif args.action == "domain-status":
            result = domain_evidence_status(args.domain)
        else:
            result = show(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Debug hypothesis error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
