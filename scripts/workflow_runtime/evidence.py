"""DWR-3 evidence, freshness, resume, correction, and closure bridge.

This is a control-plane adapter over existing TailTrail artifacts.  It never
executes a compiled stage, retries a command, mutates project source, or turns
missing evidence into a pass.  The durable record contains references and
hashes only; host-supplied execution facts remain in their existing run log.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from workflow_runtime import compiler, contracts, evidence_completion, ownership, storage, task_scope


LEDGER = ownership.LEDGER
CHANGE_TYPES = {
    "source-edit", "manifest-change", "policy-change", "graph-stale",
    "doc-only-edit", "branch-change", "dependency-add", "security-finding",
}


def _load(name: str, filename: str) -> Any:
    scripts = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(name, scripts / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


EXECUTION = _load("dwr3_execution_evidence", "execution-evidence.py")
CLOSURE = _load("dwr3_closure_report", "completion-report.py")
CORRECTION = _load("dwr3_closure_correction", "closure-correction.py")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _directory(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent


def evidence_path(root: Path, workflow_id: str) -> Path:
    return _directory(root, workflow_id) / "evidence-v1.json"


def receipt_path(root: Path, workflow_id: str) -> Path:
    return _directory(root, workflow_id) / "completion-receipt-v1.json"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact(root: Path, path: Path) -> dict[str, str] | None:
    if not path.is_file():
        return None
    relative = _relative(root, path)
    if not relative.startswith(".tailtrail/"):
        raise ValueError("DWR-3 may reference only local .tailtrail artifacts")
    return {"ref": relative, "hash": _file_hash(path)}


def _latest(root: Path, run_id: str, folder: str, pattern: str) -> dict[str, str] | None:
    directory = LEDGER.state_dir(root, run_id) / folder
    items = sorted(directory.glob(pattern)) if directory.is_dir() else []
    return _artifact(root, items[-1]) if items else None


def _downstream(stages: list[dict[str, Any]], roots: set[str]) -> set[str]:
    selected = set(roots)
    changed = True
    while changed:
        changed = False
        for stage in stages:
            stage_id = str(stage["stage_id"])
            if stage_id not in selected and set(stage.get("prerequisites", [])) & selected:
                selected.add(stage_id); changed = True
    return selected


def _affected(stages: list[dict[str, Any]], change_type: str) -> set[str]:
    names = {str(stage["stage_id"]) for stage in stages}
    if change_type == "doc-only-edit":
        return set()
    if change_type in {"branch-change", "policy-change"}:
        return names
    if change_type in {"manifest-change", "dependency-add", "graph-stale"}:
        return _downstream(stages, {"discover", "graph-impact"} & names)
    if change_type == "source-edit":
        return _downstream(stages, {"implement"} & names)
    if change_type == "security-finding":
        return _downstream(stages, ({"security"} if "security" in names else {"review"}) & names)
    raise ValueError(f"unsupported freshness change type `{change_type}`")


def _artifact_refs(root: Path, run_id: str) -> dict[str, dict[str, str]]:
    state = LEDGER.state_dir(root, run_id)
    refs: dict[str, dict[str, str]] = {}
    candidates = {
        "execution_evidence": state / "execution" / "evidence-stream.jsonl",
        "architecture": _latest(root, run_id, "architecture", "assessment-*.json"),
        "behaviour": _latest(root, run_id, "behavior", "assessment-*.json"),
        "maintainability": _latest(root, run_id, "maintainability", "assessment-*.json"),
        "checkpoint": _latest(root, run_id, "checkpoints", "checkpoint-*.json"),
        "review": _latest(root, run_id, "reviews", "review-*.json"),
        "completion_gate": _latest(root, run_id, "completion-gates", "gate-*.json"),
        "correction": _latest(root, run_id, "closure-corrections", "correction-*.json"),
        "recovery": _artifact(root, state / "recovery" / "boundary.json"),
        "completion_report": _latest(root, run_id, "completion-reports", "report-*.json"),
        "ci": _latest(root, run_id, "ci", "*.json"),
    }
    stream = _artifact(root, candidates.pop("execution_evidence"))
    if stream:
        refs["execution_evidence"] = stream
    for name, value in candidates.items():
        if value:
            refs[name] = value
    return refs


def _stage_statuses(root: Path, run_id: str, plan: dict[str, Any], refs: dict[str, dict[str, str]], prior: dict[str, Any] | None) -> list[dict[str, Any]]:
    events = EXECUTION.show(root, run_id).get("events", [])
    source = any(item.get("kind") == "source-edit" for item in events)
    passing = any(item.get("kind") in {"command-result", "ci-receipt"} and item.get("outcome") == "pass" for item in events)
    has_review = "review" in refs
    has_completion = "completion_report" in refs
    prior_rows = {str(item.get("stage_id")): item for item in (prior or {}).get("stages", []) if isinstance(item, dict)}
    relevant_by_stage = {
        "bootstrap": set(),
        "discover": {"checkpoint"},
        "graph-impact": {"checkpoint"},
        "clarify": {"checkpoint"},
        "implement": {"execution_evidence", "checkpoint", "correction", "recovery"},
        "focused-test": {"execution_evidence", "completion_gate", "ci"},
        "tests": {"execution_evidence", "completion_gate", "ci"},
        "security": {"execution_evidence", "ci"},
        "review": {"review", "architecture", "behaviour", "maintainability", "execution_evidence"},
        "fulfilment": {"checkpoint", "review", "completion_gate", "completion_report"},
    }
    rows: list[dict[str, Any]] = []
    for stage in plan["stages"]:
        stage_id = str(stage["stage_id"])
        passed = stage_id == "bootstrap" or (stage_id == "implement" and source) or (stage_id in {"focused-test", "tests"} and passing) or (stage_id == "review" and has_review) or (stage_id == "fulfilment" and has_completion)
        prior_row = prior_rows.get(stage_id, {})
        status = "stale" if prior_row.get("status") == "stale" else ("passed" if passed else "pending")
        relevant = sorted(set(refs) & relevant_by_stage.get(stage_id, set()))
        stable = {"stage_id": stage_id, "stage_fingerprint": _hash(stage), "evidence_refs": {name: refs[name] for name in relevant}}
        rows.append({"stage_id": stage_id, "status": status, "evidence_refs": sorted(refs), "freshness_hash": _hash(stable)})
    return rows


def collect(root: Path, workflow_id: str) -> dict[str, Any]:
    """Capture references to existing evidence without running any control."""
    root = root.resolve(); binding = ownership.show(root, workflow_id); plan = compiler.show(root, workflow_id)
    # DWR-2 intentionally did not capture execution scope. DWR-3 captures it
    # at the first evidence checkpoint, after the canonical anchor exists.
    try:
        task_scope.show(root, workflow_id)
    except ValueError as error:
        if "does not exist" not in str(error):
            raise
        task_scope.initialize(root, workflow_id)
    prior = show(root, workflow_id, missing_ok=True)
    refs = _artifact_refs(root, binding["tailtrail_run_id"])
    payload = {
        "schema_version": "1", "type": "tailtrail-workflow-evidence", "workflow_id": workflow_id,
        "tailtrail_run_id": binding["tailtrail_run_id"], "compiler_plan_fingerprint": plan["plan_fingerprint"],
        "artifact_refs": refs, "stages": _stage_statuses(root, binding["tailtrail_run_id"], plan, refs, prior),
        "freshness_events": list((prior or {}).get("freshness_events", [])),
        "boundary": "DWR-3 records hashes and references to existing TailTrail evidence only. It does not run a test, retry a command, execute a stage, or infer missing proof.",
    }
    payload["evidence_fingerprint"] = _hash({key: value for key, value in payload.items() if key != "evidence_fingerprint"})
    contracts.require_valid(payload)
    path = evidence_path(root, workflow_id)
    if path.is_file() and _read(path).get("evidence_fingerprint") == payload["evidence_fingerprint"]:
        return {"artifact": _relative(root, path), **_read(path), "reused": True}
    LEDGER.atomic_json(path, payload)
    storage.capture(root, workflow_id)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_evidence_collected", {"workflow_id": workflow_id, "artifact": _relative(root, path), "stage_count": len(payload["stages"])})
    return {"artifact": _relative(root, path), **payload, "reused": False}


def show(root: Path, workflow_id: str, missing_ok: bool = False) -> dict[str, Any] | None:
    root = root.resolve(); path = evidence_path(root, workflow_id)
    if not path.is_file():
        if missing_ok:
            return None
        raise ValueError(f"DWR-3 evidence does not exist for `{workflow_id}`; run `tailtrail workflow evidence collect`")
    payload = _read(path)
    if payload.get("type") != "tailtrail-workflow-evidence" or payload.get("workflow_id") != workflow_id:
        raise ValueError("DWR-3 evidence artifact is invalid")
    return {"artifact": _relative(root, path), **payload}


def refresh(root: Path, workflow_id: str, change_types: list[str]) -> dict[str, Any]:
    """Mark only stages affected by explicit, categorical freshness evidence stale."""
    root = root.resolve(); invalid = sorted(set(change_types) - CHANGE_TYPES)
    if invalid:
        raise ValueError("unsupported freshness change type(s): " + ", ".join(invalid))
    current = collect(root, workflow_id); plan = compiler.show(root, workflow_id)
    impacted: set[str] = set()
    for change_type in sorted(set(change_types)):
        impacted |= _affected(plan["stages"], change_type)
    rows = []
    for row in current["stages"]:
        rows.append({**row, "status": "stale" if row["stage_id"] in impacted else row["status"]})
    event = {"change_types": sorted(set(change_types)), "stale_stage_ids": sorted(impacted)}
    payload = {key: value for key, value in current.items() if key not in {"artifact", "reused", "evidence_fingerprint"}}
    payload["stages"] = rows; payload["freshness_events"] = [*payload.get("freshness_events", []), event]
    payload["evidence_fingerprint"] = _hash({key: value for key, value in payload.items() if key != "evidence_fingerprint"})
    path = evidence_path(root, workflow_id); LEDGER.atomic_json(path, payload)
    binding = ownership.show(root, workflow_id)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_freshness_updated", {"workflow_id": workflow_id, **event})
    return {"artifact": _relative(root, path), **payload}


def resume(root: Path, workflow_id: str) -> dict[str, Any]:
    """Return the shortest continuation; no stage or command is dispatched."""
    root = root.resolve(); evidence = show(root, workflow_id); scope = task_scope.freshness(root, workflow_id)
    if not scope["valid"]:
        return {"type": "tailtrail-workflow-resume", "workflow_id": workflow_id, "status": "blocked", "reason": "task-scoped canonical state is invalid", "scope": scope, "boundary": "No resume or execution occurred."}
    stale = [row["stage_id"] for row in evidence["stages"] if row["status"] == "stale"]
    pending = [row["stage_id"] for row in evidence["stages"] if row["status"] == "pending"]
    next_stage = stale[0] if stale else (pending[0] if pending else None)
    status = "resume-ready" if next_stage else "evidence-complete"
    return {"type": "tailtrail-workflow-resume", "workflow_id": workflow_id, "status": status, "next_stage": next_stage, "stale_stage_ids": stale, "preserved_passed_stage_ids": [row["stage_id"] for row in evidence["stages"] if row["status"] == "passed"], "scope": scope, "boundary": "This is a shortest-path recommendation only. DWR-3 does not automatically retry code-changing, test, scanner, Git, provider, or shell actions."}


def correction(root: Path, workflow_id: str) -> dict[str, Any]:
    """Attach one existing closure correction route and return its safe resume path."""
    root = root.resolve(); binding = ownership.show(root, workflow_id); packet = CORRECTION.handoff(root, binding["tailtrail_run_id"])
    evidence = collect(root, workflow_id)
    if packet.get("status") == "no-correction-needed":
        return {"workflow_id": workflow_id, "correction": packet, "resume": resume(root, workflow_id)}
    impacted = _affected(compiler.show(root, workflow_id)["stages"], "source-edit")
    rows = [{**row, "status": "stale" if row["stage_id"] in impacted else row["status"]} for row in evidence["stages"]]
    payload = {key: value for key, value in evidence.items() if key not in {"artifact", "reused", "evidence_fingerprint"}}
    payload["stages"] = rows; payload["artifact_refs"]["correction"] = _artifact(root, Path(packet["artifact"])) or payload["artifact_refs"].get("correction")
    payload["evidence_fingerprint"] = _hash({key: value for key, value in payload.items() if key != "evidence_fingerprint"})
    LEDGER.atomic_json(evidence_path(root, workflow_id), payload)
    return {"workflow_id": workflow_id, "correction": {"artifact": _relative(root, Path(packet["artifact"])), "status": packet["status"]}, "resume": resume(root, workflow_id), "boundary": "The existing correction route was attached. No correction action was executed or retried."}


def close(root: Path, workflow_id: str, accepted_incomplete: bool = False, approved: bool = False) -> dict[str, Any]:
    return evidence_completion.close(root, workflow_id, accepted_incomplete, approved)


def sync_closure(root: Path, run_id: str, report: dict[str, Any]) -> dict[str, Any] | None:
    """Called by canonical closure finalization when this run has a DWR workflow."""
    return evidence_completion.sync_closure(root, run_id, report)


def validate(root: Path, workflow_id: str) -> dict[str, Any]:
    return evidence_completion.validate(root, workflow_id)
