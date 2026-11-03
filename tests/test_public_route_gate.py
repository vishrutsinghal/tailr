from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import host_contract
from scripts.intake_pipeline import IntakePipeline


ROOT = Path(__file__).resolve().parents[1]
TASK_START = [sys.executable, str(ROOT / "scripts" / "task-start.py")]
AUDIT = [sys.executable, str(ROOT / "scripts" / "planning-audit.py")]
REVISE = [sys.executable, str(ROOT / "scripts" / "planning-revision.py")]
TIMEOUT = 300


def _run(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=root, text=True, capture_output=True, check=False, timeout=TIMEOUT)


def _planning_readiness_receipt(
    root: Path, goal: str, *, host_contract_fingerprint: str | None = None,
) -> dict:
    pipeline = IntakePipeline(root)
    run = pipeline.create_run(goal, "existing-code-change")
    values = {
        "expected-behavior": "The widget returns the revised result.",
        "existing-owner": "src/work.py",
        "proof-command": "python3 -m unittest tests.test_work",
    }
    answers = {}
    for field_id, value in values.items():
        question = pipeline.issue_question(run["run_id"], field_id, f"Provide {field_id}")
        answer = pipeline.record_answer(
            run["run_id"], field_id, value, source="direct-question",
            question_id=question["payload"]["question_id"],
        )
        answer_id = answer["payload"]["answer_id"]
        pipeline.accept_answer(
            run["run_id"], answer_id,
            {"outcome": "accepted", "verified_by": "navigator"},
        )
        answers[field_id] = answer_id
    snapshot = pipeline.replay(run["run_id"])
    states = {row["answer_id"]: row for row in snapshot["answer_states"]}
    target_identity = {"root": root.as_posix()}
    if host_contract_fingerprint:
        target_identity["host_contract_fingerprint"] = host_contract_fingerprint
    return pipeline.mint_planning_readiness(
        run["run_id"], accepted_answer_ids=list(answers.values()),
        requirement_projections=[{
            "requirement_uid": "req-ready", "consumer_component_id": "planning-lock",
            "projection_kind": "requirement",
        }],
        operational_bindings={"requirements": [{
            "requirement_uid": "req-ready", "statement": "Create the widget.",
            "source_answer_ids": list(answers.values()), "profile_fields": list(values),
            "semantic_delta": "validated", "dependencies_checked": True,
            "path_bindings": [{
                "path": "src/work.py", "role": "implementation-owner", "existing": True,
                "new_file_verdict": "not-applicable", "source_answer_ids": [answers["existing-owner"]],
            }],
            "proof_bindings": [{
                "path": "tests/test_work.py", "command": values["proof-command"], "tier": "unit",
                "asserted_behavior": "The widget behavior is proven.",
                "source_answer_id": answers["proof-command"],
                "source_answer_ids": [answers["proof-command"]],
                "evidence_fingerprint": states[answers["proof-command"]]["source_evidence_fingerprint"],
            }],
            "criteria": {
                "positive": ["The widget works."], "negative": ["Nothing else changes."],
                "source_answer_ids": [answers["expected-behavior"]],
            },
            "correction_premise": {
                "status": "not-applicable", "source_answer_ids": [answers["expected-behavior"]],
            },
        }]},
        expected_packet_view_fingerprint=snapshot["packet_view_fingerprint"],
        target_identity=target_identity,
    )


class PublicRouteGateTests(unittest.TestCase):
    def _repo(self, files: dict[str, str]) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for relative, body in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return temporary, root

    def _start(self, root: Path, goal: str, run_id: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return _run([*TASK_START, goal, "--root", root.as_posix(),
                     "--format", "json", "--planning-run-id", run_id, *extra], root)

    def test_declared_implementation_skips_eval_harness(self) -> None:
        temporary, root = self._repo({
            "src/work.py": "def run():\n    return 1\n",
            "tests/test_work.py": "def test_run():\n    assert True\n",
        })
        try:
            result = self._start(
                root, "Create the Phase 2A widget protocol and prove it with evidence",
                "gate-eval-impl", "--aidlc", "off", "--task-type", "implementation",
                "--changed", "src/work.py",
            )
            self.assertIn(result.returncode, (0, 2), result.stderr)
            payload = json.loads(result.stdout)
            navigator = payload.get("navigator", {})
            self.assertNotEqual(navigator.get("navigator_mode"), "evaluation_harness")
        finally:
            temporary.cleanup()

    def test_contradicted_contract_creates_no_run(self) -> None:
        temporary, root = self._repo({"src/work.py": "x = 1\n"})
        try:
            contract = {
                "schema_version": "1", "type": "tailtrail-host-input-contract",
                "run_id": "", "contract_id": "ctr-gate", "profile": "review/read-only",
                "change_intent": "validation", "request_mode": "read-only",
                "behavior_surface": "cli-contract",
                "paths": [{"path": "src/work.py", "role": "existing-implementation-owner"}],
                "criteria": {"positive": ["report ships"], "negative": ["nothing else breaks"]},
                "proof": {"command": "pytest", "tiers": ["unit"]},
                "private_reasoning_excluded": True,
            }
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            result = self._start(
                root, "Create the widget and prove it", "gate-contract-no",
                "--aidlc", "off", "--task-type", "implementation",
                "--host-contract-file", contract_path.as_posix(),
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            runs = root / ".tailtrail" / "runs"
            self.assertFalse(runs.is_dir() and any(runs.iterdir()))
        finally:
            temporary.cleanup()

    def test_contradicted_contract_renders_a_markdown_boundary_without_navigator(self) -> None:
        temporary, root = self._repo({"src/work.py": "x = 1\n"})
        try:
            contract = {
                "schema_version": "1", "type": "tailtrail-host-input-contract",
                "run_id": "", "contract_id": "ctr-gate-markdown", "profile": "review/read-only",
                "change_intent": "validation", "request_mode": "read-only",
                "behavior_surface": "cli-contract",
                "paths": [{"path": "src/work.py", "role": "existing-implementation-owner"}],
                "criteria": {"positive": ["report ships"], "negative": ["nothing else breaks"]},
                "proof": {"command": "pytest", "tiers": ["unit"]},
                "private_reasoning_excluded": True,
            }
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            result = _run([
                *TASK_START, "Create the widget and prove it", "--root", root.as_posix(),
                "--format", "markdown", "--planning-run-id", "gate-contract-markdown",
                "--aidlc", "off", "--task-type", "implementation",
                "--host-contract-file", contract_path.as_posix(),
            ], root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("# TailTrail Host Input Contract Required", result.stdout)
            self.assertIn("Planning Lock: not created", result.stdout)
            self.assertNotIn("internal error", result.stderr)
            runs = root / ".tailtrail" / "runs"
            self.assertFalse(runs.is_dir() and any(runs.iterdir()))
        finally:
            temporary.cleanup()

    def test_implementation_contract_requires_and_accepts_matching_planning_readiness(self) -> None:
        temporary, root = self._repo({
            "src/work.py": "def run():\n    return 1\n",
            "tests/test_work.py": "def test_run():\n    assert True\n",
        })
        try:
            contract = {
                "schema_version": "1", "type": "tailtrail-host-input-contract",
                "run_id": "", "contract_id": "ctr-gate-ok", "profile": "new feature",
                "change_intent": "new-capability", "request_mode": "implementation",
                "behavior_surface": "cli-contract",
                "paths": [
                    {"path": "src/work.py", "role": "existing-implementation-owner"},
                    {"path": "tests/test_work.py", "role": "existing-proof-path"},
                ],
                "criteria": {"positive": ["work ships"], "negative": ["nothing else breaks"]},
                "proof": {"command": "pytest tests/test_work.py", "tiers": ["unit"]},
                "private_reasoning_excluded": True,
            }
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            goal = "Create the widget in src/work.py and prove it"
            result = self._start(
                root, goal, "gate-contract-raw", "--aidlc", "off",
                "--changed", "src/work.py",
                "--host-contract-file", contract_path.as_posix(),
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            raw_boundary = json.loads(result.stdout)
            self.assertEqual(raw_boundary.get("status"), "planning-readiness-required")
            self.assertFalse((root / ".tailtrail" / "runs" / "gate-contract-raw").exists())

            validated_contract = host_contract.validate(contract, root=root, goal=goal)["validated"]
            receipt = _planning_readiness_receipt(
                root, goal, host_contract_fingerprint=validated_contract["fingerprint"],
            )
            receipt_path = root / "readiness.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            result = self._start(
                root, goal, "gate-contract-ok", "--aidlc", "off",
                "--changed", "src/work.py",
                "--host-contract-file", contract_path.as_posix(),
                "--planning-readiness-receipt-file", receipt_path.as_posix(),
            )
            self.assertIn(result.returncode, (0, 2), result.stderr)
            payload = json.loads(result.stdout)
            recorded = payload.get("host_input_contract", {})
            self.assertEqual(recorded.get("request_mode"), "implementation", payload)
            self.assertEqual(recorded.get("authority_source"), "host-contract")
            self.assertEqual(
                payload.get("planning_readiness", {}).get("receipt_id"), receipt["receipt_id"]
            )
            navigator = payload.get("navigator", {})
            self.assertNotEqual(navigator.get("navigator_mode"), "evaluation_harness")
            row = navigator.get("requirement_matrix", [])[0]
            self.assertEqual(row.get("requirement_uid"), "req-ready")
            self.assertIn("The widget works.", row.get("acceptance_criteria", []))
            self.assertIn("Nothing else changes.", row.get("preserve_rules", []))
            self.assertEqual(
                row.get("validation_contract", {}).get("commands"),
                ["python3 -m unittest tests.test_work"],
            )
            self.assertEqual(
                row.get("scope_evidence", {}).get("proof_paths"), ["tests/test_work.py"]
            )
            self.assertEqual(
                payload.get("planning_readiness", {}).get("reconciliation", {}).get("phase"),
                "start-persistence",
            )
        finally:
            temporary.cleanup()

    def test_validation_only_contract_routes_before_owner_scope_selection(self) -> None:
        """A non-write contract must not be blocked for lacking a source owner."""
        temporary, root = self._repo({
            "src/work.py": "def run():\n    return 1\n",
            "tests/test_work.py": "import unittest\n\nclass T(unittest.TestCase):\n    def test_run(self):\n        self.assertTrue(True)\n",
        })
        try:
            contract = {
                "schema_version": "1", "type": "tailtrail-host-input-contract",
                "run_id": "", "contract_id": "ctr-validation-only", "profile": "QA/validation-only",
                "change_intent": "validation", "request_mode": "validation-only",
                "behavior_surface": "cli-contract",
                "paths": [
                    {"path": "src/work.py", "role": "inspection-input"},
                    {"path": "tests/test_work.py", "role": "existing-proof-path"},
                ],
                "criteria": {"positive": ["the route is represented"], "negative": ["source is not editable"]},
                "proof": {"command": "python3 -m unittest tests.test_work", "tiers": ["unit"]},
                "private_reasoning_excluded": True,
            }
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            result = self._start(
                root,
                "Validate the Start Plan route without editing source.",
                "gate-contract-validation-only",
                "--aidlc", "off", "--host-contract-file", contract_path.as_posix(),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            navigator = payload.get("navigator", {})
            quality = navigator.get("scope_quality", {})
            self.assertEqual("passed", quality.get("status"))
            self.assertEqual("validation-only", quality.get("mode"))
            self.assertEqual([], navigator.get("scope_evidence", {}).get("implementation_owners", []))
            self.assertEqual(["tests/test_work.py"], quality.get("proof_paths"))
            self.assertEqual(
                "validation-only",
                navigator.get("host_scope_routing", {}).get("request_mode"),
            )
            audit = _run([
                *AUDIT, "--root", root.as_posix(), "--run-id", "gate-contract-validation-only",
            ], root)
            self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
            self.assertEqual("clean", json.loads(audit.stdout).get("status"))
            revised = _run([
                *REVISE, "propose", "--root", root.as_posix(),
                "--run-id", "gate-contract-validation-only", "--approved-proposal",
                "--changes", json.dumps([{
                    "kind": "proof-update", "requirement_uid": "REQ-01",
                    "reason": "Retain the accepted validation-only proof binding.",
                    "evidence_plan": ["Run the accepted validation-only unit proof."],
                    "commands": ["python3 -m unittest tests.test_work"], "tiers": ["unit"],
                }]),
            ], root)
            self.assertEqual(revised.returncode, 0, revised.stdout + revised.stderr)
            revision_artifact = root / ".tailtrail" / "runs" / "gate-contract-validation-only" / "planning" / "revisions" / "revision-v2.json"
            revision_payload = json.loads(revision_artifact.read_text(encoding="utf-8"))
            revised_navigator = revision_payload["proposed_report"]["navigator"]
            self.assertEqual("validation-only", revised_navigator["scope_quality"]["mode"])
            self.assertFalse(revised_navigator["scope_quality"]["blocking"])
            self.assertEqual([], revised_navigator["requirement_matrix"][0]["scope_evidence"]["implementation_owners"])
            markdown = _run([
                *TASK_START,
                "Validate the Start Plan route without editing source.",
                "--root", root.as_posix(), "--format", "markdown",
                "--planning-run-id", "gate-contract-validation-only-markdown",
                "--aidlc", "off", "--host-contract-file", contract_path.as_posix(),
            ], root)
            self.assertEqual(markdown.returncode, 0, markdown.stdout + markdown.stderr)
            self.assertIn("no implementation authority", markdown.stdout)
            self.assertIn("Not applicable: this is a `validation-only` plan", markdown.stdout)
        finally:
            temporary.cleanup()

    def test_stale_planning_readiness_fails_before_planning_lock_with_actionable_guidance(self) -> None:
        temporary, root = self._repo({
            "src/work.py": "def run():\n    return 1\n",
            "tests/test_work.py": "# proof\n",
        })
        try:
            goal = "Create the widget in src/work.py and prove it"
            receipt = _planning_readiness_receipt(root, goal)
            receipt_path = root / "readiness.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            (root / "src" / "work.py").write_text("def run():\n    return 2\n", encoding="utf-8")
            result = self._start(
                root, goal, "gate-readiness-stale", "--aidlc", "off",
                "--planning-readiness-receipt-file", receipt_path.as_posix(),
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload.get("status"), "planning-readiness-required")
            self.assertIn("target changed", payload.get("reason", ""))
            self.assertIn("mint a planning-readiness receipt", payload.get("next_action", ""))
            self.assertFalse((root / ".tailtrail" / "runs" / "gate-readiness-stale").exists())
        finally:
            temporary.cleanup()

    def test_read_only_contract_uses_inspection_route_without_owner_scope(self) -> None:
        temporary, root = self._repo({"src/work.py": "def run():\n    return 1\n"})
        try:
            contract = {
                "schema_version": "1", "type": "tailtrail-host-input-contract",
                "run_id": "", "contract_id": "ctr-read-only", "profile": "review/read-only",
                "change_intent": "validation", "request_mode": "read-only",
                "behavior_surface": "cli-contract",
                "paths": [{"path": "src/work.py", "role": "inspection-input"}],
                "criteria": {"positive": ["the route is inspected"], "negative": ["source is not editable"]},
                "proof": {"command": "python3 -m unittest", "tiers": ["unit"]},
                "private_reasoning_excluded": True,
            }
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            result = self._start(
                root,
                "Inspect the Start Plan route without editing source.",
                "gate-contract-read-only",
                "--aidlc", "off", "--host-contract-file", contract_path.as_posix(),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            navigator = payload.get("navigator", {})
            quality = navigator.get("scope_quality", {})
            self.assertEqual("passed", quality.get("status"))
            self.assertEqual("read-only", quality.get("mode"))
            self.assertEqual(["src/work.py"], quality.get("inspection_paths"))
            self.assertEqual([], navigator.get("scope_evidence", {}).get("implementation_owners", []))
        finally:
            temporary.cleanup()

    def test_audit_correction_applies_through_real_clis(self) -> None:
        temporary, root = self._repo({
            "src/service.py": "def cancel():\n    return True\n",
            "tests/test_service.py": "import unittest\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        pass\n",
        })
        try:
            result = self._start(
                root, "Cancel an eligible order in src/service.py covered by tests/test_service.py",
                "gate-audit-loop", "--aidlc", "off",
                "--changed", "src/service.py", "--changed", "tests/test_service.py",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            run_id = (payload.get("planning_lock", {}) or {}).get("run_id")
            self.assertEqual(run_id, "gate-audit-loop")
            audited = _run([*AUDIT, "--root", root.as_posix(), "--run-id", run_id], root)
            self.assertEqual(audited.returncode, 2, audited.stderr)
            findings = json.loads(audited.stdout).get("findings", [])
            template = next(
                f for f in findings
                if f.get("correction_kind") == "template" and f.get("type") == "unresolved-tier-proof"
            )
            # Fill the template's open field with a real command through the
            # real revise CLI, including the required authority marker.
            changes = [{
                "kind": "proof-update",
                "requirement_uid": template["requirement_uid"],
                "reason": "attach proof for %s" % template["tier"],
                "evidence_plan": ["Run the %s proof" % template["tier"]],
                "commands": ["pytest tests/test_service.py"],
                "tiers": [template["tier"]],
            }]
            revised = _run(
                [sys.executable, str(ROOT / "scripts" / "planning-revision.py"),
                 "propose", "--root", root.as_posix(), "--run-id", run_id,
                 "--changes", json.dumps(changes), "--approved-proposal"],
                root,
            )
            self.assertEqual(revised.returncode, 0, revised.stdout + revised.stderr)
            reaudit = _run([*AUDIT, "--root", root.as_posix(), "--run-id", run_id], root)
            remaining = json.loads(reaudit.stdout).get("findings", [])
            self.assertFalse(any(
                f.get("type") == "unresolved-tier-proof" and f.get("tier") == template["tier"]
                for f in remaining
            ), remaining)
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
