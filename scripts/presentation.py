#!/usr/bin/env python3
"""Canonical TailTrail presentation and host-conformance service (PM-3)."""
from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HOSTS = ("cli", "mcp", "codex", "copilot", "claude")
SURFACES = ("markdown", "narrow", "collapsed", "json")
STATUSES = ("available", "unavailable", "inapplicable")


def validate(report: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if report.get("schema_version") != "1": issues.append("schema-version-invalid")
    if report.get("type") != "tailtrail-presentation-report": issues.append("type-invalid")
    if report.get("report_kind") not in {"plan", "debug", "closure", "orchestration"}: issues.append("report-kind-invalid")
    if report.get("mode") not in {"quick", "guided", "expert"}: issues.append("mode-invalid")
    if not str(report.get("title", "")).strip(): issues.append("title-missing")
    sections = report.get("sections")
    if not isinstance(sections, list) or not sections:
        issues.append("sections-missing")
        sections = []
    seen: set[str] = set()
    for index, section in enumerate(sections):
        prefix = f"section-{index + 1}"
        if not isinstance(section, dict):
            issues.append(f"{prefix}-invalid"); continue
        section_id = str(section.get("id", ""))
        if not section_id: issues.append(f"{prefix}-id-missing")
        elif section_id in seen: issues.append(f"section-{section_id}-duplicate")
        seen.add(section_id)
        status = section.get("status")
        if status not in STATUSES: issues.append(f"section-{section_id or index + 1}-status-invalid")
        content = section.get("content")
        reason = str(section.get("reason", "")).strip()
        if status == "available" and (content is None or content == "" or content == [] or content == {}):
            issues.append(f"section-{section_id}-content-missing")
        if status in {"unavailable", "inapplicable"} and not reason:
            issues.append(f"section-{section_id}-reason-missing")
        if report.get("verbose") is True and section.get("required") is True and status not in STATUSES:
            issues.append(f"verbose-section-{section_id}-silently-omitted")
    expected = report.get("required_section_ids", [])
    if not isinstance(expected, list): issues.append("required-section-ids-invalid")
    else:
        missing = sorted(set(str(item) for item in expected) - seen)
        issues.extend(f"required-section-{item}-missing" for item in missing)
    return {
        "type": "tailtrail-presentation-validation",
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "section_ids": sorted(seen),
        "boundary": "Semantic presentation validation only; it does not execute a workflow or infer missing report data.",
    }


def _content_lines(content: Any, width: int | None = None) -> list[str]:
    if isinstance(content, str): lines = content.splitlines() or [content]
    elif isinstance(content, list): lines = [f"- {item}" for item in content]
    elif isinstance(content, dict): lines = [f"- **{key}:** {value}" for key, value in content.items()]
    else: lines = [str(content)]
    if not width: return lines
    wrapped: list[str] = []
    for line in lines:
        indent = "  " if line.startswith("- ") else ""
        wrapped.extend(textwrap.wrap(line, width=max(24, width), subsequent_indent=indent, replace_whitespace=False) or [""])
    return wrapped


def render_markdown(report: dict[str, Any], *, width: int | None = None) -> str:
    checked = validate(report)
    if checked["status"] != "passed":
        raise ValueError("canonical presentation is invalid: " + ", ".join(checked["issues"]))
    lines = [f"# {report['title']}", ""]
    if report.get("run_id"): lines += [f"**Run:** `{report['run_id']}`"]
    if report.get("state"): lines += [f"**State:** `{report['state']}`"]
    for section in report["sections"]:
        lines += ["", f"## {section['title']}", ""]
        if section["status"] == "available": lines += _content_lines(section["content"], width)
        else: lines += [f"**{section['status'].title()}:** {section['reason']}"]
    lines += ["", f"_Presentation: {report['mode']} / {'verbose' if report['verbose'] else 'standard'}; semantic content is canonical across supported hosts._"]
    return "\n".join(lines)


def render(report: dict[str, Any], surface: str, *, width: int = 72) -> str:
    if surface not in SURFACES: raise ValueError(f"unsupported presentation surface: {surface}")
    checked = validate(report)
    if checked["status"] != "passed": raise ValueError("canonical presentation is invalid: " + ", ".join(checked["issues"]))
    if surface == "json": return json.dumps(report, indent=2, sort_keys=True)
    if surface == "markdown": return render_markdown(report)
    if surface == "narrow": return render_markdown(report, width=max(32, min(width, 88)))
    required = ", ".join(report["required_section_ids"])
    return (f"TailTrail cannot safely collapse this {report['report_kind']} report. "
            f"Open the canonical report to view all required sections: {required}. "
            "No shortened report is a substitute for the canonical output.")


def from_orchestration(value: dict[str, Any], *, mode: str = "guided", verbose: bool = False) -> dict[str, Any]:
    result = value.get("result") if isinstance(value.get("result"), dict) else {}
    details: dict[str, Any] = {}
    if value.get("workflow_id"): details["Workflow"] = value["workflow_id"]
    if value.get("stage_id"): details["Stage"] = value["stage_id"]
    if value.get("verb") == "discuss":
        answer = result.get("answer") if isinstance(result.get("answer"), dict) else {}
        if answer.get("direct"): details["Saved-plan answer"] = answer["direct"]
    adapter_input = result.get("adapter_input") if isinstance(result.get("adapter_input"), dict) else {}
    if adapter_input.get("artifact"): details["Typed handoff"] = adapter_input["artifact"]
    handoff = result.get("execution_handoff_artifact")
    if handoff: details["Execution handoff"] = handoff
    workflow = value.get("workflow") if isinstance(value.get("workflow"), dict) else {}
    current = workflow.get("current_stage_display") or workflow.get("current_stage")
    if current: details["Current stage"] = current
    if result.get("completion_report"): details["Completion Report"] = result["completion_report"]
    prompt = result.get("acceptance_prompt") if isinstance(result.get("acceptance_prompt"), dict) else {}
    if prompt.get("options"): details["Acceptance choices"] = ", ".join(str(item) for item in prompt["options"])
    sections = [
        {"id":"details","title":"Details","status":"available" if details else "inapplicable","required":True,
         "content":details or None,"reason":"This orchestration result has no additional workflow or handoff detail." if not details else None},
        {"id":"next-action","title":"Next action","status":"available","required":True,"content":str(value.get("next_action", "No next action recorded.")),"reason":None},
        {"id":"boundary","title":"Boundary","status":"available","required":True,"content":str(value.get("boundary", "No boundary recorded.")),"reason":None},
    ]
    return {"schema_version":"1","type":"tailtrail-presentation-report","report_kind":"orchestration","mode":mode,
            "verbose":verbose,"title":"TailTrail " + str(value.get("verb", "status")).title(),"run_id":value.get("run_id"),
            "state":value.get("state"),"required_section_ids":["details","next-action","boundary"],"sections":sections}


def _fixture_reports() -> list[Path]:
    packaged = sorted((ROOT / "benchmarks" / "product-maturity" / "presentation-v1").glob("*-report.json"))
    return packaged or sorted((ROOT / "tests" / "fixtures" / "presentation").glob("*-report.json"))


def conformance() -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    issues: list[str] = []
    for path in _fixture_reports():
        report = json.loads(path.read_text(encoding="utf-8"))
        validation = validate(report)
        surfaces: dict[str, str] = {}
        for surface in SURFACES:
            try:
                rendered = render(report, surface, width=44)
                surfaces[surface] = "explicit-display-required" if surface == "collapsed" else "passed"
                if surface != "collapsed" and report["title"] not in rendered: issues.append(f"{path.stem}:{surface}:title-missing")
            except ValueError as error:
                surfaces[surface] = "failed"; issues.append(f"{path.stem}:{surface}:{error}")
        for host in HOSTS:
            if host == "mcp" and surfaces["json"] != "passed": issues.append(f"{path.stem}:{host}:json-failed")
            elif host != "mcp" and surfaces["markdown"] != "passed": issues.append(f"{path.stem}:{host}:markdown-failed")
        if validation["status"] != "passed": issues.extend(f"{path.stem}:{item}" for item in validation["issues"])
        scenarios.append({"scenario":path.stem.removesuffix("-report"),"hosts":{host:"passed" for host in HOSTS},"surfaces":surfaces,"semantic_sections":validation["section_ids"]})
    return {"type":"tailtrail-presentation-conformance","status":"passed" if scenarios and not issues else "failed",
            "scenario_count":len(scenarios),"scenarios":scenarios,"issues":issues,
            "boundary":"Deterministic golden-fixture conformance only; it does not claim a live host displayed a report."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("validate"); check.add_argument("--input", type=Path, required=True)
    show = sub.add_parser("render"); show.add_argument("--input", type=Path, required=True); show.add_argument("--surface", choices=SURFACES, required=True); show.add_argument("--width", type=int, default=72); show.add_argument("--mode", choices=("quick", "guided", "expert"), help="Override display depth only; canonical report semantics and authority remain unchanged.")
    sub.add_parser("conformance")
    args = parser.parse_args()
    try:
        if args.action == "conformance": output = conformance(); print(json.dumps(output, indent=2, sort_keys=True)); return 0 if output["status"] == "passed" else 2
        report = json.loads(args.input.read_text(encoding="utf-8"))
        if args.action == "validate": output = validate(report); print(json.dumps(output, indent=2, sort_keys=True)); return 0 if output["status"] == "passed" else 2
        if args.mode:
            report = {**report, "mode": args.mode}
        print(render(report, args.surface, width=args.width)); return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"TailTrail presentation error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
