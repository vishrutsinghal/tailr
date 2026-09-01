from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V3 = load("pm_l3_v3", "scripts/learning-v3.py")
RETRIEVAL = load("pm_l3_retrieval", "scripts/learning-retrieval.py")
RECEIPTS = load("pm_l3_receipts", "scripts/learning-use-receipt.py")
LOCK = load("pm_l3_lock", "scripts/planning-lock.py")
ANCHOR = load("pm_l3_anchor", "scripts/change-intent-anchor.py")
REPORT = load("pm_l3_completion", "scripts/completion-report.py")
LEDGER = load("pm_l3_ledger", "scripts/run-ledger.py")


def completion(uid: str, *, complete: bool = True, drift: bool = False) -> dict:
    return {
        "overall_status": "complete" if complete and not drift else "evidence-incomplete",
        "requirement_status": {
            "complete": 1 if complete and not drift else 0,
            "total": 1,
            "requirements": [{"requirement_uid": uid, "status": "complete" if complete and not drift else "incomplete"}],
        },
        "harnesses": [
            {"name": "Requirement Completion Harness", "status": "pass" if complete and not drift else "fail"},
            {"name": "Evidence-Aware Testing", "status": "pass" if complete else "fail"},
        ],
        "drift": {"status": "unresolved" if drift else "none-unresolved", "findings": [{"requirement_uid": uid, "classification": "new-drift"}] if drift else []},
        "execution_failures": {"status": "none-recorded", "unresolved": []},
        "tests": {"status": "pass" if complete else "fail"},
    }


class LearningUseReceiptTests(unittest.TestCase):
    def setup_run(self, root: Path, run_id: str = "run", *, decision_type: str = "implementation") -> tuple[dict, str, dict]:
        learning = V3.latest_records(V3.read_records(root)).get("lrn-receipt-test")
        if learning is None:
            learning = V3.build_record(
                root,
                learning_id="lrn-receipt-test",
                learning_class="positive-pattern",
                summary="Use a focused validation receipt",
                advice="Run the focused validation receipt before closure",
                source_kind="pm-l3-test",
                source_ref="fixture.json",
                source_fingerprint="sha256:" + "0" * 64,
                captured_by="PM-L3 test",
                task_types=["test"],
                tags=[],
                path_patterns=[],
                exclusions=[],
                invalidators=[],
                confidence_score=90,
            )
            learning = V3.append_record(root, learning)
        proposal = RETRIEVAL.build_proposal(
            root, task_types=["test"], tags=[], paths=[], requirement_ids=[], mode="standard",
        )
        LOCK.create(root, "validate receipt attribution", run_id)
        LOCK.save_start_report(root, run_id, {
            "goal": "validate receipt attribution",
            "navigator": {"learning_use_proposal": proposal},
        })
        LOCK.approve(root, run_id, True)
        anchor_proposal = root / f"{run_id}-proposal.json"
        anchor_proposal.write_text(json.dumps({"requirements": [{
            "statement": "record learning use",
            "acceptance_criteria": ["receipt is attributed"],
            "preserve_rules": ["do not claim causality"],
            "likely_paths": ["scripts/learning-use-receipt.py"],
            "evidence_plan": ["focused test"],
        }]}), encoding="utf-8")
        ANCHOR.draft(root, run_id, anchor_proposal)
        uid = ANCHOR.approve(root, run_id)["requirements"][0]["requirement_uid"]
        return learning, uid, proposal

    def record(self, root: Path, learning: dict, uid: str, *, run_id: str = "run", decision: str = "applied", decision_type: str = "implementation") -> dict:
        return RECEIPTS.record_decision(
            root, run_id,
            learning_id=learning["learning_id"], decision=decision, decision_type=decision_type,
            requirement_uids=[uid], rationale=f"PM-L3 test decision: {decision}", approved=True,
        )

    def test_records_every_decision_state_append_only_and_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            types = ["implementation", "validation", "architecture", "behavior", "review"]
            rows = [self.record(root, learning, uid, decision=decision, decision_type=kind) for decision, kind in zip(sorted(RECEIPTS.DECISIONS), types)]
            reused = self.record(root, learning, uid, decision=sorted(RECEIPTS.DECISIONS)[0], decision_type=types[0])
            events = RECEIPTS.read_events(root, "run")

        self.assertEqual({row["decision"] for row in rows}, RECEIPTS.DECISIONS)
        self.assertEqual(len(events), 5)
        self.assertTrue(reused["reused"])
        self.assertTrue(all(row["requirement_uids"] == [uid] for row in events))
        self.assertTrue(all(row["utility"] is None for row in events))

    def test_decision_requires_approved_lock_known_requirement_and_saved_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            with self.assertRaisesRegex(ValueError, "requires --approved"):
                RECEIPTS.record_decision(root, "run", learning_id=learning["learning_id"], decision="applied", decision_type="implementation", requirement_uids=[uid], rationale="safe", approved=False)
            with self.assertRaisesRegex(ValueError, "known approved"):
                RECEIPTS.record_decision(root, "run", learning_id=learning["learning_id"], decision="applied", decision_type="implementation", requirement_uids=["unknown"], rationale="safe", approved=True)
            with self.assertRaisesRegex(ValueError, "single local"):
                RECEIPTS.show(root, "../run")
            with self.assertRaisesRegex(Exception, "sensitive"):
                RECEIPTS.record_decision(root, "run", learning_id=learning["learning_id"], decision="applied", decision_type="implementation", requirement_uids=[uid], rationale="token=do-not-store", approved=True)

    def test_terminal_or_blocked_advice_cannot_be_applied(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            V3.terminal_transition(root, learning["learning_id"], "revoke", "new evidence invalidated it")
            with self.assertRaisesRegex(ValueError, "terminal"):
                self.record(root, learning, uid)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            path = LEDGER.state_dir(root, "run") / "planning" / "start-report-v1.json"
            saved = json.loads(path.read_text(encoding="utf-8"))
            proposal = saved["report"]["navigator"]["learning_use_proposal"]
            match = proposal["matches"].pop()
            proposal["blocked"].append({
                "learning_id": match["learning_id"], "record_id": match["record_id"],
                "reasons": ["blocked by current evidence"], "invalidator_checks": [],
            })
            path.write_text(json.dumps(saved), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "blocked learning advice"):
                self.record(root, learning, uid)

    def test_closure_attribution_is_requirement_linked_non_causal_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            self.record(root, learning, uid)
            first = RECEIPTS.attribute_completion(root, "run", completion(uid), completion_ref=".tailtrail/runs/run/completion-reports/report-1.json")
            report_path = root / ".tailtrail" / "runs" / "run" / "completion-reports" / "report-1.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text("{}\n", encoding="utf-8")
            repeated = RECEIPTS.attribute_completion(root, "run", completion(uid), completion_ref=".tailtrail/runs/run/completion-reports/report-2.json")
            events = RECEIPTS.read_events(root, "run")
            utility = RECEIPTS.utility_adjustments(root)

        self.assertEqual(first["associations"], {"potentially-helped": 1})
        self.assertTrue(repeated["receipts"][0]["reused"])
        self.assertEqual(len(events), 2)
        attribution = events[-1]
        self.assertFalse(attribution["utility"]["causal_claim"])
        self.assertEqual(attribution["outcome"]["requirements"], [{"requirement_uid": uid, "status": "complete"}])
        self.assertEqual(attribution["utility"]["applied_delta"], 2)
        self.assertEqual(utility[learning["learning_id"]]["total_delta"], 2)

    def test_missing_referenced_report_is_repaired_by_a_superseding_attribution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            self.record(root, learning, uid)
            first = RECEIPTS.attribute_completion(root, "run", completion(uid), completion_ref=".tailtrail/runs/run/completion-reports/missing.json")
            repaired = RECEIPTS.attribute_completion(root, "run", completion(uid), completion_ref=".tailtrail/runs/run/completion-reports/report-2.json")
            events = RECEIPTS.read_events(root, "run")

        self.assertFalse(first["receipts"][0]["reused"])
        self.assertFalse(repaired["receipts"][0]["reused"])
        self.assertEqual(len(events), 3)
        self.assertEqual(events[-1]["outcome"]["completion_report_ref"], ".tailtrail/runs/run/completion-reports/report-2.json")

    def test_revised_closure_supersedes_prior_attribution_and_negative_evidence_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            self.record(root, learning, uid)
            RECEIPTS.attribute_completion(root, "run", completion(uid))
            revised = RECEIPTS.attribute_completion(root, "run", completion(uid, drift=True))
            events = RECEIPTS.read_events(root, "run")
            utility = RECEIPTS.utility_adjustments(root)

        self.assertEqual(revised["associations"], {"possible-harm": 1})
        self.assertEqual(len(events), 3)
        self.assertEqual(events[-1]["previous_event_id"], events[-2]["event_id"])
        self.assertEqual(utility[learning["learning_id"]]["total_delta"], -6)
        self.assertEqual(utility[learning["learning_id"]]["attribution_count"], 1)

    def test_association_matrix_is_categorical_and_never_infers_causality(self) -> None:
        uid = "req-1"
        base = {"requirement_uids": [uid], "evidence_refs": ["proposal.json"]}
        cases = [
            ({**base, "decision": "stale"}, completion(uid), "stale"),
            ({**base, "decision": "rejected", "evidence_refs": ["proposal.json", "review.json"]}, completion(uid), "rejected-by-evidence"),
            ({**base, "decision": "ignored"}, completion(uid), "neutral"),
            ({**base, "decision": "advisory"}, completion(uid), "neutral"),
            ({**base, "decision": "applied"}, completion(uid, complete=False), "insufficient"),
            ({**base, "decision": "applied"}, completion(uid, drift=True), "possible-harm"),
            ({**base, "decision": "applied"}, completion(uid), "potentially-helped"),
        ]
        inconclusive = completion(uid)
        inconclusive["requirement_status"]["requirements"][0]["status"] = "incomplete"
        cases.append(({**base, "decision": "applied"}, inconclusive, "inconclusive"))
        for decision, evidence, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(RECEIPTS.association(decision, evidence), expected)

    def test_domain_caps_bound_repeated_observed_associations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            deltas = []
            for index in range(3):
                run_id = f"run-{index}"
                learning, uid, _ = self.setup_run(root, run_id, decision_type="security")
                self.record(root, learning, uid, run_id=run_id, decision_type="security")
                result = RECEIPTS.attribute_completion(root, run_id, completion(uid))
                deltas.append(result["receipts"][0]["utility_delta"])
            utility = RECEIPTS.utility_adjustments(root)

        self.assertEqual(deltas, [2, 2, 1])
        self.assertEqual(utility["lrn-receipt-test"]["total_delta"], 5)

    def test_project_lock_keeps_domain_cap_under_parallel_closures(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index in range(2):
                run_id = f"seed-{index}"
                learning, uid, _ = self.setup_run(root, run_id)
                self.record(root, learning, uid, run_id=run_id, decision_type="security")
                RECEIPTS.attribute_completion(root, run_id, completion(uid))
            pending = []
            for index in range(2):
                run_id = f"parallel-{index}"
                learning, uid, _ = self.setup_run(root, run_id)
                self.record(root, learning, uid, run_id=run_id, decision_type="security")
                pending.append((run_id, uid))
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda item: RECEIPTS.attribute_completion(root, item[0], completion(item[1])), pending))
            deltas = sorted(result["receipts"][0]["utility_delta"] for result in results)
            utility = RECEIPTS.utility_adjustments(root)

        self.assertEqual(deltas, [0, 1])
        self.assertEqual(utility["lrn-receipt-test"]["total_delta"], 5)

    def test_observed_utility_is_consumed_by_retrieval_without_causal_language(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            before = RETRIEVAL.build_proposal(root, task_types=["test"], tags=[], paths=[], requirement_ids=[], mode="standard")["matches"][0]
            self.record(root, learning, uid)
            RECEIPTS.attribute_completion(root, "run", completion(uid))
            after = RETRIEVAL.build_proposal(root, task_types=["test"], tags=[], paths=[], requirement_ids=[], mode="standard")["matches"][0]

        self.assertEqual(after["applicability_score"], before["applicability_score"] + 2)
        self.assertEqual(after["observed_utility_delta"], 2)
        self.assertEqual(after["attribution_count"], 1)
        self.assertNotIn("caused", " ".join(after["match_explanations"]).lower())

    def test_completion_report_joins_receipt_to_harness_and_validation_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            self.record(root, learning, uid, decision_type="validation")
            run = LEDGER.state_dir(root, "run")
            for name in ("checkpoints", "reviews", "completion-gates", "validation-receipts"):
                (run / name).mkdir(parents=True, exist_ok=True)
            (run / "checkpoints" / "checkpoint-1.json").write_text(json.dumps({
                "requirements": [{"requirement_uid": uid, "state": "validated", "evidence": [{"outcome": "pass"}]}],
                "changed_paths": [{"path": "scripts/learning-use-receipt.py"}], "drift": [],
            }), encoding="utf-8")
            (run / "reviews" / "review-1.json").write_text(json.dumps({"complete": True, "findings": []}), encoding="utf-8")
            (run / "completion-gates" / "gate-1.json").write_text(json.dumps({"complete": True, "findings": []}), encoding="utf-8")
            (run / "validation-receipts" / "unit.json").write_text(json.dumps({"tier": "unit", "outcome": "pass"}), encoding="utf-8")
            result = REPORT.build(root, "run")
            rendered = REPORT.render(result)
            saved = json.loads(Path(result["run_artifact"]).read_text(encoding="utf-8"))
            receipt_events = RECEIPTS.read_events(root, "run")

        self.assertEqual(result["learning_use"]["status"], "attributed")
        self.assertEqual(result["learning_use"]["receipts"][0]["requirement_uids"], [uid])
        self.assertIn("## Learning use and closure attribution", rendered)
        self.assertIn("validation: applied", rendered)
        self.assertEqual(saved["learning_use"]["associations"], {"potentially-helped": 1})
        testing_harness = next(item for item in receipt_events[-1]["outcome"]["harnesses"] if item["name"] == "Evidence-Aware Testing")
        self.assertEqual(testing_harness["status"], "pass")
        self.assertEqual(testing_harness["artifact"], ".tailtrail/runs/run/completion-gates/gate-1.json")
        self.assertEqual(receipt_events[-1]["outcome"]["validation_refs"], [".tailtrail/runs/run/validation-receipts/unit.json"])

    def test_digest_tampering_fails_closed_and_cli_route_is_public(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            self.record(root, learning, uid)
            target = RECEIPTS.stream(root, "run")
            event = json.loads(target.read_text(encoding="utf-8"))
            event["rationale"] = "tampered"
            target.write_text(json.dumps(event) + "\n", encoding="utf-8")
            validation = RECEIPTS.validate(root, "run")
            cli = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "tailtrail.py"), "learn", "receipt", "validate", "--root", str(root), "--run-id", "run"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

        self.assertEqual(validation["status"], "failed")
        self.assertEqual(cli.returncode, 1)
        self.assertIn("receipt event digest is invalid", cli.stdout)

    def test_semantically_invalid_utility_fails_even_with_recomputed_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            learning, uid, _ = self.setup_run(root)
            self.record(root, learning, uid, decision_type="security")
            RECEIPTS.attribute_completion(root, "run", completion(uid))
            target = RECEIPTS.stream(root, "run")
            rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
            rows[-1]["utility"]["domain_cap"] = 10
            rows[-1]["chain"]["digest"] = RECEIPTS.event_digest(rows[-1])
            target.write_text("\n".join(RECEIPTS.canonical(row) for row in rows) + "\n", encoding="utf-8")
            result = RECEIPTS.validate(root, "run")

        self.assertEqual(result["status"], "failed")
        self.assertIn("domain cap", " ".join(result["issues"]))

    def test_receipt_schema_is_closed_and_privacy_preserving(self) -> None:
        schema = json.loads((ROOT / "schemas" / "learning-use-receipt-event.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["type"]["const"], "tailtrail-learning-use-receipt-event")
        self.assertFalse(schema["$defs"]["utility"]["properties"]["causal_claim"]["const"])
        self.assertFalse(schema["$defs"]["privacy"]["properties"]["raw_prompt"]["const"])


if __name__ == "__main__":
    unittest.main()
