"""Define and deterministically normalize all six Deferred Phase 5 workflow templates."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


def _stage(stage_id: str, capability_id: str, prerequisites: list[str], evidence: list[str], **extra: Any) -> dict[str, Any]:
    return {"stage_id": stage_id, "capability_id": capability_id, "prerequisites": prerequisites, "evidence": evidence, **extra}


TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "small-change": [
        _stage("bootstrap", "canonical-local-state", [], ["canonical-binding"]),
        _stage("discover", "code-graph-mapper", ["bootstrap"], ["local-graph"]),
        _stage("implement", "requirement-completion-harness", ["discover"], ["source-edit-receipt"]),
        _stage("focused-test", "evidence-aware-testing", ["implement"], ["focused-validation"]),
        _stage("review", "review", ["focused-test"], ["requirement-review"]),
        _stage("fulfilment", "requirement-completion-harness", ["review"], ["completion-assessment"]),
    ],
    "delivery": [
        _stage("bootstrap", "canonical-local-state", [], ["canonical-binding"]),
        _stage("discover", "code-graph-mapper", ["bootstrap"], ["local-graph"]),
        _stage("clarify", "aidlc", ["discover"], ["approved-requirements"]),
        _stage("plan", "navigator", ["clarify"], ["implementation-slices"]),
        _stage("implement", "requirement-completion-harness", ["plan"], ["source-edit-receipt"]),
        _stage("focused-test", "evidence-aware-testing", ["implement"], ["focused-validation"]),
        _stage("review", "review", ["focused-test"], ["requirement-review"]),
        _stage("fulfilment", "requirement-completion-harness", ["review"], ["completion-assessment"]),
        _stage("handoff", "program-delivery-orchestrator", ["fulfilment"], ["delivery-handoff"]),
    ],
    "risk-sensitive": [
        _stage("bootstrap", "canonical-local-state", [], ["canonical-binding"]),
        _stage("discover", "code-graph-mapper", ["bootstrap"], ["local-graph"]),
        _stage("clarify", "aidlc", ["discover"], ["approved-requirements"]),
        _stage("risk-plan", "navigator", ["clarify"], ["risk-plan"]),
        _stage("implement", "requirement-completion-harness", ["risk-plan"], ["source-edit-receipt", "risk-authority"]),
        _stage("tests", "evidence-aware-testing", ["implement"], ["tiered-validation"]),
        _stage("security", "security-vulnerability", ["tests"], ["security-assessment"]),
        _stage("quality", "quality-signals", ["security"], ["quality-assessment"]),
        _stage("review", "review", ["quality"], ["requirement-review"]),
        _stage("fulfilment", "requirement-completion-harness", ["review"], ["completion-assessment"]),
        _stage("release-approval", "canonical-local-state", ["fulfilment"], ["release-approval"], control_kind="approval-gate"),
        _stage("handoff", "program-delivery-orchestrator", ["release-approval"], ["risk-handoff"]),
    ],
    "review-only": [
        _stage("scope-diff", "canonical-local-state", [], ["approved-review-scope"]),
        _stage("graph-impact", "code-graph-mapper", ["scope-diff"], ["local-graph"]),
        _stage("review", "review", ["graph-impact"], ["review-result"]),
        _stage("fulfilment", "requirement-completion-harness", ["review"], ["requirement-assessment"]),
        _stage("optional-fix-proposal", "navigator", ["fulfilment"], ["fix-proposal-decision"]),
    ],
    "ci-scanner-remediation": [
        _stage("ingest-finding", "quality-signals", [], ["saved-finding-receipt"]),
        _stage("graph-overlay", "code-graph-mapper", ["ingest-finding"], ["finding-overlay"]),
        _stage("root-cause", "review", ["graph-overlay"], ["root-cause-assessment"]),
        _stage("fix-plan", "navigator", ["root-cause"], ["approved-fix-plan"]),
        _stage("fix-approval", "canonical-local-state", ["fix-plan"], ["fix-approval"], control_kind="approval-gate"),
        _stage("implement", "requirement-completion-harness", ["fix-approval"], ["source-edit-receipt"]),
        _stage("focused-validation", "evidence-aware-testing", ["implement"], ["focused-validation"]),
        _stage("finding-recheck", "quality-signals", ["focused-validation"], ["finding-recheck"]),
        _stage("review", "review", ["finding-recheck"], ["requirement-review"]),
        _stage("fulfilment", "requirement-completion-harness", ["review"], ["completion-assessment"]),
    ],
    "repository-discovery": [
        _stage("bootstrap", "canonical-local-state", [], ["canonical-binding"]),
        _stage("graph-freshness", "code-graph-mapper", ["bootstrap"], ["graph-freshness"]),
        _stage("bounded-discovery", "code-graph-mapper", ["graph-freshness"], ["bounded-discovery"]),
        _stage("architecture-summary", "review", ["bounded-discovery"], ["architecture-summary"]),
    ],
}


def select_template(feature_ids: set[str]) -> str:
    if "security-vulnerability" in feature_ids: return "risk-sensitive"
    # QA planning also selects quality-signals, but that alone is not a saved
    # CI/scanner remediation intent. The graph overlay signal distinguishes the
    # actual Sonar/CI route from ordinary focused validation.
    if {"quality-signals", "code-graph-mapper"} <= feature_ids: return "ci-scanner-remediation"
    if feature_ids and feature_ids <= {"navigator", "code-graph-mapper", "review"}:
        return "review-only" if "review" in feature_ids else "repository-discovery"
    if feature_ids & {"aidlc", "official-aidlc-bridge", "behavior-harness", "architecture-fitness-harness", "higher-tier-testing-release-confidence", "program-delivery-orchestrator"}: return "delivery"
    return "small-change"


def merge_stages(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge exact duplicate stage declarations; reject conflicting ones."""
    merged: dict[str, dict[str, Any]] = {}
    for stage in stages:
        stage_id = str(stage.get("stage_id", ""))
        if not stage_id: raise ValueError("compiler stage requires stage_id")
        existing = merged.get(stage_id)
        if existing is None:
            merged[stage_id] = {**stage, "prerequisites": list(stage.get("prerequisites", [])), "evidence": sorted(set(stage.get("evidence", [])))}; continue
        if any(existing.get(key) != stage.get(key) for key in ("capability_id", "prerequisites", "control_kind")):
            raise ValueError(f"duplicate stage `{stage_id}` has incompatible capability, prerequisites, or control kind")
        existing["evidence"] = sorted(set(existing["evidence"]) | set(stage.get("evidence", [])))
    return list(merged.values())


def resolve_graph(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Topologically order a stage graph and reject missing prerequisites/cycles."""
    identifiers = {str(stage.get("stage_id", "")) for stage in stages}
    if len(identifiers) != len(stages) or "" in identifiers: raise ValueError("compiled stage IDs must be present and unique")
    dependencies = {str(stage["stage_id"]): set(stage.get("prerequisites", [])) for stage in stages}
    missing = sorted({item for values in dependencies.values() for item in values if item not in identifiers})
    if missing: raise ValueError("stage prerequisite is missing: " + ", ".join(missing))
    reverse: dict[str, set[str]] = defaultdict(set)
    for stage_id, values in dependencies.items():
        for value in values: reverse[value].add(stage_id)
    ready = deque(stage_id for stage_id in identifiers if not dependencies[stage_id]); ordered: list[str] = []
    order = {str(stage["stage_id"]): index for index, stage in enumerate(stages)}
    ready = deque(sorted(ready, key=order.get))
    while ready:
        stage_id = ready.popleft(); ordered.append(stage_id)
        for child in sorted(reverse[stage_id], key=order.get):
            dependencies[child].remove(stage_id)
            if not dependencies[child]: ready.append(child)
    if len(ordered) != len(stages): raise ValueError("workflow stage prerequisites contain a cycle")
    indexed = {str(stage["stage_id"]): stage for stage in stages}
    return [indexed[stage_id] for stage_id in ordered]
