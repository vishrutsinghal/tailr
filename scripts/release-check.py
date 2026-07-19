#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PUBLIC_FILES = (
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/docs_feedback.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/ISSUE_TEMPLATE/security_note.md",
    ".github/pull_request_template.md",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "DEMO.md",
    "LICENSE",
    "NOTICE.md",
    "PUBLIC-CLAIMS.md",
    "PUBLIC-RELEASE-METADATA.md",
    "PUBLIC-ROADMAP.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "RELEASE-CHECKLIST.md",
    "README.md",
    "USER-GUIDE.md",
    "VERSIONING.md",
    "scripts/public-doc-audit.py",
    "scripts/smoke-test.py",
)
FORBIDDEN_TRACKED_SUFFIXES = (
    ".DS_Store",
    "__pycache__",
)
FORBIDDEN_TRACKED_PARTS = (
    ".tailtrail",
)
PUBLIC_BLOCKERS = tuple(["REPLACE_WITH_PUBLIC_" + "SECURITY_CONTACT"])
PUBLIC_REPO_PATTERNS = (
    re.compile(r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"),
    re.compile(r"git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"),
)
PUBLIC_CLAIM_FILES = (
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "DEMO.md",
    "PUBLIC-ROADMAP.md",
    "README.md",
    "USER-GUIDE.md",
    "TAILTRAIL-COMMANDS.md",
    "RELEASE-CHECKLIST.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    "VERSIONING.md",
)
RISKY_CLAIM_PATTERNS = (
    ("guaranteed token savings", re.compile(r"\bguarantee(?:d|s)?\s+token\s+savings?\b", re.IGNORECASE)),
    ("guaranteed code quality", re.compile(r"\bguarantee(?:d|s)?\s+code\s+quality\b", re.IGNORECASE)),
    ("fully automatic compliance", re.compile(r"\bfully\s+automatic\s+compliance\b", re.IGNORECASE)),
    ("replaces CI", re.compile(r"\breplaces?\s+(?:your\s+)?CI\b", re.IGNORECASE)),
    ("replaces tests", re.compile(r"\breplaces?\s+(?:your\s+)?tests?\b", re.IGNORECASE)),
    ("replaces code review", re.compile(r"\breplaces?\s+(?:human\s+)?code\s+review\b", re.IGNORECASE)),
    ("replaces security review", re.compile(r"\breplaces?\s+(?:human\s+)?security\s+review\b", re.IGNORECASE)),
    ("replaces scanners", re.compile(r"\breplaces?\s+(?:SAST|dependency|vulnerability|secret|security)?\s*scanners?\b", re.IGNORECASE)),
    ("proves vulnerabilities are fixed", re.compile(r"\bproves?\s+vulnerabilit(?:y|ies)\s+(?:are\s+)?fixed\b", re.IGNORECASE)),
    ("self-healing without review", re.compile(r"\bself[- ]heals?\b|\bself[- ]healing\b", re.IGNORECASE)),
    ("automatic policy enforcement everywhere", re.compile(r"\bautomatically\s+enforces?\s+(?:organization\s+)?policy\s+everywhere\b", re.IGNORECASE)),
)
EXACT_SAVINGS_PATTERN = re.compile(r"\bexact\s+(?:token\s+)?savings?\b", re.IGNORECASE)
CAUTION_TERMS = (
    "not ",
    "does not",
    "do not",
    "never",
    "without",
    "avoid",
    "disallow",
    "disallowed",
    "unsupported",
    "fail on",
    "fails on",
    "should fail",
    "risky phrase",
    "release check",
    "only when",
    "unless",
    "measured",
    "telemetry",
    "evidence",
)


def git_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        files: list[str] = []
        for path in ROOT.rglob("*"):
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.is_file():
                files.append(path.relative_to(ROOT).as_posix())
        return sorted(files)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check_required(errors: list[str]) -> None:
    for item in REQUIRED_PUBLIC_FILES:
        if not (ROOT / item).is_file():
            errors.append(f"missing public release file: {item}")


def check_manifest(errors: list[str]) -> None:
    manifest_path = ROOT / ".codex-plugin" / "plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        errors.append(f"invalid plugin manifest JSON: {error}")
        return
    if manifest.get("license") != "Apache-2.0":
        errors.append(".codex-plugin/plugin.json license must be Apache-2.0 for the public release")


def check_license_provenance(errors: list[str]) -> None:
    license_body = read("LICENSE")
    notice_body = read("NOTICE.md")
    metadata_body = read("PUBLIC-RELEASE-METADATA.md")
    manifest = json.loads(read(".codex-plugin/plugin.json"))

    if not license_body.startswith("Apache License\nVersion 2.0"):
        errors.append("LICENSE must contain Apache License 2.0 text for the public release")
    if "Public license: Apache-2.0." not in metadata_body:
        errors.append("PUBLIC-RELEASE-METADATA.md must record Apache-2.0 as the public license")
    if "Expected manifest value: `Apache-2.0`." not in metadata_body:
        errors.append("PUBLIC-RELEASE-METADATA.md must record the expected plugin manifest license")
    if manifest.get("license") not in metadata_body:
        errors.append("plugin manifest license must match PUBLIC-RELEASE-METADATA.md")
    if "Copyright 2026 TailTrail project maintainers." not in notice_body:
        errors.append("NOTICE.md must include the TailTrail copyright holder text")
    if "does not vendor third-party source code, assets, or documentation" not in notice_body:
        errors.append("NOTICE.md must include the third-party vendoring provenance statement")


def check_tracked_files(errors: list[str]) -> None:
    for file in git_files():
        parts = set(Path(file).parts)
        if any(file.endswith(suffix) for suffix in FORBIDDEN_TRACKED_SUFFIXES):
            errors.append(f"tracked local artifact should be removed: {file}")
        if parts.intersection(FORBIDDEN_TRACKED_PARTS):
            errors.append(f"tracked local TailTrail state should be removed: {file}")


def check_public_blockers(errors: list[str]) -> None:
    for file in git_files():
        path = ROOT / file
        if not path.is_file():
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in PUBLIC_BLOCKERS:
            if marker in body:
                errors.append(f"{file} contains public release blocker marker: {marker}")
        for pattern in PUBLIC_REPO_PATTERNS:
            if pattern.search(body):
                errors.append(f"{file} contains a direct public repository reference")


def cautious_context(lines: list[str], index: int) -> str:
    start = max(0, index - 1)
    end = min(len(lines), index + 2)
    nearby = lines[start:end]
    previous_heading = []
    for previous in range(index - 1, max(-1, index - 6), -1):
        text = lines[previous].strip()
        if text:
            previous_heading.append(text)
        if text.endswith(":") or text.startswith("#"):
            break
    return " ".join([*reversed(previous_heading), *nearby]).lower()


def is_cautioned(lines: list[str], index: int) -> bool:
    context = cautious_context(lines, index)
    return any(term in context for term in CAUTION_TERMS)


def check_public_claims(errors: list[str]) -> None:
    for file in PUBLIC_CLAIM_FILES:
        path = ROOT / file
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            for label, pattern in RISKY_CLAIM_PATTERNS:
                if pattern.search(line) and not is_cautioned(lines, index):
                    errors.append(f"{file}:{index + 1} contains unsupported public claim ({label})")
            if EXACT_SAVINGS_PATTERN.search(line) and not is_cautioned(lines, index):
                errors.append(f"{file}:{index + 1} mentions exact savings without measured telemetry wording")


def check_public_doc_audit(errors: list[str]) -> None:
    audit_script = ROOT / "scripts" / "public-doc-audit.py"
    result = subprocess.run([sys.executable, audit_script.as_posix(), "--root", ROOT.as_posix()], cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        errors.append(f"public documentation audit failed: {details}")


def main() -> int:
    errors: list[str] = []
    check_required(errors)
    check_manifest(errors)
    check_license_provenance(errors)
    check_tracked_files(errors)
    check_public_blockers(errors)
    check_public_claims(errors)
    check_public_doc_audit(errors)

    if errors:
        print("TailTrail release check failed.", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("TailTrail release check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
