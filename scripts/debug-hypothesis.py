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
DEFAULT_CYCLE_LIMIT = 3
OUTCOMES = {"strengthens", "eliminates", "unchanged", "regressed", "new-drift", "inconclusive"}


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = load("debug_hypothesis_ledger", "run-ledger.py")
REPRO = load("debug_hypothesis_reproduction", "debug-reproduction.py")
EVIDENCE = load("debug_hypothesis_evidence", "execution-evidence.py")
CONTINUITY = load("debug_hypothesis_continuity", "context-continuity.py")
GOVERNANCE = load("debug_hypothesis_governance", "debug-governance.py")


def ledger_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "hypotheses" / "hypothesis-ledger.json"


def experiments_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "experiments" / "debug-experiments.jsonl"


def proposals_directory(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "experiments" / "proposals"


def rankings_directory(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "hypotheses" / "rankings"


def recovery_directory(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "recovery-replan"


def _failure_fingerprint(root: Path, run_id: str) -> str:
    path = L.state_dir(root, run_id) / "debug" / "fingerprint" / "failure-fingerprint-v1.json"
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8")); fingerprint = str(value.get("fingerprint", "")).strip()
        if fingerprint: return fingerprint if fingerprint.startswith("sha256:") else "sha256:" + fingerprint
    contract = REPRO.read_existing(root, run_id) or {}
    fingerprint = str(contract.get("approved_fingerprint", "")).strip()
    if not fingerprint: raise ValueError("approved reproduction has no stable failure fingerprint")
    return fingerprint


def _requirement_uid(root: Path, run_id: str) -> str:
    contract = REPRO.read_existing(root, run_id) or {}
    uid = str(contract.get("requirement_uid", "")).strip()
    if not uid: raise ValueError("approved reproduction has no requirement UID")
    return uid


def read_ledger(root: Path, run_id: str) -> dict[str, Any]:
    path = ledger_path(root, run_id)
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8"))
        value.setdefault("requirement_uid", None); value.setdefault("failure_fingerprint", None)
        value.setdefault("cycle_limit", DEFAULT_CYCLE_LIMIT); value.setdefault("cycle", 1)
        value.setdefault("experiments_since_reset", 0); value.setdefault("investigation_blocked", False)
        value.setdefault("recovery_replan_ref", None)
        return value
    return {"schema_version": "1", "type": "tailtrail-hypothesis-ledger", "run_id": run_id, "requirement_uid": None, "failure_fingerprint": None, "cycle_limit": DEFAULT_CYCLE_LIMIT, "cycle": 1, "experiments_since_reset": 0, "investigation_blocked": False, "recovery_replan_ref": None, "hypotheses": [], "sequence": 0}


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
    ledger["requirement_uid"] = ledger.get("requirement_uid") or _requirement_uid(root, run_id)
    ledger["failure_fingerprint"] = ledger.get("failure_fingerprint") or _failure_fingerprint(root, run_id)
    ledger.setdefault("cycle", 1); ledger.setdefault("recovery_replan_ref", None)
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


def _continuity(root: Path, run_id: str, uid: str) -> dict[str, Any]:
    try:
        result = CONTINUITY.render(root, run_id, uid, "correction-cycle", 180)
        return {"status": "recorded", "state": result.get("state", {}).get("intervention_receipt")}
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return {"status": "unavailable", "reason": str(error)}


def _recovery_packet(root: Path, run_id: str, ledger: dict[str, Any]) -> str:
    directory = recovery_directory(root, run_id); revision = len(list(directory.glob("recovery-replan-v*.json"))) + 1
    experiments = [json.loads(line) for line in experiments_path(root, run_id).read_text(encoding="utf-8").splitlines() if line.strip()]
    payload = {"schema_version":"1", "type":"tailtrail-debug-recovery-replan", "run_id":run_id,
        "revision":revision, "requirement_uid":ledger["requirement_uid"], "failure_fingerprint":ledger["failure_fingerprint"],
        "cycle_exhausted":ledger["cycle"], "preserved_hypotheses":ledger["hypotheses"],
        "preserved_experiment_refs":[f"debug/experiments/debug-experiments.jsonl#{row['sequence']}" for row in experiments],
        "prior_mistakes":[row["action"] for row in experiments if row["outcome"] in {"unchanged","regressed","new-drift"}],
        "next":"Replan against the same approved reproduction and preserved evidence; do not restart or repeat an unchanged experiment.",
        "boundary":"Metadata-only Recovery/Replan packet. It preserves the approved reproduction, evidence, eliminated hypotheses, and prior mistakes; it does not run commands, edit source, or approve another cycle."}
    path = directory / f"recovery-replan-v{revision}.json"; L.atomic_json(path, payload)
    return path.relative_to(root).as_posix()


def record_experiment(root: Path, run_id: str, hypothesis_id: str, action: str, outcome: str, evidence_event_id: str, deterministic: bool, expected_signal: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    if not deterministic:
        raise ValueError("experiments must be deterministic; non-deterministic actions are rejected")
    if outcome not in OUTCOMES: raise ValueError(f"unsupported experiment outcome `{outcome}`")
    outcome = "unchanged" if outcome == "inconclusive" else outcome
    require_reproduction_approved(root, run_id)
    ledger = read_ledger(root, run_id)
    if ledger["investigation_blocked"]:
        raise ValueError("investigation is blocked by the cycle limit; run `replan --approved` before recording another experiment")
    row = _find(ledger, hypothesis_id)
    if row.get("status") != "open": raise ValueError("experiments may only target an open hypothesis")
    requirement_uid = ledger.get("requirement_uid") or _requirement_uid(root, run_id)
    failure_fingerprint = ledger.get("failure_fingerprint") or _failure_fingerprint(root, run_id)
    ledger["requirement_uid"] = requirement_uid; ledger["failure_fingerprint"] = failure_fingerprint
    ledger.setdefault("cycle", 1); ledger.setdefault("recovery_replan_ref", None)
    evidence_log = EVIDENCE.show(root, run_id)
    matched = next((event for event in evidence_log["events"] if event.get("fingerprint") == evidence_event_id), None)
    if matched is None:
        raise ValueError("evidence_event_id does not match a recorded execution-evidence event for this run; record real command/harness evidence first")
    if requirement_uid not in matched.get("requirement_uids", []):
        raise ValueError("execution evidence is not linked to this investigation requirement UID")
    experiments_file = experiments_path(root, run_id)
    existing = [json.loads(line) for line in experiments_file.read_text(encoding="utf-8").splitlines() if line.strip()] if experiments_file.is_file() else []
    expected_signal = str(expected_signal or "Observe a deterministic signal that distinguishes this hypothesis from its alternatives.").strip()
    identity = hashlib.sha256(json.dumps({"hypothesis_id":hypothesis_id,"action":action.strip(),"expected_signal":expected_signal,"failure_fingerprint":failure_fingerprint}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if any(item.get("experiment_fingerprint") == identity for item in existing):
        raise ValueError("identical experiment already ran against the same unchanged failure fingerprint; revise the discriminating action or replan")
    sequence = len(existing) + 1
    experiment = {"schema_version": "1", "type": "tailtrail-debug-experiment", "run_id": run_id, "sequence": sequence, "cycle": ledger["cycle"], "hypothesis_id": hypothesis_id, "requirement_uid": requirement_uid, "failure_fingerprint": failure_fingerprint, "action": action.strip(), "expected_signal": expected_signal, "deterministic": True, "outcome": outcome, "evidence_event_id": evidence_event_id, "experiment_fingerprint": identity, "evidence_boundary": f"Backed by execution-evidence fingerprint {evidence_event_id}."}
    experiments_file.parent.mkdir(parents=True, exist_ok=True)
    with experiments_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(experiment, sort_keys=True, separators=(",", ":")) + "\n")
    note = f"{action} (evidence:{evidence_event_id})"
    if outcome == "eliminates":
        row["status"] = "eliminated"
        row["contradicting_evidence"].append(note)
    elif outcome == "strengthens" and row["status"] == "open":
        row["supporting_evidence"].append(note)
    elif outcome in {"regressed", "new-drift"}:
        row["contradicting_evidence"].append(note)
    ledger["experiments_since_reset"] += 1
    ledger["sequence"] = sequence
    if ledger["experiments_since_reset"] >= ledger["cycle_limit"]:
        ledger["investigation_blocked"] = True
        ledger["recovery_replan_ref"] = _recovery_packet(root, run_id, ledger)
    if outcome in {"unchanged", "regressed", "new-drift"}:
        experiment["continuity"] = _continuity(root, run_id, requirement_uid)
    L.atomic_json(ledger_path(root, run_id), ledger)
    L.append_event(root, run_id, "debug_experiment_recorded", {"hypothesis_id": hypothesis_id, "sequence": sequence, "outcome": outcome})
    if ledger["investigation_blocked"]:
        L.append_event(root, run_id, "debug_investigation_blocked", {"cycle_limit": ledger["cycle_limit"], "experiments_since_reset": ledger["experiments_since_reset"], "recovery_replan_ref": ledger["recovery_replan_ref"]})
    GOVERNANCE.build(root, run_id)
    return ledger


def reprioritize(root: Path, run_id: str, rankings: list[dict[str, Any]]) -> dict[str, Any]:
    """Save and apply an explicit complete ordering without erasing ledger history."""
    root = root.resolve(); require_reproduction_approved(root, run_id)
    ledger = read_ledger(root, run_id)
    expected = {row["hypothesis_id"] for row in ledger["hypotheses"] if row.get("status") == "open"}
    supplied = [str(row.get("hypothesis_id", "")).strip() for row in rankings]
    ranks = [row.get("rank") for row in rankings]
    if set(supplied) != expected or len(supplied) != len(set(supplied)):
        raise ValueError("reprioritization must include every open hypothesis exactly once")
    if not all(isinstance(rank, int) and rank > 0 for rank in ranks) or len(ranks) != len(set(ranks)):
        raise ValueError("reprioritization ranks must be unique positive integers")
    by_id = {row["hypothesis_id"]: row["rank"] for row in rankings}
    previous = {row["hypothesis_id"]: row.get("rank") for row in ledger["hypotheses"]}
    for row in ledger["hypotheses"]:
        if row["hypothesis_id"] in by_id: row["rank"] = by_id[row["hypothesis_id"]]
    revision = len(list(rankings_directory(root, run_id).glob("ranking-v*.json"))) + 1
    payload = {"schema_version":"1", "type":"tailtrail-debug-hypothesis-ranking", "run_id":run_id,
        "revision":revision, "requirement_uid":ledger.get("requirement_uid") or _requirement_uid(root, run_id),
        "failure_fingerprint":ledger.get("failure_fingerprint") or _failure_fingerprint(root, run_id),
        "previous_ranks":previous, "rankings":sorted(rankings, key=lambda item:item["rank"]),
        "boundary":"Metadata ordering only. No experiment or project command was run."}
    path = rankings_directory(root, run_id) / f"ranking-v{revision}.json"
    L.atomic_json(path, payload); L.atomic_json(ledger_path(root, run_id), ledger)
    L.append_event(root, run_id, "debug_hypotheses_reprioritized", {"revision":revision})
    return {**payload, "artifact":path.relative_to(root).as_posix()}


def propose_experiment(root: Path, run_id: str, hypothesis_id: str, action: str, expected_signal: str) -> dict[str, Any]:
    """Persist a deterministic experiment proposal; execution remains external."""
    root = root.resolve(); require_reproduction_approved(root, run_id)
    ledger = read_ledger(root, run_id); hypothesis = _find(ledger, hypothesis_id)
    if hypothesis.get("status") != "open": raise ValueError("experiments may only be proposed for an open hypothesis")
    action = action.strip(); expected_signal = expected_signal.strip()
    if not action or not expected_signal: raise ValueError("experiment proposal requires action and expected_signal")
    fingerprint = hashlib.sha256(json.dumps({"hypothesis_id":hypothesis_id,"action":action,
        "expected_signal":expected_signal,"failure_fingerprint":ledger.get("failure_fingerprint") or _failure_fingerprint(root, run_id)},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    existing = list(proposals_directory(root, run_id).glob("proposal-v*.json")); revision = len(existing) + 1
    payload = {"schema_version":"1", "type":"tailtrail-debug-experiment-proposal", "run_id":run_id,
        "revision":revision, "hypothesis_id":hypothesis_id,
        "requirement_uid":ledger.get("requirement_uid") or _requirement_uid(root, run_id),
        "failure_fingerprint":ledger.get("failure_fingerprint") or _failure_fingerprint(root, run_id),
        "action":action, "expected_signal":expected_signal, "deterministic":True,
        "experiment_fingerprint":fingerprint,
        "boundary":"Proposal only. The host must separately approve and execute any safe command, record factual execution evidence, then record the outcome."}
    path = proposals_directory(root, run_id) / f"proposal-v{revision}.json"
    L.atomic_json(path, payload); hypothesis["next_experiment"] = path.relative_to(root).as_posix(); L.atomic_json(ledger_path(root, run_id), ledger)
    L.append_event(root, run_id, "debug_experiment_proposed", {"hypothesis_id":hypothesis_id,"revision":revision})
    return {**payload, "artifact":path.relative_to(root).as_posix()}


def replan(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    root = root.resolve()
    ledger = read_ledger(root, run_id)
    if not ledger["investigation_blocked"]:
        raise ValueError("investigation is not currently blocked")
    if not approved:
        raise ValueError("resuming a blocked investigation requires --approved")
    ledger["investigation_blocked"] = False
    ledger["experiments_since_reset"] = 0
    ledger["cycle"] = int(ledger.get("cycle", 1)) + 1
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
    experiment_parser.add_argument("--expected-signal")
    experiment_parser.add_argument("--outcome", required=True, choices=sorted(OUTCOMES))
    experiment_parser.add_argument("--evidence-event-id", required=True)
    experiment_parser.add_argument("--deterministic", action="store_true")

    proposal_parser = sub.add_parser("propose")
    proposal_parser.add_argument("--root", type=Path, default=Path.cwd())
    proposal_parser.add_argument("--run-id", required=True)
    proposal_parser.add_argument("--hypothesis-id", required=True)
    proposal_parser.add_argument("--experiment-action", required=True)
    proposal_parser.add_argument("--expected-signal", required=True)
    proposal_parser.add_argument("--approved", action="store_true")

    ranking_parser = sub.add_parser("reprioritize")
    ranking_parser.add_argument("--root", type=Path, default=Path.cwd())
    ranking_parser.add_argument("--run-id", required=True)
    ranking_parser.add_argument("--input", type=Path, required=True, help="JSON array of hypothesis_id/rank objects")
    ranking_parser.add_argument("--approved", action="store_true")

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
            result = record_experiment(args.root, args.run_id, args.hypothesis_id, args.experiment_action, args.outcome, args.evidence_event_id, args.deterministic, args.expected_signal)
        elif args.action == "propose":
            if not args.approved: raise ValueError("proposing an experiment requires --approved")
            result = propose_experiment(args.root, args.run_id, args.hypothesis_id, args.experiment_action, args.expected_signal)
        elif args.action == "reprioritize":
            if not args.approved: raise ValueError("reprioritizing hypotheses requires --approved")
            rankings = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(rankings, list): raise ValueError("--input must contain a JSON array")
            result = reprioritize(args.root, args.run_id, rankings)
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
