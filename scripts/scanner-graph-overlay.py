#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tailtrail",
    "__pycache__",
    "aidlc-rules",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "coverage",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "bin",
    "obj",
}

TEXT_EXTENSIONS = {
    ".cs",
    ".csproj",
    ".gradle",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".lock",
    ".md",
    ".properties",
    ".py",
    ".sln",
    ".sql",
    ".tf",
    ".tfvars",
    ".toml",
    ".ts",
    ".tsx",
    ".xml",
    ".yaml",
    ".yml",
}

MANIFEST_NAMES = {
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
    "Dockerfile",
    "sonar-project.properties",
}

SONAR_RULE_PATTERN = re.compile(r"\b(?:[A-Za-z][A-Za-z0-9_-]*:)?S\d+\b")
VULNERABILITY_ID_PATTERN = re.compile(r"\b(CVE-\d{4}-\d{4,}|GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}|CWE-\d+)\b", re.IGNORECASE)
SEVERITY_PATTERN = re.compile(r"\b(BLOCKER|CRITICAL|HIGH|MAJOR|MEDIUM|MODERATE|MINOR|LOW|INFO|INFORMATIONAL)\b", re.IGNORECASE)
PATH_PATTERN = re.compile(r"(?P<path>[\w./\\-]+\.(?:csproj|gradle|java|jsonl|json|jsx|lock|toml|tsx|yaml|yml|xml|sql|kt|js|ts|py|go|cs|rb|php|tf|tfvars|sln|properties))(?::(?P<line>\d+))?")
PACKAGE_PATTERN = re.compile(r"\b(?:package|component|module|dependency|library|artifact|image|resource)\s*[:=]+\s*([@\w./:-]+)", re.IGNORECASE)
FINDING_HINT = re.compile(r"sonar|quality gate|issue|rule|severity|code smell|bug|vulnerab|hotspot|cve-|ghsa-|cwe-|secret|sast|audit|misconfig", re.IGNORECASE)
TEST_HINTS = ("test", "tests", "__tests__", "spec", "specs")
DEFAULT_MAX_INPUT_BYTES = 10 * 1024 * 1024
NOISY_TOKENS = {
    "app",
    "application",
    "build",
    "code",
    "config",
    "data",
    "file",
    "index",
    "main",
    "src",
    "source",
    "test",
    "tests",
    "util",
    "utils",
}
SECRET_ASSIGNMENT_PATTERN = re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|bearer|client[_-]?secret|password|secret|token)\b\s*[:=]\s*['\"]?[^'\"\s,;]+")
BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/-]+=*")
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL)
LONG_SECRET_PATTERN = re.compile(r"\b[A-Za-z0-9+/=_-]{32,}\b")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_size(path: Path, max_bytes: int) -> None:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError(f"Cannot read scanner report `{path}`: {exc}") from exc
    if size > max_bytes:
        raise ValueError(
            f"Scanner report `{path}` is {size} bytes, which exceeds the {max_bytes} byte limit. "
            "Split, filter, or summarize the report before passing it to TailTrail."
        )


def read_lines(path: Path, max_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> list[str]:
    ensure_size(path, max_bytes)
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def read_json(path: Path, max_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> Any | None:
    try:
        ensure_size(path, max_bytes)
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def unique(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def normalize_severity(value: Any) -> list[str]:
    text = str(value or "").strip().upper()
    if not text:
        return []
    if text == "ERROR":
        text = "HIGH"
    elif text in {"WARNING", "WARN"}:
        text = "MEDIUM"
    elif text in {"NOTE", "NONE"}:
        text = "LOW"
    return [text]


def redact_text(value: Any) -> str:
    text = str(value or "")
    text = PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", text)
    text = BEARER_PATTERN.sub("Bearer [REDACTED_TOKEN]", text)
    text = SECRET_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
    text = LONG_SECRET_PATTERN.sub("[REDACTED_SECRET]", text)
    return text


def is_useful_token(token: str) -> bool:
    cleaned = token.strip().lower()
    if len(cleaned) < 4 or cleaned in NOISY_TOKENS:
        return False
    if cleaned.endswith((".py", ".java", ".cs", ".js", ".ts", ".json", ".xml", ".yaml", ".yml", ".tf", ".sql", ".lock")):
        return True
    if re.match(r"^(cve|ghsa|cwe)-", cleaned):
        return True
    return bool(re.search(r"[a-z]", cleaned) and (re.search(r"\d", cleaned) or cleaned not in NOISY_TOKENS))


def trivy_vulnerability_kind(result: dict[str, Any], target: Any) -> str:
    descriptor = " ".join(str(item or "").lower() for item in (result.get("Class"), result.get("Type"), target))
    dependency_markers = {
        "bundler",
        "cargo",
        "composer",
        "gemfile",
        "gobinary",
        "gomod",
        "jar",
        "lang-pkgs",
        "npm",
        "nuget",
        "package-lock.json",
        "pip",
        "pipenv",
        "pnpm",
        "poetry",
        "pom.xml",
        "requirements.txt",
        "yarn",
    }
    if any(marker in descriptor for marker in dependency_markers):
        return "dependency vulnerability"
    if any(marker in descriptor for marker in ("os-pkgs", "container", "image", "docker")):
        return "container/image vulnerability"
    return "dependency/security vulnerability"


def structured_finding(
    *,
    root: Path,
    source: str,
    kind: str,
    report_path: Path,
    source_line: int,
    rules: list[Any],
    vulnerability_ids: list[Any],
    severities: list[Any],
    components: list[Any],
    affected_paths: list[Any],
    evidence: Any,
) -> dict[str, Any]:
    return {
        "source": source,
        "kind": kind,
        "source_file": report_path.as_posix(),
        "source_line": source_line,
        "rules": unique([str(item) for item in rules if item], 8),
        "vulnerability_ids": unique([str(item).upper() for item in vulnerability_ids if item], 8),
        "severities": unique([severity for item in severities for severity in normalize_severity(item)], 4),
        "components": unique([str(item) for item in components if item], 8),
        "affected_paths": unique([normalize_report_path(root, str(item)) for item in affected_paths if item], 8),
        "evidence": redact_text(evidence or "structured scanner finding"),
    }


def safe_relative(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def normalize_report_path(root: Path, value: str) -> str:
    cleaned = value.strip().strip("`'\"")
    if ":" in cleaned and not cleaned.startswith("/") and re.match(r"^[A-Za-z]:", cleaned):
        cleaned = cleaned.replace("\\", "/")
    if ":" in cleaned and not Path(cleaned).exists():
        before_line = cleaned.rsplit(":", 1)[0]
        if Path(before_line).suffix:
            cleaned = before_line
    path = Path(cleaned)
    if path.is_absolute():
        rel = safe_relative(path, root)
        return rel or path.as_posix()
    return cleaned.replace("\\", "/")


def classify_scope(path_text: str) -> str:
    path = Path(path_text)
    lowered = path_text.lower()
    if path.name in MANIFEST_NAMES or path.suffix in {".csproj", ".sln", ".lock", ".gradle"}:
        return "manifest"
    if path.suffix in {".yaml", ".yml", ".json", ".xml", ".properties", ".toml"}:
        return "config"
    if path.suffix in {".tf", ".tfvars"}:
        return "terraform"
    if path.suffix == ".sql":
        return "database"
    if any(f"/{hint}/" in f"/{lowered}/" or path.name.lower().startswith(f"{hint}_") or hint in path.stem.lower() for hint in TEST_HINTS):
        return "test"
    if path.suffix in {".py", ".java", ".cs", ".js", ".ts", ".tsx", ".jsx", ".kt"}:
        return "source"
    return "unknown"


def finding_kind(line: str, source: str) -> str:
    lowered = line.lower()
    if source == "sonar":
        if "hotspot" in lowered or "vulnerab" in lowered or "security" in lowered:
            return "sonar security/static-analysis finding"
        if "quality gate" in lowered:
            return "sonar quality-gate finding"
        return "sonar static-analysis finding"
    if "secret" in lowered:
        return "secret finding"
    if any(term in lowered for term in ("checkov", "tfsec", "terraform", "kubernetes", "cloudformation")):
        return "iac/cloud misconfiguration"
    if any(term in lowered for term in ("semgrep", "codeql", "bandit", "fortify", "checkmarx", "veracode", "sast")):
        return "sast/code vulnerability"
    if any(term in lowered for term in ("trivy", "grype", "image", "container")):
        return "container/image vulnerability"
    return "dependency/security vulnerability"


def extract_severities(line: str) -> list[str]:
    severities: list[str] = []
    for match in SEVERITY_PATTERN.finditer(line):
        raw = match.group(1)
        prefix = line[max(0, match.start() - 18) : match.start()].lower()
        if raw.isupper() or any(term in prefix for term in ("severity", "level", "priority", "risk", "rating")):
            severities.append(raw.upper())
    return unique(severities, 4)


def parse_findings(paths: list[Path], source: str, max_findings: int, root: Path, max_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for report_path in paths:
        structured = parse_structured_findings(report_path, source, max_findings - len(findings), root, max_bytes)
        if structured:
            findings.extend(structured)
            if len(findings) >= max_findings:
                return findings[:max_findings]
            continue
        for line_number, line in enumerate(read_lines(report_path, max_bytes), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            rules = unique([item.upper() if item.upper().startswith(("CVE-", "GHSA-", "CWE-")) else item for item in SONAR_RULE_PATTERN.findall(stripped)], 8)
            ids = unique([item.upper() for item in VULNERABILITY_ID_PATTERN.findall(stripped)], 8)
            severities = extract_severities(stripped)
            packages = unique([match.group(1) for match in PACKAGE_PATTERN.finditer(stripped)], 8)
            affected_paths = unique([normalize_report_path(root, match.group("path")) for match in PATH_PATTERN.finditer(stripped)], 8)
            lowered = stripped.lower()
            if source == "sonar" and not (rules or "quality gate" in lowered or "sonar" in lowered or "code smell" in lowered or "hotspot" in lowered):
                continue
            if source == "vulnerability" and not (ids or packages or ("vulnerab" in lowered or "secret" in lowered or "sast" in lowered or "audit" in lowered or "cwe-" in lowered)):
                continue
            if not FINDING_HINT.search(stripped) and not (rules or ids):
                continue
            key = (source, ",".join(rules + ids + affected_paths + packages), stripped[:120])
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                {
                    "source": source,
                    "kind": finding_kind(stripped, source),
                    "source_file": report_path.as_posix(),
                    "source_line": line_number,
                    "rules": rules,
                    "vulnerability_ids": ids,
                    "severities": severities,
                    "components": packages,
                    "affected_paths": affected_paths,
                    "evidence": redact_text(stripped),
                }
            )
            if len(findings) >= max_findings:
                return findings
    return findings


def parse_structured_findings(report_path: Path, source: str, max_findings: int, root: Path, max_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> list[dict[str, Any]]:
    data = read_json(report_path, max_bytes)
    if not isinstance(data, dict) or max_findings <= 0:
        return []
    if data.get("version") and isinstance(data.get("runs"), list):
        return parse_sarif(report_path, data, source, max_findings, root)
    if source == "vulnerability" and isinstance(data.get("Results"), list):
        return parse_trivy(report_path, data, max_findings, root)
    if source == "vulnerability" and isinstance(data.get("matches"), list):
        return parse_grype(report_path, data, max_findings, root)
    return []


def parse_sarif(report_path: Path, data: dict[str, Any], source: str, max_findings: int, root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for run in data.get("runs", []) if isinstance(data.get("runs"), list) else []:
        if not isinstance(run, dict):
            continue
        driver = run.get("tool", {}).get("driver", {}) if isinstance(run.get("tool"), dict) else {}
        rules = {}
        for rule in driver.get("rules", []) if isinstance(driver.get("rules"), list) else []:
            if isinstance(rule, dict) and rule.get("id"):
                rules[str(rule["id"])] = rule
        for index, result in enumerate(run.get("results", []) if isinstance(run.get("results"), list) else [], start=1):
            if not isinstance(result, dict):
                continue
            rule_id = str(result.get("ruleId", "")).strip()
            rule = rules.get(rule_id, {})
            message = result.get("message", {})
            message_text = message.get("text") if isinstance(message, dict) else message
            locations = result.get("locations", [])
            affected: list[str] = []
            if isinstance(locations, list):
                for location in locations[:4]:
                    physical = location.get("physicalLocation", {}) if isinstance(location, dict) else {}
                    artifact = physical.get("artifactLocation", {}) if isinstance(physical, dict) else {}
                    region = physical.get("region", {}) if isinstance(physical, dict) else {}
                    uri = artifact.get("uri") if isinstance(artifact, dict) else ""
                    line = region.get("startLine") if isinstance(region, dict) else None
                    if uri:
                        affected.append(f"{uri}:{line}" if line else uri)
            properties = {}
            for source_props in (rule.get("properties"), result.get("properties")):
                if isinstance(source_props, dict):
                    properties.update(source_props)
            severity = result.get("level") or properties.get("severity") or properties.get("problem.severity") or properties.get("security-severity")
            kind = "sast/code vulnerability" if source == "vulnerability" else "sonar/static-analysis finding"
            findings.append(
                structured_finding(
                    root=root,
                    source=source,
                    kind=kind,
                    report_path=report_path,
                    source_line=index,
                    rules=[rule_id],
                    vulnerability_ids=[rule_id] if rule_id.upper().startswith(("CVE-", "GHSA-", "CWE-")) else [],
                    severities=[severity],
                    components=[rule.get("name") or rule_id],
                    affected_paths=affected,
                    evidence=message_text or rule_id,
                )
            )
            if len(findings) >= max_findings:
                return findings
    return findings


def parse_trivy(report_path: Path, data: dict[str, Any], max_findings: int, root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in data.get("Results", []) if isinstance(data.get("Results"), list) else []:
        if not isinstance(result, dict):
            continue
        target = result.get("Target")
        for vulnerability in result.get("Vulnerabilities", []) or []:
            if not isinstance(vulnerability, dict):
                continue
            findings.append(
                structured_finding(
                    root=root,
                    source="vulnerability",
                    kind=trivy_vulnerability_kind(result, target),
                    report_path=report_path,
                    source_line=len(findings) + 1,
                    rules=[],
                    vulnerability_ids=[vulnerability.get("VulnerabilityID")],
                    severities=[vulnerability.get("Severity")],
                    components=[vulnerability.get("PkgName")],
                    affected_paths=[target],
                    evidence=vulnerability.get("Title") or vulnerability.get("Description") or vulnerability.get("VulnerabilityID"),
                )
            )
            if len(findings) >= max_findings:
                return findings
        for misconfig in result.get("Misconfigurations", []) or []:
            if not isinstance(misconfig, dict):
                continue
            affected = target
            cause = misconfig.get("CauseMetadata")
            if isinstance(cause, dict) and cause.get("Resource"):
                affected = cause.get("Resource")
            findings.append(
                structured_finding(
                    root=root,
                    source="vulnerability",
                    kind="iac/cloud misconfiguration",
                    report_path=report_path,
                    source_line=len(findings) + 1,
                    rules=[misconfig.get("ID"), misconfig.get("AVDID")],
                    vulnerability_ids=[],
                    severities=[misconfig.get("Severity")],
                    components=[misconfig.get("Type")],
                    affected_paths=[affected],
                    evidence=misconfig.get("Title") or misconfig.get("Message") or misconfig.get("ID"),
                )
            )
            if len(findings) >= max_findings:
                return findings
    return findings


def parse_grype(report_path: Path, data: dict[str, Any], max_findings: int, root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for match in data.get("matches", []) if isinstance(data.get("matches"), list) else []:
        if not isinstance(match, dict):
            continue
        vulnerability = match.get("vulnerability", {}) if isinstance(match.get("vulnerability"), dict) else {}
        artifact = match.get("artifact", {}) if isinstance(match.get("artifact"), dict) else {}
        locations = artifact.get("locations", []) if isinstance(artifact.get("locations"), list) else []
        affected = "not detected"
        if locations and isinstance(locations[0], dict):
            affected = locations[0].get("path") or locations[0].get("layerID") or "not detected"
        findings.append(
            structured_finding(
                root=root,
                source="vulnerability",
                kind="container/image vulnerability",
                report_path=report_path,
                source_line=len(findings) + 1,
                rules=[],
                vulnerability_ids=[vulnerability.get("id")],
                severities=[vulnerability.get("severity")],
                components=[artifact.get("name")],
                affected_paths=[affected],
                evidence=vulnerability.get("description") or vulnerability.get("id"),
            )
        )
        if len(findings) >= max_findings:
            return findings
    return findings


def changed_files(root: Path) -> list[str]:
    result = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def list_candidates(root: Path, limit: int) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if len(files) >= limit:
            break
        if is_skipped(path) or not path.is_file():
            continue
        if path.suffix in TEXT_EXTENSIONS or path.name in MANIFEST_NAMES:
            files.append(path)
    return sorted(files)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def tokens_for(path_text: str, findings: list[dict[str, Any]]) -> list[str]:
    path = Path(path_text)
    tokens = [path.name, path.stem, path_text.replace("/", "."), path_text]
    for finding in findings:
        tokens.extend(finding["rules"])
        tokens.extend(finding["vulnerability_ids"])
        tokens.extend(finding["components"])
    return unique([token for token in tokens if token != "not detected" and is_useful_token(token)], 24)


def looks_like_test(path: Path) -> bool:
    lowered = path.as_posix().lower()
    return any(f"/{hint}/" in f"/{lowered}/" or path.name.lower().startswith(f"{hint}_") or hint in path.stem.lower() for hint in TEST_HINTS)


def related_files(root: Path, path_text: str, findings: list[dict[str, Any]], candidates: list[Path], limit: int) -> tuple[list[dict[str, str]], list[str], list[str]]:
    tokens = tokens_for(path_text, findings)
    related: list[dict[str, str]] = []
    tests: list[str] = []
    manifests: list[str] = []
    target = (root / path_text).resolve()
    for candidate in candidates:
        rel = safe_relative(candidate, root)
        if not rel or candidate.resolve() == target:
            continue
        body = read_text(candidate)
        haystack = f"{rel}\n{body}"
        matched = [token for token in tokens if token and token in haystack]
        if not matched:
            if candidate.name in MANIFEST_NAMES and (classify_scope(path_text) in {"source", "manifest"}):
                manifests.append(rel)
            continue
        reason = "mentions " + ", ".join(matched[:3])
        if looks_like_test(candidate):
            tests.append(rel)
        elif candidate.name in MANIFEST_NAMES:
            manifests.append(rel)
        related.append({"path": rel, "reason": reason})
        if len(related) >= limit:
            break
    return related[:limit], unique(tests, limit), unique(manifests, limit)


def ast_summary(root: Path, path_text: str, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"enabled": False, "symbols": [], "calls": [], "endpoints": [], "db_tables": [], "config_usage": [], "notes": ["AST enrichment skipped by flag."]}
    path = root / path_text
    if not path.is_file():
        return {"enabled": True, "symbols": [], "calls": [], "endpoints": [], "db_tables": [], "config_usage": [], "notes": ["Affected file is not present locally."]}
    command = [sys.executable, (SCRIPTS / "ast-map.py").as_posix(), "--root", root.as_posix(), "--changed", path_text, "--depth", "v1", "--format", "json"]
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return {"enabled": True, "symbols": [], "calls": [], "endpoints": [], "db_tables": [], "config_usage": [], "notes": ["AST enrichment command did not complete."]}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"enabled": True, "symbols": [], "calls": [], "endpoints": [], "db_tables": [], "config_usage": [], "notes": ["AST enrichment output was not JSON."]}
    symbols = data.get("symbols", [])
    return {
        "enabled": True,
        "symbols": [f"{item.get('kind', 'symbol')} {item.get('name', '')} at line {item.get('line', '?')}" for item in symbols[:8]],
        "calls": [f"{item.get('caller', '?')} -> {item.get('callee', '?')}" for item in data.get("call_hints", [])[:8]],
        "endpoints": [str(item.get("route", item)) for item in data.get("endpoints", [])[:6]],
        "db_tables": [str(item.get("table", item)) for item in data.get("db_tables", [])[:6]],
        "config_usage": [str(item.get("key", item.get("source", item))) for item in data.get("config_usage", [])[:6]],
        "notes": [],
    }


def overlay(
    root: Path,
    sonar: list[Path],
    vulnerability: list[Path],
    changed: list[str],
    include_ast: bool,
    max_findings: int,
    max_related: int,
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
) -> dict[str, Any]:
    findings = parse_findings(sonar, "sonar", max_findings, root, max_input_bytes) + parse_findings(vulnerability, "vulnerability", max_findings, root, max_input_bytes)
    by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        for affected in finding["affected_paths"]:
            by_file[affected].append(finding)
    for path_text in changed:
        by_file[path_text]
    if not by_file and not changed:
        for path_text in changed_files(root):
            by_file[path_text]

    candidates = list_candidates(root, 2500)
    impacted_files: list[dict[str, Any]] = []
    for path_text in sorted(by_file):
        file_findings = by_file[path_text]
        related, tests, manifests = related_files(root, path_text, file_findings, candidates, max_related)
        ast = ast_summary(root, path_text, include_ast and classify_scope(path_text) in {"source", "database", "terraform"})
        impacted_files.append(
            {
                "path": path_text,
                "exists": (root / path_text).is_file(),
                "scope": classify_scope(path_text),
                "finding_count": len(file_findings),
                "rules": unique([rule for item in file_findings for rule in item["rules"]], 16),
                "vulnerability_ids": unique([item_id for item in file_findings for item_id in item["vulnerability_ids"]], 16),
                "severities": unique([severity for item in file_findings for severity in item["severities"]], 8),
                "components": unique([component for item in file_findings for component in item["components"]], 16),
                "related_files": related,
                "likely_tests": tests,
                "nearby_manifests": manifests,
                "ast": ast,
                "commands": {
                    "ast_v1": f"python3 scripts/tailtrail.py graph ast --changed {path_text} --depth v1",
                    "review_graph": f"python3 scripts/tailtrail.py graph --changed {path_text}",
                    "code_graph_refresh": f"python3 scripts/tailtrail.py graph refresh --changed {path_text}",
                },
            }
        )

    suggested_read_order = unique(
        [item["path"] for item in impacted_files if item["scope"] in {"manifest", "config"}]
        + [item["path"] for item in impacted_files if item["scope"] in {"source", "database", "terraform"}]
        + [path for item in impacted_files for path in item["likely_tests"]]
        + [item["path"] for item in impacted_files if item["scope"] == "test"]
        + [item["path"] for item in impacted_files],
        24,
    )

    return {
        "type": "tailtrail-scanner-graph-overlay",
        "generated_at": now_utc(),
        "root": root.as_posix(),
        "scanner_inputs": {
            "sonar": [path.as_posix() for path in sonar],
            "vulnerability": [path.as_posix() for path in vulnerability],
        },
        "finding_count": len(findings),
        "findings": findings,
        "impacted_files": impacted_files,
        "suggested_read_order": suggested_read_order,
        "next_actions": next_actions(findings, impacted_files),
        "boundaries": [
            "This overlay reads provided scanner output and local metadata only.",
            "It does not run Sonar, vulnerability scanners, tests, builds, or network queries.",
            "It does not prove findings are fixed; rerun the approved scanner after remediation.",
            "Current scanner output, source code, policy, and guardrails override cached or inferred graph metadata.",
        ],
        "future_candidates": [
            "Provider-specific report parsers for Sonar JSON, dependency-check XML, CycloneDX, SPDX, and additional scanner schemas.",
            "Deeper language-server or AST provider integration when evidence shows simple overlays miss important edges.",
            "Data-flow-lite mapping from endpoints through services to database tables for selected high-risk stacks.",
        ],
    }


def next_actions(findings: list[dict[str, Any]], impacted_files: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    if not findings:
        actions.append("No scanner finding was detected; verify the report path and preserve the exact original scanner output.")
    if impacted_files:
        actions.append("Read the suggested files in order before editing; start with manifests/configs, then source, then tests.")
        actions.append("Use the per-file AST V1 command when a finding touches a source file with unclear call or symbol impact.")
    if any(item["source"] == "vulnerability" for item in findings):
        actions.append("Apply Dependency Gate before package, BOM, lockfile, base image, or scanner-policy changes.")
    if any(item["source"] == "sonar" for item in findings):
        actions.append("Preserve exact Sonar rule IDs and severities in the remediation plan and final validation note.")
    actions.append("Ask for approval before running any scanner, audit, build, or test command.")
    return actions


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Scanner Graph Overlay",
        "",
        f"- Findings detected: {report['finding_count']}",
        f"- Sonar reports: {len(report['scanner_inputs']['sonar'])}",
        f"- Vulnerability reports: {len(report['scanner_inputs']['vulnerability'])}",
        "",
        "## Findings",
        "",
    ]
    if report["findings"]:
        for finding in report["findings"][:24]:
            identifiers = finding["rules"] + finding["vulnerability_ids"]
            identity = ", ".join(f"`{item}`" for item in identifiers) or "`not detected`"
            affected = ", ".join(f"`{item}`" for item in finding["affected_paths"]) or "`not detected`"
            severity = ", ".join(f"`{item}`" for item in finding["severities"]) or "`not detected`"
            lines.extend(
                [
                    f"- {finding['source']} / {finding['kind']}: {identity}",
                    f"  - Severity: {severity}",
                    f"  - Affected: {affected}",
                    f"  - Evidence: `{finding['evidence']}`",
                ]
            )
    else:
        lines.append("- not detected")

    lines.extend(["", "## Impact Overlay", ""])
    if report["impacted_files"]:
        for item in report["impacted_files"]:
            tags = []
            if item["rules"]:
                tags.append("rules " + ", ".join(item["rules"]))
            if item["vulnerability_ids"]:
                tags.append("ids " + ", ".join(item["vulnerability_ids"]))
            if item["severities"]:
                tags.append("severity " + ", ".join(item["severities"]))
            tag_text = "; ".join(tags) or "no direct scanner tag"
            lines.extend(
                [
                    f"### `{item['path']}`",
                    "",
                    f"- Scope: `{item['scope']}`",
                    f"- Exists locally: `{str(item['exists']).lower()}`",
                    f"- Finding count: {item['finding_count']} ({tag_text})",
                ]
            )
            if item["ast"]["symbols"]:
                lines.append("- AST symbols:")
                lines.extend(f"  - `{symbol}`" for symbol in item["ast"]["symbols"])
            if item["ast"]["calls"]:
                lines.append("- AST call hints:")
                lines.extend(f"  - `{call}`" for call in item["ast"]["calls"])
            if item["likely_tests"]:
                lines.append("- Likely tests:")
                lines.extend(f"  - `{test}`" for test in item["likely_tests"])
            if item["related_files"]:
                lines.append("- Related files:")
                lines.extend(f"  - `{related['path']}`: {related['reason']}" for related in item["related_files"][:8])
            if item["nearby_manifests"]:
                lines.append("- Nearby manifests:")
                lines.extend(f"  - `{manifest}`" for manifest in item["nearby_manifests"])
            lines.extend(
                [
                    "- Useful commands:",
                    f"  - `{item['commands']['ast_v1']}`",
                    f"  - `{item['commands']['review_graph']}`",
                    f"  - `{item['commands']['code_graph_refresh']}`",
                    "",
                ]
            )
    else:
        lines.append("- No impacted file could be inferred. Add `--changed path/to/file` or use a report with file paths.")

    lines.extend(["## Suggested Read Order", ""])
    lines.extend(f"- `{item}`" for item in report["suggested_read_order"] or ["not detected"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in report["next_actions"])
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {item}" for item in report["boundaries"])
    lines.extend(["", "## Future Candidates", ""])
    lines.extend(f"- {item}" for item in report["future_candidates"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Overlay Sonar and vulnerability findings onto TailTrail graph impact metadata.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument("--sonar", type=Path, action="append", default=[], help="Local Sonar/static-analysis report text file.")
    parser.add_argument("--vulnerability", type=Path, action="append", default=[], help="Local vulnerability/audit/SAST report text file.")
    parser.add_argument("--changed", action="append", default=[], help="Changed or affected file to include in the overlay.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--max-findings", type=int, default=40)
    parser.add_argument("--max-related", type=int, default=12)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_INPUT_BYTES, help="Maximum scanner report size to read.")
    parser.add_argument("--no-ast", action="store_true", help="Skip AST V1 enrichment for impacted source files.")
    args = parser.parse_args()

    root = args.root.resolve()
    missing = [path.as_posix() for path in [*args.sonar, *args.vulnerability] if not path.is_file()]
    if missing:
        print("Missing scanner report file(s):", file=sys.stderr)
        for item in missing:
            print(f"- {item}", file=sys.stderr)
        return 2

    try:
        report = overlay(root, args.sonar, args.vulnerability, args.changed, not args.no_ast, max(args.max_findings, 1), max(args.max_related, 1), max(args.max_bytes, 1))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
