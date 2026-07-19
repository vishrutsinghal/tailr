#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BLOCKED_TOKENS = {
    "deploy",
    "publish",
    "release",
    "upload",
    "push",
    "rm",
    "rmdir",
    "del",
    "delete",
    "drop",
    "destroy",
    "migrate",
    "apply",
    "terraform",
    "kubectl",
    "helm",
    "aws",
    "gcloud",
    "az",
    "scp",
    "ssh",
}

NETWORKISH_TOKENS = {
    "sonar-scanner",
    "sonar:sonar",
    "sonarqube",
    "audit",
    "snyk",
    "trivy",
    "grype",
    "pip-audit",
    "osv-scanner",
    "dependency-check",
}

ALLOWED_ROOTS = {
    "mvn",
    "gradle",
    "./gradlew",
    "npm",
    "yarn",
    "pnpm",
    "pytest",
    "tox",
    "ruff",
    "mypy",
    "dotnet",
    "go",
    "make",
    "cargo",
    "sonar-scanner",
}

ALLOWED_PYTHON_MODULES = {"pytest", "ruff", "mypy", "tox"}


def classify(command: str) -> dict[str, Any]:
    try:
        parts = shlex.split(command)
    except ValueError as error:
        return {"allowed": False, "classification": "blocked", "reasons": [f"Command could not be parsed: {error}"], "parts": []}
    lowered = [part.lower() for part in parts]
    reasons = []
    if not parts:
        reasons.append("Command is empty.")
    root = lowered[0] if lowered else ""
    if root not in ALLOWED_ROOTS:
        if root in {"python", "python3"} and len(lowered) >= 3 and lowered[1] == "-m" and lowered[2] in ALLOWED_PYTHON_MODULES:
            pass
        else:
            reasons.append("Command root is not in the local quality-tool allowlist.")
    blocked = sorted(token for token in BLOCKED_TOKENS if token in lowered)
    networkish = sorted(token for token in NETWORKISH_TOKENS if any(token in part for part in lowered))
    if blocked:
        reasons.append("Blocked token detected: " + ", ".join(blocked))
    classification = "needs approval" if networkish else "safe local"
    if networkish:
        reasons.append("Potential scanner/network/credential token detected: " + ", ".join(networkish))
    return {
        "allowed": bool(parts and not blocked and not any("allowlist" in reason for reason in reasons)),
        "classification": "blocked" if blocked or not parts or any("allowlist" in reason for reason in reasons) else classification,
        "reasons": reasons or ["No blocked token detected."],
        "parts": parts,
    }


def output_path(root: Path) -> Path:
    directory = root / ".tailtrail" / "quality-runs"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return directory / f"quality-run-{stamp}.log"


def run_quality(root: Path, command: str, approved: bool, timeout: int) -> tuple[dict[str, Any], int]:
    safety = classify(command)
    if not approved:
        return {
            "type": "quality-run",
            "status": "not run",
            "command": command,
            "classification": safety["classification"],
            "reasons": ["Missing --approved. Quality commands only run after explicit approval.", *safety["reasons"]],
        }, 2
    if not safety["allowed"]:
        return {
            "type": "quality-run",
            "status": "blocked",
            "command": command,
            "classification": safety["classification"],
            "reasons": safety["reasons"],
        }, 2

    try:
        result = subprocess.run(safety["parts"], cwd=root, text=True, capture_output=True, check=False, timeout=timeout)
    except FileNotFoundError as error:
        return {
            "type": "quality-run",
            "status": "failed",
            "command": command,
            "classification": safety["classification"],
            "exit_code": 127,
            "reasons": [f"Command executable was not found: {error.filename}"],
            "next_actions": ["Install or use the repo-approved local quality tool, then rerun the exact approved command."],
        }, 127
    except subprocess.TimeoutExpired:
        return {
            "type": "quality-run",
            "status": "failed",
            "command": command,
            "classification": safety["classification"],
            "exit_code": 124,
            "reasons": [f"Command timed out after {timeout} seconds."],
            "next_actions": ["Rerun with a larger timeout only if the user approves the longer command."],
        }, 124
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    destination = output_path(root)
    destination.write_text(combined, encoding="utf-8")
    report = {
        "type": "quality-run",
        "status": "passed" if result.returncode == 0 else "failed",
        "command": command,
        "classification": safety["classification"],
        "exit_code": result.returncode,
        "output_file": destination.as_posix(),
        "first_output_lines": combined.splitlines()[:20],
        "next_actions": [
            "Use `ci summarize --file` for build/test/lint output when noisy.",
            "Use `sonar summarize --file` if the output is Sonar/static-analysis evidence.",
            "Do not claim quality gates pass unless this command is the relevant gate and exited 0.",
        ],
    }
    return report, result.returncode


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Quality Run",
        "",
        f"- Status: {report['status']}",
        f"- Command: `{report['command']}`",
        f"- Classification: {report['classification']}",
    ]
    if "exit_code" in report:
        lines.append(f"- Exit code: {report['exit_code']}")
    if "output_file" in report:
        lines.append(f"- Output file: `{report['output_file']}`")
    lines.extend(["", "## Reasons", ""])
    lines.extend(f"- {item}" for item in report.get("reasons", ["Command executed after approval."]))
    if report.get("first_output_lines"):
        lines.extend(["", "## First Output Lines", ""])
        lines.extend(f"- `{item}`" for item in report["first_output_lines"])
    if report.get("next_actions"):
        lines.extend(["", "## Next Actions", ""])
        lines.extend(f"- {item}" for item in report["next_actions"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one explicitly approved local quality command and save output.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root where the command should run.")
    parser.add_argument("--command", required=True, help="Exact command to run.")
    parser.add_argument("--approved", action="store_true", help="Required confirmation that the user approved this exact command.")
    parser.add_argument("--timeout", type=int, default=120, help="Command timeout in seconds.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    report, code = run_quality(args.root.resolve(), args.command, args.approved, args.timeout)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(markdown(report), end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
