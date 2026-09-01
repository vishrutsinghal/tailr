#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import release_manifest

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer token", re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/-]{16,}=*")),
    ("secret assignment", re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|secret|token)\b\s*[:=]\s*['\"]?[^'\"\s,;]{12,}")),
)
PRIVATE_PATTERNS = (
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
USER_FACING_DOCS = {"README.md", "QUICKSTART.md", "TAILTRAIL-COMMANDS.md", "USER-GUIDE.md", "COMPLETE-END-TO-END-WORKFLOW.md", "USEFUL-PROMPTS.md", "demo-project-layout/tailtrail-demo-workspace/tailtrail/USER-GUIDE.md"}
UNDERSCORE_MODULE_PATHS = ("scripts/context_receipt.py", "scripts/prompt_profile.py", "scripts/token_budget_coach.py", "scripts/token_telemetry.py")
CAUTION_TERMS = ("not ", "does not", "do not", "never", "without", "unsupported", "disallowed", "only when", "unless", "measured", "evidence", "risky", "avoid", "confirm no")


def cautioned(lines: list[str], index: int) -> bool:
    return any(term in " ".join(lines[max(0, index - 8):min(len(lines), index + 2)]).lower() for term in CAUTION_TERMS)


def audit(root: Path, manifest: dict | None = None) -> list[str]:
    manifest = manifest or release_manifest.load(root)
    findings: list[str] = []
    allowed_urls = manifest["public_audit"]["allowed_repository_urls"]
    for relative in release_manifest.auditable_files(root, manifest):
        body = (root / relative).read_text(encoding="utf-8", errors="replace")
        lines = body.splitlines()
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(body):
                findings.append(f"{relative}:{body.count(chr(10), 0, match.start()) + 1} {label}")
        for reference in release_manifest.repository_reference_findings(body, allowed_urls):
            findings.append(f"{relative}:{body.count(chr(10), 0, body.find(reference)) + 1} unapproved repository reference: {reference}")
        for label, pattern in PRIVATE_PATTERNS:
            for match in pattern.finditer(body):
                line = body.count("\n", 0, match.start()) + 1
                if not cautioned(lines, line - 1):
                    findings.append(f"{relative}:{line} {label}")
        for index, line in enumerate(lines):
            for label, pattern in RISKY_CLAIMS:
                if pattern.search(line) and not cautioned(lines, index):
                    findings.append(f"{relative}:{index + 1} unsupported public claim: {label}")
            if relative in USER_FACING_DOCS:
                for module_path in UNDERSCORE_MODULE_PATHS:
                    if module_path in line:
                        findings.append(f"{relative}:{index + 1} user-facing doc references internal module path: {module_path}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit release-manifest-scoped TailTrail files for private residue and unsupported claims.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    try:
        findings = audit(args.root.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        findings = [f"release manifest could not be loaded: {error}"]
    if args.format == "json":
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
