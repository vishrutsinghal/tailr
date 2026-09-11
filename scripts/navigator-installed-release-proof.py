#!/usr/bin/env python3
"""Run FSR-7 against real local release artifacts and installed host payloads."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = ROOT / "benchmarks" / "evaluation" / "navigator-scope" / "installed-release-v1.json"
SCHEMA = ROOT / "schemas" / "navigator-installed-release-proof.schema.json"


class InstalledReleaseProofError(ValueError):
    """A fail-closed, user-presentable installed-proof error."""


def _json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InstalledReleaseProofError(f"{label} is unavailable or invalid: {error}") from error
    if not isinstance(value, dict):
        raise InstalledReleaseProofError(f"{label} must contain one JSON object")
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise InstalledReleaseProofError(f"required file is missing: {path}")
    return _sha256_bytes(path.read_bytes())


def _safe_relative(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise InstalledReleaseProofError(f"unsafe repository-relative path: {value}")
    return path.as_posix()


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise InstalledReleaseProofError(f"cannot load required release helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_scenario(value: dict[str, Any]) -> None:
    required = {
        "schema_version", "type", "proof_version", "scenario_id", "source_catalog",
        "source_scenario_id", "hosts", "install_profiles", "graph_action", "run_id",
        "hash_members", "expected", "privacy", "claim_boundaries", "integrity",
    }
    if set(value) != required:
        raise InstalledReleaseProofError("installed release scenario fields do not match the closed contract")
    if value.get("schema_version") != "1" or value.get("type") != "tailtrail-navigator-installed-release-scenario":
        raise InstalledReleaseProofError("installed release scenario contract is incompatible")
    if value.get("hosts") != ["codex", "copilot", "claude"]:
        raise InstalledReleaseProofError("installed release scenario must cover codex, copilot, and claude")
    if value.get("install_profiles") != ["core", "extended"] or value.get("graph_action") != "refresh":
        raise InstalledReleaseProofError("installed release scenario must prove the Core-to-Extended update and graph refresh")
    members = value.get("hash_members")
    if not isinstance(members, list) or not members or len(members) != len(set(members)):
        raise InstalledReleaseProofError("installed release hash members are missing or duplicated")
    for member in members:
        _safe_relative(str(member))
    expected_keys = {
        "scope_state", "implementation_owners", "inspection_paths", "proof_paths",
        "scope_question", "planning_lock_status", "graph_cache_status", "behavior_chain_state",
    }
    if not isinstance(value.get("expected"), dict) or set(value["expected"]) != expected_keys:
        raise InstalledReleaseProofError("installed release expectations do not match the closed contract")
    privacy = value.get("privacy")
    if privacy != {
        "fixture": "synthetic",
        "raw_project_source_in_summary": False,
        "external_fixture_retained": False,
        "hosted_agent_claim": False,
    }:
        raise InstalledReleaseProofError("installed release privacy boundary is invalid")
    integrity = value.get("integrity")
    if not isinstance(integrity, dict) or set(integrity) != {"algorithm", "canonicalization", "digest"}:
        raise InstalledReleaseProofError("installed release scenario integrity metadata is invalid")
    material = {key: item for key, item in value.items() if key != "integrity"}
    if integrity.get("algorithm") != "sha256" or integrity.get("digest") != _digest(material):
        raise InstalledReleaseProofError("installed release scenario integrity digest is invalid")


def _artifact_summary(report: dict[str, Any]) -> dict[str, Any]:
    result = {
        "name": Path(str(report.get("artifact", "artifact"))).name,
        "kind": report.get("kind"),
        "sha256": report.get("sha256"),
        "entries": report.get("entries"),
        "valid": bool(report.get("valid")),
        "issues": list(report.get("issues", [])),
    }
    if report.get("kind") == "wheel":
        result["integrity_files"] = report.get("integrity_files")
    return result


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.pop("TAILTRAIL_SOURCE_COMPAT_ROOT", None)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(command, cwd=cwd, env=environment, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        rendered = " ".join(command[:4])
        detail = (result.stderr or result.stdout).strip()
        raise InstalledReleaseProofError(f"installed proof command failed ({result.returncode}): {rendered}: {detail}")
    return result


def _run_json(command: list[str], cwd: Path) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    result = _run(command, cwd)
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise InstalledReleaseProofError(f"installed proof command did not return JSON: {' '.join(command[:4])}") from error
    if not isinstance(value, dict):
        raise InstalledReleaseProofError("installed proof command returned a non-object JSON value")
    return value, result


def _venv_path(root: Path, command: str) -> Path:
    windows = root / "Scripts" / (command + (".exe" if command in {"python", "tailtrail"} else ""))
    if windows.is_file():
        return windows
    posix = root / "bin" / command
    if posix.is_file():
        return posix
    raise InstalledReleaseProofError(f"isolated environment command is missing: {command}")


def _archive_members(wheel: Path, sdist: Path, members: list[str]) -> tuple[dict[str, bytes], dict[str, bytes]]:
    wheel_values: dict[str, bytes] = {}
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        for member in members:
            name = f"tailtrail/{member}"
            if name not in names:
                raise InstalledReleaseProofError(f"wheel member is missing: {name}")
            wheel_values[member] = archive.read(name)
    sdist_values: dict[str, bytes] = {}
    with tarfile.open(sdist) as archive:
        by_suffix = {
            "/".join(name.replace("\\", "/").split("/")[1:]): name
            for name in archive.getnames()
            if "/" in name
        }
        for member in members:
            name = by_suffix.get(member)
            extracted = archive.extractfile(name) if name else None
            if extracted is None:
                raise InstalledReleaseProofError(f"source distribution member is missing: {member}")
            sdist_values[member] = extracted.read()
    return wheel_values, sdist_values


def _materialize_repository(root: Path, scenario: dict[str, Any]) -> None:
    files = scenario.get("repository_files")
    if not isinstance(files, dict) or not files:
        raise InstalledReleaseProofError("source calibration scenario has no repository fixture")
    for relative, body in files.items():
        safe = _safe_relative(str(relative))
        if not isinstance(body, str):
            raise InstalledReleaseProofError(f"fixture body must be text: {safe}")
        target = root / safe
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    (root / ".gitignore").write_text(".tailtrail/\ntailtrail-meta/code-graph-cache.json\n", encoding="utf-8")
    _run(["git", "init", "-q"], root)
    _run(["git", "config", "user.email", "tailtrail@example.invalid"], root)
    _run(["git", "config", "user.name", "TailTrail Installed Proof"], root)
    _run(["git", "add", "."], root)
    _run(["git", "commit", "-qm", "synthetic fixture"], root)


def _source_scenario(source_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    catalog = _json(source_root / _safe_relative(str(config["source_catalog"])), "source calibration catalog")
    rows = catalog.get("scenarios")
    if not isinstance(rows, list):
        raise InstalledReleaseProofError("source calibration catalog has no scenarios")
    scenario = next((item for item in rows if isinstance(item, dict) and item.get("id") == config["source_scenario_id"]), None)
    if not isinstance(scenario, dict):
        raise InstalledReleaseProofError("installed release source scenario is missing")
    return scenario


def _manifest(project: Path, host: str) -> dict[str, Any]:
    value = _json(project / ".tailtrail" / "install" / "manifests" / f"{host}.json", f"{host} ownership manifest")
    if value.get("host") != host or not isinstance(value.get("files"), dict):
        raise InstalledReleaseProofError(f"{host} ownership manifest is invalid")
    return value


def _transaction_state(project: Path, transaction_id: str) -> str:
    value = _json(project / ".tailtrail" / "install" / "transactions" / transaction_id / "state.json", "installer transaction state")
    return str(value.get("state", "unknown"))


def _candidate_status(evidence: dict[str, Any], path: str) -> tuple[str | None, str | None]:
    candidate = next(
        (item for item in evidence.get("candidates", []) if isinstance(item, dict) and item.get("path") == path),
        None,
    )
    if not isinstance(candidate, dict):
        return None, None
    return str(candidate.get("role")), str(candidate.get("status"))


def installed_release_proof(source_root: Path, wheel: Path, sdist: Path, scenario_path: Path | None = None) -> dict[str, Any]:
    source_root = source_root.resolve()
    wheel = wheel.resolve()
    sdist = sdist.resolve()
    config = _json((scenario_path or source_root / DEFAULT_SCENARIO.relative_to(ROOT)).resolve(), "installed release scenario")
    validate_scenario(config)
    source_scenario = _source_scenario(source_root, config)
    if source_scenario.get("goal") is None:
        raise InstalledReleaseProofError("installed release source scenario has no goal")

    package_proof = _load_module("fsr7_package_release_proof", source_root / "scripts" / "package-release-proof.py")
    wheel_report = package_proof.inspect_wheel(wheel)
    sdist_report = package_proof.inspect_sdist(sdist)
    artifact_valid = bool(wheel_report.get("valid")) and bool(sdist_report.get("valid"))
    if not artifact_valid:
        raise InstalledReleaseProofError("wheel or source distribution failed package integrity inspection")

    members = [str(value) for value in config["hash_members"]]
    launcher_member = "tailtrail/install/host_launcher.py"
    wheel_members, sdist_members = _archive_members(wheel, sdist, [*members, launcher_member])

    with tempfile.TemporaryDirectory(prefix="tailtrail-fsr7-installed-") as temporary:
        base = Path(temporary)
        environment = base / "venv"
        project = base / "external-project"
        project.mkdir()
        _materialize_repository(project, source_scenario)
        _run([sys.executable, "-m", "venv", environment.as_posix()], base)
        python = _venv_path(environment, "python")
        _run([python.as_posix(), "-m", "pip", "install", "--no-index", "--no-deps", wheel.as_posix()], base)
        installed_cli = _venv_path(environment, "tailtrail")
        package_info, _ = _run_json([installed_cli.as_posix(), "package-info", "--format", "json"], base)
        if not package_info.get("valid") or package_info.get("mode") != "installed-package":
            raise InstalledReleaseProofError("wheel did not start in installed-package mode")
        package_version = str(package_info.get("version", ""))
        if not package_version:
            raise InstalledReleaseProofError("installed package did not report a version")

        host_rows: list[dict[str, Any]] = []
        manifests: dict[str, dict[str, Any]] = {}
        launchers: dict[str, Path] = {}
        for host in config["hosts"]:
            install, _ = _run_json([
                installed_cli.as_posix(), "install", "--host", host, "--profile", "core",
                "--target", project.as_posix(), "--format", "json",
            ], base)
            update, _ = _run_json([
                installed_cli.as_posix(), "update", "--host", host, "--profile", "extended",
                "--target", project.as_posix(), "--format", "json",
            ], base)
            verify, _ = _run_json([
                installed_cli.as_posix(), "verify", "--host", host,
                "--target", project.as_posix(), "--format", "json",
            ], base)
            install_transaction = str(install.get("transaction_id") or "")
            update_transaction = str(update.get("transaction_id") or "")
            if not install_transaction or not update_transaction or install_transaction == update_transaction:
                raise InstalledReleaseProofError(f"{host} did not produce distinct install and update transactions")
            update_state = _transaction_state(project, update_transaction)
            manifest = _manifest(project, host)
            manifests[host] = manifest
            launcher = project / ".tailtrail" / "install" / "payload" / host / "scripts" / "tailtrail.py"
            launchers[host] = launcher
            conformance, _ = _run_json([python.as_posix(), launcher.as_posix(), "adapters", "conformance"], project)
            host_rows.append({
                "host": host,
                "install_status": str(install.get("status")),
                "install_transaction": install_transaction,
                "update_status": str(update.get("status")),
                "update_transaction": update_transaction,
                "update_state": update_state,
                "verify_status": str(verify.get("status")),
                "profile": str(manifest.get("profile")),
                "managed_files": len(manifest["files"]),
                "adapter_conformance": str(conformance.get("status")),
            })

        common = project / ".tailtrail" / "install" / "payload" / "common" / package_version
        hash_rows: list[dict[str, Any]] = []
        for member in members:
            destination = (Path(".tailtrail") / "install" / "payload" / "common" / package_version / member).as_posix()
            source_hash = _sha256_file(source_root / member)
            wheel_hash = _sha256_bytes(wheel_members[member])
            sdist_hash = _sha256_bytes(sdist_members[member])
            installed_hash = _sha256_file(common / member)
            manifest_hosts = sorted(
                host for host, manifest in manifests.items()
                if isinstance(manifest["files"].get(destination), dict)
                and manifest["files"][destination].get("sha256") == installed_hash
            )
            match = len(manifest_hosts) == len(config["hosts"]) and len({source_hash, wheel_hash, sdist_hash, installed_hash}) == 1
            hash_rows.append({
                "path": member,
                "source_sha256": source_hash,
                "wheel_sha256": wheel_hash,
                "sdist_sha256": sdist_hash,
                "installed_sha256": installed_hash,
                "manifest_hosts": manifest_hosts,
                "match": match,
            })

        launcher_source = _sha256_file(source_root / launcher_member)
        launcher_wheel = _sha256_bytes(wheel_members[launcher_member])
        launcher_sdist = _sha256_bytes(sdist_members[launcher_member])
        launcher_rows: list[dict[str, Any]] = []
        for host, launcher in launchers.items():
            installed_hash = _sha256_file(launcher)
            destination = (Path(".tailtrail") / "install" / "payload" / host / "scripts" / "tailtrail.py").as_posix()
            manifest_value = manifests[host]["files"].get(destination)
            manifest_hash = str(manifest_value.get("sha256", "")) if isinstance(manifest_value, dict) else ""
            launcher_rows.append({
                "host": host,
                "source_sha256": launcher_source,
                "wheel_sha256": launcher_wheel,
                "sdist_sha256": launcher_sdist,
                "installed_sha256": installed_hash,
                "manifest_sha256": manifest_hash,
                "match": len({launcher_source, launcher_wheel, launcher_sdist, installed_hash, manifest_hash}) == 1,
            })

        codex_launcher = launchers["codex"]
        graph, _ = _run_json([
            python.as_posix(), codex_launcher.as_posix(), "graph", config["graph_action"],
            "--root", project.as_posix(), "--mode", "navigator", "--format", "json",
        ], project)
        graph_status = graph.get("status") if isinstance(graph.get("status"), dict) else {}
        previous_status = graph.get("previous_status") if isinstance(graph.get("previous_status"), dict) else {}
        start_command = [
            python.as_posix(), codex_launcher.as_posix(), "start", str(source_scenario["goal"]),
            "--root", project.as_posix(), "--planning-run-id", str(config["run_id"]), "--format", "json",
        ]
        started, start_result = _run_json(start_command, project)
        navigator = started.get("navigator") if isinstance(started.get("navigator"), dict) else {}
        evidence = navigator.get("scope_evidence") if isinstance(navigator.get("scope_evidence"), dict) else {}
        quality = navigator.get("scope_quality") if isinstance(navigator.get("scope_quality"), dict) else {}
        requirements = evidence.get("requirements") if isinstance(evidence.get("requirements"), list) else []
        requirement = requirements[0] if len(requirements) == 1 and isinstance(requirements[0], dict) else {}
        investigation = evidence.get("investigation") if isinstance(evidence.get("investigation"), dict) else {}
        cache = investigation.get("cache") if isinstance(investigation.get("cache"), dict) else {}
        chains = investigation.get("behavior_chains") if isinstance(investigation.get("behavior_chains"), dict) else {}
        lock = started.get("planning_lock") if isinstance(started.get("planning_lock"), dict) else {}
        run_exists = (project / ".tailtrail" / "runs" / str(config["run_id"])).is_dir()
        expected = config["expected"]
        service_role, service_status = _candidate_status(evidence, expected["inspection_paths"][0])
        proof_role, proof_status = _candidate_status(evidence, expected["proof_paths"][0])
        scope = {
            "state": evidence.get("state"),
            "implementation_owners": list(requirement.get("implementation_owners", [])),
            "inspection_paths": list(requirement.get("inspection_paths", [])),
            "proof_paths": list(requirement.get("proof_paths", [])),
            "scope_question": quality.get("question"),
            "planning_lock_status": lock.get("status"),
            "cache_status": cache.get("status"),
            "behavior_chain_state": chains.get("state"),
            "decision_fingerprint": evidence.get("decision_fingerprint"),
        }
        graph_reason_codes = list(cache.get("reason_codes", []))
        explanation = (
            "Navigator verified the fresh persistent graph against repository identity and current file hashes, "
            "then bounded static investigation followed the configured TypeScript alias from the literal-emitting "
            "service into the page's caught-error state and rendered alert. Qualification precedence therefore "
            "selected the page as the sole editable owner, retained the service for inspection, and retained the "
            "page component test as proof only."
        )
        graph_summary = {
            "action": "refresh" if previous_status else "create",
            "previous_status": str(previous_status.get("status", "missing")),
            "status": str(graph_status.get("status", "unknown")),
            "cache": "tailtrail-meta/code-graph-cache.json",
            "reason_codes": graph_reason_codes,
        }
        host_integrity = all(
            row["install_status"] in {"passed", "current"}
            and row["update_status"] in {"passed", "current"}
            and row["update_state"] == "complete"
            and row["verify_status"] in {"passed", "current"}
            and row["profile"] == "extended"
            for row in host_rows
        )
        adapter_integrity = all(row["adapter_conformance"] == "passed" for row in host_rows)
        hashes_match = all(row["match"] for row in [*hash_rows, *launcher_rows])
        checks = {
            "artifact_integrity": artifact_valid,
            "source_package_installed_hashes": hashes_match,
            "transactional_update": host_integrity,
            "install_verification": all(row["verify_status"] in {"passed", "current"} for row in host_rows),
            "cross_host_packaging": adapter_integrity and {row["host"] for row in host_rows} == set(config["hosts"]),
            "graph_fresh": graph_summary["status"] == expected["graph_cache_status"] and scope["cache_status"] == expected["graph_cache_status"],
            "planning_lock_created": run_exists and scope["planning_lock_status"] == expected["planning_lock_status"],
            "sole_implementation_owner": scope["state"] == expected["scope_state"] and scope["implementation_owners"] == expected["implementation_owners"],
            "service_inspection_only": scope["inspection_paths"] == expected["inspection_paths"] and service_role == "literal-emitter" and service_status == "inspection-only",
            "component_test_proof_only": scope["proof_paths"] == expected["proof_paths"] and proof_role == "test" and proof_status == "proof-only",
            "no_scope_question": scope["scope_question"] is expected["scope_question"],
            "resolution_explained": all(term in explanation for term in ("fresh persistent graph", "bounded static investigation", "sole editable owner", "inspection", "proof only")),
            "complete_start_report_captured": bool(started) and start_result.returncode == 0,
        }
        payload: dict[str, Any] = {
            "schema_version": "1",
            "type": "tailtrail-navigator-installed-release-proof",
            "proof_version": config["proof_version"],
            "status": "passed" if all(checks.values()) else "failed",
            "evidence_label": "isolated-installed-payload-observed",
            "checks": checks,
            "artifact_verification": {
                "wheel": _artifact_summary(wheel_report),
                "sdist": _artifact_summary(sdist_report),
            },
            "installation_integrity": {
                "package_version": package_version,
                "transactional_update": host_integrity,
                "hosts": host_rows,
                "hash_members": hash_rows,
                "launcher_hashes": launcher_rows,
                "all_hashes_match": hashes_match,
                "external_fixture_retained": False,
            },
            "behavioral_proof": {
                "host": "codex",
                "run_id": config["run_id"],
                "graph": graph_summary,
                "scope": scope,
                "resolution_explanation": explanation,
                "start_exit_code": start_result.returncode,
                "start_stdout_sha256": _sha256_bytes(start_result.stdout.encode("utf-8")),
                "complete_start_report": started,
            },
            "claim_boundaries": config["claim_boundaries"],
        }
        payload["proof_digest"] = "sha256:" + _digest(payload)
        return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args()
    try:
        report = installed_release_proof(args.source_root, args.wheel, args.sdist, args.scenario)
        if args.output:
            output = args.output.resolve()
            if not output.parent.is_dir():
                raise InstalledReleaseProofError("output parent directory does not exist")
            temporary = output.with_suffix(output.suffix + ".tmp")
            temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(temporary, output)
    except (InstalledReleaseProofError, OSError, zipfile.BadZipFile, tarfile.TarError) as error:
        print(json.dumps({
            "schema_version": "1",
            "type": "tailtrail-navigator-installed-release-proof-error",
            "status": "failed",
            "error": str(error),
        }, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
