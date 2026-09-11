#!/usr/bin/env python3
"""Deterministic negative assurance and calibration for Navigator scope v2.

Only sealed committed fixture receipts contribute metrics. The command never
stores source bodies, prompts, identities, or live productivity claims.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "benchmarks" / "evaluation" / "navigator-scope" / "v1.json"
DEFAULT_KNOWN_GAP_BASELINE = ROOT / "tailtrail-meta" / "navigator-scope-baseline-v1.json"
DEFAULT_FSR6_CATALOG = ROOT / "benchmarks" / "evaluation" / "navigator-scope" / "fsr6-v1.json"
PRIVACY = {"sanitized": True, "raw_prompt": False, "raw_source": False, "raw_log": False, "identity_fields": False}
SURFACES = {"cli", "mcp", "codex", "copilot", "claude"}
RAW_MARKERS = {"prompt_raw", "raw_prompt", "source_code", "raw_source", "raw_log", "stack_trace", "secret", "password", "token", "credential", "user_identity"}
NEGATIVE_GATES = ["conflict", "freshness", "invalidator", "privacy", "explicit-use-receipt", "closure-attribution"]
_FSR6_ASSURANCE_CACHE: dict[str, Any] | None = None


class ScopeCalibrationError(ValueError):
    pass


def load_module(name: str, relative: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def unsigned_digest(value: dict[str, Any]) -> str:
    unsigned = copy.deepcopy(value)
    unsigned.pop("integrity", None)
    return digest(unsigned)


def exact_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ScopeCalibrationError(f"{label} contract is not closed")


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ScopeCalibrationError(f"{label} is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ScopeCalibrationError(f"{label} is invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ScopeCalibrationError(f"{label} must be an object")
    return value


def contains_raw_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if lowered in RAW_MARKERS or any(marker in lowered for marker in ("raw_prompt", "raw_source", "raw_log", "source_code", "identity")):
                if lowered not in PRIVACY:
                    return str(key)
            found = contains_raw_key(nested)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = contains_raw_key(item)
            if found:
                return found
    return None


def validate_integrity(value: dict[str, Any], label: str) -> None:
    integrity = value.get("integrity")
    exact_keys(integrity, {"algorithm", "canonicalization", "digest"}, f"{label} integrity")
    if integrity["algorithm"] != "sha256" or integrity["canonicalization"] != "sorted compact JSON excluding integrity":
        raise ScopeCalibrationError(f"{label} integrity contract is invalid")
    if integrity["digest"] != unsigned_digest(value):
        raise ScopeCalibrationError(f"{label} digest mismatch")


def supported_languages() -> list[str]:
    relationships = load_module("ns8_code_relationships", "scripts/code_relationships.py")
    return sorted(set(relationships.LANGUAGE_BY_SUFFIX.values()))


def validate_decision(value: dict[str, Any], label: str) -> None:
    exact_keys(value, {"state", "implementation_owners", "strongest_evidence", "safe_refusal"}, label)
    if value["state"] not in {"resolved", "unresolved", "ambiguous", "blocked-by-limits"}:
        raise ScopeCalibrationError(f"{label} state is invalid")
    if value["strongest_evidence"] not in {"none", "weak", "medium", "strong"}:
        raise ScopeCalibrationError(f"{label} evidence strength is invalid")
    if not isinstance(value["implementation_owners"], list) or len(value["implementation_owners"]) != len(set(value["implementation_owners"])):
        raise ScopeCalibrationError(f"{label} owners are invalid")
    if not all(isinstance(item, str) and item and ".." not in Path(item).parts and not Path(item).is_absolute() for item in value["implementation_owners"]):
        raise ScopeCalibrationError(f"{label} contains an unsafe owner path")
    if not isinstance(value["safe_refusal"], bool):
        raise ScopeCalibrationError(f"{label} safe_refusal must be boolean")
    if value["state"] == "resolved" and value["safe_refusal"]:
        raise ScopeCalibrationError(f"{label} resolved state cannot be a safe refusal")
    if value["state"] != "resolved" and value["implementation_owners"]:
        raise ScopeCalibrationError(f"{label} unresolved state cannot claim implementation owners")


def validate_receipt(receipt: dict[str, Any]) -> None:
    fields = {
        "receipt_id", "source_kind", "factual", "task_class", "language", "request_kind",
        "negative_boundaries", "expected", "observed", "manual_scope_revision",
        "investigation", "surface_fingerprints", "receipt_fingerprint",
    }
    exact_keys(receipt, fields, "decision receipt")
    if not re.fullmatch(r"ns8-[a-z0-9-]+", str(receipt["receipt_id"])):
        raise ScopeCalibrationError("decision receipt ID is invalid")
    if receipt["source_kind"] != "committed-fixture" or receipt["factual"] is not True:
        raise ScopeCalibrationError("metrics require a factual committed-fixture receipt")
    if receipt["request_kind"] not in {"code-change", "test-only", "documentation-only", "debug"}:
        raise ScopeCalibrationError("decision receipt request kind is invalid")
    validate_decision(receipt["expected"], "expected decision")
    validate_decision(receipt["observed"], "observed decision")
    investigation = receipt["investigation"]
    exact_keys(investigation, {"files_read", "bytes_read", "relationship_hops", "duration_ms", "fresh_graph_reused", "stale_graph_rejected"}, "investigation metrics")
    if any(not isinstance(investigation[key], int) or isinstance(investigation[key], bool) or investigation[key] < 0 for key in ("files_read", "bytes_read", "relationship_hops", "duration_ms")):
        raise ScopeCalibrationError("investigation counts must be non-negative integers")
    if not isinstance(investigation["fresh_graph_reused"], bool) or not isinstance(investigation["stale_graph_rejected"], bool):
        raise ScopeCalibrationError("graph observations must be boolean")
    if set(receipt["surface_fingerprints"]) != SURFACES or not all(re.fullmatch(r"sha256:[0-9a-f]{64}", str(value)) for value in receipt["surface_fingerprints"].values()):
        raise ScopeCalibrationError("surface decision fingerprints are invalid")
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_fingerprint"}
    if receipt["receipt_fingerprint"] != "sha256:" + digest(unsigned):
        raise ScopeCalibrationError(f"decision receipt fingerprint mismatch: {receipt['receipt_id']}")


def validate_catalog(catalog: dict[str, Any]) -> None:
    fields = {"schema_version", "type", "catalog_version", "evidence_label", "supported_languages", "negative_boundaries", "thresholds", "receipts", "negative_learning", "privacy", "claim_boundaries", "integrity"}
    exact_keys(catalog, fields, "calibration catalog")
    if catalog["schema_version"] != "1" or catalog["type"] != "tailtrail-navigator-scope-calibration-catalog" or catalog["evidence_label"] != "committed-fixture-observed":
        raise ScopeCalibrationError("calibration catalog identity is invalid")
    if catalog["privacy"] != PRIVACY or contains_raw_key(catalog):
        raise ScopeCalibrationError("calibration catalog violates the sanitized privacy boundary")
    if catalog["supported_languages"] != supported_languages():
        raise ScopeCalibrationError("calibration catalog must cover exactly the supported relationship languages")
    if not isinstance(catalog["negative_boundaries"], list) or len(catalog["negative_boundaries"]) < 1 or len(catalog["negative_boundaries"]) != len(set(catalog["negative_boundaries"])):
        raise ScopeCalibrationError("negative boundary catalog is invalid")
    thresholds = catalog["thresholds"]
    exact_keys(thresholds, {"weak_only_lock_count_max", "test_only_false_scope_count_max", "fingerprint_mismatch_count_max", "owner_precision_min", "owner_recall_min"}, "thresholds")
    if thresholds["weak_only_lock_count_max"] != 0 or thresholds["test_only_false_scope_count_max"] != 0 or thresholds["fingerprint_mismatch_count_max"] != 0:
        raise ScopeCalibrationError("negative assurance count thresholds must be zero")
    receipts = catalog["receipts"]
    if not isinstance(receipts, list) or len(receipts) < len(catalog["supported_languages"]):
        raise ScopeCalibrationError("calibration receipt corpus is incomplete")
    ids: set[str] = set()
    for receipt in receipts:
        validate_receipt(receipt)
        if receipt["receipt_id"] in ids:
            raise ScopeCalibrationError("decision receipt IDs must be unique")
        ids.add(receipt["receipt_id"])
    learning = catalog["negative_learning"]
    exact_keys(learning, {"learning_id", "learning_class", "source_receipt_ids", "summary", "advice", "task_types", "tags", "path_patterns", "confidence_score", "invalidators", "stale_when", "capture_default", "use_default", "closure_attribution"}, "negative learning")
    if (
        learning["learning_class"] != "avoid-history" or not set(learning["source_receipt_ids"]) <= ids
        or learning["capture_default"] != "do-not-capture" or learning["use_default"] != "do-not-use"
        or learning["closure_attribution"] != "required-after-explicit-use" or not 0 <= learning["confidence_score"] < 60
    ):
        raise ScopeCalibrationError("negative learning candidate governance is invalid")
    if not isinstance(catalog["claim_boundaries"], list) or len(catalog["claim_boundaries"]) < 3:
        raise ScopeCalibrationError("claim boundaries are incomplete")
    validate_integrity(catalog, "calibration catalog")


def known_gap_baseline_summary(path: Path = DEFAULT_KNOWN_GAP_BASELINE) -> dict[str, Any]:
    """Return the sealed FSR-0 characterization without treating it as release proof."""
    baseline = read_json(path, "Navigator known-gap baseline")
    if baseline.get("type") != "tailtrail-navigator-scope-baseline":
        raise ScopeCalibrationError("Navigator known-gap baseline type is invalid")
    validate_integrity(baseline, "Navigator known-gap baseline")
    if "FSR-0" not in baseline.get("program_extensions", []):
        raise ScopeCalibrationError("Navigator known-gap baseline does not include FSR-0")
    fixtures = {
        str(row.get("id")): row
        for row in baseline.get("fixtures", [])
        if isinstance(row, dict) and row.get("id")
    }
    calibration = baseline.get("calibration")
    if not isinstance(calibration, dict):
        raise ScopeCalibrationError("Navigator known-gap calibration is missing")
    known_ids = [str(value) for value in calibration.get("known_false_stop_ids", [])]
    control_ids = [str(value) for value in calibration.get("safe_stop_control_ids", [])]
    if not known_ids or not control_ids or not set([*known_ids, *control_ids]) <= set(fixtures):
        raise ScopeCalibrationError("Navigator known-gap calibration references unknown fixtures")
    metrics = calibration.get("metrics")
    if not isinstance(metrics, dict):
        raise ScopeCalibrationError("Navigator known-gap calibration metrics are missing")
    expected_metrics = {
        "known_false_stop_count": len(known_ids),
        "safe_stop_control_count": len(control_ids),
        "observed_irrelevant_option_count": sum(
            max(
                0,
                len(fixtures[fixture_id]["current_result"].get("scope_question_options", []))
                - len(fixtures[fixture_id]["expected_result"].get("implementation_owners", [])),
            )
            for fixture_id in known_ids
        ),
        "unsafe_lock_count": sum(
            bool(fixtures[fixture_id]["current_result"].get("planning_lock_created"))
            for fixture_id in [*known_ids, *control_ids]
        ),
    }
    if metrics != expected_metrics:
        raise ScopeCalibrationError("Navigator known-gap calibration metrics do not match fixtures")
    return {
        "baseline_version": baseline["baseline_version"],
        "baseline_digest": baseline["integrity"]["digest"],
        "phase": "FSR-0",
        "status": "known-gap",
        "known_false_stop_ids": known_ids,
        "safe_stop_control_ids": control_ids,
        **metrics,
        "release_ready": False,
        "claim_boundary": "FSR-0 freezes observed failure and safe-stop controls; it is not evidence that the false stop is fixed.",
    }


def aggregate(values: list[int]) -> dict[str, float | int]:
    return {
        "total": sum(values),
        "minimum": min(values) if values else 0,
        "maximum": max(values) if values else 0,
        "mean": round(mean(values), 4) if values else 0,
    }


def grouped_rate(receipts: list[dict[str, Any]], key: str) -> dict[str, float]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for receipt in receipts:
        groups.setdefault(str(receipt[key]), []).append(receipt)
    return {
        name: round(sum(row["observed"]["state"] != "resolved" for row in rows) / len(rows), 4)
        for name, rows in sorted(groups.items())
    }


def test_path(path: str) -> bool:
    lowered = Path(path).as_posix().lower()
    return lowered.startswith("tests/") or "/tests/" in f"/{lowered}" or Path(lowered).name.startswith("test_") or Path(lowered).name.endswith("test.java")


def _safe_relative(value: Any, label: str) -> str:
    path = Path(str(value))
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ScopeCalibrationError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def validate_fsr6_catalog(value: dict[str, Any]) -> None:
    exact_keys(value, {
        "schema_version", "type", "calibration_version", "evidence_label",
        "thresholds", "scenarios", "language_profiles", "privacy",
        "claim_boundaries", "integrity",
    }, "FSR-6 calibration")
    if value["schema_version"] != "1" or value["type"] != "tailtrail-navigator-fsr6-calibration":
        raise ScopeCalibrationError("FSR-6 calibration identity is invalid")
    if value["evidence_label"] != "executable-committed-fixture":
        raise ScopeCalibrationError("FSR-6 metrics require executable committed fixtures")
    exact_keys(value["thresholds"], {
        "false_stop_rate_max", "irrelevant_option_rate_max", "unsafe_lock_count_max",
        "reason_code_accuracy_min", "owner_precision_min", "owner_recall_min",
        "language_profile_pass_rate_min",
    }, "FSR-6 thresholds")
    thresholds = value["thresholds"]
    for key, threshold in thresholds.items():
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not 0 <= threshold <= 1:
            raise ScopeCalibrationError(f"FSR-6 threshold is invalid: {key}")
    if thresholds["unsafe_lock_count_max"] != 0:
        raise ScopeCalibrationError("FSR-6 unsafe lock tolerance must remain zero")
    scenarios = value["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) < 3:
        raise ScopeCalibrationError("FSR-6 needs resolved and safe-stop executable scenarios")
    ids: set[str] = set()
    states: set[str] = set()
    for row in scenarios:
        exact_keys(row, {
            "id", "source_fixture_id", "goal", "repository_files", "expected_state",
            "expected_owners", "expected_proof_paths", "expected_question_options",
            "expected_primary_reason", "expect_planning_lock",
        }, "FSR-6 scenario")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(row["id"])) or row["id"] in ids:
            raise ScopeCalibrationError("FSR-6 scenario IDs must be unique slugs")
        ids.add(row["id"])
        states.add(str(row["expected_state"]))
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(row["source_fixture_id"])):
            raise ScopeCalibrationError("FSR-6 source fixture ID is invalid")
        if not isinstance(row["goal"], str) or not row["goal"].strip():
            raise ScopeCalibrationError("FSR-6 scenario goal is missing")
        if not isinstance(row["repository_files"], dict) or not row["repository_files"]:
            raise ScopeCalibrationError("FSR-6 scenario repository fixture is missing")
        for path, body in row["repository_files"].items():
            _safe_relative(path, "FSR-6 repository fixture path")
            if not isinstance(body, str):
                raise ScopeCalibrationError("FSR-6 repository fixture bodies must be text")
        for field in ("expected_owners", "expected_proof_paths", "expected_question_options"):
            if not isinstance(row[field], list) or len(row[field]) != len(set(row[field])):
                raise ScopeCalibrationError(f"FSR-6 scenario {field} is invalid")
            for path in row[field]:
                _safe_relative(path, f"FSR-6 scenario {field}")
        if row["expected_state"] not in {"resolved", "ambiguous", "unresolved", "blocked-by-limits"}:
            raise ScopeCalibrationError("FSR-6 expected scope state is invalid")
        if not isinstance(row["expect_planning_lock"], bool):
            raise ScopeCalibrationError("FSR-6 lock expectation must be boolean")
        if row["expect_planning_lock"] != (row["expected_state"] == "resolved"):
            raise ScopeCalibrationError("FSR-6 only resolved scenarios may expect a Planning Lock")
    if "resolved" not in states or not ({"ambiguous", "unresolved", "blocked-by-limits"} & states):
        raise ScopeCalibrationError("FSR-6 must measure both safe resolution and correct stopping")
    _safe_relative(value["language_profiles"], "FSR-6 language profile fixture")
    exact_keys(value["privacy"], {"sanitized_report", "synthetic_fixtures", "raw_source_in_report", "identity_fields"}, "FSR-6 privacy")
    if value["privacy"] != {"sanitized_report": True, "synthetic_fixtures": True, "raw_source_in_report": False, "identity_fields": False}:
        raise ScopeCalibrationError("FSR-6 privacy boundary is invalid")
    if not isinstance(value["claim_boundaries"], list) or len(value["claim_boundaries"]) < 3:
        raise ScopeCalibrationError("FSR-6 claim boundaries are incomplete")
    validate_integrity(value, "FSR-6 calibration")


def validate_language_profiles(value: dict[str, Any]) -> None:
    exact_keys(value, {
        "schema_version", "type", "fixture_version", "evidence_label",
        "noise_files_per_profile", "profiles", "privacy", "integrity",
    }, "language profile fixtures")
    if value["schema_version"] != "1" or value["type"] != "tailtrail-navigator-language-profile-fixtures":
        raise ScopeCalibrationError("language profile fixture identity is invalid")
    if value["evidence_label"] != "executable-synthetic-fixture":
        raise ScopeCalibrationError("language profile fixtures must be executable synthetic evidence")
    if not isinstance(value["noise_files_per_profile"], int) or value["noise_files_per_profile"] < 10:
        raise ScopeCalibrationError("language profiles must retain noisy-repository coverage")
    profiles = value["profiles"]
    if not isinstance(profiles, list) or len(profiles) != len(supported_languages()):
        raise ScopeCalibrationError("language profile fixture count is incomplete")
    languages: set[str] = set()
    ids: set[str] = set()
    for row in profiles:
        exact_keys(row, {"id", "language", "path", "body", "expected_definitions", "expected_imports"}, "language profile")
        if row["id"] in ids or row["language"] in languages:
            raise ScopeCalibrationError("language profile IDs and languages must be unique")
        ids.add(str(row["id"]))
        languages.add(str(row["language"]))
        _safe_relative(row["path"], "language profile source path")
        if not isinstance(row["body"], str) or not row["body"]:
            raise ScopeCalibrationError("language profile body is missing")
        for field in ("expected_definitions", "expected_imports"):
            if not isinstance(row[field], list) or not row[field]:
                raise ScopeCalibrationError(f"language profile {field} is incomplete")
    if sorted(languages) != supported_languages():
        raise ScopeCalibrationError("language profiles do not match supported relationship languages")
    exact_keys(value["privacy"], {"classification", "derived_from_proprietary_source", "contains_raw_prompt", "contains_identity_fields"}, "language profile privacy")
    if value["privacy"] != {"classification": "synthetic", "derived_from_proprietary_source": False, "contains_raw_prompt": False, "contains_identity_fields": False}:
        raise ScopeCalibrationError("language profile privacy boundary is invalid")
    validate_integrity(value, "language profile fixtures")


def execute_language_profiles(value: dict[str, Any]) -> dict[str, Any]:
    validate_language_profiles(value)
    relationships = load_module("fsr6_code_relationships", "scripts/code_relationships.py")
    results: list[dict[str, Any]] = []
    for row in value["profiles"]:
        with tempfile.TemporaryDirectory(prefix="tailtrail-fsr6-language-") as temporary:
            repository = Path(temporary)
            source = repository / row["path"]
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(row["body"], encoding="utf-8")
            for index in range(value["noise_files_per_profile"]):
                decoy = repository / "noise" / row["language"] / f"unrelated_{index:02d}{source.suffix}"
                decoy.parent.mkdir(parents=True, exist_ok=True)
                decoy.write_text("// synthetic unrelated calibration noise\n" if source.suffix != ".py" else "# synthetic unrelated calibration noise\n", encoding="utf-8")
            facts = relationships.extract(source, repository, row["body"])
        definitions = sorted({str(item["value"]) for item in facts["definitions"]})
        imports = sorted({str(item["value"]) for item in facts["imports"]})
        passed = (
            facts["language"] == row["language"]
            and set(row["expected_definitions"]) <= set(definitions)
            and set(row["expected_imports"]) <= set(imports)
        )
        results.append({
            "profile_id": row["id"], "language": row["language"], "status": "passed" if passed else "failed",
            "noise_files": value["noise_files_per_profile"], "definition_contract": set(row["expected_definitions"]) <= set(definitions),
            "import_contract": set(row["expected_imports"]) <= set(imports),
        })
    passed_count = sum(row["status"] == "passed" for row in results)
    return {
        "fixture_version": value["fixture_version"], "fixture_digest": value["integrity"]["digest"],
        "supported": len(results), "passed": passed_count,
        "pass_rate": round(passed_count / len(results), 4) if results else 0.0,
        "profiles": results,
    }


def _materialize_fixture(root: Path, fixture: dict[str, Any]) -> None:
    files = fixture.get("repository_files")
    if not isinstance(files, dict) or not files:
        raise ScopeCalibrationError("executable scope fixture has no repository files")
    for relative, body in files.items():
        target = root / _safe_relative(relative, "scope fixture path")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(body), encoding="utf-8")


def execute_fsr6_assurance(config: dict[str, Any]) -> dict[str, Any]:
    validate_fsr6_catalog(config)
    navigator = load_module("fsr6_navigator", "scripts/navigator.py")
    scenario_results: list[dict[str, Any]] = []
    expected_owners: list[str] = []
    observed_owners: list[str] = []
    for index, scenario in enumerate(config["scenarios"], start=1):
        with tempfile.TemporaryDirectory(prefix="tailtrail-fsr6-scope-") as temporary:
            repository = Path(temporary)
            _materialize_fixture(repository, scenario)
            report = navigator.decide(str(scenario["goal"]), repository, [], "tailtrail", detect_git_changes=False)
            evidence = report["scope_evidence"]
            quality = report["scope_quality"]
            requirement = evidence["requirements"][0]
            observed_state = str(evidence["state"])
            owners = list(requirement["implementation_owners"]) if observed_state == "resolved" else []
            proof_paths = list(requirement["proof_paths"]) if observed_state == "resolved" else []
            question = quality.get("question") if isinstance(quality, dict) else None
            options = list(question.get("options", [])) if isinstance(question, dict) else []
            investigation = evidence.get("investigation", {})
            primary_reason = str(
                investigation.get("decision_reason")
                or investigation.get("resolution_failure_reason")
                or investigation.get("stop_reason")
                or "unknown"
            )
            run_id = f"fsr6-{index:02d}"
            command = [
                sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), str(scenario["goal"]),
                "--root", repository.as_posix(), "--planning-run-id", run_id, "--format", "json",
            ]
            started = subprocess.run(command, cwd=repository, text=True, capture_output=True, check=False)
            run_created = (repository / ".tailtrail" / "runs" / run_id).is_dir()
        expected_lock = bool(scenario["expect_planning_lock"])
        expected_state = str(scenario["expected_state"])
        expected_owner_set = set(scenario["expected_owners"])
        observed_owner_set = set(owners)
        expected_owners.extend(scenario["expected_owners"])
        observed_owners.extend(owners)
        irrelevant = sorted(set(options) - set(scenario["expected_question_options"]))
        unsafe_lock = run_created and (
            not expected_lock or observed_state != expected_state or observed_owner_set != expected_owner_set
        )
        false_stop = expected_lock and not run_created
        state_match = observed_state == expected_state
        owner_match = observed_owner_set == expected_owner_set
        proof_match = set(proof_paths) == set(scenario["expected_proof_paths"])
        options_match = options == scenario["expected_question_options"]
        reason_match = primary_reason == scenario["expected_primary_reason"]
        lock_match = run_created == expected_lock and started.returncode == (0 if expected_lock else 2)
        passed = all((state_match, owner_match, proof_match, options_match, reason_match, lock_match)) and not unsafe_lock and not false_stop
        scenario_results.append({
            "scenario_id": scenario["id"], "status": "passed" if passed else "failed",
            "expected_state": expected_state, "observed_state": observed_state,
            "expected_owners": sorted(expected_owner_set), "observed_owners": sorted(observed_owner_set),
            "expected_proof_paths": sorted(scenario["expected_proof_paths"]), "observed_proof_paths": sorted(proof_paths),
            "question_options": options, "irrelevant_options": irrelevant,
            "expected_primary_reason": scenario["expected_primary_reason"], "observed_primary_reason": primary_reason,
            "planning_lock_expected": expected_lock, "planning_lock_created": run_created,
            "start_exit_code": started.returncode, "false_stop": false_stop, "unsafe_lock": unsafe_lock,
        })
    profile_path = ROOT / config["language_profiles"]
    profiles = execute_language_profiles(read_json(profile_path, "language profile fixtures"))
    resolved_expected = sum(bool(row["planning_lock_expected"]) for row in scenario_results)
    total_options = sum(len(row["question_options"]) for row in scenario_results)
    false_stops = sum(bool(row["false_stop"]) for row in scenario_results)
    unsafe_locks = sum(bool(row["unsafe_lock"]) for row in scenario_results)
    irrelevant_options = sum(len(row["irrelevant_options"]) for row in scenario_results)
    reason_matches = sum(row["expected_primary_reason"] == row["observed_primary_reason"] for row in scenario_results)
    true_positive = sum(len(set(row["expected_owners"]) & set(row["observed_owners"])) for row in scenario_results)
    metrics = {
        "scenario_count": len(scenario_results),
        "false_stop_count": false_stops,
        "false_stop_rate": round(false_stops / resolved_expected, 4) if resolved_expected else 0.0,
        "irrelevant_option_count": irrelevant_options,
        "irrelevant_option_rate": round(irrelevant_options / total_options, 4) if total_options else 0.0,
        "unsafe_lock_count": unsafe_locks,
        "reason_code_accuracy": round(reason_matches / len(scenario_results), 4),
        "owner_precision": round(true_positive / len(observed_owners), 4) if observed_owners else 1.0,
        "owner_recall": round(true_positive / len(expected_owners), 4) if expected_owners else 1.0,
        "language_profile_pass_rate": profiles["pass_rate"],
    }
    thresholds = config["thresholds"]
    checks = [
        ("false_stop_rate", "<=", thresholds["false_stop_rate_max"]),
        ("irrelevant_option_rate", "<=", thresholds["irrelevant_option_rate_max"]),
        ("unsafe_lock_count", "<=", thresholds["unsafe_lock_count_max"]),
        ("reason_code_accuracy", ">=", thresholds["reason_code_accuracy_min"]),
        ("owner_precision", ">=", thresholds["owner_precision_min"]),
        ("owner_recall", ">=", thresholds["owner_recall_min"]),
        ("language_profile_pass_rate", ">=", thresholds["language_profile_pass_rate_min"]),
    ]
    threshold_results = [{
        "metric": metric, "operator": operator, "threshold": threshold, "actual": metrics[metric],
        "passed": metrics[metric] <= threshold if operator == "<=" else metrics[metric] >= threshold,
    } for metric, operator, threshold in checks]
    baseline = known_gap_baseline_summary()
    baseline_delta = {
        "false_stop_count": {"before": baseline["known_false_stop_count"], "after": false_stops, "delta": false_stops - baseline["known_false_stop_count"]},
        "irrelevant_option_count": {"before": baseline["observed_irrelevant_option_count"], "after": irrelevant_options, "delta": irrelevant_options - baseline["observed_irrelevant_option_count"]},
        "unsafe_lock_count": {"before": baseline["unsafe_lock_count"], "after": unsafe_locks, "delta": unsafe_locks - baseline["unsafe_lock_count"]},
    }
    return {
        "calibration_version": config["calibration_version"], "calibration_digest": config["integrity"]["digest"],
        "status": "passed" if all(row["passed"] for row in threshold_results) and all(row["status"] == "passed" for row in scenario_results) else "failed",
        "metrics": metrics, "baseline_delta": baseline_delta, "threshold_results": threshold_results,
        "scenarios": scenario_results, "language_profiles": profiles,
        "claim_boundaries": config["claim_boundaries"],
    }


def default_fsr6_assurance() -> dict[str, Any]:
    """Execute the sealed FSR-6 corpus once per process and return a copy."""
    global _FSR6_ASSURANCE_CACHE
    if _FSR6_ASSURANCE_CACHE is None:
        _FSR6_ASSURANCE_CACHE = execute_fsr6_assurance(
            read_json(DEFAULT_FSR6_CATALOG, "FSR-6 calibration")
        )
    return copy.deepcopy(_FSR6_ASSURANCE_CACHE)


def build_report(catalog: dict[str, Any]) -> dict[str, Any]:
    validate_catalog(catalog)
    known_gap_baseline = known_gap_baseline_summary()
    executable_assurance = default_fsr6_assurance()
    receipts = catalog["receipts"]
    expected_owners = [owner for row in receipts for owner in row["expected"]["implementation_owners"]]
    observed_owners = [owner for row in receipts for owner in row["observed"]["implementation_owners"]]
    true_positive = sum(len(set(row["expected"]["implementation_owners"]) & set(row["observed"]["implementation_owners"])) for row in receipts)
    weak_only = [row for row in receipts if row["observed"]["state"] == "resolved" and row["observed"]["strongest_evidence"] in {"none", "weak"}]
    test_false = [row for row in receipts if row["request_kind"] != "test-only" and row["observed"]["implementation_owners"] and all(test_path(path) for path in row["observed"]["implementation_owners"])]
    mismatches = [row for row in receipts if len(set(row["surface_fingerprints"].values())) != 1]
    unresolved = [row for row in receipts if row["observed"]["state"] != "resolved"]
    metrics = {
        "receipt_count": len(receipts),
        "weak_only_lock_count": len(weak_only),
        "test_only_false_scope_count": len(test_false),
        "scope_unresolved_rate": {
            "overall": round(len(unresolved) / len(receipts), 4),
            "by_task": grouped_rate(receipts, "task_class"),
            "by_language": grouped_rate(receipts, "language"),
        },
        "safe_refusal_count": sum(bool(row["observed"]["safe_refusal"]) for row in receipts),
        "manual_scope_revision_rate": round(sum(bool(row["manual_scope_revision"]) for row in receipts) / len(receipts), 4),
        "owner_precision": round(true_positive / len(observed_owners), 4) if observed_owners else 1.0,
        "owner_recall": round(true_positive / len(expected_owners), 4) if expected_owners else 1.0,
        "investigation": {
            "files": aggregate([row["investigation"]["files_read"] for row in receipts]),
            "bytes": aggregate([row["investigation"]["bytes_read"] for row in receipts]),
            "hops": aggregate([row["investigation"]["relationship_hops"] for row in receipts]),
            "duration_ms": aggregate([row["investigation"]["duration_ms"] for row in receipts]),
        },
        "fresh_graph_reuse_count": sum(bool(row["investigation"]["fresh_graph_reused"]) for row in receipts),
        "stale_graph_rejection_count": sum(bool(row["investigation"]["stale_graph_rejected"]) for row in receipts),
        "fingerprint_mismatch_count": len(mismatches),
    }
    findings: list[dict[str, Any]] = []
    for row in receipts:
        expected, observed = set(row["expected"]["implementation_owners"]), set(row["observed"]["implementation_owners"])
        kinds: list[str] = []
        if observed - expected:
            kinds.append("false-positive-owner")
        if expected - observed:
            kinds.append("false-negative-owner")
        if row in weak_only:
            kinds.append("weak-only-lock")
        if row in test_false:
            kinds.append("test-only-false-scope")
        if row in mismatches:
            kinds.append("surface-fingerprint-mismatch")
        findings.extend({"receipt_id": row["receipt_id"], "kind": kind, "expected_owners": sorted(expected), "observed_owners": sorted(observed), "action": "review-required"} for kind in kinds)
    covered_languages = sorted({row["language"] for row in receipts})
    covered_boundaries = sorted({boundary for row in receipts for boundary in row["negative_boundaries"]})
    coverage = {
        "supported_languages": catalog["supported_languages"],
        "covered_languages": covered_languages,
        "missing_languages": sorted(set(catalog["supported_languages"]) - set(covered_languages)),
        "required_negative_boundaries": catalog["negative_boundaries"],
        "covered_negative_boundaries": covered_boundaries,
        "missing_negative_boundaries": sorted(set(catalog["negative_boundaries"]) - set(covered_boundaries)),
    }
    thresholds = catalog["thresholds"]
    threshold_results = [
        {"metric": "weak_only_lock_count", "operator": "<=", "threshold": thresholds["weak_only_lock_count_max"], "actual": metrics["weak_only_lock_count"], "passed": metrics["weak_only_lock_count"] <= thresholds["weak_only_lock_count_max"]},
        {"metric": "test_only_false_scope_count", "operator": "<=", "threshold": thresholds["test_only_false_scope_count_max"], "actual": metrics["test_only_false_scope_count"], "passed": metrics["test_only_false_scope_count"] <= thresholds["test_only_false_scope_count_max"]},
        {"metric": "fingerprint_mismatch_count", "operator": "<=", "threshold": thresholds["fingerprint_mismatch_count_max"], "actual": metrics["fingerprint_mismatch_count"], "passed": metrics["fingerprint_mismatch_count"] <= thresholds["fingerprint_mismatch_count_max"]},
        {"metric": "owner_precision", "operator": ">=", "threshold": thresholds["owner_precision_min"], "actual": metrics["owner_precision"], "passed": metrics["owner_precision"] >= thresholds["owner_precision_min"]},
        {"metric": "owner_recall", "operator": ">=", "threshold": thresholds["owner_recall_min"], "actual": metrics["owner_recall"], "passed": metrics["owner_recall"] >= thresholds["owner_recall_min"]},
        {"metric": "language_coverage", "operator": ">=", "threshold": len(catalog["supported_languages"]), "actual": len(covered_languages), "passed": not coverage["missing_languages"]},
        {"metric": "negative_boundary_coverage", "operator": ">=", "threshold": len(catalog["negative_boundaries"]), "actual": len(covered_boundaries), "passed": not coverage["missing_negative_boundaries"]},
    ]
    report = {
        "schema_version": "1",
        "type": "tailtrail-navigator-scope-calibration-report",
        "status": "passed" if all(row["passed"] for row in threshold_results) and executable_assurance["status"] == "passed" else "failed",
        "evidence_label": "committed-fixture-observed",
        "catalog": {"version": catalog["catalog_version"], "digest": catalog["integrity"]["digest"], "receipt_count": len(receipts)},
        "coverage": coverage,
        "metrics": metrics,
        "threshold_results": threshold_results,
        "false_positive_review": findings,
        "known_gap_baseline": known_gap_baseline,
        "executable_assurance": executable_assurance,
        "negative_learning": {
            "learning_id": catalog["negative_learning"]["learning_id"],
            "state": "candidate-only",
            "source_receipt_ids": catalog["negative_learning"]["source_receipt_ids"],
            "capture_requires_approval": True,
            "use_requires_approval": True,
            "closure_attribution_required": True,
            "governance_gates": NEGATIVE_GATES,
        },
        "privacy": PRIVACY,
        "claims": {
            "posture": "fixture-only-no-performance-claim",
            "productivity_claim": False,
            "causal_benefit_claim": False,
            "boundaries": catalog["claim_boundaries"],
        },
        "integrity": {"algorithm": "sha256", "canonicalization": "sorted compact JSON excluding integrity", "digest": ""},
    }
    report["integrity"]["digest"] = unsigned_digest(report)
    return report


def capture_negative(root: Path, catalog: dict[str, Any], approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ScopeCalibrationError("negative learning capture requires --approved")
    if not root.is_dir():
        raise ScopeCalibrationError(f"project root is missing: {root}")
    report = build_report(catalog)
    if report["status"] != "passed" or report["false_positive_review"]:
        raise ScopeCalibrationError("negative learning capture requires a passing, false-positive-free calibration report")
    v3 = load_module("ns8_learning_v3", "scripts/learning-v3.py")
    candidate = catalog["negative_learning"]
    existing = v3.latest_records(v3.read_records(root)).get(candidate["learning_id"])
    if existing:
        if existing["provenance"]["source_fingerprint"] != "sha256:" + catalog["integrity"]["digest"]:
            raise ScopeCalibrationError("existing negative learning has different calibration provenance")
        return {"status": "already-captured", "record": existing, "boundary": "Existing governed candidate reused; no duplicate Learning V3 event was written."}
    record = v3.build_record(
        root,
        learning_id=candidate["learning_id"],
        learning_class=candidate["learning_class"],
        summary=candidate["summary"],
        advice=candidate["advice"],
        source_kind="navigator-scope-negative-calibration",
        source_ref=f"navigator-scope-calibration:v1:{catalog['integrity']['digest']}",
        source_fingerprint="sha256:" + catalog["integrity"]["digest"],
        captured_by="Navigator NS-8 Calibration",
        evidence_refs=[f"decision-receipt:{receipt_id}" for receipt_id in candidate["source_receipt_ids"]],
        task_types=candidate["task_types"],
        tags=candidate["tags"],
        path_patterns=candidate["path_patterns"],
        exclusions=[],
        invalidators=candidate["invalidators"],
        stale_when=candidate["stale_when"],
        confidence_score=candidate["confidence_score"],
        curated=False,
        reason="approval-gated governed negative-learning capture from sealed NS-8 receipts",
    )
    saved = v3.append_record(root, record)
    return {
        "status": "captured",
        "record": saved,
        "next_gate": "Project-framed retrieval may propose this weak-note only after conflict, freshness, invalidator, and privacy checks; explicit use receipt and later closure attribution remain required.",
        "boundary": "Capture records an inert Learning V3 candidate. It does not inject advice, change scope, approve a plan, or grant execution authority.",
    }


def render(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    known_gap = report["known_gap_baseline"]
    executable = report["executable_assurance"]
    release_metrics = executable["metrics"]
    lines = [
        "# TailTrail Navigator Scope Calibration",
        "",
        f"- Status: `{report['status']}`",
        f"- Evidence: `{report['evidence_label']}`",
        f"- Decision receipts: `{metrics['receipt_count']}`",
        f"- Supported language coverage: `{len(report['coverage']['covered_languages'])}/{len(report['coverage']['supported_languages'])}`",
        f"- Negative boundary coverage: `{len(report['coverage']['covered_negative_boundaries'])}/{len(report['coverage']['required_negative_boundaries'])}`",
        "",
        "## Negative assurance",
        "",
        f"- Weak-only locks: `{metrics['weak_only_lock_count']}`",
        f"- Non-test requests falsely scoped only to tests: `{metrics['test_only_false_scope_count']}`",
        f"- Surface fingerprint mismatches: `{metrics['fingerprint_mismatch_count']}`",
        f"- Safe refusals (protected, not failures): `{metrics['safe_refusal_count']}`",
        f"- Owner precision / recall: `{metrics['owner_precision']:.4f}` / `{metrics['owner_recall']:.4f}`",
        f"- Manual scope revision rate: `{metrics['manual_scope_revision_rate']:.4f}`",
        "",
        "## Executable FSR-6 assurance",
        "",
        f"- Scenario results: `{sum(row['status'] == 'passed' for row in executable['scenarios'])}/{len(executable['scenarios'])}` passed",
        f"- Supported language profiles: `{executable['language_profiles']['passed']}/{executable['language_profiles']['supported']}` passed",
        f"- False-stop rate: `{release_metrics['false_stop_rate']:.4f}`",
        f"- Irrelevant-option rate: `{release_metrics['irrelevant_option_rate']:.4f}`",
        f"- Unsafe locks: `{release_metrics['unsafe_lock_count']}`",
        f"- Reason-code accuracy: `{release_metrics['reason_code_accuracy']:.4f}`",
        f"- Owner precision / recall: `{release_metrics['owner_precision']:.4f}` / `{release_metrics['owner_recall']:.4f}`",
        f"- False-stop delta from FSR-0: `{executable['baseline_delta']['false_stop_count']['delta']}`",
        f"- Irrelevant-option delta from FSR-0: `{executable['baseline_delta']['irrelevant_option_count']['delta']}`",
        "",
        "## Open characterization baseline",
        "",
        f"- Phase: `{known_gap['phase']}`",
        f"- Status: `{known_gap['status']}`",
        f"- Known false stops: `{known_gap['known_false_stop_count']}`",
        f"- Safe-stop controls: `{known_gap['safe_stop_control_count']}`",
        f"- Irrelevant scope options observed: `{known_gap['observed_irrelevant_option_count']}`",
        f"- Unsafe locks: `{known_gap['unsafe_lock_count']}`",
        f"- Release ready: `{str(known_gap['release_ready']).lower()}`",
        f"- Boundary: {known_gap['claim_boundary']}",
        "",
        "## Learning boundary",
        "",
        f"- `{report['negative_learning']['learning_id']}` remains `candidate-only`.",
        "- Capture and use each require explicit approval; later closure attribution is mandatory.",
        "- Conflict, freshness, invalidator, privacy, use-receipt, and closure-attribution gates remain authoritative.",
        "",
        "## Claim boundary",
        "",
        "- Fixture-only evidence; no productivity, quality-improvement, or causal-benefit claim.",
    ]
    if report["false_positive_review"]:
        lines.extend(["", "## False-positive review", ""])
        lines.extend(f"- `{row['receipt_id']}`: `{row['kind']}` (`review-required`)" for row in report["false_positive_review"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "report", "capture-negative"))
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        catalog = read_json(args.catalog, "scope calibration catalog")
        if args.command == "validate":
            validate_catalog(catalog)
            value: Any = {"schema_version": "1", "type": "tailtrail-navigator-scope-calibration-validation", "status": "passed", "receipts": len(catalog["receipts"]), "languages": catalog["supported_languages"], "negative_boundaries": catalog["negative_boundaries"], "boundary": "Read-only sealed fixture and privacy validation; no metric or learning state was written."}
        elif args.command == "report":
            value = build_report(catalog)
        else:
            value = capture_negative(args.root.resolve(), catalog, args.approved)
    except (OSError, json.JSONDecodeError, ScopeCalibrationError, ValueError) as error:
        print(f"Navigator scope calibration error: {error}")
        return 2
    if args.format == "json" or args.command != "report":
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        print(render(value), end="")
    return 0 if value.get("status") != "failed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
