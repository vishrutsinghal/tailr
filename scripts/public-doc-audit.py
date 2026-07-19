#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".json", ".yml", ".yaml", ".toml"}
SKIP_PARTS = {".git", ".tailtrail", "__pycache__", "aidlc-rules"}
SKIP_FILES = {
    "scripts/public-doc-audit.py",
    "scripts/release-check.py",
}
SECRET_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer token", re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/-]{16,}=*")),
    ("secret assignment", re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|secret|token)\b\s*[:=]\s*['\"]?[^'\"\s,;]{12,}")),
)
PRIVATE_PATTERNS = (
    ("private repository reference", re.compile(r"https?://github\.com/(?!vsingha7_uhg/TailTrail\b)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")),
    ("ssh repository reference", re.compile(r"git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")),
    ("internal placeholder", re.compile(r"\b(REPLACE_WITH_|TODO_SECURITY_CONTACT|INTERNAL_ONLY|PRIVATE_REPO)\b")),
    ("internal company phrasing", re.compile(r"\b(company-internal|internal-only policy|proprietary customer)\b", re.IGNORECASE)),
)
RISKY_CLAIMS = (
    ("guaranteed token savings", re.compile(r"\bguarantee(?:d|s)?\s+token\s+savings?\b", re.IGNORECASE)),
    ("replaces review", re.compile(r"\breplaces?\s+(?:human\s+)?(?:code|security)\s+review\b", re.IGNORECASE)),
    ("replaces CI/tests/scanners", re.compile(r"\breplaces?\s+(?:CI|tests?|scanners?)\b", re.IGNORECASE)),
    ("fully automatic compliance", re.compile(r"\bfully\s+automatic\s+compliance\b", re.IGNORECASE)),
    ("self healing claim", re.compile(r"\bself[- ]heals?\b|\bself[- ]healing\b", re.IGNORECASE)),
)
UNDERSCORE_MODULE_PATHS = (
    "scripts/context_receipt.py",
    "scripts/prompt_profile.py",
    "scripts/token_budget_coach.py",
    "scripts/token_telemetry.py",
)
USER_FACING_DOCS = {
    "README.md",
    "QUICKSTART.md",
    "TAILTRAIL-COMMANDS.md",
    "USER-GUIDE.md",
    "USEFUL-PROMPTS.md",
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/USER-GUIDE.md",
}
CAUTION_TERMS = (
    "not ",
    "does not",
    "do not",
    "do not claim",
    "not designed",
    "never",
    "without",
    "unsupported",
    "disallowed",
    "disallowed claims",
    "only when",
    "unless",
    "measured",
    "evidence",
    "risky",
    "avoid",
    "avoid this wording",
    "confirm no",
)


def files(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.is_file() and path.relative_to(root).as_posix() not in SKIP_FILES and path.suffix in TEXT_SUFFIXES:
            result.append(path)
    return sorted(result)


def cautioned(lines: list[str], index: int) -> bool:
    start = max(0, index - 8)
    end = min(len(lines), index + 2)
    context = " ".join(lines[start:end]).lower()
    return any(term in context for term in CAUTION_TERMS)


def audit(root: Path) -> list[str]:
    findings: list[str] = []
    for path in files(root):
        rel = path.relative_to(root).as_posix()
        body = path.read_text(encoding="utf-8", errors="replace")
        lines = body.splitlines()
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(body):
                line = body.count("\n", 0, match.start()) + 1
                findings.append(f"{rel}:{line} {label}")
        for label, pattern in PRIVATE_PATTERNS:
            for match in pattern.finditer(body):
                line = body.count("\n", 0, match.start()) + 1
                if not cautioned(lines, line - 1):
                    findings.append(f"{rel}:{line} {label}")
        for index, line in enumerate(lines):
            for label, pattern in RISKY_CLAIMS:
                if pattern.search(line) and not cautioned(lines, index):
                    findings.append(f"{rel}:{index + 1} unsupported public claim: {label}")
            if rel in USER_FACING_DOCS:
                for module_path in UNDERSCORE_MODULE_PATHS:
                    if module_path in line:
                        findings.append(f"{rel}:{index + 1} user-facing doc references internal module path: {module_path}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit public TailTrail docs for private residue and unsupported claims.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    findings = audit(args.root.resolve())
    if args.format == "json":
        import json

        print(json.dumps({"type": "public-doc-audit", "findings": findings}, indent=2))
    elif findings:
        print("TailTrail public doc audit failed.", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
    else:
        print("TailTrail public doc audit passed.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
