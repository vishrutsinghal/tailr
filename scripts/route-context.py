#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / ".tailtrail" / "token-router-state.json"


@dataclass(frozen=True)
class Route:
    name: str
    lane: str
    supporting_lane: str | None
    slice: str
    load: list[str]
    avoid: list[str]
    exactness_risk: str
    exact_text: bool
    reason: str
    fallback: str


ROUTES: dict[str, Route] = {
    "core": Route(
        name="core",
        lane="text-slice",
        supporting_lane=None,
        slice="core",
        load=["AGENTS.md", "skills/tailtrail/SKILL.md", "tailtrail-policy.md when present", "GUARDRAILS.md behavior contract", "context/guardrail-layers.md implementation and code consistency layers for non-trivial or risky work", "exact relevant source files"],
        avoid=["DESIGN.md", "ROADMAP.md", "examples/"],
        exactness_risk="high",
        exact_text=True,
        reason="Normal code work needs compact TailTrail guidance plus exact source.",
        fallback="Use project-map if the relevant source path is unclear.",
    ),
    "review": Route(
        name="review",
        lane="text-slice",
        supporting_lane="context-map",
        slice="review",
        load=["skills/tailtrail-review/SKILL.md", "tailtrail-policy.md when present", "GUARDRAILS.md behavior contract", "context/guardrail-layers.md review and code consistency layers", "context/change-impact.md", "exact diff or changed files"],
        avoid=["examples/", "ROADMAP.md", "DESIGN.md", "broad repo scans"],
        exactness_risk="high",
        exact_text=True,
        reason="Review work needs exact changed text and a small impact frame.",
        fallback="Load one likely caller or focused test if impact is unclear.",
    ),
    "dependency": Route(
        name="dependency",
        lane="text-slice",
        supporting_lane=None,
        slice="core",
        load=["AGENTS.md", "skills/tailtrail/SKILL.md", "tailtrail-policy.md when present", "DEPENDENCY-GATE.md", "GUARDRAILS.md behavior contract", "context/guardrail-layers.md dependency layer", "dependency manifest snippets"],
        avoid=["broad docs", "unrelated source", "all examples"],
        exactness_risk="high",
        exact_text=True,
        reason="Dependency choices depend on exact package names, versions, and existing capabilities.",
        fallback="Load DEPENDENCY-GATE.md or the local dependency policy when dependency ownership is unclear.",
    ),
    "aidlc": Route(
        name="aidlc",
        lane="text-slice",
        supporting_lane="reuse-cache",
        slice="aidlc",
        load=["AIDLC.md", "tailtrail-policy.md when present", "GUARDRAILS.md behavior contract", "context/guardrail-layers.md AIDLC layer", "aidlc/stages/README.md", "active stage playbook", "templates/aidlc-state.md for new work", "aidlc-docs/aidlc-state.md when resuming"],
        avoid=["all lifecycle artifacts", "all templates", "old audit details unless needed"],
        exactness_risk="medium",
        exact_text=False,
        reason="Lifecycle work should load the active stage and state rather than every process file.",
        fallback="Use context-brief when the active lifecycle state is still too large.",
    ),
    "handoff": Route(
        name="handoff",
        lane="text-slice",
        supporting_lane="output-slicer",
        slice="aidlc",
        load=["aidlc/stages/handoff.md", "tailtrail-policy.md when present", "GUARDRAILS.md behavior contract", "context/guardrail-layers.md handoff layer", "templates/diff-handoff.md", "templates/validation-handoff.md", "exact changed files or validation output"],
        avoid=["all lifecycle artifacts", "raw full logs", "unrelated stage playbooks"],
        exactness_risk="high",
        exact_text=True,
        reason="Handoff needs compact summary plus exact changed or validation material available for review.",
        fallback="Load operations notes if deployment or production support is in scope.",
    ),
    "example": Route(
        name="example",
        lane="text-slice",
        supporting_lane=None,
        slice="examples",
        load=["one matching examples/*.md file"],
        avoid=["all examples", "ROADMAP.md", "DESIGN.md"],
        exactness_risk="low",
        exact_text=False,
        reason="Example calibration usually needs one matching example, not the whole set.",
        fallback="Use core slice if the example turns into implementation work.",
    ),
    "project-map": Route(
        name="project-map",
        lane="context-map",
        supporting_lane="text-slice",
        slice="project-map",
        load=["context/project-map.md", "context/change-impact.md", "targeted search results", "exact selected source files"],
        avoid=["whole directories", "generated files", "dependency trees"],
        exactness_risk="medium",
        exact_text=False,
        reason="Unknown code areas should be narrowed with a relevance map before broad reading.",
        fallback="Load exact source for the most likely path before editing.",
    ),
    "output": Route(
        name="output",
        lane="output-slicer",
        supporting_lane=None,
        slice="output",
        load=["templates/tool-summary.md", "GUARDRAILS.md behavior contract", "context/guardrail-layers.md QA / validation layer for risky failures", "first relevant failure", "counts", "affected files"],
        avoid=["raw full logs unless the log itself is being debugged"],
        exactness_risk="medium",
        exact_text=False,
        reason="Noisy tool output is usually useful as counts, first failures, and next actions.",
        fallback="Keep exact log lines when diagnosing a parser, stack trace, or flaky failure.",
    ),
    "tool": Route(
        name="tool",
        lane="tool-sandbox",
        supporting_lane="output-slicer",
        slice="output",
        load=["templates/tool-summary.md", "exact fields needed from the tool response"],
        avoid=["raw HTML dumps", "raw API JSON dumps", "unfiltered MCP payloads"],
        exactness_risk="medium",
        exact_text=False,
        reason="External tool payloads should be summarized unless exact fields are required.",
        fallback="Request exact fields by path when the summary is insufficient.",
    ),
    "cache": Route(
        name="cache",
        lane="reuse-cache",
        supporting_lane=None,
        slice="cache",
        load=["context/cache-index.md", "templates/context-brief.md"],
        avoid=["rediscovering unchanged project facts", "stale summaries"],
        exactness_risk="medium",
        exact_text=False,
        reason="Repeated project facts should be reused when their invalidation rules still hold.",
        fallback="Refresh the summary if source files, commands, versions, or policy changed.",
    ),
    "compression": Route(
        name="compression",
        lane="compressed-reference",
        supporting_lane="prune",
        slice="compression",
        load=["context/compression-policy.md", "context/prune-rules.md", "GUARDRAILS.md behavior contract", "context/guardrail-layers.md token saving layer"],
        avoid=["code", "diffs", "configs", "commands", "security rules"],
        exactness_risk="low",
        exact_text=False,
        reason="Compression is only suitable for bulky, stable, non-exact reference material.",
        fallback="Use exact text pass-through if byte-for-byte detail matters.",
    ),
    "exact": Route(
        name="exact",
        lane="exact-pass-through",
        supporting_lane=None,
        slice="none",
        load=["GUARDRAILS.md behavior contract", "context/guardrail-layers.md global pointer", "exact source, diff, config, command, ID, path, or security text"],
        avoid=["summaries", "compression", "lossy rewriting"],
        exactness_risk="high",
        exact_text=True,
        reason="This task depends on byte-for-byte material.",
        fallback="Use a surrounding brief only after the exact material is preserved.",
    ),
}

ROUTES["qa"] = Route(
    name="qa",
    lane="output-slicer",
    supporting_lane="text-slice",
    slice="output",
    load=["templates/validation-handoff.md", "templates/tool-summary.md", "tailtrail-policy.md when present", "GUARDRAILS.md behavior contract", "context/guardrail-layers.md QA / validation layer", "exact validation command, result, first failure, or changed behavior"],
    avoid=["raw full logs unless the failure line matters", "unrelated test suites", "generic test wish lists"],
    exactness_risk="high",
    exact_text=True,
    reason="QA work needs exact validation evidence plus compact failure and coverage framing.",
    fallback="Load aidlc/extensions/testing-baseline.md if validation scope is unclear.",
)

ROUTES["ci-sonar"] = Route(
    name="ci-sonar",
    lane="output-slicer",
    supporting_lane="text-slice",
    slice="output",
    load=["templates/tool-summary.md", "tailtrail-policy.md when present", "GUARDRAILS.md behavior contract", "context/guardrail-layers.md CI / Sonar layer", "exact job, stage, rule ID, file, line, command, and first relevant failure"],
    avoid=["lossy summaries of rule IDs or file paths", "unrelated pipeline logs", "generated or vendor areas unless policy allows"],
    exactness_risk="high",
    exact_text=True,
    reason="CI and Sonar fixes depend on exact rule, stage, file, line, and command evidence.",
    fallback="Load the relevant source file and one likely shared helper if the reported line is only a symptom.",
)

ROUTES["release"] = Route(
    name="release",
    lane="text-slice",
    supporting_lane="output-slicer",
    slice="aidlc",
    load=["aidlc/stages/handoff.md", "templates/diff-handoff.md", "templates/validation-handoff.md", "templates/operations-notes.md when deployment is in scope", "tailtrail-policy.md when present", "GUARDRAILS.md behavior contract", "context/guardrail-layers.md release layer", "exact final diff, validation evidence, version, branch, or approval text"],
    avoid=["new implementation work unless a release blocker is found", "raw full logs", "invented deployment or approval status"],
    exactness_risk="high",
    exact_text=True,
    reason="Release readiness needs compact handoff plus exact validation, approval, rollback, and version evidence.",
    fallback="Load operations notes when production deployment, monitoring, or support ownership is in scope.",
)


ALIASES: dict[str, str] = {
    "aidlc": "aidlc",
    "audit": "aidlc",
    "bug": "core",
    "build": "output",
    "ci": "ci-sonar",
    "code": "core",
    "coding": "core",
    "compress": "compression",
    "config": "exact",
    "dependency": "dependency",
    "deps": "dependency",
    "design": "project-map",
    "diff": "review",
    "example": "example",
    "fix": "core",
    "hook": "router",
    "handoff": "handoff",
    "implementation": "core",
    "lifecycle": "aidlc",
    "install": "dependency",
    "lint": "output",
    "log": "output",
    "logs": "output",
    "mcp": "tool",
    "output": "output",
    "output-log": "output",
    "package": "dependency",
    "prompt": "router",
    "qa": "qa",
    "quality": "qa",
    "quality-gate": "ci-sonar",
    "refactor": "core",
    "review": "review",
    "release": "release",
    "route": "router",
    "router": "router",
    "security": "exact",
    "sonar": "ci-sonar",
    "slice": "router",
    "test": "output",
    "tool": "tool",
}

ROUTES["router"] = Route(
    name="router",
    lane="text-slice",
    supporting_lane=None,
    slice="router",
    load=["context/TailTrail.map.md", "context/token-router.md", "context/guardrail-layers.md token saving layer when exactness risk matters"],
    avoid=["all examples", "ROADMAP.md unless changing roadmap", "DESIGN.md unless changing design"],
    exactness_risk="medium",
    exact_text=False,
    reason="Token-saving decisions should load the tiny map and router, not every TailTrail doc.",
    fallback="Use templates/router-decision.md for broad or repeated routing decisions.",
)


def normalize(value: str) -> str:
    cleaned = value.strip().lower().replace("_", "-")
    return ALIASES.get(cleaned, cleaned)


def classify(words: Iterable[str]) -> str:
    text = " ".join(words).lower()
    if not text.strip():
        return "router"

    checks = [
        ("review", ["review", "diff", "pull request", "pr "]),
        ("ci-sonar", ["sonar", "quality gate", "pipeline", "ci issue", "ci failure", "scan"]),
        ("qa", ["qa", "validation", "regression", "acceptance", "test plan"]),
        ("output", ["test", "build", "lint", "log", "stack trace", "failure", "ci"]),
        ("tool", ["browser", "api", "mcp", "html", "json payload", "tool output"]),
        ("dependency", ["dependency", "package", "library", "install", "version"]),
        ("aidlc", ["aidlc", "lifecycle", "stage gate", "audit"]),
        ("handoff", ["handoff", "hand off", "transfer", "closeout"]),
        ("release", ["release", "rollback", "deployment", "deploy", "approval package"]),
        ("compression", ["compress", "compression", "image compression", "bulky reference"]),
        ("cache", ["cache", "memory", "repeated facts", "rediscover"]),
        ("project-map", ["unknown area", "map project", "broad repo", "where is"]),
        ("example", ["example", "sample", "calibration"]),
        ("exact", ["exact", "security", "config", "secret", "hash", "id", "authorization"]),
        ("core", ["code", "fix", "implement", "refactor", "bug"]),
        ("router", ["router", "route", "slice", "token"]),
    ]
    for route, needles in checks:
        if any(needle in text for needle in needles):
            return route
    return "core"


def route_for(raw: str, prompt_words: list[str]) -> Route:
    route_name = normalize(raw)
    if route_name == "auto":
        route_name = classify(prompt_words)
    if route_name not in ROUTES:
        known = ", ".join(sorted(ROUTES))
        raise SystemExit(f"Unknown route '{raw}'. Known routes: {known}")
    return ROUTES[route_name]


def state_payload(route: Route, prompt: str) -> dict[str, object]:
    return {
        "last_route": route.name,
        "lane": route.lane,
        "supporting_lane": route.supporting_lane,
        "slice": route.slice,
        "exactness_risk": route.exactness_risk,
        "exact_text": route.exact_text,
        "prompt": prompt,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_state(path: Path, route: Route, prompt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state_payload(route, prompt), indent=2) + "\n", encoding="utf-8")


def print_markdown(route: Route) -> None:
    print(f"# TailTrail Router Decision: {route.name}")
    print()
    print(f"- Lane: `{route.lane}`")
    if route.supporting_lane:
        print(f"- Supporting lane: `{route.supporting_lane}`")
    print(f"- Slice: `{route.slice}`")
    print(f"- Exactness risk: `{route.exactness_risk}`")
    print(f"- Exact text required: `{str(route.exact_text).lower()}`")
    print(f"- Reason: {route.reason}")
    print(f"- Fallback: {route.fallback}")
    print()
    print("Load:")
    for item in route.load:
        print(f"- {item}")
    print()
    print("Avoid:")
    for item in route.avoid:
        print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Route a TailTrail task to the smallest safe context slice.")
    parser.add_argument("route", nargs="?", default="auto", help="Route name or 'auto'.")
    parser.add_argument("prompt", nargs="*", help="Optional task text used when route is 'auto'.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help="State file path.")
    parser.add_argument("--no-state", action="store_true", help="Do not write persisted router state.")
    args = parser.parse_args()

    route = route_for(args.route, args.prompt)
    prompt = " ".join(args.prompt)

    if args.format == "json":
        print(json.dumps(asdict(route), indent=2))
    else:
        print_markdown(route)

    if not args.no_state:
        write_state(args.state, route, prompt)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
