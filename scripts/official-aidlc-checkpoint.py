#!/usr/bin/env python3
"""Persist deterministic official-AI-DLC evidence checkpoints for Full runs.

This adapter does not execute an external AI-DLC workflow, tests, CI, or model.
It turns approved TailTrail requirements and supplied, saved receipts into
small, requirement-linked checkpoint artifacts for the official lifecycle.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STAGES = {"design", "construction", "build-and-test", "handoff", "operations"}
STRATEGIES = {"minimal", "standard", "comprehensive"}


def load(relative: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = load("scripts/run-ledger.py", "official_checkpoint_ledger")
STATE = load("scripts/official-aidlc-state.py", "official_checkpoint_state")
SAN = load("scripts/official-aidlc-sanitize.py", "official_checkpoint_sanitizer")
RUNTIME = load("scripts/official-aidlc-runtime.py", "official_checkpoint_runtime")


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def state(root: Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id:
        raise ValueError("run_id must be one local TailTrail run identifier")
    return L.state_dir(root.resolve(), run_id)


def bridge(root: Path, run_id: str) -> dict[str, Any]:
    item = state(root, run_id) / "aidlc-official" / "bridge-v1.json"
    if not item.is_file():
        raise ValueError("official evidence checkpoints require a Full-mode bridge")
    payload = read(item)
    if payload.get("mode") != "full":
        raise ValueError("official evidence checkpoints require a Full-mode bridge")
    RUNTIME.assert_attached(root, run_id)
    return payload


def anchor(root: Path, run_id: str) -> dict[str, Any]:
    item = state(root, run_id) / "anchors" / "approved-v1.json"
    if not item.is_file():
        raise ValueError("official evidence checkpoints require an approved TailTrail anchor")
    return read(item)


def relative(root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError("artifact must be inside the project root") from error


def artifact(root: Path, run_id: str, name: str) -> Path:
    return state(root, run_id) / "aidlc-official" / "checkpoints" / name


def write(root: Path, run_id: str, name: str, payload: dict[str, Any]) -> str:
    path = artifact(root, run_id, name)
    SAN.validate_artifact(root, payload, "checkpoint")
    L.atomic_json(path, payload)
    return path.relative_to(root.resolve()).as_posix()


def requirement_rows(root: Path, run_id: str) -> list[dict[str, Any]]:
    STATE.assert_consistent(root, run_id)
    return [{"requirement_uid": row["requirement_uid"], "display_id": row.get("display_id"), "statement": row["statement"], "official_requirement_ref": row.get("official_requirement_ref")} for row in anchor(root, run_id)["requirements"]]


def perspectives(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = " ".join(item["statement"].lower() for item in rows)
    selected = [
        ("product", "all approved requirements need an observable outcome"),
        ("developer", "all approved requirements need a bounded implementation packet"),
        ("quality", "all approved requirements need requirement-linked evidence"),
    ]
    if len(rows) > 1 or any(word in text for word in ("api", "service", "caller", "contract", "data")):
        selected.append(("architect", "multi-boundary or contract impact requires architecture-fit assessment"))
    if any(word in text for word in ("security", "auth", "privacy", "payment", "secret", "terraform", "infrastructure")):
        selected.append(("devsecops", "risk terms require existing guardrail, dependency, or CI evidence"))
    if any(word in text for word in ("release", "rollout", "migration", "production", "terraform", "infrastructure")):
        selected.extend([("platform", "delivery includes platform or environment concerns"), ("operations", "delivery includes rollout, recovery, or operational proof")])
    return [{"perspective": name, "status": "selected", "requirement_uids": [row["requirement_uid"] for row in rows], "reason": reason, "boundary": "Host reasoning plus existing deterministic TailTrail controls; no model sub-agent was executed."} for name, reason in selected]


def design_plan(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    RUNTIME.assert_attached(root, run_id, expected_stage="design")
    identity, rows = bridge(root, run_id), requirement_rows(root, run_id)
    decisions = []
    for row in rows:
        lowered = row["statement"].lower()
        material = any(word in lowered for word in ("api", "contract", "data", "auth", "security", "migration", "release", "terraform"))
        decisions.append({"decision_id": f"DES-{len(decisions)+1:02d}", "requirement_uid": row["requirement_uid"], "statement": row["statement"], "material": material, "alternatives": ["reuse existing repository boundary", "introduce a new boundary only if repository evidence proves it is required"], "recommended": "reuse existing repository boundary", "status": "awaiting-design-approval" if material else "non-material-guidance"})
    payload = {"schema_version": "1", "type": "tailtrail-official-aidlc-design-plan", "run_id": run_id, "official_stage": "design", "official_intent_id": identity["official_intent_id"], "requirements": rows, "perspectives": perspectives(rows), "decisions": decisions, "discovery_frame": {"user_stories": [{"requirement_uid": row["requirement_uid"], "story": f"As a delivery stakeholder, I need {row['statement']} so the approved outcome is observable."} for row in rows], "technical_scenarios": [{"requirement_uid": row["requirement_uid"], "acceptance": "Use the approved acceptance criteria and preserve rules from the immutable anchor."} for row in rows]}, "boundary": "Planning artifact only. It does not inspect source, select an unapproved architecture, or authorize implementation."}
    location = write(root, run_id, "design-plan-v1.json", payload)
    L.append_event(root, run_id, "harness_plan", {"kind": "official-aidlc-design", "artifact": location, "decisions": len(decisions), "perspectives": [item["perspective"] for item in payload["perspectives"]]})
    return {**payload, "artifact": location}


def design_approve(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    root = root.resolve()
    RUNTIME.assert_attached(root, run_id, expected_stage="design")
    if not approved:
        raise ValueError("design approval requires --approved")
    plan_path = artifact(root, run_id, "design-plan-v1.json")
    if not plan_path.is_file():
        raise ValueError("create the official design plan first")
    plan = read(plan_path)
    payload = {"schema_version": "1", "type": "tailtrail-official-aidlc-design-decision", "run_id": run_id, "official_stage": "design", "approved": True, "design_plan": plan_path.relative_to(root).as_posix(), "decisions": plan["decisions"], "perspectives": plan["perspectives"], "boundary": "Approval authorizes only the recorded design decisions within the already approved requirement anchor."}
    location = write(root, run_id, "design-decision-v1.json", payload)
    L.append_event(root, run_id, "planning_activated", {"kind": "official-aidlc-design", "artifact": location, "decision_ids": [item["decision_id"] for item in payload["decisions"]]})
    return {**payload, "artifact": location}


def tiers(statement: str, strategy: str) -> list[str]:
    base = ["unit"]
    lowered = statement.lower()
    if strategy != "minimal" or any(word in lowered for word in ("service", "api", "caller", "inventory", "refund", "database")):
        base.append("integration")
    if any(word in lowered for word in ("api", "contract", "schema")):
        base.append("contract")
    if strategy == "comprehensive" or any(word in lowered for word in ("journey", "notification", "user flow")):
        base.append("e2e")
    if strategy == "comprehensive" and any(word in lowered for word in ("release", "terraform", "infrastructure", "migration")):
        base.extend(["infrastructure", "release-smoke"])
    return list(dict.fromkeys(base))


def test_plan(root: Path, run_id: str, strategy: str) -> dict[str, Any]:
    root = root.resolve()
    RUNTIME.assert_attached(root, run_id, expected_stage="build-and-test")
    if strategy not in STRATEGIES:
        raise ValueError("strategy must be minimal, standard, or comprehensive")
    design = artifact(root, run_id, "design-decision-v1.json")
    if not design.is_file():
        raise ValueError("official test strategy requires an approved official design decision")
    rows = requirement_rows(root, run_id)
    mapped = [{"requirement_uid": row["requirement_uid"], "official_requirement_ref": row.get("official_requirement_ref"), "official_test_intent": f"Prove: {row['statement']}", "required_tiers": tiers(row["statement"], strategy), "planned_receipt_types": ["validation-evidence-receipt"], "applicable_harnesses": ["Requirement Completion Harness", "Evidence-Aware Testing"], "status": "planned"} for row in rows]
    payload = {"schema_version": "1", "type": "tailtrail-official-aidlc-test-plan-bridge", "run_id": run_id, "official_stage": "build-and-test", "official_test_strategy": strategy, "design_decision": design.relative_to(root).as_posix(), "requirements": mapped, "boundary": "Strategy maps minimum evidence tiers; it does not run commands or treat planned test counts as proof."}
    location = write(root, run_id, "test-plan-v1.json", payload)
    L.append_event(root, run_id, "harness_plan", {"kind": "official-aidlc-test-strategy", "artifact": location, "strategy": strategy, "requirements": len(mapped)})
    return {**payload, "artifact": location}


def construction_checkpoint(root: Path, run_id: str, checkpoint_path: Path) -> dict[str, Any]:
    """Link a saved TailTrail construction checkpoint; never run implementation."""
    root = root.resolve()
    RUNTIME.assert_attached(root, run_id, expected_stage="implementation")
    if not artifact(root, run_id, "design-decision-v1.json").is_file():
        raise ValueError("construction checkpoint requires an approved official design decision")
    if not checkpoint_path.is_file():
        raise ValueError("construction checkpoint artifact does not exist")
    supplied = read(checkpoint_path)
    SAN.validate_input(supplied, "construction-checkpoint-input")
    if supplied.get("type") != "tailtrail-harness-checkpoint" or supplied.get("run_id") != run_id:
        raise ValueError("construction checkpoint must be a saved TailTrail harness checkpoint for this run")
    known = {row["requirement_uid"] for row in requirement_rows(root, run_id)}
    observed = {row.get("requirement_uid") for row in supplied.get("requirements", [])}
    payload = {"schema_version": "1", "type": "tailtrail-official-aidlc-construction-checkpoint", "run_id": run_id, "official_stage": "construction", "source_checkpoint": relative(root, checkpoint_path), "requirements": sorted(known), "missing_requirement_uids": sorted(known - observed), "complete": known.issubset(observed), "boundary": "Links an already saved construction checkpoint. It does not inspect source, apply code, or claim validation."}
    location = write(root, run_id, "construction-checkpoint-v1.json", payload)
    L.append_event(root, run_id, "harness_checkpoint", {"kind": "official-aidlc-construction", "artifact": location, "complete": payload["complete"]})
    return {**payload, "artifact": location}


def evidence_checkpoint(root: Path, run_id: str, receipts: list[Path]) -> dict[str, Any]:
    root = root.resolve()
    RUNTIME.assert_attached(root, run_id, expected_stage="build-and-test")
    plan_path = artifact(root, run_id, "test-plan-v1.json")
    if not plan_path.is_file():
        raise ValueError("create the official test-plan bridge first")
    plan = read(plan_path)
    supplied = []
    for path in receipts:
        if not path.is_file():
            raise ValueError(f"receipt does not exist: {path}")
        payload = read(path)
        SAN.validate_input(payload, "validation-receipt-input")
        supplied.extend(payload.get("results", [payload]) if isinstance(payload, dict) else [])
    gaps = []
    for row in plan["requirements"]:
        present = {str(item.get("tier")) for item in supplied if row["requirement_uid"] in item.get("requirement_uids", []) and item.get("outcome") == "pass"}
        missing = [tier for tier in row["required_tiers"] if tier not in present]
        row["observed_tiers"] = sorted(present); row["status"] = "validated" if not missing else "evidence-gap"
        if missing:
            gaps.append({"requirement_uid": row["requirement_uid"], "evidence_gap": f"missing passing tiers: {', '.join(missing)}", "affected_symbols_or_files": [], "recommended_official_stage": "build-and-test", "next": "create one bounded correction packet; preserve anchor and previous evidence"})
    payload = {"schema_version": "1", "type": "tailtrail-official-aidlc-evidence-checkpoint", "run_id": run_id, "official_stage": "build-and-test", "test_plan": plan_path.relative_to(root).as_posix(), "requirements": plan["requirements"], "receipt_artifacts": [relative(root, path) for path in receipts], "gaps": gaps, "complete": not gaps, "boundary": "Supplied saved receipts only. TailTrail did not run, infer, or rewrite tests."}
    location = write(root, run_id, "evidence-checkpoint-v1.json", payload)
    L.append_event(root, run_id, "harness_checkpoint", {"kind": "official-aidlc-evidence", "artifact": location, "complete": payload["complete"], "gaps": len(gaps)})
    if gaps:
        correction = {"schema_version": "1", "type": "tailtrail-official-aidlc-correction-packet", "run_id": run_id, "official_return_stage": "build-and-test", "gaps": gaps, "checkpoint": location, "boundary": "Bounded correction only; preserve requirements, approved design, receipts, drift, and recovery history."}
        correction_location = write(root, run_id, "build-and-test-correction-v1.json", correction)
        L.append_event(root, run_id, "closure_correction_routed", {"kind": "official-aidlc-evidence", "artifact": correction_location, "stage": "build-and-test", "gaps": len(gaps)})
        payload["correction_packet"] = correction_location
    return {**payload, "artifact": location}


def handoff(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    RUNTIME.assert_attached(root, run_id, expected_stage="handoff")
    evidence = artifact(root, run_id, "evidence-checkpoint-v1.json")
    if not evidence.is_file():
        raise ValueError("record the official evidence checkpoint before handoff")
    checkpoint = read(evidence)
    payload = {"schema_version": "1", "type": "tailtrail-official-aidlc-handoff", "run_id": run_id, "official_stage": "handoff", "evidence_checkpoint": evidence.relative_to(root).as_posix(), "ready": bool(checkpoint.get("complete")), "next_stage": "operations" if checkpoint.get("complete") else "build-and-test", "boundary": "Handoff is a local reference to saved TailTrail evidence; it does not deploy, release, or accept delivery."}
    location = write(root, run_id, "handoff-v1.json", payload)
    L.append_event(root, run_id, "completion_report_created", {"kind": "official-aidlc-handoff", "artifact": location, "ready": payload["ready"], "next_stage": payload["next_stage"]})
    return {**payload, "artifact": location}


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    directory = state(root, run_id) / "aidlc-official" / "checkpoints"
    canonical = STATE.project(root, run_id)
    return {"run_id": run_id, "canonical_state": {"status": canonical["status"], "valid": canonical["valid"], "issues": canonical["issues"]}, "artifacts": [{"path": path.relative_to(root).as_posix(), "type": read(path).get("type"), "stage": read(path).get("official_stage")} for path in sorted(directory.glob("*.json"))], "boundary": "Read-only checkpoint inventory."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("design-plan", "design-approve", "show", "handoff"):
        item = sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if name == "design-approve": item.add_argument("--approved", action="store_true")
    test = sub.add_parser("test-plan"); test.add_argument("--root", type=Path, default=Path.cwd()); test.add_argument("--run-id", required=True); test.add_argument("--strategy", choices=sorted(STRATEGIES), default="standard")
    construction = sub.add_parser("construction"); construction.add_argument("--root", type=Path, default=Path.cwd()); construction.add_argument("--run-id", required=True); construction.add_argument("--checkpoint", type=Path, required=True)
    evidence = sub.add_parser("evidence"); evidence.add_argument("--root", type=Path, default=Path.cwd()); evidence.add_argument("--run-id", required=True); evidence.add_argument("--receipt", type=Path, action="append", required=True)
    args = parser.parse_args(); root = args.root.resolve()
    try:
        payload = {"design-plan": design_plan, "design-approve": lambda r, i: design_approve(r, i, args.approved), "construction": lambda r, i: construction_checkpoint(r, i, args.checkpoint), "test-plan": lambda r, i: test_plan(r, i, args.strategy), "evidence": lambda r, i: evidence_checkpoint(r, i, args.receipt), "handoff": handoff, "show": show}[args.action](root, args.run_id)
        print(json.dumps(payload, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Official AIDLC checkpoint error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
