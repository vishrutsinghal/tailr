#!/usr/bin/env python3
"""Enforce TailTrail repository policy and emit stable JSON/SARIF findings."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = "tailtrail-enforcement-policy.json"
SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}
LOCKED_RULES = {"approval-scope", "evidence-truth", "stale-completion", "dependency-decision", "safeguard-preservation", "local-state", "redaction", "release-manifest"}
SECRET_PATTERNS = (
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("generic credential", re.compile(r"(?i)\b(?:password|secret|api[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
)


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, PACKAGE_ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GUARD = load_script("tailtrail_e6_guard", "guardrail-check.py")
DEPENDENCY = load_script("tailtrail_e6_dependency", "dependency-decision.py")


@dataclass
class Finding:
    rule_id: str
    classification: str
    severity: str
    path: str
    line: int
    message: str
    evidence: str
    remediation: str
    state: str = "new"
    blocking: bool = False
    fingerprint: str = ""

    def finalize(self) -> "Finding":
        normalized = "\0".join((self.rule_id, self.path.replace("\\", "/"), str(self.line), self.message, self.evidence))
        self.fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return self

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def validate_policy(value: Any) -> list[str]:
    issues: list[str] = []
    required = {"schema_version", "type", "policy_version", "minimum_tailtrail_version", "rules", "evidence", "approval", "dependency", "baseline", "suppressions", "limits"}
    if not isinstance(value, dict):
        return ["policy must be an object"]
    if set(value) != required:
        issues.append(f"policy fields must be exactly {sorted(required)}")
    if value.get("schema_version") != "1" or value.get("type") != "tailtrail-repository-enforcement-policy" or value.get("policy_version") != 1:
        issues.append("policy identity must be schema v1, repository-enforcement type, policy version 1")
    rules = value.get("rules")
    if not isinstance(rules, dict) or not rules:
        issues.append("rules must be a non-empty object")
        rules = {}
    missing = LOCKED_RULES - set(rules)
    if missing:
        issues.append(f"policy missing locked Core rules: {sorted(missing)}")
    for rule_id, rule in rules.items():
        if not isinstance(rule, dict):
            issues.append(f"rule {rule_id} must be an object")
            continue
        allowed = {"classification", "enabled", "severity", "protected_paths"}
        required_rule = {"classification", "enabled", "severity"}
        if not required_rule <= set(rule) or set(rule) - allowed:
            issues.append(f"rule {rule_id} has incompatible fields")
        if rule.get("classification") not in {"enforced", "host-assisted", "advisory"} or rule.get("severity") not in SEVERITY_RANK or not isinstance(rule.get("enabled"), bool):
            issues.append(f"rule {rule_id} has invalid classification, severity, or enabled value")
        if rule_id in LOCKED_RULES and (rule.get("classification") != "enforced" or rule.get("enabled") is not True):
            issues.append(f"locked Core rule {rule_id} must remain enabled and enforced")
        protected_paths = rule.get("protected_paths")
        if protected_paths is not None and (not isinstance(protected_paths, list) or not protected_paths or not all(isinstance(item, str) and item for item in protected_paths)):
            issues.append(f"rule {rule_id} protected_paths must be a non-empty list of strings")
    suppressions = value.get("suppressions", {})
    if not isinstance(suppressions, dict) or suppressions.get("allow_high_severity") is not False:
        issues.append("high-severity suppression must remain disabled")
    for section, keys in (("approval", {"directory", "maximum_age_days"}), ("dependency", {"decision_directory"}), ("baseline", {"path"}), ("suppressions", {"path", "maximum_days", "allow_high_severity"}), ("limits", {"maximum_diff_bytes", "maximum_findings"}), ("evidence", {"markers"})):
        item = value.get(section)
        if not isinstance(item, dict) or set(item) != keys:
            issues.append(f"policy section {section} has incompatible fields")
    strings = (("approval", "directory"), ("dependency", "decision_directory"), ("baseline", "path"), ("suppressions", "path"))
    for section, key in strings:
        item = value.get(section, {})
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item.get(key):
            issues.append(f"policy {section}.{key} must be a non-empty string")
    markers = value.get("evidence", {}).get("markers") if isinstance(value.get("evidence"), dict) else None
    if not isinstance(markers, list) or not markers or not all(isinstance(item, str) and item for item in markers):
        issues.append("policy evidence.markers must be a non-empty list of strings")
    numeric = (("approval", "maximum_age_days", 1, 365), ("suppressions", "maximum_days", 1, 90), ("limits", "maximum_diff_bytes", 1024, None), ("limits", "maximum_findings", 1, 10000))
    for section, key, minimum, maximum in numeric:
        item = value.get(section, {})
        number = item.get(key) if isinstance(item, dict) else None
        if not isinstance(number, int) or isinstance(number, bool) or number < minimum or (maximum is not None and number > maximum):
            issues.append(f"policy {section}.{key} is outside its supported integer range")
    return issues


def merge_override(policy: dict[str, Any], override: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    result = copy.deepcopy(policy)
    issues: list[str] = []
    if set(override) - {"schema_version", "type", "policy_version", "rules", "limits"}:
        issues.append("override contains unsupported fields")
    if override.get("schema_version") != "1" or override.get("type") != "tailtrail-repository-enforcement-override" or override.get("policy_version") != 1:
        issues.append("override identity is incompatible with policy version 1")
        return result, issues
    for rule_id, changed in override.get("rules", {}).items():
        if rule_id not in result["rules"] or not isinstance(changed, dict):
            issues.append(f"override references unknown rule {rule_id}")
            continue
        current = result["rules"][rule_id]
        local_issues: list[str] = []
        if set(changed) - {"classification", "enabled", "severity", "protected_paths"}:
            local_issues.append(f"override has unsupported fields for {rule_id}")
        if changed.get("enabled") is False and rule_id in LOCKED_RULES:
            local_issues.append(f"override cannot disable locked Core rule {rule_id}")
        if "classification" in changed and changed["classification"] != current["classification"]:
            local_issues.append(f"override cannot change rule classification for {rule_id}")
        if "severity" in changed and changed["severity"] not in SEVERITY_RANK:
            local_issues.append(f"override has invalid severity for {rule_id}")
        elif "severity" in changed and SEVERITY_RANK[changed["severity"]] < SEVERITY_RANK[current["severity"]]:
            local_issues.append(f"override cannot lower severity for {rule_id}")
        protected_paths = changed.get("protected_paths")
        if protected_paths is not None and (not isinstance(protected_paths, list) or not protected_paths or not all(isinstance(item, str) and item for item in protected_paths)):
            local_issues.append(f"override protected_paths must be a non-empty list of strings for {rule_id}")
        issues.extend(local_issues)
        if not local_issues:
            current.update({key: value for key, value in changed.items() if key != "protected_paths"})
            if "protected_paths" in changed:
                current["protected_paths"] = sorted(set(current.get("protected_paths", [])) | set(changed["protected_paths"]))
    for key, value in override.get("limits", {}).items():
        if key not in result["limits"] or not isinstance(value, int) or value > result["limits"][key]:
            issues.append(f"override limit {key} must tighten the default")
        else:
            result["limits"][key] = value
    return result, issues


def explain_policy(policy: dict[str, Any]) -> dict[str, Any]:
    """Read-only effective-policy view: what is applied after any override merge.

    This is the E9 "effective-policy" administrator diagnostic. It never runs
    against a diff or repository content; it only reports the merged rule
    catalog that `evaluate()` would use.
    """
    rules = {
        rule_id: {
            "classification": config["classification"],
            "enabled": config["enabled"],
            "severity": config["severity"],
            "protected_paths": config.get("protected_paths", []),
            "locked": rule_id in LOCKED_RULES,
        }
        for rule_id, config in policy["rules"].items()
    }
    counts = {"enforced": 0, "host-assisted": 0, "advisory": 0}
    for config in rules.values():
        if config["enabled"]:
            counts[config["classification"]] += 1
    return {
        "schema_version": "1",
        "type": "tailtrail-repository-effective-policy",
        "policy_version": policy["policy_version"],
        "rules": rules,
        "counts": counts,
        "boundary": "Read-only merged rule catalog only. It does not evaluate a diff, run a scan, or change policy state.",
    }


def resolve_diff(root: Path, args: argparse.Namespace) -> tuple[str, str]:
    if args.diff:
        return args.diff.read_text(encoding="utf-8"), "file"
    if args.initial:
        result = git(root, "show", "--format=", "--unified=3", args.head or "HEAD")
        if result.returncode:
            raise ValueError(result.stderr.strip() or "unable to build initial commit diff")
        return result.stdout, "initial"
    if args.base:
        head = args.head or "HEAD"
        exists = git(root, "cat-file", "-e", f"{args.base}^{{commit}}")
        if exists.returncode:
            result = git(root, "show", "--format=", "--unified=3", head)
            if result.returncode:
                raise ValueError("base is unavailable and initial diff fallback failed")
            return result.stdout, "initial"
        result = git(root, "diff", "--unified=3", args.base, head)
        if result.returncode:
            raise ValueError(result.stderr.strip() or "git range diff failed")
        return result.stdout, "range"
    result = git(root, "diff", "--cached", "--unified=3")
    if result.returncode:
        raise ValueError(result.stderr.strip() or "staged diff failed")
    return result.stdout, "staged"


def rule(policy: dict[str, Any], rule_id: str) -> dict[str, Any]:
    return policy["rules"][rule_id]


def make(policy: dict[str, Any], rule_id: str, path: str, line: int, message: str, evidence: str, remediation: str) -> Finding:
    config = rule(policy, rule_id)
    return Finding(rule_id, config["classification"], config["severity"], path or "<repository>", max(1, line), message, evidence[:500], remediation).finalize()


def approval_records(root: Path, policy: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    issues: list[str] = []
    directory = root / policy["approval"]["directory"]
    if not directory.is_dir():
        return records, issues
    today = date.today()
    for path in sorted(directory.glob("*.json")):
        try:
            item = read_json(path)
            expires = date.fromisoformat(item["expires"])
            if set(item) != {"schema_version", "type", "policy_version", "approval_id", "approved", "owner", "reason", "paths", "expires"}:
                raise ValueError("closed approval fields do not match")
            if item["schema_version"] != "1" or item["type"] != "tailtrail-repository-approval" or item["policy_version"] != 1 or item["approved"] is not True:
                raise ValueError("approval identity or decision is invalid")
            if expires < today:
                continue
            if expires > today + timedelta(days=policy["approval"]["maximum_age_days"]):
                raise ValueError("approval exceeds maximum age")
            if not item["owner"] or not item["reason"] or not item["paths"]:
                raise ValueError("approval owner, reason, and paths are required")
            records.append(item)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            issues.append(f"{path.relative_to(root).as_posix()}: {error}")
    return records, issues


def path_matches(path: str, pattern: str) -> bool:
    return path == pattern or (pattern.endswith("/") and path.startswith(pattern))


def core_findings(root: Path, policy: dict[str, Any], diff: str, pr_body: str) -> list[Finding]:
    diff_lines, files = GUARD.parse_diff(diff)
    findings: list[Finding] = []
    records, approval_issues = approval_records(root, policy)
    for issue in approval_issues:
        findings.append(make(policy, "approval-scope", "tailtrail-meta/approvals", 1, "Invalid repository approval record", issue, "Replace it with a current closed v1 approval record."))
    protected = rule(policy, "approval-scope").get("protected_paths", [])
    for path in files:
        if not any(path_matches(path, pattern) for pattern in protected):
            continue
        approved = any(any(path_matches(path, pattern) for pattern in item["paths"]) for item in records)
        if not approved:
            findings.append(make(policy, "approval-scope", path, 1, "Protected path changed without repository approval", path, "Add a current owner/reason approval record scoped to this path."))

    guard_findings = []
    guard_findings += GUARD.check_safeguard_removal(diff_lines)
    for path in files:
        normalized = path.replace("\\", "/")
        if normalized.startswith(".tailtrail/") or normalized == "tailtrail/.tailtrail-install.json":
            guard_findings.append(
                GUARD.Finding(
                    rule="local-tailtrail-state-staged",
                    rule_class="local-state",
                    severity="high",
                    path=path,
                    line=1,
                    evidence=path,
                    recommendation="Remove local TailTrail runtime state from the change; commit only reviewed tailtrail-meta governance metadata.",
                    guardrail="GUARDRAILS.md",
                )
            )
    guard_findings += GUARD.check_validation_claims([("<pull-request-body>", pr_body)] if pr_body else [])
    added_by_path: dict[str, list[str]] = {}
    for line in diff_lines:
        if line.kind == "added":
            added_by_path.setdefault(line.path, []).append(line.text)
    guard_findings += GUARD.check_validation_claims([(path, "\n".join(lines)) for path, lines in added_by_path.items()])
    mapping = {"safeguard-removal": "safeguard-preservation", "local-state": "local-state", "validation-claim": "evidence-truth"}
    for item in guard_findings:
        if item.rule_class == "validation-claim" and re.search(r"(?i)\b(?:not|un)[- ](?:validated|verified|deployed)\b", item.evidence):
            continue
        rule_id = mapping[item.rule_class]
        findings.append(make(policy, rule_id, item.path, item.line, item.recommendation, item.evidence, item.recommendation))

    dependency = DEPENDENCY.check(root, policy["dependency"]["decision_directory"], diff)
    for item in dependency["errors"]:
        findings.append(make(policy, "dependency-decision", policy["dependency"]["decision_directory"], 1, "Invalid dependency decision", item, "Correct the decision record against the closed schema."))
    for item in dependency["missing_decisions"]:
        findings.append(make(policy, "dependency-decision", item["path"], 1, "Dependency change lacks an approved matching decision", item["evidence"], "Add an approved dependency decision with owner, alternatives, validation, and rollback."))

    for line in diff_lines:
        if line.kind != "added":
            continue
        for label, pattern in SECRET_PATTERNS:
            match = pattern.search(line.text)
            if match:
                digest = hashlib.sha256(match.group(0).encode("utf-8")).hexdigest()[:16]
                findings.append(make(policy, "redaction", line.path, line.line, f"Sensitive value detected: {label}", f"[redacted sha256:{digest}]", "Remove and rotate the value; use a secret manager or sanitized fixture."))
        if ("completion" in line.path.lower() or "closure" in line.path.lower()) and re.search(r'(?i)(?:"status"\s*:\s*"complete"|\bcomplete[d]?\b)', line.text):
            evidence_present = any(marker.lower() in diff.lower() for marker in policy["evidence"]["markers"])
            if not evidence_present:
                findings.append(make(policy, "stale-completion", line.path, line.line, "Completion claim has no same-change evidence", line.text.strip(), "Attach current command/result evidence or keep completion incomplete."))

    release_sensitive = any(path in {"release-manifest.json", "pyproject.toml", "package-manifest.json"} or path.startswith(".github/workflows/") for path in files)
    if release_sensitive:
        manifest = root / "release-manifest.json"
        if not manifest.is_file():
            findings.append(make(policy, "release-manifest", "release-manifest.json", 1, "Release-sensitive change has no release manifest", "missing release-manifest.json", "Add and validate the versioned release manifest."))
        else:
            try:
                release_module = load_script("tailtrail_e6_release_manifest", "release_manifest.py")
                value = release_module.load(root)
                existing = [path for path in release_module.git_files(root) if (root / path).is_file()]
                issues = release_module.validate(root, value, existing)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                issues = [str(error)]
            for issue in issues[:20]:
                findings.append(make(policy, "release-manifest", "release-manifest.json", 1, "Release manifest validation failed", issue, "Update the manifest and candidate scope, then rerun enforcement."))
    return findings


def load_baseline(root: Path, policy: dict[str, Any]) -> tuple[set[str], list[str]]:
    path = root / policy["baseline"]["path"]
    if not path.is_file():
        return set(), ["baseline file is missing"]
    try:
        value = read_json(path)
        if set(value) != {"schema_version", "type", "policy_version", "generated_at", "findings"} or value["schema_version"] != "1" or value["type"] != "tailtrail-enforcement-baseline" or value["policy_version"] != 1:
            raise ValueError("baseline identity or fields are incompatible")
        return {item["fingerprint"] for item in value["findings"] if set(item) == {"fingerprint", "rule_id", "path"}}, []
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return set(), [str(error)]


def load_suppressions(root: Path, policy: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    path = root / policy["suppressions"]["path"]
    if not path.is_file():
        return {}, ["suppression file is missing"]
    today = date.today()
    result: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    try:
        value = read_json(path)
        if set(value) != {"schema_version", "type", "policy_version", "suppressions"} or value["schema_version"] != "1" or value["type"] != "tailtrail-enforcement-suppressions" or value["policy_version"] != 1:
            raise ValueError("suppression identity or fields are incompatible")
        for item in value["suppressions"]:
            if set(item) != {"fingerprint", "rule_id", "path", "owner", "reason", "expires"}:
                issues.append("suppression has incompatible fields")
                continue
            expiry = date.fromisoformat(item["expires"])
            if expiry < today or expiry > today + timedelta(days=policy["suppressions"]["maximum_days"]):
                issues.append(f"suppression {item['fingerprint']} is expired or exceeds maximum duration")
                continue
            if not item["owner"] or not item["reason"]:
                issues.append(f"suppression {item['fingerprint']} lacks owner or reason")
                continue
            result[item["fingerprint"]] = item
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        issues.append(str(error))
    return result, issues


def evaluate(root: Path, policy: dict[str, Any], diff: str, diff_mode: str, pr_body: str) -> dict[str, Any]:
    findings = core_findings(root, policy, diff, pr_body)
    baseline, baseline_issues = load_baseline(root, policy)
    suppressions, suppression_issues = load_suppressions(root, policy)
    for issue in [*baseline_issues, *suppression_issues]:
        findings.append(make(policy, "approval-scope", POLICY_FILE, 1, "Enforcement metadata is invalid", issue, "Restore compatible baseline/suppression metadata."))
    for item in findings:
        if item.fingerprint in baseline:
            item.state = "baseline"
        suppression = suppressions.get(item.fingerprint)
        if suppression and suppression["rule_id"] == item.rule_id and suppression["path"] == item.path and item.severity != "high":
            item.state = "suppressed"
        item.blocking = item.classification == "enforced" and (
            item.severity == "high" or (item.severity == "medium" and item.state == "new")
        )
    findings = sorted(findings, key=lambda item: (item.path, item.line, item.rule_id, item.fingerprint))
    if len(findings) > policy["limits"]["maximum_findings"]:
        findings = findings[:policy["limits"]["maximum_findings"]]
        findings.append(make(policy, "approval-scope", POLICY_FILE, 1, "Finding limit exceeded", str(len(findings)), "Reduce the change scope or raise the limit through reviewed policy."))
        findings[-1].blocking = True
    blocking = sum(item.blocking for item in findings)
    return {"schema_version": "1", "type": "tailtrail-repository-enforcement-report", "status": "failed" if blocking else "passed", "policy_version": 1, "diff_mode": diff_mode, "finding_count": len(findings), "blocking_count": blocking, "findings": [item.as_dict() for item in findings], "rule_catalog": {key: value["classification"] for key, value in policy["rules"].items()}, "limitations": ["Deterministic repository enforcement does not execute project code or replace tests, scanners, review, or host observation.", "Host-assisted and advisory rules are reported but never represented as independently enforced."]}


def sarif(report: dict[str, Any]) -> dict[str, Any]:
    rules = {}
    results = []
    level = {"high": "error", "medium": "warning", "low": "note"}
    for item in report["findings"]:
        rules[item["rule_id"]] = {"id": item["rule_id"], "shortDescription": {"text": item["message"]}, "help": {"text": item["remediation"]}}
        results.append({"ruleId": item["rule_id"], "level": level[item["severity"]], "message": {"text": item["message"]}, "locations": [{"physicalLocation": {"artifactLocation": {"uri": item["path"]}, "region": {"startLine": item["line"]}}}], "partialFingerprints": {"tailtrailFingerprint": item["fingerprint"]}, "properties": {"classification": item["classification"], "state": item["state"], "blocking": item["blocking"], "evidence": item["evidence"], "remediation": item["remediation"]}})
    return {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0", "runs": [{"tool": {"driver": {"name": "TailTrail Repository Enforcement", "version": "0.6.0", "informationUri": "https://github.com/vishrutsinghal/tailr", "rules": list(rules.values())}}, "results": results}]}


def migrate(input_path: Path, output_path: Path) -> int:
    if output_path.exists():
        raise ValueError("migration output already exists")
    value = read_json(input_path)
    if value.get("version") != 0 or set(value) != {"version", "enforce"}:
        raise ValueError("only closed v0 {version,enforce} policies can migrate")
    policy = read_json(PACKAGE_ROOT / POLICY_FILE)
    known = set(policy["rules"])
    if not set(value["enforce"]) <= known:
        raise ValueError("v0 policy contains unknown rules")
    for rule_id, config in policy["rules"].items():
        if rule_id not in LOCKED_RULES:
            config["enabled"] = rule_id in value["enforce"]
    output_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--root", type=Path, default=Path.cwd())
    explain = sub.add_parser("explain")
    explain.add_argument("--root", type=Path, default=Path.cwd())
    explain.add_argument("--policy", type=Path)
    explain.add_argument("--override", type=Path)
    check = sub.add_parser("check")
    check.add_argument("--root", type=Path, default=Path.cwd())
    check.add_argument("--policy", type=Path)
    check.add_argument("--override", type=Path)
    check.add_argument("--diff", type=Path)
    check.add_argument("--base")
    check.add_argument("--head")
    check.add_argument("--initial", action="store_true")
    check.add_argument("--pr-body", type=Path)
    check.add_argument("--format", choices=("json", "sarif"), default="json")
    check.add_argument("--output", type=Path)
    migration = sub.add_parser("migrate")
    migration.add_argument("--input", type=Path, required=True)
    migration.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "migrate":
        try:
            return migrate(args.input, args.output)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(json.dumps({"type": "tailtrail-enforcement-migration", "status": "failed", "issues": [str(error)]}))
            return 1
    root = args.root.resolve()
    policy_path = getattr(args, "policy", None) or root / POLICY_FILE
    try:
        policy = read_json(policy_path)
        issues = validate_policy(policy)
        if getattr(args, "override", None):
            policy, override_issues = merge_override(policy, read_json(args.override))
            issues += override_issues + validate_policy(policy)
    except (OSError, json.JSONDecodeError) as error:
        issues = [str(error)]
        policy = None
    if args.action == "validate":
        payload = {"schema_version": "1", "type": "tailtrail-enforcement-policy-validation", "status": "failed" if issues else "passed", "policy_version": policy.get("policy_version") if policy else None, "issues": issues}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if issues else 0
    if args.action == "explain":
        if issues or policy is None:
            payload = {"schema_version": "1", "type": "tailtrail-repository-effective-policy", "policy_version": None, "rules": {}, "counts": {}, "boundary": "Read-only merged rule catalog only.", "issues": issues}
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 1
        print(json.dumps(explain_policy(policy), indent=2, sort_keys=True))
        return 0
    if issues or policy is None:
        payload = {"schema_version": "1", "type": "tailtrail-repository-enforcement-report", "status": "failed", "policy_version": 1, "diff_mode": "file" if args.diff else "staged", "finding_count": 1, "blocking_count": 1, "findings": [Finding("policy-schema", "enforced", "high", POLICY_FILE, 1, "Policy validation failed", "; ".join(issues), "Use a compatible closed v1 policy.").finalize().as_dict()], "rule_catalog": {}, "limitations": ["Invalid policy fails closed."]}
        payload["findings"][0]["blocking"] = True
    else:
        try:
            diff, mode = resolve_diff(root, args)
            if len(diff.encode("utf-8")) > policy["limits"]["maximum_diff_bytes"]:
                raise ValueError("diff exceeds policy maximum_diff_bytes")
            pr_body = args.pr_body.read_text(encoding="utf-8") if args.pr_body else ""
            payload = evaluate(root, policy, diff, mode, pr_body)
        except (OSError, ValueError) as error:
            item = make(policy, "approval-scope", "<input>", 1, "Enforcement input failed", str(error), "Provide a readable bounded diff or valid Git range.")
            item.blocking = True
            payload = {"schema_version": "1", "type": "tailtrail-repository-enforcement-report", "status": "failed", "policy_version": 1, "diff_mode": "file" if args.diff else "staged", "finding_count": 1, "blocking_count": 1, "findings": [item.as_dict()], "rule_catalog": {key: value["classification"] for key, value in policy["rules"].items()}, "limitations": ["Invalid enforcement input fails closed."]}
    rendered = json.dumps(sarif(payload) if args.format == "sarif" else payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
