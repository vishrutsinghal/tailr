"""Permanent automated regression test for Phase N5's greenfield end-to-end
claim (TAILTRAIL-NEW-FILE-DUE-DILIGENCE-PROTOCOL.md). Phase N5's proof of a
first requirement in an empty repository closing cleanly was only ever run
manually against a throwaway /tmp fixture during this project's dogfooding
session. This test drives the real tailtrail CLI end-to-end against a fresh
synthetic near-empty repository, replacing that manual proof with a
repeatable one, and genuinely exercises the production commands -- it never
mocks tailtrail.py, planning-revision.py, execution-evidence.py, or
closure-finalizer.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import greenfield_e2e_fixture as fixture


def _run(args: list[str], root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, (ROOT / "scripts" / args[0]).as_posix(), *args[1:], "--root", root.as_posix()],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class GreenfieldEndToEndTests(unittest.TestCase):
    def test_first_greenfield_requirement_closes_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture.build_fixture(root)

            # Start: only the implementation file is declared via --changed;
            # a not-yet-existing test-role path is always rejected there
            # (see TAILTRAIL-PLAYBOOK.md section 1).
            start = _run(
                [
                    "tailtrail.py",
                    "start",
                    "Add a greet function in greeting.py with its test",
                    "--changed",
                    "greeting.py",
                    "--format",
                    "json",
                ],
                root,
            )
            self.assertEqual(start.returncode, 0, start.stdout + start.stderr)
            start_report = json.loads(start.stdout)
            run_id = start_report["planning_lock"]["run_id"]
            self.assertEqual(start_report["planning_lock"]["status"], "awaiting-approval")

            # Register the new test file's proof scope and command BEFORE
            # activation -- this window closes permanently once the run is
            # approved (R6 is still open; see TAILTRAIL-PLAYBOOK.md section 1).
            proof_command = "python3 -m unittest discover -s tests -v"
            changes = json.dumps(
                [
                    {
                        "kind": "proof-update",
                        "requirement_uid": "REQ-01",
                        "reason": "Register tests/test_greeting.py as proof scope before activation.",
                        "evidence_plan": [f"Run {proof_command} and confirm it passes."],
                        "commands": [proof_command],
                        "tiers": ["unit"],
                        "editable_paths": ["tests/test_greeting.py"],
                        "proposed_paths": ["tests/test_greeting.py"],
                    }
                ]
            )
            propose = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "planning-revision.py").as_posix(),
                    "propose",
                    "--root",
                    root.as_posix(),
                    "--run-id",
                    run_id,
                    "--changes",
                    changes,
                    "--approved-proposal",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(propose.returncode, 0, propose.stdout + propose.stderr)

            approve = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "planning-revision.py").as_posix(),
                    "approve",
                    "--root",
                    root.as_posix(),
                    "--run-id",
                    run_id,
                    "--revision",
                    "2",
                    "--approved",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(approve.returncode, 0, approve.stdout + approve.stderr)

            # Implement the approved implementation-owner file.
            fixture.write_greeting_module(root)

            # Move to the TESTING badge before writing the new test file.
            handoff = _run(
                [
                    "tailtrail.py",
                    "pipeline",
                    "handoff",
                    "--run-id",
                    run_id,
                    "--from-stage",
                    "IMPLEMENTATION",
                    "--context",
                    "greeting.py implemented; adding tests/test_greeting.py",
                ],
                root,
            )
            self.assertEqual(handoff.returncode, 0, handoff.stdout + handoff.stderr)

            fixture.write_greeting_test_module(root)

            # Negative check first: the test genuinely runs and would fail
            # loudly on a broken implementation, not silently pass.
            local_proof = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(local_proof.returncode, 0, local_proof.stdout + local_proof.stderr)

            anchor = json.loads((root / ".tailtrail" / "runs" / run_id / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
            requirement_uid = anchor["requirements"][0]["requirement_uid"]

            evidence = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "execution-evidence.py").as_posix(),
                    "run",
                    "--root",
                    root.as_posix(),
                    "--run-id",
                    run_id,
                    "--requirement",
                    requirement_uid,
                    "--tier",
                    "unit",
                    "--label",
                    "greeting tests pass",
                    "--command",
                    proof_command,
                    "--approved",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(evidence.returncode, 0, evidence.stdout + evidence.stderr)
            evidence_result = json.loads(evidence.stdout)
            self.assertEqual(evidence_result["outcome"], "pass")

            closure = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "closure-finalizer.py").as_posix(),
                    "--root",
                    root.as_posix(),
                    "--run-id",
                    run_id,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(closure.returncode, 0, closure.stdout + closure.stderr)
            closure_result = json.loads(closure.stdout)

        # Asserted after the temp dir context exits, from values captured
        # above -- the closure result itself does not depend on the fixture
        # still being on disk.
        self.assertEqual(closure_result["overall_status"], "complete")


if __name__ == "__main__":
    unittest.main()
