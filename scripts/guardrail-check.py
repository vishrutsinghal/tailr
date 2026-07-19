#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

ENFORCE_CLASSES = {
    "dependency-gate": "Dependency/manifest change without a Dependency Gate note.",
    "safeguard-removal": "Removed auth, authz, validation, escaping, logging, rate-limit, or test call.",
    "local-state": "Staged file matches TailTrail local-runtime-state patterns.",
    "validation-claim": "Commit/PR text claims validation passed without an evidence marker.",
}

RULE_CLASSES = {
    "dependency-gate-required": "dependency-gate",
    "safeguard-removal-review": "safeguard-removal",
    "local-tailtrail-state-staged": "local-state",
    "validation-claim-needs-evidence": "validation-claim",
}

DEPENDENCY_FILES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "Gemfile",
    "Gemfile.lock",
    "packages.lock.json",
}

SAFEGUARD_FILE_EXTENSIONS = {
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sql",
    ".swift",
    ".tf",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}

LOCAL_STATE_PATTERNS = (
    re.compile(r"^\.tailtrail/.*state.*\.json$"),
    re.compile(r"^\.tailtrail/.*events.*\.jsonl$"),
    re.compile(r"^\.tailtrail/.*scores.*\.jsonl$"),
    re.compile(r"^\.tailtrail/token-usage\.jsonl$"),
    re.compile(r"^\.tailtrail/enterprise-report\.md$"),
    re.compile(r"^\.tailtrail/(quality-runs|vulnerability-runs|task-starts)/"),
    re.compile(r"^\.tailtrail/"),
    re.compile(r"^tailtrail/\.tailtrail-install\.json$"),
    re.compile(r"^tailtrail/"),
    re.compile(r"^aidlc-docs/"),
)

STRICT_LOCAL_INSTALL_FILES = {
    ".github/copilot-instructions.md",
    ".cursor/rules/tailtrail.mdc",
    ".openai/chatgpt-instructions.md",
    "CLAUDE.md",
    "GEMINI.md",
    "AGENTS.md",
    "AIDLC.md",
    "DEPENDENCY-GATE.md",
    "GUARDRAILS.md",
    "GOVERNANCE.md",
    "TOKEN-AUTOPILOT.md",
    "TOKEN-SLICER.md",
    "TAILTRAIL-COMMANDS.md",
    "USEFUL-PROMPTS.md",
    "USER-GUIDE.md",
    "tailtrail-policy.md",
    "tailtrail-policy.example.md",
}

DEPENDENCY_HINT = re.compile(
    r"("
    r"^\s*[\w@./-]+==[\w.*+-]+"
    r"|^\s*[\w@./-]+>=[\w.*+-]+"
    r"|^\s*[\w@./-]+<=[\w.*+-]+"
    r"|^\s*[\w@./-]+~=[\w.*+-]+"
    r"|^\s*['\"][\w@./-]+['\"]\s*:\s*['\"][\w^~><=.*+-]+['\"]"
    r"|<dependency>"
    r"|<groupId>"
    r"|implementation\s+['\"]"
    r"|api\s+['\"]"
    r"|compileOnly\s+['\"]"
    r"|runtimeOnly\s+['\"]"
    r"|cargo\s+"
    r")",
    re.IGNORECASE,
)

GATE_MARKER = re.compile(r"DEPENDENCY-GATE|Dependency Gate|dependency approval|approved dependency|new dependency approved", re.IGNORECASE)

SAFEGUARD_TERMS = (
    "auth",
    "authorization",
    "permission",
    "validate",
    "validation",
    "sanitize",
    "escape",
    "csrf",
    "xss",
    "rate limit",
    "ratelimit",
    "audit",
    "log",
    "rollback",
    "transaction",
    "migration",
    "test",
    "spec",
    "encrypt",
    "decrypt",
    "secret",
    "token",
    "password",
)

VALIDATION_CLAIM = re.compile(
    r"\b("
    r"tests?\s+(?:pass(?:ed|es)?|green|succeed(?:ed)?)"
    r"|validated"
    r"|verified"
    r"|deployed"
    r"|build\s+(?:pass(?:ed|es)?|green|succeed(?:ed)?)"
    r"|lint\s+(?:pass(?:ed|es)?|green|succeed(?:ed)?)"
    r"|all\s+checks\s+(?:pass(?:ed|es)?|green)"
    r")\b",
    re.IGNORECASE,
)

EVIDENCE_MARKER = re.compile(
    r"("
    r"evidence\s*:"
    r"|commands?\s+run\s*:"
    r"|checks?\s+(?:or\s+tests\s+)?run\s*:"
    r"|validation\s*:"
    r"|result\s*:"
    r"|exit\s+code\s*:"
    r"|python3\s+"
    r"|npm\s+"
    r"|mvn\s+"
    r"|gradle\s+"
    r"|pytest"
    r"|go\s+test"
    r"|dotnet\s+test"
    r")",
    re.IGNORECASE,
)


@dataclass
class DiffLine:
    kind: str
    path: str
    line: int
    text: str


@dataclass
class Finding:
    rule: str
    rule_class: str
    severity: str
    path: str
    line: int
    evidence: str
    recommendation: str
    guardrail: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def run_git(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def staged_diff(root: Path) -> str:
    result = run_git(["diff", "--cached", "--unified=3"], root)
    if result.returncode != 0:
        raise SystemExit(result.stderr or "git diff --cached failed")
    return result.stdout


def staged_files(root: Path) -> list[str]:
    result = run_git(["diff", "--cached", "--name-only"], root)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise SystemExit(f"Unable to read {path}: {error}") from error


def parse_diff(diff: str) -> tuple[list[DiffLine], list[str]]:
    lines: list[DiffLine] = []
    files: list[str] = []
    current_path = ""
    old_line = 0
    new_line = 0
    hunk_pattern = re.compile(r"@@ -(?P<old>\d+)(?:,\d+)? \+(?P<new>\d+)(?:,\d+)? @@")

    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            current_path = raw[6:]
            if current_path not in files:
                files.append(current_path)
            continue
        if raw.startswith("+++ /dev/null"):
            current_path = ""
            continue
        hunk = hunk_pattern.match(raw)
        if hunk:
            old_line = int(hunk.group("old"))
            new_line = int(hunk.group("new"))
            continue
        if not current_path:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            lines.append(DiffLine("added", current_path, new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            lines.append(DiffLine("removed", current_path, old_line, raw[1:]))
            old_line += 1
        elif raw.startswith(" "):
            old_line += 1
            new_line += 1
    if not lines and not files:
        for index, raw in enumerate(diff.splitlines(), start=1):
            if raw.startswith("+") and not raw.startswith("+++"):
                text = raw[1:]
                synthetic = DiffLine("added", "package.json", index, text)
                if looks_like_dependency_addition(synthetic):
                    lines.append(synthetic)
                    files.append("package.json")
            elif raw.startswith("-") and not raw.startswith("---"):
                lines.append(DiffLine("removed", "unknown.py", index, raw[1:]))
    return lines, files


def is_dependency_file(path: str) -> bool:
    return Path(path).name in DEPENDENCY_FILES


def looks_like_dependency_addition(line: DiffLine) -> bool:
    text = line.text.strip()
    if not text or text.startswith(("//", "#")):
        return False
    if text in {"{", "}", "[", "]", ","}:
        return False
    return bool(DEPENDENCY_HINT.search(text))


def dependency_gate_present(diff: str, extra_texts: list[str]) -> bool:
    return bool(GATE_MARKER.search("\n".join([diff, *extra_texts])))


def check_dependency_gate(diff_lines: list[DiffLine], diff: str, extra_texts: list[str]) -> list[Finding]:
    if dependency_gate_present(diff, extra_texts):
        return []
    findings: list[Finding] = []
    for line in diff_lines:
        if line.kind != "added" or not is_dependency_file(line.path):
            continue
        if not looks_like_dependency_addition(line):
            continue
        findings.append(
            Finding(
                rule="dependency-gate-required",
                rule_class="dependency-gate",
                severity="high",
                path=line.path,
                line=line.line,
                evidence=line.text.strip(),
                recommendation="Add a Dependency Gate note or explicit dependency approval before committing dependency changes.",
                guardrail="DEPENDENCY-GATE.md",
            )
        )
    return findings


def check_safeguard_removal(diff_lines: list[DiffLine]) -> list[Finding]:
    findings: list[Finding] = []
    for line in diff_lines:
        if line.kind != "removed":
            continue
        if Path(line.path).suffix not in SAFEGUARD_FILE_EXTENSIONS:
            continue
        text = line.text.strip()
        lowered = text.lower()
        if not text or text.startswith(("//", "#", "*")):
            continue
        matched = [term for term in SAFEGUARD_TERMS if term in lowered]
        if not matched:
            continue
        findings.append(
            Finding(
                rule="safeguard-removal-review",
                rule_class="safeguard-removal",
                severity="medium",
                path=line.path,
                line=line.line,
                evidence=text,
                recommendation=f"Review removed safeguard signal `{matched[0]}` and document why protection is preserved or intentionally changed.",
                guardrail="GUARDRAILS.md",
            )
        )
    return findings


def is_tailtrail_source_checkout(root: Path) -> bool:
    return (root / ".codex-plugin" / "plugin.json").is_file() and (root / "skills" / "tailtrail" / "SKILL.md").is_file()


def local_state_path(path: str, root: Path) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("tailtrail-meta/"):
        return False
    if normalized in STRICT_LOCAL_INSTALL_FILES and not is_tailtrail_source_checkout(root):
        return True
    return any(pattern.search(normalized) for pattern in LOCAL_STATE_PATTERNS)


def check_local_state(files: list[str], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not local_state_path(path, root):
            continue
        findings.append(
            Finding(
                rule="local-tailtrail-state-staged",
                rule_class="local-state",
                severity="high",
                path=path,
                line=1,
                evidence=path,
                recommendation="Remove local TailTrail install/runtime files from the commit or add the appropriate .gitignore rule. Commit only reviewed tailtrail-meta/ metadata by default.",
                guardrail="GUARDRAILS.md",
            )
        )
    return findings


def check_validation_claims(texts: list[tuple[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    for source, body in texts:
        if not body.strip():
            continue
        has_evidence = bool(EVIDENCE_MARKER.search(body))
        for index, line in enumerate(body.splitlines(), start=1):
            if not VALIDATION_CLAIM.search(line):
                continue
            if has_evidence:
                continue
            findings.append(
                Finding(
                    rule="validation-claim-needs-evidence",
                    rule_class="validation-claim",
                    severity="high",
                    path=source,
                    line=index,
                    evidence=line.strip(),
                    recommendation="Add command/result evidence or reword the claim as not yet validated.",
                    guardrail="GUARDRAILS.md",
                )
            )
    return findings


def load_policy_notes(root: Path) -> list[str]:
    notes: list[str] = []
    path = root / ".tailtrail" / "policy-overrides.json"
    if not path.is_file():
        return notes
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return notes
    guardrail = value.get("guardrail_check")
    if isinstance(guardrail, dict):
        allow_notes = guardrail.get("notes")
        if isinstance(allow_notes, list):
            notes.extend(str(item) for item in allow_notes)
    return notes


def parse_fail_on(value: str | None) -> list[str]:
    if not value:
        return []
    classes = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in classes if item not in ENFORCE_CLASSES]
    if unknown:
        allowed = ", ".join(sorted(ENFORCE_CLASSES))
        raise SystemExit(f"Unknown --fail-on class: {', '.join(unknown)}. Allowed classes: {allowed}")
    return sorted(set(classes))


def blocked_by_fail_on(findings: list[Finding], fail_on_classes: list[str]) -> list[Finding]:
    selected = set(fail_on_classes)
    return [item for item in findings if item.rule_class in selected]


def enforcement_mode(enforce: bool, fail_on_classes: list[str]) -> str:
    if enforce and fail_on_classes:
        return "enforce+fail-on:" + ",".join(fail_on_classes)
    if enforce:
        return "enforce"
    if fail_on_classes:
        return "fail-on:" + ",".join(fail_on_classes)
    return "advisory"


def report(findings: list[Finding], enforce: bool, fail_on_classes: list[str]) -> dict[str, Any]:
    high_count = sum(1 for item in findings if item.severity == "high")
    fail_on_blocking = blocked_by_fail_on(findings, fail_on_classes)
    severity_blocking = [item for item in findings if enforce and item.severity == "high"]
    blocking_rules = {(item.rule, item.path, item.line) for item in [*fail_on_blocking, *severity_blocking]}
    blocking_count = len(blocking_rules)
    return {
        "type": "tailtrail-guardrail-check",
        "status": "failed" if blocking_count else "passed",
        "mode": "fail-on" if fail_on_classes and not enforce else "enforce" if enforce and not fail_on_classes else "enforce+fail-on" if enforce else "advisory",
        "mode_label": enforcement_mode(enforce, fail_on_classes),
        "enforce": enforce,
        "fail_on_classes": fail_on_classes,
        "finding_count": len(findings),
        "high_count": high_count,
        "blocking_count": blocking_count,
        "findings": [item.as_dict() for item in findings],
        "boundaries": [
            "This is a deterministic local check, not a complete code review.",
            "Advisory mode does not block commits.",
            "Enforce mode blocks only high-severity findings.",
            "Current source, project policy, reviewers, tests, CI, and security scanners still win.",
        ],
    }


def markdown(data: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Guardrail Check",
        "",
        f"- Mode: {data['mode_label']}",
        f"- Enforce (severity gate): {'on' if data['enforce'] else 'off'}",
        f"- Status: `{data['status']}`",
        f"- Findings: {data['finding_count']} ({data['blocking_count']} blocking, {data['finding_count'] - data['blocking_count']} advisory)",
        f"- High severity: {data['high_count']}",
        "",
        "## Findings",
        "",
    ]
    if data["findings"]:
        for item in data["findings"]:
            lines.extend(
                [
                    f"### {item['rule']}",
                    "",
                    f"- Class: `{item['rule_class']}`",
                    f"- Severity: `{item['severity']}`",
                    f"- Location: `{item['path']}:{item['line']}`",
                    f"- Evidence: `{item['evidence']}`",
                    f"- Guardrail: `{item['guardrail']}`",
                    f"- Recommendation: {item['recommendation']}",
                    "",
                ]
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {item}" for item in data["boundaries"])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check high-value TailTrail guardrails against a diff and optional commit/PR text.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument("--diff", type=Path, help="Patch/diff file to inspect. Defaults to staged git diff.")
    parser.add_argument("--commit-message", type=Path, help="Commit message file to check for validation claims.")
    parser.add_argument("--pr-body", type=Path, help="PR body file to check for validation claims.")
    parser.add_argument("--enforce", action="store_true", help="Return non-zero when high-severity findings are present.")
    parser.add_argument("--fail-on", help="Comma-separated guardrail classes to enforce: dependency-gate,safeguard-removal,local-state,validation-claim.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    fail_on_classes = parse_fail_on(args.fail_on)
    root = args.root.resolve()
    if args.diff:
        diff = read_text(args.diff)
        staged = []
    else:
        diff = staged_diff(root)
        staged = staged_files(root)
    diff_lines, diff_files = parse_diff(diff)
    files = sorted(set([*staged, *diff_files]))
    claim_texts: list[tuple[str, str]] = []
    if args.commit_message:
        claim_texts.append((args.commit_message.as_posix(), read_text(args.commit_message)))
    if args.pr_body:
        claim_texts.append((args.pr_body.as_posix(), read_text(args.pr_body)))
    extra_texts = [*load_policy_notes(root), *[body for _, body in claim_texts]]

    findings = []
    findings.extend(check_dependency_gate(diff_lines, diff, extra_texts))
    findings.extend(check_safeguard_removal(diff_lines))
    findings.extend(check_local_state(files, root))
    findings.extend(check_validation_claims(claim_texts))

    data = report(findings, args.enforce, fail_on_classes)
    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(markdown(data), end="")
    return 1 if data["blocking_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
