from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "scripts").as_posix() not in sys.path:
    sys.path.insert(0, (ROOT / "scripts").as_posix())
CATALOG_PATH = ROOT / "benchmarks/evaluation/navigator-scope/v1.json"
CATALOG_SCHEMA = ROOT / "schemas/navigator-scope-calibration-catalog.schema.json"
REPORT_SCHEMA = ROOT / "schemas/navigator-scope-calibration-report.schema.json"


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CAL = load("ns8_scope_calibration_test", "scripts/navigator-scope-calibration.py")
V3 = load("ns8_learning_v3_test", "scripts/learning-v3.py")
RETRIEVAL = load("ns8_learning_retrieval_test", "scripts/learning-retrieval.py")
RECEIPTS = load("ns8_learning_receipts_test", "scripts/learning-use-receipt.py")
LOCK = load("ns8_planning_lock_test", "scripts/planning_lock.py")
ANCHOR = load("ns8_anchor_test", "scripts/change-intent-anchor.py")
CONTRACTS = load("ns8_contracts_test", "scripts/workflow_runtime/contracts.py")


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def reseal(catalog: dict) -> dict:
    for receipt in catalog["receipts"]:
        unsigned = {key: value for key, value in receipt.items() if key != "receipt_fingerprint"}
        receipt["receipt_fingerprint"] = "sha256:" + hashlib.sha256(canonical(unsigned)).hexdigest()
    unsigned_catalog = {key: value for key, value in catalog.items() if key != "integrity"}
    catalog["integrity"]["digest"] = hashlib.sha256(canonical(unsigned_catalog)).hexdigest()
    return catalog


def reseal_document(value: dict) -> dict:
    unsigned = {key: item for key, item in value.items() if key != "integrity"}
    value["integrity"]["digest"] = hashlib.sha256(canonical(unsigned)).hexdigest()
    return value


def completion(uid: str) -> dict:
    return {
        "overall_status": "complete",
        "requirement_status": {"complete": 1, "total": 1, "requirements": [{"requirement_uid": uid, "status": "complete"}]},
        "harnesses": [
            {"name": "Requirement Completion Harness", "status": "pass"},
            {"name": "Evidence-Aware Testing", "status": "pass"},
        ],
        "drift": {"status": "none-unresolved", "findings": []},
        "execution_failures": {"status": "none-recorded", "unresolved": []},
        "tests": {"status": "pass"},
    }


class NavigatorScopeCalibrationTests(unittest.TestCase):
    def catalog(self) -> dict:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    def test_catalog_and_report_are_closed_schema_valid_and_sealed(self) -> None:
        catalog = self.catalog()
        CAL.validate_catalog(catalog)
        report = CAL.build_report(catalog)

        self.assertEqual([], CONTRACTS.validate_document(catalog, json.loads(CATALOG_SCHEMA.read_text(encoding="utf-8"))))
        self.assertEqual([], CONTRACTS.validate_document(report, json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))))
        self.assertEqual("passed", report["status"])
        self.assertEqual("known-gap", report["known_gap_baseline"]["status"])
        self.assertEqual(1, report["known_gap_baseline"]["known_false_stop_count"])
        self.assertEqual(1, report["known_gap_baseline"]["safe_stop_control_count"])
        self.assertEqual(9, report["known_gap_baseline"]["observed_irrelevant_option_count"])
        self.assertEqual(0, report["known_gap_baseline"]["unsafe_lock_count"])
        self.assertFalse(report["known_gap_baseline"]["release_ready"])
        self.assertEqual("passed", report["executable_assurance"]["status"])
        self.assertEqual(CAL.unsigned_digest(report), report["integrity"]["digest"])

    def test_metrics_cover_every_language_and_negative_boundary_without_causal_claims(self) -> None:
        report = CAL.build_report(self.catalog())
        metrics = report["metrics"]

        self.assertEqual(CAL.supported_languages(), report["coverage"]["covered_languages"])
        self.assertEqual([], report["coverage"]["missing_languages"])
        self.assertEqual([], report["coverage"]["missing_negative_boundaries"])
        self.assertEqual(0, metrics["weak_only_lock_count"])
        self.assertEqual(0, metrics["test_only_false_scope_count"])
        self.assertEqual(0, metrics["fingerprint_mismatch_count"])
        self.assertEqual(1.0, metrics["owner_precision"])
        self.assertEqual(1.0, metrics["owner_recall"])
        self.assertEqual(2, metrics["safe_refusal_count"])
        self.assertGreater(metrics["scope_unresolved_rate"]["overall"], 0)
        self.assertTrue(all(row["passed"] for row in report["threshold_results"]))
        self.assertFalse(report["claims"]["productivity_claim"])
        self.assertFalse(report["claims"]["causal_benefit_claim"])
        self.assertNotIn("productivity improvement", json.dumps(report).lower())

    def test_fsr6_executes_false_stop_safe_stop_and_language_profile_contracts(self) -> None:
        assurance = CAL.default_fsr6_assurance()
        metrics = assurance["metrics"]

        self.assertEqual("passed", assurance["status"])
        self.assertEqual(3, metrics["scenario_count"])
        self.assertEqual(0, metrics["false_stop_count"])
        self.assertEqual(0.0, metrics["false_stop_rate"])
        self.assertEqual(0, metrics["irrelevant_option_count"])
        self.assertEqual(0.0, metrics["irrelevant_option_rate"])
        self.assertEqual(0, metrics["unsafe_lock_count"])
        self.assertEqual(1.0, metrics["reason_code_accuracy"])
        self.assertEqual(1.0, metrics["owner_precision"])
        self.assertEqual(1.0, metrics["owner_recall"])
        self.assertEqual(7, assurance["language_profiles"]["supported"])
        self.assertEqual(7, assurance["language_profiles"]["passed"])
        self.assertTrue(all(row["status"] == "passed" for row in assurance["scenarios"]))
        self.assertEqual(-1, assurance["baseline_delta"]["false_stop_count"]["delta"])
        self.assertEqual(-9, assurance["baseline_delta"]["irrelevant_option_count"]["delta"])

    def test_fsr6_unsafe_lock_and_invented_expected_owner_fail_release_thresholds(self) -> None:
        config = json.loads(CAL.DEFAULT_FSR6_CATALOG.read_text(encoding="utf-8"))
        config["scenarios"][0]["expected_owners"] = ["src/components/RemoveButton.tsx"]
        reseal_document(config)

        assurance = CAL.execute_fsr6_assurance(config)

        self.assertEqual("failed", assurance["status"])
        self.assertEqual(1, assurance["metrics"]["unsafe_lock_count"])
        self.assertLess(assurance["metrics"]["owner_precision"], 1.0)
        self.assertTrue(any(not row["passed"] for row in assurance["threshold_results"]))

    def test_fsr6_catalogs_reject_tampering_and_nonzero_unsafe_lock_tolerance(self) -> None:
        config = json.loads(CAL.DEFAULT_FSR6_CATALOG.read_text(encoding="utf-8"))
        config["thresholds"]["unsafe_lock_count_max"] = 1
        reseal_document(config)
        with self.assertRaisesRegex(CAL.ScopeCalibrationError, "unsafe lock tolerance"):
            CAL.validate_fsr6_catalog(config)

        profiles = json.loads((ROOT / config["language_profiles"]).read_text(encoding="utf-8"))
        profiles["profiles"][0]["expected_definitions"] = ["InventedOwner"]
        with self.assertRaisesRegex(CAL.ScopeCalibrationError, "digest mismatch"):
            CAL.validate_language_profiles(profiles)

    def test_safe_refusal_is_observable_but_not_a_failed_threshold(self) -> None:
        report = CAL.build_report(self.catalog())
        threshold_names = {row["metric"] for row in report["threshold_results"]}

        self.assertEqual("passed", report["status"])
        self.assertNotIn("scope_unresolved_rate", threshold_names)
        self.assertGreater(report["metrics"]["safe_refusal_count"], 0)
        self.assertEqual([], report["false_positive_review"])

    def test_false_scope_and_surface_drift_fail_calibration_and_enter_review(self) -> None:
        catalog = self.catalog()
        receipt = next(row for row in catalog["receipts"] if row["receipt_id"] == "ns8-python-owner")
        receipt["observed"]["implementation_owners"] = ["tests/test_aidlc_requirements.py"]
        receipt["surface_fingerprints"]["claude"] = "sha256:" + "f" * 64
        reseal(catalog)

        report = CAL.build_report(catalog)
        findings = {(row["receipt_id"], row["kind"]) for row in report["false_positive_review"]}

        self.assertEqual("failed", report["status"])
        self.assertEqual(1, report["metrics"]["test_only_false_scope_count"])
        self.assertEqual(1, report["metrics"]["fingerprint_mismatch_count"])
        self.assertIn(("ns8-python-owner", "false-positive-owner"), findings)
        self.assertIn(("ns8-python-owner", "test-only-false-scope"), findings)
        self.assertIn(("ns8-python-owner", "surface-fingerprint-mismatch"), findings)

    def test_tampered_or_nonfactual_receipts_are_rejected_before_metrics(self) -> None:
        tampered = self.catalog()
        tampered["receipts"][0]["observed"]["strongest_evidence"] = "medium"
        with self.assertRaisesRegex(CAL.ScopeCalibrationError, "fingerprint mismatch"):
            CAL.build_report(tampered)

        fabricated = self.catalog()
        fabricated["receipts"][0]["factual"] = False
        reseal(fabricated)
        with self.assertRaisesRegex(CAL.ScopeCalibrationError, "factual committed-fixture"):
            CAL.build_report(fabricated)

    def test_raw_or_identity_fields_cannot_enter_calibration(self) -> None:
        catalog = self.catalog()
        catalog["raw_source"] = "not allowed"
        reseal(catalog)
        with self.assertRaisesRegex(CAL.ScopeCalibrationError, "contract is not closed|privacy"):
            CAL.validate_catalog(catalog)

    def test_negative_learning_capture_is_default_deny_idempotent_and_weak_note(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(CAL.ScopeCalibrationError, "requires --approved"):
                CAL.capture_negative(root, self.catalog(), False)
            first = CAL.capture_negative(root, self.catalog(), True)
            second = CAL.capture_negative(root, self.catalog(), True)

        record = first["record"]
        self.assertEqual("captured", first["status"])
        self.assertEqual("already-captured", second["status"])
        self.assertEqual("avoid-history", record["learning_class"])
        self.assertEqual("weak-note", record["utility"]["confidence_band"])
        self.assertFalse(record["utility"]["curated"])
        self.assertFalse(record["utility"]["causal_claim"])
        self.assertEqual(CAL.PRIVACY | {"sensitivity": "normal"}, record["privacy"])

    def test_negative_learning_is_blocked_when_graph_freshness_invalidator_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            learning = CAL.capture_negative(root, self.catalog(), True)["record"]
            graph = root / ".tailtrail/code-graph-cache.json"
            graph.parent.mkdir(parents=True, exist_ok=True)
            graph.write_text("{}\n", encoding="utf-8")
            proposal = RETRIEVAL.build_proposal(
                root,
                task_types=["build"],
                tags=["navigator-scope", "negative-assurance"],
                paths=[],
                requirement_ids=[],
                mode="lite",
            )

        blocked = next(row for row in proposal["blocked"] if row["learning_id"] == learning["learning_id"])
        self.assertNotIn(learning["learning_id"], {row["learning_id"] for row in proposal["matches"]})
        self.assertIn("graph-change invalidator triggered", blocked["reasons"])

    def test_learning_requires_retrieval_use_receipt_and_later_closure_attribution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            captured = CAL.capture_negative(root, self.catalog(), True)["record"]
            proposal = RETRIEVAL.build_proposal(
                root,
                task_types=["build"],
                tags=["navigator-scope", "negative-assurance"],
                paths=[],
                requirement_ids=[],
                mode="lite",
            )
            self.assertEqual("proposed", proposal["state"])
            self.assertTrue(proposal["approval"]["required"])
            self.assertEqual("do-not-use", proposal["approval"]["default"])

            LOCK.create(root, "verify negative scope learning gates", "ns8-run")
            LOCK.save_start_report(root, "ns8-run", {"goal": "verify negative scope learning gates", "navigator": {"learning_use_proposal": proposal}})
            LOCK.approve(root, "ns8-run", True)
            anchor_proposal = root / "anchor.json"
            anchor_proposal.write_text(json.dumps({"requirements": [{
                "statement": "preserve implementation ownership scope",
                "acceptance_criteria": ["test-only lexical matches are not implementation owners"],
                "preserve_rules": ["safe refusal remains allowed"],
                "likely_paths": ["scripts/navigator_scope.py"],
                "evidence_plan": ["NS-8 calibration receipt"],
            }]}), encoding="utf-8")
            ANCHOR.draft(root, "ns8-run", anchor_proposal)
            uid = ANCHOR.approve(root, "ns8-run")["requirements"][0]["requirement_uid"]

            before = RECEIPTS.attribute_completion(root, "ns8-run", completion(uid))
            decision = RECEIPTS.record_decision(
                root,
                "ns8-run",
                learning_id=captured["learning_id"],
                decision="applied",
                decision_type="implementation",
                requirement_uids=[uid],
                rationale="Explicitly apply the governed negative scope advice.",
                approved=True,
            )
            attributed = RECEIPTS.attribute_completion(root, "ns8-run", completion(uid))
            events = RECEIPTS.read_events(root, "ns8-run")

        self.assertEqual("no-receipts", before["status"])
        self.assertEqual("decision", decision["event_kind"])
        self.assertEqual("attributed", attributed["status"])
        self.assertEqual("potentially-helped", events[-1]["outcome"]["association"])
        self.assertFalse(events[-1]["utility"]["causal_claim"])

    def test_eval_scope_cli_route_is_read_only_and_reports_fixture_boundary(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/tailtrail.py"), "eval", "scope", "report", "--format", "json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("passed", report["status"])
        self.assertEqual("committed-fixture-observed", report["evidence_label"])
        self.assertEqual("fixture-only-no-performance-claim", report["claims"]["posture"])
        self.assertEqual("known-gap", report["known_gap_baseline"]["status"])
        self.assertFalse(report["known_gap_baseline"]["release_ready"])


if __name__ == "__main__":
    unittest.main()
