#!/usr/bin/env python3
"""NS-9 migration, real-run release proof, and fail-closed rollback controls."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PYTHON = sys.executable
RELEASE_FIXTURE = ROOT / "benchmarks" / "evaluation" / "navigator-scope" / "release-v1.json"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

import navigator_scope
import release_manifest


class ScopeReleaseError(ValueError):
    pass


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ScopeReleaseError(f"JSON object required: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def migration_report(root: Path) -> dict[str, Any]:
    """Audit saved reports without modifying, projecting, or upgrading them."""
    runs = root / ".tailtrail" / "runs"
    paths = sorted(runs.glob("*/planning/start-report-v*.json")) if runs.is_dir() else []
    before = {path: _sha256(path) for path in paths}
    records: list[dict[str, Any]] = []
    for path in paths:
        value = _json(path)
        report = value.get("report") if isinstance(value.get("report"), dict) else value
        navigator = report.get("navigator") if isinstance(report, dict) else None
        evidence = navigator.get("scope_evidence") if isinstance(navigator, dict) else None
        relative = path.relative_to(root).as_posix()
        if not isinstance(evidence, dict):
            records.append({
                "artifact": relative,
                "classification": "legacy-v1-immutable",
                "saved_authority": "finish-only",
                "revision_policy": "remain-v1-until-explicit-new-start",
                "scope_interpretation": "not-reinterpreted",
                "sha256": before[path],
            })
            continue
        if evidence.get("schema_version") != navigator_scope.SCHEMA_VERSION or not navigator_scope.verify_decision_fingerprint(evidence):
            if isinstance(evidence, dict) and navigator_scope.verify_decision_fingerprint_legacy(evidence):
                records.append({
                    "artifact": relative,
                    "classification": "superseded-v2",
                    "saved_authority": "superseded-scheme",
                    "revision_policy": "no-background-rewrite",
                    "scope_interpretation": "superseded",
                    "sha256": before[path],
                })
                continue
            records.append({
                "artifact": relative,
                "classification": "invalid-v2",
                "saved_authority": "blocked",
                "revision_policy": "no-background-rewrite",
                "scope_interpretation": "rejected",
                "sha256": before[path],
            })
            continue
        records.append({
            "artifact": relative,
            "classification": "scope-v2",
            "saved_authority": "bound-to-saved-fingerprint",
            "revision_policy": "v2-evidence-required",
            "scope_interpretation": "verified-v2",
            "sha256": before[path],
        })
    after = {path: _sha256(path) for path in paths}
    counts = {name: sum(row["classification"] == name for row in records) for name in ("legacy-v1-immutable", "scope-v2", "superseded-v2", "invalid-v2")}
    status = "passed" if before == after and counts["invalid-v2"] == 0 else "failed"
    return {
        "schema_version": "1",
        "type": "tailtrail-navigator-scope-migration-report",
        "status": status,
        "root": root.as_posix(),
        "records": records,
        "counts": counts,
        "immutability": {"files_before": len(before), "files_after": len(after), "content_unchanged": before == after, "background_rewrite": False},
        "shadow_comparison": {"enabled": False, "raw_goals": False, "raw_source": False, "v1_may_override_v2": False},
        "boundary": "Legacy reports remain byte-identical and keep only their saved authority. Lexical v1 reasons are never converted into v2 ownership evidence.",
    }


def write_policy(root: Path, state: str, reason_code: str, approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ScopeReleaseError("rollback policy mutation requires --approved")
    root = root.resolve()
    if not root.is_dir():
        raise ScopeReleaseError(f"project root is missing: {root}")
    policy = navigator_scope.seal_scope_policy(state, reason_code)
    path = root / navigator_scope.SCOPE_POLICY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return {
        "schema_version": "1",
        "type": "tailtrail-navigator-scope-rollback-control",
        "status": "enabled" if state == navigator_scope.SCOPE_UNAVAILABLE else "disabled",
        "scope_investigation": state,
        "policy": path.relative_to(root).as_posix(),
        "policy_fingerprint": policy["integrity"]["digest"],
        "fallback": "none",
        "boundary": "The switch changes only new Start availability. Existing v1/v2 runs and installed payloads are not rewritten or deleted.",
    }


def _run(command: list[str], cwd: Path, expected: set[int] = {0}) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode not in expected:
        raise ScopeReleaseError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}{result.stderr}")
    return result


def _fixture(root: Path, *, ambiguous: bool = False) -> None:
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='ns9-proof'\nversion='1.0.0'\n", encoding="utf-8")
    (root / ".gitignore").write_text(".tailtrail/\n", encoding="utf-8")
    body = "def validate_quantity(value: int) -> bool:\n    return value > 0\n"
    (root / "src" / "order_validation.py").write_text(body, encoding="utf-8")
    if ambiguous:
        (root / "src" / "legacy_validation.py").write_text(body, encoding="utf-8")
    (root / "tests" / "test_order_validation.py").write_text(
        "import unittest\nfrom src.order_validation import validate_quantity\n\n"
        "class QuantityTest(unittest.TestCase):\n"
        "    def test_quantity(self):\n"
        "        self.assertTrue(validate_quantity(1))\n"
        "        self.assertFalse(validate_quantity(0))\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_requirements.py").write_text("# lexical requirement decoy; not an implementation owner\n", encoding="utf-8")
    _run(["git", "init", "-q"], root)
    _run(["git", "config", "user.email", "tailtrail@example.invalid"], root)
    _run(["git", "config", "user.name", "TailTrail Release Proof"], root)
    _run(["git", "add", "."], root)
    _run(["git", "commit", "-qm", "fixture"], root)


def _mcp_module() -> Any:
    spec = importlib.util.spec_from_file_location("ns9_mcp_release", SCRIPTS / "mcp-server.py")
    if spec is None or spec.loader is None:
        raise ScopeReleaseError("MCP server is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _calibration_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "fsr6_scope_calibration_release", SCRIPTS / "navigator-scope-calibration.py"
    )
    if spec is None or spec.loader is None:
        raise ScopeReleaseError("Navigator scope calibration is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _scope_evidence(started: dict[str, Any]) -> dict[str, Any]:
    try:
        evidence = started["navigator"]["scope_evidence"]
    except (KeyError, TypeError) as error:
        raise ScopeReleaseError("Start did not return canonical scope evidence") from error
    if not navigator_scope.verify_decision_fingerprint(evidence):
        raise ScopeReleaseError("Start returned invalid v2 scope evidence")
    return evidence


def real_run_proof() -> dict[str, Any]:
    fixture = _json(RELEASE_FIXTURE)
    with tempfile.TemporaryDirectory(prefix="tailtrail-ns9-") as temporary:
        base = Path(temporary)
        project = base / "resolved"
        project.mkdir()
        _fixture(project)
        cli = [PYTHON, (SCRIPTS / "tailtrail.py").as_posix()]
        goal = str(fixture["goal"])
        explicit_paths = [str(path) for path in fixture["resolved"]["explicit_paths"]]
        start_args = [value for path in explicit_paths for value in ("--changed", path)]
        start = _run([*cli, "start", goal, "--root", project.as_posix(), *start_args, "--planning-run-id", "ns9-cli", "--format", "json"], project)
        started = json.loads(start.stdout)
        cli_evidence = _scope_evidence(started)
        roles = navigator_scope.role_projection(cli_evidence, include_excluded=True)
        owners = [row["path"] for row in roles["implementation_owners"]]
        proofs = [row["path"] for row in roles["proof_paths"]]
        if owners != fixture["resolved"]["implementation_owners"] or proofs != fixture["resolved"]["proof_paths"]:
            raise ScopeReleaseError(f"unexpected release-fixture scope: owners={owners}, proof={proofs}")
        if set(fixture["resolved"]["never_implementation_owners"]) & set(owners):
            raise ScopeReleaseError("lexical test decoy became an implementation owner")

        mcp = _mcp_module()
        mcp_result = mcp.tailtrail_start({
            "goal": goal,
            "root": project.as_posix(),
            "changed": explicit_paths,
            "run_id": "ns9-mcp",
            "format": "json",
            "approved": True,
        })
        mcp_contract = mcp_result["scope_contract"]
        if mcp_contract["decision_fingerprint"] != cli_evidence["decision_fingerprint"]:
            raise ScopeReleaseError("CLI and MCP scope fingerprints diverged")

        activated = json.loads(_run([*cli, "planning", "activate", "--root", project.as_posix(), "--run-id", "ns9-cli", "--approved", "--format", "json"], project).stdout)
        if activated["planning_lock"]["status"] != "approved":
            raise ScopeReleaseError("Planning Lock activation failed")
        anchor = _json(project / ".tailtrail" / "runs" / "ns9-cli" / "anchors" / "approved-v1.json")
        requirement_uids = [row["requirement_uid"] for row in anchor["requirements"]]
        source = project / "src" / "order_validation.py"
        source.write_text("def validate_quantity(value: int) -> bool:\n    return value > 0\n", encoding="utf-8")
        edit_event = {"kind": "source-edit", "requirement_uids": requirement_uids, "changed_paths": ["src/order_validation.py"]}
        _run([*cli, "execution-evidence", "record", "--root", project.as_posix(), "--run-id", "ns9-cli", "--event", json.dumps(edit_event), "--approved"], project)
        for requirement in anchor["requirements"]:
            contract = requirement.get("validation_contract", {})
            commands = contract.get("commands", [])
            tiers = contract.get("tiers", [])
            if not commands or not tiers:
                raise ScopeReleaseError("approved real-run validation contract has no executable command or tier")
            arguments = [*cli, "execution-evidence", "run", "--root", project.as_posix(), "--run-id", "ns9-cli", "--requirement", requirement["requirement_uid"]]
            arguments.extend(value for tier in tiers for value in ("--tier", str(tier)))
            arguments.extend(["--changed", "src/order_validation.py", "--label", "NS-9 release fixture", "--command", str(commands[0]), "--approved"])
            observed = json.loads(_run(arguments, project).stdout)
            if observed.get("outcome") != "pass":
                raise ScopeReleaseError("approved real-run validation command did not pass: " + json.dumps(observed, sort_keys=True))
        _run([*cli, "harness", "architecture", "--root", project.as_posix(), "--run-id", "ns9-cli", "--changed", "src/order_validation.py"], project)
        completion = json.loads(_run([*cli, "closure", "finalize", "--root", project.as_posix(), "--run-id", "ns9-cli"], project).stdout)
        if completion.get("overall_status") != "complete":
            raise ScopeReleaseError("real-run Completion Report is not complete: " + json.dumps({"overall_status": completion.get("overall_status"), "assessments": completion.get("assessments"), "correction": completion.get("correction")}, sort_keys=True))

        blocked = base / "blocked"
        blocked.mkdir()
        _fixture(blocked)
        write_policy(blocked, navigator_scope.SCOPE_UNAVAILABLE, "release-proof-rollback", True)
        negative = _run([*cli, "start", goal, "--root", blocked.as_posix(), "--changed", "src/order_validation.py", "--format", "json"], blocked, {2})
        negative_report = json.loads(negative.stdout)
        if negative_report.get("status") != navigator_scope.SCOPE_UNAVAILABLE or (blocked / ".tailtrail" / "runs").exists():
            raise ScopeReleaseError("rollback Start did not fail closed before run persistence")
        negative_mcp = mcp.tailtrail_start({"goal": goal, "root": blocked.as_posix(), "changed": ["src/order_validation.py"], "run_id": "ns9-negative-mcp", "format": "json", "approved": True})
        if negative_mcp["result"].get("status") != navigator_scope.SCOPE_UNAVAILABLE or (blocked / ".tailtrail" / "runs").exists():
            raise ScopeReleaseError("MCP rollback Start created a run artifact")

        unresolved = base / "unresolved"
        unresolved.mkdir()
        (unresolved / "tests").mkdir()
        (unresolved / ".gitignore").write_text(".tailtrail/\n", encoding="utf-8")
        (unresolved / "pyproject.toml").write_text("[project]\nname='ns9-unresolved'\nversion='1.0.0'\n", encoding="utf-8")
        (unresolved / "tests" / "test_requirements.py").write_text("# lexical requirement words only\n", encoding="utf-8")
        _run(["git", "init", "-q"], unresolved)
        _run(["git", "config", "user.email", "tailtrail@example.invalid"], unresolved)
        _run(["git", "config", "user.name", "TailTrail Release Proof"], unresolved)
        _run(["git", "add", "."], unresolved)
        _run(["git", "commit", "-qm", "fixture"], unresolved)
        unresolved_result = _run([*cli, "start", "fix multiline requirement splitting", "--root", unresolved.as_posix(), "--planning-run-id", "ns9-unresolved", "--format", "json"], unresolved, {2})
        unresolved_report = json.loads(unresolved_result.stdout)
        if not unresolved_report.get("scope_quality_boundary") or (unresolved / ".tailtrail" / "runs").exists():
            raise ScopeReleaseError("unresolved Start did not fail closed without run artifacts")

        conflicting = base / "conflicting"
        conflicting.mkdir()
        (conflicting / "services" / "a").mkdir(parents=True)
        (conflicting / "services" / "b").mkdir(parents=True)
        (conflicting / "tests").mkdir()
        (conflicting / ".gitignore").write_text(".tailtrail/\n", encoding="utf-8")
        (conflicting / "pyproject.toml").write_text("[project]\nname='ns9-conflicting'\nversion='1.0.0'\n", encoding="utf-8")
        parser_body = "def parse_multiline(value):\n    return value\n"
        (conflicting / "services" / "a" / "parser.py").write_text(parser_body, encoding="utf-8")
        (conflicting / "services" / "b" / "parser.py").write_text(parser_body, encoding="utf-8")
        (conflicting / "tests" / "test_parser.py").write_text("# parser multiline proof\n", encoding="utf-8")
        _run(["git", "init", "-q"], conflicting)
        _run(["git", "config", "user.email", "tailtrail@example.invalid"], conflicting)
        _run(["git", "config", "user.name", "TailTrail Release Proof"], conflicting)
        _run(["git", "add", "."], conflicting)
        _run(["git", "commit", "-qm", "fixture"], conflicting)
        conflicting_result = _run([*cli, "start", "fix parser multiline splitting", "--root", conflicting.as_posix(), "--planning-run-id", "ns9-conflicting", "--format", "json"], conflicting, {2})
        conflicting_report = json.loads(conflicting_result.stdout)
        conflict_state = (conflicting_report.get("scope_quality") or {}).get("evidence_state")
        if conflict_state not in {"ambiguous", "conflicting"} or not conflicting_report.get("scope_quality_boundary") or (conflicting / ".tailtrail" / "runs").exists():
            raise ScopeReleaseError("conflicting Start did not fail closed without run artifacts")

        return {
            "cli": {"state": cli_evidence["state"], "decision_fingerprint": cli_evidence["decision_fingerprint"], "owners": owners, "proof_paths": proofs, "planning_lock": "approved"},
            "mcp": {"state": mcp_contract["state"], "decision_fingerprint": mcp_contract["decision_fingerprint"], "parity": True},
            "closure": {"overall_status": completion["overall_status"], "completion_report_present": bool(completion.get("completion_report"))},
            "negative": {"rollback_cli": "no-run-artifact", "rollback_mcp": "no-run-artifact", "unresolved_cli": "no-run-artifact", "conflicting_cli": "no-run-artifact", "conflict_state": conflict_state, "status": navigator_scope.SCOPE_UNAVAILABLE, "fallback": "none"},
        }


def package_integrity_issues(root: Path) -> list[str]:
    """Verify source release inventory or installed-package checksums."""
    integrity_path = root / "package-integrity.json"
    if not integrity_path.is_file():
        return release_manifest.validate(root, release_manifest.load(root))
    integrity = _json(integrity_path)
    package = _json(root / "package-manifest.json")
    files = integrity.get("files")
    if not isinstance(files, dict):
        return ["package integrity file map is invalid"]
    issues: list[str] = []
    for relative, expected in sorted(files.items()):
        path = root / str(relative)
        if not path.is_file():
            issues.append(f"packaged file is missing: {relative}")
        elif _sha256(path) != expected:
            issues.append(f"packaged file checksum mismatch: {relative}")
    for relative in package.get("runtime_required", []):
        if not (root / str(relative)).is_file():
            issues.append(f"runtime package member is missing: {relative}")
    return issues


def fsr6_artifact_coverage(fixture: dict[str, Any]) -> dict[str, Any]:
    required = [str(path) for path in fixture.get("required_fsr6_artifacts", [])]
    if not required or len(required) != len(set(required)):
        raise ScopeReleaseError("FSR-6 release artifact inventory is missing or duplicated")
    manifest = release_manifest.load(ROOT)
    # Tests are intentionally excluded from wheel/sdist runtime payloads, but
    # they remain mandatory source-release evidence. Combine tracked source
    # inputs with explicitly approved candidate additions for a truthful
    # repository-release inventory rather than treating runtime packaging as
    # test publication.
    release_inventory = set(release_manifest.git_files(ROOT)) | set(
        str(path) for path in manifest.get("candidate_additions", [])
    )
    package = _json(ROOT / "package-manifest.json")
    package_inventory = set(str(path) for path in package.get("required_files", [])) | set(
        str(path) for path in package.get("runtime_required", [])
    )
    package_applicable = [path for path in required if not path.startswith("tests/")]
    # An installed wheel intentionally has no test tree.  Source-only proof is
    # checked against the release inventory; physical package members are
    # checked only for the subset declared applicable to runtime packages.
    physical_required = required if (ROOT / ".git").exists() else package_applicable
    missing_files = [path for path in physical_required if not (ROOT / path).is_file()]
    missing_release_inventory = [path for path in required if path not in release_inventory]
    missing_package_inventory = [path for path in package_applicable if path not in package_inventory]
    return {
        "required_count": len(required),
        "source_release_count": len(required) - len(missing_release_inventory),
        "package_applicable_count": len(package_applicable),
        "package_inventory_count": len(package_applicable) - len(missing_package_inventory),
        "missing_files": missing_files,
        "missing_source_release_inventory": missing_release_inventory,
        "missing_package_inventory": missing_package_inventory,
        "status": "passed" if not (missing_files or missing_release_inventory or missing_package_inventory) else "failed",
    }


def local_runtime_hygiene(fixture: dict[str, Any]) -> dict[str, Any]:
    prefixes = tuple(str(value) for value in fixture.get("forbidden_runtime_artifact_prefixes", []))
    if not prefixes:
        raise ScopeReleaseError("FSR-6 runtime-artifact exclusions are missing")
    if (ROOT / ".git").exists():
        tracked = release_manifest.git_files(ROOT)
    else:
        # A wheel install may generate interpreter caches at runtime.  Those
        # are not published members, so inspect its sealed inventory instead
        # of conflating local bytecode with committed release state.
        package = _json(ROOT / "package-manifest.json")
        tracked = sorted(
            set(str(path) for path in package.get("required_files", []))
            | set(str(path) for path in package.get("runtime_required", []))
        )
    violations = sorted(
        path for path in tracked
        if any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)
    )
    return {
        "forbidden_prefixes": list(prefixes),
        "tracked_violation_count": len(violations),
        "tracked_violations": violations,
        "status": "passed" if not violations else "failed",
        "boundary": "Only tracked release inputs are inspected; untracked user workspace state is neither deleted nor treated as published.",
    }


def adapter_conformance() -> dict[str, Any]:
    result = _run([PYTHON, (SCRIPTS / "host-adapter-conformance.py").as_posix()], ROOT)
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ScopeReleaseError("host adapter conformance did not return JSON") from error
    if report.get("status") != "passed":
        raise ScopeReleaseError("host adapter conformance failed")
    return {
        "status": "passed",
        "hosts": list(report.get("hosts", [])),
        "scope_contract_version": report.get("scope_contract_version"),
        "scope_reasoning_contract_version": report.get("scope_reasoning_contract_version"),
    }


def release_proof(root: Path) -> dict[str, Any]:
    fixture = _json(RELEASE_FIXTURE)
    manifest_errors = package_integrity_issues(ROOT)
    contract = _json(ROOT / "platform-release-contract.json")
    required_hosts = set(fixture["hosts"])
    required_platforms = set(fixture["platforms"])
    platforms = set(contract.get("supported_operating_systems", [])) | set(contract.get("compatibility_fixtures", []))
    platform_ok = required_hosts <= set(contract.get("host_profiles", [])) and required_platforms <= platforms
    real = real_run_proof()
    migration = migration_report(root)
    calibration = _calibration_module().default_fsr6_assurance()
    artifacts = fsr6_artifact_coverage(fixture)
    runtime_hygiene = local_runtime_hygiene(fixture)
    adapters = adapter_conformance()
    checks = {
        "release_manifest": not manifest_errors,
        "platform_and_host_contract": platform_ok,
        "migration_immutability": migration["status"] == "passed",
        "cli_mcp_real_run": real["cli"]["decision_fingerprint"] == real["mcp"]["decision_fingerprint"],
        "planning_approval_closure": real["closure"]["overall_status"] == "complete",
        "negative_no_artifacts": all(real["negative"][key] == "no-run-artifact" for key in ("rollback_cli", "rollback_mcp", "unresolved_cli", "conflicting_cli")),
        "lexical_fallback_absent": real["negative"]["fallback"] == "none",
        "calibration_thresholds": calibration["status"] == "passed",
        "unsafe_lock_zero": calibration["metrics"]["unsafe_lock_count"] == 0,
        "supported_language_profiles": calibration["language_profiles"]["passed"] == calibration["language_profiles"]["supported"],
        "adapter_conformance": adapters["status"] == "passed",
        "fsr6_artifact_coverage": artifacts["status"] == "passed",
        "generated_runtime_hygiene": runtime_hygiene["status"] == "passed",
    }
    return {
        "schema_version": "1",
        "type": "tailtrail-navigator-scope-release-proof",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "manifest_issues": manifest_errors,
        "platforms": sorted(platforms),
        "hosts": sorted(contract.get("host_profiles", [])),
        "migration": {"status": migration["status"], "counts": migration["counts"], "immutability": migration["immutability"], "shadow_comparison": migration["shadow_comparison"]},
        "real_run": real,
        "calibration": calibration,
        "adapter_conformance": adapters,
        "artifact_coverage": artifacts,
        "local_runtime_hygiene": runtime_hygiene,
        "artifact_boundary": "Wheel and sdist inventory/checksum proof remains mandatory through package-release-proof.py and the self-contained-package release gate.",
        "boundary": "This proof uses real CLI and MCP entrypoints in isolated repositories. It does not claim hosted operating-system observations or replace signed release receipts.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("migration", "release-proof", "rollback-status", "rollback-enable", "rollback-disable"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--reason-code", default="operator-release-rollback")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "migration":
            value = migration_report(root)
        elif args.command == "release-proof":
            value = release_proof(root)
        elif args.command == "rollback-status":
            value = {"schema_version": "1", "type": "tailtrail-navigator-scope-rollback-status", **navigator_scope.scope_release_status(root), "boundary": "Status is read-only and does not create, rewrite, approve, or delete a run."}
        elif args.command == "rollback-enable":
            value = write_policy(root, navigator_scope.SCOPE_UNAVAILABLE, args.reason_code, args.approved)
        else:
            value = write_policy(root, navigator_scope.SCOPE_AVAILABLE, args.reason_code, args.approved)
    except (OSError, json.JSONDecodeError, ScopeReleaseError, ValueError) as error:
        print(json.dumps({"schema_version": "1", "type": "tailtrail-navigator-scope-release-error", "status": "failed", "error": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value.get("status") != "failed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
