#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class IntentFlow:
    name: str
    title: str
    prompt: str
    load: list[str]
    avoid: list[str]
    run_order: list[str]
    validation: list[str]
    notes: list[str]


FLOWS: dict[str, IntentFlow] = {
    "hello": IntentFlow(
        name="hello",
        title="TailTrail Hello",
        prompt=(
            "Run the TailTrail installation smoke check and show the output. Treat TailTrail casing and the common "
            "`taitrail` typo as TailTrail. Prefer `tailtrail hello` when the launcher is installed; otherwise run "
            "`python3 scripts/tailtrail.py hello` from the TailTrail pack. Do not replace this with a conversational greeting."
        ),
        load=["scripts/tailtrail.py when present", ".tailtrail-install.json when present"],
        avoid=["broad repo scans", "ROADMAP.md", "USER-GUIDE.md", "source files unrelated to installation status"],
        run_order=["run TailTrail hello command", "show install status and TailTrail location", "suggest doctor only if deeper validation is needed"],
        validation=["tailtrail hello or python3 scripts/tailtrail.py hello exits successfully"],
        notes=["Use `TAILTRAIL_QUIET=1` or `--quiet` when a script-friendly output is needed."],
    ),
    "implementation": IntentFlow(
        name="implementation",
        title="TailTrail Implementation",
        prompt=(
            "Use TailTrail. Read the relevant files first, trace important callers or tests, "
            "reuse existing project patterns, avoid new dependencies unless clearly justified, "
            "and make the smallest maintainable change that preserves safeguards."
        ),
        load=["AGENTS.md", "tailtrail-policy.md when present", "GUARDRAILS.md relevant sections for non-trivial or risky work", "context/guardrail-layers.md implementation and code consistency layers for non-trivial or risky work", "skills/tailtrail/SKILL.md when using Codex", "exact relevant source files"],
        avoid=["ROADMAP.md", "DESIGN.md", "all examples", "unrelated lifecycle artifacts"],
        run_order=["understand request", "inspect relevant code", "implement focused change", "run focused validation"],
        validation=["project-specific focused test or check when available"],
        notes=["Use lean mode when the user asks for the smallest useful version."],
    ),
    "delivery": IntentFlow(
        name="delivery",
        title="TailTrail Delivery Flow",
        prompt=(
            "Use TailTrail delivery flow. Start with the smallest useful AIDLC plan, implement with TailTrail's "
            "reuse-first rules, run focused validation, review the final diff, and prepare a handoff when the work "
            "will be reviewed, paused, transferred, or approved."
        ),
        load=["context/flow-catalog.md", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/validation/exactness sections", "context/guardrail-layers.md implementation, code consistency, AIDLC, review, QA / validation, and handoff layers as needed", "AIDLC.md", "active AIDLC stage playbook", "skills/tailtrail/SKILL.md when using Codex", "skills/tailtrail-review/SKILL.md when using Codex", "exact source and final diff"],
        avoid=["all lifecycle artifacts", "all examples", "raw full logs", "unrelated design docs"],
        run_order=["scope the outcome", "AIDLC state and plan", "implementation", "focused validation", "review final diff", "handoff if useful"],
        validation=["python3 scripts/aidlc-check.py --root . when AIDLC docs are present", "project-specific focused test or check"],
        notes=["Use this as the normal larger-feature path. Use plain TailTrail for tiny low-risk edits."],
    ),
    "risk": IntentFlow(
        name="risk",
        title="TailTrail Risk Flow",
        prompt=(
            "Use TailTrail risk flow. Inspect dependency, security, validation, data integrity, rollout, and ownership "
            "risk before implementation or approval. Prefer existing platform and project capabilities before adding "
            "new dependencies or broad rewrites."
        ),
        load=["context/flow-catalog.md", "context/review-lenses.md", "tailtrail-policy.md when present", "GUARDRAILS.md risk/validation/exactness sections", "context/guardrail-layers.md dependency, QA / validation, CI / Sonar, release, or token saving layer as needed", "DEPENDENCY-GATE.md", "aidlc/extensions/security-baseline.md", "aidlc/extensions/testing-baseline.md", "exact source, diff, config, dependency, or rollout material"],
        avoid=["all lifecycle artifacts", "broad repo scans", "raw full logs unless diagnosing exact failure"],
        run_order=["identify risk boundary", "inspect exact risky material", "apply dependency/security/testing checks", "name blockers or mitigations", "capture handoff if ownership changes"],
        validation=["focused test or manual check for each accepted risk", "dependency/security review evidence when applicable"],
        notes=["Use this before package changes, auth/data work, production-sensitive edits, and uncertain rollouts."],
    ),
    "review": IntentFlow(
        name="review",
        title="TailTrail Review",
        prompt=(
            "Use TailTrail Review. Check the diff for unnecessary dependencies, duplicate logic, "
            "over-broad rewrites, weakened safeguards, missing focused validation, and behavior risk. "
            "Lead with concrete findings."
        ),
        load=["skills/tailtrail-review/SKILL.md when using Codex", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/validation/exactness/review sections", "context/guardrail-layers.md review and code consistency layers", "context/change-impact.md", "exact diff or changed files"],
        avoid=["broad repo scans", "all examples", "ROADMAP.md", "DESIGN.md"],
        run_order=["inspect diff", "trace risky callers when needed", "report findings by severity", "name validation gaps"],
        validation=["review exact changed files and available test evidence"],
        notes=["Do not create lifecycle docs unless the review discovers a need for them."],
    ),
    "architecture_review": IntentFlow(
        name="architecture_review",
        title="TailTrail Architecture Review",
        prompt=(
            "Use TailTrail architecture review. Check boundaries, data flow, coupling, shared abstractions, migration "
            "paths, blast radius, and whether the change fits existing project architecture before suggesting new "
            "structure."
        ),
        load=["context/review-lenses.md", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/review sections", "context/guardrail-layers.md review and code consistency layers", "context/change-impact.md", "exact diff or changed files", "likely callers and tests"],
        avoid=["style-only commentary", "broad rewrites", "new abstractions without repeated need"],
        run_order=["map changed boundaries", "trace callers/data flow", "find coupling or migration risk", "report concrete findings", "name validation gaps"],
        validation=["architecture-sensitive focused test or caller check when available"],
        notes=["Prefer adapting existing architecture over introducing a new pattern for one change."],
    ),
    "security_review": IntentFlow(
        name="security_review",
        title="TailTrail Security Review",
        prompt=(
            "Use TailTrail security review. Check authentication, authorization, secrets, input handling, escaping, "
            "dependency risk, privacy, auditability, and trust-boundary validation. Do not remove safeguards to make "
            "the code shorter."
        ),
        load=["context/review-lenses.md", "tailtrail-policy.md when present", "GUARDRAILS.md safeguard/exactness/validation sections", "context/guardrail-layers.md review and dependency layers", "aidlc/extensions/security-baseline.md", "DEPENDENCY-GATE.md when dependencies changed", "exact source, diff, config, or policy text"],
        avoid=["lossy summaries for security rules", "broad unrelated source", "generic security advice without exact evidence"],
        run_order=["identify trust boundaries", "inspect exact security-sensitive code", "check dependency/config risk", "report exploitable findings", "name required validation"],
        validation=["security-focused test, config check, or manual verification evidence"],
        notes=["Keep exact text for auth rules, secrets handling, configs, IDs, paths, and policy requirements."],
    ),
    "qa_review": IntentFlow(
        name="qa_review",
        title="TailTrail QA Review",
        prompt=(
            "Use TailTrail QA review. Check user flows, regression paths, automated and manual validation, fixtures, "
            "edge cases, and whether the change has enough evidence to be accepted."
        ),
        load=["context/review-lenses.md", "tailtrail-policy.md when present", "GUARDRAILS.md validation truth and exactness sections", "context/guardrail-layers.md QA / validation layer", "aidlc/extensions/testing-baseline.md", "templates/validation-handoff.md", "exact diff, changed files, or validation output"],
        avoid=["raw full logs unless the failure line matters", "unrelated test suites", "generic test wish lists"],
        run_order=["identify changed behavior", "map regression paths", "inspect validation evidence", "name missing focused checks", "prepare validation handoff if useful"],
        validation=["one focused check for non-trivial logic", "manual path when automation is unavailable"],
        notes=["Use this before merge when behavior changed but confidence is unclear."],
    ),
    "ci_sonar": IntentFlow(
        name="ci_sonar",
        title="TailTrail CI/Sonar Flow",
        prompt=(
            "Use TailTrail CI/Sonar flow. Preserve the exact job, stage, rule ID, severity, file, line, command, "
            "and first relevant failure. Fix the smallest root cause, check nearby shared code when the reported "
            "line may be only a symptom, and name the exact validation needed to prove the issue is resolved."
        ),
        load=["tailtrail-policy.md when present", "GUARDRAILS.md validation truth and exactness sections", "context/guardrail-layers.md CI / Sonar layer", "templates/tool-summary.md", "templates/validation-handoff.md", "exact job, rule, file, line, command, and first relevant failure"],
        avoid=["lossy summaries of scanner evidence", "unrelated pipeline logs", "generated or vendor areas unless policy allows"],
        run_order=["capture exact failing evidence", "identify smallest root cause", "inspect shared helper or nearby repeats when needed", "apply focused fix", "rerun or name exact validation"],
        validation=["rerun the exact CI/Sonar/local command when available", "preserve unresolved failures as exact evidence"],
        notes=["Use this for pipeline quality gates, Sonar findings, static analysis, and CI failure remediation."],
    ),
    "maintainability_review": IntentFlow(
        name="maintainability_review",
        title="TailTrail Maintainability Review",
        prompt=(
            "Use TailTrail maintainability review. Check simplicity, duplication, naming, unnecessary abstractions, "
            "readability, local conventions, and future ownership cost while preserving correctness and safeguards."
        ),
        load=["context/review-lenses.md", "tailtrail-policy.md when present", "GUARDRAILS.md safeguard/review sections", "context/guardrail-layers.md review and code consistency layers", "skills/tailtrail-review/SKILL.md when using Codex", "exact diff or changed files"],
        avoid=["personal style churn", "rewrites without behavior or ownership benefit", "removing validation to reduce lines"],
        run_order=["inspect diff", "compare existing conventions", "find avoidable complexity", "recommend smallest maintainable simplification", "name validation gaps"],
        validation=["focused check confirming behavior still holds after simplification"],
        notes=["Prefer boring explicit code over clever abstractions unless the abstraction removes real duplication."],
    ),
    "dependency_review": IntentFlow(
        name="dependency_review",
        title="TailTrail Dependency Review",
        prompt=(
            "Use TailTrail dependency review. Apply the dependency gate to package additions, upgrades, replacements, "
            "or service/tooling changes. Prefer standard library, platform-native features, framework capabilities, "
            "database/cloud capabilities, and already-installed dependencies."
        ),
        load=["context/review-lenses.md", "tailtrail-policy.md when present", "GUARDRAILS.md dependency/validation/exactness sections", "context/guardrail-layers.md dependency layer", "DEPENDENCY-GATE.md", "dependency manifest snippets", "exact package request, version, or diff"],
        avoid=["broad dependency tree dumps", "unrelated source", "approving packages without ownership/security/license rationale"],
        run_order=["state the problem", "check existing capabilities", "compare ownership risk", "approve/reject", "name required validation"],
        validation=["manifest check", "focused behavior check when dependency is accepted"],
        notes=["Use this for dependency changes; use risk flow when dependency risk is part of a broader production concern."],
    ),
    "dependency": IntentFlow(
        name="dependency",
        title="TailTrail Dependency Gate",
        prompt=(
            "Apply TailTrail's dependency gate before recommending or adding any package. Prefer standard library, "
            "platform-native features, framework capabilities, database/cloud capabilities, and already-installed "
            "dependencies before approving new ownership."
        ),
        load=["tailtrail-policy.md when present", "GUARDRAILS.md dependency/validation/exactness sections", "context/guardrail-layers.md dependency layer", "DEPENDENCY-GATE.md", "dependency manifest snippets", "exact package request or version"],
        avoid=["unrelated source", "all docs", "broad dependency tree dumps"],
        run_order=["state the problem", "check existing capabilities", "compare ownership risk", "approve or reject with rationale"],
        validation=["verify manifest changes and focused tests when a dependency is accepted"],
        notes=["New dependencies need a clear maintenance, security, license, and supply-chain rationale."],
    ),
    "aidlc": IntentFlow(
        name="aidlc",
        title="TailTrail AIDLC",
        prompt=(
            "Use TailTrail AIDLC standard depth unless the task clearly calls for minimal or comprehensive depth. "
            "Create or update aidlc-docs with useful task state, requirements, workflow plan, implementation plan, "
            "validation handoff, and audit notes as needed. Load only the active stage playbook."
        ),
        load=["AIDLC.md", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/uncertainty/approval/validation/exactness sections", "context/guardrail-layers.md AIDLC layer", "aidlc/stages/README.md", "active AIDLC stage playbook", "aidlc-docs/aidlc-state.md when present"],
        avoid=["all lifecycle artifacts", "all templates", "old audit details unless needed"],
        run_order=["detect or resume lifecycle state", "clarify requirements", "plan workflow", "implement approved unit", "update validation and audit notes"],
        validation=["python3 scripts/aidlc-check.py --root ."],
        notes=["Keep lifecycle docs compact. Use comprehensive depth only for high-risk or multi-team work."],
    ),
    "aidlc_review": IntentFlow(
        name="aidlc_review",
        title="TailTrail AIDLC Then Review",
        prompt=(
            "Use TailTrail AIDLC first, then TailTrail Review. Update lifecycle docs only with useful task state, "
            "implement the smallest maintainable change, then review the final diff for dependency risk, duplicate logic, "
            "over-broad rewrites, weakened safeguards, and missing focused validation."
        ),
        load=["AIDLC.md", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/validation/exactness/review sections", "context/guardrail-layers.md AIDLC, implementation, code consistency, review, and QA / validation layers as needed", "active AIDLC stage playbook", "skills/tailtrail-review/SKILL.md when using Codex", "exact source and final diff"],
        avoid=["all lifecycle artifacts", "all examples", "raw full logs", "DESIGN.md unless changing TailTrail design"],
        run_order=["AIDLC state and plan", "implementation", "focused validation", "review final diff", "handoff if useful"],
        validation=["python3 scripts/aidlc-check.py --root .", "project-specific focused test or check"],
        notes=["This is the recommended default for meaningful feature, bug, or refactor work."],
    ),
    "review_aidlc": IntentFlow(
        name="review_aidlc",
        title="TailTrail Review Then AIDLC",
        prompt=(
            "Use TailTrail Review first, then TailTrail AIDLC. Review the current diff, decide what should be kept, "
            "changed, or removed, then update aidlc-docs to reflect the final intended implementation path."
        ),
        load=["skills/tailtrail-review/SKILL.md when using Codex", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/validation/exactness/review sections", "context/guardrail-layers.md review and AIDLC layers", "exact diff", "AIDLC.md", "active AIDLC stage playbook"],
        avoid=["unrelated lifecycle docs", "all templates", "broad repo scans"],
        run_order=["review current diff", "identify required fixes", "update lifecycle state", "apply focused fixes", "validate"],
        validation=["python3 scripts/aidlc-check.py --root .", "project-specific focused test or check"],
        notes=["Use this for messy, inherited, or untrusted changes."],
    ),
    "aidlc_handoff": IntentFlow(
        name="aidlc_handoff",
        title="TailTrail AIDLC Then Handoff",
        prompt=(
            "Use TailTrail AIDLC first, then create a TailTrail handoff. Update lifecycle docs only with useful task "
            "state, requirements, workflow plan, implementation plan, validation handoff, and audit notes as needed. "
            "Then summarize task intent, changed files, reused code, intentionally skipped work, validation run, "
            "validation not run, remaining risk, and next owner or approval."
        ),
        load=["AIDLC.md", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/validation/exactness sections", "context/guardrail-layers.md AIDLC, handoff, and QA / validation layers", "active AIDLC stage playbook", "aidlc/stages/handoff.md", "templates/diff-handoff.md", "templates/validation-handoff.md"],
        avoid=["all lifecycle artifacts", "all templates", "raw full logs", "unrelated stage playbooks"],
        run_order=["AIDLC state and plan", "implementation or lifecycle update", "focused validation", "handoff summary", "next owner or approval"],
        validation=["python3 scripts/aidlc-check.py --root .", "ensure handoff references exact changed files and validation evidence"],
        notes=["Use this when work needs durable lifecycle state plus a transfer package."],
    ),
    "review_handoff": IntentFlow(
        name="review_handoff",
        title="TailTrail Review Then Handoff",
        prompt=(
            "Use TailTrail Review first, then create a TailTrail handoff. Review the final diff for unnecessary "
            "dependencies, duplicate logic, over-broad rewrites, weakened safeguards, missing focused validation, "
            "and behavior risk. Then summarize findings, changed files, validation evidence, remaining risk, and "
            "the next owner or approval."
        ),
        load=["skills/tailtrail-review/SKILL.md when using Codex", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/validation/exactness/review sections", "context/guardrail-layers.md review, handoff, and QA / validation layers", "context/change-impact.md", "exact diff or changed files", "aidlc/stages/handoff.md", "templates/diff-handoff.md"],
        avoid=["broad repo scans", "all examples", "all lifecycle artifacts", "raw full logs"],
        run_order=["inspect final diff", "report review findings", "capture validation evidence", "create handoff", "name next owner or approval"],
        validation=["review exact changed files and available test evidence", "ensure handoff captures unresolved risk"],
        notes=["Use this before review transfer, approval, or a second assistant continuing the work."],
    ),
    "aidlc_review_handoff": IntentFlow(
        name="aidlc_review_handoff",
        title="TailTrail AIDLC, Review, Then Handoff",
        prompt=(
            "Use TailTrail AIDLC first, TailTrail Review second, and TailTrail Handoff last. Update lifecycle docs only "
            "with useful task state, implement the smallest maintainable change, review the final diff for dependency "
            "risk, duplicate logic, over-broad rewrites, weakened safeguards, and missing focused validation, then "
            "create a compact handoff with changed files, validation evidence, skipped work, remaining risk, and next "
            "owner or approval."
        ),
        load=["AIDLC.md", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/validation/exactness/review sections", "context/guardrail-layers.md AIDLC, implementation, code consistency, review, QA / validation, and handoff layers as needed", "active AIDLC stage playbook", "skills/tailtrail-review/SKILL.md when using Codex", "aidlc/stages/handoff.md", "templates/diff-handoff.md", "templates/validation-handoff.md", "exact source and final diff"],
        avoid=["all lifecycle artifacts", "all examples", "raw full logs", "DESIGN.md unless changing TailTrail design"],
        run_order=["AIDLC state and plan", "implementation", "focused validation", "review final diff", "create handoff", "name next owner or approval"],
        validation=["python3 scripts/aidlc-check.py --root .", "project-specific focused test or check", "ensure handoff references validation evidence"],
        notes=["Use this for meaningful work that will be reviewed, paused, transferred, or approved."],
    ),
    "handoff": IntentFlow(
        name="handoff",
        title="TailTrail Handoff",
        prompt=(
            "Create a TailTrail handoff for this work. Summarize task intent, changed files, reused code, intentionally "
            "skipped work, validation run, validation not run, remaining risk, and next owner or approval."
        ),
        load=["tailtrail-policy.md when present", "GUARDRAILS.md evidence/validation/exactness sections", "context/guardrail-layers.md handoff and QA / validation layers", "aidlc/stages/handoff.md", "templates/diff-handoff.md", "templates/validation-handoff.md", "exact changed files or validation output"],
        avoid=["all lifecycle artifacts", "raw full logs", "unrelated stage playbooks"],
        run_order=["summarize work", "summarize validation", "state risk", "name next owner or approval"],
        validation=["ensure handoff references exact changed files and known validation evidence"],
        notes=["Use operations notes when deployment, rollback, monitoring, or support is in scope."],
    ),
    "release": IntentFlow(
        name="release",
        title="TailTrail Release Flow",
        prompt=(
            "Use TailTrail release flow. Prepare the change for approval by summarizing final diff, validation evidence, "
            "dependency decisions, risk, rollback or recovery notes, documentation impact, and the next owner or approval."
        ),
        load=["context/flow-catalog.md", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/validation/exactness sections", "context/guardrail-layers.md release, handoff, and QA / validation layers", "aidlc/stages/handoff.md", "templates/diff-handoff.md", "templates/validation-handoff.md", "templates/operations-notes.md when deployment is in scope", "exact final diff or validation output"],
        avoid=["raw full logs", "unrelated lifecycle artifacts", "new implementation work unless a release blocker is found"],
        run_order=["inspect final diff", "capture validation evidence", "check risk and rollback", "prepare handoff", "name next approval"],
        validation=["ensure release notes reference exact changed files and validation evidence"],
        notes=["This is a release readiness handoff, not a deployment daemon."],
    ),
    "learnings": IntentFlow(
        name="learnings",
        title="TailTrail Project Learnings",
        prompt=(
            "Use TailTrail project learnings. Capture durable project patterns, validation commands, dependency "
            "decisions, common pitfalls, and architecture constraints in `.tailtrail/learnings.md` only when the fact "
            "will help future agents avoid repeated discovery or repeated mistakes."
        ),
        load=["templates/learnings.md", ".tailtrail/learnings.md when present", "exact evidence for the learning"],
        avoid=["chat transcript dumps", "temporary guesses", "stale facts without refresh rules"],
        run_order=["identify durable learning", "verify evidence", "add concise entry", "include refresh condition"],
        validation=["learning references exact source, command, decision, or observed behavior"],
        notes=["Keep learnings short and delete stale entries."],
    ),
    "token": IntentFlow(
        name="token",
        title="TailTrail Token Routing",
        prompt=(
            "Use TailTrail Token Autopilot. Skip routing for tiny low-risk work. For non-trivial, broad, noisy, review, "
            "dependency, AIDLC, or handoff work, route to one smallest safe context slice and keep exact text for source, "
            "diffs, configs, commands, versions, paths, IDs, hashes, stack traces, and security rules."
        ),
        load=["TOKEN-AUTOPILOT.md", "context/TailTrail.map.md", "context/token-router.md when deciding strategy", "context/guardrail-layers.md token saving layer when exactness risk matters"],
        avoid=["loading every TailTrail doc", "raw full logs unless required", "lossy summaries for exact material"],
        run_order=["decide skip or route", "choose one route", "load only selected slice", "preserve exact task material"],
        validation=["python3 scripts/token-auto.py \"<prompt>\" --no-state"],
        notes=["Prefer this when context feels large or repetitive."],
    ),
}


ALIASES: list[tuple[str, str]] = [
    ("hello", r"\b(hello (tailtrail|taitrail)|(tailtrail|taitrail) hello|hi (tailtrail|taitrail)|ping (tailtrail|taitrail))\b"),
    ("delivery", r"\b(delivery flow|ship this feature|feature flow|end-to-end flow)\b"),
    ("risk", r"\b(risk flow|risk review|production risk|high risk|release risk)\b"),
    ("release", r"\b(release flow|release handoff|ready to release|prepare release|approval package)\b"),
    ("architecture_review", r"\b(architecture review|architectural review|review architecture|data flow review)\b"),
    ("security_review", r"\b(security review|secure review|auth review|authorization review|owasp|stride)\b"),
    ("qa_review", r"\b(qa review|test review|validation review|regression review)\b"),
    ("ci_sonar", r"\b(ci sonar|sonar|quality gate|pipeline issue|pipeline failure|ci issue|ci failure|static analysis)\b"),
    ("maintainability_review", r"\b(maintainability review|maintenance review|simplicity review|cleanup review)\b"),
    ("dependency_review", r"\b(dependency review|package review|dependency risk review)\b"),
    ("learnings", r"\b(project learnings|save learning|capture learning|remember this pattern|update learnings)\b"),
    ("aidlc_review_handoff", r"\b(aidlc\s*(and|\+|then)?\s*review\s*(and|\+|then)\s*handoff|full flow\s*(and|\+|with)\s*handoff)\b"),
    ("aidlc_handoff", r"\b(aidlc\s*(and|\+|then)\s*handoff|handoff\s*(after|with)\s*aidlc)\b"),
    ("review_handoff", r"\b(review\s*(and|\+|then)\s*handoff|handoff\s*(after|with)\s*review)\b"),
    ("aidlc_review", r"\b(full flow|aidlc\s*(and|\+|then)\s*review|review\s*(and|\+)\s*aidlc after implementation)\b"),
    ("review_aidlc", r"\b(review\s*(then|first).*\baidlc|stabilize\s*(then|and)\s*document)\b"),
    ("dependency", r"\b(dependency gate|check dependency|new package|add package|install package|deps?)\b"),
    ("review", r"\b(tailtrail review|use review|review this|review diff|code review)\b"),
    ("handoff", r"\b(handoff|hand off|transfer package|closeout)\b"),
    ("token", r"\b(token|save tokens|route context|token router|token autopilot|slice context)\b"),
    ("aidlc", r"\b(aidlc|lifecycle|standard depth|comprehensive depth|minimal depth)\b"),
    ("implementation", r"\b(use tailtrail|tailtrail|implement|fix this|small change|refactor)\b"),
]


def normalize_prompt(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def resolve_intent(value: str) -> str:
    text = normalize_prompt(value)
    if text in FLOWS:
        return text
    for name, pattern in ALIASES:
        if re.search(pattern, text):
            return name
    return "implementation"


def default_override_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    env_path = os.environ.get("TAILTRAIL_INTENT_OVERRIDES")
    if env_path:
        paths.append(Path(env_path))
    paths.extend([
        root / ".tailtrail" / "intent-overrides.json",
        root / "tailtrail" / "intent-overrides.json",
    ])
    return paths


def load_overrides(path: Path | None, root: Path) -> tuple[dict[str, Any], Path | None]:
    paths = [path] if path else default_override_paths(root)
    for candidate in paths:
        if candidate and candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8")), candidate
    return {}, None


def merge_flow(flow: IntentFlow, override: dict[str, Any]) -> IntentFlow:
    updates: dict[str, Any] = {}
    for field in ("title", "prompt", "load", "avoid", "run_order", "validation", "notes"):
        if field in override:
            updates[field] = override[field]
    return replace(flow, **updates)


def apply_overrides(flow: IntentFlow, overrides: dict[str, Any]) -> IntentFlow:
    flow_overrides = overrides.get("flows", {})
    if not isinstance(flow_overrides, dict):
        raise SystemExit("intent override file must contain an object field named 'flows'")
    override = flow_overrides.get(flow.name, {})
    if not override:
        return flow
    if not isinstance(override, dict):
        raise SystemExit(f"intent override for '{flow.name}' must be an object")
    return merge_flow(flow, override)


def markdown(flow: IntentFlow, source: Path | None) -> str:
    lines = [
        f"# {flow.title}",
        "",
        f"- Flow: `{flow.name}`",
        f"- Override source: `{source.as_posix() if source else 'none'}`",
        "",
        "## Expanded Prompt",
        "",
        flow.prompt,
        "",
        "## Run Order",
    ]
    lines.extend(f"- {item}" for item in flow.run_order)
    lines.extend(["", "## Load"])
    lines.extend(f"- {item}" for item in flow.load)
    lines.extend(["", "## Avoid"])
    lines.extend(f"- {item}" for item in flow.avoid)
    lines.extend(["", "## Validation"])
    lines.extend(f"- {item}" for item in flow.validation)
    if flow.notes:
        lines.extend(["", "## Notes"])
        lines.extend(f"- {item}" for item in flow.notes)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Expand short TailTrail intent phrases into full workflow prompts.")
    parser.add_argument("prompt", nargs="*", help="Short user phrase, such as 'use AIDLC and review'.")
    parser.add_argument("--flow", choices=sorted(FLOWS), help="Bypass phrase matching and select a flow directly.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root used to discover override files.")
    parser.add_argument("--overrides", type=Path, help="Explicit intent override JSON file.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    args = parser.parse_args()

    raw_prompt = " ".join(args.prompt)
    flow_name = args.flow or resolve_intent(raw_prompt)
    overrides, override_source = load_overrides(args.overrides, args.root.resolve())
    flow = apply_overrides(FLOWS[flow_name], overrides)

    if args.format == "json":
        payload = asdict(flow)
        payload["override_source"] = override_source.as_posix() if override_source else None
        payload["input"] = raw_prompt
        print(json.dumps(payload, indent=2))
    else:
        print(markdown(flow, override_source), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
