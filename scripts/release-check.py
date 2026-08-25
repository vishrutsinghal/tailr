#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import release_manifest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BLOCKERS = ("REPLACE_WITH_PUBLIC_" + "SECURITY_CONTACT",)
PUBLIC_CLAIM_FILES = ("ARCHITECTURE.md", "CHANGELOG.md", "DEMO.md", "PUBLIC-ROADMAP.md", "README.md", "USER-GUIDE.md", "TAILTRAIL-COMMANDS.md", "RELEASE-CHECKLIST.md", "SECURITY.md", "SUPPORT.md", "CONTRIBUTING.md", "VERSIONING.md")
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
)
EXACT_SAVINGS_PATTERN = re.compile(r"\bexact\s+(?:token\s+)?savings?\b", re.IGNORECASE)
CAUTION_TERMS = ("not ", "does not", "do not", "never", "without", "avoid", "disallow", "unsupported", "fail on", "only when", "unless", "measured", "telemetry", "evidence")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check_claims(errors: list[str]) -> None:
    for file in PUBLIC_CLAIM_FILES:
        path = ROOT / file
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            context = " ".join(lines[max(0, index - 6):min(len(lines), index + 2)]).lower()
            cautioned = any(term in context for term in CAUTION_TERMS)
            for label, pattern in RISKY_CLAIM_PATTERNS:
                if pattern.search(line) and not cautioned:
                    errors.append(f"{file}:{index + 1} contains unsupported public claim ({label})")
            if EXACT_SAVINGS_PATTERN.search(line) and not cautioned:
                errors.append(f"{file}:{index + 1} mentions exact savings without measured telemetry wording")


def check_license(errors: list[str]) -> None:
    plugin = json.loads(read(".codex-plugin/plugin.json"))
    if plugin.get("license") != "Apache-2.0":
        errors.append(".codex-plugin/plugin.json license must be Apache-2.0")
    if not read("LICENSE").startswith("Apache License\nVersion 2.0"):
        errors.append("LICENSE must contain Apache License 2.0 text")
    if "Public license: Apache-2.0." not in read("PUBLIC-RELEASE-METADATA.md"):
        errors.append("PUBLIC-RELEASE-METADATA.md must record Apache-2.0")
    if "Copyright 2026 TailTrail project maintainers." not in read("NOTICE.md"):
        errors.append("NOTICE.md must include the TailTrail copyright holder text")


def main() -> int:
    try:
        manifest = release_manifest.load(ROOT)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"TailTrail release check failed.\n- invalid release manifest: {error}", file=sys.stderr)
        return 1
    candidate = release_manifest.candidate_files(ROOT, manifest)
    tracked_existing = [path for path in release_manifest.git_files(ROOT) if (ROOT / path).is_file()]
    errors = release_manifest.validate(ROOT, manifest, tracked_existing)
    for file in candidate:
        path = ROOT / file
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for blocker in PUBLIC_BLOCKERS:
            if blocker in body:
                errors.append(f"{file} contains public release blocker marker: {blocker}")
    check_license(errors)
    check_claims(errors)
    audit = subprocess.run([sys.executable, "scripts/public-doc-audit.py", "--root", ROOT.as_posix()], cwd=ROOT, text=True, capture_output=True, check=False)
    if audit.returncode:
        errors.append(f"public documentation audit failed: {(audit.stderr or audit.stdout).strip()}")
    if errors:
        print("TailTrail release check failed.", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"TailTrail release check passed ({len(candidate)} candidate files, manifest v{manifest['schema_version']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
