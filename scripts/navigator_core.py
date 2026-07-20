#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FeatureDecision:
    name: str
    reason: str


RISK_KEYWORDS = {
    "auth": "auth/security",
    "authorization": "auth/security",
    "permission": "auth/security",
    "secret": "secrets",
    "password": "secrets",
    "token": "secrets/token",
    "security": "security",
    "dependency": "dependency",
    "package": "dependency",
    "library": "dependency",
    "upgrade": "dependency",
    "migration": "data migration",
    "schema": "data shape",
    "production": "production",
    "release": "release",
    "sonar": "ci/sonar",
    "sonarqube": "ci/sonar",
    "sonarcloud": "ci/sonar",
    "ci": "ci/sonar",
    "pipeline": "ci/sonar",
    "quality gate": "ci/sonar",
    "vulnerability": "vulnerability scan",
    "vulnerabilities": "vulnerability scan",
    "vuln": "vulnerability scan",
    "cve": "vulnerability scan",
    "ghsa": "vulnerability scan",
    "sast": "vulnerability scan",
    "secret leak": "vulnerability scan",
    "container scan": "vulnerability scan",
    "image scan": "vulnerability scan",
    "trivy": "vulnerability scan",
    "snyk": "vulnerability scan",
    "semgrep": "vulnerability scan",
    "codeql": "vulnerability scan",
    "fortify": "vulnerability scan",
    "checkmarx": "vulnerability scan",
    "veracode": "vulnerability scan",
    "gitleaks": "vulnerability scan",
    "dependency-check": "vulnerability scan",
    "dependency audit": "vulnerability scan",
    "multi-team": "multi-team",
    "regulated": "regulated",
    "compliance": "regulated",
}

TASK_KEYWORDS = {
    "bug": "bug",
    "fix": "bug",
    "refactor": "refactor",
    "review": "review",
    "diff": "review",
    "pr": "review",
    "feature": "feature",
    "add": "feature",
    "implement": "implementation",
    "endpoint": "feature",
    "api": "feature",
    "test": "qa",
    "tests": "qa",
    "unit test": "qa",
    "unit tests": "qa",
    "regression": "qa",
    "coverage": "qa",
    "test coverage": "qa",
    "validation": "qa",
    "handoff": "handoff",
    "release": "release",
    "sonar": "ci-sonar",
    "sonarqube": "ci-sonar",
    "sonarcloud": "ci-sonar",
    "ci": "ci-sonar",
    "quality gate": "ci-sonar",
    "lint": "qa",
    "scanner": "qa",
    "scan": "qa",
    "vulnerability": "security",
    "vulnerabilities": "security",
    "vuln": "security",
    "cve": "security",
    "ghsa": "security",
    "sast": "security",
    "secret leak": "security",
    "container scan": "security",
    "image scan": "security",
    "trivy": "security",
    "snyk": "security",
    "semgrep": "security",
    "codeql": "security",
    "fortify": "security",
    "checkmarx": "security",
    "veracode": "security",
    "gitleaks": "security",
    "dependency-check": "security",
    "dependency": "dependency",
    "package": "dependency",
    "security": "security",
    "auth": "security",
}

TINY_KEYWORDS = ("typo", "comment", "rename", "readme", "docs only", "documentation only")

CI_SONAR_TERMS = (
    "sonar",
    "sonarqube",
    "sonarcloud",
    "sonar-scanner",
    "quality gate",
    "pipeline",
    "build failed",
    "test failed",
    "ci failed",
    "lint failed",
    "static analysis",
    "file:line",
)

VULNERABILITY_TERMS = (
    "cve",
    "ghsa",
    "vulnerability",
    "vulnerabilities",
    "vuln",
    "sast",
    "secret leak",
    "container scan",
    "image scan",
    "trivy",
    "snyk",
    "npm audit",
    "pip-audit",
    "dependency-check",
    "gitleaks",
    "codeql",
    "fortify",
    "checkmarx",
    "veracode",
    "semgrep",
    "bandit",
    "checkov",
    "tfsec",
)

TEST_PRECISION_TERMS = (
    "add test",
    "add tests",
    "add unit test",
    "add unit tests",
    "unit test",
    "unit tests",
    "regression test",
    "regression tests",
    "test coverage",
    "coverage",
    "test case",
    "test cases",
    "focused test",
    "focused tests",
    "after dev",
    "after development",
    "post-change validation",
    "post change validation",
    "validation confidence",
    "before pr",
    "before raising pr",
    "before merge",
)

TEST_ADDITION_TERMS = (
    "add test",
    "add tests",
    "add unit test",
    "add unit tests",
    "add regression test",
    "add regression tests",
    "add focused test",
    "add focused tests",
    "add focused unit test",
    "add focused unit tests",
    "add validation test",
    "add validation tests",
    "add focused validation",
    "add validation coverage",
    "add test coverage",
)

CROSS_REPO_REFERENCE_TERMS = (
    "cross-repo",
    "cross repo",
    "reference:",
    "reference repo",
    "reference repository",
    "target:",
    "other repo",
    "other repository",
    "sibling repo",
    "sibling repository",
    "use repo",
    "use service",
    "as reference",
    "take reference",
    "same pattern",
    "match pattern",
    "target repo",
)

REJECTION_TERMS = (
    "reject",
    "rejected",
    "rejection",
    "not accepted",
    "did not accept",
    "didn't accept",
    "not liked",
    "did not like",
    "didn't like",
    "bad suggestion",
    "wrong suggestion",
)

REVISION_TERMS = (
    "revise",
    "revised",
    "revision",
    "changed the plan",
    "changed approach",
    "different approach",
    "edit plan",
)

REPO_OVERVIEW_TERMS = (
    "tell me important features",
    "important features of this repo",
    "important features in this repo",
    "what does this repo do",
    "what this repo does",
    "summarize this repo",
    "repo overview",
    "repository overview",
    "project overview",
    "explain this repo",
    "explain this repository",
    "what are the main features",
    "main features of this repo",
    "key features of this repo",
    "important modules",
    "understand this repo",
    "walk me through this repo",
)

REVIEW_INTENT_TERMS = (
    "review my code",
    "review my changes",
    "review the code",
    "review code",
    "code review",
    "review this pr",
    "review pr",
    "review this branch",
    "check this pr",
    "check for bugs",
    "quality review",
    "security review",
    "review after",
    "review it after",
    "after implementation",
    "before pr",
    "before raising pr",
)

FULL_REVIEW_TERMS = (
    "full repo review",
    "full repository review",
    "review entire repo",
    "review whole repo",
    "full code review",
    "architecture review",
    "broad review",
)

BRANCH_REVIEW_TERMS = (
    "branch against",
    "against main",
    "against master",
    "against develop",
    "before pr",
    "before raising pr",
    "current branch",
    "this branch",
)

PATH_REVIEW_TERMS = (
    "this folder",
    "this directory",
    "this module",
    "under ",
    "--dir",
)


def is_repo_overview_request(goal: str) -> bool:
    lowered = goal.lower()
    return any(term in lowered for term in REPO_OVERVIEW_TERMS)


def review_requested(goal: str, tasks: list[str] | None = None) -> bool:
    lowered = goal.lower()
    return "review" in (tasks or []) or any(term in lowered for term in REVIEW_INTENT_TERMS)


def post_implementation_review_requested(goal: str) -> bool:
    lowered = goal.lower()
    return any(term in lowered for term in ("review after", "review it after", "after implementation", "then review", "and review"))


def full_review_requested(goal: str) -> bool:
    lowered = goal.lower()
    return any(term in lowered for term in FULL_REVIEW_TERMS)


def branch_review_requested(goal: str) -> bool:
    lowered = goal.lower()
    return any(term in lowered for term in BRANCH_REVIEW_TERMS)


def path_review_requested(goal: str) -> bool:
    lowered = goal.lower()
    return any(term in lowered for term in PATH_REVIEW_TERMS)


def feature_signal_is_test_only(goal: str) -> bool:
    lowered = goal.lower()
    if not any(term in lowered for term in TEST_ADDITION_TERMS):
        return False
    non_test_feature_terms = ("feature", "implement", "endpoint", "api", "workflow", "service", "screen", "page")
    return not any(term in lowered for term in non_test_feature_terms)


def task_types(goal: str) -> list[str]:
    if is_repo_overview_request(goal):
        return ["repo-overview"]
    lowered = goal.lower()
    found = []
    for word, task in TASK_KEYWORDS.items():
        if word == "add" and task == "feature" and feature_signal_is_test_only(goal):
            continue
        if word in lowered and task not in found:
            found.append(task)
    return found or ["implementation"]


def risk_indicators(goal: str, changed: list[str]) -> list[str]:
    lowered = goal.lower()
    risks = {label for word, label in RISK_KEYWORDS.items() if word in lowered}
    path_text = " ".join(changed).lower()
    for word, label in RISK_KEYWORDS.items():
        if word in path_text:
            risks.add(label)
    if len(changed) > 3:
        risks.add("multi-file")
    return sorted(risks)


def is_tiny(goal: str, risks: list[str], changed: list[str]) -> bool:
    lowered = goal.lower()
    return bool(any(word in lowered for word in TINY_KEYWORDS) and not risks and len(changed) <= 1)


def has_override(goal: str, phrase: str) -> bool:
    return phrase in goal.lower()


def term_found(goal: str, terms: tuple[str, ...]) -> bool:
    lowered = goal.lower()
    return any(term in lowered for term in terms)


def ci_sonar_requested(goal: str, tasks: list[str], risks: list[str]) -> bool:
    return "ci-sonar" in tasks or "ci/sonar" in risks or term_found(goal, CI_SONAR_TERMS)


def vulnerability_requested(goal: str, risks: list[str]) -> bool:
    return "vulnerability scan" in risks or term_found(goal, VULNERABILITY_TERMS)


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


def test_precision_requested(goal: str, tasks: list[str], risks: list[str], changed: list[str]) -> bool:
    lowered = goal.lower()
    if any(term in lowered for term in TEST_PRECISION_TERMS):
        return True
    if "qa" in tasks and any(task in tasks for task in ("bug", "feature", "implementation", "refactor", "review")):
        return True
    if "ci/sonar" in risks and any(term in lowered for term in ("fix", "resolve", "remediate", "change")):
        return True
    return bool(changed and any(term in lowered for term in ("test", "validate", "validation")))


def heavy_graph_candidate(goal: str, tasks: list[str], risks: list[str]) -> bool:
    if any(task in tasks for task in ("ci-sonar", "qa", "review", "dependency", "security")):
        return True
    if any(risk in risks for risk in ("ci/sonar", "vulnerability scan", "dependency", "multi-file", "production", "regulated")):
        return True
    return any(term in goal.lower() for term in ("heavy read", "full code scan", "before pr", "broad review"))


def quoted(value: str) -> str:
    return json.dumps(value)


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


def cross_repo_reference_plan(goal: str, root: Path, command_prefix: str) -> dict[str, object] | None:
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


def capture_mode(goal: str) -> str:
    lowered = goal.lower()
    if any(term in lowered for term in REJECTION_TERMS):
        return "rejected"
    if any(term in lowered for term in REVISION_TERMS):
        return "revised"
    return "accepted"


def normalized_learning_tags(tasks: list[str], risks: list[str]) -> list[str]:
    tags = tasks + [risk.replace("/", "-").replace(" ", "-") for risk in risks]
    return sorted(dict.fromkeys(tag for tag in tags if tag))
