#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
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
            "`taitrail` or `tailtrial` typo as TailTrail. Prefer `tailtrail hello` when the launcher is installed; otherwise run "
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
    "guide": IntentFlow(
        name="guide",
        title="TailTrail Guide",
        prompt=(
            "Answer the user's read-only question from the relevant files. "
            "Do not create a Planning Lock, do not implement, and do not run project commands. "
            "Read-only TailTrail inspection commands (graph, map) may be run to gather facts. "
            "For a repo-overview question, structure the answer in this order: "
            "1) functional idea first — what the system does and who it serves, with a simple text flow diagram and flow lines showing how a request moves through the parts; "
            "2) how it is built — language, frameworks, dependencies, build and test commands; "
            "3) deployment pattern — containers, compose, orchestration, infrastructure-as-code, environments; "
            "4) code map — important files and folders with one line each on what lives there. "
            "If the answer reveals follow-up work, propose it and wait for approval instead of starting it."
        ),
        load=["AGENTS.md", "tailtrail-policy.md when present", "README.md", "requirements.txt or manifest", "infra/ and services/ layout", "bootstrap snapshot status (`tailtrail bootstrap status --root .`)", "exact relevant source files"],
        avoid=["ROADMAP.md", "DESIGN.md", "all examples", "unrelated lifecycle artifacts", "Planning Lock creation", "implementation edits", "project command execution", "bootstrap refresh without explicit approval"],
        run_order=["understand question", "check bootstrap snapshot status and reuse its recorded facts", "inspect relevant code read-only", "run read-only tailtrail graph or map commands when the question needs them", "answer functional idea with flow diagram first", "answer build, tech, and deployment", "answer code map", "propose follow-up work without starting it"],
        validation=["no Planning Lock was created", "no source file was modified", "no project command was run", "answer covers function, flow, build, deployment, and code map in order"],
        notes=["Route here for tell-me/show-me/explain questions with no change verb. A later explicit task still needs its own Start and approval."],
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
    "aidlc_full": IntentFlow(
        name="aidlc_full",
        title="TailTrail Official AI-DLC (Full Mode)",
        prompt=(
            "Use Full AI-DLC mode with the pinned official AWS AI-DLC pack. First verify `tailtrail aidlc official "
            "status --root .` is compatible. For a task, create a new TailTrail Start Planning Lock using "
            "`--aidlc full`; official requirements lead the lifecycle and TailTrail preserves the approved anchor, "
            "evidence, drift controls, and completion record. Do not silently downgrade to Standard mode."
        ),
        load=[".tailtrail/official-aidlc/manifest.json", "AIDLC.md", "tailtrail-policy.md when present", "GUARDRAILS.md evidence/uncertainty/approval/validation/exactness sections", "official AI-DLC Requirements Analysis rule after pack compatibility passes"],
        avoid=["unverified pack files", "arbitrary pack-script execution", "all lifecycle artifacts before an active task exists"],
        run_order=["verify pinned official-pack compatibility", "start a new Full-mode Planning Lock with the user goal", "run official requirements stage", "approve the resulting anchor", "attach/record official lifecycle receipts and TailTrail evidence"],
        validation=["python3 scripts/tailtrail.py aidlc official status --root .", "python3 scripts/tailtrail.py start \"<goal>\" --aidlc full --verbose"],
        notes=["This phrase selects Full-mode readiness only; it cannot create a Planning Lock without a task goal.", "Full mode is blocked rather than downgraded when the official pack is missing or altered."],
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


INTENT_ENVELOPE_SCHEMA_VERSION = "1"
MAX_INTENT_INPUT_LENGTH = 8192
ACTIVE_STATES = ("none", "awaiting-approval", "active", "closure-ready", "detached", "ambiguous")
VAGUE_APPROVAL_PHRASES = {
    "do it",
    "go ahead",
    "looks good",
    "looks good to me",
    "proceed",
    "sounds good",
}
EXPLICIT_APPROVAL_PATTERN = re.compile(
    r"^(?:(?:tailtrail\s+)?approve(?:\s+(?:this|the)\s+plan)?|i\s+approve(?:\s+(?:this|the)\s+plan)?)$",
    re.IGNORECASE,
)


def _explicit_hints(text: str) -> dict[str, Any]:
    normalized = normalize_prompt(text)
    aidlc_match = re.search(r"\baidlc\s+(off|lite|standard|full)\b", normalized)
    if not aidlc_match and re.search(r"\bfull\s+(?:official\s+)?aidlc\b", normalized):
        aidlc = "full"
    else:
        aidlc = aidlc_match.group(1) if aidlc_match else None
    return {
        "aidlc": aidlc,
        "debug": bool(re.search(r"\b(debug|diagnose|root[- ]cause)\b", normalized)),
        "hands_free": bool(re.search(r"\b(hands[- ]free|end[- ]to[- ]end)\b", normalized)),
        "verbose": "--verbose" in normalized or bool(re.search(r"\b(verbose|complete audit detail)\b", normalized)),
        "no_planning_lock_explicit": "--no-planning-lock" in normalized,
    }


def _extract_wrapped_goal(value: str, action: str) -> str | None:
    patterns = {
        "start": (
            r"^(?:tailtrail|taitrail|tailtrial)\s+start\s*(?:[:,\-]\s*|\s+)(.+)$",
            r"^(?:please\s+)?(?:use|using)\s+(?:tailtrail|taitrail|tailtrial)\s*(?:[:,\-]\s*|\s+to\s+)(.+)$",
            r"^(?:please\s+)?(?:tailtrail|taitrail|tailtrial)\s+(?:to\s+)?(.+)$",
            r"^(?:tailtrail|taitrail|tailtrial)\s*[:,\-]\s*(.+)$",
            r"^(?:can|could)\s+(?:tailtrail|taitrail|tailtrial)\s+(?:help\s+me\s+)?(?:to\s+)?(.+)$",
        ),
        "guide": (
            r"^(?:tailtrail|taitrail|tailtrial)\s+guide\s*(?:[:,\-]\s*|\s+)(.+)$",
        ),
        "discuss": (
            r"^(?:tailtrail|taitrail|tailtrial)\s+discuss(?:\s+--question)?\s*(?:[:,\-]\s*|\s+)(.+)$",
        ),
    }
    for pattern in patterns.get(action, ()):
        match = re.match(pattern, value.strip(), re.IGNORECASE | re.DOTALL)
        if match:
            goal = match.group(1).strip()
            if action in {"start", "guide"} and goal.startswith(('"', "'")):
                try:
                    tokens = shlex.split(goal)
                except ValueError:
                    tokens = []
                if tokens:
                    goal = tokens[0]
            elif action in {"start", "guide"}:
                goal = re.split(
                    r"\s+--(?:aidlc|verbose|debug|build|changed|no-planning-lock|intent-feature)\b",
                    goal,
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )[0]
            if len(goal) >= 2 and goal[0] == goal[-1] and goal[0] in {'"', "'"}:
                goal = goal[1:-1]
            return goal.strip()
    return None


def _operation(action: str, goal: str | None, flow: str | None, hints: dict[str, Any]) -> dict[str, Any]:
    names = {
        "hello": "hello",
        "guide": "guide",
        "start": "start",
        "discuss": "planning-discuss",
        "status": "flow-status",
        "approve": "planning-approve",
        "continue": "continue",
        "close": "close",
        "stop": "stop",
        "resume": "resume",
        "ordinary-agent": None,
        "named-flow": "intent-expand",
        "clarify": None,
    }
    arguments: dict[str, Any] = {}
    if goal:
        arguments["goal" if action in {"guide", "start"} else "question"] = goal
    if flow:
        arguments["flow"] = flow
    if action == "resume":
        match = re.search(r"--run-id(?:=|\s+)([A-Za-z0-9][A-Za-z0-9._-]{0,127})", goal or "")
        if match:
            arguments = {"run_id": match.group(1)}
    if action == "start":
        for key in ("aidlc", "debug", "hands_free", "verbose", "no_planning_lock_explicit"):
            if hints.get(key) not in {None, False}:
                arguments[key] = hints[key]
    return {"name": names[action], "arguments": arguments}


def _envelope(
    value: str,
    active_state: str,
    action: str,
    *,
    goal: str | None = None,
    flow: str | None = None,
    confidence: str = "high",
    matched_by: str,
    reason_codes: list[str] | None = None,
    requires_clarification: bool = False,
    explicit_approval_detected: bool = False,
) -> dict[str, Any]:
    hints = _explicit_hints(value)
    authority_class = {
        "hello": "read-only",
        "guide": "read-only",
        "start": "planning-only",
        "discuss": "saved-planning-only",
        "status": "read-only",
        "approve": "controlled-explicit-approval",
        "continue": "approved-run-only",
        "close": "evidence-closure-only",
        "stop": "controlled-explicit-stop",
        "resume": "controlled-exact-resume",
        "ordinary-agent": "none",
        "named-flow": "read-only",
        "clarify": "none",
    }[action]
    return {
        "schema_version": INTENT_ENVELOPE_SCHEMA_VERSION,
        "type": "tailtrail-intent-envelope",
        "input": value,
        "active_state": active_state,
        "action": action,
        "goal": goal,
        "flow": flow,
        "confidence": confidence,
        "matched_by": matched_by,
        "requires_clarification": requires_clarification,
        "reason_codes": reason_codes or [],
        "explicit_hints": hints,
        "operation": _operation(action, goal, flow, hints),
        "authority": {
            "classification": authority_class,
            "approval_inferred": False,
            "explicit_approval_detected": explicit_approval_detected,
            "execution_granted": False,
            "boundary": (
                "Intent resolution is read-only. The recommended operation must enforce its own saved-state, "
                "approval, evidence, and execution boundaries."
            ),
        },
    }


def resolve_request(value: str, *, active_state: str = "none") -> dict[str, Any]:
    """Resolve loose user words to one safe typed TailTrail operation.

    This function never executes the operation and never treats embedded words
    such as approve, deploy, or run as authority. Approval is recognized only
    when the complete normalized utterance is an explicit approval statement.
    """
    if active_state not in ACTIVE_STATES:
        raise ValueError(f"active_state must be one of: {', '.join(ACTIVE_STATES)}")
    if len(value) > MAX_INTENT_INPUT_LENGTH:
        raise ValueError(f"intent input must not exceed {MAX_INTENT_INPUT_LENGTH} characters")
    raw = value.strip()
    normalized = normalize_prompt(raw)
    if not raw:
        return _envelope(
            value, active_state, "clarify", confidence="low", matched_by="empty-input",
            reason_codes=["goal-required"], requires_clarification=True,
        )

    if re.fullmatch(r"(?:(?:tailtrail|taitrail|tailtrial)\s+(?:stop|exit)|(?:stop|exit|leave)\s+(?:tailtrail|taitrail|tailtrial)(?:\s+mode)?|leave\s+(?:tailtrail|taitrail|tailtrial)\s+mode)", normalized):
        return _envelope(value, active_state, "stop", matched_by="explicit-stop", reason_codes=["stop-has-highest-routing-precedence"])

    resume_match = re.fullmatch(r"(?:tailtrail|taitrail|tailtrial)\s+resume\s+--run-id(?:=|\s+)([A-Za-z0-9][A-Za-z0-9._-]{0,127})", normalized)
    if resume_match:
        return _envelope(value, active_state, "resume", goal=raw, matched_by="exact-run-resume", reason_codes=["exact-run-id-required"])
    if re.fullmatch(r"(?:tailtrail|taitrail|tailtrial)\s+resume(?:\s+.*)?", normalized):
        return _envelope(value, active_state, "clarify", confidence="high", matched_by="resume-without-exact-run-id", reason_codes=["exact-run-id-required"], requires_clarification=True)

    if re.search(ALIASES[0][1], normalized):
        return _envelope(value, active_state, "hello", matched_by="hello-alias", reason_codes=["installation-smoke-check"])

    if active_state == "ambiguous":
        return _envelope(
            value, active_state, "clarify", confidence="high", matched_by="ambiguous-active-state",
            reason_codes=["exact-run-id-required"], requires_clarification=True,
        )

    if active_state == "detached":
        start_goal = _extract_wrapped_goal(raw, "start")
        if start_goal:
            return _envelope(value, active_state, "start", goal=start_goal, matched_by="explicit-tailtrail-goal")
        return _envelope(
            value, active_state, "ordinary-agent", confidence="high", matched_by="detached-routing",
            reason_codes=["tailtrail-session-detached"],
        )

    if EXPLICIT_APPROVAL_PATTERN.fullmatch(normalized):
        if active_state != "awaiting-approval":
            return _envelope(
                value, active_state, "clarify", confidence="high", matched_by="explicit-approval-without-eligible-run",
                reason_codes=["awaiting-approval-run-required"], requires_clarification=True,
                explicit_approval_detected=True,
            )
        return _envelope(
            value, active_state, "approve", matched_by="explicit-approval",
            reason_codes=["approval-must-be-revalidated-by-controlled-operation"], explicit_approval_detected=True,
        )

    if normalized in VAGUE_APPROVAL_PHRASES:
        return _envelope(
            value, active_state, "clarify", confidence="high", matched_by="vague-approval-language",
            reason_codes=["approval-not-explicit"], requires_clarification=True,
        )

    exact_actions = (
        ("status", r"^(?:tailtrail\s+)?(?:flow\s+)?status$"),
        ("continue", r"^(?:tailtrail\s+)?(?:continue|next)$"),
        ("close", r"^(?:tailtrail\s+)?close(?:\s+(?:it|run))?$"),
    )
    for action, pattern in exact_actions:
        if re.fullmatch(pattern, normalized):
            if active_state == "none":
                return _envelope(
                    value, active_state, "clarify", confidence="high", matched_by="run-action-without-active-run",
                    reason_codes=["active-run-required"], requires_clarification=True,
                )
            if action == "continue" and active_state == "awaiting-approval":
                return _envelope(
                    value, active_state, "clarify", confidence="high", matched_by="continue-before-approval",
                    reason_codes=["explicit-approval-required"], requires_clarification=True,
                )
            return _envelope(value, active_state, action, matched_by="exact-run-action", reason_codes=["active-run-context"])

    if active_state != "none":
        natural_run_actions = (
            ("status", r"\b(show|what(?:'s| is)|check)\b.*\b(status|progress|state)\b|\bhow is (?:it|the run) going\b"),
            ("continue", r"\b(keep going|continue)(?:\s+(?:it|the run|work))?\b"),
            ("close", r"\b(close|finish|complete)(?:\s+(?:it|the run|this out))\b"),
        )
        for action, pattern in natural_run_actions:
            if re.search(pattern, normalized):
                if action == "continue" and active_state == "awaiting-approval":
                    return _envelope(
                        value, active_state, "clarify", confidence="high", matched_by="continue-before-approval",
                        reason_codes=["explicit-approval-required"], requires_clarification=True,
                    )
                return _envelope(
                    value, active_state, action, confidence="medium", matched_by="active-run-language",
                    reason_codes=["active-run-context"],
                )

    discuss_goal = _extract_wrapped_goal(raw, "discuss")
    if discuss_goal:
        if active_state == "none":
            return _envelope(
                value, active_state, "clarify", confidence="high", matched_by="discussion-without-active-run",
                reason_codes=["active-run-required"], requires_clarification=True,
            )
        return _envelope(value, active_state, "discuss", goal=discuss_goal, matched_by="explicit-discuss")
    if active_state != "none" and re.search(r"\b(why|explain|which files|what scope|what validation)\b", normalized):
        return _envelope(value, active_state, "discuss", goal=raw, matched_by="active-run-question")

    guide_goal = _extract_wrapped_goal(raw, "guide")
    if guide_goal:
        return _envelope(value, active_state, "guide", goal=guide_goal, matched_by="explicit-guide")
    if re.search(r"\b(show me (?:how|an approach)|how should|safest approach|guide me|what approach)\b", normalized):
        return _envelope(value, active_state, "guide", goal=raw, confidence="medium", matched_by="advisory-language")
    if active_state == "none" and is_informational_question(raw):
        return _envelope(value, active_state, "guide", goal=raw, confidence="medium", matched_by="informational-question")

    start_goal = _extract_wrapped_goal(raw, "start")
    if start_goal:
        return _envelope(value, active_state, "start", goal=start_goal, matched_by="explicit-tailtrail-goal")

    flow = resolve_intent(raw)
    if normalized in {"tailtrail", "use tailtrail"}:
        return _envelope(value, active_state, "named-flow", flow="implementation", matched_by="named-flow-alias")
    if flow != "implementation":
        return _envelope(value, active_state, "named-flow", flow=flow, matched_by="named-flow-alias")

    if active_state != "none":
        return _envelope(
            value, active_state, "ordinary-agent", confidence="high", matched_by="non-tailtrail-active-context",
            reason_codes=["attached-run-does-not-own-ordinary-conversation"],
        )

    if re.search(r"\b(fix|add|change|create|debug|diagnose|implement|refactor|reject|remove|replace|update)\b", normalized) or _explicit_hints(raw)["hands_free"]:
        return _envelope(
            value, active_state, "start", goal=raw, confidence="medium", matched_by="task-language",
            reason_codes=["safe-default-is-planning-lock"],
        )

    return _envelope(
        value, active_state, "clarify", confidence="low", matched_by="unclassified-language",
        reason_codes=["material-intent-unclear"], requires_clarification=True,
    )


def intent_markdown(envelope: dict[str, Any]) -> str:
    operation = envelope["operation"]["name"] or "none"
    goal = envelope.get("goal") or "none"
    reasons = ", ".join(envelope.get("reason_codes", [])) or "none"
    return (
        "# TailTrail Intent Resolution\n\n"
        f"- Action: `{envelope['action']}`\n"
        f"- Operation: `{operation}`\n"
        f"- Goal: `{goal}`\n"
        f"- Active state: `{envelope['active_state']}`\n"
        f"- Confidence: `{envelope['confidence']}`\n"
        f"- Requires clarification: `{str(envelope['requires_clarification']).lower()}`\n"
        f"- Reasons: `{reasons}`\n\n"
        f"{envelope['authority']['boundary']}\n"
    )


ALIASES: list[tuple[str, str]] = [
    ("hello", r"\b(hello (tailtrail|taitrail|tailtrial)|(tailtrail|taitrail|tailtrial) hello|hi (tailtrail|taitrail|tailtrial)|ping (tailtrail|taitrail|tailtrial))\b"),
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
    ("aidlc_full", r"\b(full\s+(official\s+)?aidlc|use\s+aidlc\s+full|aidlc\s+full\s+mode)\b"),
    ("aidlc", r"\b(aidlc|lifecycle|standard depth|comprehensive depth|minimal depth)\b"),
    ("implementation", r"\b(use tailtrail|tailtrail|implement|fix this|small change|refactor)\b"),
]


def normalize_prompt(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


TASK_VERBS = r"\b(fix|add|change|create|debug|diagnose|implement|refactor|reject|remove|replace|update)\b"
QUESTION_PATTERN = r"\b(tell me|what are|what is|what's|list|describe|explain|summarize|summarise|show me|overview|which features|what features|code graph|call graph|read order|generate the .* graph|show .* graph)\b"


def is_informational_question(value: str) -> bool:
    """Detect read-only questions that must not become a Planning Lock.

    A change verb or hands-free cue keeps task routing; otherwise tell-me /
    explain-style asks route to guide (answer only, no implementation).
    """
    text = normalize_prompt(value)
    return (
        bool(re.search(QUESTION_PATTERN, text))
        and not re.search(TASK_VERBS, text)
        and not _explicit_hints(value)["hands_free"]
    )


def resolve_intent(value: str) -> str:
    text = normalize_prompt(value)
    if text in FLOWS:
        return text
    if is_informational_question(value):
        return "guide"
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
    parser = argparse.ArgumentParser(description="Expand named TailTrail flows or resolve loose words to a typed intent.")
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Short phrase, or: resolve '<loose user words>'.",
    )
    parser.add_argument("--flow", choices=sorted(FLOWS), help="Bypass phrase matching and select a flow directly.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root used to discover override files.")
    parser.add_argument("--overrides", type=Path, help="Explicit intent override JSON file.")
    parser.add_argument(
        "--active-state",
        choices=ACTIVE_STATES,
        default="none",
        help="Saved TailTrail state used only when resolving a stateful follow-up.",
    )
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    args = parser.parse_args()

    resolve_mode = bool(args.prompt and args.prompt[0].lower() == "resolve")
    raw_prompt = " ".join(args.prompt[1:] if resolve_mode else args.prompt)
    if resolve_mode:
        try:
            envelope = resolve_request(raw_prompt, active_state=args.active_state)
        except ValueError as error:
            parser.error(str(error))
        if args.format == "json":
            print(json.dumps(envelope, indent=2))
        else:
            print(intent_markdown(envelope), end="")
        return 0

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
