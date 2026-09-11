#!/usr/bin/env python3
"""Validate bounded host-assisted diagnosis evidence for Debug Start.

The active host may inspect repository text and user-supplied artifacts before
creating a Debug Start plan.  This contract retains only public, hash-bound
evidence: it never accepts private reasoning, execution authority, a proven
root-cause claim, or an assertion that project code/tests were executed.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import navigator_scope


SCHEMA_VERSION = "1"
DIAGNOSIS_TYPE = "tailtrail-host-debug-diagnosis"
HOSTS = {"codex", "copilot", "claude"}
ROLES = {"implementation-owner", "inspection", "proof", "configuration"}
BEHAVIOR_ROLES = {
    "output-renderer", "data-transfer", "data-producer", "proof",
    "configuration", "candidate-only",
}
TRACE_ROLES = BEHAVIOR_ROLES | {"observed-output"}
TRACE_RELATIONSHIPS = {"rendered-by", "reads-from", "receives-from", "exercises"}
EVIDENCE_KINDS = {
    "artifact-read", "configuration-read", "source-read", "static-search", "test-read",
}
FINDING_STATES = {"observation", "hypothesis"}
CONFIDENCE = {"low", "medium", "high"}
TEST_TIERS = {"reproduction", "regression", "behaviour", "unit", "component", "integration", "static"}
TEST_STATES = {"existing", "proposed"}
PROOF_BOUNDARIES = {"composition", "renderer", "final-output"}
REPRODUCTION_STATES = {"not-run", "artifact-inspected", "candidate-identified"}
FORBIDDEN_KEYS = {"chain_of_thought", "private_reasoning", "reasoning", "execution_authority", "approved"}
TOP_LEVEL_FIELDS = {
    "schema_version", "type", "host", "root", "goal_fingerprint", "authority",
    "checks_performed", "evidence", "findings", "test_cases", "reproduction",
    "unknowns", "status", "token_estimate", "boundary", "preflight",
    "requirement_refinement", "behavior_trace", "proposal", "safe_fallback", "evidence_completeness",
}
PROPOSAL_ROUTES = {"prepare-reproduction", "request-more-evidence"}
PROPOSAL_BOUNDARY = "advisory-only; no approval or execution authority"
IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_-]{0,63}$")


def _fingerprint(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def goal_fingerprint(goal: str) -> str:
    return _fingerprint(goal)


def _strings(value: Any, field: str, *, maximum: int = 20) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{field} must contain at most {maximum} non-empty strings")
    return list(dict.fromkeys(item.strip() for item in value))


def _identifier(value: Any, field: str) -> str:
    text = str(value or "")
    if not IDENTIFIER.fullmatch(text):
        raise ValueError(f"{field} must be a stable public identifier")
    return text


def _bounded_statement(value: Any, field: str, *, maximum: int = 800) -> str:
    text = " ".join(str(value or "").split())
    if not text or len(text) > maximum:
        raise ValueError(f"{field} must be a non-empty public statement of at most {maximum} characters")
    return text


def _reject_private_fields(value: Any, path: str = "diagnosis") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_KEYS:
                raise ValueError(f"{path}.{key} is not accepted by the public diagnosis contract")
            _reject_private_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_private_fields(child, f"{path}[{index}]")


def _line_slice(text: str, start: int | None, end: int | None) -> tuple[int, int, int]:
    lines = text.splitlines(keepends=True) or [text]
    if start is None and end is None:
        return 1, len(lines), len(text)
    if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start or end > len(lines):
        raise ValueError("diagnosis evidence line range is outside the current file")
    return start, end, sum(len(line) for line in lines[start - 1:end])


def _merge_ranges(rows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(rows):
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def _behavior_graph_topology(nodes: list[dict[str, Any]], edges: list[dict[str, str]]) -> dict[str, Any]:
    """Derive bounded graph shape from behavior-flow edges, excluding proof links."""
    behavior_nodes = {
        row["id"]: row for row in nodes
        if row["role"] in {"observed-output", "output-renderer", "data-transfer", "data-producer"}
    }
    flow_edges = [
        row for row in edges
        if row["relationship"] != "exercises"
        and row["from"] in behavior_nodes
        and row["to"] in behavior_nodes
    ]
    outgoing = {node_id: [] for node_id in behavior_nodes}
    incoming = {node_id: [] for node_id in behavior_nodes}
    undirected = {node_id: set() for node_id in behavior_nodes}
    for edge in flow_edges:
        outgoing[edge["from"]].append(edge["to"])
        incoming[edge["to"]].append(edge["from"])
        undirected[edge["from"]].add(edge["to"])
        undirected[edge["to"]].add(edge["from"])
    observed = [node_id for node_id, row in behavior_nodes.items() if row["role"] == "observed-output"]
    entries = observed or sorted(node_id for node_id in behavior_nodes if not incoming[node_id])
    terminals = sorted(node_id for node_id in behavior_nodes if not outgoing[node_id])
    branches = sorted(node_id for node_id in behavior_nodes if len(outgoing[node_id]) > 1)
    merges = sorted(node_id for node_id in behavior_nodes if len(incoming[node_id]) > 1)

    components = 0
    unseen = set(behavior_nodes)
    while unseen:
        components += 1
        pending = [next(iter(unseen))]
        while pending:
            node_id = pending.pop()
            if node_id not in unseen:
                continue
            unseen.remove(node_id)
            pending.extend(undirected[node_id] & unseen)

    indegree = {node_id: len(incoming[node_id]) for node_id in behavior_nodes}
    pending = [node_id for node_id, count in indegree.items() if count == 0]
    visited = 0
    while pending:
        node_id = pending.pop()
        visited += 1
        for target in outgoing[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                pending.append(target)
    cyclic = visited != len(behavior_nodes)

    path_count = 0
    capped = False

    def count_paths(node_id: str, active: set[str]) -> None:
        nonlocal path_count, capped
        if capped or node_id in active:
            return
        if not outgoing[node_id]:
            path_count += 1
            capped = path_count >= 64
            return
        for target in outgoing[node_id]:
            count_paths(target, active | {node_id})

    for entry in entries:
        count_paths(entry, set())
    if cyclic:
        shape = "cyclic"
    elif components > 1:
        shape = "disconnected"
    elif branches and merges:
        shape = "branching-and-converging"
    elif branches:
        shape = "branching"
    elif merges:
        shape = "converging"
    else:
        shape = "linear"
    return {
        "shape": shape,
        "entry_node_ids": sorted(entries),
        "terminal_node_ids": terminals,
        "branch_node_ids": branches,
        "merge_node_ids": merges,
        "component_count": components,
        "cyclic": cyclic,
        "path_count": path_count,
        "path_count_capped": capped,
    }


def _validate_behavior_trace(value: Any, evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("debug diagnosis behavior_trace must be an object")
    if value.get("direction") != "observed-output-to-producer":
        raise ValueError("debug diagnosis behavior trace direction is invalid")
    state = str(value.get("state", ""))
    if state not in {"partial", "resolved-to-producer"}:
        raise ValueError("debug diagnosis behavior trace state is invalid")
    evidence_by_id = {row["id"]: row for row in evidence}
    evidence_ids = set(evidence_by_id)
    nodes_input = value.get("nodes", [])
    edges_input = value.get("edges", [])
    if not isinstance(nodes_input, list) or not nodes_input or len(nodes_input) > 30:
        raise ValueError("debug diagnosis behavior trace requires 1 to 30 nodes")
    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for index, raw in enumerate(nodes_input):
        if not isinstance(raw, dict):
            raise ValueError("debug diagnosis behavior trace nodes must be objects")
        node_id = _identifier(raw.get("id"), f"behavior_trace.nodes[{index}].id")
        if node_id in node_ids:
            raise ValueError(f"duplicate debug diagnosis behavior trace node: {node_id}")
        node_ids.add(node_id)
        role = str(raw.get("role", ""))
        if role not in TRACE_ROLES:
            raise ValueError(f"debug diagnosis behavior trace node {node_id} has invalid role")
        evidence_id = raw.get("evidence_id")
        if role != "observed-output" and evidence_id not in evidence_ids:
            raise ValueError(f"debug diagnosis behavior trace node {node_id} lacks current evidence")
        if role == "observed-output" and evidence_id not in {None, ""}:
            raise ValueError("observed-output trace nodes must reference the supplied artifact, not repository evidence")
        if role != "observed-output":
            evidence_row = evidence_by_id[str(evidence_id)]
            if raw.get("path") != evidence_row["path"]:
                raise ValueError(f"debug diagnosis behavior trace node {node_id} path does not match its evidence")
            raw_symbols = _strings(raw.get("symbols", []), f"behavior_trace.nodes[{index}].symbols", maximum=10)
            if set(raw_symbols) != set(evidence_row.get("symbols", [])):
                raise ValueError(f"debug diagnosis behavior trace node {node_id} symbols do not match its evidence")
            if role not in evidence_row.get("behavior_roles", []):
                raise ValueError(f"debug diagnosis behavior trace node {node_id} role does not match its evidence")
        else:
            raw_symbols = _strings(raw.get("symbols", []), f"behavior_trace.nodes[{index}].symbols", maximum=10)
        nodes.append({
            "id": node_id,
            "role": role,
            "path": _bounded_statement(raw.get("path"), f"behavior_trace.nodes[{index}].path"),
            "symbols": raw_symbols,
            "evidence_id": evidence_id or None,
        })
    if not isinstance(edges_input, list) or len(edges_input) > 40:
        raise ValueError("debug diagnosis behavior trace must contain at most 40 edges")
    edges: list[dict[str, str]] = []
    edge_ids: set[str] = set()
    for index, raw in enumerate(edges_input):
        if not isinstance(raw, dict):
            raise ValueError("debug diagnosis behavior trace edges must be objects")
        edge_id = _identifier(raw.get("id"), f"behavior_trace.edges[{index}].id")
        source = str(raw.get("from", ""))
        target = str(raw.get("to", ""))
        relationship = str(raw.get("relationship", ""))
        if edge_id in edge_ids or source not in node_ids or target not in node_ids or source == target:
            raise ValueError(f"debug diagnosis behavior trace edge {edge_id} is invalid")
        if relationship not in TRACE_RELATIONSHIPS:
            raise ValueError(f"debug diagnosis behavior trace edge {edge_id} has invalid relationship")
        source_role = next(row["role"] for row in nodes if row["id"] == source)
        target_role = next(row["role"] for row in nodes if row["id"] == target)
        allowed_roles = {
            "rendered-by": ({"observed-output"}, {"output-renderer"}),
            "reads-from": ({"output-renderer", "data-transfer"}, {"data-transfer", "data-producer"}),
            "receives-from": ({"data-transfer"}, {"data-transfer", "data-producer"}),
            "exercises": ({"proof"}, {"output-renderer", "data-transfer", "data-producer"}),
        }
        allowed_sources, allowed_targets = allowed_roles[relationship]
        if source_role not in allowed_sources or target_role not in allowed_targets:
            raise ValueError(f"debug diagnosis behavior trace edge {edge_id} is incompatible with its node roles")
        edge_ids.add(edge_id)
        edges.append({"id": edge_id, "from": source, "to": target, "relationship": relationship})
    divergence = _strings(value.get("divergence_candidates", []), "behavior_trace.divergence_candidates", maximum=20)
    if not set(divergence).issubset(node_ids):
        raise ValueError("debug diagnosis behavior trace has unsupported divergence candidates")
    node_by_id = {row["id"]: row for row in nodes}
    for node_id in divergence:
        row = node_by_id[node_id]
        evidence_row = evidence_by_id.get(str(row.get("evidence_id")), {})
        if row["role"] not in {"output-renderer", "data-transfer", "data-producer"} or evidence_row.get("role") != "implementation-owner":
            raise ValueError("debug diagnosis behavior trace divergence candidates must be implementation behavior owners")
    topology = _behavior_graph_topology(nodes, edges)
    supplied_topology = value.get("topology")
    if supplied_topology is not None and supplied_topology != topology:
        raise ValueError("debug diagnosis behavior graph topology does not match its nodes and edges")
    if state == "resolved-to-producer":
        supported_producers = [
            row for row in nodes
            if row["role"] == "data-producer"
            and evidence_by_id.get(str(row.get("evidence_id")), {}).get("role") == "implementation-owner"
        ]
        if not supported_producers:
            raise ValueError("resolved debug behavior trace must reach an implementation-owner data producer")
        traversable = [row for row in edges if row["relationship"] != "exercises"]
        reachable = {row["id"] for row in nodes if row["role"] == "observed-output"}
        changed = True
        while changed:
            changed = False
            for edge in traversable:
                if edge["from"] in reachable and edge["to"] not in reachable:
                    reachable.add(edge["to"])
                    changed = True
        if not any(row["id"] in reachable for row in supported_producers):
            raise ValueError("resolved debug behavior trace has no complete observed-output-to-producer evidence path")
        terminal_roles = {node_by_id[node_id]["role"] for node_id in topology["terminal_node_ids"]}
        if (
            topology["cyclic"]
            or topology["component_count"] != 1
            or not topology["entry_node_ids"]
            or not topology["terminal_node_ids"]
            or terminal_roles != {"data-producer"}
        ):
            raise ValueError("resolved debug behavior graph must connect every branch from observed output to a data producer")
    return {
        "direction": "observed-output-to-producer",
        "state": state,
        "nodes": nodes,
        "edges": edges,
        "divergence_candidates": divergence,
        "topology": topology,
        "boundary": _bounded_statement(value.get("boundary"), "behavior_trace.boundary"),
    }


def _proof_boundaries(
    raw: dict[str, Any],
    tier: str,
    state: str,
    path: str | None,
    evidence: list[dict[str, Any]],
    behavior_trace: dict[str, Any] | None,
    field: str,
) -> list[str]:
    supplied = _strings(raw.get("proof_boundaries", []), field, maximum=3)
    if not set(supplied).issubset(PROOF_BOUNDARIES):
        raise ValueError(f"{field} contains an unsupported proof boundary")
    derived: set[str] = {"final-output"} if tier == "reproduction" else set()
    if path and behavior_trace:
        proof_evidence_ids = {row["id"] for row in evidence if row["role"] == "proof" and row["path"] == path}
        nodes = {row["id"]: row for row in behavior_trace.get("nodes", [])}
        proof_node_ids = {
            node_id for node_id, row in nodes.items()
            if row.get("role") == "proof" and row.get("evidence_id") in proof_evidence_ids
        }
        for edge in behavior_trace.get("edges", []):
            if edge.get("from") not in proof_node_ids:
                continue
            target_role = (nodes.get(edge.get("to")) or {}).get("role")
            if target_role in {"data-transfer", "data-producer"}:
                derived.add("composition")
            elif target_role == "output-renderer":
                derived.add("renderer")
            elif target_role == "observed-output":
                derived.add("final-output")
    if state == "existing":
        return sorted(derived)
    return sorted(set(supplied) | derived)


def _evidence_completeness(
    evidence: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    test_cases: list[dict[str, Any]],
    reproduction: dict[str, Any],
    unknowns: list[str],
    preflight: dict[str, Any] | None,
    refinement: dict[str, Any] | None,
    behavior_trace: dict[str, Any] | None,
    proposal: dict[str, Any] | None,
) -> dict[str, Any]:
    """Report deterministic contract coverage without judging semantic truth."""
    roles = {row["role"] for row in evidence}
    tiers = {row["tier"] for row in test_cases}
    finding_ids = {row["id"] for row in findings}
    evidence_ids = {row["id"] for row in evidence}
    checks: list[dict[str, str]] = []
    gaps: list[str] = []

    def record(check_id: str, passed: bool, detail: str, gap: str) -> None:
        checks.append({"id": check_id, "status": "pass" if passed else "incomplete", "detail": detail})
        if not passed:
            gaps.append(gap)

    record(
        "current-source-binding",
        bool(evidence),
        "Every accepted evidence row is path-, hash-, and line-range-bound to current repository text.",
        "No current-source evidence row is available.",
    )
    record(
        "repository-role-coverage",
        {"implementation-owner", "proof"}.issubset(roles),
        "Implementation-owner and focused-proof roles are both represented.",
        "The diagnosis needs both an implementation-owner slice and a focused-proof slice.",
    )
    trace_complete = behavior_trace is not None and (
        behavior_trace.get("state") == "resolved-to-producer" or bool(unknowns)
    )
    record(
        "behavior-trace-coverage",
        trace_complete,
        "The trace is structurally evidence-bound; a partial trace is paired with an explicit unknown.",
        "Provide a structurally evidence-bound trace, or name the unresolved trace boundary.",
    )
    finding_complete = bool(findings) and all(set(row["evidence_ids"]).issubset(evidence_ids) for row in findings)
    record(
        "finding-traceability",
        finding_complete,
        "Every preliminary observation or hypothesis references accepted evidence.",
        "Every preliminary finding must reference accepted evidence.",
    )
    reproduction_complete = bool(reproduction.get("proposed_steps")) and bool(
        reproduction.get("candidate_command") or reproduction.get("artifact_refs") or reproduction.get("status") == "not-run"
    )
    record(
        "reproduction-contract",
        reproduction_complete,
        "The diagnosis contains an explicit bounded reproduction route or an explicit not-run boundary.",
        "Add bounded reproduction steps and either a candidate command, an inspected artifact, or an explicit not-run boundary.",
    )
    correction_cases = [row for row in test_cases if row["tier"] != "reproduction"]
    proof_complete = (
        "reproduction" in tiers
        and bool(tiers.intersection({"regression", "behaviour", "unit", "component", "integration"}))
        and bool(correction_cases)
        and all(row.get("proof_boundaries") for row in correction_cases)
    )
    record(
        "test-contract",
        proof_complete,
        "The test plan covers final-output reproduction plus trace-matched correction/preservation proof boundaries.",
        "Add final-output reproduction and at least one trace-matched composition, renderer, or final-output correction proof.",
    )
    refinement_refs = set((refinement or {}).get("evidence_ids", []))
    refinement_complete = bool(refinement) and bool(refinement.get("acceptance_criteria")) and bool(refinement.get("preserve_rules")) and refinement_refs.issubset(evidence_ids | finding_ids)
    record(
        "requirement-traceability",
        refinement_complete,
        "The refined requirement has acceptance, preservation, and evidence references.",
        "Add an evidence-linked requirement refinement with acceptance criteria and preservation rules.",
    )
    record(
        "preflight-binding",
        preflight is not None and bool(preflight.get("reuse_key")),
        "The host diagnosis declares one bounded preflight packet, its deterministic reuse key, and one reasoning pass.",
        "Bind the diagnosis to its bounded preflight packet and deterministic reuse key.",
    )
    record(
        "typed-host-proposal",
        proposal is not None,
        "The host returned one closed, ID-only advisory proposal with no execution or approval authority.",
        "Return the closed typed host proposal instead of unrestricted reasoning.",
    )
    return {
        "status": "complete" if not gaps else "incomplete",
        "checks": checks,
        "gaps": gaps,
        "boundary": "TailTrail validates deterministic evidence coverage, freshness, role consistency, and traceability. The active host owns semantic interpretation; completeness is not proof that a finding or proposed fix is true.",
    }


def _validate_host_proposal(
    value: Any,
    evidence: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    test_cases: list[dict[str, Any]],
    behavior_trace: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("debug diagnosis requires one typed host proposal")
    allowed = {
        "route", "requirement_id", "owner_evidence_ids", "proof_evidence_ids",
        "trace_node_ids", "finding_ids", "test_case_ids", "boundary",
    }
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise ValueError("debug diagnosis proposal contains unsupported field(s): " + ", ".join(unexpected))
    route = str(value.get("route", ""))
    if route not in PROPOSAL_ROUTES:
        raise ValueError("debug diagnosis proposal route is invalid")
    if value.get("requirement_id") != "REQ-DEBUG-01":
        raise ValueError("debug diagnosis proposal must target REQ-DEBUG-01")
    if value.get("boundary") != PROPOSAL_BOUNDARY:
        raise ValueError("debug diagnosis proposal must remain advisory-only")
    owner_ids = _strings(value.get("owner_evidence_ids", []), "proposal.owner_evidence_ids", maximum=20)
    proof_ids = _strings(value.get("proof_evidence_ids", []), "proposal.proof_evidence_ids", maximum=20)
    trace_node_ids = _strings(value.get("trace_node_ids", []), "proposal.trace_node_ids", maximum=30)
    finding_ids = _strings(value.get("finding_ids", []), "proposal.finding_ids", maximum=10)
    test_case_ids = _strings(value.get("test_case_ids", []), "proposal.test_case_ids", maximum=12)
    expected_owners = {row["id"] for row in evidence if row["role"] == "implementation-owner"}
    expected_proofs = {row["id"] for row in evidence if row["role"] == "proof"}
    expected_trace_nodes = {
        row["id"] for row in (behavior_trace or {}).get("nodes", [])
        if row.get("role") != "observed-output"
    }
    if set(owner_ids) != expected_owners:
        raise ValueError("debug diagnosis proposal owner references do not match validated owner evidence")
    if set(proof_ids) != expected_proofs:
        raise ValueError("debug diagnosis proposal proof references do not match validated proof evidence")
    if set(trace_node_ids) != expected_trace_nodes:
        raise ValueError("debug diagnosis proposal trace references do not match the validated behavior trace")
    if set(finding_ids) != {row["id"] for row in findings}:
        raise ValueError("debug diagnosis proposal finding references are incomplete")
    if set(test_case_ids) != {row["id"] for row in test_cases}:
        raise ValueError("debug diagnosis proposal test references are incomplete")
    if route == "prepare-reproduction" and (not owner_ids or not proof_ids or not test_case_ids):
        raise ValueError("prepare-reproduction proposal requires owner, proof, and test references")
    return {
        "route": route,
        "requirement_id": "REQ-DEBUG-01",
        "owner_evidence_ids": owner_ids,
        "proof_evidence_ids": proof_ids,
        "trace_node_ids": trace_node_ids,
        "finding_ids": finding_ids,
        "test_case_ids": test_case_ids,
        "boundary": PROPOSAL_BOUNDARY,
    }


def _safe_fallback(
    behavior_trace: dict[str, Any] | None,
    reproduction: dict[str, Any],
    test_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Derive whether Debug can proceed without asking the user for more input."""
    sources: list[str] = []
    if reproduction.get("artifact_refs"):
        sources.append("artifact")
    if reproduction.get("candidate_command"):
        sources.append("candidate-command")
    if reproduction.get("proposed_steps"):
        sources.append("bounded-procedure")
    if any(row.get("tier") == "reproduction" and (row.get("command") or row.get("path")) for row in test_cases):
        sources.append("focused-reproduction-proof")
    sources = list(dict.fromkeys(sources))
    trace_state = (behavior_trace or {}).get("state", "partial")
    if not sources:
        return {
            "state": "awaiting-reproduction-input",
            "trigger": "reproduction-and-external-context-unavailable",
            "trace_state": trace_state,
            "correction_scope": "blocked",
            "user_input": "required",
            "reproduction_sources": [],
            "next_action": "Ask only for the smallest reproduction command, artifact, or external observation needed to continue.",
            "boundary": "No correction scope may be inferred while reproduction and external context are unavailable.",
        }
    if trace_state == "resolved-to-producer":
        state = "not-needed"
        trigger = "trace-resolved"
        next_action = "Prepare the bounded reproduction after Planning Lock approval."
    else:
        state = "continue-approved-debug-investigation"
        trigger = "local-helper-unresolved"
        next_action = "Preserve the partial trace and continue to approved reproduction; do not infer correction scope."
    return {
        "state": state,
        "trigger": trigger,
        "trace_state": trace_state,
        "correction_scope": "blocked",
        "user_input": "not-required",
        "reproduction_sources": sources,
        "next_action": next_action,
        "boundary": "Preflight evidence is orientation only. Correction scope remains blocked until reproduction and root-cause proof complete their separate approvals.",
    }


def _focused_command(root: Path, path: str | None) -> str | None:
    if not path:
        return None
    lowered = path.casefold()
    name = Path(path).name
    if path.endswith(".py") and ("/test" in lowered or name.startswith("test_")):
        return f"pytest {path} -q"
    if ".cy." in lowered:
        try:
            scripts = json.loads((root / "package.json").read_text(encoding="utf-8")).get("scripts", {})
        except (OSError, json.JSONDecodeError, AttributeError):
            scripts = {}
        for script_name, value in scripts.items():
            if "cypress" in str(value).casefold() and "component" in str(value).casefold():
                return f'npm run {script_name} -- --spec "{path}"'
    if any(marker in lowered for marker in (".spec.", ".test.")) and (root / "package.json").is_file():
        return f'npm test -- "{path}"'
    if path.endswith("_test.go"):
        return f"go test ./{Path(path).parent.as_posix()}"
    return None


def validate(root: Path, goal: str, payload: dict[str, Any], host: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("debug diagnosis must be a JSON object")
    _reject_private_fields(payload)
    unexpected = sorted(set(payload) - TOP_LEVEL_FIELDS)
    if unexpected:
        raise ValueError("debug diagnosis contains unsupported field(s): " + ", ".join(unexpected))
    root = root.resolve()
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("type") != DIAGNOSIS_TYPE:
        raise ValueError("debug diagnosis schema or type is incompatible")
    if host not in HOSTS or payload.get("host") != host:
        raise ValueError("debug diagnosis host does not match the active host")
    if payload.get("root") != root.as_posix():
        raise ValueError("debug diagnosis root does not match the resolved target")
    if payload.get("goal_fingerprint") != goal_fingerprint(goal):
        raise ValueError("debug diagnosis is not bound to the exact current goal")
    if payload.get("authority") != "advisory-only":
        raise ValueError("debug diagnosis authority must be advisory-only")

    actions = _strings(payload.get("checks_performed", []), "checks_performed", maximum=8)
    if not set(actions).issubset(EVIDENCE_KINDS):
        raise ValueError("debug diagnosis contains an unsupported or executable check kind")

    evidence_input = payload.get("evidence")
    if not isinstance(evidence_input, list) or not evidence_input or len(evidence_input) > 20:
        raise ValueError("debug diagnosis requires 1 to 20 bounded evidence rows")
    evidence: list[dict[str, Any]] = []
    evidence_ids: set[str] = set()
    file_text: dict[str, str] = {}
    file_ranges: dict[str, list[tuple[int, int]]] = {}
    role_tokens = {role: 0 for role in ROLES}
    for index, raw in enumerate(evidence_input):
        if not isinstance(raw, dict):
            raise ValueError("debug diagnosis evidence rows must be objects")
        evidence_id = _identifier(raw.get("id"), f"evidence[{index}].id")
        if evidence_id in evidence_ids:
            raise ValueError(f"duplicate debug diagnosis evidence id: {evidence_id}")
        evidence_ids.add(evidence_id)
        relative, rejection = navigator_scope.normalize_repository_path(root, str(raw.get("path", "")))
        if rejection or relative is None:
            raise ValueError(f"debug diagnosis evidence path is unsafe: {raw.get('path', '')}")
        repository_role, _ = navigator_scope.classify_repository_role(root, relative)
        if repository_role in {"managed-tooling", "generated", "documentation", "unknown"}:
            raise ValueError(f"debug diagnosis evidence path is not application scope: {relative}")
        text, read_rejection, current_hash = navigator_scope.safe_text(root, relative)
        if read_rejection or text is None or current_hash is None:
            raise ValueError(f"debug diagnosis evidence cannot read current text: {relative} ({read_rejection})")
        if raw.get("sha256") != current_hash:
            raise ValueError(f"debug diagnosis evidence is stale: {relative}")
        role = str(raw.get("role", ""))
        if role not in ROLES:
            raise ValueError(f"debug diagnosis evidence role is invalid: {role}")
        behavior_roles = _strings(raw.get("behavior_roles", []), f"evidence[{index}].behavior_roles", maximum=6)
        if not set(behavior_roles).issubset(BEHAVIOR_ROLES):
            raise ValueError(f"debug diagnosis evidence behavior role is invalid: {relative}")
        if behavior_roles:
            if role == "implementation-owner" and not set(behavior_roles).intersection({"output-renderer", "data-transfer", "data-producer"}):
                raise ValueError(f"debug diagnosis implementation owner lacks behavior-specific evidence: {relative}")
            if role == "proof" and "proof" not in behavior_roles:
                raise ValueError(f"debug diagnosis proof path lacks proof behavior role: {relative}")
            if role == "configuration" and "configuration" not in behavior_roles:
                raise ValueError(f"debug diagnosis configuration path lacks configuration behavior role: {relative}")
            if role == "implementation-owner" and "candidate-only" in behavior_roles:
                raise ValueError(f"debug diagnosis cannot promote a candidate-only path to implementation owner: {relative}")
        kind = str(raw.get("kind", ""))
        if kind not in EVIDENCE_KINDS:
            raise ValueError(f"debug diagnosis evidence kind is invalid: {kind}")
        start, end, _characters = _line_slice(text, raw.get("start_line"), raw.get("end_line"))
        file_text[relative] = text
        file_ranges.setdefault(relative, []).append((start, end))
        evidence.append({
            "id": evidence_id,
            "path": relative,
            "sha256": current_hash,
            "role": role,
            "behavior_roles": behavior_roles,
            "kind": kind,
            "symbols": _strings(raw.get("symbols", []), f"evidence[{index}].symbols", maximum=10),
            "start_line": start,
            "end_line": end,
            "finding": _bounded_statement(raw.get("finding"), f"evidence[{index}].finding"),
        })

    evidenced_actions = {row["kind"] for row in evidence}
    if reproduction_input := payload.get("reproduction"):
        if isinstance(reproduction_input, dict) and reproduction_input.get("artifact_refs"):
            evidenced_actions.add("artifact-read")
    unsupported_actions = sorted(set(actions) - evidenced_actions)
    if unsupported_actions:
        raise ValueError("debug diagnosis claims checks without matching evidence: " + ", ".join(unsupported_actions))

    behavior_trace = _validate_behavior_trace(payload.get("behavior_trace"), evidence)

    findings_input = payload.get("findings")
    if not isinstance(findings_input, list) or not findings_input or len(findings_input) > 10:
        raise ValueError("debug diagnosis requires 1 to 10 preliminary findings")
    findings: list[dict[str, Any]] = []
    finding_ids: set[str] = set()
    for index, raw in enumerate(findings_input):
        if not isinstance(raw, dict):
            raise ValueError("debug diagnosis findings must be objects")
        finding_id = _identifier(raw.get("id"), f"findings[{index}].id")
        if finding_id in finding_ids:
            raise ValueError(f"duplicate debug diagnosis finding id: {finding_id}")
        finding_ids.add(finding_id)
        references = _strings(raw.get("evidence_ids", []), f"findings[{index}].evidence_ids", maximum=10)
        if not references or not set(references).issubset(evidence_ids):
            raise ValueError(f"debug diagnosis finding {finding_id} has unsupported evidence references")
        state = str(raw.get("state", ""))
        confidence = str(raw.get("confidence", ""))
        if state not in FINDING_STATES or confidence not in CONFIDENCE:
            raise ValueError(f"debug diagnosis finding {finding_id} has invalid state or confidence")
        findings.append({
            "id": finding_id,
            "statement": _bounded_statement(raw.get("statement"), f"findings[{index}].statement"),
            "state": state,
            "confidence": confidence,
            "evidence_ids": references,
        })

    tests_input = payload.get("test_cases")
    if not isinstance(tests_input, list) or not tests_input or len(tests_input) > 12:
        raise ValueError("debug diagnosis requires 1 to 12 concrete test cases")
    test_cases: list[dict[str, Any]] = []
    test_ids: set[str] = set()
    for index, raw in enumerate(tests_input):
        if not isinstance(raw, dict):
            raise ValueError("debug diagnosis test cases must be objects")
        test_id = _identifier(raw.get("id"), f"test_cases[{index}].id")
        if test_id in test_ids:
            raise ValueError(f"duplicate debug diagnosis test id: {test_id}")
        test_ids.add(test_id)
        tier = str(raw.get("tier", ""))
        state = str(raw.get("state", ""))
        if tier not in TEST_TIERS or state not in TEST_STATES:
            raise ValueError(f"debug diagnosis test case {test_id} has invalid tier or state")
        path_value = str(raw.get("path", "")).strip()
        path: str | None = None
        if path_value:
            path, rejection = navigator_scope.normalize_repository_path(root, path_value)
            if rejection or path is None:
                raise ValueError(f"debug diagnosis test path is unsafe: {path_value}")
            role, _ = navigator_scope.classify_repository_role(root, path)
            if state == "existing" and role != "test":
                raise ValueError(f"existing debug diagnosis test path is not a current test: {path}")
            if role in {"managed-tooling", "generated"}:
                raise ValueError(f"debug diagnosis test path is not application scope: {path}")
        raw_command = raw.get("command")
        command = (" ".join(raw_command.split()) if isinstance(raw_command, str) else "") or _focused_command(root, path)
        test_cases.append({
            "id": test_id,
            "requirement_id": "REQ-DEBUG-01",
            "tier": tier,
            "state": state,
            "statement": _bounded_statement(raw.get("statement"), f"test_cases[{index}].statement"),
            "path": path,
            "command": command,
            "proof_boundaries": _proof_boundaries(
                raw,
                tier,
                state,
                path,
                evidence,
                behavior_trace,
                f"test_cases[{index}].proof_boundaries",
            ),
        })

    reproduction_input = payload.get("reproduction")
    if not isinstance(reproduction_input, dict) or reproduction_input.get("status") not in REPRODUCTION_STATES:
        raise ValueError("debug diagnosis reproduction status is invalid")
    reproduction = {
        "status": reproduction_input["status"],
        "observation": _bounded_statement(reproduction_input.get("observation"), "reproduction.observation"),
        "expected": _bounded_statement(reproduction_input.get("expected"), "reproduction.expected"),
        "artifact_refs": _strings(reproduction_input.get("artifact_refs", []), "reproduction.artifact_refs", maximum=8),
        "proposed_steps": _strings(reproduction_input.get("proposed_steps", []), "reproduction.proposed_steps", maximum=10),
        "candidate_command": (
            " ".join(reproduction_input["candidate_command"].split())
            if isinstance(reproduction_input.get("candidate_command"), str)
            else None
        ) or None,
    }
    unknowns = _strings(payload.get("unknowns", []), "unknowns", maximum=10)

    preflight_input = payload.get("preflight")
    preflight: dict[str, Any] | None = None
    if preflight_input is not None:
        if not isinstance(preflight_input, dict):
            raise ValueError("debug diagnosis preflight must be an object")
        packet_fingerprint = str(preflight_input.get("packet_fingerprint", ""))
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", packet_fingerprint):
            raise ValueError("debug diagnosis preflight packet fingerprint is invalid")
        passes = int(preflight_input.get("host_reasoning_passes", 0))
        if passes != 1:
            raise ValueError("debug diagnosis requires exactly one host reasoning pass")
        raw_reuse_key = preflight_input.get("reuse_key")
        reuse_key = str(raw_reuse_key) if raw_reuse_key else ""
        if reuse_key and not re.fullmatch(r"sha256:[a-f0-9]{64}", reuse_key):
            raise ValueError("debug diagnosis preflight reuse key is invalid")
        preflight = {
            "packet_fingerprint": packet_fingerprint,
            "elapsed_ms": max(0, int(preflight_input.get("elapsed_ms", 0))),
            "files_considered": max(0, int(preflight_input.get("files_considered", 0))),
            "files_read": max(0, int(preflight_input.get("files_read", 0))),
            "bytes_read": max(0, int(preflight_input.get("bytes_read", 0))),
            "estimated_tokens": max(0, int(preflight_input.get("estimated_tokens", 0))),
            "termination_reason": _bounded_statement(preflight_input.get("termination_reason"), "preflight.termination_reason", maximum=100),
            "host_reasoning_passes": 1,
            "reuse_key": reuse_key or None,
        }

    refinement_input = payload.get("requirement_refinement")
    refinement: dict[str, Any] | None = None
    if refinement_input is not None:
        if not isinstance(refinement_input, dict):
            raise ValueError("debug diagnosis requirement_refinement must be an object")
        references = _strings(refinement_input.get("evidence_ids", []), "requirement_refinement.evidence_ids", maximum=10)
        observation_ids = {row["id"] for row in findings if row["state"] == "observation"}
        if not references or not set(references).issubset(evidence_ids | observation_ids):
            raise ValueError("debug diagnosis requirement refinement needs current observation evidence")
        refinement = {
            "statement": _bounded_statement(refinement_input.get("statement"), "requirement_refinement.statement"),
            "acceptance_criteria": _strings(refinement_input.get("acceptance_criteria", []), "requirement_refinement.acceptance_criteria", maximum=10),
            "preserve_rules": _strings(refinement_input.get("preserve_rules", []), "requirement_refinement.preserve_rules", maximum=10),
            "evidence_ids": references,
        }

    proposal = _validate_host_proposal(
        payload.get("proposal"),
        evidence,
        findings,
        test_cases,
        behavior_trace,
    )
    safe_fallback = _safe_fallback(behavior_trace, reproduction, test_cases)
    expected_route = (
        "request-more-evidence"
        if safe_fallback["state"] == "awaiting-reproduction-input"
        else "prepare-reproduction"
    )
    if proposal["route"] != expected_route:
        if expected_route == "prepare-reproduction":
            raise ValueError(
                "debug diagnosis must prepare reproduction when a bounded reproduction route or external artifact is available"
            )
        raise ValueError(
            "debug diagnosis may prepare reproduction only when a bounded reproduction route or external artifact is available"
        )

    working_chars = 0
    full_chars = sum(len(text) for text in file_text.values())
    for path, ranges in file_ranges.items():
        lines = file_text[path].splitlines(keepends=True) or [file_text[path]]
        for start, end in _merge_ranges(ranges):
            characters = sum(len(line) for line in lines[start - 1:end])
            working_chars += characters
            roles = {row["role"] for row in evidence if row["path"] == path and row["start_line"] <= end and row["end_line"] >= start}
            if roles:
                share = (characters + len(roles) - 1) // len(roles)
                for role in roles:
                    role_tokens[role] += (share + 3) // 4
    contract_chars = len(json.dumps({"findings": findings, "test_cases": test_cases, "reproduction": reproduction, "unknowns": unknowns}, separators=(",", ":")))
    planned_tokens = (working_chars + contract_chars + 3) // 4
    ceiling_tokens = (full_chars + contract_chars + 3) // 4
    reduction = round((1 - planned_tokens / ceiling_tokens) * 100, 2) if ceiling_tokens else 0.0
    ranges_resolved = all(row["start_line"] and row["end_line"] for row in evidence)
    roles = {row["role"] for row in evidence}
    reproduction_observed = reproduction["status"] == "artifact-inspected"
    trace_resolved = bool(behavior_trace and behavior_trace.get("state") == "resolved-to-producer")
    confidence = (
        "high"
        if ranges_resolved
        and reproduction_observed
        and trace_resolved
        and {"implementation-owner", "proof"}.issubset(roles)
        else "medium"
        if ranges_resolved and "implementation-owner" in roles
        else "low"
    )
    confidence_basis = (
        "current hash-bound owner and proof slices, an inspected failure artifact, and a backward trace that reaches a data producer; actual host/model tokens require linked telemetry"
        if confidence == "high"
        else "current hash-bound slices are resolved, but the backward trace, failure artifact, or one required repository role remains unresolved"
        if confidence == "medium"
        else "one or more required owner, proof, or bounded-range inputs remain unresolved"
    )
    evidence_completeness = _evidence_completeness(
        evidence,
        findings,
        test_cases,
        reproduction,
        unknowns,
        preflight,
        refinement,
        behavior_trace,
        proposal,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "type": DIAGNOSIS_TYPE,
        "host": host,
        "root": root.as_posix(),
        "goal_fingerprint": goal_fingerprint(goal),
        "status": "preliminary",
        "authority": "advisory-only",
        "checks_performed": actions,
        "evidence": evidence,
        "behavior_trace": behavior_trace,
        "findings": findings,
        "test_cases": test_cases,
        "reproduction": reproduction,
        "unknowns": unknowns,
        "preflight": preflight,
        "requirement_refinement": refinement,
        "proposal": proposal,
        "safe_fallback": safe_fallback,
        "evidence_completeness": evidence_completeness,
        "token_estimate": {
            "planned_working_set_tokens": planned_tokens,
            "full_scoped_file_ceiling_tokens": ceiling_tokens,
            "estimated_context_reduction_percent": reduction,
            "confidence": confidence,
            "by_role_tokens": role_tokens,
            "basis": confidence_basis,
        },
        "boundary": "Pre-plan host diagnosis is advisory and read-only. TailTrail validates deterministic evidence completeness, not semantic truth. The diagnosis does not reproduce the issue, prove root cause, approve experiments, grant correction scope, execute project commands, or authorize source writes.",
    }
