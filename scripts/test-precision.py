#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "specs"}
HELPER_TOKENS = ("fixture", "factory", "helper", "mock", "stub", "support", "conftest", "testutil", "test_util")
MAX_TEST_FILE_BYTES = 120_000


@dataclass(frozen=True)
class Framework:
    name: str
    evidence: list[str]
    default_commands: list[str]


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def existing(root: Path, candidates: list[str]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        rows.append({"path": candidate, "exists": (root / candidate).is_file()})
    return rows


def is_test_file(path: str) -> bool:
    item = Path(path)
    lowered = path.lower()
    parts = {part.lower() for part in item.parts}
    return (
        item.name.lower().startswith("test_")
        or item.name.lower().endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".test.js", ".spec.js"))
        or bool(parts.intersection(TEST_DIR_NAMES))
        or "/tests/" in lowered
        or "/test/" in lowered
    )


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def detect_frameworks(root: Path) -> list[Framework]:
    frameworks: list[Framework] = []

    py_evidence = [item for item in ("pyproject.toml", "pytest.ini", "tox.ini", "requirements.txt", "setup.cfg") if (root / item).exists()]
    if py_evidence or any((root / name).is_dir() for name in ("tests", "test")):
        commands = ["pytest"]
        if (root / "tox.ini").is_file():
            commands.append("tox")
        frameworks.append(Framework("python", py_evidence or ["tests/"], commands))

    if (root / "pom.xml").is_file():
        frameworks.append(Framework("java-maven", ["pom.xml"], ["mvn test"]))

    gradle_evidence = [item for item in ("build.gradle", "build.gradle.kts", "gradlew", "settings.gradle", "settings.gradle.kts") if (root / item).exists()]
    if gradle_evidence:
        command = "./gradlew test" if (root / "gradlew").exists() else "gradle test"
        frameworks.append(Framework("java-gradle", gradle_evidence, [command]))

    package_json = root / "package.json"
    if package_json.is_file():
        package = read_json(package_json)
        scripts = package.get("scripts", {}) if isinstance(package.get("scripts"), dict) else {}
        deps = {}
        for key in ("dependencies", "devDependencies"):
            value = package.get(key)
            if isinstance(value, dict):
                deps.update(value)
        evidence = ["package.json"]
        commands = []
        for script_name in ("test", "lint", "typecheck"):
            if script_name in scripts:
                commands.append(f"npm run {script_name}" if script_name != "test" else "npm test")
        if not commands and any(name in deps for name in ("jest", "vitest", "mocha")):
            commands.append("npm test")
        frameworks.append(Framework("node", evidence, commands or ["npm test"]))

    dotnet_evidence = [relpath(path, root) for path in list(root.glob("*.sln")) + list(root.glob("**/*.csproj"))[:5]]
    if dotnet_evidence:
        frameworks.append(Framework("dotnet", dotnet_evidence, ["dotnet test"]))

    if (root / "go.mod").is_file():
        frameworks.append(Framework("go", ["go.mod"], ["go test ./..."]))

    return frameworks


def basename_without_suffix(path: str) -> str:
    return Path(path).stem


def python_test_candidates(path: str) -> list[str]:
    source = Path(path)
    stem = source.stem
    parts = list(source.parts)
    without_prefix = parts
    if parts and parts[0] in {"src", "lib", "app"}:
        without_prefix = parts[1:]
    module_dir = Path(*without_prefix).parent if len(without_prefix) > 1 else Path()
    return [
        (Path("tests") / module_dir / f"test_{stem}.py").as_posix(),
        (Path("test") / module_dir / f"test_{stem}.py").as_posix(),
        (source.parent / f"test_{stem}.py").as_posix(),
    ]


def java_test_candidates(path: str) -> list[str]:
    source = Path(path)
    class_name = source.stem
    parts = list(source.parts)
    if "src" in parts and "main" in parts and "java" in parts:
        java_index = parts.index("java")
        package = Path(*parts[java_index + 1 : -1])
        return [
            (Path("src/test/java") / package / f"{class_name}Test.java").as_posix(),
            (Path("src/test/java") / package / f"{class_name}Tests.java").as_posix(),
        ]
    return [
        (Path("src/test/java") / f"{class_name}Test.java").as_posix(),
        (Path("src/test/java") / f"{class_name}Tests.java").as_posix(),
        (source.parent / f"{class_name}Test.java").as_posix(),
    ]


def dotnet_test_candidates(path: str) -> list[str]:
    source = Path(path)
    class_name = source.stem
    return [
        (Path("tests") / f"{class_name}Tests.cs").as_posix(),
        (source.parent / f"{class_name}Tests.cs").as_posix(),
        (source.parent / f"{class_name}Test.cs").as_posix(),
    ]


def node_test_candidates(path: str) -> list[str]:
    source = Path(path)
    stem = source.stem
    suffix = source.suffix
    return [
        (source.parent / f"{stem}.test{suffix}").as_posix(),
        (source.parent / f"{stem}.spec{suffix}").as_posix(),
        (Path("__tests__") / source.parent / f"{stem}.test{suffix}").as_posix(),
    ]


def go_test_candidates(path: str) -> list[str]:
    source = Path(path)
    return [(source.parent / f"{source.stem}_test.go").as_posix()]


def infer_test_files(root: Path, changed: list[str]) -> list[dict[str, Any]]:
    rows = []
    for item in changed:
        suffix = Path(item).suffix.lower()
        if suffix == ".py":
            candidates = python_test_candidates(item)
        elif suffix == ".java":
            candidates = java_test_candidates(item)
        elif suffix == ".cs":
            candidates = dotnet_test_candidates(item)
        elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
            candidates = node_test_candidates(item)
        elif suffix == ".go":
            candidates = go_test_candidates(item)
        else:
            candidates = []
        if is_test_file(item):
            candidates = [item, *candidates]
        rows.append({"changed_file": item, "candidates": existing(root, candidates)})
    return rows


def find_existing_helpers(root: Path, limit: int = 25) -> list[dict[str, str]]:
    helpers: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if len(helpers) >= limit:
            break
        if not path.is_file():
            continue
        relative = relpath(path, root)
        parts = set(Path(relative).parts)
        name = path.name.lower()
        if not parts.intersection(TEST_DIR_NAMES) and ".tests" not in relative.lower():
            continue
        if any(token in name for token in HELPER_TOKENS):
            helpers.append({"path": relative, "reason": "existing test helper/fixture naming"})
    return helpers


def classify_risk(goal: str, changed: list[str]) -> list[str]:
    text = " ".join([goal, *changed]).lower()
    risks = []
    if any(token in text for token in ("auth", "permission", "role", "token", "secret", "encrypt", "security")):
        risks.append("security or authorization")
    if any(token in text for token in ("validate", "validation", "required", "null", "empty", "schema")):
        risks.append("validation or input boundary")
    if any(token in text for token in ("migration", "sql", "table", "database", "transaction", "data")):
        risks.append("data integrity")
    if any(token in text for token in ("api", "endpoint", "contract", "request", "response")):
        risks.append("API contract")
    if any(Path(item).suffix.lower() in {".yml", ".yaml", ".tf", ".json", ".toml", ".properties"} for item in changed):
        risks.append("configuration or infrastructure")
    return risks or ["standard behavior regression"]


def test_case_matrix(goal: str, changed: list[str]) -> list[dict[str, str]]:
    risks = classify_risk(goal, changed)
    rows = [
        {
            "case": "regression",
            "purpose": "Capture the exact behavior that was broken or requested so it fails before the fix.",
            "precision": "One focused assertion tied to the changed path.",
        },
        {
            "case": "happy path",
            "purpose": "Confirm the intended behavior works for normal valid input.",
            "precision": "Use existing fixtures and avoid broad setup.",
        },
        {
            "case": "negative path",
            "purpose": "Confirm invalid input, failed dependency, or rejected state is handled safely.",
            "precision": "Assert the user-visible error, status, or persisted state.",
        },
        {
            "case": "boundary path",
            "purpose": "Cover empty, null, missing, duplicate, min/max, or edge-case values when relevant.",
            "precision": "Add only the boundary most likely to break the changed logic.",
        },
    ]
    if any(risk in risks for risk in ("security or authorization", "validation or input boundary", "data integrity", "API contract")):
        rows.append(
            {
                "case": "guard preservation",
                "purpose": f"Protect important safeguards detected for: {', '.join(risks)}.",
                "precision": "Verify the guard still blocks the unsafe path after the change.",
            }
        )
    if "configuration or infrastructure" in risks:
        rows.append(
            {
                "case": "configuration load",
                "purpose": "Confirm config, IaC, or manifest changes are parseable and scoped.",
                "precision": "Use the repo's existing validate/plan/lint command rather than a broad deployment.",
            }
        )
    return rows


def focused_commands(root: Path, changed: list[str], frameworks: list[Framework], likely_tests: list[dict[str, Any]]) -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []
    first_existing_test = ""
    first_candidate = ""
    for row in likely_tests:
        for candidate in row["candidates"]:
            first_candidate = first_candidate or candidate["path"]
            if candidate["exists"]:
                first_existing_test = candidate["path"]
                break
        if first_existing_test:
            break

    if not frameworks and first_existing_test:
        suffix = Path(first_existing_test).suffix.lower()
        if suffix == ".py":
            commands.append({"command": f"python3 {first_existing_test}", "reason": "focused Python stdlib test file"})
        elif suffix in {".js", ".mjs", ".cjs"}:
            commands.append({"command": f"node --test {first_existing_test}", "reason": "focused Node test file"})

    class_hint = basename_without_suffix(changed[0]) if changed else "*"
    for framework in frameworks:
        if framework.name == "python":
            target = first_existing_test or first_candidate or "tests"
            commands.append({"command": f"pytest {target}", "reason": "focused Python test path"})
        elif framework.name == "java-maven":
            test_class = f"{class_hint}Test"
            commands.append({"command": f"mvn test -Dtest={test_class}", "reason": "focused Maven test class"})
        elif framework.name == "java-gradle":
            test_class = f"*{class_hint}Test"
            gradle = "./gradlew" if (root / "gradlew").exists() else "gradle"
            commands.append({"command": f"{gradle} test --tests '{test_class}'", "reason": "focused Gradle test filter"})
        elif framework.name == "node":
            target = first_existing_test or first_candidate or ""
            command = f"npm test -- {target}".rstrip()
            commands.append({"command": command, "reason": "focused Node test target"})
        elif framework.name == "dotnet":
            commands.append({"command": f"dotnet test --filter FullyQualifiedName~{class_hint}", "reason": "focused .NET test filter"})
        elif framework.name == "go":
            package = Path(changed[0]).parent.as_posix() if changed else "./..."
            commands.append({"command": f"go test ./{package}" if package not in {"", "."} else "go test ./...", "reason": "focused Go package test"})
    if not commands:
        commands.append({"command": "Use the repo's existing focused test command from README, Makefile, or CI config.", "reason": "no known test framework detected"})
    return commands


def plan(root: Path, changed: list[str], goal: str = "") -> dict[str, Any]:
    root = root.resolve()
    normalized_changed = [relpath((root / item), root) if not Path(item).is_absolute() else relpath(Path(item), root) for item in changed]
    frameworks = detect_frameworks(root)
    likely_tests = infer_test_files(root, normalized_changed)
    helpers = find_existing_helpers(root)
    return {
        "schema_version": "1",
        "type": "test-precision-plan",
        "root": root.as_posix(),
        "goal": goal,
        "changed_files": normalized_changed,
        "detected_frameworks": [
            {"name": item.name, "evidence": item.evidence, "default_commands": item.default_commands} for item in frameworks
        ],
        "likely_test_files": likely_tests,
        "existing_helpers": helpers,
        "risk_tags": classify_risk(goal, normalized_changed),
        "test_case_matrix": test_case_matrix(goal, normalized_changed),
        "focused_validation_commands": focused_commands(root, normalized_changed, frameworks, likely_tests),
        "rules": [
            "Add or update the smallest test that would fail before the code change.",
            "Reuse existing fixtures, factories, helpers, and naming conventions before creating new test scaffolding.",
            "Assert public behavior, outputs, persisted state, or error handling instead of implementation internals.",
            "Keep broad suites, scanners, builds, and vulnerability tools behind explicit user approval.",
            "Do not weaken validation, authorization, escaping, data integrity, or accessibility guards to make tests pass.",
        ],
        "approval": "Review this plan before writing tests or running commands.",
    }


def line_summary(line: str) -> str:
    stripped = " ".join(line.strip().split())
    return stripped[:180]


def discovered_tests(path: Path) -> list[dict[str, Any]]:
    try:
        body = path.read_text(encoding="utf-8")[:MAX_TEST_FILE_BYTES]
    except (OSError, UnicodeDecodeError):
        return []
    rows: list[dict[str, Any]] = []
    lines = body.splitlines()
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        name = ""
        if stripped.startswith("def test_"):
            name = stripped.removeprefix("def ").split("(", 1)[0]
        elif stripped.startswith("public void ") or stripped.startswith("void "):
            candidate = stripped.replace("public void ", "").replace("void ", "").split("(", 1)[0]
            if "test" in candidate.lower() or candidate[:1].isupper():
                name = candidate
        elif stripped.startswith("[Fact]") or stripped.startswith("[Test]"):
            name = f"{stripped} near line {index}"
        elif any(stripped.startswith(prefix) for prefix in ("it(", "it ", "test(", "describe(")):
            name = stripped.split("(", 1)[0].strip() or "javascript test block"
        elif stripped.startswith("func Test"):
            name = stripped.removeprefix("func ").split("(", 1)[0]
        if not name:
            continue
        nearby = []
        for hint in lines[index : min(index + 8, len(lines))]:
            hint_text = hint.strip()
            if any(token in hint_text.lower() for token in ("assert", "expect", "should", "equal", "status", "throws", "error")):
                nearby.append(line_summary(hint_text))
            if len(nearby) >= 3:
                break
        rows.append({"name": name, "line": index, "evidence_hints": nearby})
    return rows


def summarize(root: Path, changed: list[str], goal: str = "") -> dict[str, Any]:
    base = plan(root, changed, goal)
    existing_tests = []
    for row in base["likely_test_files"]:
        for candidate in row["candidates"]:
            if not candidate["exists"]:
                continue
            test_path = root / candidate["path"]
            existing_tests.append(
                {
                    "path": candidate["path"],
                    "changed_file": row["changed_file"],
                    "tests": discovered_tests(test_path),
                }
            )
    covered_hints = []
    for item in existing_tests:
        for test in item["tests"]:
            covered_hints.append(f"{item['path']}:{test['line']} {test['name']}")
    return {
        "schema_version": "1",
        "type": "test-coverage-summary",
        "root": root.resolve().as_posix(),
        "goal": goal,
        "changed_files": base["changed_files"],
        "likely_test_files": base["likely_test_files"],
        "existing_test_files": existing_tests,
        "recommended_test_case_matrix": base["test_case_matrix"],
        "plain_english_summary": {
            "appears_covered": covered_hints,
            "recommended_cases_to_confirm": [f"{row['case']}: {row['purpose']}" for row in base["test_case_matrix"]],
            "missing_or_uncertain": "If a recommended case is not represented by a discovered test name or assertion hint, inspect or add focused coverage before claiming it is tested.",
        },
        "boundary": "This is a heuristic read-only summary of likely test files. It does not execute tests or prove coverage.",
    }


def render_summary_markdown(report: dict[str, Any]) -> str:
    lines = ["# Test Coverage Summary", ""]
    if report["goal"]:
        lines.extend(["## Goal", report["goal"], ""])
    lines.extend(["## Changed Files"])
    lines.extend(f"- {item}" for item in report["changed_files"]) if report["changed_files"] else lines.append("- none supplied")
    lines.append("")
    lines.append("## Existing Test Files Inspected")
    if report["existing_test_files"]:
        for item in report["existing_test_files"]:
            lines.append(f"- `{item['path']}` for `{item['changed_file']}`")
            if item["tests"]:
                for test in item["tests"]:
                    lines.append(f"  - line {test['line']}: {test['name']}")
                    for hint in test["evidence_hints"]:
                        lines.append(f"    - hint: {hint}")
            else:
                lines.append("  - no recognizable test functions or blocks found")
    else:
        lines.append("- no likely existing test files found")
    lines.append("")
    lines.append("## Recommended Cases To Confirm")
    for item in report["recommended_test_case_matrix"]:
        lines.append(f"- {item['case']}: {item['purpose']}")
    lines.append("")
    lines.append("## Boundary")
    lines.append(report["boundary"])
    return "\n".join(lines) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Test Precision Planner", ""]
    if report["goal"]:
        lines.extend(["## Goal", report["goal"], ""])
    lines.extend(["## Changed Files"])
    if report["changed_files"]:
        lines.extend(f"- {item}" for item in report["changed_files"])
    else:
        lines.append("- none supplied; add `--changed path/to/file` for a sharper plan")
    lines.append("")

    lines.append("## Detected Frameworks")
    for framework in report["detected_frameworks"]:
        lines.append(f"- {framework['name']}: evidence {', '.join(framework['evidence'])}")
    if not report["detected_frameworks"]:
        lines.append("- none detected from common manifests")
    lines.append("")

    lines.append("## Likely Test Files")
    for row in report["likely_test_files"]:
        lines.append(f"- {row['changed_file']}")
        if row["candidates"]:
            for candidate in row["candidates"]:
                state = "exists" if candidate["exists"] else "candidate"
                lines.append(f"  - {candidate['path']} ({state})")
        else:
            lines.append("  - no language-specific convention inferred")
    if not report["likely_test_files"]:
        lines.append("- add changed files for likely test placement")
    lines.append("")

    lines.append("## Test Case Matrix")
    for row in report["test_case_matrix"]:
        lines.append(f"- {row['case']}: {row['purpose']} {row['precision']}")
    lines.append("")

    lines.append("## Existing Helpers To Reuse")
    if report["existing_helpers"]:
        lines.extend(f"- {item['path']}: {item['reason']}" for item in report["existing_helpers"])
    else:
        lines.append("- none detected from common helper names")
    lines.append("")

    lines.append("## Focused Validation Commands")
    for command in report["focused_validation_commands"]:
        lines.append(f"- `{command['command']}`: {command['reason']}")
    lines.append("")

    lines.append("## Rules")
    lines.extend(f"- {item}" for item in report["rules"])
    lines.append("")
    lines.append("## Approval")
    lines.append(report["approval"])
    lines.append("TailTrail does not run tests, write files, or create test cases from this command.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan precise tests and focused validation for a repo change.")
    parser.add_argument("action", nargs="?", default="plan", choices=["plan", "summarize"], help="Action to run.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target repo root.")
    parser.add_argument("--changed", action="append", default=[], help="Changed or target file. Repeat for multiple files.")
    parser.add_argument("--goal", default="", help="Optional task goal to sharpen risk and test-case suggestions.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    report = summarize(args.root, args.changed, args.goal) if args.action == "summarize" else plan(args.root, args.changed, args.goal)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    elif args.action == "summarize":
        print(render_summary_markdown(report), end="")
    else:
        print(render_markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
