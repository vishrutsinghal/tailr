#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

import target_workspace
import start_posture
import requirement_discovery
import architecture_planning
import behaviour_planning
import maintainability_planning
import ui_planning


ROOT = Path(__file__).resolve().parents[1]
NAVIGATOR_PATH = ROOT / "scripts" / "navigator.py"
SPEC = importlib.util.spec_from_file_location("tailtrail_navigator", NAVIGATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("Unable to load scripts/navigator.py")
navigator = importlib.util.module_from_spec(SPEC)
sys.modules["tailtrail_navigator"] = navigator
SPEC.loader.exec_module(navigator)

PLANNING_LOCK_PATH = ROOT / "scripts" / "planning-lock.py"
LOCK_SPEC = importlib.util.spec_from_file_location("tailtrail_planning_lock", PLANNING_LOCK_PATH)
if LOCK_SPEC is None or LOCK_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/planning-lock.py")
planning_lock = importlib.util.module_from_spec(LOCK_SPEC)
sys.modules["tailtrail_planning_lock"] = planning_lock
LOCK_SPEC.loader.exec_module(planning_lock)

BRIDGE_SPEC = importlib.util.spec_from_file_location("tailtrail_official_aidlc_bridge", ROOT / "scripts" / "aidlc-official-bridge.py")
if BRIDGE_SPEC is None or BRIDGE_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/aidlc-official-bridge.py")
official_aidlc_bridge = importlib.util.module_from_spec(BRIDGE_SPEC)
sys.modules["tailtrail_official_aidlc_bridge"] = official_aidlc_bridge
BRIDGE_SPEC.loader.exec_module(official_aidlc_bridge)

WORKFLOW_START_SPEC = importlib.util.spec_from_file_location("tailtrail_workflow_start_integration", ROOT / "scripts" / "workflow_runtime" / "start_integration.py")
if WORKFLOW_START_SPEC is None or WORKFLOW_START_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/workflow_runtime/start_integration.py")
workflow_start_integration = importlib.util.module_from_spec(WORKFLOW_START_SPEC)
sys.modules["tailtrail_workflow_start_integration"] = workflow_start_integration
WORKFLOW_START_SPEC.loader.exec_module(workflow_start_integration)

SPEC_KIT_BRIDGE_SPEC = importlib.util.spec_from_file_location("tailtrail_spec_kit_bridge", ROOT / "scripts" / "spec-kit-bridge.py")
if SPEC_KIT_BRIDGE_SPEC is None or SPEC_KIT_BRIDGE_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/spec-kit-bridge.py")
spec_kit_bridge = importlib.util.module_from_spec(SPEC_KIT_BRIDGE_SPEC)
sys.modules["tailtrail_spec_kit_bridge"] = spec_kit_bridge
SPEC_KIT_BRIDGE_SPEC.loader.exec_module(spec_kit_bridge)

HOST_WORKSPACE_SPEC = importlib.util.spec_from_file_location("tailtrail_host_workspace_adapter", ROOT / "scripts" / "host-workspace-adapter.py")
if HOST_WORKSPACE_SPEC is None or HOST_WORKSPACE_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/host-workspace-adapter.py")
host_workspace_adapter = importlib.util.module_from_spec(HOST_WORKSPACE_SPEC)
sys.modules["tailtrail_host_workspace_adapter"] = host_workspace_adapter
HOST_WORKSPACE_SPEC.loader.exec_module(host_workspace_adapter)

ENTERPRISE_POLICY_SPEC = importlib.util.spec_from_file_location("tailtrail_enterprise_target_policy", ROOT / "scripts" / "enterprise-target-policy.py")
if ENTERPRISE_POLICY_SPEC is None or ENTERPRISE_POLICY_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/enterprise-target-policy.py")
enterprise_target_policy = importlib.util.module_from_spec(ENTERPRISE_POLICY_SPEC)
sys.modules["tailtrail_enterprise_target_policy"] = enterprise_target_policy
ENTERPRISE_POLICY_SPEC.loader.exec_module(enterprise_target_policy)

APPROX_CHARS_PER_TOKEN = 4
LARGE_CONTEXT_FILES = (
    "ROADMAP.md",
    "USER-GUIDE.md",
    "ENTERPRISE-REVIEW.md",
    "DESIGN.md",
    "TOKEN-SLICER.md",
)
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


def display_prose(value: Any) -> str:
    """Normalize host-escaped prose for stable, single-line Markdown display.

    Canonical artifacts retain the original user text. Only host-facing prose
    is normalized, so Windows paths and exact evidence fields are not altered.
    """
    text = re.sub(r"\\(?:r\\n|n|r)", " ", str(value))
    text = " ".join(text.split())
    return text.translate(str.maketrans({"\u2013": "-", "\u2014": "-", "\u2212": "-", "\ufffd": "-"}))

def target_root_from_goal(goal: str) -> str | None:
    """Extract one explicit local target root from user wording.

    URLs and relative document references are deliberately not roots.  A path
    is accepted only when nearby wording says it is where the change belongs;
    this prevents a reference repository or a document path from silently
    becoming the editable project.
    """
    return target_workspace.prompt_candidate(goal)


def resolve_target_root(goal: str, supplied_root: Path | None, host_workspace: Path | None = None, alias: str | None = None, aliases: dict[str, Path] | None = None) -> dict[str, Any]:
    """Resolve the planning root before Navigator discovers any files."""
    return target_workspace.resolve(goal, explicit_root=supplied_root, host_workspace=host_workspace, alias=alias, aliases=aliases)


def target_boundary_report(goal: str, resolution: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    """Return a non-persisted report when the requested target cannot be read."""
    return {
        "goal": goal,
        "root": None,
        "command_prefix": command_prefix,
        "target_root": resolution,
        "target_boundary": True,
        "next_step": "Open the target repository in this host or rerun Start with an accessible --root path.",
    }


def render_target_boundary_report(report: dict[str, Any]) -> str:
    target = report["target_root"]
    requested = str(target["requested"])
    return "\n".join(
        [
            "# TailTrail Start Plan",
            "",
            f"**Goal:** {display_prose(report['goal'])}",
            "",
            "## Target repository boundary",
            "",
            f"- Requested target: `{requested}`",
            f"- Status: **{target['status']}** - {display_prose(target['reason'])}.",
            "- No Planning Lock was created and no repository files, Git state, tests, scanners, or project commands were used.",
            "",
            "## Next step",
            "",
            "- Open that repository in the current host, or rerun with an accessible path:",
            f"  `{report['command_prefix']} start \"your goal\" --root \"{requested}\"`",
            "- If it is a reference-only repository, provide an accessible editable target with `--root` and keep the reference read-only.",
            "",
        ]
    )


def requested_technical_scope(goal: str) -> list[str]:
    """Return user-named delivery areas without claiming repository paths."""
    lowered = goal.lower()
    cues = (
        (("api", "contract"), "API and public contract"),
        (("service", "orchestration"), "service orchestration"),
        (("repository", "model"), "repository and authoritative state model"),
        (("inventory", "reservation", "allocation"), "inventory, allocation, and reservation effects"),
        (("payment", "charge", "refund"), "payment charge/refund idempotency"),
        (("notification", "publish"), "notification ordering and deduplication"),
        (("audit",), "immutable audit evidence"),
        (("unit", "integration", "contract", "behaviour", "behavior"), "unit, integration, contract, and behaviour proof"),
        (("metric", "observability"), "operational metrics and observability"),
        (("ci",), "CI evidence"),
        (("migration", "compatibility"), "migration and compatibility"),
        (("rollout", "rollback"), "rollout and rollback safety"),
        (("terraform", "infrastructure"), "infrastructure boundary: plan only; do not apply"),
    )
    return [label for terms, label in cues if any(term in lowered for term in terms)]


def target_fit_boundary_report(
    goal: str,
    root: Path,
    fit: dict[str, Any],
    command_prefix: str,
    planned: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a non-persisted, target-agnostic plan for a low-confidence workspace."""
    planned = planned or {}
    delivery = planned.get("guided_delivery", {}) if isinstance(planned, dict) else {}
    navigator_plan = planned.get("navigator", {}) if isinstance(planned, dict) else {}
    program = delivery.get("hands_free_program") if isinstance(delivery, dict) else None
    requirements = program.get("feature_requirements", []) if isinstance(program, dict) else navigator_plan.get("requirement_matrix", [])
    return {
        "goal": goal,
        "root": root.as_posix(),
        "command_prefix": command_prefix,
        "target_fit": fit,
        "target_fit_boundary": True,
        "requirements": requirements if isinstance(requirements, list) else [],
        "program": program if isinstance(program, dict) else None,
        "aidlc_mode": planned.get("aidlc_mode", {}) if isinstance(planned, dict) else {},
        "selected_features": delivery.get("selected", []) if isinstance(delivery, dict) else [],
        "technical_scope": requested_technical_scope(goal),
    }


def render_target_fit_boundary_report(report: dict[str, Any]) -> str:
    fit = report["target_fit"]
    root = str(report["root"])
    lines = [
        "# TailTrail Pre-Target Start Plan",
        "",
        f"**Goal:** {display_prose(report['goal'])}",
        "",
        "## Target confirmation",
        "",
        f"- Current workspace: `{root}`",
        f"- Status: **{fit['status']}** - {display_prose(fit['reason'])}.",
        "- TailTrail rejected the discovered file scope, but preserved the target-independent requirements and delivery design below.",
        "- No Planning Lock was created. Full AIDLC, implementation, tests, scanners, and Git changes have not started.",
    ]
    requirements = [item for item in report.get("requirements", []) if isinstance(item, dict)]
    if requirements:
        lines.extend(["", "## Requirement bifurcation", ""])
        for item in requirements:
            lines.append(f"- **{item.get('display_id', 'REQ')}:** {display_prose(item.get('statement', ''))}")
    technical_scope = [str(item) for item in report.get("technical_scope", [])]
    if technical_scope:
        lines.extend(["", "## Intended technical scope", ""])
        lines.extend(f"- {display_prose(item)}" for item in technical_scope)
    aidlc = report.get("aidlc_mode", {})
    if isinstance(aidlc, dict) and aidlc:
        mode = str(aidlc.get("mode", "unknown"))
        route_text = {
            "lite": "After target confirmation, local AIDLC Lite remains the requirement-clarification route; no official lifecycle stage is implied.",
            "off": "After target confirmation, AIDLC remains disabled and the approved Navigator requirement boundary governs implementation.",
            "standard": "After target confirmation, the pinned official Requirements Analysis stage owns questions and approved decisions.",
            "full": "After target confirmation, the pinned official lifecycle owns requirements, design, implementation, build/test, and handoff stages.",
        }.get(mode, "After target confirmation, TailTrail preserves the selected AIDLC authority route.")
        lines.extend([
            "",
            "## AIDLC route",
            "",
            f"- Requested mode: **{display_prose(mode)}**.",
            f"- Preflight state: `{aidlc.get('state', 'unavailable')}`.",
            f"- {route_text}",
            "- Question Orchestrator validates relevance and requirement traceability; TailTrail does not replace the official questionnaire.",
        ])
    features = [item for item in report.get("selected_features", []) if isinstance(item, dict)]
    if features:
        lines.extend(["", "## Selected TailTrail features", "", "| Feature | Use after target confirmation |", "| --- | --- |"])
        for item in features:
            lines.append(f"| {display_prose(item.get('name', 'TailTrail control'))} | {display_prose(item.get('why', 'Selected for this task.'))} |")
    program = report.get("program")
    if isinstance(program, dict):
        lines.extend(["", "## End-to-end delivery program", "", "Proposed dependency order:"])
        for index, stage in enumerate(program.get("dependency_order", []), start=1):
            lines.append(f"{index}. {display_prose(stage)}")
        lines.extend([
            "",
            f"- First active slice: {display_prose(program.get('first_active_slice', 'requirements only'))}",
            f"- Approval gate: {display_prose(program.get('approval_gate', 'target and requirements approval required'))}",
        ])
    candidates = fit.get("discovered_candidates", [])
    if candidates:
        lines.extend(["", "## Rejected workspace matches", ""])
        lines.append("- These paths were not accepted as implementation scope: " + ", ".join(f"`{path}`" for path in candidates) + ".")
    missing_changed = fit.get("missing_changed_paths", [])
    if missing_changed:
        lines.extend(["", "## Invalid explicit paths", ""])
        lines.append("- These `--changed` paths do not exist in the selected repository: " + ", ".join(f"`{path}`" for path in missing_changed) + ".")
    lines.extend([
        "",
        "## Next action",
        "",
        "- Open the application repository and rerun this same Start request there.",
        "- Or append an explicit target to the command you just ran:",
        "  `--root \"D:/absolute/path/to/target-project\"`",
        "- Once the target is confirmed, TailTrail reruns read-only impact mapping there, creates the Planning Lock, and continues through the selected AIDLC route.",
        "",
    ])
    return "\n".join(lines)


def delivery_run_signals(root: Path, run_id: str | None) -> dict[str, Any]:
    if not run_id:
        return {"status": "not-requested", "run_id": None, "correction_cycle": False, "recovery_risk": False, "drift": []}
    if Path(run_id).name != run_id:
        raise ValueError("run_id must be a single local run identifier")
    directory = root / ".tailtrail" / "runs" / run_id
    if not directory.is_dir():
        return {"status": "missing", "run_id": run_id, "correction_cycle": False, "recovery_risk": False, "drift": []}
    feedback = sorted((directory / "feedback").glob("feedback-*.json"))
    checkpoints = sorted((directory / "checkpoints").glob("checkpoint-*.json"))
    drift: list[str] = []
    if checkpoints:
        try:
            checkpoint = json.loads(checkpoints[-1].read_text(encoding="utf-8"))
            drift = sorted({str(item.get("classification")) for item in checkpoint.get("drift", []) if isinstance(item, dict) and item.get("classification") in {"unchanged", "regressed", "new-drift", "needs-decision"}})
        except (OSError, json.JSONDecodeError):
            drift = ["unreadable-checkpoint"]
    recovery_paths = list((directory / "recovery").glob("plan-*.json")) + list((directory / "recovery" / "reconciliation").glob("assessment-*.json"))
    return {
        "status": "found", "run_id": run_id, "correction_cycle": bool(feedback) or bool(drift),
        "recovery_risk": bool(recovery_paths), "drift": drift,
        "evidence": [path.relative_to(root).as_posix() for path in [feedback[-1] if feedback else None, checkpoints[-1] if checkpoints else None, *recovery_paths] if path],
    }


def hands_free_requirements(goal: str) -> list[dict[str, str]]:
    """Turn a broad hands-free goal into an approval-ready, local requirement boundary."""
    lowered = goal.lower()

    # Choose the requested capability before interpreting preservation wording.
    # A programme that says "preserve cancellation" must not become a
    # cancellation programme merely because it also mentions inventory, refunds,
    # notifications, or audit records.
    amendment_cues = (
        "order amendment", "order-amendment", "amend order", "amendment",
        "change quantity", "change the quantity", "change delivery address",
        "delivery address", "order revision", "expected revision",
    )
    if any(cue in lowered for cue in amendment_cues):
        statements = [
            "Define amendment eligibility by fulfilment stage and preserve existing create-order and cancellation behavior.",
            "Maintain one authoritative order revision and reject stale concurrent amendment attempts.",
            "Allow only the approved quantity transition for each fulfilment stage and release only excess reserved inventory.",
            "Allow an authorized post-shipment delivery-address correction only with an audit reason while preserving product and quantity immutability.",
            "Recalculate the amendment amount and issue an additional charge or partial refund exactly once through an idempotent amendment action.",
            "Persist an immutable before/after amendment audit record with actor, reason, and revision identifiers.",
            "Send one customer amendment notification only after all required durable effects succeed.",
            "Update the API contract with explicit amendment success, validation, conflict, forbidden, and transient-failure behavior.",
            "Add focused unit, integration, contract, and behaviour evidence for amendment, concurrency, side-effect ordering, and preserved flows.",
        ]
        if any(word in lowered for word in ("migration", "compatibility", "legacy")):
            statements.append("Preserve compatible legacy order records and provide migration evidence for the revised order model.")
        if any(word in lowered for word in ("rollout", "terraform", "release", "operations", "metrics", "ci")):
            statements.append("Provide operational metrics, CI/reconciliation evidence, and staged rollout/rollback criteria without applying infrastructure in the local demo.")
        return [{"display_id": f"REQ-{index:02d}", "statement": statement} for index, statement in enumerate(statements, start=1)]

    statements: list[str] = []
    if "cancel" in lowered:
        statements.append("Define the cancellation eligibility rule and preserve non-cancellable order behavior.")
    if "stock" in lowered or "inventory" in lowered or "restock" in lowered:
        statements.append("Release inventory exactly once after an eligible cancellation succeeds.")
    if "refund" in lowered or "payment" in lowered:
        statements.append("Issue one refund for an eligible cancellation and preserve payment failure handling.")
    if "notification" in lowered or "notify" in lowered:
        statements.append("Send one cancellation notification only after the required cancellation effects succeed.")
    if "audit" in lowered:
        statements.append("Record an audit event with the cancellation outcome and relevant identifiers.")
    if "api" in lowered or "contract" in lowered or "endpoint" in lowered:
        statements.append("Update the API contract without weakening existing order behavior outside cancellation.")
    if "test" in lowered or "validation" in lowered:
        statements.append("Add focused unit, integration, contract, and behaviour evidence appropriate to the changed paths.")
    if "rollout" in lowered or "terraform" in lowered or "release" in lowered:
        statements.append("Provide rollout, rollback, and infrastructure-impact evidence; do not apply infrastructure in the local demo.")
    if not statements:
        statements = [
            "Break the requested outcome into independently verifiable feature requirements.",
            "Map each approved requirement to code paths, preservation rules, and computational evidence.",
        ]
    return [{"display_id": f"REQ-{index:02d}", "statement": statement} for index, statement in enumerate(statements, start=1)]


def _aidlc_intent(lowered: str) -> str:
    """Classify explicit natural-language AIDLC mode without relying on word order.

    This intentionally recognizes only a mode qualifier next to AIDLC. Generic
    words such as ``complete`` or ``no`` elsewhere in a product request must
    not silently change the lifecycle mode.
    """
    normalized = lowered.replace("ai-dlc", "aidlc")
    if "aidlc" not in normalized:
        return "none"
    if re.search(r"\b(without|skip|disable|no)\s+aidlc\b|\baidlc\s+(off|disabled)\b", normalized):
        return "opt-out"
    if re.search(r"\b(full|official|enterprise)\s+aidlc\b|\baidlc\s+(full|official|enterprise)\b", normalized):
        return "full"
    if re.search(r"\b(standard|medium|normal|regular)\s+aidlc\b|\baidlc\s+(standard|medium|normal|regular)\b", normalized):
        return "standard"
    return "requested"


def aidlc_mode_selection(goal: str, requested: str | None, root: Path, plan: dict[str, Any], manifest: str | None) -> dict[str, Any]:
    """Choose the smallest lifecycle mode from explicit wording and task evidence.

    A user-provided flag wins. Standard and Full are official-pack-backed when
    available; an unavailable pack falls back transparently to TailTrail Lite.
    """
    lowered = goal.lower()
    hands_free = any(phrase in lowered for phrase in ("hands-free", "hands free", "end-to-end", "end to end"))
    if requested:
        normalized = "standard" if requested == "medium" else requested
        selected = official_aidlc_bridge.preflight(root, normalized, manifest)
        selected["selection"] = "explicit-flag"
        selected["full_escalation"] = {"state": "not-evaluated", "reason": "An explicit mode flag takes precedence."}
        return selected
    intent = _aidlc_intent(lowered)
    if intent == "opt-out":
        selected = official_aidlc_bridge.preflight(root, "off", manifest)
        selected["selection"] = "explicit-natural-language-opt-out"
        selected["full_escalation"] = {"state": "not-evaluated", "reason": "The request explicitly opted out of AIDLC."}
        return selected
    if intent == "full":
        selected = official_aidlc_bridge.preflight(root, "full", manifest)
        selected["selection"] = "explicit-natural-language-full"
        selected["full_escalation"] = {"state": "selected", "reason": "The request explicitly asked for Full official AIDLC."}
        return selected
    if intent == "standard":
        selected = official_aidlc_bridge.preflight(root, "standard", manifest)
        selected["selection"] = "explicit-natural-language-standard"
        selected["full_escalation"] = {"state": "not-eligible", "reason": "The request explicitly asked for Standard AIDLC mode."}
        return selected
    if intent == "none" and not hands_free:
        selected = official_aidlc_bridge.preflight(root, "lite", manifest)
        selected["selection"] = "default"
        selected["full_escalation"] = {"state": "not-eligible", "reason": "The request is not hands-free and did not explicitly request stronger AIDLC routing."}
        return selected
    signal_words = ("regulated", "compliance", "multi-team", "production", "release", "rollout", "migration", "infrastructure", "terraform", "security", "operations", "programme", "program")
    signals = [word for word in signal_words if word in lowered]
    risks = [str(item).lower() for item in plan.get("risk_indicators", [])]
    if hands_free and (len(signals) >= 2 or any(value in {"release", "security", "production"} for value in risks)):
        try:
            selected = official_aidlc_bridge.preflight(root, "full", manifest)
        except ValueError:
            selected = official_aidlc_bridge.preflight(root, "standard", manifest)
            selected["full_escalation"] = {
                "state": "eligible-awaiting-compatible-pack",
                "signals": signals,
                "reason": "Navigator found programme-scale signals, but Phase A compatibility is not ready; remain in Standard mode. Full mode requires a verified pack and a new Full-mode Planning Lock; this Standard run cannot be silently upgraded.",
            }
        else:
            selected["selection"] = "navigator-hands-free-escalation"
            selected["full_escalation"] = {
                "state": "selected",
                "signals": signals,
                "reason": "Navigator found programme-scale signals and a compatible pinned official pack; Full execution still requires a new Full-mode Planning Lock and cannot silently upgrade an existing run.",
            }
            return selected
    else:
        selected = official_aidlc_bridge.preflight(root, "standard", manifest)
        selected["full_escalation"] = {"state": "not-eligible", "signals": signals, "reason": "Standard mode covers the requested AIDLC depth without a Full official lifecycle transition."}
    selected["selection"] = "hands-free-default" if hands_free else "explicit-natural-language-aidlc"
    return selected


def aidlc_mode_features(mode: str) -> dict[str, list[str]]:
    """Describe the mode-owned controls; task-selected harnesses remain separate."""
    common = [
        "Navigator planning and Planning Lock",
        "Task-selected impact, requirement, testing, and review controls",
        "Explicit approval before implementation",
    ]
    if mode == "lite":
        return {"included": [*common, "Local AIDLC Lifecycle Lite only when Navigator selects it", "Question Orchestrator context, quality, and requirement traceability"], "not_included": ["Mandatory AIDLC requirements workshop", "Official pack verification or bridge identity"]}
    if mode == "standard":
        return {"included": [*common, "Verified official AI-DLC Requirements Analysis rules loaded by the host", "Question Orchestrator grounding, quality, and requirement traceability", "Host-generated official questions with options, TailTrail recommendations, and reasoning", "Canonical approved anchor and requirement-linked execution handoff"], "not_included": ["Full official lifecycle stages after requirements"]}
    if mode == "full":
        return {"included": [*common, "Phase A pinned-pack compatibility verification", "Full official AI-DLC lifecycle rules loaded by the host", "Question Orchestrator grounding, quality, and requirement traceability", "Host-generated official questions with options, TailTrail recommendations, and reasoning", "TailTrail anchor frozen from approved official requirement references and decisions", "After approval: receipt-driven official runtime attachment with ordered resume, redo, jump, and recovery history"], "not_included": ["TailTrail-generated substitute questions or silent local fallback"]}
    return {"included": [*common, "AIDLC lifecycle routing disabled for this run"], "not_included": ["Local AIDLC Requirements stage", "Official pack verification and bridge identity"]}


def guided_delivery(plan: dict[str, Any], goal: str, changed: list[str], root: Path, run_id: str | None = None) -> dict[str, Any]:
    """Choose the smallest delivery harness sequence after Navigator planning.

    This is a local routing decision, not an executor. The host/agent remains
    responsible for implementation after the user approves the plan.
    """
    lowered = goal.lower()
    tasks = {str(item).lower() for item in plan.get("task_types", [])}
    risks = {str(item).lower() for item in plan.get("risk_indicators", [])}
    hands_free = any(phrase in lowered for phrase in ("hands-free", "hands free", "end-to-end", "end to end"))
    multiple_requirements = len(plan.get("requirement_matrix", [])) > 1
    tiny = plan.get("recommended_workflow") == ["lean"] and not hands_free and not multiple_requirements
    broad = hands_free or len(changed) > 1 or any(word in lowered for word in ("feature", "implement", "workflow", "service", "endpoint", "api", "migration"))
    user_facing = behaviour_planning.selected_for(goal)
    ui_change = navigator.core.ui_change_requested(goal, changed)
    run = delivery_run_signals(root, run_id)
    selected: list[dict[str, str]] = []
    later: list[dict[str, str]] = []

    def add(name: str, why: str) -> None:
        selected.append({"name": name, "why": why})

    def defer(name: str, when: str) -> None:
        later.append({"name": name, "when": when})

    if tiny:
        add("Lean delivery", "narrow, low-risk task; preserve the existing small-diff workflow")
        stages = ["inspect the exact target", "implement the smallest change", "run focused proof", "report completion"]
    else:
        add("Canonical requirements", "create or confirm the approved requirement boundary before source changes")
        if "aidlc_requirements" in plan.get("recommended_workflow", []):
            add("Question Orchestrator", "ground AIDLC questions in saved requirements and inventory evidence, validate relevance, and map every decision to requirement IDs")
        add("Requirement Completion Harness", "map the requirement to code, preservation rules, and proof")
        if changed or broad:
            add("Requirement-to-Impact Map", "trace likely files, callers, and focused tests before implementation")
        add("Evidence-Aware Testing", "choose focused proof before claiming the requirement is complete")
        if broad:
            add("Architecture Fitness Harness", "multi-file or service/API scope can miss callers or change the wrong layer")
        if user_facing:
            add("Behaviour Harness", "the task names a user-facing/API/workflow outcome that needs flow evidence")
        if ui_change:
            add("UI Consistency Guardrail", "UI work must reuse the repository's existing components, tokens, layout, responsive, and accessibility conventions")
        if "refactor" in tasks:
            add("Maintainability Harness", "confirm the change did not add duplicate logic or unnecessary abstraction")
        if hands_free:
            add("Program Delivery Harness", "explicit hands-free/end-to-end request needs feature ordering and resume state")
        stages = ["approve requirements and scope", "map impacted paths", "implement the approved smallest change", "run selected computational checks", "issue one completion report"]
        if multiple_requirements:
            stages = ["approve the segregated requirement matrix and scope", "order requirements by dependency and select the first active requirement", "map and implement one approved requirement at a time", "record requirement-linked proof and drift at each checkpoint", "reconcile every requirement row in one completion report"]
        if ui_change:
            stages.insert(2, "inspect the existing UI system and nearest comparable screen; reuse its established patterns")
        if hands_free:
            stages = ["propose feature requirements and dependency order", "approve the program anchor and first active slice", "map and implement one approved slice at a time", "run selected computational checks at each checkpoint", "reconcile against the full approved program anchor"]

    if run["correction_cycle"]:
        add("Context Continuity Harness", "the selected run has a feedback packet or unresolved checkpoint drift: " + ", ".join(run["drift"] or ["feedback packet"]))
        add("Bounded Correction", "use the active requirement and evidence gap for one correction cycle before re-checking completion")
        stages = ["load current requirement evidence", "render continuity packet", "apply one bounded correction", "rerun selected computational checks", "issue updated completion report"]
    if run["recovery_risk"]:
        add("Git Readiness / Recovery Boundary", "the selected run has a recovery plan or reconciliation assessment; preserve task ownership before any recovery action")
        stages.insert(0, "verify the task recovery boundary")

    if not run["correction_cycle"]:
        defer("Context Continuity Harness", "a correction cycle, repeated evidence gap, scope drift, recovery, feature transition, or rejected requirement occurs; pass --run-id to evaluate that run")
    if not run["recovery_risk"]:
        defer("Safe Git Recovery", "the selected task has recovery risk, a failed bounded correction, or explicit rollback need; pass --run-id to evaluate that run")
    defer("Higher-Tier Testing", "the selected evidence profile requires integration, contract, E2E, infrastructure, or release confidence")
    if not hands_free:
        defer("Program Delivery Harness", "the user explicitly asks for hands-free or end-to-end multi-feature delivery")
    if not user_facing:
        defer("Behaviour Harness", "the approved requirement includes a user-facing, API, or journey contract")
    if ui_change:
        defer("Visual Regression Evidence", "the repository already has a project-owned visual test, or the approved task explicitly requires browser/screenshot proof; TailTrail will not add a visual-test dependency by default")
    if not broad:
        defer("Architecture Fitness Harness", "the approved scope expands beyond a narrow one-file change or adds callers/layers")
    if not risks:
        defer("Security / release controls", "the approved task introduces auth, secrets, dependency, migration, production, or release risk")

    hands_free_program = None
    if hands_free:
        hands_free_program = {
            "status": "proposed",
            "source_goal": goal,
            "feature_requirements": hands_free_requirements(goal),
            "dependency_order": [
                "Requirement and acceptance breakdown",
                "Read-only impact mapping and reusable-pattern discovery",
                "First independently verifiable implementation slice",
                "Remaining slices in dependency order",
                "Cross-slice integration proof and completion reconciliation",
            ],
            "first_active_slice": "Requirement gathering and program-anchor proposal only; no source implementation is active yet.",
            "approval_gate": "Approve the proposed feature requirements, dependency order, and first active slice before implementation begins.",
        }
        if ui_change:
            requirements = hands_free_program["feature_requirements"]
            requirements.append(
                {
                    "display_id": f"REQ-{len(requirements) + 1:02d}",
                    "statement": "Preserve the established UI system by reusing existing components, tokens, layout, responsive behavior, and accessibility patterns; do not introduce a parallel visual system.",
                }
            )

    return {
        "mode": "lean" if tiny else "guided-delivery",
        "selected": selected,
        "activated_later": later,
        "stages": stages,
        "run_signals": run,
        "approval_required": True,
        "approval_prompt": "Approve this guided delivery plan. Implement only the approved scope, run the selected proof, and return one completion report with unresolved evidence clearly named.",
        "execution_boundary": "Start selects and sequences TailTrail controls. It does not itself edit source, run tests, or invoke an implementation agent; those actions begin only after explicit approval.",
        "hands_free_program": hands_free_program,
    }


def approx_tokens(chars: int) -> int:
    return start_posture.approx_tokens(chars, APPROX_CHARS_PER_TOKEN)


def file_chars(path: Path) -> int:
    return start_posture.file_chars(path)


def existing_file_tokens(root: Path, paths: list[str]) -> tuple[int, list[dict[str, Any]]]:
    return start_posture.existing_file_tokens(root, paths, APPROX_CHARS_PER_TOKEN)


def avoided_context_from_plan(root: Path, plan: dict[str, Any]) -> list[str]:
    avoid_text = " ".join(str(item) for item in plan.get("avoid", []))
    avoided = [item for item in LARGE_CONTEXT_FILES if item in avoid_text and (root / item).is_file()]
    return avoided


def likely_used_files(plan: dict[str, Any]) -> list[str]:
    files = []
    for item in plan.get("likely_impacted_files", []):
        if isinstance(item, dict) and item.get("path"):
            files.append(str(item["path"]))
    return list(dict.fromkeys(files))


def token_posture(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    return start_posture.token_posture(root, plan, LARGE_CONTEXT_FILES, APPROX_CHARS_PER_TOKEN)


def learning_quality(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    tailtrail = root / ".tailtrail"
    events = tailtrail / "learning-events.jsonl"
    v3_events = tailtrail / "learning-v3" / "events.jsonl"
    index = tailtrail / "learning-index.md"
    refresh_actions = tailtrail / "learning-refresh-actions.json"
    matches = []
    use_proposal = plan.get("learning_use_proposal")
    if isinstance(use_proposal, dict):
        raw_matches = use_proposal.get("matches", [])
        if isinstance(raw_matches, list):
            matches = raw_matches[:3]
    elif isinstance(plan.get("graph_learning"), dict):
        raw_matches = plan["graph_learning"].get("matches", [])
        if isinstance(raw_matches, list):
            matches = raw_matches[:3]
    proposal_approval = use_proposal.get("approval", {}) if isinstance(use_proposal, dict) else {}
    action_count = 0
    blocking_actions = 0
    if refresh_actions.is_file():
        try:
            data = json.loads(refresh_actions.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        raw_actions = data.get("actions", []) if isinstance(data, dict) else []
        if isinstance(raw_actions, list):
            action_count = sum(1 for item in raw_actions if isinstance(item, dict))
            blocking_actions = sum(
                1
                for item in raw_actions
                if isinstance(item, dict) and item.get("action") in {"mark-stale", "suppress", "archive", "delete"}
            )
    review_recommended = False
    review_reason = "no learning index or events detected"
    if index.is_file() and (events.is_file() or v3_events.is_file()) and not refresh_actions.is_file():
        review_recommended = True
        review_reason = "learning index and events exist but no refresh actions have been recorded"
    elif blocking_actions:
        review_recommended = True
        review_reason = "blocking learning refresh actions exist and should be checked before reuse"
    elif matches and not refresh_actions.is_file():
        review_recommended = True
        review_reason = "learning matches surfaced without a refresh-action history"
    return {
        "index_exists": index.is_file(),
        "events_exist": events.is_file() or v3_events.is_file(),
        "refresh_actions_exist": refresh_actions.is_file(),
        "refresh_action_count": action_count,
        "blocking_refresh_actions": blocking_actions,
        "surfaced_matches": len(matches),
        "approval_required": bool(proposal_approval.get("required") or plan.get("learning_approval")),
        "review_recommended": review_recommended,
        "review_reason": review_reason,
        "review_command": "python3 scripts/tailtrail.py learn review --root .",
        "rule": "Learnings are advisory only. Use, ignore, or edit surfaced learnings before implementation.",
    }


def setup_posture(root: Path, command_prefix: str) -> dict[str, Any]:
    return start_posture.setup_posture(root, command_prefix, ROOT)


def review_posture(plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    return start_posture.review_posture(plan, command_prefix)


def harness_posture(root: Path, command_prefix: str) -> dict[str, Any]:
    return start_posture.harness_posture(root, command_prefix)


def bootstrap_posture(plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    return start_posture.bootstrap_posture(plan, command_prefix)


def evaluation_posture(goal: str, plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    return start_posture.evaluation_posture(goal, plan, command_prefix, EVALUATION_TRIGGER_WORDS)


def code_intelligence_policy(command_prefix: str) -> dict[str, Any]:
    return {
        "default": "local-only",
        "default_engine_path": ["lite", "v1", "v2"],
        "default_command": f"{command_prefix} graph ast --changed path/to/file --depth v1",
        "v2_command": f"{command_prefix} graph ast --changed path/to/file --depth v2",
        "v3_command": f"{command_prefix} graph ast --changed path/to/file --depth v3 --provider-output tailtrail-meta/providers/semantic.json --approved",
        "levels": [
            {"name": "lite", "meaning": "Fast selected-file symbol map.", "when": "Use when you only need to know which symbols exist."},
            {"name": "v1", "meaning": "Normal local impact map.", "when": "Use before most edits to see references, calls, hierarchy, endpoints, DB/config clues, likely tests, and changed-symbol impact."},
            {"name": "v2", "meaning": "Richer local semantic metadata.", "when": "Use when V1 is not enough and you need symbol index, import/module edges, endpoint-to-handler links, data-flow-lite hints, or provider readiness."},
            {"name": "v3", "meaning": "Provider-backed metadata ingestion.", "when": "Use only when provider-backed semantic intelligence is requested or an approved provider-output file exists."},
        ],
        "v3_rule": "V3 is never default and requires explicit --depth v3 plus --provider-output, plus --approved or local policy enablement.",
        "navigator_rule": "Navigator may recommend V3 only when provider-backed semantic intelligence is requested or an approved provider-output file exists for the task.",
        "auto_run_rule": "TailTrail must not auto-run JDT, Roslyn, LSP/language servers, SCIP, tree-sitter, SQL parsers, Terraform parsers, MCP providers, networked services, or repo-owned extractors.",
        "evidence_rule": "Provider-backed metadata is advisory. Exact source, tests, CI, scanner evidence, policy, guardrails, and explicit user direction still win.",
    }


def next_actions(plan: dict[str, Any]) -> list[dict[str, str]]:
    actions = [
        {
            "action": "review",
            "label": "Review the plan first.",
            "when": "Always.",
            "prompt": "Review this TailTrail Start report. I will approve or edit the plan before implementation.",
        },
        {
            "action": "approve",
            "label": "Approve implementation.",
            "when": "Use when selected features, impacted files, and validation look right.",
            "prompt": "Approve this plan. Implement the smallest maintainable change and run or name the focused validation.",
        },
        {
            "action": "edit",
            "label": "Edit the plan.",
            "when": "Use when the plan is too heavy, too light, missing files, or recommending the wrong command.",
            "prompt": "Edit the plan: keep the useful selected features, skip anything too heavy, add the missing files, and use the repo-approved validation command.",
        },
        {
            "action": "validation",
            "label": "Confirm focused validation.",
            "when": "Use before or after implementation when the validation command needs to be explicit.",
            "prompt": "Use this focused validation only: REPLACE_WITH_EXACT_COMMAND. If it cannot run, explain why and name the closest manual check.",
        },
    ]
    if plan.get("scan_approval"):
        actions.append(
            {
                "action": "scan-approval",
                "label": "Approve exactly one scan command, or decline scans.",
                "when": "Use only after reviewing the Scan Approval section.",
                "prompt": "Approve only this command: REPLACE_WITH_EXACT_COMMAND. Do not run any other scanner, audit, build, or networked command.",
            }
        )
    use_proposal = plan.get("learning_use_proposal")
    proposal_approval = use_proposal.get("approval", {}) if isinstance(use_proposal, dict) else {}
    if plan.get("learning_approval") or proposal_approval.get("required"):
        actions.append(
            {
                "action": "learning-approval",
                "label": "Choose whether the surfaced Learning V3 proposal may influence the plan.",
                "when": "Use only when a project-framed Learning Use Proposal has eligible matches.",
                "prompt": "Choose use selected learnings, ignore all learnings, or edit selected learning IDs. Default to do-not-use. Current source, tests, scanner evidence, policy, and guardrails win.",
            }
        )
    if plan.get("review_plan"):
        review = plan["review_plan"]
        actions.append(
            {
                "action": "review-after-implementation",
                "label": "Approve post-implementation review.",
                "when": "Use after implementation and focused validation when you want TailTrail to review the changed scope.",
                "prompt": f"Approve TailTrail review of {review['default']}. Show findings with severity, file, function, line, impact, fix, validation, confidence, and safe-fix status. Do not apply fixes without approval.",
            }
        )
    actions.append(
        {
            "action": "defer-heavy",
            "label": "Make the workflow leaner.",
            "when": "Use when this is a narrow fix or docs-only task.",
            "prompt": "This is too heavy. Use lean mode: read only the target file and focused test, make the smallest change, and do not run broad scanners.",
        }
    )
    return actions


def build_report(
    goal: str,
    root: Path,
    changed: list[str],
    command_prefix: str,
    run_id: str | None = None,
    aidlc_mode: str = "",
    official_manifest: str | None = None,
    spec_kit_feature: str | None = None,
    workflow_override: str | None = None,
    has_error_artifact: bool = False,
    has_reproduction_command: bool = False,
) -> dict[str, Any]:
    command_prefix = normalize_command_prefix(root, command_prefix)
    plan = navigator.decide(
        goal,
        root,
        changed,
        command_prefix,
        workflow_override=workflow_override,
        has_error_artifact=has_error_artifact,
        has_reproduction_command=has_reproduction_command,
    )
    classification = plan.get("workflow_classification", {})
    if classification.get("workflow_type") == "debug-investigation":
        impacted = [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)]
        estimated_tokens = int((plan.get("token_budget", {}) or {}).get("budget_tokens", 4000))
        requirement = {
            "display_id": "REQ-DEBUG-01",
            "kind": "debug-investigation",
            "statement": "Prove the reported symptom's root cause while preserving the approved successful path and blocking correction until separately approved.",
            "acceptance_criteria": [
                "A deterministic or explicitly bounded intermittent reproduction is approved.",
                "The proven cause is supported by saved experiment evidence and a competing hypothesis is eliminated.",
                "No correction or source write occurs before separate approval.",
            ],
            "preserve_rules": [
                "Preserve current successful behaviour outside the reproduced failure path.",
                "Do not call production systems or external providers during planning.",
            ],
            "likely_paths": [str(item.get("path")) for item in impacted if item.get("path")],
            "validation_contract": {"tiers": ["reproduction", "root-cause", "regression", "behaviour"]},
            "confidence": "planning-evidence-only",
        }
        requirement_facets = [
            {"id": "REQ-DEBUG-01.A", "objective": "Reproduce the reported failure under an approved, bounded procedure.", "proof": "A saved command-result receipt matches the approved actual outcome."},
            {"id": "REQ-DEBUG-01.B", "objective": "Preserve successful behaviour outside the reproduced failure path.", "proof": "Focused preservation evidence passes after the correction."},
            {"id": "REQ-DEBUG-01.C", "objective": "Prove one root cause and eliminate a relevant competing hypothesis.", "proof": "Requirement-linked experiment receipts support the root-cause decision."},
            {"id": "REQ-DEBUG-01.D", "objective": "Keep any correction within separately approved file and symbol scope.", "proof": "The post-edit scope check reports no unresolved unexpected path."},
        ]
        plan["requirement_matrix"] = [requirement]
        validation_rows = [
            {"tier": "Reproduction", "proof_target": "The approved trigger produces the saved failure signature.", "candidate_evidence": "Approved reproduction command plus exact command-result receipt.", "activation_gate": "After reproduction-contract approval.", "pass_condition": "Observed actual outcome matches the approved contract repeatably or within its bounded intermittent rule."},
            {"tier": "Root cause", "proof_target": "One hypothesis explains the failure and a relevant alternative is eliminated.", "candidate_evidence": "Approved experiment result linked to an Execution Evidence fingerprint.", "activation_gate": "After hypothesis ranking and experiment approval.", "pass_condition": "Saved evidence strengthens the selected cause and eliminates a competing hypothesis."},
            {"tier": "Regression", "proof_target": "The corrected path no longer produces the duplicate effect.", "candidate_evidence": "Reproduction rerun plus a focused regression-test receipt.", "activation_gate": "After separate correction approval and implementation.", "pass_condition": "The original failure is absent and the focused regression check passes."},
            {"tier": "Behaviour", "proof_target": "Successful first-attempt behaviour and approved external-effect invariants remain intact.", "candidate_evidence": "Approved behaviour scenario and requirement-linked receipt.", "activation_gate": "During selected-Harness convergence.", "pass_condition": "Preservation scenario passes with no unresolved behaviour drift."},
        ]
        token_parts = {
            "planning_and_reproduction": round(estimated_tokens * 0.20),
            "orientation_and_hypotheses": round(estimated_tokens * 0.20),
            "bounded_experiments": round(estimated_tokens * 0.25),
            "correction_and_scope_check": round(estimated_tokens * 0.15),
        }
        token_parts["validation_and_closure"] = estimated_tokens - sum(token_parts.values())
        delivery = {
            "mode": "debug-investigation",
            "selected": [
                {"name": "Debug Harness", "why": "turn the saved symptom into reproduction and root-cause evidence before correction"},
                {"name": "Reproduction Contract", "why": "freeze the expected failure, command boundary, and success criteria before experiments"},
                {"name": "Durable Workflow Runtime", "why": "preserve investigation state, approvals, evidence, retries, and resume position under one run"},
                {"name": "Hypothesis Ledger and Bounded Experiment Loop", "why": "rank falsifiable causes and reject unsupported or repeated probes"},
                {"name": "Execution Evidence", "why": "link real command outcomes to the active requirement and experiment"},
                {"name": "Token Harness", "why": "keep future logs and traces bounded while preserving exact failure evidence"},
            ],
            "activated_later": [
                {"name": "Code Graph orientation", "when": "after reproduction approval; refresh only when saved graph evidence is absent or stale"},
                {"name": "Context Continuity", "when": "after an unchanged, regressed, repeated, or cycle-exhausting experiment"},
                {"name": "Correction Scope and Drift Check", "when": "after root cause proof and separate correction approval"},
                {"name": "Requirement Completion, Architecture, Behaviour, Maintainability, and Evidence-Aware Testing", "when": "after correction implementation produces factual execution evidence"},
                {"name": "Canonical Closure and Debug Governance", "when": "after selected Harness convergence"},
                {"name": "Evaluation and governed learning", "when": "after Completion Report generation and trusted acceptance"},
            ],
            "stages": [
                "approve the Debug Planning Lock",
                "draft and approve the versioned reproduction contract",
                "create project orientation and assess Code Graph freshness",
                "record competing hypotheses and approve their ranking",
                "propose and approve one bounded discriminating experiment",
                "run the approved probe and record exact Execution Evidence",
                "prove or reject root cause from saved evidence",
                "propose and separately approve file and symbol correction scope",
                "implement the bounded correction and compare actual scope for drift",
                "run regression and preservation evidence, then selected Harness convergence",
                "finalize canonical closure, token posture, governance, and learning eligibility",
            ],
            "execution_boundary": "This Start run creates planning metadata only. It does not open Debug Intake, inspect source, execute reproduction, approve experiments, edit code, or grant correction authority.",
            "hands_free_program": None,
        }
        return {
            "goal": goal,
            "root": root.as_posix(),
            "command_prefix": command_prefix,
            "navigator": plan,
            "guided_delivery": delivery,
            "debug_plan": {
                "workflow_type": "debug-investigation",
                "classification_reason_code": classification.get("reason_code"),
                "classification_reason": classification.get("reason"),
                "known_symptom": classification.get("known_symptom") or goal,
                "material_unknowns": list(classification.get("unknown_evidence", [])),
                "classification_evidence": {
                    "explicit_override": workflow_override == "debug",
                    "error_artifact_supplied": has_error_artifact,
                    "reproduction_command_supplied": has_reproduction_command,
                },
                "reproduction_questions": [
                    "Confirm the exact failure signature and restored-behaviour result, including relevant effect counts, status, or error boundary.",
                    ("Confirm that the supplied reproduction procedure is the smallest safe discriminating probe and define its expected exit status or bounded outcome." if has_reproduction_command else "Provide or approve the smallest deterministic reproduction command, fixture, or bounded intermittent procedure."),
                    "Confirm the successful path, external-effect invariants, safety limits, and data that must remain unchanged during investigation.",
                ],
                "requirement_facets": requirement_facets,
                "evidence_tiers": ["reproduction", "root-cause", "regression", "behaviour"],
                "validation_rows": validation_rows,
                "token_breakdown": token_parts,
                "safety_boundary": "Planning is metadata-only. No source reads, tests, scanners, Git changes, external calls, reproduction approval, or correction authority are created.",
                "exactness_posture": "The symptom, run identity, target identity, supplied evidence-presence flags, and future receipts remain exact. No raw error or command content is copied into this plan.",
                "scope_source": "user-supplied-candidates" if changed else "saved-code-graph" if plan.get("graph_cache") else "unresolved",
            },
            "architecture_plan": {"selected": False, "status": "deferred-until-reproduction"},
            "behaviour_plan": {"selected": False, "status": "deferred-until-correction"},
            "maintainability_plan": {"selected": False, "status": "deferred-until-correction"},
            "ui_plan": {"selected": False, "surface_status": "not-selected"},
            "ui_consistency": {"selected": False},
            "aidlc_mode": {"mode": "off", "selection": "debug-investigation", "state": "not-selected", "boundary": "AIDLC is not selected by DI-2; requirement/reproduction authority is handled by later debug phases."},
            "aidlc_mode_features": {"included": [], "not_included": ["AIDLC lifecycle during Debug Start planning"]},
            "spec_kit_source": None,
            "next_actions": [],
            "token_posture": {
                "used_tokens": estimated_tokens,
                "baseline_tokens": estimated_tokens,
                "avoided_tokens": 0,
                "estimated_reduction_percent": 0,
            },
            "learning_quality": {},
            "setup_posture": {},
            "review_posture": {"selected": False, "scope": "debug correction only after implementation"},
            "harness_posture": {},
            "bootstrap_posture": {},
            "evaluation_posture": {},
            "code_intelligence": {"mode": "saved-only", "external_providers": "not-run"},
            "next_step": "Review and approve this Debug Start Plan before drafting a reproduction contract.",
        }
    plan["likely_impacted_files"] = architecture_planning.filter_weak_suggestions(
        goal,
        [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)],
    )
    behaviour_selected = behaviour_planning.selected_for(goal)
    ui_change = navigator.core.ui_change_requested(goal, changed)
    ui_profile = ui_planning.discover(root, goal, changed) if ui_change else {"selected": False, "surface_status": "not-selected", "candidates": []}
    plan["likely_impacted_files"] = behaviour_planning.filter_weak_suggestions(
        goal, plan["likely_impacted_files"]
    )
    plan["likely_impacted_files"] = architecture_planning.add_explicit_role_candidates(
        root, goal, plan["likely_impacted_files"]
    )
    plan["likely_impacted_files"] = behaviour_planning.add_role_candidates(
        root, goal, plan["likely_impacted_files"], behaviour_selected
    )
    if ui_change:
        plan["likely_impacted_files"] = ui_planning.refine_impacted(
            goal, changed, plan["likely_impacted_files"], ui_profile
        )
    initial_paths = [str(item.get("path")) for item in plan.get("likely_impacted_files", []) if isinstance(item, dict) and item.get("path")]
    if not plan.get("revision_requirement_matrix"):
        plan["requirement_matrix"] = requirement_discovery.matrix(goal, initial_paths)
    delivery = guided_delivery(plan, goal, changed, root, run_id)
    spec_kit_source = spec_kit_bridge.load(root, spec_kit_feature) if spec_kit_feature else None
    if spec_kit_source:
        paths = [str(item.get("path")) for item in plan.get("likely_impacted_files", []) if isinstance(item, dict) and item.get("path")]
        plan["requirement_matrix"] = spec_kit_bridge.requirement_matrix(spec_kit_source, paths)
        plan["selected_features"] = [
            {"name": "Intent Bridge", "why": f"use imported `{spec_kit_feature}` requirements without regeneration or source writes"},
            *plan.get("selected_features", []),
        ]
        delivery["selected"] = [
            {"name": "Intent Bridge", "why": f"preserve {len(spec_kit_source['requirements'])} imported requirements and source revision through approval"},
            *delivery["selected"],
        ]
    else:
        paths = [str(item.get("path")) for item in plan.get("likely_impacted_files", []) if isinstance(item, dict) and item.get("path")]
        program = delivery.get("hands_free_program")
        if isinstance(program, dict) and isinstance(program.get("feature_requirements"), list):
            plan["requirement_matrix"] = requirement_discovery.from_features(program["feature_requirements"], paths)
    architecture_selected = any(
        item.get("name") == "Architecture Fitness Harness"
        for item in delivery.get("selected", [])
        if isinstance(item, dict)
    )
    architecture_plan = architecture_planning.build(
        goal,
        plan.get("likely_impacted_files", []),
        plan.get("requirement_matrix", []),
        architecture_selected,
    )
    architecture_planning.apply_contracts(plan.get("requirement_matrix", []), architecture_plan)
    ui_plan = ui_planning.build(
        goal,
        plan.get("requirement_matrix", []),
        ui_profile,
        ui_change,
    )
    ui_planning.apply_contracts(plan.get("requirement_matrix", []), ui_plan)
    behaviour_selected = any(
        item.get("name") == "Behaviour Harness"
        for item in delivery.get("selected", [])
        if isinstance(item, dict)
    )
    behaviour_plan = behaviour_planning.build(
        goal,
        plan.get("likely_impacted_files", []),
        plan.get("requirement_matrix", []),
        behaviour_selected,
    )
    behaviour_planning.apply_contracts(plan.get("requirement_matrix", []), behaviour_plan)
    maintainability_selected = any(
        item.get("name") == "Maintainability Harness"
        for item in delivery.get("selected", [])
        if isinstance(item, dict)
    )
    maintainability_plan = maintainability_planning.build(
        goal,
        plan.get("likely_impacted_files", []),
        plan.get("requirement_matrix", []),
        maintainability_selected,
    )
    maintainability_planning.apply_contracts(plan.get("requirement_matrix", []), maintainability_plan)
    mode = aidlc_mode_selection(goal, aidlc_mode, root, plan, official_manifest)
    if mode["mode"] == "off":
        delivery["selected"] = [item for item in delivery["selected"] if item.get("name") != "AIDLC"]
        plan["selected_features"] = [item for item in plan.get("selected_features", []) if item.get("name") != "AIDLC"]
        delivery["activated_later"].append({"name": "AIDLC", "when": "disabled explicitly with --aidlc off for this Start run"})
    return {
        "goal": goal,
        "root": root.as_posix(),
        "command_prefix": command_prefix,
        "navigator": plan,
        "guided_delivery": delivery,
        "architecture_plan": architecture_plan,
        "behaviour_plan": behaviour_plan,
        "maintainability_plan": maintainability_plan,
        "ui_plan": ui_plan,
        "ui_consistency": {
            "selected": ui_change,
            "surface_status": ui_plan.get("surface_status", "not-selected"),
            "command": f"{command_prefix} ui discover --root {json.dumps(root.as_posix())}" + "".join(f" --changed {path}" for path in changed[:5]),
            "boundary": "Reuse existing components, styles, tokens, layout, responsive behavior, and accessibility patterns. Preserve the established UI system; do not introduce a UI library, font, global token set, or unrelated redesign without explicit approval.",
        },
        "aidlc_mode": mode,
        "aidlc_mode_features": aidlc_mode_features(mode["mode"]),
        "spec_kit_source": spec_kit_source,
        "next_actions": next_actions(plan),
        "token_posture": start_posture.token_posture(root, plan, LARGE_CONTEXT_FILES, APPROX_CHARS_PER_TOKEN),
        "learning_quality": learning_quality(root, plan),
        "setup_posture": start_posture.setup_posture(root, command_prefix, ROOT),
        "review_posture": start_posture.review_posture(plan, command_prefix),
        "harness_posture": start_posture.harness_posture(root, command_prefix),
        "bootstrap_posture": start_posture.bootstrap_posture(plan, command_prefix),
        "evaluation_posture": start_posture.evaluation_posture(goal, plan, command_prefix, EVALUATION_TRIGGER_WORDS),
        "code_intelligence": code_intelligence_policy(command_prefix),
        "next_step": "Review the guided delivery plan, then approve or edit before implementation.",
    }


def normalize_command_prefix(root: Path, command_prefix: str) -> str:
    """Render commands relative to the target project, not the agent's cwd."""
    normalized = command_prefix.replace("\\", "/")
    if "tailtrail.py" not in normalized:
        return command_prefix
    if "tailtrail/scripts/tailtrail.py" in normalized:
        return command_prefix
    if "scripts/tailtrail.py" in normalized:
        if (root / "tailtrail" / "scripts" / "tailtrail.py").is_file():
            return command_prefix.replace("scripts/tailtrail.py", "tailtrail/scripts/tailtrail.py").replace("scripts\\tailtrail.py", "tailtrail\\scripts\\tailtrail.py")
        return command_prefix
    runner = command_prefix.split("tailtrail.py", 1)[0].strip()
    if not runner:
        return command_prefix
    if (root / "tailtrail" / "scripts" / "tailtrail.py").is_file():
        return f"{runner} tailtrail/scripts/tailtrail.py"
    if (root / "scripts" / "tailtrail.py").is_file():
        return f"{runner} scripts/tailtrail.py"
    return command_prefix


def focused_validation_command(root: Path, impacted: list[dict[str, Any]], command_prefix: str) -> str | None:
    """Suggest one runnable focused test command when the local convention is clear."""
    test_paths = [str(item.get("path", "")) for item in impacted if isinstance(item, dict) and "test" in str(item.get("path", "")).lower()]
    if not test_paths:
        return None
    test_path = Path(test_paths[0])
    candidate = root / test_path
    try:
        body = candidate.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    # The project path can itself contain "tailtrail" (for example
    # D:/PD/TailTrail_Test/tailtrail/scripts/tailtrail.py), so never derive
    # the interpreter by splitting the full launcher path.
    lowered = command_prefix.lower().lstrip()
    if lowered.startswith("py -3 "):
        runner = "py -3"
    elif lowered.startswith("python3 "):
        runner = "python3"
    elif lowered.startswith("python "):
        runner = "python"
    else:
        runner = "python3"
    if "import unittest" in body or "from unittest" in body:
        return f"{runner} -m unittest discover -s {test_path.parent.as_posix()} -p {test_path.name} -v"
    if test_path.suffix == ".py":
        return f"{runner} -m pytest {test_path.as_posix()}"
    return None


def focused_validation_plan(
    root: Path,
    impacted: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    command_prefix: str,
) -> list[dict[str, str]]:
    """Return every requested validation tier without inventing a test target."""
    requested: list[str] = []
    for row in requirements:
        contract = row.get("validation_contract", {}) if isinstance(row, dict) else {}
        for tier in contract.get("tiers", []) if isinstance(contract, dict) else []:
            if isinstance(tier, str) and tier not in requested:
                requested.append(tier)
    test_items = [
        item for item in impacted
        if isinstance(item, dict) and "test" in str(item.get("path", "")).lower()
    ]
    rows: list[dict[str, str]] = []
    for tier in requested or ["unit"]:
        tier_paths = [
            item for item in test_items
            if f"/{tier}/" in "/" + str(item.get("path", "")).lower().replace("\\", "/") + "/"
        ]
        if tier == "behaviour" and not tier_paths:
            tier_paths = [
                item for item in test_items
                if "/tests/ui/" in "/" + str(item.get("path", "")).lower().replace("\\", "/")
                or any(marker in str(item.get("path", "")).lower() for marker in ("accessibility", "a11y", "visual"))
            ]
        candidate_items = tier_paths or ([] if tier in {"unit", "integration", "contract", "behaviour", "e2e"} else test_items)
        command = focused_validation_command(root, candidate_items[:1], command_prefix) if candidate_items else None
        rows.append({
            "tier": tier,
            "candidate": str(candidate_items[0].get("path")) if candidate_items else "not resolved from planning evidence",
            "command": command or "",
            "status": "planned after approval" if command else "must be discovered after approval",
        })
    return rows


def short_trigger(value: str) -> str:
    """Keep deferred-feature cells readable; detailed rules remain in verbose artifacts."""
    lowered = value.lower()
    if "context continuity" in lowered or "correction cycle" in lowered:
        return "After incomplete work, drift, rejection, failed correction, or slice transition."
    if "git recovery" in lowered or "rollback" in lowered or "recovery risk" in lowered:
        return "After recovery risk, repeated failure, conflict, or explicit rollback need."
    if "higher-tier" in lowered or "integration" in lowered or "contract" in lowered:
        return "When the approved proof needs integration, contract, behaviour, infrastructure, or release evidence."
    return value.split(";")[0].rstrip(".") + "."


def debug_start_report(report: dict[str, Any], verbose: bool = False) -> str:
    """Render one canonical, planning-only Debug Start report."""
    plan = report["navigator"]
    debug_plan = report["debug_plan"]
    delivery = report["guided_delivery"]
    lock = report.get("planning_lock")
    impacted = [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)]
    requirements = [item for item in plan.get("requirement_matrix", []) if isinstance(item, dict)]
    lines = ["# TailTrail Debug Start Plan", ""]
    lines.extend(["## Planning Lock", ""])
    if lock:
        lines.extend([
            f"- Run ID: `{lock['run_id']}`",
            f"- Target identity: `{lock.get('target_identity', {}).get('fingerprint', 'legacy lock')}`.",
            f"- State: **{lock['status']}**; managed writes allowed: **{str(lock['writes_allowed']).lower()}**.",
            f"- Saved plan: `{report.get('planning_report', {}).get('artifact', 'saved with this run')}`.",
        ])
    else:
        lines.append("- No persisted Planning Lock is attached to this rendered report.")
    lines.extend([
        "",
        "## Start Here",
        "",
        "- Review the symptom boundary, unknowns, proposed reproduction questions, and safety controls.",
        "- Nothing in this report reproduces, diagnoses, or changes the project.",
        "",
        "## Navigator Decision",
        "",
        f"- Workflow type: `{debug_plan['workflow_type']}`",
        f"- Reason: `{debug_plan.get('classification_reason_code')}` - {display_prose(debug_plan.get('classification_reason'))}",
        f"- Known symptom: {display_prose(debug_plan.get('known_symptom'))}",
        "- Material unknowns:",
    ])
    lines.extend(f"  - {display_prose(item)}" for item in debug_plan.get("material_unknowns", []))
    evidence = debug_plan.get("classification_evidence", {})
    lines.extend([
        f"- Classification evidence: explicit override `{str(evidence.get('explicit_override', False)).lower()}`, error artifact supplied `{str(evidence.get('error_artifact_supplied', False)).lower()}`, reproduction command supplied `{str(evidence.get('reproduction_command_supplied', False)).lower()}`.",
        f"- Approval posture: {plan.get('workflow_classification', {}).get('approval_posture')}",
        "",
        "## Scope",
        "",
        f"- Target repository: `{report['root']}`",
        f"- Scope source: `{debug_plan.get('scope_source')}`.",
    ])
    if impacted:
        if debug_plan.get("scope_source") == "user-supplied-candidates":
            lines.append("- The paths below were supplied by the user as inspection candidates; orientation must confirm their roles before correction scope is approved.")
        elif debug_plan.get("scope_source") == "saved-code-graph":
            lines.append("- Saved graph evidence is advisory and was not freshness-checked during Planning Lock.")
        for item in impacted if verbose else impacted[:6]:
            lines.append(f"- `{item.get('path')}` - {display_prose(item.get('reason'))}")
    else:
        lines.append("- Likely code scope is unresolved. Source discovery is deferred until approval.")
    lines.extend(["", "## Requirements", ""])
    for item in requirements:
        lines.append(f"- **{item.get('display_id')}:** {display_prose(item.get('statement'))}")
        if verbose:
            lines.append("  - Preserve:")
            lines.extend(f"    - {display_prose(rule)}" for rule in item.get("preserve_rules", []))
            lines.append("  - Acceptance:")
            lines.extend(f"    - {display_prose(rule)}" for rule in item.get("acceptance_criteria", []))
    facets = [item for item in debug_plan.get("requirement_facets", []) if isinstance(item, dict)]
    if facets:
        lines.extend(["", "### Requirement facets", "", "| ID | Investigation objective | Required proof |", "| --- | --- | --- |"])
        for facet in facets:
            lines.append(f"| {facet.get('id')} | {display_prose(facet.get('objective'))} | {display_prose(facet.get('proof'))} |")
    lines.extend(["", "## Selected TailTrail features", "", "| Feature | When | Why |", "| --- | --- | --- |", "| Navigator | Planning now | classified the symptom-first workflow and created the canonical Planning Lock |"])
    for item in delivery.get("selected", []):
        lines.append(f"| {item.get('name')} | Planning / after approval | {display_prose(item.get('why'))} |")
    lines.extend(["", "## Deferred TailTrail features", ""])
    for item in delivery.get("activated_later", []):
        lines.append(f"- **{item.get('name')}:** {display_prose(item.get('when'))}")
    lines.extend(["", "## Proposed reproduction questions", ""])
    for index, question in enumerate(debug_plan.get("reproduction_questions", []), start=1):
        lines.append(f"{index}. {display_prose(question)}")
    lines.extend(["", "## Plan", ""])
    for index, stage in enumerate(delivery.get("stages", []), start=1):
        lines.append(f"{index}. {display_prose(stage)}")
    lines.extend(["", "## Guided delivery", "", f"- Boundary: {delivery.get('execution_boundary')}", "- The Debug Intake artifact and reproduction contract are not created or approved by this Start command."])
    lines.extend([
        "", "## Focused validation", "",
        "No validation has run during Planning Lock. The table defines the approved evidence path instead of implying a result.", "",
        "| Evidence tier | What it must prove | Candidate evidence | Activation gate | Pass condition |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in debug_plan.get("validation_rows", []):
        lines.append(
            f"| {display_prose(row.get('tier'))} | {display_prose(row.get('proof_target'))} | "
            f"{display_prose(row.get('candidate_evidence'))} | {display_prose(row.get('activation_gate'))} | "
            f"{display_prose(row.get('pass_condition'))} |"
        )
    token = report["token_posture"]
    lines.extend([
        "",
        "## Token estimate",
        "",
        f"- Estimated focused context budget: approximately `{token['used_tokens']}` tokens.",
        "- Evidence: local planning estimate only; actual model tokens require run-linked host/provider telemetry.",
    ])
    breakdown = debug_plan.get("token_breakdown", {})
    if breakdown:
        lines.extend([
            "", "| Stage group | Estimated tokens |", "| --- | ---: |",
            f"| Planning and reproduction | {breakdown.get('planning_and_reproduction', 0)} |",
            f"| Orientation and hypotheses | {breakdown.get('orientation_and_hypotheses', 0)} |",
            f"| Bounded experiments | {breakdown.get('bounded_experiments', 0)} |",
            f"| Correction and scope check | {breakdown.get('correction_and_scope_check', 0)} |",
            f"| Validation and closure | {breakdown.get('validation_and_closure', 0)} |",
        ])
    lines.extend([
        "",
        "## Evidence posture",
        "",
        f"- Exactness: {debug_plan.get('exactness_posture')}",
        f"- Safety: {debug_plan.get('safety_boundary')}",
        "- External providers, tests, scanners, source inspection, Debug Intake, and correction execution: **not run**.",
        "",
        "## Approval",
        "",
        "- Approve this exact Debug Start Plan to allow DI-3 to draft a reproduction contract under the same run ID.",
        "- Reject or revise the symptom, scope, questions, evidence tiers, or safety boundary while keeping this run awaiting approval.",
        "- Use `--build` in a new Start request only if this should be treated as an implementation requirement instead of an unexplained symptom.",
        "",
    ])
    return "\n".join(lines)


def compact_start_report(report: dict[str, Any]) -> str:
    """Keep the normal Start response short enough to approve confidently."""
    plan = report["navigator"]
    delivery = report["guided_delivery"]
    lock = report.get("planning_lock")
    impacted = [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)]
    root = Path(str(report["root"]))
    goal = display_prose(report["goal"])
    lowered_goal = goal.lower()
    lines = ["# TailTrail Start Plan", "", f"**Goal:** {goal}", ""]
    if lock:
        lines.extend(
            [
                "## Planning Lock",
                "",
                f"- Run ID: `{lock['run_id']}`",
                f"- Target identity: `{lock.get('target_identity', {}).get('fingerprint', 'legacy lock')}`.",
                "- Status: **awaiting approval** - no source files, tests, scanners, or Git changes were run.",
                "",
            ]
        )
        host = lock.get("host_workspace")
        if isinstance(host, dict) and host.get("host"):
            lines.append(f"- Host workspace: `{host.get('host')}` / `{host.get('status')}` ({host.get('mapping', 'not-mapped')}).")
        policy = lock.get("enterprise_policy")
        if isinstance(policy, dict):
            lines.append(f"- Enterprise target policy: `{policy.get('status', 'not-configured')}`.")
    workflow_runtime = report.get("workflow_runtime", {})
    if isinstance(workflow_runtime, dict) and workflow_runtime.get("enabled"):
        lines.extend(["", "## Workflow runtime", "", f"- Draft: `{workflow_runtime.get('workflow_id')}` - no durable workflow artifacts exist before approval.", "- After approval: bind the canonical anchor, declare selected capabilities, and freeze the non-executing compiler graph."])
    lines.extend(["## Scope", ""])
    target = report.get("target_root")
    if isinstance(target, dict) and target.get("requested"):
        lines.append(f"- Target repository: `{target['requested']}` ({target.get('status', 'verified')}).")
    for item in impacted[:4]:
        lines.append(f"- `{item['path']}` - {display_prose(item['reason'])}")
    if not impacted:
        if report.get("ui_plan", {}).get("selected"):
            lines.append("- UI implementation surface not discovered. Confirm the frontend/UI root or approve bounded read-only UI discovery; backend files were not substituted as UI scope.")
        else:
            lines.append("- Scope unresolved: no reliable repository file matched this goal. Add `--changed path/to/file` or approve read-only discovery; unrelated Git changes were not used.")
    roles = report.get("input_roles", {})
    if isinstance(roles, dict):
        read_only_count = max(0, len(roles.get("inputs", [])) - 1)
        lines.extend(["", "## Input roles", "", f"- Target: `{roles.get('target_root', root.as_posix())}` - editable only after approval.", f"- Read-only inputs: {read_only_count}. References, design, requirements, and evidence cannot become implementation scope."])
    lines.extend(["", "## Requirements", ""])
    hands_free_program = delivery.get("hands_free_program")
    spec_kit_source = report.get("spec_kit_source")
    requirement_rows = [item for item in plan.get("requirement_matrix", []) if isinstance(item, dict)]
    for item in requirement_rows:
        lines.append(f"- **{item.get('display_id', 'REQ')}:** {display_prose(item.get('statement', ''))}")
    if isinstance(spec_kit_source, dict):
        lines.append(f"- Source: `{spec_kit_source['feature_id']}` / `{spec_kit_source['source_revision']}` (imported snapshot v{spec_kit_source['snapshot_version']}).")
    if not requirement_rows:
        lines.append("- Implement the approved goal with the smallest maintainable change.")
    aidlc = report.get("aidlc_requirements")
    if isinstance(aidlc, dict):
        stage = aidlc.get("aidlc_stage", {})
        if aidlc.get("state") == "official-aidlc-host-generation-required":
            lines.extend(["", "## Official AIDLC requirements", "", "- The verified official Requirements Analysis stage is ready for the configured host.", "- The host must load the recorded official rules and saved Question Orchestrator context, then generate material questions with requirement traceability, options, TailTrail advisory recommendations, and evidence-grounded reasoning before implementation can be approved.", "- TailTrail validates grounding and persists that official stage artifact under this same run ID; it will not fabricate a local substitute questionnaire.", ""])
        else:
            lines.extend(["", "## AIDLC requirements and recommendations", "", "- Assumption: " + "; ".join(stage.get("assumptions", [])), "- Non-goal: " + "; ".join(stage.get("non_goals", [])), ""])
            for question in aidlc.get("questions", []):
                lines.extend([f"### {question.get('id', 'Question')} - {display_prose(question.get('question', ''))}", f"- **Recommended:** {display_prose(question.get('recommended', ''))}", f"- **Reasoning:** {display_prose(question.get('reasoning', ''))}", ""])
    aidlc_mode = report.get("aidlc_mode", {})
    if isinstance(aidlc_mode, dict):
        lines.extend(["", "## AIDLC mode", "", f"- Selected mode: `{aidlc_mode.get('mode')}`", f"- Selection: `{aidlc_mode.get('selection')}`", f"- State: `{aidlc_mode.get('state')}`", f"- Boundary: {aidlc_mode.get('boundary')}"])
        escalation = aidlc_mode.get("full_escalation", {})
        if isinstance(escalation, dict): lines.append(f"- Full escalation: `{escalation.get('state')}` - {display_prose(escalation.get('reason'))}")
        if aidlc_mode.get("mode") in {"standard", "full"}:
            lines.append("- Official stage: verified official Requirements Analysis rules govern these questions; the host generates them and TailTrail validates/imports approved decisions before freezing the anchor.")
    mode_features = report.get("aidlc_mode_features", {})
    if isinstance(mode_features, dict):
        lines.extend(["", "## AIDLC mode features", "", "| Included | Not included in this mode |", "| --- | --- |"])
        included = mode_features.get("included", []); excluded = mode_features.get("not_included", [])
        for index in range(max(len(included), len(excluded))):
            left = included[index] if index < len(included) else ""
            right = excluded[index] if index < len(excluded) else ""
            lines.append(f"| {left} | {right} |")
    selected = [item for item in delivery.get("selected", []) if isinstance(item, dict)]
    feature_rows = [("Navigator", "Planning now", "created this scoped Planning Lock and approval gate")]
    if any("Code Review Graph" in str(item.get("reason", "")) for item in impacted):
        feature_rows.append(("Code Review Graph Lite", "Planning now", "identified likely callers and focused validation context"))
    feature_rows.extend((str(item.get("name", "TailTrail control")), "After approval", str(item.get("why", "Selected for this task."))) for item in selected)
    if feature_rows:
        lines.extend(["", "## Selected TailTrail features", "", "| Feature | When | Used for this task |", "| --- | --- | --- |"])
        for name, when, why in feature_rows:
            lines.append(f"| {name} | {when} | {why} |")
    lines.extend(architecture_planning.markdown_lines(report.get("architecture_plan", {}), detailed=False))
    lines.extend(behaviour_planning.markdown_lines(report.get("behaviour_plan", {}), detailed=False))
    lines.extend(maintainability_planning.markdown_lines(report.get("maintainability_plan", {}), detailed=False))
    lines.extend(ui_planning.markdown_lines(report.get("ui_plan", {}), detailed=False))
    lines.extend(["", "## Plan", ""])
    if hands_free_program:
        lines.append("- Proposed dependency order:")
        for index, stage in enumerate(hands_free_program["dependency_order"], start=1):
            lines.append(f"  {index}. {stage}")
        lines.append(f"- First active slice: {hands_free_program['first_active_slice']}")
        lines.append(f"- Program approval gate: {hands_free_program['approval_gate']}")
    else:
        if len(requirement_rows) > 1:
            lines.append("- Confirm dependency order and select the first active requirement.")
            lines.append("- Implement one approved requirement row at a time; map changed scope and focused proof to the same `REQ-*` ID before advancing.")
            lines.append("- Reconcile every requirement row, preservation rule, evidence result, and unresolved drift in the Completion Report.")
        elif report.get("ui_consistency", {}).get("selected"):
            lines.append("- Inspect the existing UI system and nearest comparable screen before changing the requested UI.")
            lines.append(f"- UI discovery: `{report['ui_consistency']['command']}`")
            lines.append(f"- Preserve: {report['ui_consistency']['boundary']}")
        else:
            lines.append("- Inspect the target, its focused test, and the likely caller.")
        if len(requirement_rows) <= 1:
            lines.append("- Make the smallest change within the listed scope.")
            lines.append("- Run focused proof, then review the changed scope.")
    validation_rows = focused_validation_plan(root, impacted, requirement_rows, str(report["command_prefix"]))
    lines.extend(["", "## Focused validation", ""])
    lines.extend(["| Tier | Candidate | Status / command |", "| --- | --- | --- |"])
    for item in validation_rows:
        detail = f"`{item['command']}`" if item["command"] else item["status"]
        lines.append(f"| {item['tier']} | `{item['candidate']}` | {detail} |")
    token = report["token_posture"]
    lines.extend(
        [
            "",
            "## Token posture",
            "",
            f"- Estimated focused context: approximately `{token['used_tokens']}` tokens (local file-size estimate).",
            f"- Estimated baseline context: approximately `{token['baseline_tokens']}` tokens; avoided context: approximately `{token['avoided_tokens']}` tokens.",
            f"- Estimated context reduction: `{token['estimated_reduction_percent']}%`.",
            "- Actual model tokens: recorded in the Completion Report only when host/provider telemetry is linked to this run ID.",
        ]
    )
    lines.extend(["", "## Approval", ""])
    if isinstance(aidlc, dict) and aidlc.get("state") == "official-aidlc-host-generation-required":
        lines.append("- The official Requirements Analysis questions must be generated, answered, and explicitly approved before TailTrail can freeze the anchor or begin implementation.")
    else:
        lines.append("- Approve this AIDLC-backed plan to accept its recommendations and begin implementation, or reject it for deeper AIDLC refinement." if isinstance(aidlc, dict) else "- Approve this plan to begin implementation, or name any file/scope change before approval.")
    if delivery.get("hands_free_program"):
        lines.append("- This is a hands-free request; approve the proposed program slices before implementation begins.")
    if report.get("ui_plan", {}).get("surface_status") == "not-discovered":
        lines.append("- UI scope must be confirmed before implementation approval; TailTrail will not treat backend candidates as the missing UI surface.")
    lines.extend(["", "_Run with `--verbose` for advanced harness, token, code-intelligence, recovery, and product-metrics detail._", ""])
    return "\n".join(lines)


def verbose_start_report(report: dict[str, Any]) -> str:
    """Render a detailed but bounded Start report that chat hosts can reproduce."""
    plan = report["navigator"]
    delivery = report["guided_delivery"]
    lock = report.get("planning_lock")
    root = Path(str(report["root"]))
    impacted = [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)]
    selected = [item for item in delivery.get("selected", []) if isinstance(item, dict)]
    deferred = [item for item in delivery.get("activated_later", []) if isinstance(item, dict)]
    goal = display_prose(report["goal"])
    lowered_goal = goal.lower()
    code_intel = report["code_intelligence"]
    token = report["token_posture"]
    review = report["review_posture"]
    lines = ["# TailTrail Start Report", "", "Navigator-first plan. Review or edit this before implementation.", ""]
    lines.extend(["## Planning Lock", ""])
    if lock:
        lines.extend(
            [
                f"- Run ID: `{lock['run_id']}`",
                f"- Target identity: `{lock.get('target_identity', {}).get('fingerprint', 'legacy lock')}`.",
                f"- State: **{lock['status']}**; managed writes allowed: **{str(lock['writes_allowed']).lower()}**.",
                "- No source files, tests, scanners, or Git changes were run.",
            ]
        )
        host = lock.get("host_workspace")
        if isinstance(host, dict) and host.get("host"):
            lines.append(f"- Host workspace: `{host.get('host')}` / `{host.get('status')}` ({host.get('mapping', 'not-mapped')}).")
        policy = lock.get("enterprise_policy")
        if isinstance(policy, dict):
            lines.append(f"- Enterprise target policy: `{policy.get('status', 'not-configured')}`.")
    else:
        lines.append("- No persisted Planning Lock is attached to this rendered report.")
    workflow_runtime = report.get("workflow_runtime", {})
    if isinstance(workflow_runtime, dict) and workflow_runtime.get("enabled"):
        lines.extend(["", "## Workflow runtime", "", f"- Draft workflow ID: `{workflow_runtime.get('workflow_id')}`.", "- Boundary: this remains a report-only draft until the exact Planning Lock is approved; no workflow artifact or stage execution has occurred."])
    lines.extend(["", "## Start Here", "", "- Review the scope, selected controls, and proof before approval.", "- Nothing in this report implements the task.", "", "## Goal", "", f"- {goal}", "", "## Navigator Decision", ""])
    lines.extend(
        [
            "- Workflow: " + " -> ".join(plan.get("recommended_workflow", [])),
            "- Task types: " + ", ".join(plan.get("task_types", [])),
            "- Risks: " + (", ".join(plan.get("risk_indicators", [])) if plan.get("risk_indicators") else "none detected"),
            f"- Post-change review: {'selected' if review['selected'] else 'available'} for `{review['scope']}`.",
            "",
            "## Scope",
            "",
            "| Path | Planning evidence |",
            "| --- | --- |",
        ]
    )
    target = report.get("target_root")
    if isinstance(target, dict) and target.get("requested"):
        lines.append(f"| Target repository | `{target['requested']}` ({target.get('status', 'verified')}) |")
    # Verbose is the escape hatch for compact Start output. Never repeat a
    # compact-mode truncation hint here: show every discovered file instead.
    for item in impacted:
        lines.append(f"| `{item.get('path')}` | {display_prose(item.get('reason'))} |")
    if not impacted:
        if report.get("ui_plan", {}).get("selected"):
            lines.append("| UI surface not discovered | Confirm the frontend/UI root or approve bounded read-only UI discovery. Backend files were not substituted as UI scope. |")
        else:
            lines.append("| Scope unresolved | Add `--changed path/to/file` or approve read-only discovery. Unrelated Git changes were not used. |")
    roles = report.get("input_roles", {})
    if isinstance(roles, dict):
        lines.extend(["", "## Input roles", "", "| Input | Role | Access | Status |", "| --- | --- | --- | --- |"])
        for item in roles.get("inputs", []):
            if isinstance(item, dict):
                lines.append(f"| `{item.get('locator')}` | {item.get('role')} | {item.get('access')} | {item.get('status')} |")
    lines.extend(["", "## Requirements", ""])
    hands_free_program = delivery.get("hands_free_program")
    spec_kit_source = report.get("spec_kit_source")
    requirement_rows = [item for item in plan.get("requirement_matrix", []) if isinstance(item, dict)]
    for item in requirement_rows:
        lines.append(f"- **{item.get('display_id', 'REQ')}:** {display_prose(item.get('statement', ''))}")
    if isinstance(spec_kit_source, dict):
        lines.append(f"- Source: `{spec_kit_source['feature_id']}` / `{spec_kit_source['source_revision']}` (imported snapshot v{spec_kit_source['snapshot_version']}).")
    if not requirement_rows:
        lines.append("- Implement the approved goal with the smallest maintainable change.")
    aidlc = report.get("aidlc_requirements")
    if isinstance(aidlc, dict):
        stage = aidlc.get("aidlc_stage", {})
        if aidlc.get("state") == "official-aidlc-host-generation-required":
            lines.extend(["", "## Official AIDLC requirements", "", "- The verified official Requirements Analysis stage is ready for the configured host.", "- The host must load the recorded official rules and saved Question Orchestrator context, then generate material questions with requirement traceability, options, TailTrail advisory recommendations, and evidence-grounded reasoning before implementation can be approved.", "- TailTrail validates grounding and persists that official stage artifact under this same run ID; it will not fabricate a local substitute questionnaire.", "", f"- Stage gate: {stage.get('stage_gate', '')}"])
        else:
            lines.extend(["", "## AIDLC requirements and recommendations", "", "### Assumptions", ""])
            lines.extend(f"- {item}" for item in stage.get("assumptions", []))
            lines.extend(["", "### Non-goals", ""])
            lines.extend(f"- {item}" for item in stage.get("non_goals", []))
            lines.extend(["", "### Questions", ""])
            for question in aidlc.get("questions", []):
                lines.extend([f"#### {question.get('id', 'Question')} - {display_prose(question.get('question', ''))}", f"- **Recommended:** {display_prose(question.get('recommended', ''))}", f"- **Reasoning:** {display_prose(question.get('reasoning', ''))}", ""])
            lines.extend(["", f"- Stage gate: {stage.get('stage_gate', '')}"])
    aidlc_mode = report.get("aidlc_mode", {})
    if isinstance(aidlc_mode, dict):
        lines.extend(["", "## AIDLC mode", "", f"- Selected mode: `{aidlc_mode.get('mode')}`", f"- Selection: `{aidlc_mode.get('selection')}`", f"- State: `{aidlc_mode.get('state')}`", f"- Boundary: {aidlc_mode.get('boundary')}"])
        escalation = aidlc_mode.get("full_escalation", {})
        if isinstance(escalation, dict): lines.append(f"- Full escalation: `{escalation.get('state')}` - {display_prose(escalation.get('reason'))}")
    mode_features = report.get("aidlc_mode_features", {})
    if isinstance(mode_features, dict):
        lines.extend(["", "## AIDLC mode features", "", "| Included | Not included in this mode |", "| --- | --- |"])
        included = mode_features.get("included", []); excluded = mode_features.get("not_included", [])
        for index in range(max(len(included), len(excluded))):
            left = included[index] if index < len(included) else ""
            right = excluded[index] if index < len(excluded) else ""
            lines.append(f"| {left} | {right} |")
    lines.extend(["", "## Selected TailTrail features", "", "| Feature | When | Why |", "| --- | --- | --- |", "| Navigator | Planning now | created this scoped Planning Lock and approval gate |"])
    if any("Code Review Graph" in str(item.get("reason", "")) for item in impacted):
        lines.append("| Code Review Graph Lite | Planning now | identified likely callers and focused validation context |")
    for item in selected:
        lines.append(f"| {item.get('name')} | After approval | {item.get('why')} |")
    lines.extend(architecture_planning.markdown_lines(report.get("architecture_plan", {}), detailed=True))
    lines.extend(behaviour_planning.markdown_lines(report.get("behaviour_plan", {}), detailed=True))
    lines.extend(maintainability_planning.markdown_lines(report.get("maintainability_plan", {}), detailed=True))
    lines.extend(ui_planning.markdown_lines(report.get("ui_plan", {}), detailed=True))
    lines.extend(["", "## Deferred TailTrail features", ""])
    for item in deferred:
        lines.append(f"- **{item.get('name')}:** {short_trigger(str(item.get('when', '')))}")
    lines.extend(["", "## Guided Delivery", "", f"- Mode: `{delivery['mode']}`", "- After approval:"])
    for index, stage in enumerate(delivery["stages"], start=1):
        lines.append(f"  {index}. {stage}")
    if hands_free_program:
        lines.append("- Program dependency order: " + " -> ".join(hands_free_program["dependency_order"]))
        lines.append(f"- First active slice: {hands_free_program['first_active_slice']}")
        lines.append(f"- Program approval gate: {hands_free_program['approval_gate']}")
    if report.get("ui_consistency", {}).get("selected"):
        lines.extend(["- UI discovery before implementation: `" + str(report["ui_consistency"]["command"]) + "`", "- UI preservation boundary: " + str(report["ui_consistency"]["boundary"])])
    lines.extend([f"- Boundary: {delivery['execution_boundary']}", "", "## Validation", ""])
    validation_rows = focused_validation_plan(root, impacted, requirement_rows, str(report["command_prefix"]))
    lines.extend(["| Tier | Candidate | Status / command |", "| --- | --- | --- |"])
    for item in validation_rows:
        detail = f"`{item['command']}`" if item["command"] else item["status"]
        lines.append(f"| {item['tier']} | `{item['candidate']}` | {detail} |")
    lines.append("- Tests and validation run only after approval.")
    lines.extend(["", "## Token estimate", "", f"- Estimated focused context: approximately `{token['used_tokens']}` tokens.", f"- Estimated baseline context: approximately `{token['baseline_tokens']}` tokens.", f"- Estimated avoided context: approximately `{token['avoided_tokens']}` tokens (`{token['estimated_reduction_percent']}%` reduction).", "- Evidence: local file-size estimate only; exact model/API usage requires linked provider telemetry.", "", "## Evidence posture", "", "- Code intelligence: local-only `lite`, `v1`, and `v2`; provider-backed V3 is not default.", "- Evidence: local estimate only; no exact token-savings claim.", "", "## Approval", ""])
    if isinstance(aidlc, dict) and aidlc.get("state") == "official-aidlc-host-generation-required":
        lines.append("- The official Requirements Analysis questions must be generated, answered, and explicitly approved before TailTrail can freeze the anchor or begin implementation.")
    else:
        lines.append("- Approve this plan to begin implementation, or name any file/scope change before approval.")
    if report.get("ui_plan", {}).get("surface_status") == "not-discovered":
        lines.append("- UI scope must be confirmed before implementation approval; TailTrail will not treat backend candidates as the missing UI surface.")
    return "\n".join(lines) + "\n"


def render_markdown(report: dict[str, Any], verbose: bool = False) -> str:
    if report.get("target_boundary"):
        return render_target_boundary_report(report)
    if report.get("target_fit_boundary"):
        return render_target_fit_boundary_report(report)
    if report.get("debug_plan"):
        return debug_start_report(report, verbose=verbose)
    plan = report["navigator"]
    lock = report.get("planning_lock")
    lock_lines = []
    if lock:
        lock_lines = [
            "## Planning Lock",
            "",
            f"- Run ID: `{lock['run_id']}`",
            f"- State: **{lock['status']}**; managed writes allowed: **{str(lock['writes_allowed']).lower()}**.",
            f"- Saved plan: `{report.get('planning_report', {}).get('artifact', 'saved with this run')}`.",
            "- Source edits, Git mutations, Terraform/Sonar execution, scanners, and managed patch application are blocked until a separate approval.",
            f"- Approve and activate this exact plan later: `{report['command_prefix']} planning activate --root . --run-id {lock['run_id']} --approved`",
            "",
        ]
    if plan.get("navigator_request", {}).get("explicit"):
        # An explicit Navigator invocation already has a concise decision and
        # separate approval gate. Do not bury it in the broader Start report.
        return "\n".join(lock_lines) + navigator.markdown(plan)
    if verbose:
        return verbose_start_report(report)
    token = report["token_posture"]
    learning = report["learning_quality"]
    setup = report["setup_posture"]
    review = report["review_posture"]
    harness = report["harness_posture"]
    bootstrap = report["bootstrap_posture"]
    evaluation = report["evaluation_posture"]
    code_intel = report["code_intelligence"]
    delivery = report["guided_delivery"]
    hands_free_program = delivery.get("hands_free_program")
    run_signals = delivery["run_signals"]
    selected = plan.get("selected_features", [])
    skipped = plan.get("skipped_features", [])
    actions = report.get("next_actions", [])
    if not verbose:
        return compact_start_report(report)
    lines = [
        "# TailTrail Start Report",
        "",
        "Navigator-first plan. Review or edit this before implementation.",
        "",
        *lock_lines,
        "## Start Here",
        "",
        f"- Next step: {report['next_step']}",
        "- Nothing has been implemented, scanned, captured, learned, or changed by this report.",
        f"- Post-change review: {'selected' if review['selected'] else 'available'} for `{review['scope']}`.",
        f"- Bootstrap Snapshot: `{bootstrap['status']}`.",
        "- Meta-Harness: available after work to review TailTrail behavior and metric confidence.",
        f"- Evaluation Harness: {'selected' if evaluation['selected'] else 'available'} for deterministic proof scenarios.",
        "- The guided delivery sequence below is the default path after approval; advanced harnesses activate only when their trigger occurs.",
        "",
        "## Guided Delivery",
        "",
        f"- Mode: `{delivery['mode']}`",
        "- After approval: " + " -> ".join(delivery["stages"]),
        "- Selected controls: " + ", ".join(item["name"] for item in delivery["selected"]),
        f"- Run evidence: `{run_signals['status']}`" + (f" for `{run_signals['run_id']}`" if run_signals["run_id"] else "; no prior-run state was inferred."),
        f"- Boundary: {delivery['execution_boundary']}",
        "- Approval: `" + delivery["approval_prompt"] + "`",
        "",
        "## Goal",
        "",
        f"- {display_prose(report['goal'])}",
        "",
        "## Navigator Decision",
        "",
        "- Workflow: " + " -> ".join(plan.get("recommended_workflow", [])),
        "- Task types: " + ", ".join(plan.get("task_types", [])),
        "- Risks: " + (", ".join(plan.get("risk_indicators", [])) if plan.get("risk_indicators") else "none detected"),
        f"- Likely impacted files: `{len(plan.get('likely_impacted_files', []))}`",
        "",
        "## Selected TailTrail features",
        "",
        "| Feature | When | Why |",
        "| --- | --- | --- |",
        "| Navigator | Planning now | created this scoped Planning Lock and approval gate |",
        *[f"| {item['name']} | After approval | {item['why']} |" for item in delivery["selected"]],
        "",
        "## Deferred TailTrail features",
        "",
        "| Feature | Activates when |",
        "| --- | --- |",
        *[f"| {item['name']} | {item['when']} |" for item in delivery["activated_later"]],
        "",
        "## Recommended Path",
        "",
        "- Workflow: " + " -> ".join(plan.get("recommended_workflow", [])),
        "- Task types: " + ", ".join(plan.get("task_types", [])),
        "- Risks: " + (", ".join(plan.get("risk_indicators", [])) if plan.get("risk_indicators") else "none detected"),
        f"- Impacted files: `{len(plan.get('likely_impacted_files', []))}`",
        f"- Selected features: `{', '.join(item['name'] for item in selected[:5]) if selected else 'none'}`",
    ]

    spec_kit_source = report.get("spec_kit_source")
    if isinstance(spec_kit_source, dict):
        lines.extend(["", "## Intent Bridge requirement source", "", f"- Feature: `{spec_kit_source['feature_id']}`", f"- Source revision: `{spec_kit_source['source_revision']}`", f"- Imported snapshot: `{spec_kit_source['import']}`", f"- Imported requirements: `{len(spec_kit_source['requirements'])}`; stories: `{len(spec_kit_source['stories'])}`; tasks: `{len(spec_kit_source['tasks'])}`.", f"- Boundary: {spec_kit_source['boundary']}"])

    if hands_free_program:
        lines.extend(
            [
                "",
                "## Hands-Free Program Plan",
                "",
                "- Status: `proposed`; no implementation slice is active yet.",
                "- Feature requirements: " + "; ".join(f"{item['display_id']} {item['statement']}" for item in hands_free_program["feature_requirements"]),
                "- Proposed dependency order: " + " -> ".join(hands_free_program["dependency_order"]),
                f"- First active slice: {hands_free_program['first_active_slice']}",
                f"- Approval gate: {hands_free_program['approval_gate']}",
            ]
        )

    if len(selected) > 5:
        lines.append(f"- More selected features: `{len(selected) - 5}` hidden in compact view; use `--verbose` for full detail.")
    if skipped:
        lines.append(f"- Skipped features: `{len(skipped)}` hidden in compact view.")
    if delivery["activated_later"]:
        lines.append("- Activates later: " + "; ".join(f"{item['name']} ({item['when']})" for item in delivery["activated_later"][:3]))
    if plan.get("scan_approval"):
        lines.append("- Scan approval: required before any broad scanner, audit, build, or vulnerability command.")

    impacted = plan.get("likely_impacted_files", [])
    if impacted:
        lines.extend(["", "## Files To Inspect First", ""])
        for item in impacted[:6]:
            if isinstance(item, dict):
                lines.append(f"- `{item.get('path')}`: {item.get('reason')}")
        if len(impacted) > 6:
            lines.append(f"- ...and `{len(impacted) - 6}` more in verbose Navigator output.")

    commands = plan.get("suggested_commands", [])
    lines.extend(["", "## Validation", ""])
    for command in commands[:5]:
        lines.append(f"- `{command}`")
    lines.extend(
        [
            f"- Review after implementation: `{review['command']}`",
            f"- Meta-Harness quick check: `{harness['command']}`",
            f"- Meta-Harness confidence: `{harness['confidence_command']}`",
        ]
    )
    if bootstrap["command"] not in commands[:5]:
        lines.append(f"- Bootstrap Snapshot: `{bootstrap['command']}`")
    if evaluation["selected"]:
        lines.extend(
            [
                f"- Evaluation scenarios: `{evaluation['list_command']}`",
                f"- Evaluation run: `{evaluation['run_command']}`",
                f"- Evaluation report: `{evaluation['report_command']}`",
            ]
        )
    if len(commands) > 5:
        lines.append(f"- ...and `{len(commands) - 5}` more suggested command(s) in verbose view.")

    lines.extend(
        [
            "",
            "## Code Intelligence",
            "",
            "- Default engine path: local-only `lite`, `v1`, and `v2`.",
            "- `lite`: fast selected-file symbols.",
            "- `v1`: normal local impact map before edits.",
            "- `v2`: richer local semantic metadata when V1 is not enough.",
            "- `v3`: provider-backed metadata only; never default.",
            f"- V3 rule: {code_intel['v3_rule']}",
            f"- Navigator rule: {code_intel['navigator_rule']}",
            f"- Auto-run rule: {code_intel['auto_run_rule']}",
            f"- Local example: `{code_intel['default_command']}`",
            f"- V3 example: `{code_intel['v3_command']}`",
            "",
            "## Evidence posture",
            "",
            f"- Approx focused tokens: `{token['used_tokens']}`",
            f"- Approx avoided tokens: `{token['avoided_tokens']}`",
            f"- Approx reduction: `{token['estimated_reduction_percent']}%`",
            "- Evidence: local estimate only; exact savings require model/API telemetry.",
            f"- Learning review: `{'recommended' if learning['review_recommended'] else 'not needed now'}` ({learning['review_reason']})",
            f"- Setup check: `{setup['recommended_check']}`",
        ]
    )
    if evaluation["selected"]:
        lines.extend(
            [
                "",
                "## Evaluation Harness",
                "",
                f"- Selected: `true` ({evaluation['reason']})",
                f"- Scenario: `{evaluation['scenario']}`",
                f"- Run: `{evaluation['run_command']}`",
                f"- Report: `{evaluation['report_command']}`",
                f"- Write report: `{evaluation['write_report_command']}`",
                f"- Rule: {evaluation['rule']}",
            ]
        )

    lines.extend(
        [
            "",
            "## After Implementation",
            "",
            f"- Review: {review['rule']}",
            f"- Review prompt: `{review['prompt']}`",
            f"- Meta-Harness: {harness['rule']}",
            f"- Shared metadata dry run: `{harness['shared_dry_run_command']}`",
            f"- Shared metadata status: `{harness['shared_status_command']}`",
            f"- Bootstrap Snapshot: {bootstrap['rule']}",
            f"- Evaluation Harness: {evaluation['rule']}",
            "- Learning capture remains approval-only after outcome is known.",
        ]
    )

    lines.extend(["", "## Approval", ""])
    for item in actions[:4]:
        lines.extend(
            [
                f"- {item['label']} `{item['prompt']}`",
            ]
        )
    if len(actions) > 4:
        lines.append(f"- Additional approval options hidden in compact view: `{len(actions) - 4}`.")

    lines.extend(
        [
        "",
        "## Decision Menu",
        "",
        ]
    )
    for item in actions:
        lines.extend(
            [
                f"### {item['label']}",
                "",
                f"- When: {item['when']}",
                f"- Prompt: `{item['prompt']}`",
                "",
            ]
        )
    lines.extend([f"For a lean next-step reminder later, run: `{report.get('command_prefix', 'python3 scripts/tailtrail.py')} next`.", ""])
    lines.extend(
        [
        "",
        "## Goal",
        "",
        f"- {display_prose(report['goal'])}",
        "",
            "## Navigator Summary",
        "",
        "- Workflow: " + " -> ".join(plan.get("recommended_workflow", [])),
        "- Task types: " + ", ".join(plan.get("task_types", [])),
        "- Risks: " + (", ".join(plan.get("risk_indicators", [])) if plan.get("risk_indicators") else "none detected"),
        f"- Selected features: `{len(selected)}`",
        f"- Skipped features: `{len(skipped)}`",
        f"- Likely impacted files: `{len(plan.get('likely_impacted_files', []))}`",
        "",
        "Top selected features:",
        ]
    )
    lines.extend(["", "## Guided Delivery Details", ""])
    lines.extend(f"- {item['name']}: {item['why']}" for item in delivery["selected"])
    lines.extend(f"- Later - {item['name']}: {display_prose(item['when'])}" for item in delivery["activated_later"])
    if run_signals.get("evidence"):
        lines.append("- Run evidence pointers: " + ", ".join(f"`{item}`" for item in run_signals["evidence"]))
    for item in selected[:6]:
        lines.append(f"- {item['name']}: {item['reason']}")
    if plan.get("scan_approval"):
        lines.extend(
            [
                "",
                "Scan approval is required before running broad quality, Sonar, vulnerability, audit, test, or build commands.",
            ]
        )
    lines.extend(
        [
            "",
            "## Token Posture",
            "",
            f"- Mode: `{token['mode']}`",
            f"- Approx baseline tokens: `{token['baseline_tokens']}`",
            f"- Approx TailTrail focused tokens: `{token['used_tokens']}`",
            f"- Approx saved tokens: `{token['estimated_saved_tokens']}`",
            f"- Approx reduction: `{token['estimated_reduction_percent']}%`",
            f"- Evidence: {token['evidence']}",
        ]
    )
    if token["used_files"]:
        lines.append("- Used file estimates:")
        lines.extend(f"  - `{item['path']}`: ~{item['approx_tokens']} tokens" for item in token["used_files"][:8])
    if token["avoided_files"]:
        lines.append("- Avoided broad context estimates:")
        lines.extend(f"  - `{item['path']}`: ~{item['approx_tokens']} tokens" for item in token["avoided_files"][:8])
    lines.extend(
        [
            "",
            "## Guarded Learning Quality",
            "",
            f"- Learning index exists: `{learning['index_exists']}`",
            f"- Learning events exist: `{learning['events_exist']}`",
            f"- Refresh actions exist: `{learning['refresh_actions_exist']}`",
            f"- Refresh action count: `{learning['refresh_action_count']}`",
            f"- Blocking refresh actions: `{learning['blocking_refresh_actions']}`",
            f"- Surfaced matches: `{learning['surfaced_matches']}`",
            f"- Learning approval required: `{learning['approval_required']}`",
            f"- Learning review recommended: `{learning['review_recommended']}`",
            f"- Learning review reason: {learning['review_reason']}",
            f"- Learning review command: `{learning['review_command']}`",
            f"- Rule: {learning['rule']}",
            "",
            "## Evaluation Harness Details",
            "",
            f"- Selected: `{evaluation['selected']}`",
            f"- Reason: {evaluation['reason']}",
            f"- Scenario: `{evaluation['scenario']}`",
            f"- List scenarios: `{evaluation['list_command']}`",
            f"- Run scenario: `{evaluation['run_command']}`",
            f"- Report scenario: `{evaluation['report_command']}`",
            f"- Write approved report: `{evaluation['write_report_command']}`",
            f"- Normalize scenario event dry run: `{evaluation['normalize_command']}`",
            f"- Rule: {evaluation['rule']}",
            "",
            "## Install And Update Posture",
            "",
            f"- Source checkout: `{setup['source_checkout']}`",
            f"- Installed pack detected in target root: `{setup['installed_pack_detected']}`",
            f"- Recommended check: `{setup['recommended_check']}`",
            f"- Recommended update check: `{setup['recommended_update_check']}`",
            f"- Note: {setup['note']}",
            "",
            "## Next Step",
            "",
            f"- {report['next_step']}",
            "- Recommended default: approve only after editing any incorrect feature, file, command, scan, or learning choice.",
            "",
            "## Code Intelligence Details",
            "",
            f"- Default: `{code_intel['default']}`",
            "- Default engine path: " + ", ".join(f"`{item}`" for item in code_intel["default_engine_path"]),
            f"- V1/default command: `{code_intel['default_command']}`",
            f"- V2 command: `{code_intel['v2_command']}`",
            f"- V3 command: `{code_intel['v3_command']}`",
            f"- V3 rule: {code_intel['v3_rule']}",
            f"- Navigator rule: {code_intel['navigator_rule']}",
            f"- Auto-run rule: {code_intel['auto_run_rule']}",
            f"- Evidence rule: {code_intel['evidence_rule']}",
        ]
    )
    for level in code_intel["levels"]:
        lines.append(f"- `{level['name']}`: {level['meaning']} When: {level['when']}")
    lines.extend(
        [
            "",
            "## Full Navigator Plan",
            "",
            navigator.markdown(plan).rstrip(),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Start a TailTrail task with Navigator-first plan, metrics, setup posture, and learning quality.")
    parser.add_argument("goal", nargs="*", help="User goal or task description.")
    parser.add_argument("--root", type=Path, default=None, help="Project root to inspect. Overrides a target repository explicitly named in the goal.")
    parser.add_argument("--host", choices=("codex", "copilot", "claude"), help="Optional host supplying the active workspace identity.")
    parser.add_argument("--host-workspace", help="Workspace path reported by the selected host. It overrides a prompt path but never an explicit --root.")
    parser.add_argument("--host-platform", choices=("auto", "windows", "macos", "linux", "wsl", "container"), default="auto", help="Platform shape of --host-workspace for safe local mapping.")
    parser.add_argument("--enterprise-policy", type=Path, help="Optional local enterprise target policy JSON. Enforced before repository discovery.")
    parser.add_argument("--target-alias", help="Optional target alias from the supplied enterprise target policy.")
    parser.add_argument("--actor", help="Optional declared actor label for a policy that requires target ownership. This is not authentication.")
    parser.add_argument("--changed", action="append", default=[], help="Changed or target file path. Repeat for multiple files.")
    workflow_group = parser.add_mutually_exclusive_group()
    workflow_group.add_argument("--debug", action="store_true", help="Force Navigator to classify this Start run as a debug investigation.")
    workflow_group.add_argument("--build", action="store_true", help="Force Navigator to classify this Start run as a normal build workflow.")
    parser.add_argument("--error", help="Declare that a failure artifact is available. The path/content is not copied into the DI-2 plan.")
    parser.add_argument("--command", dest="reproduction_command", help="Declare that a reproduction command is available. Its content is not copied into the DI-2 plan.")
    parser.add_argument("--run-id", help="Optional exact TailTrail run ID. Enables evidence-driven correction and recovery routing for that run only.")
    parser.add_argument("--planning-run-id", help="Optional new Planning Lock run ID. Defaults to a generated run ID.")
    parser.add_argument("--reference-root", action="append", default=[], help="Read-only reference repository path for this plan. Repeat for multiple references.")
    parser.add_argument("--related-repo", action="append", default=[], help="Read-only sibling/related repository path. Repeat as needed.")
    parser.add_argument("--design-reference", action="append", default=[], help="Read-only local or external design reference. Repeat as needed.")
    parser.add_argument("--requirement-artifact", action="append", default=[], help="Read-only local requirement/specification artifact. Repeat as needed.")
    parser.add_argument("--evidence-artifact", action="append", default=[], help="Read-only local CI, scan, or validation artifact. Repeat as needed.")
    parser.add_argument("--aidlc", choices=("lite", "standard", "medium", "full", "off"), default=None, help="Optional AIDLC override. Without it: normal Start uses Lite, 'using AIDLC' uses Standard, hands-free uses Standard with eligible Full escalation, and full/official wording requires Full.")
    parser.add_argument("--official-aidlc-manifest", help="Optional in-root official AIDLC compatibility manifest used only with --aidlc full.")
    parser.add_argument("--official-intent-id", help="Optional official AIDLC intent identity to map to this TailTrail run in full mode.")
    parser.add_argument("--official-session-id", help="Optional official AIDLC host session identity to map to this TailTrail run in full mode.")
    parser.add_argument("--official-stage", choices=("requirements", "design", "implementation", "build-and-test", "handoff", "operations"), default="requirements", help="Initial official AIDLC stage identity for full mode.")
    parser.add_argument("--intent-feature", "--spec-kit-feature", dest="spec_kit_feature", help="Explicitly use one already-imported Intent Bridge feature as the authoritative requirement source for this Planning Lock.")
    parser.add_argument("--no-planning-lock", action="store_true", help="Advanced compatibility escape hatch; does not create the local planning artifact.")
    parser.add_argument("--no-workflow", action="store_true", help="Compatibility escape hatch; keep this Start run outside the DWR workflow runtime.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--command-prefix", default="python3 scripts/tailtrail.py", help="Command prefix to show in suggested commands.")
    parser.add_argument("--verbose", action="store_true", help="Include full decision menu, posture details, and Navigator output.")
    args = parser.parse_args()

    goal = " ".join(args.goal).strip()
    if not goal:
        parser.error("goal is required")
    try:
        loaded_policy = enterprise_target_policy.load(args.enterprise_policy)
        policy_aliases = enterprise_target_policy.aliases(loaded_policy)
        if args.host_workspace and not args.host:
            parser.error("--host-workspace requires --host codex, copilot, or claude")
        host_resolution = host_workspace_adapter.resolve(args.host or "codex", args.host_workspace, host_platform=args.host_platform) if args.host else None
        if args.root is None and isinstance(host_resolution, dict) and host_resolution.get("status") not in {"verified", "not-provided"}:
            report = target_boundary_report(goal, host_resolution, args.command_prefix)
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True, default=str))
            else:
                print(render_markdown(report, verbose=args.verbose), end="")
            return 2
        host_root = Path(str(host_resolution["root"])) if isinstance(host_resolution, dict) and host_resolution.get("status") == "verified" else None
        target = resolve_target_root(goal, args.root, host_root, args.target_alias, policy_aliases)
        if target["status"] != "verified":
            report = target_boundary_report(goal, target, args.command_prefix)
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True, default=str))
            else:
                print(render_markdown(report, verbose=args.verbose), end="")
            return 2
        root = target["root"]
        applied_alias = args.target_alias if target.get("source") == "alias" else None
        policy_result = enterprise_target_policy.evaluate(root, loaded_policy, actor=args.actor, selected_alias=applied_alias)
        if policy_result["blocking"]:
            report = target_boundary_report(goal, {"requested": root.as_posix(), "status": "blocked", "source": "enterprise-policy", "reason": "; ".join(policy_result["issues"])}, args.command_prefix)
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True, default=str))
            else:
                print(render_markdown(report, verbose=args.verbose), end="")
            return 2
        requested_spec_kit_feature = args.spec_kit_feature or spec_kit_bridge.feature_from_goal(goal)
        intent_requested = "intent bridge" in goal.lower() or "spec kit" in goal.lower()
        if intent_requested and not requested_spec_kit_feature:
            parser.error("Select an imported Intent Bridge feature with --intent-feature <feature>; TailTrail will not guess or auto-import a requirement source.")
        workflow_override = "debug" if args.debug else "build" if args.build else None
        report = build_report(
            goal,
            root,
            args.changed,
            args.command_prefix,
            args.run_id,
            args.aidlc or "",
            args.official_aidlc_manifest,
            requested_spec_kit_feature,
            workflow_override,
            bool(args.error),
            bool(args.reproduction_command),
        )
        report["target_root"] = {key: value for key, value in target.items() if key != "root"}
        fit = target_workspace.assess_plan_fit(
            goal,
            root,
            report.get("navigator", {}).get("likely_impacted_files", []),
            resolution_source=str(target.get("source", "unknown")),
            changed=args.changed,
        )
        report["target_fit"] = fit
        if fit["blocking"]:
            boundary = target_fit_boundary_report(goal, root, fit, args.command_prefix, report)
            if args.format == "json":
                print(json.dumps(boundary, indent=2, sort_keys=True, default=str))
            else:
                print(render_markdown(boundary, verbose=args.verbose), end="")
            return 2
        if isinstance(host_resolution, dict):
            report["host_workspace"] = {key: value for key, value in host_resolution.items() if key != "root"}
        report["enterprise_policy"] = policy_result
        report["input_roles"] = target_workspace.input_roles(root, reference_roots=args.reference_root, related_repos=args.related_repo, design_references=args.design_reference, requirement_artifacts=args.requirement_artifact, evidence_artifacts=args.evidence_artifact)
        effective_aidlc_mode = report["aidlc_mode"]["mode"]
        if not args.no_planning_lock:
            report["planning_lock"] = planning_lock.create(root, goal, args.planning_run_id, args.reference_root, input_roles=report["input_roles"], host_workspace=host_resolution, enterprise_policy=policy_result)
            report["workflow_runtime"] = workflow_start_integration.draft(
                report,
                report["planning_lock"]["run_id"],
                disabled=args.no_workflow or bool(report.get("debug_plan")),
            )
            if report.get("debug_plan") and not args.no_workflow:
                report["workflow_runtime"] = {
                    "enabled": False,
                    "state": "deferred-to-di-4",
                    "reason": "The canonical debug-investigation DWR template is introduced in DI-4.",
                    "boundary": "DI-2 creates only the canonical Planning Lock and saved Debug Start report.",
                }
            report["target_resolution_receipt"] = enterprise_target_policy.receipt(root, report["planning_lock"]["run_id"], target_identity=report["planning_lock"]["target_identity"], input_roles=report["input_roles"], policy_result=policy_result, host_workspace=host_resolution)
            if effective_aidlc_mode in {"standard", "full"}:
                report["official_aidlc_bridge"] = official_aidlc_bridge.create(
                    root, report["planning_lock"]["run_id"], goal,
                    manifest=args.official_aidlc_manifest,
                    official_intent_id=args.official_intent_id,
                    official_session_id=args.official_session_id,
                    official_stage=args.official_stage,
                    mode=effective_aidlc_mode,
                )
            report["planning_report"] = planning_lock.save_start_report(root, report["planning_lock"]["run_id"], report)
            selected = report.get("navigator", {}).get("selected_features", [])
            if effective_aidlc_mode == "standard" and not report.get("spec_kit_source"):
                report["aidlc_requirements"] = planning_lock.request_official_aidlc_requirements(root, report["planning_lock"]["run_id"])
                report["planning_report"] = planning_lock.enrich_start_report(root, report["planning_lock"]["run_id"], report)
            elif effective_aidlc_mode == "standard" and report.get("spec_kit_source"):
                report["aidlc_requirements"] = {"state": "not-run", "reason": "Imported Intent Bridge requirements are the authoritative boundary; TailTrail must not generate a parallel requirement questionnaire."}
                report["planning_report"] = planning_lock.enrich_start_report(root, report["planning_lock"]["run_id"], report)
            elif effective_aidlc_mode == "full":
                report["aidlc_requirements"] = planning_lock.request_official_aidlc_requirements(root, report["planning_lock"]["run_id"])
                report["planning_report"] = planning_lock.enrich_start_report(root, report["planning_lock"]["run_id"], report)
        elif args.no_workflow:
            report["workflow_runtime"] = workflow_start_integration.draft(report, "not-persisted", disabled=True)
    except ValueError as error:
        parser.error(str(error))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report, verbose=args.verbose), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
