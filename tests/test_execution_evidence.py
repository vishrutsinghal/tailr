from __future__ import annotations

import importlib.util
import json
import shlex
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


ledger = load("execution_evidence_v2_ledger_test", "scripts/run-ledger.py")
anchor = load("execution_evidence_v2_anchor_test", "scripts/change-intent-anchor.py")
lock = load("execution_evidence_v2_lock_test", "scripts/planning-lock.py")
evidence = load("execution_evidence_v2_test", "scripts/execution-evidence.py")


class ManagedExecutionEvidenceTests(unittest.TestCase):
    def setup_run(self, root: Path, command: str) -> str:
        (root / "src").mkdir()
        (root / "src" / "service.py").write_text("value = 1\n", encoding="utf-8")
        lock.create(root, "validate service", "run")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{
            "statement": "The service remains valid.",
            "acceptance_criteria": ["focused proof passes"],
            "preserve_rules": [],
            "likely_paths": ["src/service.py"],
            "evidence_plan": ["component and behaviour"],
            "validation_contract": {"state": "required", "tiers": ["component", "behaviour"], "commands": [command]},
            "behavior_contract": {"scenarios": [{
                "scenario_id": "BHV-01", "preconditions": [], "action": "validate",
                "expected_outcome": "validation succeeds", "preservation": [],
                "evidence": [{"tier": "component", "asserted_behavior": "validation succeeds"}, {"tier": "behaviour", "asserted_behavior": "validation succeeds"}],
            }]},
        }]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        uid = anchor.approve(root, "run")["requirements"][0]["requirement_uid"]
        lock.approve(root, "run", True)
        return uid

    def test_executes_exact_approved_command_and_captures_trusted_facts(self) -> None:
        command = f"{shlex.quote(sys.executable)} -c {shlex.quote('print(\"proof ok\")')}"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root, command)
            result = evidence.run_command(root, "run", [uid], ["component", "behaviour"], command, "page proof", ["src/service.py"], True, 30)
            events = evidence.show(root, "run")["events"]
            saved = events[-1]
            stdout = (root / result["stdout_artifact"]).read_text(encoding="utf-8")

        self.assertEqual(result["outcome"], "pass")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(stdout, "proof ok\n")
        self.assertEqual(saved["evidence_quality"], "trusted")
        self.assertEqual(saved["tiers"], ["component", "behaviour"])
        self.assertEqual(saved["scenario_ids"], ["BHV-01"])
        self.assertIn("TailTrail executed", saved["evidence_boundary"])

    def test_failure_exit_and_redacted_output_are_factual(self) -> None:
        source = "import sys; print('token=visible-secret', file=sys.stderr); raise SystemExit(7)"
        command = f"{shlex.quote(sys.executable)} -c {shlex.quote(source)}"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root, command)
            result = evidence.run_command(root, "run", [uid], ["component"], command, "failing proof", ["src/service.py"], True, 30)
            stderr = (root / result["stderr_artifact"]).read_text(encoding="utf-8")

        self.assertEqual(result["outcome"], "fail")
        self.assertEqual(result["exit_code"], 7)
        self.assertIn("token=[REDACTED]", stderr)
        self.assertNotIn("visible-secret", stderr)

    def test_rejects_unapproved_command_and_tier_without_execution(self) -> None:
        command = f"{shlex.quote(sys.executable)} -c {shlex.quote('print(1)')}"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root, command)
            with self.assertRaisesRegex(ValueError, "command is not approved"):
                evidence.run_command(root, "run", [uid], ["component"], "echo wrong", "wrong", [], True)
            with self.assertRaisesRegex(ValueError, "tiers are not approved"):
                evidence.run_command(root, "run", [uid], ["unit"], command, "wrong tier", [], True)

    def test_command_specific_check_authorizes_static_tier_for_legacy_anchor(self) -> None:
        command = f"{shlex.quote(sys.executable)} -c {shlex.quote('print(\"static ok\")')}"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root, command)
            approved_path = ledger.state_dir(root, "run") / "anchors" / "approved-v1.json"
            approved = json.loads(approved_path.read_text(encoding="utf-8"))
            approved["requirements"][0]["validation_contract"]["checks"] = [{
                "kind": "static", "command": command, "tiers": ["static"], "candidate_paths": [],
            }]
            approved_path.write_text(json.dumps(approved), encoding="utf-8")

            result = evidence.run_command(root, "run", [uid], ["static"], command, "static proof", [], True, 30)
            with self.assertRaisesRegex(ValueError, "tiers are not approved"):
                evidence.run_command(root, "run", [uid], ["component"], command, "wrong tier", [], True, 30)

        self.assertEqual("pass", result["outcome"])
        self.assertEqual(["static"], result["tiers"])


if __name__ == "__main__":
    unittest.main()
