#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import navigator_core as core
import navigator_discovery as discovery
import navigator_render
import navigator_scope
import prompt_profile
import requirement_discovery
import token_budget_coach
import pipeline_manager
import pipeline_judge


ROOT = Path(__file__).resolve().parents[1]
# Reuse the interpreter that launched TailTrail. This keeps nested helper calls
# working for Windows `py -3` installs as well as Unix `python3` installs.
PYTHON = sys.executable
# Compatibility exports for callers that used the former in-module discovery
# constants. New code should use ``navigator_discovery`` directly.
MAX_REVIEW_GRAPH_ARGUMENT_CHARS = discovery.MAX_REVIEW_GRAPH_ARGUMENT_CHARS
MAX_REVIEW_GRAPH_CHANGED_PATHS = discovery.MAX_REVIEW_GRAPH_CHANGED_PATHS
def load_registry_module() -> Any | None:
    path = ROOT / "scripts" / "tailtrail-registry.py"
    spec = importlib.util.spec_from_file_location("tailtrail_registry_for_navigator", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_bootstrap_module() -> Any | None:
    path = ROOT / "scripts" / "bootstrap-snapshot.py"
    spec = importlib.util.spec_from_file_location("tailtrail_bootstrap_for_navigator", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_learning_retrieval_module() -> Any | None:
    path = ROOT / "scripts" / "learning-retrieval.py"
    spec = importlib.util.spec_from_file_location("tailtrail_learning_retrieval_for_navigator", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def registry_workflow(task: str) -> dict[str, Any] | None:
    module = load_registry_module()
    if module is None:
        return None
    try:
        registry = module.load_registry()
        return module.workflow_projection(registry, task)
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None


def bootstrap_snapshot_status(root: Path, should_check: bool, command_prefix: str) -> dict[str, Any] | None:
    if not should_check:
        return None
    module = load_bootstrap_module()
    if module is None:
        return {
            "status": "unavailable",
            "reason": "bootstrap-snapshot.py is not available in this TailTrail pack",
            "command": f"{command_prefix} bootstrap snapshot --root {core.quoted(root.as_posix())} --write-result",
            "recommended_action": "Continue with normal focused discovery.",
        }
    try:
        status = module.snapshot_status(root)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {
            "status": "unavailable",
            "reason": "bootstrap snapshot status could not be computed",
            "command": f"{command_prefix} bootstrap snapshot --root {core.quoted(root.as_posix())} --write-result",
            "recommended_action": "Continue with normal focused discovery.",
        }
    action = "reuse" if status.get("status") == "fresh" else "create_or_refresh"
    command_action = "refresh" if status.get("exists") else "snapshot"
    command = f"{command_prefix} bootstrap {command_action} --root {core.quoted(root.as_posix())}"
    if command_action == "snapshot":
        command += " --write-result"
    return {
        "status": status.get("status", "unknown"),
        "reason": status.get("reason", "not recorded"),
        "path": status.get("path", ".tailtrail/bootstrap-snapshot.json"),
        "action": action,
        "command": command,
        "languages": status.get("languages", []),
        "manifests": status.get("manifests", []),
        "test_signals": status.get("test_signals", []),
        "ci_signals": status.get("ci_signals", []),
        "scanner_signals": status.get("scanner_signals", []),
        "recommended_action": status.get("recommended_action", "Use focused discovery."),
    }


@dataclass(frozen=True)
class FeatureDecision:
    name: str
    reason: str


EVALUATION_TRIGGER_WORDS = {
    "benchmark",
    "demo",
    "evidence",
    "eval",
    "evaluation",
    "harness",
    "metric",
    "metrics",
    "pitch",
    "proof",
    "regression",
    "report",
    "scenario",
}


def git_changed(root: Path) -> list[str]:
    return discovery.git_changed(root)


def goal_discovery_terms(goal: str) -> list[str]:
    return discovery.goal_discovery_terms(goal)


def goal_discovered_paths(
    root: Path,
    goal: str,
    limit: int = 2,
    query_terms: list[str] | None = None,
    canonical_literals: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    return discovery.goal_discovered_paths(root, goal, limit, query_terms, canonical_literals)


def repository_discovered_paths(root: Path, goal: str, limit: int = 5, query_terms: list[str] | None = None) -> list[dict[str, Any]]:
    return discovery.repository_discovered_paths(root, goal, limit, query_terms)


def is_actionable_changed_path(root: Path, path: str) -> bool:
    return discovery.is_actionable_changed_path(root, path)


def bounded_review_graph_paths(changed: list[str]) -> list[str]:
    return discovery.bounded_review_graph_paths(changed)


def existing_state(root: Path) -> dict[str, bool]:
    return {
        "aidlc_docs": (root / "aidlc-docs").exists(),
        "learnings": (root / ".tailtrail" / "learnings.md").exists(),
        "learning_index": (root / ".tailtrail" / "learning-index.md").exists(),
        "learning_v3": (root / ".tailtrail" / "learning-v3" / "events.jsonl").exists(),
        "installed_pack_manifest": any(root.glob("**/.tailtrail-install.json")),
        "tailtrail_policy": (root / "tailtrail-policy.md").exists(),
        "code_graph_cache": graph_cache_candidates(root)[0].exists() or graph_cache_candidates(root)[1].exists(),
        "shared_code_graph_cache": graph_cache_candidates(root)[0].exists(),
    }


def run_review_graph(root: Path, changed: list[str]) -> dict[str, Any] | None:
    return discovery.run_review_graph(root, changed)


def run_graph_learning(root: Path, changed: list[str], tasks: list[str], risks: list[str]) -> dict[str, Any] | None:
    return discovery.run_graph_learning(root, changed, tasks, risks)


def graph_learning_index_exists(root: Path, state: dict[str, bool]) -> bool:
    return state.get("learning_v3", False) or state["learning_index"] or (root / ".tailtrail" / "graph-learning-index.json").exists()


def learning_retrieval_mode(goal: str) -> str:
    lowered = goal.lower()
    if "--aidlc full" in lowered or "aidlc full" in lowered:
        return "full"
    if "--aidlc standard" in lowered or "aidlc standard" in lowered:
        return "standard"
    return "lite"


def learning_use_proposal(root: Path, goal: str, changed: list[str], tasks: list[str], risks: list[str]) -> dict[str, Any] | None:
    mode = learning_retrieval_mode(goal)

    def blocked(reason: str) -> dict[str, Any]:
        try:
            retrieval = load_learning_retrieval_module()
            thresholds = retrieval.effective_thresholds(root)[0] if retrieval else None
        except (OSError, ValueError):
            thresholds = None
        return {
            "schema_version": "1",
            "type": "tailtrail-learning-use-proposal",
            "state": "blocked",
            "task_frame": {
                "project_frame": {"kind": "repository", "id": "sha256:" + hashlib.sha256(root.resolve().as_posix().encode("utf-8")).hexdigest()},
                "task_types": sorted(set(task.lower() for task in tasks)),
                "tags": sorted(set(tag.lower() for tag in normalized_learning_tags(tasks, risks))),
                "paths": sorted(set(Path(path).as_posix().lower() for path in changed)),
                "requirement_ids": [],
                "mode": mode,
            },
            "threshold": (thresholds or {"lite": 60, "standard": 50, "full": 45})[mode],
            "result_cap": 3,
            "matches": [],
            "blocked": [{"learning_id": "store", "record_id": "unknown", "reasons": [reason], "invalidator_checks": []}],
            "approval": {"required": False, "default": "do-not-use", "choices": ["ignore all learnings"]},
            "boundary": "Fail closed: invalid, stale, conflicting, or unreadable learning state cannot influence implementation.",
        }
    if not (root / ".tailtrail" / "learning-v3" / "events.jsonl").is_file():
        # Cold start is explicit, not silent: there is no store to evaluate,
        # so report the empty state instead of implying matches were checked.
        proposal = blocked("No learning store exists yet")
        proposal["blocked"][0]["reasons"].append(
            "V3 learnings accrue automatically from accepted closures; this project has none recorded yet"
        )
        return proposal

    module = load_learning_retrieval_module()
    if module is None:
        return blocked("Learning retrieval gate is unavailable")
    try:
        return module.build_proposal(
            root,
            task_types=tasks,
            tags=normalized_learning_tags(tasks, risks),
            paths=changed,
            requirement_ids=[],
            mode=mode,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return blocked(f"Learning V3 retrieval failed closed: {error}")


def normalized_learning_tags(tasks: list[str], risks: list[str]) -> list[str]:
    tags = tasks + [risk.replace("/", "-").replace(" ", "-") for risk in risks]
    return sorted(dict.fromkeys(tag for tag in tags if tag))


def learning_skip_reason(root: Path, tiny: bool, state: dict[str, bool], graph_learning: dict[str, Any] | None) -> str:
    if tiny:
        return "tiny task"
    if not graph_learning_index_exists(root, state):
        return "no index"
    graph_status = graph_learning.get("graph_status", {}) if isinstance(graph_learning, dict) else {}
    if graph_status.get("status") in {"stale", "invalid"}:
        return "stale graph"
    return "no matching tags/files/rules"


def learning_approval(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not matches:
        return None
    ids = []
    for item in matches[:3]:
        event = item.get("event", {})
        if isinstance(event, dict):
            ids.append(str(event.get("id", "unknown")))
    return {
        "question": "Should these surfaced learnings influence the implementation plan?",
        "default": "edit plan",
        "learning_ids": ids,
        "choices": [
            {
                "choice": "use learnings",
                "meaning": "Use the matching learnings as advisory repo patterns after inspecting current source, tests, policy, and scanner evidence.",
            },
            {
                "choice": "ignore learnings",
                "meaning": "Do not use the surfaced learnings for this task; proceed from current code and evidence only.",
            },
            {
                "choice": "edit plan",
                "meaning": "Choose specific learning IDs to keep or remove before implementation.",
            },
        ],
        "advisory_rule": "Learnings are advisory only. Current source, tests, CI, scanners, policies, guardrails, and explicit user instructions override old learnings.",
    }


def capture_mode(goal: str) -> str:
    lowered = goal.lower()
    if any(term in lowered for term in REJECTION_TERMS):
        return "rejected"
    if any(term in lowered for term in REVISION_TERMS):
        return "revised"
    return "accepted"


def get_stage_aware_instructions(root: Path, run_id: str) -> str:
    """Return role-specific steering instructions based on the active pipeline stage."""
    manager = pipeline_manager.PipelineManager(root, run_id)
    stage = manager.get_current_stage()
    
    if stage == "IMPLEMENTATION":
        return (
            "You are currently in the IMPLEMENTATION slice. "
            "Focus exclusively on production source code and supporting assets. "
            "Do not propose or edit test files in this stage."
        )
    elif stage == "TESTING":
        return (
            "You are currently in the TESTING slice. "
            "Focus exclusively on proof paths, test classes, and validation specs. "
            "Production source code is read-only; do not attempt to modify it."
        )
    elif stage == "INFRA":
        return (
            "You are currently in the INFRA slice. "
            "Focus exclusively on configuration manifests and infrastructure-as-code. "
            "Production source and tests are read-only."
        )
    return "You are in a general planning or orientation state."

def get_stage_aware_profile(root: Path, run_id: str, tasks: list[str], risks: list[str]) -> str:
    """Select a prompt profile that aligns with the active pipeline stage."""
    manager = pipeline_manager.PipelineManager(root, run_id)
    stage = manager.get_current_stage()
    
    # Start with the base profile based on task/risk
    profile_name = prompt_profile.choose_profile(tasks, risks)
    
    # Overlay stage-specific constraints
    if stage == "TESTING":
        # Ensure the profile is steered toward validation and proof
        return f"{profile_name}-test-worker"
    elif stage == "INFRA":
        return f"{profile_name}-infra-worker"
        
    return profile_name


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def meta_harness_hints(root: Path, relevant_feature_ids: list[str]) -> dict[str, Any]:
    path = root / ".tailtrail" / "meta-harness-proposals.jsonl"
    rows = read_jsonl(path)
    if not rows:
        return {
            "status": "missing",
            "path": path.as_posix(),
            "hints": [],
            "rule": "Navigator only reads already-approved local Meta-Harness proposal records; it does not run harness analysis.",
        }

    accepted_statuses = {"accepted", "implemented"}
    approved_ids = {
        str(row.get("proposal_id"))
        for row in rows
        if row.get("type") == "tailtrail-meta-harness-proposal-record"
        and row.get("status") in accepted_statuses
        and row.get("proposal_id")
    }
    proposals = [
        row
        for row in rows
        if row.get("type") == "tailtrail-meta-harness-proposal"
        and row.get("status") in {"proposed", "accepted", "implemented"}
        and row.get("proposal_id")
    ]
    if not approved_ids:
        approved_ids = {str(row.get("proposal_id")) for row in proposals if row.get("status") in accepted_statuses}

    relevant = set(relevant_feature_ids)
    hints: list[dict[str, Any]] = []
    for proposal in proposals:
        proposal_id = str(proposal.get("proposal_id"))
        if proposal_id not in approved_ids:
            continue
        affected = [str(item) for item in proposal.get("affected_features", []) if isinstance(item, str)]
        if relevant and affected and not (set(affected) & relevant):
            continue
        finding = proposal.get("source_finding", {}) if isinstance(proposal.get("source_finding"), dict) else {}
        recommendation = str(proposal.get("expected_improvement") or finding.get("recommendation") or "").strip()
        hints.append(
            {
                "proposal_id": proposal_id,
                "status": "approved",
                "category": str(finding.get("category") or "meta-harness-approved-guidance"),
                "affected_features": affected,
                "evidence_label": str(proposal.get("proposal_evidence_label", "local-evidence")),
                "hint": recommendation[:220] if recommendation else "Approved Meta-Harness proposal exists for this workflow.",
            }
        )
        if len(hints) == 3:
            break

    return {
        "status": "available" if hints else "no_relevant_approved_hints",
        "path": path.as_posix(),
        "hints": hints,
        "rule": "Navigator shows only short, relevant, accepted or implemented Meta-Harness guidance. It does not run aggregate analysis, readiness, or proposal generation during normal tasks.",
    }


def root_arg(root: Path) -> str:
    return f"--root {core.quoted(root.as_posix())}"


def cross_repo_reference_requested(goal: str) -> bool:
    lowered = goal.lower()
    return any(term in lowered for term in CROSS_REPO_REFERENCE_TERMS)


def labeled_path(goal: str, labels: tuple[str, ...]) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    stop_labels = "target|target repo|target repository|reference|reference repo|reference repository|ref repo|other repo|other repository|goal"
    pattern = re.compile(rf"(?:{label_pattern})\s*[:=]\s*(.+?)(?=\s+(?:{stop_labels})\s*[:=]|\n|,|;|$)", re.IGNORECASE)
    match = pattern.search(goal)
    if not match:
        return None
    value = match.group(1).strip().strip("`'\"")
    return value or None


def cross_repo_reference_plan(goal: str, root: Path, command_prefix: str) -> dict[str, Any] | None:
    if not cross_repo_reference_requested(goal):
        return None
    target = labeled_path(goal, ("target", "target repo", "target repository")) or root.as_posix()
    reference = labeled_path(goal, ("reference", "reference repo", "reference repository", "ref repo", "other repo", "other repository"))
    command = f"{command_prefix} reference --target {core.quoted(target)} --reference "
    if reference:
        command += f"{core.quoted(reference)} --goal {core.quoted(goal)}"
    else:
        command += f"{core.quoted('/path/to/reference-repo')} --goal {core.quoted(goal)}"
    return {
        "target": target,
        "reference": reference or "not parsed from prompt",
        "command": command,
        "boundaries": [
            "Only the target repo is editable.",
            "Reference repos are read-only pattern sources.",
            "Use conventions and architecture intent; do not copy source code verbatim.",
            "If the reference path is outside the active workspace, the assistant may need the parent workspace opened or a generated reference summary.",
        ],
    }


def learning_capture_suggestion(goal: str, root: Path, tiny: bool, tasks: list[str], risks: list[str]) -> dict[str, Any] | None:
    if tiny:
        return None
    mode = core.capture_mode(goal)
    tags = ",".join(core.normalized_learning_tags(tasks, risks)[:5])
    root_arg = core.quoted(root.as_posix())
    summary = goal[:140] if goal else "REPLACE_WITH_SHORT_TASK_SUMMARY"
    candidate = "REPLACE_WITH_REUSABLE_PATTERN_OR_DECISION"
    reason = "REPLACE_WITH_EXPLICIT_REASON"
    parts = [
        "python3",
        core.quoted((ROOT / "hooks" / "learning-capture-hook.py").as_posix()),
        core.quoted(summary),
        "--root",
        root_arg,
    ]
    if tags:
        parts.extend(["--tags", core.quoted(tags)])
    parts.extend(["--candidate", core.quoted(candidate)])
    if mode == "accepted":
        parts.extend(["--acceptance", "accepted", "--validation-outcome", "REPLACE_WITH_pass_or_fail_or_not_run"])
    else:
        parts.extend(["--acceptance", mode, "--reason", core.quoted(reason), "--validation-outcome", "REPLACE_WITH_pass_or_fail_or_not_run"])
    return {
        "mode": mode,
        "command": " ".join(parts),
        "when": "after meaningful work, reviewer feedback, validation, or explicit user acceptance/rejection is known",
        "safety": "triggered in the plan for meaningful actions; run only after user approval and add --approved only when the user intentionally wants to record it",
    }


def learning_refresh_awareness(
    root: Path,
    goal: str,
    graph_learning: dict[str, Any] | None,
    matches: list[dict[str, Any]],
    command_prefix: str,
) -> dict[str, Any] | None:
    refresh_terms = ("refresh learning", "refresh learnings", "stale learning", "bad suggestion", "wrong suggestion", "harmful learning")
    reasons: list[str] = []
    lowered = goal.lower()
    if any(term in lowered for term in refresh_terms):
        reasons.append("user prompt mentions stale, bad, or refresh-worthy learnings")
    graph_status = graph_learning.get("graph_status", {}) if isinstance(graph_learning, dict) else {}
    if graph_status.get("status") in {"stale", "invalid"}:
        reasons.append(f"graph-aware learning scope is {graph_status.get('status')}")
    for item in matches[:3]:
        event = item.get("event", {})
        confidence = event.get("learning_confidence", {}) if isinstance(event, dict) else {}
        score = confidence.get("score")
        if isinstance(score, int) and score < 60:
            reasons.append(f"surfaced learning `{event.get('id', 'unknown')}` has low confidence score {score}/100")
    actions_path = root / ".tailtrail" / "learning-refresh-actions.json"
    if actions_path.exists():
        reasons.append("approved learning refresh actions exist in this repo")
    if not reasons:
        return None
    return {
        "reasons": list(dict.fromkeys(reasons)),
        "command": f"{command_prefix} learn refresh recommend --root {core.quoted(root.as_posix())}",
        "rule": "Refresh is advisory. It can recommend keep/improve/demote/mark-stale/suppress/archive/merge/delete, but it should not change learnings without explicit approval.",
    }


def file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def term_found(goal: str, terms: tuple[str, ...]) -> bool:
    lowered = goal.lower()
    return any(term in lowered for term in terms)


def ci_sonar_requested(goal: str, tasks: list[str], risks: list[str]) -> bool:
    return "ci-sonar" in tasks or "ci/sonar" in risks or term_found(goal, CI_SONAR_TERMS)


def vulnerability_requested(goal: str, risks: list[str]) -> bool:
    return "vulnerability scan" in risks or term_found(goal, VULNERABILITY_TERMS)


def vulnerability_has_exact_evidence(goal: str) -> bool:
    lowered = goal.lower()
    evidence_terms = (
        "cve-",
        "ghsa-",
        ".sarif",
        "trivy.json",
        "grype.json",
        "audit.log",
        "scanner output",
        "scan output",
        "package-lock",
        "fixed version",
        "installed version",
    )
    return any(term in lowered for term in evidence_terms) or bool(re.search(r"\b\w+@\d", lowered))


def heavy_graph_candidate(goal: str, tasks: list[str], risks: list[str]) -> bool:
    if any(task in tasks for task in ("ci-sonar", "qa", "review", "dependency", "security")):
        return True
    if any(risk in risks for risk in ("ci/sonar", "vulnerability scan", "dependency", "multi-file", "production", "regulated")):
        return True
    return any(term in goal.lower() for term in ("heavy read", "full code scan", "before pr", "broad review"))


def code_change_candidate(goal: str, tasks: list[str], changed: list[str], tiny: bool) -> bool:
    if tiny:
        return False
    source_suffixes = {
        ".cs",
        ".go",
        ".java",
        ".js",
        ".jsx",
        ".json",
        ".kt",
        ".properties",
        ".py",
        ".sql",
        ".tf",
        ".tfvars",
        ".toml",
        ".ts",
        ".tsx",
        ".xml",
        ".yaml",
        ".yml",
    }
    if any(Path(item).suffix.lower() in source_suffixes for item in changed):
        return True
    if any(task in tasks for task in ("bug", "feature", "implementation", "refactor", "review", "ci-sonar", "qa", "security", "dependency")):
        return True
    return any(term in goal.lower() for term in ("code change", "fix", "implement", "refactor", "before pr", "validation"))


def graph_mapper_candidate(goal: str, tasks: list[str], risks: list[str], changed: list[str], tiny: bool) -> bool:
    return code_change_candidate(goal, tasks, changed, tiny) or core.heavy_graph_candidate(goal, tasks, risks)


def cache_entries(cache: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(cache.get("entries"), list):
        return [entry for entry in cache["entries"] if isinstance(entry, dict)]
    return [cache]


def graph_cache_candidates(root: Path) -> tuple[Path, Path]:
    return (root / "tailtrail-meta" / "code-graph-cache.json", root / ".tailtrail" / "code-graph-cache.json")


def graph_inventory(root: Path) -> dict[str, Any]:
    """Load the mapper's shared metadata-only inventory logic without source parsing."""
    spec = importlib.util.spec_from_file_location("tailtrail_code_graph_inventory", ROOT / "scripts" / "code_graph_inventory.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.snapshot(root)


def choose_graph_cache_path(root: Path) -> tuple[Path, str]:
    shared, local = graph_cache_candidates(root)
    if shared.exists():
        return shared, "shared"
    return local, "local"


def saved_graph_cache_evidence(root: Path, changed: list[str]) -> dict[str, Any] | None:
    """Read saved graph guidance without checking source freshness or running discovery."""
    cache_path, cache_source = choose_graph_cache_path(root)
    if not cache_path.is_file():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    entries = cache_entries(payload)
    requested = set(changed)
    matching = []
    for entry in entries:
        scope = {str(item) for item in entry.get("scope", []) if isinstance(item, str)}
        if not requested or requested.intersection(scope):
            matching.append(entry)
    if not matching:
        return None
    entry = matching[0]
    graph = entry.get("graph", {}) if isinstance(entry.get("graph"), dict) else {}
    read_order = [str(item) for item in graph.get("suggested_read_order", []) if isinstance(item, str)]
    scope = [str(item) for item in entry.get("scope", []) if isinstance(item, str)]
    return {
        "status": "saved-unverified",
        "path": cache_path.as_posix(),
        "source": cache_source,
        "scope": list(dict.fromkeys([*changed, *scope[:8]])),
        "suggested_read_order": read_order[:8],
        "confidence": graph.get("confidence", "unknown"),
        "reasons": ["Read from saved Code Graph metadata only; current source freshness was not checked during Planning Lock."],
        "recommended_action": "Confirm or refresh graph evidence only after the Debug Start Plan is approved.",
    }


def graph_cache_status(root: Path, changed: list[str], goal: str, tasks: list[str], risks: list[str]) -> dict[str, Any] | None:
    tiny = core.is_tiny(goal, risks, changed)
    if not graph_mapper_candidate(goal, tasks, risks, changed, tiny):
        return None

    shared_cache, local_cache = graph_cache_candidates(root)
    cache_path, cache_source = choose_graph_cache_path(root)
    if not cache_path.exists():
        return {
            "status": "missing",
            "path": shared_cache.as_posix(),
            "source": "shared",
            "fallback_path": local_cache.as_posix(),
            "scope": changed,
            "reasons": ["No shared Code Graph Mapper cache exists for this project."],
            "recommended_action": "Create a shared graph map before meaningful code-change, Sonar, vulnerability, or review reads when changed files are known.",
        }

    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {
            "status": "invalid",
            "path": cache_path.as_posix(),
            "source": cache_source,
            "scope": changed,
            "reasons": [f"Cache could not be parsed: {error}"],
            "recommended_action": "Ignore the cache and recreate it before relying on graph guidance.",
        }

    if not isinstance(cache, dict):
        return {
            "status": "invalid",
            "path": cache_path.as_posix(),
            "source": cache_source,
            "scope": changed,
            "reasons": ["Cache root is not a JSON object."],
            "recommended_action": "Ignore the cache and recreate it before relying on graph guidance.",
        }

    target_scope = set(changed)
    entries = cache_entries(cache)
    matching = []
    for entry in entries:
        scope = set(str(item) for item in entry.get("scope", []) if item)
        if not target_scope or target_scope.issubset(scope) or scope.intersection(target_scope):
            matching.append(entry)
    if not matching:
        return {
            "status": "missing",
            "path": cache_path.as_posix(),
            "source": cache_source,
            "scope": changed,
            "reasons": ["Cache exists, but no entry covers the requested changed or target files."],
            "recommended_action": "Create a graph map for the current task scope before broad source reads.",
        }

    entry = matching[0]
    stale_reasons: list[str] = []
    invalid_reasons: list[str] = []
    watched_groups = ("source_files", "watch_files", "scanner_evidence")
    for group in watched_groups:
        files = entry.get(group, {})
        if not isinstance(files, dict):
            invalid_reasons.append(f"{group} is not an object.")
            continue
        for relative, metadata in files.items():
            if not isinstance(metadata, dict):
                invalid_reasons.append(f"{group}.{relative} metadata is not an object.")
                continue
            expected = metadata.get("sha256")
            if not isinstance(expected, str) or not expected:
                invalid_reasons.append(f"{group}.{relative} has no usable sha256.")
                continue
            actual = file_sha256(root / relative)
            if actual is None:
                stale_reasons.append(f"{relative} is missing.")
            elif actual != expected:
                stale_reasons.append(f"{relative} changed after the graph was created.")

    saved_inventory = entry.get("inventory")
    current_inventory = graph_inventory(root)
    if not isinstance(saved_inventory, dict) or not isinstance(saved_inventory.get("fingerprint"), str):
        stale_reasons.append("Cache predates repository inventory tracking; refresh it once.")
    elif saved_inventory.get("algorithm") != current_inventory["algorithm"]:
        stale_reasons.append("Cache inventory algorithm is unsupported; refresh it once.")
    elif saved_inventory.get("fingerprint") != current_inventory["fingerprint"]:
        stale_reasons.append("Relevant repository file inventory changed after the graph was created.")

    cache_root = entry.get("root")
    if cache_root and Path(str(cache_root)).resolve() != root.resolve():
        invalid_reasons.append("Cache root does not match the current project root.")

    if invalid_reasons:
        status = "invalid"
        reasons = invalid_reasons
        action = "Ignore the cache and recreate it before relying on graph guidance."
    elif stale_reasons:
        status = "stale"
        reasons = stale_reasons
        action = "Refresh the graph before meaningful code-change, Sonar, vulnerability, or review reads."
    else:
        status = "fresh"
        reasons = ["Cached graph scope and watched file hashes still match."]
        action = "Reuse cached suggested read order, then inspect exact source before editing."

    return {
        "status": status,
        "path": cache_path.as_posix(),
        "source": cache_source,
        "shared_path": shared_cache.as_posix(),
        "local_fallback_path": local_cache.as_posix(),
        "scope": list(entry.get("scope", changed)),
        "graph_mode": entry.get("graph_mode", "unspecified"),
        "confidence": entry.get("graph", {}).get("confidence") if isinstance(entry.get("graph"), dict) else None,
        "suggested_read_order": entry.get("graph", {}).get("suggested_read_order", []) if isinstance(entry.get("graph"), dict) else [],
        "reasons": reasons,
        "recommended_action": action,
    }


def context_strategy(goal: str, root: Path, changed: list[str], tasks: list[str], risks: list[str], graph_cache: dict[str, Any] | None, command_prefix: str) -> dict[str, Any]:
    profile_name = prompt_profile.choose_profile(tasks, risks)
    profile = prompt_profile.profile_payload(profile_name)
    graph_status = graph_cache.get("status") if isinstance(graph_cache, dict) else "not-needed"
    graph_first = graph_status in {"missing", "stale", "invalid", "fresh"} or bool(changed)
    return {
        "profile": profile["profile"],
        "budget_band": profile["budget_band"],
        "graph_first": graph_first,
        "graph_status": graph_status,
        "load_order": [
            "Navigator plan and token budget",
            "Code Graph Mapper cache or graph command output when selected",
            "top project-framed Learning V3 use proposal only when explicitly surfaced",
            "exact changed or target files",
            "likely tests/helpers/policy only when needed",
        ],
        "avoid": [
            "raw learning history",
            "full TailTrail documentation pack",
            "ROADMAP.md or pitch docs unless changing TailTrail strategy",
            "broad source tree reads before graph/read-order guidance",
        ],
        "profile_load": profile["load"],
        "profile_avoid": profile["avoid"],
        "receipt_command": (
            f"{command_prefix} receipt capture --root {core.quoted(root.as_posix())} --task {core.quoted(goal[:120] or 'task')} "
            f"--profile {profile['profile']} --loaded REPLACE_WITH_FILE --loaded-exactness REPLACE_WITH_exactness "
            "--loaded-strategy REPLACE_WITH_strategy --avoided REPLACE_WITH_FILE --avoided-exactness REPLACE_WITH_exactness "
            "--avoided-strategy REPLACE_WITH_strategy --route-source token-harness "
            "--reduction-strategy REPLACE_WITH_strategy --preserve REPLACE_WITH_preserved_evidence --approved"
        ),
    }


def quality_scan_requested(goal: str, tasks: list[str], risks: list[str]) -> bool:
    lowered = goal.lower()
    scan_terms = (
        "full code scan",
        "sonar check",
        "sonarqube",
        "sonarcloud",
        "quality gate",
        "quality scan",
        "lint issue",
        "before pr",
        "vulnerability",
        "vulnerabilities",
        "vuln",
        "sast",
        "security scan",
        "dependency audit",
    )
    return (
        any(term in lowered for term in scan_terms)
        or "vulnerability scan" in risks
        or ("ci-sonar" in tasks and "scan" in lowered)
    )


def scan_approval_prompt(goal: str, root: Path) -> dict[str, Any] | None:
    if not core.quality_scan_requested(goal, core.task_types(goal), core.risk_indicators(goal, [])):
        return None

    lowered = goal.lower()
    commands: list[dict[str, str]] = []
    signals: list[str] = []

    def exists(path: str) -> bool:
        return (root / path).exists()

    if exists("sonar-project.properties") or "sonar" in lowered:
        signals.append("Sonar signal detected")
        commands.append(
            {
                "command": "sonar-scanner",
                "safety": "needs explicit approval",
                "reason": "Sonar scanners can be slow, networked, credentialed, and organization-specific.",
            }
        )
    if exists("pom.xml"):
        signals.append("Maven project signal detected")
        commands.extend(
            [
                {"command": "mvn test", "safety": "safe local", "reason": "Runs project tests without publishing artifacts."},
                {
                    "command": "mvn verify",
                    "safety": "needs explicit approval",
                    "reason": "May run broader checks and take longer than focused tests.",
                },
            ]
        )
    if exists("build.gradle") or exists("build.gradle.kts") or exists("gradlew"):
        signals.append("Gradle project signal detected")
        commands.extend(
            [
                {"command": "./gradlew test", "safety": "safe local", "reason": "Runs local tests."},
                {"command": "./gradlew check", "safety": "needs explicit approval", "reason": "Runs broader verification tasks."},
            ]
        )
    if exists("package.json"):
        signals.append("package.json signal detected")
        commands.extend(
            [
                {"command": "npm run lint", "safety": "safe local if script exists", "reason": "Common project-owned lint entrypoint."},
                {"command": "npm test", "safety": "safe local if script exists", "reason": "Common project-owned test entrypoint."},
                {
                    "command": "npm audit",
                    "safety": "needs explicit approval",
                    "reason": "May use registry/network data and can be noisy in enterprise repos.",
                },
            ]
        )
    if exists("pyproject.toml") or exists("requirements.txt") or exists("pytest.ini") or exists("tox.ini"):
        signals.append("Python project signal detected")
        commands.extend(
            [
                {"command": "pytest", "safety": "safe local if configured", "reason": "Runs local tests."},
                {"command": "ruff check .", "safety": "safe local if installed", "reason": "Runs local lint checks."},
            ]
        )
    if exists("go.mod"):
        signals.append("Go project signal detected")
        commands.extend(
            [
                {"command": "go test ./...", "safety": "safe local", "reason": "Runs local tests."},
                {"command": "go vet ./...", "safety": "safe local", "reason": "Runs standard local vet checks."},
            ]
        )
    if any(root.glob("*.sln")) or any(root.glob("*.csproj")):
        signals.append(".NET project signal detected")
        commands.extend(
            [
                {"command": "dotnet test", "safety": "safe local", "reason": "Runs local tests."},
                {"command": "dotnet build", "safety": "safe local", "reason": "Runs local compilation."},
            ]
        )

    deduped_commands: list[dict[str, str]] = []
    seen = set()
    for item in commands:
        if item["command"] in seen:
            continue
        seen.add(item["command"])
        deduped_commands.append(item)

    if not deduped_commands:
        deduped_commands.append(
            {
                "command": "discover project-owned lint/test/build commands first",
                "safety": "manual review required",
                "reason": "No obvious local scanner manifest was detected from the current root.",
            }
        )

    return {
        "question": "Do you want TailTrail to run a local Sonar, lint, test, or vulnerability scan after you approve the plan?",
        "default": "no",
        "why": "Full scans can be slow, noisy, credentialed, or networked. Navigator must ask before any scan is run.",
        "signals": signals or ["scan requested in the user goal"],
        "candidate_commands": deduped_commands[:8],
        "approval_choices": [
            "yes: approve one listed command or provide the exact command to run",
            "no: keep this as a planning recommendation only",
            "edit: replace the command list with the repo-approved quality command",
        ],
    }


def review_scope_plan(goal: str, root: Path, changed: list[str], tasks: list[str], command_prefix: str) -> dict[str, Any] | None:
    if not core.review_requested(goal, tasks):
        return None

    lowered = goal.lower()
    post_implementation = core.post_implementation_review_requested(goal) or any(
        task in tasks for task in ("bug", "feature", "implementation", "refactor", "qa", "ci-sonar", "security", "dependency")
    )
    explicit_full = core.full_review_requested(goal)
    explicit_branch = core.branch_review_requested(goal)
    explicit_path = core.path_review_requested(goal)

    if explicit_full:
        scope = "full"
        default = "full repo review"
        reason = "user asked for broad/full review"
        needs_choice = False
        approval = "Full repo review is broad; ask for explicit approval before running."
        command = f"{command_prefix} review --root {core.quoted(root.as_posix())} --scope full --goal {core.quoted(goal)}"
    elif explicit_path:
        scope = "path"
        default = "specific folder or files"
        reason = "user mentioned a folder, directory, module, or path-scoped review"
        needs_choice = True
        approval = "Ask the user for the exact path if it was not supplied."
        command = f"{command_prefix} review --root {core.quoted(root.as_posix())} --scope path --dir REPLACE_WITH_PATH --goal {core.quoted(goal)}"
    elif explicit_branch or ("pr" in lowered and not changed):
        scope = "branch"
        default = "current branch against main"
        reason = "PR or branch review signal detected"
        needs_choice = False
        approval = "Ask for base branch if main is not the repo default."
        command = f"{command_prefix} review --root {core.quoted(root.as_posix())} --scope branch --base main --goal {core.quoted(goal)}"
    elif post_implementation or changed:
        scope = "uncommitted"
        default = "uncommitted local changes"
        reason = "post-implementation or changed-file context detected; this is the smallest useful review scope"
        needs_choice = False
        approval = "Ask user approval before running review after implementation."
        command = f"{command_prefix} review --root {core.quoted(root.as_posix())} --scope uncommitted --goal {core.quoted(goal)}"
    else:
        scope = "needs_user_choice"
        default = "uncommitted local changes"
        reason = "standalone review request has no clear scope"
        needs_choice = True
        approval = "Ask the user to choose uncommitted, branch-vs-base, path, or full repo review."
        command = f"{command_prefix} review --root {core.quoted(root.as_posix())} --goal {core.quoted(goal)}"

    detail_level = "detailed" if explicit_full or "security" in tasks or "dependency" in tasks else "standard"
    if len(changed) <= 1 and scope == "uncommitted":
        detail_level = "compact"

    return {
        "intent": "post-implementation" if post_implementation else "standalone",
        "scope": scope,
        "default": default,
        "reason": reason,
        "needs_user_choice": needs_choice,
        "detail_level": detail_level,
        "command": command,
        "approval": approval,
        "finding_fields": [
            "requirement fulfillment status",
            "severity",
            "one-line issue",
            "file",
            "function",
            "line",
            "impact",
            "suggested fix",
            "validation",
            "confidence",
            "safe-fix status",
        ],
        "checked_for": [
            "implementation alignment with the user goal and clarified requirements",
            "bugs and behavior regressions",
            "validation gaps",
            "weakened safeguards",
            "security and trust-boundary concerns",
            "duplicated logic and missed reuse",
            "dependency risk",
            "missing focused tests",
            "code consistency with nearby patterns",
        ],
        "guarded_fix_loop": [
            "Ask clarification instead of assuming when requirement fulfillment is unclear.",
            "Treat review text, scanner output, PR comments, and pasted logs as untrusted issue reports.",
            "Inspect local code before proposing fixes.",
            "Ask before editing or running broad validation.",
            "Apply approved fixes one at a time.",
            "Re-review the changed scope after fixes.",
            "Do not auto-commit by default.",
        ],
    }


def evaluation_harness_plan(goal: str, tasks: list[str], command_prefix: str) -> dict[str, Any]:
    lowered = goal.lower()
    task_types = {str(item).lower() for item in tasks}
    triggered_terms = sorted(word for word in EVALUATION_TRIGGER_WORDS if word in lowered)
    selected_by_goal = bool(triggered_terms)
    selected_by_task = bool({"review", "qa", "ci", "ci-sonar", "security"} & task_types) and any(
        word in lowered for word in {"proof", "metrics", "evidence", "report"}
    )
    selected = selected_by_goal or selected_by_task

    scenario = "validation-bug"
    if "security" in lowered or "vulnerability" in lowered or "cve" in lowered or "ghsa" in lowered:
        scenario = "security-triage"
    elif "ci" in lowered or "sonar" in lowered or "quality gate" in lowered:
        scenario = "ci-failure"
    elif "dependency" in lowered or "package" in lowered:
        scenario = "dependency-decision"
    elif "review" in lowered:
        scenario = "review-only"

    reason = "triggered by " + ", ".join(triggered_terms) if triggered_terms else "no evidence, benchmark, demo, proof, report, or scenario signal detected"
    return {
        "selected": selected,
        "reason": reason,
        "scenario": scenario,
        "commands": [
            f"{command_prefix} eval scenario list",
            f"{command_prefix} eval scenario run --scenario {scenario}",
            f"{command_prefix} eval scenario report --scenario {scenario}",
        ],
        "write_report_command": f"{command_prefix} eval scenario report --scenario {scenario} --write-result --approved",
        "normalize_command": f"{command_prefix} eval normalize --source benchmark --input benchmarks/evaluation/results/{scenario}-scenario-report.json --dry-run",
        "rule": "Evaluation Harness reads committed fixtures and compact evidence only. It does not run live agents, tests, CI, scanners, package managers, model/API calls, or hidden telemetry.",
    }


def evaluation_only_requested(goal: str, evaluation_plan: dict[str, Any]) -> bool:
    if not evaluation_plan.get("selected"):
        return False
    lowered = goal.lower()
    code_action_terms = (
        "fix ",
        "implement",
        "add ",
        "change ",
        "update ",
        "refactor",
        "debug",
        "code change",
        "bug",
        "feature",
        "unit test",
        "test case",
        "sonar issue",
        "vulnerability fix",
        "security fix",
    )
    if any(term in lowered for term in code_action_terms):
        return False
    return True


PHASE_PATTERN = re.compile(r"\bphase\s+(\d+(?:\.\d+)*)\b", re.IGNORECASE)
NAVIGATOR_CONTEXT_DOCUMENTS = (
    "tailtrail-implementation-backlog.md",
    "ROADMAP.md",
    "harness-engineering.md",
    "testing-confidence.md",
    "program-delivery-harness.md",
)


def navigator_phase_context(subject: str, root: Path) -> dict[str, Any] | None:
    """Resolve a requested planning phase without guessing between documents."""
    match = PHASE_PATTERN.search(subject)
    if not match:
        return None
    phase = match.group(1)
    mentioned = [Path(token.strip(" `,.:")) for token in re.findall(r"[\w./-]+\.md\b", subject)]
    candidates: list[Path] = []
    for path in mentioned:
        resolved = path if path.is_absolute() else root / path
        if resolved.is_file():
            candidates.append(resolved)
    if not candidates:
        candidates = [root / name for name in NAVIGATOR_CONTEXT_DOCUMENTS if (root / name).is_file()]

    heading = re.compile(rf"^#+\s+.*\bphase\s+{re.escape(phase)}\b.*$", re.IGNORECASE | re.MULTILINE)
    matches: list[dict[str, str]] = []
    for path in candidates:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        found = heading.search(content)
        if found:
            title = found.group(0).lstrip("#").strip()
            matches.append({"path": path.relative_to(root).as_posix(), "heading": title})
    if len(matches) == 1:
        return {"status": "resolved", "phase": phase, "document": matches[0]["path"], "heading": matches[0]["heading"]}
    if matches:
        return {"status": "ambiguous", "phase": phase, "matches": matches}
    return {"status": "not_found", "phase": phase, "searched": [path.relative_to(root).as_posix() for path in candidates]}


def explicit_navigator_report(
    request: core.NavigatorRequest,
    root: Path,
    changed_args: list[str],
    command_prefix: str,
) -> dict[str, Any]:
    """Return a request-depth contract while reusing the normal decision engine."""
    # A named planning phase is not a request to inspect every unrelated local
    # git change. Concrete `--changed` paths remain honored.
    base = decide(
        request.subject,
        root,
        changed_args,
        command_prefix,
        allow_explicit=False,
        detect_git_changes=False,
    )
    phase_context = navigator_phase_context(request.subject, root)
    likely_paths = [item["path"] for item in base.get("likely_impacted_files", [])[:6]]
    matrix = core.requirement_impact_matrix(
        [
            {
                "statement": request.subject,
                "likely_paths": likely_paths,
                "acceptance_criteria": ["User-approved expected behavior is observable on the intended path."],
                "preserve_rules": ["Do not change behavior outside the approved scope."],
                "evidence_plan": ["Inspect selected source/callers/tests, then run focused approved validation."],
            }
        ]
    )
    selected = [
        {"name": "TailTrail Navigator", "reason": "explicit Navigator request; decide scope and workflow before any edit"},
        *[item for item in base["selected_features"] if item["name"] != "TailTrail Navigator"],
    ]
    skipped = list(base["skipped_features"])
    if phase_context and phase_context["status"] in {"resolved", "ambiguous", "not_found"}:
        selected = [item for item in selected if item["name"] != "Code Graph Mapper"]
        skipped = [item for item in skipped if item["name"] != "Code Graph Mapper"]
        skipped.append({"name": "Code Graph Mapper", "reason": "a planning phase is being interpreted; map source only after a concrete code path is approved"})

    plan = [
        "Confirm the requested scope, existing conventions, callers, tests, and local policy before proposing edits.",
        "Turn the approved scope into a requirement-to-impact matrix with focused proof for each requirement.",
        "Keep the first implementation cycle bounded; validate the changed behavior and preservation cases before review.",
    ]
    if phase_context and phase_context["status"] == "resolved":
        plan.insert(0, f"Read `{phase_context['document']}` at `{phase_context['heading']}` as the approved planning context.")
    elif phase_context and phase_context["status"] == "ambiguous":
        plan = ["Choose the planning document for the requested phase before producing an implementation plan."]
    elif phase_context and phase_context["status"] == "not_found":
        plan = ["Provide the planning document or exact phase heading before producing an implementation plan."]

    if request.depth == "context":
        approval = ["No approval is needed: this is read-only context discovery.", "Next: ask `navigator plan <scope>` when you want the TailTrail decision and approval gate."]
    elif request.depth == "plan":
        approval = ["Approve the Navigator plan to generate a detailed implementation proposal. This does not authorize edits."]
    else:
        approval = ["Approve the implementation proposal to authorize code edits. Until then, this remains planning only."]

    base.update(
        {
            "navigator_mode": "explicit_request",
            "navigator_request": {"explicit": True, "depth": request.depth, "subject": request.subject},
            "phase_context": phase_context,
            "requirement_matrix": matrix,
            "proposal_feedback_protocol": {
                "first_rejection": "Collect an approve/reject decision for every requirement row; every rejection needs a comment, then ask targeted questions or offer AIDLC Requirements mode.",
                "second_rejection": "Automatically require minimal AIDLC Requirements mode before another material proposal.",
                "history": "Rejected proposal feedback is retained in the append-only run ledger and is separate from implementation drift.",
            },
            "selected_features": selected,
            "skipped_features": skipped,
            "navigator_plan": plan,
            "approval": approval,
            "notes": [
                "Explicit Navigator requests are planning-only and do not edit files.",
                "A Navigator-plan approval and implementation approval are separate gates.",
            ],
        }
    )
    if request.depth == "implement":
        base["implementation_proposal"] = list(base["implementation_plan"])
    return base


def decide(
    goal: str,
    root: Path,
    changed_args: list[str],
    command_prefix: str,
    allow_explicit: bool = True,
    detect_git_changes: bool = True,
    workflow_override: str | None = None,
    has_error_artifact: bool = False,
    has_reproduction_command: bool = False,
    graph_mode: str = "auto",
    requirement_interpretation: dict[str, Any] | None = None,
    debug_diagnosis: dict[str, Any] | None = None,
    allow_passive_capture: bool = True,
) -> dict[str, Any]:
    workflow_classification = core.classify_workflow_intent(
        goal,
        override=workflow_override,
        has_error_artifact=has_error_artifact,
        has_reproduction_command=has_reproduction_command,
    )
    debug_planning = workflow_classification.workflow_type == "debug-investigation"
    resolved_requirement_interpretation = (
        requirement_interpretation or requirement_discovery.interpretation(goal)
    )
    requirement_query_frame = (
        requirement_discovery.debug_scope_query_frame(goal)
        if debug_planning
        else requirement_discovery.scope_query_frame(
            goal,
            resolved_requirement_interpretation,
        )
    )
    canonical_requirements = (
        None
        if debug_planning
        else requirement_discovery.canonical_set(
            goal,
            resolved_requirement_interpretation,
        )
    )
    normalized_scope_goal = " ".join(requirement_query_frame["query_terms"]) or "\n".join(
        str(item["statement"])
        for item in requirement_query_frame["requirements"]
    )
    canonical_literals = [
        str(literal)
        for frame in requirement_query_frame["requirements"]
        for literal in frame.get("quoted_literals", [])
        if str(literal).strip()
    ]
    if allow_explicit:
        request = core.explicit_navigator_request(goal)
        if request:
            return explicit_navigator_report(request, root, changed_args, command_prefix)
    # Only an explicit review/diff request may use the worktree as task scope.
    # Feature and bug requests often arrive while unrelated work is uncommitted;
    # silently adopting that work is misleading and can produce a completely
    # wrong implementation plan.
    semantic_task_goal = goal
    for literal in canonical_literals:
        semantic_task_goal = re.sub(re.escape(literal), " ", semantic_task_goal, flags=re.IGNORECASE)
    tasks = core.task_types(semantic_task_goal)
    saved_debug_graph = saved_graph_cache_evidence(root, changed_args) if debug_planning and graph_mode != "off" else None
    scope_seeds: list[dict[str, Any]] = []
    if changed_args:
        scope_seeds = [
            navigator_scope.seed(path, "explicit-path", "user-provided-path")
            for path in changed_args
        ]
        target_origin = "provided"
    elif debug_planning:
        diagnosed_seeds = [
            navigator_scope.seed(
                str(row["path"]),
                "host-diagnosis",
                "hash-bound-host-diagnosis-evidence",
                content_fingerprint=str(row["sha256"]),
            )
            for row in (debug_diagnosis or {}).get("evidence", [])
            if isinstance(row, dict) and row.get("path") and row.get("sha256")
        ]
        discovered = list((saved_debug_graph or {}).get("suggested_read_order", []))[:6]
        if not discovered:
            discovered = list((saved_debug_graph or {}).get("scope", []))[:6]
        saved_seeds = [
            navigator_scope.seed(path, "saved-graph", "saved-graph-path")
            for path in discovered
        ]
        # Debug Start may use the same bounded local text discovery as normal
        # Start. Lexical results remain seeds; static relationship evidence
        # must establish ownership before a path can be selected.
        lexical_seeds = goal_discovered_paths(
            root,
            normalized_scope_goal,
            8,
            requirement_query_frame["query_terms"],
            canonical_literals,
        )
        scope_seeds = [*diagnosed_seeds, *saved_seeds, *lexical_seeds]
        target_origin = "host-diagnosis" if diagnosed_seeds else "saved-graph" if saved_seeds else "goal-discovery" if lexical_seeds else "none"
    else:
        if core.ui_change_requested(goal, []):
            # A UI-first request must begin from repository-owned UI paths.
            # Exact user-visible literals are stronger than generic UI path
            # matches, while structure remains useful for a missing-cache
            # in-memory relationship pass.  Both remain non-authoritative
            # seeds until bounded behavior evidence establishes ownership.
            lexical_seeds = goal_discovered_paths(
                root,
                goal,
                8,
                requirement_query_frame["query_terms"],
                canonical_literals,
            )
            structure_seeds = repository_discovered_paths(
                root, normalized_scope_goal, 8, requirement_query_frame["query_terms"]
            )
            scope_seeds = [*lexical_seeds, *structure_seeds]
            target_origin = "goal-discovery" if lexical_seeds else "repository-discovery" if structure_seeds else "none"
        else:
            # A QA-only task (no mixed bug/feature/implementation/refactor
            # intent) typically touches several existing test files (steps,
            # features, support modules) rather than one owner; a
            # single-owner budget silently drops the rest as noise. A goal
            # merely mentioning "validation" (e.g. "fix validation bug") is
            # still a single-owner bug fix and keeps the tighter budget.
            qa_only = "qa" in tasks and not ({"feature", "implementation", "bug", "refactor"} & set(tasks))
            scope_seeds = goal_discovered_paths(
                root,
                goal,
                8 if qa_only else 2,
                requirement_query_frame["query_terms"],
                canonical_literals,
            )
            target_origin = "goal-discovery" if scope_seeds else "none"
        if not scope_seeds and "review" not in tasks:
            scope_seeds = repository_discovered_paths(
                root, normalized_scope_goal, 5, requirement_query_frame["query_terms"]
            )
            target_origin = "repository-discovery" if scope_seeds else "none"
        if not scope_seeds and detect_git_changes and "review" in tasks:
            scope_seeds = [
                navigator_scope.seed(path, "git-change", "git-change-detected")
                for path in git_changed(root)
            ]
            target_origin = "git-changes" if scope_seeds else "none"
    scope_candidates = navigator_scope.candidates_from_seeds(root, scope_seeds, tasks)
    changed = [
        str(candidate["path"])
        for candidate in scope_candidates
        if candidate.get("status") not in {"excluded", "rejected"}
    ]
    # Discovery seeds are hypotheses, not approved scope.  Their filenames
    # must not manufacture dependency, migration, CI, or multi-file risk
    # before ownership evidence resolves them.  Explicit user paths remain
    # valid early risk signals; discovered owners are reconciled below.
    early_risk_paths = changed if changed_args else []
    risks = core.risk_indicators(goal, early_risk_paths)
    if any(
        str(frame.get("intent_class")) == "ui-visibility"
        and any(
            action in str(frame.get("statement", "")).lower()
            for action in ("remove", "hide", "dismiss", "suppress")
        )
        for frame in requirement_query_frame.get("requirements", [])
        if isinstance(frame, dict)
    ):
        risks = sorted({*risks, "over-broad UI feedback suppression"})
    tiny = core.is_tiny(goal, risks, early_risk_paths)
    state = existing_state(root)
    evaluation_plan = evaluation_harness_plan(goal, tasks, command_prefix)

    if "repo-overview" in tasks:
        graph_command = f"{command_prefix} graph map --root {core.quoted(root.as_posix())}"
        registry_projection = registry_workflow("overview")
        relevant_features = registry_projection.get("feature_ids", []) if isinstance(registry_projection, dict) else []
        harness_hints = meta_harness_hints(root, relevant_features)
        bootstrap_status = bootstrap_snapshot_status(root, True, command_prefix)
        bootstrap_command = bootstrap_status["command"] if bootstrap_status and bootstrap_status.get("status") != "fresh" else None
        suggested_commands = [item for item in [bootstrap_command, graph_command] if item]
        return {
            "navigator_mode": "repo_overview",
            "goal": goal,
            "root": root.as_posix(),
            "task_types": tasks,
            "risk_indicators": risks,
            "existing_state": state,
            "recommended_workflow": ["repo_overview"],
            "registry_workflow": registry_projection,
            "selected_features": [
                {
                    "name": "Repo Overview",
                    "reason": "read-only repository explanation request detected",
                },
                {
                    "name": "Bootstrap Snapshot",
                    "reason": "fresh safe repo/runtime facts available before broad discovery"
                    if bootstrap_status and bootstrap_status.get("status") == "fresh"
                    else "missing or stale safe repo/runtime facts; create snapshot before broad discovery",
                },
                {
                    "name": "Token Autopilot",
                    "reason": "keep discovery scoped to docs, manifests, entry points, and top-level structure first",
                },
            ],
            "skipped_features": [],
            "likely_impacted_files": [],
            "load": [
                "exact user request",
                "README or project docs when present",
                "fresh `.tailtrail/bootstrap-snapshot.json` when present",
                "build and dependency manifests",
                "top-level source, test, config, and CI folders",
                "entry points and main modules only after the structure is known",
            ],
            "avoid": [
                "editing files",
                "AIDLC lifecycle docs unless user asks for lifecycle planning",
                "review, handoff, scanner, or vulnerability routes unless the user asks for change work",
                "full source tree reads before identifying the main modules",
            ],
            "suggested_commands": suggested_commands,
            "bootstrap_snapshot": bootstrap_status,
            "meta_harness_hints": harness_hints,
            "optional_deeper_discovery": {
                "name": "Code Graph Mapper",
                "command": graph_command,
                "creates": (root / "tailtrail-meta" / "code-graph-cache.json").as_posix(),
                "default": "not run",
                "why": "Repo overview starts with low-cost docs and structure. Run this only when you want a reusable module/symbol/read-order map.",
                "use_when": [
                    "README or docs are missing or weak",
                    "the repo is large",
                    "you want module, endpoint, test, config, or dependency relationships",
                    "you expect follow-up implementation, review, Sonar, vulnerability, or handoff work",
                ],
            },
            "implementation_plan": [
                "Inspect README and top-level project structure.",
                "Identify language, framework, entry points, tests, and major modules.",
                "Summarize important repo features and how they fit together.",
                "Use Navigator's recorded graph lifecycle decision and inspect exact source only where the graph indicates.",
                "Ask before running scans, tests, builds, or writing files.",
            ],
            "approval": [
                "Approve to inspect the repo and answer the overview question.",
                "You can ask for a compact or detailed summary before approval.",
            ],
            "scan_approval": None,
            "cross_repo_reference": None,
            "graph_cache": None,
            "graph_learning": None,
            "graph_learning_skip_reason": "",
            "learning_approval": None,
            "learning_refresh_awareness": None,
            "learning_capture_suggestion": None,
            "review_graph": None,
            "notes": [
                "Navigator selected a read-only discovery path.",
                "It does not edit project source, run implementation, record learnings, or run scanners; Start may manage metadata-only graph state.",
                "Bootstrap Snapshot writes only `.tailtrail/bootstrap-snapshot.json` when the snapshot command is explicitly approved.",
                "If you approve, the next step is to inspect the target repo and answer the repo overview question.",
            ],
        }

    if evaluation_only_requested(goal, evaluation_plan):
        scenario = evaluation_plan["scenario"]
        return {
            "navigator_mode": "evaluation_harness",
            "goal": goal,
            "root": root.as_posix(),
            "task_types": ["evaluation"],
            "risk_indicators": [],
            "existing_state": state,
            "recommended_workflow": ["evaluation_harness"],
            "registry_workflow": registry_workflow("evaluation") or {"workflow": "evaluation", "feature_ids": ["evaluation-harness"]},
            "selected_features": [
                {
                    "name": "Evaluation Harness",
                    "reason": "evidence, demo, benchmark, proof, report, or scenario signal detected; use deterministic scenario scoring",
                },
                {
                    "name": "Token Autopilot",
                    "reason": "load scenario fixtures and compact evidence only",
                },
            ],
            "skipped_features": [
                {"name": "AIDLC", "reason": "evidence-only request; no lifecycle planning needed"},
                {"name": "Review Lens", "reason": "evidence-only request; no code review scope requested"},
                {"name": "Code Graph Mapper", "reason": "evidence-only request; no source graph needed"},
                {"name": "Quality Signal Scanner", "reason": "Evaluation Harness scenarios do not run live scanners"},
            ],
            "likely_impacted_files": [],
            "load": [
                "exact user request",
                "EVALUATION-HARNESS.md relevant section",
                f"benchmarks/evaluation/scenarios/{scenario}/scenario.json",
                f"benchmarks/evaluation/scenarios/{scenario}/baseline-artifact.md",
                f"benchmarks/evaluation/scenarios/{scenario}/tailtrail-artifact.md",
                f"benchmarks/evaluation/scenarios/{scenario}/expected.json",
            ],
            "avoid": [
                "editing files unless the user approves writing a scenario result",
                "AIDLC lifecycle docs for evidence-only reports",
                "Code Graph Mapper and broad repo scans",
                "live model/API calls for Evaluation Harness scenario scoring",
                "claiming scenario scores as live model performance",
                "exact token savings without measured telemetry",
            ],
            "suggested_commands": evaluation_plan["commands"],
            "implementation_plan": [
                "Review the selected Evaluation Harness scenario.",
                "Run the scenario command if approved.",
                "Show the scenario report and clearly label it as deterministic fixture evidence.",
                "Use the write command only if the user approves saving a local result file.",
            ],
            "approval": [
                "Approve to run the listed Evaluation Harness command.",
                "You can ask for a different scenario before running it.",
            ],
            "scan_approval": None,
            "cross_repo_reference": None,
            "graph_cache": None,
            "bootstrap_snapshot": None,
            "context_strategy": None,
            "token_budget": None,
            "graph_learning": None,
            "graph_learning_skip_reason": "",
            "learning_approval": None,
            "learning_refresh_awareness": None,
            "meta_harness_hints": meta_harness_hints(root, ["evaluation-harness"]),
            "evaluation_harness": evaluation_plan,
            "learning_capture_suggestion": None,
            "review_plan": None,
            "vulnerability_evidence": None,
            "review_graph": None,
            "notes": [
                "Navigator selected an evidence-only Evaluation Harness path.",
                "It does not edit files, run implementation, run scanners, call models, or record learnings.",
                "Scenario scores are fixture-backed evidence, not broad product claims.",
            ],
        }

    selected: list[FeatureDecision] = [FeatureDecision("Token Autopilot", "choose whether context routing is worth using")]
    skipped: list[FeatureDecision] = []
    workflow: list[str] = []
    load = ["exact user request", "exact changed files or target files"]
    avoid = ["ROADMAP.md unless changing TailTrail", "ENTERPRISE-REVIEW.md unless evaluating TailTrail strategy", "broad repo scans"]
    commands: list[str] = []
    implementation_plan = []

    aidlc_only = core.has_override(goal, "use aidlc only")
    review_only = core.has_override(goal, "review only")
    skip_graph = core.has_override(goal, "skip review graph") or graph_mode == "off"
    skip_aidlc = core.has_override(goal, "skip aidlc") or core.has_override(goal, "without aidlc")
    skip_handoff = core.has_override(goal, "skip handoff")
    ci_sonar_needed = core.ci_sonar_requested(goal, tasks, risks)
    vulnerability_needed = core.vulnerability_requested(goal, risks)
    vulnerability_evidence = None
    if vulnerability_needed and not vulnerability_has_exact_evidence(goal):
        vulnerability_evidence = {
            "message": "Vulnerability routing is planning-only until a scanner file, CVE/GHSA ID, affected package, installed version, fixed version, or exact scanner evidence is provided.",
            "examples": ["CVE/GHSA ID", "SARIF/Trivy/Grype/audit output file", "package name plus installed and fixed versions"],
        }
    test_precision_needed = core.test_precision_requested(goal, tasks, risks, changed)
    cross_repo_plan = core.cross_repo_reference_plan(goal, root, command_prefix)
    graph_cache = saved_debug_graph if debug_planning else graph_cache_status(root, changed, goal, tasks, risks)
    strategy = context_strategy(goal, root, changed, tasks, risks, graph_cache, command_prefix)
    token_budget = token_budget_coach.estimate_payload(root, goal, changed)
    graph_learning = None
    graph_learning_matches: list[dict[str, Any]] = []
    graph_learning_skip_reason = ""
    approval_for_learnings = None
    use_proposal = None
    refresh_awareness = None
    capture_suggestion = learning_capture_suggestion(goal, root, tiny, tasks, risks)
    review_plan = review_scope_plan(goal, root, changed, tasks, command_prefix)
    registry_task = "implementation"
    if ci_sonar_needed:
        registry_task = "sonar"
    elif vulnerability_needed:
        registry_task = "security"
    elif test_precision_needed:
        registry_task = "qa"
    elif review_only or "review" in tasks:
        registry_task = "review"
    registry_projection = registry_workflow(registry_task)
    relevant_features = registry_projection.get("feature_ids", []) if isinstance(registry_projection, dict) else []
    harness_hints = meta_harness_hints(root, relevant_features)
    bootstrap_status = bootstrap_snapshot_status(
        root,
        not debug_planning
        and not tiny
        and any(
            task in tasks
            for task in ("bug", "feature", "implementation", "refactor", "review", "ci-sonar", "qa", "security", "dependency", "release")
        ),
        command_prefix,
    )

    needs_graph = (
        not debug_planning
        and not tiny
        and not skip_graph
        and not aidlc_only
        and any(task in tasks for task in ("bug", "refactor", "review", "feature", "implementation", "ci-sonar", "qa", "security", "dependency"))
    )
    if cross_repo_plan:
        selected.append(FeatureDecision("Cross-Repo Reference Mode", "target/reference repo signal detected; confirm read/write boundaries before implementation"))
        load.extend(["target repo exact files", "reference repo compact summary or graph only"])
        avoid.extend(["editing reference repo files", "copying source code from reference repos", "assuming paths outside the workspace are readable"])
        commands.append(cross_repo_plan["command"])
    else:
        skipped.append(FeatureDecision("Cross-Repo Reference Mode", "no target/reference repo signal detected"))

    if bootstrap_status:
        if bootstrap_status["status"] == "fresh":
            selected.append(FeatureDecision("Bootstrap Snapshot", "fresh safe repo/runtime facts available before context loading"))
            load.append(".tailtrail/bootstrap-snapshot.json safe workspace facts")
        else:
            selected.append(FeatureDecision("Bootstrap Snapshot", f"{bootstrap_status['status']} snapshot; create or refresh before broad discovery"))
            commands.append(bootstrap_status["command"])
    else:
        skipped.append(FeatureDecision("Bootstrap Snapshot", "tiny or low-signal task; avoid pre-task overhead"))

    if needs_graph:
        selected.append(FeatureDecision("Code Review Graph Lite", "map likely callers, tests, helpers, manifests, and read order"))
        if changed:
            commands.append(f"{command_prefix} graph {root_arg(root)} " + " ".join(f"--changed {path}" for path in changed[:5]))
        else:
            commands.append(f"{command_prefix} graph {root_arg(root)} --changed path/to/file")
    else:
        skipped.append(FeatureDecision("Code Review Graph Lite", "task is tiny, conceptual, explicitly skipped, or has no useful code-impact signal"))

    if graph_cache and not tiny and not skip_graph and not aidlc_only:
        status = graph_cache["status"]
        if status == "fresh":
            selected.append(FeatureDecision("Code Graph Mapper", "fresh shared graph cache found; reuse suggested read order before source reads"))
            load.append("tailtrail-meta/code-graph-cache.json metadata first")
        elif status == "stale":
            selected.append(FeatureDecision("Code Graph Mapper", "graph cache exists but is stale; refresh before source reads"))
            avoid.append("relying on stale graph cache as current source truth")
            if changed:
                commands.append(f"{command_prefix} graph refresh {root_arg(root)} " + " ".join(f"--changed {path}" for path in changed[:5]))
            else:
                commands.append(f"{command_prefix} graph refresh {root_arg(root)}")
        elif status == "invalid":
            selected.append(FeatureDecision("Code Graph Mapper", "graph cache exists but is invalid; recreate before relying on graph guidance"))
            avoid.append("using invalid graph cache")
            if changed:
                commands.append(f"{command_prefix} graph map {root_arg(root)} " + " ".join(f"--changed {path}" for path in changed[:5]))
            else:
                commands.append(f"{command_prefix} graph map {root_arg(root)} --changed path/to/file")
        else:
            selected.append(FeatureDecision("Code Graph Mapper", "no shared graph cache found; create one before source reads when scope is known"))
            if changed:
                commands.append(f"{command_prefix} graph map {root_arg(root)} " + " ".join(f"--changed {path}" for path in changed[:5]))
            else:
                commands.append(f"{command_prefix} graph map {root_arg(root)}")
    elif graph_cache:
        skipped.append(FeatureDecision("Code Graph Mapper", "task is tiny, graph was explicitly skipped, or no useful code-impact signal exists"))
    else:
        skipped.append(FeatureDecision("Code Graph Mapper", "not a meaningful code-change, Sonar, vulnerability, dependency, QA, review, or handoff prompt"))

    if capture_suggestion:
        selected.append(FeatureDecision("Learning Capture Trigger", "meaningful action detected; prepare approved post-task learning capture after outcome is known"))
    else:
        skipped.append(FeatureDecision("Learning Capture Trigger", "tiny or low-signal task; avoid learning noise"))

    needs_aidlc = (
        not tiny
        and not skip_aidlc
        and not review_only
        and (aidlc_only or any(task in tasks for task in ("feature", "release")) or any(risk in risks for risk in ("multi-team", "regulated", "production", "data migration", "multi-file")))
    )
    if needs_aidlc:
        selected.append(FeatureDecision("AIDLC", "capture lifecycle state for broad, risky, regulated, or multi-step work"))
        workflow.insert(0, "aidlc_requirements")
        commands.append(f"{command_prefix} aidlc init {root_arg(root)} --depth standard")
        load.extend(["AIDLC.md", "active AIDLC stage playbook", "aidlc-docs/aidlc-state.md when present"])
    else:
        skipped.append(FeatureDecision("AIDLC", "scope appears small or user explicitly skipped lifecycle"))

    if not tiny and any(task in tasks for task in ("review", "bug", "refactor", "feature", "ci-sonar", "qa", "security", "dependency")) and not aidlc_only:
        selected.append(FeatureDecision("Review Lens", "check behavior risk, validation gaps, duplication, scope, and safeguards"))
        workflow.append("review")
        commands.append(f'{command_prefix} intent "use review"')
        load.extend(["GUARDRAILS.md relevant sections", "context/guardrail-layers.md relevant layer", "context/review-lenses.md when review is broad"])
    else:
        skipped.append(FeatureDecision("Review Lens", "not needed for AIDLC-only or tiny low-risk work"))

    if review_plan and not aidlc_only:
        selected.append(FeatureDecision("Navigator-Led Review", f"default scope: {review_plan['default']}"))
        if "review" not in workflow:
            workflow.append("review")
        commands.append(review_plan["command"])
        load.extend(["exact diff for selected review scope", "nearby functions and tests for review findings"])
        avoid.extend(["asking the user to memorize review flags", "applying review fixes without approval"])

    dependency_vulnerability = vulnerability_needed and any(term in goal.lower() for term in ("dependency", "package", "npm audit", "pip-audit", "cve", "ghsa", "dependency-check"))
    if (any(risk == "dependency" for risk in risks) or dependency_vulnerability) and not aidlc_only:
        selected.append(FeatureDecision("Dependency Gate", "package, dependency, library, or upgrade signal detected"))
        workflow.append("dependency_review")
        commands.append(f'{command_prefix} intent "use dependency gate"')
        load.append("DEPENDENCY-GATE.md")
    else:
        skipped.append(FeatureDecision("Dependency Gate", "no dependency/package signal detected"))

    if ("security" in tasks or any(risk in risks for risk in ("auth/security", "secrets", "security", "secrets/token", "vulnerability scan"))) and not aidlc_only:
        selected.append(FeatureDecision("Security Review", "auth, secrets, permissions, or trust-boundary signal detected"))
        workflow.append("security_review")
        commands.append(f'{command_prefix} intent "use security review"')
        load.extend(["aidlc/extensions/security-baseline.md", "exact auth/security policy or code"])
    else:
        skipped.append(FeatureDecision("Security Review", "no auth, secrets, permission, or security signal detected"))

    if ci_sonar_needed:
        selected.append(FeatureDecision("CI/Sonar Intelligence", "pipeline, Sonar, lint, test, static-analysis, or quality-gate signal detected"))
        workflow.append("ci_sonar_intelligence")
        load.extend(["exact CI/Sonar output if provided", "rule IDs, file paths, line numbers, commands, and first relevant failures"])
        avoid.extend(["pasting or reloading huge CI/Sonar logs when a local file summary would be cheaper"])
    else:
        skipped.append(FeatureDecision("CI/Sonar Intelligence", "no pipeline, Sonar, static-analysis, lint, test, or quality-gate signal detected"))

    if ci_sonar_needed:
        selected.append(FeatureDecision("QA / CI-Sonar Lens", "validation, pipeline, or scanner signal detected"))
        workflow.append("qa_review")
        commands.append(f"{command_prefix} route ci-sonar")
        load.extend(["templates/validation-handoff.md", "templates/tool-summary.md", "exact CI/Sonar rule, job, file, line, and command evidence"])
    elif "qa" in tasks:
        selected.append(FeatureDecision("Focused QA Lens", "validation behavior needs a targeted regression and preservation check"))
        workflow.append("qa_review")
        load.extend(["existing nearby tests and fixtures", "focused validation expectations"])
    else:
        skipped.append(FeatureDecision("QA / CI-Sonar Lens", "no validation, scanner, or pipeline signal detected"))

    if test_precision_needed and not aidlc_only:
        selected.append(FeatureDecision("Test Precision Planner", "unit, regression, coverage, or post-change validation signal detected"))
        if "test_precision" not in workflow:
            workflow.append("test_precision")
        test_command_parts = [f"{command_prefix} test plan", f"--root {core.quoted(root.as_posix())}", f"--goal {core.quoted(goal)}"]
        if changed:
            test_command_parts.extend(f"--changed {path}" for path in changed[:5])
        else:
            test_command_parts.append("--changed path/to/file")
        commands.append(" ".join(test_command_parts))
        load.extend(["existing nearby tests and fixtures", "repo test naming conventions", "focused validation expectations"])
    else:
        skipped.append(FeatureDecision("Test Precision Planner", "no unit, regression, coverage, or post-change validation signal detected"))

    if vulnerability_needed and not aidlc_only:
        selected.append(FeatureDecision("Security And Vulnerability Intelligence", "CVE, GHSA, SAST, secret, container, audit, or vulnerability signal detected"))
        workflow.append("vulnerability_review")
        commands.append(f"{command_prefix} vulnerability scan {root_arg(root)}")
        load.extend(["exact vulnerability IDs, package names, versions, severities, scanner names, and affected paths", "templates/vulnerability-summary.md", "templates/vulnerability-remediation.md when the user asks for a fix"])
        avoid.extend(["treating vulnerability findings as generic Sonar code smells", "claiming a vulnerability is fixed without scanner or validation evidence"])
        if vulnerability_evidence:
            avoid.append("claiming vulnerability remediation is complete before exact scanner evidence is provided")
    else:
        skipped.append(FeatureDecision("Security And Vulnerability Intelligence", "no CVE, GHSA, SAST, secret, container, audit, or vulnerability signal detected"))

    scan_approval = scan_approval_prompt(goal, root)
    if scan_approval:
        selected.append(FeatureDecision("Quality Signal Scanner", "scan-like Sonar, lint, quality-gate, or vulnerability request detected"))
        workflow.append("quality_scan_approval")
        load.extend(["exact requested scanner or rule evidence", "project quality tool config when present"])
        avoid.extend(["running Sonar, vulnerability, audit, broad build, or networked scanner commands without explicit yes/no approval"])
    else:
        skipped.append(FeatureDecision("Quality Signal Scanner", "no full scan, local quality precheck, Sonar check, or vulnerability scan request detected"))

    needs_handoff = not skip_handoff and not tiny and any(
        core.keyword_found(goal, word)
        for word in ("handoff", "pr", "release", "reviewer", "approval", "transfer")
    )
    if needs_handoff:
        selected.append(FeatureDecision("Handoff", "review, approval, release, or transfer signal detected"))
        workflow.append("handoff")
        commands.append(f'{command_prefix} intent "use handoff"')
        load.extend(["templates/diff-handoff.md", "templates/validation-handoff.md"])
    else:
        skipped.append(FeatureDecision("Handoff", "no handoff, transfer, release, or approval signal detected"))

    if state["learnings"] and not tiny:
        selected.append(FeatureDecision("Project Learnings", "project learnings exist; use at most relevant curated notes as advisory context only"))
        load.append(".tailtrail/learnings.md only if directly relevant")
    else:
        reason = "tiny task" if tiny else "no learning file found"
        skipped.append(FeatureDecision("Project Learnings", reason))

    if not tiny and graph_learning_index_exists(root, state):
        graph_learning = run_graph_learning(root, changed, tasks, risks)
        graph_learning_matches = graph_learning.get("matches", []) if isinstance(graph_learning, dict) else []
        use_proposal = learning_use_proposal(root, goal, changed, tasks, risks)
        proposal_matches = use_proposal.get("matches", []) if isinstance(use_proposal, dict) else []
        proposal_state = use_proposal.get("state") if isinstance(use_proposal, dict) else None
        if proposal_matches:
            selected.append(FeatureDecision("Graph-Aware Learning", "project-framed V3 learnings passed applicability, privacy, freshness, invalidator, and contradiction gates; explicit use choice is still required"))
            load.append("Learning V3 use proposal only; never raw history or unapproved advice")
            mode = learning_retrieval_mode(goal)
            command = f"{command_prefix} learn retrieve --root {core.quoted(root.as_posix())} --mode {mode} --task-types {core.quoted(','.join(tasks))}"
            if changed:
                command += " " + " ".join(f"--path {core.quoted(path)}" for path in changed[:5])
            tags = normalized_learning_tags(tasks, risks)
            if tags:
                command += f" --tags {core.quoted(','.join(tags))}"
            commands.append(command)
        elif proposal_state == "blocked":
            reasons = [reason for row in (use_proposal.get("blocked", []) if isinstance(use_proposal, dict) else []) if isinstance(row, dict) for reason in row.get("reasons", [])]
            if any("No learning store exists yet" in str(reason) for reason in reasons):
                graph_learning_skip_reason = "no learning store exists yet; V3 learnings accrue automatically from accepted closures"
            else:
                graph_learning_skip_reason = "all applicable V3 learnings were blocked by freshness, invalidator, exclusion, privacy, threshold, or contradiction checks"
            skipped.append(FeatureDecision("Graph-Aware Learning", graph_learning_skip_reason))
        else:
            graph_learning_skip_reason = "no high-value project-framed V3 learning matched; Lite remains quiet"
            skipped.append(FeatureDecision("Graph-Aware Learning", graph_learning_skip_reason))
    else:
        graph_learning_skip_reason = learning_skip_reason(root, tiny, state, graph_learning)
        skipped.append(FeatureDecision("Graph-Aware Learning", graph_learning_skip_reason))

    refresh_awareness = learning_refresh_awareness(root, goal, graph_learning, graph_learning_matches, command_prefix)
    if refresh_awareness:
        selected.append(FeatureDecision("Learning Refresh Awareness", "refresh signal detected; suggest refresh review without changing learning files"))
        commands.append(refresh_awareness["command"])
    else:
        skipped.append(FeatureDecision("Learning Refresh Awareness", "no stale, low-confidence, contradictory, or user-requested refresh signal detected"))

    if harness_hints["hints"]:
        selected.append(FeatureDecision("Approved Meta-Harness Hints", "short productized guidance exists for this workflow; use as advisory planning context only"))
        load.append("approved Meta-Harness hint summary only, not raw harness analysis")
    else:
        skipped.append(FeatureDecision("Approved Meta-Harness Hints", harness_hints["status"]))

    if evaluation_plan["selected"]:
        selected.append(FeatureDecision("Evaluation Harness", "evidence, demo, benchmark, proof, report, or scenario signal detected; use deterministic scenario scoring"))
        commands.extend(evaluation_plan["commands"])
        load.extend(
            [
                "EVALUATION-HARNESS.md relevant section",
                f"benchmarks/evaluation/scenarios/{evaluation_plan['scenario']}/scenario.json",
                f"benchmarks/evaluation/scenarios/{evaluation_plan['scenario']}/artifacts when needed",
                f"benchmarks/evaluation/scenarios/{evaluation_plan['scenario']}/expected when needed",
            ]
        )
        avoid.extend(
            [
                "live model/API calls for Evaluation Harness scenario scoring",
                "claiming scenario scores as live model performance",
                "exact token savings without measured telemetry",
            ]
        )
    else:
        skipped.append(FeatureDecision("Evaluation Harness", evaluation_plan["reason"]))

    if tiny:
        selected.append(FeatureDecision("TailTrail Lean", "tiny low-risk task; keep the workflow minimal"))
        workflow = ["lean"]
        implementation_plan = [
            "Confirm the change is tiny and low risk.",
            "Read the exact target file only.",
            "Make the smallest edit.",
            "Run or name the smallest relevant check if behavior changed.",
        ]
    else:
        if not workflow:
            workflow = ["implementation"]
        elif "implementation" not in workflow:
            # Requirements authority must precede implementation. Other
            # planning/review lenses can follow the implementation stage.
            requirements_index = workflow.index("aidlc_requirements") if "aidlc_requirements" in workflow else -1
            workflow.insert(requirements_index + 1, "implementation")
        if "review" in workflow and ("qa_review" in workflow or "test_precision" in workflow):
            # Review findings are most useful after the focused change and
            # validation evidence exist, so display it as a post-change step.
            workflow.remove("review")
            workflow.append("review")
        implementation_plan = [
            "Review this Navigator plan and edit it if needed.",
            "If Code Graph Mapper is selected as missing, stale, or invalid, approve graph map or refresh before broad source reads.",
            "Inspect exact target files and any graph-suggested callers/tests before implementation.",
            "Apply the smallest maintainable change that preserves safeguards.",
            "Use Test Precision Planner when selected to identify the regression, negative, boundary, and guard-preservation test cases before running commands.",
            "Run or name focused validation tied to the changed behavior.",
            "After user acceptance or reviewer feedback, approve learning capture only if the change produced a reusable repo pattern.",
            "Prepare review or handoff notes when ownership, PR review, or release is involved.",
        ]
        if review_plan:
            implementation_plan.insert(
                -1,
                "After implementation and focused validation, ask approval to review the selected scope before proposing fixes.",
            )

    # Structure discovery is intentionally a planning inventory, not a claim
    # about callers. Do not let graph suggestions bypass typed classification.
    # Debug Start is static orientation only. Even a TailTrail-owned graph
    # helper is still a spawned command, so defer it until the approved Debug
    # orientation stage. Build planning retains the existing bounded helper.
    graph = (
        run_review_graph(root, changed)
        if not debug_planning and needs_graph and changed and target_origin != "repository-discovery"
        else None
    )
    if graph:
        graph_paths = [
            str(path)
            for path in graph.get("suggested_read_order", [])[1:6]
            if str(path) not in set(changed)
        ]
        if graph_paths:
            scope_seeds.extend(
                navigator_scope.seed(path, "fresh-graph", "review-graph-suggested-read")
                for path in graph_paths
            )
            scope_candidates = navigator_scope.candidates_from_seeds(root, scope_seeds, tasks)

    scope_candidates, scope_edges, scope_investigation = navigator_scope.investigate(
        root,
        requirement_query_frame["requirements"],
        scope_candidates,
        ["debug", *tasks] if debug_planning else tasks,
        allow_git_inventory=not debug_planning,
        allow_persistent_cache=graph_mode != "off",
        allow_passive_capture=allow_passive_capture,
    )
    deduplicated_impacted = navigator_scope.project_likely_impacted(scope_candidates)
    scope_evidence = navigator_scope.evidence_document(
        root,
        goal,
        requirement_query_frame["requirements"],
        scope_candidates,
        edges=scope_edges,
        investigation=scope_investigation,
    )
    scope_host_packet = navigator_scope.host_reasoning_packet(scope_evidence)
    scope_quality = navigator_scope.assess_scope_quality(root, goal, tasks, scope_evidence)

    cache_reasons = set(scope_investigation.get("cache", {}).get("reason_codes", []))
    scope_cache_status = str(scope_investigation.get("cache", {}).get("status", "not-checked"))
    ephemeral_scope_resolved = (
        scope_investigation.get("state") == "resolved"
        and "bounded-ephemeral-graph-built" in cache_reasons
    )
    missing_cache_scope_resolved = ephemeral_scope_resolved and scope_cache_status == "missing"
    if missing_cache_scope_resolved:
        commands = [
            command for command in commands
            if " graph map " not in f" {command} " and " graph refresh " not in f" {command} "
        ]
        implementation_plan = [
            step for step in implementation_plan
            if not step.startswith("If Code Graph Mapper is selected as missing")
        ]
        implementation_plan.insert(
            1,
            "Reuse the resolved bounded in-memory relationship evidence; a persistent graph cache is optional for future runs.",
        )

    approval = [
        "Review this plan before implementation.",
        "You can edit selected features, skipped features, impacted files, validation, or commands.",
        "Reply approve to proceed, or send an edited plan.",
    ]

    display_tasks = tasks
    if workflow_classification.workflow_type == "debug-investigation":
        display_tasks = ["debug"]
        workflow = [
            "debug_intake",
            "reproduction_contract",
            "bounded_investigation",
            "correction_proposal",
        ]
        implementation_plan = [
            "Review the classified symptom and missing evidence without editing source.",
            "Draft and separately approve a deterministic reproduction contract.",
            "Map the failing path and record bounded experiments against ranked hypotheses.",
            "Require root-cause proof before proposing a correction.",
            "Keep correction implementation and canonical closure blocked until their required approved stages.",
        ]

    selected_rows = [decision.__dict__ for decision in selected]
    skipped_rows = [decision.__dict__ for decision in skipped]
    if missing_cache_scope_resolved:
        for item in selected_rows:
            if item.get("name") == "Code Graph Mapper":
                item["reason"] = "no fresh shared cache was available; bounded static relationships resolved the implementation owner without persisting a cache"
    if workflow_classification.workflow_type == "debug-investigation":
        known_selected = {str(item.get("name")) for item in selected_rows}
        debug_rows = []
        for name in workflow_classification.selected_features:
            if name not in known_selected:
                debug_rows.append({"name": name, "reason": workflow_classification.reason})
                known_selected.add(name)
        selected_rows = [*debug_rows, *selected_rows]
        skipped_rows.extend(
            {"name": item.split(" until ", 1)[0], "reason": item}
            for item in workflow_classification.conditional_features
        )

    return {
        "goal": goal,
        "requirement_interpretation": resolved_requirement_interpretation,
        "canonical_requirements": canonical_requirements,
        "requirement_query_frame": requirement_query_frame,
        "root": root.as_posix(),
        "target_origin": target_origin,
        "scope_evidence": scope_evidence,
        "scope_host_packet": scope_host_packet,
        "scope_quality": scope_quality,
        "scope_candidates": scope_candidates,
        "task_types": display_tasks,
        "risk_indicators": risks,
        "existing_state": state,
        "recommended_workflow": workflow,
        "registry_workflow": registry_projection,
        "workflow_classification": workflow_classification.__dict__,
        "selected_features": selected_rows,
        "skipped_features": skipped_rows,
        "likely_impacted_files": deduplicated_impacted,
        "load": list(dict.fromkeys(load)),
        "avoid": list(dict.fromkeys(avoid)),
        "suggested_commands": list(dict.fromkeys(commands)),
        "implementation_plan": implementation_plan,
        "approval": approval,
        "scan_approval": scan_approval,
        "cross_repo_reference": cross_repo_plan,
        "graph_cache": graph_cache,
        "bootstrap_snapshot": bootstrap_status,
        "context_strategy": strategy,
        "token_budget": token_budget,
        "graph_learning": graph_learning,
        "graph_learning_skip_reason": graph_learning_skip_reason,
        "learning_approval": approval_for_learnings,
        "learning_use_proposal": use_proposal,
        "learning_refresh_awareness": refresh_awareness,
        "meta_harness_hints": harness_hints,
        "evaluation_harness": evaluation_plan,
        "learning_capture_suggestion": capture_suggestion,
        "review_plan": review_plan,
        "vulnerability_evidence": vulnerability_evidence,
        "review_graph": graph,
        "notes": [
            "Navigator is deterministic and advisory.",
            "It does not edit files or run implementation.",
            "Learnings are advisory only and never override current source, CI, scanner, policy, guardrails, or explicit user direction.",
            "It must ask before running Sonar, vulnerability, audit, broad build, or other scanner commands.",
            "Learning capture is triggered in the plan after meaningful work but must not write learning files until the user approves capture.",
            "Individual TailTrail features should not auto-trigger outside Navigator.",
        ],
    }



def markdown(report: dict[str, Any], view: str = "full") -> str:
    return navigator_render.markdown(report, view)

def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend the smallest useful TailTrail workflow for a user goal.")
    parser.add_argument("goal", nargs="*", help="User goal or task description.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument("--changed", action="append", default=[], help="Changed or target file path. Repeat for multiple files.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    parser.add_argument("--view", choices=["full", "compact", "commands-only"], default="full", help="Markdown view.")
    parser.add_argument("--command-prefix", default="python3 scripts/tailtrail.py", help="Command prefix to show in suggested commands.")
    args = parser.parse_args()

    goal = " ".join(args.goal).strip()
    if not goal:
        parser.error("goal is required")
    report = decide(goal, args.root.resolve(), args.changed, args.command_prefix)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(markdown(report, args.view), end="")
    return 0


def start_hands_free_slice(root: Path, goal: str, run_id: str) -> str:
    """Initialize a Hands-Free slice. Breaks the goal into the sequential pipeline stages.
    
    Checks if the goal contains hands-free cue phrases. If detected, sets the 
    active stage to IMPLEMENTATION in the Planning Lock.
    
    Args:
        root: The project root path.
        goal: The user's task goal description.
        run_id: The current run ID.
        
    Returns:
        Status message indicating slice initiation or lack of hands-free cues.
    """
    lowered = goal.lower()
    is_hands_free = any(phrase in lowered for phrase in ("hands-free", "hands free", "end-to-end", "end to end"))
    
    from scripts.pipeline_manager import PipelineManager
    manager = PipelineManager(root, run_id)
    
    if is_hands_free:
        manager.set_stage("IMPLEMENTATION")
        return "Hands-Free slice initiated. Starting with IMPLEMENTATION stage. New badge active."
    
    return "No hands-free cues detected."


def process_handoff(root: Path, run_id: str, from_stage: str, manifest_data: dict[str, Any]) -> str:
    """Process a handoff from one pipeline stage to the next.
    
    Validates the transition using the PipelineJudge and persists the state
    using the PipelineManager.
    
    Args:
        root: The project root path.
        run_id: The current run ID.
        from_stage: The stage being completed (e.g., "IMPLEMENTATION").
        manifest_data: Dictionary containing change_manifest, requirement_pointers, context, and evidence.
    
    Returns:
        A status message indicating the result of the handoff.
    """
    from scripts.pipeline_manager import PipelineManager, HandoffManifest
    from scripts.pipeline_judge import PipelineJudge
    
    manager = PipelineManager(root, run_id)
    judge = PipelineJudge(root, run_id)
    
    # 1. Structure the manifest data for the Drift Gate check.
    # The Drift Gate requires 'requirement_pointers' and 'evidence' to be present.
    evidence = manifest_data.get("evidence", [])
    requirement_pointers = manifest_data.get("requirement_pointers", [])
    
    # Build the structured evidence dict expected by the Judge
    structured_evidence = {
        "requirement_pointers": requirement_pointers,
        "change_manifest": manifest_data.get("change_manifest", []),
        "context": manifest_data.get("context", ""),
        "evidence": evidence
    }
    
    # 1. Determine the next stage in the pipeline sequence.
    # Stage sequence: IMPLEMENTATION -> TESTING -> INFRA
    stage_sequence = ["IMPLEMENTATION", "TESTING", "INFRA"]
    from_idx = stage_sequence.index(from_stage) if from_stage in stage_sequence else -1
    to_stage = stage_sequence[from_idx + 1] if from_idx >= 0 and from_idx + 1 < len(stage_sequence) else from_stage

    # 2. Verify the stage transition using the Judge
    # This will automatically check the Drift Gate if moving from TESTING to INFRA.
    allowed, error = judge.verify_stage_transition(from_stage, to_stage, structured_evidence)
    if not allowed:
        return f"Stage transition blocked: {error}"
    
    # 3. Persist the transition and advance the stage using the Manager
    manifest = HandoffManifest(
        from_stage=from_stage,
        to_stage=manager.get_current_stage(),
        change_manifest=manifest_data.get("change_manifest", []),
        requirement_pointers=manifest_data.get("requirement_pointers", []),
        context=manifest_data.get("context", ""),
        evidence=manifest_data.get("evidence", [])
    )
    
    next_stage = manager.complete_stage(from_stage, manifest)
    
    if next_stage:
        return f"Slicing successful. Transitioned to {next_stage}. New badge active."
    else:
        return "Pipeline complete. All stages verified."

if __name__ == "__main__":
    raise SystemExit(main())
