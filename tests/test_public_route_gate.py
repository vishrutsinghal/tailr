from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASK_START = [sys.executable, str(ROOT / "scripts" / "task-start.py")]
AUDIT = [sys.executable, str(ROOT / "scripts" / "planning-audit.py")]
REVISE = [sys.executable, str(ROOT / "scripts" / "planning-revision.py")]
TIMEOUT = 300


def _run(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=root, text=True, capture_output=True, check=False, timeout=TIMEOUT)


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

    def test_accepted_contract_routes_and_records(self) -> None:
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
            result = self._start(
                root, "Create the widget in src/work.py and prove it",
                "gate-contract-ok", "--aidlc", "off",
                "--changed", "src/work.py",
                "--host-contract-file", contract_path.as_posix(),
            )
            self.assertIn(result.returncode, (0, 2), result.stderr)
            payload = json.loads(result.stdout)
            recorded = payload.get("host_input_contract", {})
            self.assertEqual(recorded.get("request_mode"), "implementation")
            self.assertEqual(recorded.get("authority_source"), "host-contract")
            navigator = payload.get("navigator", {})
            self.assertNotEqual(navigator.get("navigator_mode"), "evaluation_harness")
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
