#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = ROOT / "benchmarks" / "scenarios"
DEFAULT_RESULTS = ROOT / "benchmarks" / "results" / "latest.md"


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    points: int
    earned: int
    reason: str


@dataclass(frozen=True)
class ArtifactResult:
    name: str
    score: int
    max_score: int
    checks: list[CheckResult]


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    title: str
    baseline: ArtifactResult
    tailtrail: ArtifactResult

    @property
    def delta(self) -> int:
        return self.tailtrail.score - self.baseline.score


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contains_any(text: str, patterns: list[str]) -> tuple[bool, str]:
    lowered = text.lower()
    for pattern in patterns:
        if pattern.lower() in lowered:
            return True, f"found `{pattern}`"
    return False, "none of the expected patterns were found"


def contains_all(text: str, patterns: list[str]) -> tuple[bool, str]:
    lowered = text.lower()
    missing = [pattern for pattern in patterns if pattern.lower() not in lowered]
    if missing:
        return False, "missing " + ", ".join(f"`{item}`" for item in missing)
    return True, "all expected patterns were found"


def must_not_contain_any(text: str, patterns: list[str]) -> tuple[bool, str]:
    lowered = text.lower()
    found = [pattern for pattern in patterns if pattern.lower() in lowered]
    if found:
        return False, "found forbidden " + ", ".join(f"`{item}`" for item in found)
    return True, "no forbidden patterns were found"


CHECKS = {
    "contains_any": contains_any,
    "contains_all": contains_all,
    "must_not_contain_any": must_not_contain_any,
}


def score_artifact(name: str, text: str, checks: list[dict[str, Any]]) -> ArtifactResult:
    results: list[CheckResult] = []
    for check in checks:
        check_name = str(check["name"])
        check_type = str(check["type"])
        points = int(check.get("points", 1))
        patterns = [str(pattern) for pattern in check.get("patterns", [])]
        if check_type not in CHECKS:
            raise SystemExit(f"Unknown check type `{check_type}` in `{check_name}`")
        passed, reason = CHECKS[check_type](text, patterns)
        results.append(CheckResult(check_name, passed, points, points if passed else 0, reason))

    return ArtifactResult(
        name=name,
        score=sum(result.earned for result in results),
        max_score=sum(result.points for result in results),
        checks=results,
    )


def scenario_dirs(selected: str | None) -> list[Path]:
    if selected:
        path = SCENARIOS_DIR / selected
        if not path.exists():
            raise SystemExit(f"Unknown scenario `{selected}`")
        return [path]
    return sorted(path for path in SCENARIOS_DIR.iterdir() if path.is_dir())


def score_scenario(path: Path) -> ScenarioResult:
    expected = read_json(path / "expected.json")
    checks = list(expected.get("checks", []))
    baseline_text = (path / "baseline-output.md").read_text(encoding="utf-8")
    tailtrail_text = (path / "tailtrail-output.md").read_text(encoding="utf-8")
    return ScenarioResult(
        name=path.name,
        title=str(expected.get("title", path.name)),
        baseline=score_artifact("baseline", baseline_text, checks),
        tailtrail=score_artifact("tailtrail", tailtrail_text, checks),
    )


def payload(results: list[ScenarioResult]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Offline artifact benchmark. Do not use as a vendor/model-wide claim.",
        "totals": {
            "baseline": sum(result.baseline.score for result in results),
            "tailtrail": sum(result.tailtrail.score for result in results),
            "max": sum(result.tailtrail.max_score for result in results),
            "delta": sum(result.delta for result in results),
        },
        "scenarios": [
            {
                "name": result.name,
                "title": result.title,
                "baseline": {
                    "score": result.baseline.score,
                    "max": result.baseline.max_score,
                    "checks": [check.__dict__ for check in result.baseline.checks],
                },
                "tailtrail": {
                    "score": result.tailtrail.score,
                    "max": result.tailtrail.max_score,
                    "checks": [check.__dict__ for check in result.tailtrail.checks],
                },
                "delta": result.delta,
            }
            for result in results
        ],
    }


def print_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Benchmark Results",
        "",
        str(data["disclaimer"]),
        "",
        "## Totals",
        "",
        f"- Baseline: `{data['totals']['baseline']} / {data['totals']['max']}`",
        f"- TailTrail: `{data['totals']['tailtrail']} / {data['totals']['max']}`",
        f"- Delta: `{data['totals']['delta']:+d}`",
        "",
        "## Scenarios",
        "",
    ]
    for scenario in data["scenarios"]:
        lines.extend([
            f"### {scenario['title']}",
            "",
            f"- Scenario: `{scenario['name']}`",
            f"- Baseline: `{scenario['baseline']['score']} / {scenario['baseline']['max']}`",
            f"- TailTrail: `{scenario['tailtrail']['score']} / {scenario['tailtrail']['max']}`",
            f"- Delta: `{scenario['delta']:+d}`",
            "",
            "TailTrail checks:",
        ])
        for check in scenario["tailtrail"]["checks"]:
            marker = "pass" if check["passed"] else "miss"
            lines.append(f"- `{marker}` {check['name']}: {check['earned']} / {check['points']} ({check['reason']})")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Score offline TailTrail benchmark artifacts.")
    parser.add_argument("--scenario", help="Run one scenario by folder name.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    parser.add_argument("--write-result", type=Path, nargs="?", const=DEFAULT_RESULTS, help="Write Markdown result to a file.")
    args = parser.parse_args()

    results = [score_scenario(path) for path in scenario_dirs(args.scenario)]
    data = payload(results)

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        output = print_markdown(data)
        print(output)
        if args.write_result:
            args.write_result.parent.mkdir(parents=True, exist_ok=True)
            args.write_result.write_text(output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
