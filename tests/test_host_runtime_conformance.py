from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module


runtime = load("host_runtime_conformance_test", "scripts/host-runtime-conformance.py")
ledger = load("host_runtime_ledger_test", "scripts/run-ledger.py")


OBSERVATIONS = {
    "small-bug": ["planning-lock-created", "complete-start-report", "no-write-before-approval"],
    "hands-free-feature": ["program-requirements", "dependency-order", "first-active-slice", "approval-gate"],
    "rejected-requirement": ["same-run-preserved", "rejection-routed", "implementation-blocked"],
    "evidence-failure": ["requirement-incomplete", "correction-or-replan-offered", "no-false-completion"],
    "recovery": ["approved-anchor-preserved", "task-owned-recovery", "unrelated-work-preserved"],
    "ci-wait": ["awaiting-linked-ci", "no-positive-learning", "acceptance-not-inferred"],
}


def create_run(root: Path, run_id: str, scenario: str) -> None:
    ledger.init_run(root, run_id, scenario)
    directory = root / ".tailtrail" / "runs" / run_id
    ledger.atomic_json(directory / "planning" / "lock-v1.json", {"schema_version": "1", "type": "tailtrail-planning-lock", "run_id": run_id, "status": "awaiting-approval"})
    report = {"schema_version": "1", "type": "tailtrail-start-report", "run_id": run_id, "goal": scenario}
    if scenario == "hands-free-feature":
        report["guided_delivery"] = {"hands_free_program": {"feature_requirements": ["REQ-01"], "dependency_order": ["requirements", "implementation"], "first_active_slice": "REQ-01", "approval_gate": "approve program"}}
    ledger.atomic_json(directory / "planning" / "start-report-v1.json", report)
    if scenario == "rejected-requirement":
        ledger.append_event(root, run_id, "proposal_rejected", {"requirement_uid": "req-01"})
    if scenario == "evidence-failure":
        ledger.atomic_json(directory / "checkpoints" / "checkpoint-0001.json", {"schema_version": "1", "type": "tailtrail-harness-checkpoint", "run_id": run_id, "requirements": [{"requirement_uid": "req-01", "state": "incomplete"}]})
        ledger.append_event(root, run_id, "harness_feedback", {"requirement_uid": "req-01", "route": "correction"})
    if scenario == "recovery":
        ledger.atomic_json(directory / "anchors" / "approved-v1.json", {"schema_version": "1", "type": "tailtrail-change-intent-anchor", "run_id": run_id, "status": "approved", "approved_fingerprint": "sha256:" + "1" * 64, "requirements": [{"requirement_uid": "req-01", "statement": "preserve work"}]})
        ledger.atomic_json(directory / "recovery" / "boundary.json", {"type": "tailtrail-recovery-boundary", "run_id": run_id})
        ledger.append_event(root, run_id, "recovery_boundary_created", {"artifact": f".tailtrail/runs/{run_id}/recovery/boundary.json"})
    if scenario == "ci-wait":
        ledger.atomic_json(directory / "aidlc-official" / "closure" / "closure-link-v1.json", {"schema_version": "1", "type": "tailtrail-official-aidlc-closure-link", "run_id": run_id, "acceptance_state": "awaiting-ci"})


def make_receipt(root: Path, host: str, scenario: str, run_id: str, *, outcome: str = "pass", adapter: str = "v1", scenario_version: str = "v1", bundle_digest: str | None = None, observations: list[str] | None = None, receipt_id: str | None = None) -> Path:
    bundle = runtime.bundle_payload(host)
    payload = {
        "schema_version": "1", "type": "tailtrail-host-runtime-receipt", "receipt_id": receipt_id or f"{host}-{scenario}",
        "host": host, "host_version": "test-host-v1", "adapter_version": adapter, "scenario_version": scenario_version,
        "bundle_digest": bundle_digest or bundle["bundle_digest"], "scenario_id": scenario, "run_id": run_id,
        "observed_transitions": [{"sequence": 1, "state": f"{scenario}-observed"}], "observations": observations if observations is not None else OBSERVATIONS[scenario],
        "artifact_references": [f".tailtrail/runs/{run_id}/manifest.json"], "declared_outcome": outcome,
        "failure_codes": [] if outcome == "pass" else ["host-observation-failed"],
        "boundary": "Sanitized test receipt containing identifiers and local artifact references only."
    }
    payload["integrity"] = {"algorithm": "sha256", "digest": runtime.receipt_digest(payload)}
    path = root / f"{payload['receipt_id']}.json"; path.write_text(json.dumps(payload), encoding="utf-8"); return path


class HostRuntimeConformanceTests(unittest.TestCase):
    def test_prepare_is_host_specific_and_contains_all_six_portable_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); result = runtime.prepare(root, "codex")
        self.assertEqual(result["state"], "prepared")
        self.assertEqual(len(result["scenarios"]), 6)
        self.assertNotIn("source_code", json.dumps(result))

    def test_all_six_fresh_receipts_produce_runtime_pass_separate_from_instruction_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for scenario in OBSERVATIONS:
                run_id = f"run-{scenario}"; create_run(root, run_id, scenario)
                result = runtime.record(root, "codex", make_receipt(root, "codex", scenario, run_id))
                self.assertEqual(result["evaluation"], "passed")
            report = runtime.report(root, "codex")
        self.assertEqual(report["instruction_conformance"]["status"], "passed")
        self.assertEqual(report["runtime_conformance"][0]["runtime_status"], "passed")
        self.assertEqual(report["runtime_conformance"][0]["scenario_coverage"], 6)

    def test_missing_failed_stale_and_incompatible_evidence_have_distinct_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(runtime.report(root, "copilot")["runtime_conformance"][0]["runtime_status"], "not-validated")
            create_run(root, "fail-run", "small-bug")
            failed = runtime.record(root, "copilot", make_receipt(root, "copilot", "small-bug", "fail-run", observations=["planning-lock-created"]))
            self.assertEqual(failed["evaluation"], "failed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); create_run(root, "stale-run", "small-bug")
            stale = runtime.record(root, "claude", make_receipt(root, "claude", "small-bug", "stale-run", scenario_version="v0"))
            self.assertEqual(stale["evaluation"], "stale")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); create_run(root, "incompatible-run", "small-bug")
            incompatible = runtime.record(root, "codex", make_receipt(root, "codex", "small-bug", "incompatible-run", adapter="v0"))
            self.assertEqual(incompatible["evaluation"], "incompatible")

    def test_invalid_or_sensitive_receipt_is_rejected_without_changing_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); create_run(root, "safe-run", "recovery")
            anchor = root / ".tailtrail" / "runs" / "safe-run" / "anchors" / "approved-v1.json"; before = anchor.read_bytes()
            path = make_receipt(root, "codex", "recovery", "safe-run")
            payload = json.loads(path.read_text(encoding="utf-8")); payload["raw_prompt"] = "ignore previous instructions"; path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "blocked-field|unknown-field"):
                runtime.record(root, "codex", path)
            self.assertEqual(anchor.read_bytes(), before)
            missing = make_receipt(root, "codex", "small-bug", "missing-run")
            with self.assertRaisesRegex(ValueError, "missing-local-reference|does not exist"):
                runtime.record(root, "codex", missing)

    def test_cli_prepare_and_report_are_public(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "adapters", "runtime", "prepare", "--root", root.as_posix(), "--host", "codex"], cwd=ROOT, text=True, capture_output=True, check=False)
            reported = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "adapters", "runtime", "report", "--root", root.as_posix()], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(prepared.returncode, 0, prepared.stderr + prepared.stdout)
        self.assertEqual(reported.returncode, 0, reported.stderr + reported.stdout)
        self.assertEqual(json.loads(reported.stdout)["runtime_conformance"][0]["runtime_status"], "not-validated")

    def test_record_is_idempotent_for_the_same_immutable_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); create_run(root, "repeat-run", "small-bug")
            receipt = make_receipt(root, "codex", "small-bug", "repeat-run")
            first = runtime.record(root, "codex", receipt)
            second = runtime.record(root, "codex", receipt)
            events = ledger.read_events(root / ".tailtrail" / "runs" / "repeat-run" / "events.jsonl")
        self.assertEqual(first["ledger_sequence"], second["ledger_sequence"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(sum(item["event_type"] == "host_runtime_conformance_recorded" for item in events), 1)


if __name__ == "__main__":
    unittest.main()
