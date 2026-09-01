import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts" / "adoption-validation.py"
    spec = importlib.util.spec_from_file_location("adoption_validation_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class AdoptionValidationTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.catalog = self.module.load_catalog()

    def tearDown(self):
        self.temporary.cleanup()

    def trial(self, *, cohort="new-user", index=0, evidence_kind="moderated-observation", safety=True, signal=None):
        definitions = self.module.cohort_map(self.catalog)[cohort]
        participant = index if index < 5 else 0
        value = {
            "schema_version": "1",
            "type": "tailtrail-adoption-trial-input",
            "trial_id": f"trial-{cohort}-{index:02d}",
            "cohort": cohort,
            "scenario_id": definitions["scenarios"][index % 3],
            "participant_ref": f"anon-{cohort}-{participant:02d}",
            "evidence_kind": evidence_kind,
            "observer_attested": evidence_kind != "protocol-fixture",
            "started_at": f"2026-09-01T{index:02d}:00:00Z",
            "valid_plan_at": f"2026-09-01T{index:02d}:02:00Z",
            "completed_at": f"2026-09-01T{index:02d}:08:00Z",
            "outcome": "completed",
            "approval_count": 1,
            "redundant_approval_count": 0,
            "intervention_count": 0,
            "false_intervention_count": 0,
            "completion_comprehension": {"correct": 4, "total": 4},
            "safety_checks": {boundary: safety for boundary in self.catalog["safety_boundaries"]},
            "feedback_signals": [signal] if signal else [],
            "evidence_refs": [] if evidence_kind == "protocol-fixture" else [f"study/session-{cohort}-{index}"],
        }
        return value

    def record_value(self, value):
        path = self.root / f"{value['trial_id']}-input.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return self.module.record(self.root, path.relative_to(self.root), True)

    def record_qualifying_set(self, signal="approval-wording-unclear"):
        for cohort in ("new-user", "experienced-user"):
            for index in range(6):
                self.record_value(self.trial(cohort=cohort, index=index, signal=signal if cohort == "new-user" and index < 3 else None))

    def test_catalog_is_sealed_and_defines_both_cohorts_and_numeric_gates(self):
        result = self.module.validate_catalog()
        self.assertEqual("passed", result["status"])
        self.assertEqual(2, result["cohorts"])
        self.assertEqual(8, result["scenario_count"])
        self.assertEqual(0, self.catalog["thresholds"]["safety_boundary_weakening_count_max"])

    def test_empty_and_fixture_only_reports_make_no_adoption_claim(self):
        empty = self.module.report(self.root)
        self.assertEqual("protocol-ready", empty["status"])
        self.assertEqual("no-adoption-claim", empty["claim_status"])
        self.record_value(self.trial(evidence_kind="protocol-fixture"))
        fixture = self.module.report(self.root)
        self.assertEqual("fixture-only", fixture["status"])
        self.assertEqual(0, fixture["evidence"]["qualifying_observations"])
        self.assertEqual("no-adoption-claim", fixture["claim_status"])

    def test_record_requires_approval_and_closed_privacy_safe_input(self):
        value = self.trial()
        path = self.root / "input.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "--approved"):
            self.module.record(self.root, Path("input.json"), False)
        value["raw_prompt"] = "must not be stored"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "prohibited"):
            self.module.record(self.root, Path("input.json"), True)
        value.pop("raw_prompt")
        value["participant_ref"] = "person@example.com"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "participant_ref"):
            self.module.record(self.root, Path("input.json"), True)

    def test_qualifying_trials_meet_all_gates_and_enable_repeated_signal(self):
        self.record_qualifying_set()
        report = self.module.report(self.root)
        self.assertEqual("qualified", report["status"])
        self.assertEqual("scenario-scoped-adoption-evidence", report["claim_status"])
        self.assertEqual(12, report["evidence"]["qualifying_observations"])
        self.assertTrue(all(row["passed"] for row in report["gates"]))
        recommendation = next(row for row in report["recommendations"] if row["signal_id"] == "approval-wording-unclear")
        self.assertTrue(recommendation["eligible"])
        self.assertEqual(3, recommendation["participant_count"])

    def test_safety_weakening_cannot_be_compensated_by_good_metrics(self):
        self.record_qualifying_set()
        path = self.root / self.module.STATE_ROOT / "trials" / "trial-new-user-00.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["safety_checks"][self.catalog["safety_boundaries"][0]] = False
        receipt = self.module.sealed(receipt)
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report = self.module.report(self.root)
        self.assertEqual("thresholds-not-met", report["status"])
        safety = next(row for row in report["gates"] if row["id"] == "overall.safety-boundary-weakening")
        self.assertFalse(safety["passed"])
        self.assertEqual("no-adoption-claim", report["claim_status"])

    def test_each_named_adoption_metric_can_block_qualification(self):
        def abandon(value, cohort, index):
            if cohort == "new-user" and index < 2:
                value.update({"outcome": "abandoned", "completed_at": None, "completion_comprehension": {"correct": 0, "total": 0}})

        def slow_plan(value, cohort, index):
            if cohort == "new-user" and index < 2:
                value["valid_plan_at"] = f"2026-09-01T{index:02d}:06:00Z"

        def excessive_approvals(value, cohort, index):
            if cohort == "new-user" and index < 2:
                value["approval_count"] = 3

        def redundant_approvals(value, _cohort, index):
            if index == 0:
                value["redundant_approval_count"] = 1

        def false_interventions(value, _cohort, index):
            if index == 0:
                value.update({"intervention_count": 1, "false_intervention_count": 1})

        def weak_comprehension(value, cohort, index):
            if cohort == "new-user" and index < 2:
                value["completion_comprehension"] = {"correct": 0, "total": 4}

        cases = (
            ("overall.abandonment-rate", abandon),
            ("new-user.time-to-plan-p75-ms", slow_plan),
            ("new-user.approval-count-p75", excessive_approvals),
            ("overall.redundant-approval-rate", redundant_approvals),
            ("overall.false-intervention-rate", false_interventions),
            ("overall.completion-comprehension", weak_comprehension),
        )
        for gate_id, mutate in cases:
            with self.subTest(gate=gate_id), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for cohort in ("new-user", "experienced-user"):
                    for index in range(6):
                        value = self.trial(cohort=cohort, index=index)
                        mutate(value, cohort, index)
                        source = root / f"{value['trial_id']}-input.json"
                        source.write_text(json.dumps(value), encoding="utf-8")
                        self.module.record(root, source.relative_to(root), True)
                report = self.module.report(root)
                selected = next(row for row in report["gates"] if row["id"] == gate_id)
                self.assertFalse(selected["passed"], report)
                self.assertEqual("thresholds-not-met", report["status"])
                self.assertEqual("no-adoption-claim", report["claim_status"])

    def test_tampered_receipt_invalidates_report(self):
        recorded = self.record_value(self.trial())
        path = self.root / recorded["artifact"]
        value = json.loads(path.read_text(encoding="utf-8"))
        value["approval_count"] = 99
        path.write_text(json.dumps(value), encoding="utf-8")
        report = self.module.report(self.root)
        self.assertEqual("invalid", report["status"])
        self.assertTrue(any("integrity" in issue for issue in report["issues"]))

    def test_evidence_backed_proposal_and_applied_decision_are_immutable(self):
        self.record_qualifying_set()
        report = self.module.report(self.root)
        recommendation = next(row for row in report["recommendations"] if row["signal_id"] == "approval-wording-unclear")
        with self.assertRaisesRegex(ValueError, "--approved"):
            self.module.propose(self.root, recommendation["recommendation_id"], False)
        proposal = self.module.propose(self.root, recommendation["recommendation_id"], True)
        with self.assertRaisesRegex(ValueError, "change-ref"):
            self.module.decide(self.root, Path(proposal["artifact"]), "applied", "evidence-supported", None, None, True)
        decision = self.module.decide(
            self.root,
            Path(proposal["artifact"]),
            "applied",
            "evidence-supported",
            "changes/approval-copy",
            "tests/adoption-copy-check",
            True,
        )
        self.assertEqual("applied", decision["decision"])
        latest = self.module.report(self.root)["improvement_decisions"]
        self.assertEqual("applied", latest[0]["decision"])
        with self.assertRaisesRegex(ValueError, "already has"):
            self.module.decide(
                self.root,
                Path(proposal["artifact"]),
                "rejected",
                "superseded",
                None,
                None,
                True,
            )
        decision_path = self.root / decision["artifact"]
        decision_path.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.module.decide(
                self.root,
                Path(proposal["artifact"]),
                "applied",
                "evidence-supported",
                "changes/approval-copy",
                "tests/adoption-copy-check",
                True,
            )

    def test_paths_outside_root_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "inside"):
            self.module.record(self.root, Path("../outside.json"), True)


if __name__ == "__main__":
    unittest.main()
