from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("completion_report_ledger", "scripts/run-ledger.py")
anchor = load("completion_report_anchor", "scripts/change-intent-anchor.py")
report = load("completion_report_script", "scripts/completion-report.py")


class CompletionReportTests(unittest.TestCase):
    def test_required_checks_preserve_command_specific_tiers(self) -> None:
        checks = report.required_validation_checks({"requirements": [{
            "requirement_uid": "req-1",
            "validation_contract": {
                "state": "required",
                "tiers": ["component", "behaviour"],
                "commands": ["npm run component", "npm run lint"],
                "checks": [
                    {"kind": "proof", "command": "npm run component", "tiers": ["component", "behaviour"], "candidate_paths": ["src/Page.cy.tsx"]},
                    {"kind": "static", "command": "npm run lint", "tiers": ["static"], "candidate_paths": []},
                ],
            },
        }]})

        by_command = {row["command"]: row for row in checks}
        self.assertEqual(["component", "behaviour"], by_command["npm run component"]["tiers"])
        self.assertEqual(["static"], by_command["npm run lint"]["tiers"])
        self.assertEqual(["src/Page.cy.tsx"], by_command["npm run component"]["candidate_paths"])

    def setup_run(self, root: Path) -> str:
        ledger.init_run(root, "run", "claim validation")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{
            "statement": "reject zero claims", "acceptance_criteria": ["zero rejected"],
            "preserve_rules": ["positive claims remain valid"], "likely_paths": ["src/validation.py"],
            "evidence_plan": ["focused + integration"],
        }]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        return anchor.approve(root, "run")["requirements"][0]["requirement_uid"]

    def write_complete_evidence(self, root: Path, uid: str) -> None:
        run = ledger.state_dir(root, "run")
        (run / "checkpoints").mkdir(parents=True)
        (run / "reviews").mkdir()
        (run / "completion-gates").mkdir()
        (run / "validation-receipts").mkdir()
        (run / "closure-records").mkdir()
        (run / "maintainability").mkdir()
        (run / "checkpoints" / "checkpoint-1.json").write_text(json.dumps({
            "checkpoint": 1, "requirements": [{"requirement_uid": uid, "state": "validated", "evidence": [{"outcome": "pass"}]}],
            "changed_paths": [{"path": "src/validation.py", "fingerprint": "sha256:test"}], "drift": [{"requirement_uid": uid, "classification": "resolved"}],
        }), encoding="utf-8")
        (run / "reviews" / "review-1.json").write_text(json.dumps({"complete": True, "findings": []}), encoding="utf-8")
        (run / "completion-gates" / "gate-1.json").write_text(json.dumps({"complete": True, "findings": []}), encoding="utf-8")
        receipt_refs = []
        for tier in ("unit", "integration"):
            path = run / "validation-receipts" / f"{tier}.json"
            path.write_text(json.dumps({"requirement_uids": [uid], "tier": tier, "tiers": [tier], "outcome": "pass", "evidence_quality": "trusted"}), encoding="utf-8")
            receipt_refs.append(path.relative_to(root).as_posix())
        (run / "closure-records" / "closure-current.json").write_text(json.dumps({
            "type": "tailtrail-closure-record", "checkpoint": (run / "checkpoints" / "checkpoint-1.json").as_posix(),
            "receipt_artifacts": receipt_refs,
        }), encoding="utf-8")
        (run / "maintainability" / "assessment-1.json").write_text(json.dumps({"complete": True}), encoding="utf-8")

    def test_single_report_summarizes_complete_local_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            result = report.build(root, "run")
            shown = report.show(root, "run")
        self.assertEqual(result["overall_status"], "complete")
        self.assertTrue(result["canonical_state"]["valid"])
        self.assertEqual(result["requirement_status"]["complete"], 1)
        self.assertEqual(result["requirement_status"]["total"], 1)
        self.assertEqual(result["changed_scope"]["status"], "approved")
        self.assertEqual(result["tests"]["passed_tiers"], ["integration", "unit"])
        harnesses = {item["name"]: item for item in result["harnesses"]}
        self.assertEqual(harnesses["Requirement Completion Harness"]["status"], "pass")
        self.assertTrue(harnesses["Maintainability Harness"]["used"])
        self.assertEqual(harnesses["Maintainability Harness"]["status"], "pass")
        self.assertEqual(shown["overall_status"], "complete")
        rendered = report.render(result)
        self.assertIn("Detail: **comprehensive**", rendered)
        self.assertIn("## What needs attention", rendered)
        self.assertIn("## Requirement status", rendered)
        self.assertIn("## Changed files", rendered)
        self.assertIn("## Validation evidence", rendered)
        self.assertIn("## Audit summary", rendered)
        self.assertIn("## Closure boundary", rendered)
        self.assertIn("- **REQ-01**", rendered)
        self.assertIn("  - **Requirement:** reject zero claims", rendered)
        self.assertIn("  - **Implementation:** **implemented**", rendered)
        self.assertIn("- **Requirement Completion Harness:** pass", rendered)
        self.assertIn("- **Canonical state:**", rendered)
        self.assertIn("- **Actual model tokens:** unavailable", rendered)
        self.assertNotIn("| ---", rendered)

    def test_missing_completion_gate_is_an_evidence_gap_not_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            (ledger.state_dir(root, "run") / "completion-gates" / "gate-1.json").unlink()
            result = report.build(root, "run")
        self.assertEqual(result["tests"]["status"], "not-evidenced")
        self.assertEqual(result["overall_status"], "evidence-incomplete")

    def test_unavailable_execution_is_blocked_not_reported_as_failed_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); uid = self.setup_run(root)
            run = ledger.state_dir(root, "run")
            (run / "validation-receipts").mkdir(parents=True)
            (run / "closure-records").mkdir()
            (run / "completion-gates").mkdir()
            receipt = run / "validation-receipts" / "target-check.json"
            receipt.write_text(json.dumps({
                "requirement_uids": [uid], "tier": "unit", "tiers": ["unit"], "outcome": "unavailable", "evidence_quality": "trusted",
                "command_label": "approved target existence check",
                "asserted_behavior": "The approved target must exist before implementation.",
            }), encoding="utf-8")
            (run / "closure-records" / "closure-current.json").write_text(json.dumps({
                "type": "tailtrail-closure-record", "checkpoint": "checkpoint-0.json",
                "receipt_artifacts": [receipt.relative_to(root).as_posix()],
            }), encoding="utf-8")
            (run / "completion-gates" / "gate-1.json").write_text(json.dumps({"complete": False, "findings": ["target unavailable"]}), encoding="utf-8")
            result = report.build(root, "run"); rendered = report.render(result)

        self.assertEqual(result["tests"]["status"], "unavailable")
        self.assertEqual(result["implementation"]["status"], "not-evidenced")
        self.assertIn("Implementation: **not-evidenced**", rendered)
        self.assertIn("## What needs attention", rendered)
        self.assertEqual(len(result["implementation"]["blockers"]), 1)
        controls = {item["control"]: item for item in result["tailtrail_status"]}
        self.assertEqual(controls["Evidence-Aware Testing"]["status"], "unavailable")
        self.assertEqual(controls["Requirement Completion Harness"]["status"], "incomplete")
        self.assertNotIn("tests fail", rendered)

    def test_no_execution_evidence_is_labelled_not_assessed_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            result = report.build(root, "run")
            rendered = report.render(result)

        self.assertEqual(result["requirement_status"]["requirements"][0]["status"], "not-evidenced")
        self.assertEqual(result["changed_scope"]["status"], "not-assessed")
        self.assertEqual(result["drift"]["status"], "not-assessed")
        self.assertEqual(result["tests"]["status"], "not-evidenced")
        self.assertIn("not assessed", rendered)
        controls = {item["control"]: item for item in result["tailtrail_status"]}
        self.assertEqual(controls["Gap learning"]["status"], "gap-recorded")
        self.assertIn("incomplete-delivery observation only", controls["Gap learning"]["detail"])

    def test_failed_tier_cannot_also_be_reported_as_passing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            run = ledger.state_dir(root, "run")
            (run / "validation-receipts").mkdir(parents=True)
            (run / "closure-records").mkdir()
            (run / "completion-gates").mkdir()
            refs = []
            for name, outcome in (("component", "fail"), ("lint", "pass")):
                path = run / "validation-receipts" / f"{name}.json"
                path.write_text(json.dumps({
                    "requirement_uids": [uid], "tier": "component", "tiers": ["component"],
                    "outcome": outcome, "evidence_quality": "trusted", "command_label": name,
                    "command": name, "asserted_behavior": f"{name} evidence",
                }), encoding="utf-8")
                refs.append(path.relative_to(root).as_posix())
            (run / "closure-records" / "closure-current.json").write_text(json.dumps({
                "type": "tailtrail-closure-record", "checkpoint": "checkpoint-1.json", "receipt_artifacts": refs,
            }), encoding="utf-8")
            (run / "completion-gates" / "gate-1.json").write_text(json.dumps({"complete": False, "findings": []}), encoding="utf-8")
            result = report.build(root, "run")
            rendered = report.render(result)

        self.assertEqual(result["tests"]["tier_results"], {"component": "fail"})
        self.assertEqual(result["tests"]["passed_tiers"], [])
        self.assertIn("Verification: **fail**; passing tiers: **none**", rendered)
        self.assertNotIn("Passed tiers: **component**", rendered)
        self.assertIn("- **component**", rendered)
        self.assertNotIn("- **lint**", rendered)
        self.assertIn("Supporting checks: **1 consolidated observation(s)**", rendered)

    def test_human_report_consolidates_legacy_receipts_and_shows_required_proof_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            run = ledger.state_dir(root, "run")
            approved = run / "anchors" / "approved-v1.json"
            anchor_payload = json.loads(approved.read_text(encoding="utf-8"))
            command = 'npm run component -- --spec "src/Page.cy.tsx"'
            anchor_payload["requirements"][0]["validation_contract"] = {
                "state": "required", "tiers": ["component", "behaviour"],
                "commands": [command], "candidate_paths": ["src/Page.cy.tsx"],
            }
            approved.write_text(json.dumps(anchor_payload), encoding="utf-8")
            (run / "validation-receipts").mkdir(parents=True)
            (run / "closure-records").mkdir()
            (run / "completion-gates").mkdir()
            refs = []
            for index in range(1, 4):
                path = run / "validation-receipts" / f"legacy-{index}.json"
                path.write_text(json.dumps({
                    "requirement_uid": uid, "tier": "component", "outcome": "blocked",
                    "evidence_quality": "declared", "command_label": "Page component proof",
                    "command": command,
                }), encoding="utf-8")
                refs.append(path.relative_to(root).as_posix())
            (run / "closure-records" / "closure-current.json").write_text(json.dumps({
                "type": "tailtrail-closure-record", "checkpoint": "checkpoint-0.json",
                "receipt_artifacts": refs,
            }), encoding="utf-8")
            (run / "completion-gates" / "gate-1.json").write_text(json.dumps({"complete": False, "findings": []}), encoding="utf-8")
            result = report.build(root, "run")
            rendered = report.render(result)

        validation_section = rendered.split("### Harness result", 1)[0]
        self.assertEqual(validation_section.count("- **Page component proof**"), 1)
        self.assertIn("**Consolidated legacy receipts:** 3", validation_section)
        self.assertIn("1 approved validation command(s) still need authoritative passing evidence", rendered)
        self.assertIn("covers REQ-01; tiers: component, behaviour", rendered)
        self.assertIn("Audit archive: **3 receipt file(s)**", rendered)
        self.assertNotIn("legacy-1.json", rendered)

    def test_report_uses_only_run_linked_measured_token_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            planning = ledger.state_dir(root, "run") / "planning"
            planning.mkdir()
            (planning / "start-report-v1.json").write_text(json.dumps({"token_posture": {"used_tokens": 42}}), encoding="utf-8")
            trail = root / ".tailtrail"
            trail.mkdir(exist_ok=True)
            (trail / "token-usage.jsonl").write_text("\n".join([
                json.dumps({"mode": "measured", "task_id": "other", "tailtrail": {"total_tokens": 999}}),
                json.dumps({"mode": "measured", "task_id": "run", "tailtrail": {"total_tokens": 123}}),
            ]) + "\n", encoding="utf-8")
            result = report.build(root, "run")
        self.assertEqual(result["token_usage"]["planning_estimate_tokens"], 42)
        self.assertEqual(result["token_usage"]["status"], "measured")
        self.assertEqual(result["token_usage"]["actual_tailtrail_tokens"], 123)
        rendered = report.render(result)
        self.assertIn("- **Actual model tokens:** 123 from 1 linked record(s)", rendered)

    def test_report_compares_host_usage_with_loose_prompt_and_aidlc_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            planning = ledger.state_dir(root, "run") / "planning"
            planning.mkdir()
            (planning / "start-report-v1.json").write_text(json.dumps({"token_posture": {
                "used_tokens": 100,
                "planned_working_set_tokens": 100,
                "scoped_file_ceiling_tokens": 1000,
                "forecast_confidence": "high",
                "repository_ceiling_tokens": 5000,
                "repository_file_count": 20,
                "estimated_saved_tokens": 900,
                "estimated_reduction_percent": 90.0,
                "saving_techniques": ["Code Graph and file-map reuse", "Navigator scope narrowing"],
                "repository_boundary": "Relevant repository files only.",
            }}), encoding="utf-8")
            trail = root / ".tailtrail"
            trail.mkdir(exist_ok=True)
            common = {"schema_version": "2", "mode": "measured", "task_id": "run", "provider": "openai", "model": "gpt-test"}
            (trail / "token-usage.jsonl").write_text("\n".join([
                json.dumps({**common, "variant": "tailtrail", "usage": {"total_tokens": 100}}),
                json.dumps({**common, "variant": "loose-prompt", "usage": {"total_tokens": 160}}),
                json.dumps({**common, "variant": "aidlc", "usage": {"total_tokens": 250}}),
            ]) + "\n", encoding="utf-8")

            result = report.build(root, "run")
            result["token_usage"]["context_estimate"]["saving_techniques"].append(
                "Project learning reuse"
            )
            result["token_usage"]["context_estimate"]["learning_evidence_references"] = [
                ".tailtrail/runs/run/learning/use-receipts.jsonl#luse-applied"
            ]
            rendered = report.render(result)

        self.assertEqual(100, result["token_usage"]["actual_tailtrail_tokens"])
        self.assertEqual(60, result["token_usage"]["comparisons"]["loose-prompt"]["saved_tokens"])
        self.assertEqual(37.5, result["token_usage"]["comparisons"]["loose-prompt"]["reduction_percent"])
        self.assertEqual(150, result["token_usage"]["comparisons"]["aidlc"]["saved_tokens"])
        self.assertIn("## Token impact", rendered)
        self.assertIn("**Loose-prompt baseline:** 160 exact tokens; TailTrail saved 60 tokens (37.5%).", rendered)
        self.assertIn("**AIDLC baseline:** 250 exact tokens; TailTrail saved 150 tokens (60.0%).", rendered)
        self.assertIn("**Planning forecast:** approximately 100 tokens from a high-confidence working set; full scoped-file ceiling 1000 tokens (90.0% reduction).", rendered)
        self.assertIn("**Repository inventory:** approximately 5000 tokens across 20 relevant file(s); informational only.", rendered)
        self.assertIn("**Major techniques:** Code Graph and file-map reuse, Navigator scope narrowing, Project learning reuse.", rendered)
        self.assertIn(
            "**Project learning evidence:** `.tailtrail/runs/run/learning/use-receipts.jsonl#luse-applied`.",
            rendered,
        )

    def test_report_reads_token_estimate_from_saved_start_report_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            planning = ledger.state_dir(root, "run") / "planning"
            planning.mkdir(exist_ok=True)
            (planning / "start-report-v1.json").write_text(json.dumps({"report": {"token_posture": {"used_tokens": 42}}}), encoding="utf-8")
            result = report.build(root, "run")
        self.assertEqual(result["token_usage"]["planning_estimate_tokens"], 42)

    def test_unresolved_drift_creates_same_run_learning_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            checkpoint = ledger.state_dir(root, "run") / "checkpoints" / "checkpoint-1.json"
            data = json.loads(checkpoint.read_text(encoding="utf-8"))
            data["drift"] = [{"requirement_uid": uid, "classification": "new-drift"}]
            checkpoint.write_text(json.dumps(data), encoding="utf-8")
            result = report.build(root, "run")
            observation = ledger.state_dir(root, "run") / "learning-observations" / "drift-v1.json"
            saved = json.loads(observation.read_text(encoding="utf-8"))
            self.assertEqual(result["drift_learning"]["status"], "recorded")
            self.assertEqual(saved["run_id"], "run")
            self.assertEqual(saved["promotion"], "same-run continuity only; explicit review is required before any cross-run learning promotion")
            self.assertEqual(result["requirement_status"]["requirements"][0]["status"], "implemented-unverified")
            self.assertEqual(result["requirement_status"]["requirements"][0]["drift"][0]["classification"], "new-drift")
            self.assertEqual(result["completion_learning"]["status"], "captured")
            events = (root / ".tailtrail" / "learning-events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(events), 1)
            event = json.loads(events[0])
            self.assertEqual(event["source_run_id"], "run")
            self.assertNotIn("reject zero claims", events[0])
            repeated = report.build(root, "run")
            self.assertEqual(repeated["completion_learning"]["status"], "reused")
            self.assertEqual(len((root / ".tailtrail" / "learning-events.jsonl").read_text(encoding="utf-8").splitlines()), 1)
            rendered = report.render(result)
            self.assertIn("- **REQ-01**", rendered)
            self.assertIn("  - **Delivery:** **implemented-unverified**", rendered)
            self.assertIn("  - **Drift:** new-drift", rendered)


if __name__ == "__main__":
    unittest.main()
