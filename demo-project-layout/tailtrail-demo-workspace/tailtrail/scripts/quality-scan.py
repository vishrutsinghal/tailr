#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SAFE_LOCAL = "safe local"
NEEDS_APPROVAL = "needs approval"
BLOCKED = "blocked"


def add_command(commands: list[dict[str, str]], command: str, safety: str, reason: str) -> None:
    if any(item["command"] == command for item in commands):
        return
    commands.append({"command": command, "safety": safety, "reason": reason})


def package_scripts(root: Path) -> dict[str, str]:
    package_json = root / "package.json"
    if not package_json.is_file():
        return {}
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        return {}
    return {str(key): str(value) for key, value in scripts.items()}


def make_targets(root: Path) -> set[str]:
    makefile = root / "Makefile"
    if not makefile.is_file():
        return set()
    targets = set()
    for line in makefile.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith(("\t", " ", "#", ".")):
            continue
        if ":" in line:
            target = line.split(":", 1)[0].strip()
            if target:
                targets.add(target)
    return targets


def detect(root: Path, changed: list[str]) -> dict[str, Any]:
    commands: list[dict[str, str]] = []
    signals: list[str] = []
    skipped: list[str] = []

    if (root / "pom.xml").is_file():
        signals.append("pom.xml")
        add_command(commands, "mvn test", SAFE_LOCAL, "Maven project test command.")
        add_command(commands, "mvn verify", NEEDS_APPROVAL, "Broader Maven verification can be slower than focused tests.")
        add_command(commands, "mvn sonar:sonar", NEEDS_APPROVAL, "Sonar Maven execution may require network, credentials, and org setup.")

    if (root / "build.gradle").is_file() or (root / "build.gradle.kts").is_file() or (root / "gradlew").is_file():
        signals.append("Gradle project")
        prefix = "./gradlew" if (root / "gradlew").is_file() else "gradle"
        add_command(commands, f"{prefix} test", SAFE_LOCAL, "Gradle local test command.")
        add_command(commands, f"{prefix} check", NEEDS_APPROVAL, "Broader Gradle verification can be slower than focused tests.")
        add_command(commands, f"{prefix} sonarqube", NEEDS_APPROVAL, "Sonar Gradle execution may require network, credentials, and org setup.")

    scripts = package_scripts(root)
    if scripts:
        signals.append("package.json")
        for name in ("lint", "test", "typecheck"):
            if name in scripts:
                add_command(commands, f"npm run {name}" if name != "test" else "npm test", SAFE_LOCAL, f"package.json defines `{name}`.")
        if "build" in scripts:
            add_command(commands, "npm run build", NEEDS_APPROVAL, "Build can be broader/slower than focused lint or tests.")
        if "audit" in scripts:
            add_command(commands, "npm run audit", NEEDS_APPROVAL, "Audit may use registry/network data and can be noisy.")
    elif (root / "package.json").is_file():
        signals.append("package.json")
        skipped.append("package.json exists but scripts could not be parsed.")

    if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file() or (root / "pytest.ini").is_file() or (root / "tox.ini").is_file():
        signals.append("Python project")
        add_command(commands, "pytest", SAFE_LOCAL, "Python test command when pytest is configured or installed.")
        add_command(commands, "ruff check .", SAFE_LOCAL, "Python lint command when ruff is installed.")
        add_command(commands, "mypy", SAFE_LOCAL, "Python type check command when mypy is configured or installed.")
        add_command(commands, "tox", NEEDS_APPROVAL, "Tox may run broad environments and take longer.")

    if any(root.glob("*.sln")) or any(root.glob("*.csproj")):
        signals.append(".NET project")
        add_command(commands, "dotnet test", SAFE_LOCAL, ".NET local test command.")
        add_command(commands, "dotnet build", SAFE_LOCAL, ".NET local build command.")

    if (root / "go.mod").is_file():
        signals.append("go.mod")
        add_command(commands, "go test ./...", SAFE_LOCAL, "Go local test command.")
        add_command(commands, "go vet ./...", SAFE_LOCAL, "Go local vet command.")

    for name in (".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", "Makefile", "sonar-project.properties"):
        if (root / name).exists():
            signals.append(name)
    if (root / "sonar-project.properties").is_file():
        add_command(commands, "sonar-scanner", NEEDS_APPROVAL, "Local Sonar scanner config exists, but execution may require network, credentials, and org setup.")
    targets = make_targets(root)
    for target in ("lint", "test", "check"):
        if target in targets:
            add_command(commands, f"make {target}", SAFE_LOCAL, f"Makefile defines `{target}` target.")

    if not commands:
        skipped.append("No known local quality command was detected from common manifests.")

    return {
        "type": "quality-scan",
        "root": root.as_posix(),
        "changed": changed,
        "detected_signals": signals,
        "recommended_checks": commands,
        "skipped": skipped,
        "approval": [
            "Review recommended commands before running.",
            "Use `quality run --approved --command \"...\"` only for an exact command you approve.",
            "Do not run deploy, publish, migration, credentialed, or destructive commands through Quality Signal Scanner.",
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Quality Signal Scanner",
        "",
        f"- Root: `{report['root']}`",
        "",
        "## Detected Signals",
        "",
    ]
    lines.extend(f"- {item}" for item in report["detected_signals"] or ["none detected"])
    lines.extend(["", "## Recommended Checks", ""])
    for item in report["recommended_checks"]:
        lines.append(f"- {item['safety']}: `{item['command']}` - {item['reason']}")
    if not report["recommended_checks"]:
        lines.append("- none")
    lines.extend(["", "## Skipped", ""])
    lines.extend(f"- {item}" for item in report["skipped"] or ["none"])
    lines.extend(["", "## Approval", ""])
    lines.extend(f"- {item}" for item in report["approval"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend local quality commands from project manifests without running them.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument("--changed", action="append", default=[], help="Changed or target file path.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    report = detect(args.root.resolve(), args.changed)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
