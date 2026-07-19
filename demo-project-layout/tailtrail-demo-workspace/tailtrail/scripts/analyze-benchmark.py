#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYSIS = ROOT / "benchmarks" / "results" / "latest-analysis.md"
REVIEW_NOTE = "Recommended changes are advisory. Review the impacted files, line numbers, and proposed prompt wording before adding anything."

THEME_ANCHORS: dict[str, list[str]] = {
    "validation truth": ["validation truth", "do not claim tests", "validation"],
    "safeguard preservation": ["safeguards", "preserve validation", "authorization", "security"],
    "dependency discipline": ["dependency layer", "dependencies", "dependency gate", "dependency"],
    "scope control": ["scope", "smallest maintainable", "broad rewrites"],
    "root-cause focus": ["root cause", "shared helpers", "callers", "caller"],
    "review impact": ["review layer", "review", "findings"],
    "validation clarity": ["qa / validation layer", "validation truth", "validation"],
    "exactness": ["exactness", "ci / sonar layer", "preserve exact", "evidence"],
    "benchmark calibration": ["benchmark", "scenario", "acceptance check"],
}

CHECK_ANCHORS: dict[str, list[str]] = {
    "avoids_false_test_claim": ["validation truth", "do not claim tests", "validation"],
    "preserves_validation": ["safeguards", "preserve validation", "validation"],
    "preserves_authorization": ["safeguards", "authorization", "security"],
    "avoids_dependency": ["dependency layer", "dependencies", "dependency gate"],
    "prefers_native_capability": ["dependency layer", "standard library", "platform-native"],
    "keeps_scope_small": ["scope", "smallest maintainable"],
    "checks_shared_path": ["implementation layer", "shared helpers", "callers"],
    "avoids_one_off_patch": ["root cause", "one-off", "callers"],
    "mentions_callers": ["review layer", "callers", "review"],
    "focused_validation": ["qa / validation layer", "focused check", "validation"],
    "preserves_rule_evidence": ["ci / sonar layer", "preserve exact", "rule id", "exactness"],
    "smallest_root_cause": ["ci / sonar layer", "root cause", "reported line"],
    "avoids_lossy_summary": ["token saving layer", "exact pass-through", "lossy"],
    "exact_validation": ["qa / validation layer", "exact commands", "validation truth"],
}

THEMES: dict[str, dict[str, object]] = {
    "avoids_false_test_claim": {
        "theme": "validation truth",
        "priority": "high",
        "files": ["GUARDRAILS.md", "context/guardrail-layers.md", "skills/tailtrail-review/SKILL.md"],
        "recommendation": "Strengthen validation-truth wording and add another false-validation benchmark scenario.",
    },
    "preserves_validation": {
        "theme": "safeguard preservation",
        "priority": "high",
        "files": ["GUARDRAILS.md", "context/guardrail-layers.md", "aidlc/extensions/testing-baseline.md"],
        "recommendation": "Tighten validation preservation guidance and add scenario coverage for removed input checks.",
    },
    "preserves_authorization": {
        "theme": "safeguard preservation",
        "priority": "high",
        "files": ["GUARDRAILS.md", "context/guardrail-layers.md", "aidlc/extensions/security-baseline.md"],
        "recommendation": "Strengthen authorization preservation wording and review security baseline examples.",
    },
    "avoids_dependency": {
        "theme": "dependency discipline",
        "priority": "high",
        "files": ["DEPENDENCY-GATE.md", "context/guardrail-layers.md", "skills/tailtrail/SKILL.md"],
        "recommendation": "Strengthen dependency-gate wording and add examples for native/platform alternatives.",
    },
    "prefers_native_capability": {
        "theme": "dependency discipline",
        "priority": "medium",
        "files": ["DEPENDENCY-GATE.md", "examples/native-date-field.md", "context/guardrail-layers.md"],
        "recommendation": "Clarify when native/platform capability should be tried before custom code or packages.",
    },
    "keeps_scope_small": {
        "theme": "scope control",
        "priority": "medium",
        "files": ["AGENTS.md", "skills/tailtrail/SKILL.md", "context/guardrail-layers.md"],
        "recommendation": "Clarify smallest-maintainable-change guidance and add a scope-control scenario if misses repeat.",
    },
    "checks_shared_path": {
        "theme": "root-cause focus",
        "priority": "medium",
        "files": ["context/change-impact.md", "examples/shared-bug-fix.md", "context/guardrail-layers.md"],
        "recommendation": "Strengthen caller/shared-helper inspection guidance.",
    },
    "avoids_one_off_patch": {
        "theme": "root-cause focus",
        "priority": "medium",
        "files": ["context/change-impact.md", "examples/shared-bug-fix.md", "skills/tailtrail/SKILL.md"],
        "recommendation": "Add clearer anti-pattern guidance for one-off caller patches.",
    },
    "mentions_callers": {
        "theme": "review impact",
        "priority": "medium",
        "files": ["context/change-impact.md", "skills/tailtrail-review/SKILL.md"],
        "recommendation": "Improve review impact guidance around callers and likely tests.",
    },
    "focused_validation": {
        "theme": "validation clarity",
        "priority": "medium",
        "files": ["aidlc/extensions/testing-baseline.md", "templates/validation-handoff.md", "context/guardrail-layers.md"],
        "recommendation": "Strengthen focused validation wording and examples.",
    },
    "preserves_rule_evidence": {
        "theme": "exactness",
        "priority": "high",
        "files": ["context/guardrail-layers.md", "GUARDRAILS.md", "templates/tool-summary.md"],
        "recommendation": "Tighten CI/Sonar exactness rules for rule IDs, jobs, stages, files, and lines.",
    },
    "smallest_root_cause": {
        "theme": "root-cause focus",
        "priority": "medium",
        "files": ["context/guardrail-layers.md", "context/change-impact.md"],
        "recommendation": "Clarify smallest-root-cause review behavior for reported scanner lines.",
    },
    "avoids_lossy_summary": {
        "theme": "exactness",
        "priority": "high",
        "files": ["TOKEN-SLICER.md", "context/guardrail-layers.md", "templates/tool-summary.md"],
        "recommendation": "Strengthen exact-pass-through guidance for scanner and validation evidence.",
    },
    "exact_validation": {
        "theme": "validation clarity",
        "priority": "high",
        "files": ["context/guardrail-layers.md", "templates/validation-handoff.md"],
        "recommendation": "Clarify exact validation command capture for CI/Sonar remediation.",
    },
}

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

PROMPT_CHANGES: dict[str, str] = {
    "validation truth": (
        "Do not claim validation, tests, CI, or scanner checks passed unless exact commands, jobs, "
        "or evidence were actually run or provided. If validation was not run, say so plainly and "
        "name the smallest next check."
    ),
    "safeguard preservation": (
        "Before simplifying code, preserve validation, authorization, escaping, accessibility, "
        "data-integrity, and trust-boundary safeguards. Do not remove a guard unless an equivalent "
        "or stronger guard remains."
    ),
    "dependency discipline": (
        "Before recommending a package, check standard library, platform-native capability, framework "
        "features, and already-installed dependencies. Add a dependency only when the native path is "
        "clearly insufficient and the tradeoff is documented."
    ),
    "scope control": (
        "Prefer the smallest maintainable change that fixes the root cause. Avoid broad rewrites, "
        "new abstractions, or unrelated cleanup unless the task explicitly requires them."
    ),
    "root-cause focus": (
        "Trace shared callers, helpers, tests, and data paths before patching one visible symptom. "
        "Fix the shared root cause when the evidence points there."
    ),
    "review impact": (
        "Review the diff for behavior impact, shared callers, likely tests, changed risk boundaries, "
        "and any missing validation before suggesting style-only feedback."
    ),
    "validation clarity": (
        "Capture exact validation commands, scanner rule IDs, job names, files, and lines when they "
        "matter. Separate verified results from recommended next checks."
    ),
    "exactness": (
        "Preserve exact CI, Sonar, scanner, policy, file, line, and command evidence. Do not compress "
        "or paraphrase evidence in a way that loses identifiers needed for remediation."
    ),
    "benchmark calibration": (
        "Review whether the benchmark expectation is clear, realistic, and mapped to a real TailTrail "
        "behavior before changing product guidance."
    ),
}


def read_input(path: Path | None) -> dict[str, Any]:
    if path:
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(sys.stdin.read())


def theme_for(check_name: str) -> dict[str, object]:
    return THEMES.get(check_name, {
        "theme": "benchmark calibration",
        "priority": "low",
        "files": ["benchmarks/scenarios/"],
        "recommendation": "Review the benchmark check and decide whether TailTrail guidance or the scenario expectation should change.",
    })


def find_anchor_line(path_text: str, theme: str, check_name: str | None = None) -> int | None:
    path = ROOT / path_text
    if not path.is_file():
        return None

    terms = [
        *CHECK_ANCHORS.get(check_name or "", []),
        *THEME_ANCHORS.get(theme, [theme]),
    ]
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return None

    for term in terms:
        for index, line in enumerate(lines, start=1):
            if term in line.lower():
                return index
    return len(lines) + 1


def proposed_changes(theme: str, files: list[str], check_name: str | None = None) -> list[dict[str, Any]]:
    prompt_change = PROMPT_CHANGES.get(theme, PROMPT_CHANGES["benchmark calibration"])
    changes = []
    for file in files:
        line = find_anchor_line(file, theme, check_name)
        changes.append({
            "file": file,
            "line": line,
            "action": "review and add or strengthen nearby guidance",
            "prompt_change": prompt_change,
            "note": "Line is a suggested anchor from the current file content; review surrounding wording before editing.",
        })
    return changes


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    weak: list[dict[str, Any]] = []
    strong_counter: Counter[str] = Counter()
    missed_counter: Counter[str] = Counter()
    discrepancies: list[dict[str, Any]] = []
    improvements: dict[str, dict[str, Any]] = {}

    for scenario in data.get("scenarios", []):
        scenario_name = str(scenario.get("name", "unknown"))
        baseline = scenario.get("baseline", {})
        tailtrail = scenario.get("tailtrail", {})
        baseline_score = int(baseline.get("score", 0))
        tailtrail_score = int(tailtrail.get("score", 0))
        if baseline_score >= tailtrail_score:
            discrepancies.append({
                "scenario": scenario_name,
                "baseline": baseline_score,
                "tailtrail": tailtrail_score,
                "issue": "baseline score is equal to or higher than TailTrail score",
            })

        for check in tailtrail.get("checks", []):
            check_name = str(check.get("name", "unknown"))
            info = theme_for(check_name)
            theme = str(info["theme"])
            if check.get("passed"):
                strong_counter[theme] += 1
                continue

            missed_counter[theme] += 1
            weak_item = {
                "scenario": scenario_name,
                "check": check_name,
                "theme": theme,
                "priority": str(info["priority"]),
                "reason": str(check.get("reason", "")),
                "likely_files": list(info["files"]),
                "recommendation": str(info["recommendation"]),
                "proposed_changes": proposed_changes(theme, list(info["files"]), check_name),
            }
            weak.append(weak_item)

            key = f"{theme}:{info['recommendation']}"
            entry = improvements.setdefault(key, {
                "theme": theme,
                "priority": str(info["priority"]),
                "recommendation": str(info["recommendation"]),
                "likely_files": list(info["files"]),
                "proposed_changes": proposed_changes(theme, list(info["files"]), check_name),
                "evidence": [],
            })
            entry["evidence"].append(f"{scenario_name} missed {check_name}")

    improvement_list = sorted(
        improvements.values(),
        key=lambda item: (PRIORITY_ORDER.get(str(item["priority"]), 9), str(item["theme"])),
    )
    strong = [{"theme": theme, "passed_checks": count} for theme, count in strong_counter.most_common()]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_generated_at": data.get("generated_at"),
        "disclaimer": "Deterministic benchmark analysis. Recommendations require human review before TailTrail changes.",
        "review_note": REVIEW_NOTE,
        "totals": data.get("totals", {}),
        "strong_areas": strong,
        "weak_areas": weak,
        "missed_themes": [{"theme": theme, "misses": count} for theme, count in missed_counter.most_common()],
        "discrepancies": discrepancies,
        "recommended_improvements": improvement_list,
        "not_automatic": [
            "does not edit TailTrail files",
            "does not run models",
            "does not observe users in the background",
            "does not log raw prompts or private repo content",
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    totals = report.get("totals", {})
    lines = [
        "# TailTrail Behavior Analysis",
        "",
        str(report["disclaimer"]),
        "",
        f"Review note: {report['review_note']}",
        "",
        "## Benchmark Summary",
        "",
        f"- Baseline: `{totals.get('baseline', 0)} / {totals.get('max', 0)}`",
        f"- TailTrail: `{totals.get('tailtrail', 0)} / {totals.get('max', 0)}`",
        f"- Delta: `{int(totals.get('delta', 0)):+d}`",
        "",
        "## Strong Areas",
        "",
    ]
    if report["strong_areas"]:
        for item in report["strong_areas"]:
            lines.append(f"- {item['theme']}: {item['passed_checks']} passed check(s)")
    else:
        lines.append("- No strong areas detected yet.")

    lines.extend(["", "## Weak Areas", ""])
    if report["weak_areas"]:
        for item in report["weak_areas"]:
            lines.extend([
                f"- {item['priority'].upper()}: {item['theme']} in `{item['scenario']}`",
                f"  - Check: `{item['check']}`",
                f"  - Evidence: {item['reason']}",
            ])
    else:
        lines.append("- No TailTrail misses detected in this benchmark result.")

    lines.extend(["", "## Discrepancies", ""])
    if report["discrepancies"]:
        for item in report["discrepancies"]:
            lines.append(f"- `{item['scenario']}`: baseline {item['baseline']} vs TailTrail {item['tailtrail']} ({item['issue']})")
    else:
        lines.append("- No baseline-over-TailTrail discrepancies detected.")

    lines.extend(["", "## Recommended Improvements", ""])
    if report["recommended_improvements"]:
        for item in report["recommended_improvements"]:
            lines.extend([
                f"- {item['priority'].upper()}: {item['recommendation']}",
                f"  - Theme: {item['theme']}",
                "  - Likely files: " + ", ".join(f"`{file}`" for file in item["likely_files"]),
                "  - Evidence: " + "; ".join(item["evidence"]),
                "  - Proposed file changes:",
            ])
            for change in item["proposed_changes"]:
                line = change["line"] if change["line"] is not None else "manual anchor"
                lines.extend([
                    f"    - `{change['file']}` near line `{line}`: {change['action']}.",
                    f"      Prompt change: {change['prompt_change']}",
                    f"      Note: {change['note']}",
                ])
    else:
        lines.append("- No immediate TailTrail changes recommended from this benchmark result.")

    lines.extend(["", "## Boundaries", ""])
    for item in report["not_automatic"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze TailTrail benchmark JSON and recommend improvement areas.")
    parser.add_argument("result", nargs="?", type=Path, help="Benchmark JSON file. Reads stdin when omitted.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    parser.add_argument("--write-result", type=Path, nargs="?", const=DEFAULT_ANALYSIS, help="Write Markdown analysis to a file.")
    args = parser.parse_args()

    report = analyze(read_input(args.result))
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        output = markdown(report)
        print(output, end="")
        if args.write_result:
            args.write_result.parent.mkdir(parents=True, exist_ok=True)
            args.write_result.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
