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
import navigator_render
import prompt_profile
import token_budget_coach


ROOT = Path(__file__).resolve().parents[1]
# Reuse the interpreter that launched TailTrail. This keeps nested helper calls
# working for Windows `py -3` installs as well as Unix `python3` installs.
PYTHON = sys.executable


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
            "command": f"{command_prefix} bootstrap snapshot --root {quoted(root.as_posix())} --write-result",
            "recommended_action": "Continue with normal focused discovery.",
        }
    try:
        status = module.snapshot_status(root)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {
            "status": "unavailable",
            "reason": "bootstrap snapshot status could not be computed",
            "command": f"{command_prefix} bootstrap snapshot --root {quoted(root.as_posix())} --write-result",
            "recommended_action": "Continue with normal focused discovery.",
        }
    action = "reuse" if status.get("status") == "fresh" else "create_or_refresh"
    command_action = "refresh" if status.get("exists") else "snapshot"
    command = f"{command_prefix} bootstrap {command_action} --root {quoted(root.as_posix())}"
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
    result = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True, capture_output=True, check=False)
    if untracked.returncode == 0:
        files.extend(line.strip() for line in untracked.stdout.splitlines() if line.strip())
    return sorted(dict.fromkeys(files))


def existing_state(root: Path) -> dict[str, bool]:
    return {
        "aidlc_docs": (root / "aidlc-docs").exists(),
        "learnings": (root / ".tailtrail" / "learnings.md").exists(),
        "learning_index": (root / ".tailtrail" / "learning-index.md").exists(),
        "installed_pack_manifest": any(root.glob("**/.tailtrail-install.json")),
        "tailtrail_policy": (root / "tailtrail-policy.md").exists(),
        "code_graph_cache": graph_cache_candidates(root)[0].exists() or graph_cache_candidates(root)[1].exists(),
        "shared_code_graph_cache": graph_cache_candidates(root)[0].exists(),
    }


def run_review_graph(root: Path, changed: list[str]) -> dict[str, Any] | None:
    if not changed:
        return None
    command = [PYTHON, (ROOT / "scripts" / "review-graph.py").as_posix(), "--root", root.as_posix(), "--format", "json"]
    for item in changed:
        command.extend(["--changed", item])
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def run_graph_learning(root: Path, changed: list[str], tasks: list[str], risks: list[str]) -> dict[str, Any] | None:
    index_exists = (root / ".tailtrail" / "learning-index.md").exists() or (root / ".tailtrail" / "graph-learning-index.json").exists()
    if not index_exists:
        return None
    tags = sorted(set(tasks + [risk.replace("/", "-").replace(" ", "-") for risk in risks]))
    command = [
        PYTHON,
        (ROOT / "scripts" / "graph-learning.py").as_posix(),
        "search",
        "--root",
        root.as_posix(),
        "--format",
        "json",
        "--limit",
        "3",
    ]
    for item in changed[:5]:
        command.extend(["--changed", item])
    if tags:
        command.extend(["--tags", ",".join(tags)])
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return None
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def graph_learning_index_exists(root: Path, state: dict[str, bool]) -> bool:
    return state["learning_index"] or (root / ".tailtrail" / "graph-learning-index.json").exists()


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


def quoted(value: str) -> str:
    return json.dumps(value)


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
    return f"--root {quoted(root.as_posix())}"


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
    command = f"{command_prefix} reference --target {quoted(target)} --reference "
    if reference:
        command += f"{quoted(reference)} --goal {quoted(goal)}"
    else:
        command += f"{quoted('/path/to/reference-repo')} --goal {quoted(goal)}"
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
    root_arg = quoted(root.as_posix())
    summary = goal[:140] if goal else "REPLACE_WITH_SHORT_TASK_SUMMARY"
    candidate = "REPLACE_WITH_REUSABLE_PATTERN_OR_DECISION"
    reason = "REPLACE_WITH_EXPLICIT_REASON"
    parts = [
        "python3",
        quoted((ROOT / "hooks" / "learning-capture-hook.py").as_posix()),
        quoted(summary),
        "--root",
        root_arg,
    ]
    if tags:
        parts.extend(["--tags", quoted(tags)])
    parts.extend(["--candidate", quoted(candidate)])
    if mode == "accepted":
        parts.extend(["--acceptance", "accepted", "--validation-outcome", "REPLACE_WITH_pass_or_fail_or_not_run"])
    else:
        parts.extend(["--acceptance", mode, "--reason", quoted(reason), "--validation-outcome", "REPLACE_WITH_pass_or_fail_or_not_run"])
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
        "command": f"{command_prefix} learn refresh recommend --root {quoted(root.as_posix())}",
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


def choose_graph_cache_path(root: Path) -> tuple[Path, str]:
    shared, local = graph_cache_candidates(root)
    if shared.exists():
        return shared, "shared"
    return local, "local"


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
            "top matching graph-aware learnings only when surfaced",
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
            f"{command_prefix} receipt capture --root {quoted(root.as_posix())} --task {quoted(goal[:120] or 'task')} "
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


def decide(goal: str, root: Path, changed_args: list[str], command_prefix: str) -> dict[str, Any]:
    changed = changed_args or git_changed(root)
    tasks = core.task_types(goal)
    risks = core.risk_indicators(goal, changed)
    tiny = core.is_tiny(goal, risks, changed)
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
                "Offer Code Graph Mapper as an approved deeper discovery step when a reusable graph cache is useful.",
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
                "It does not edit files, run implementation, record learnings, run scanners, or create graph cache files by itself.",
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
    skip_graph = core.has_override(goal, "skip review graph")
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
    graph_cache = graph_cache_status(root, changed, goal, tasks, risks)
    strategy = context_strategy(goal, root, changed, tasks, risks, graph_cache, command_prefix)
    token_budget = token_budget_coach.estimate_payload(root, goal, changed)
    graph_learning = None
    graph_learning_matches: list[dict[str, Any]] = []
    graph_learning_skip_reason = ""
    approval_for_learnings = None
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
        not tiny
        and any(
            task in tasks
            for task in ("bug", "feature", "implementation", "refactor", "review", "ci-sonar", "qa", "security", "dependency", "release")
        ),
        command_prefix,
    )

    needs_graph = (
        not tiny
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
                commands.append(f"{command_prefix} graph refresh {root_arg(root)} --changed path/to/file")
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
                commands.append(f"{command_prefix} graph map {root_arg(root)} --changed path/to/file")
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
        workflow.append("aidlc")
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

    if ci_sonar_needed or "qa" in tasks:
        selected.append(FeatureDecision("QA / CI-Sonar Lens", "validation, pipeline, or scanner signal detected"))
        workflow.append("qa_review")
        commands.append(f"{command_prefix} route ci-sonar")
        load.extend(["templates/validation-handoff.md", "templates/tool-summary.md", "exact CI/Sonar rule, job, file, line, and command evidence"])
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

    needs_handoff = not skip_handoff and not tiny and any(word in goal.lower() for word in ("handoff", "pr", "release", "reviewer", "approval", "transfer"))
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
        if graph_learning_matches:
            selected.append(FeatureDecision("Graph-Aware Learning", "matching curated learnings found for the current tags, files, or graph scope; user must choose use, ignore, or edit"))
            load.append(".tailtrail/graph-learning-index.json or .tailtrail/learning-index.md metadata only")
            approval_for_learnings = learning_approval(graph_learning_matches)
            commands.append(f"{command_prefix} learn graph search --root {core.quoted(root.as_posix())} " + (" ".join(f"--changed {path}" for path in changed[:5]) if changed else "--tags " + ",".join(core.normalized_learning_tags(tasks, risks)[:3])))
        else:
            graph_learning_skip_reason = learning_skip_reason(root, tiny, state, graph_learning)
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
            # The workflow label is an execution path, not a list of planning
            # lenses. A fix must visibly begin with the approved implementation.
            workflow.insert(0, "implementation")
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

    graph = run_review_graph(root, changed) if needs_graph and changed else None
    impacted = []
    if graph and graph.get("changed"):
        impacted.extend({"path": path, "reason": "changed file"} for path in graph.get("changed", []))
        for path in graph.get("suggested_read_order", [])[1:6]:
            impacted.append({"path": path, "reason": "suggested by Code Review Graph Lite"})
    else:
        impacted.extend({"path": path, "reason": "provided or detected changed file"} for path in changed[:8])

    approval = [
        "Review this plan before implementation.",
        "You can edit selected features, skipped features, impacted files, validation, or commands.",
        "Reply approve to proceed, or send an edited plan.",
    ]

    return {
        "goal": goal,
        "root": root.as_posix(),
        "task_types": tasks,
        "risk_indicators": risks,
        "existing_state": state,
        "recommended_workflow": workflow,
        "registry_workflow": registry_projection,
        "selected_features": [decision.__dict__ for decision in selected],
        "skipped_features": [decision.__dict__ for decision in skipped],
        "likely_impacted_files": impacted,
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


if __name__ == "__main__":
    raise SystemExit(main())
