from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LOCK = load("tailtrail_stop_cli_lock_test", "planning-lock.py")
SESSION = load("tailtrail_stop_cli_session_test", "session_control.py")
INTENT = load("tailtrail_stop_intent_test", "expand-intent.py")
MCP = load("tailtrail_stop_mcp_test", "mcp-server.py")
RESOLUTION = load("tailtrail_stop_resolution_test", "orchestration/run_resolution.py")


class TailTrailStopResumeTests(unittest.TestCase):
    def _cli(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tailtrail.py"), *args, "--root", str(root)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )

    def test_cli_stop_returns_zero_and_does_not_fall_through_to_start(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); LOCK.create(root, "keep the plan", "cli-stop-run"); SESSION.attach(root, "cli-stop-run")
            result = self._cli(root, "stop")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("# TailTrail Stopped"))
        self.assertIn("Run ID: `cli-stop-run`", result.stdout)
        self.assertNotIn("Scope Confirmation Required", result.stdout)

    def test_cli_stop_with_no_run_is_a_zero_exit_noop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self._cli(Path(temp), "stop")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Run ID: `none`", result.stdout)

    def test_cli_exact_resume_attaches_but_does_not_approve(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); LOCK.create(root, "keep the plan", "cli-resume-run"); SESSION.attach(root, "cli-resume-run"); SESSION.stop(root)
            result = self._cli(root, "resume", "--run-id", "cli-resume-run")
            lock = LOCK.show(root, "cli-resume-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Outcome: `resumed-awaiting-approval`", result.stdout)
        self.assertEqual(lock["status"], "awaiting-approval")

    def test_detached_intent_routes_ordinary_work_away_from_tailtrail(self) -> None:
        stopped = INTENT.resolve_request("stop TailTrail", active_state="awaiting-approval")
        ordinary = INTENT.resolve_request("fix the parser and run tests", active_state="detached")
        resumed = INTENT.resolve_request("tailtrail resume --run-id start-123", active_state="detached")
        self.assertEqual(stopped["action"], "stop")
        self.assertEqual(ordinary["action"], "ordinary-agent")
        self.assertIsNone(ordinary["operation"]["name"])
        self.assertEqual(resumed["action"], "resume")
        self.assertEqual(resumed["operation"]["arguments"], {"run_id": "start-123"})

    def test_detached_resolution_cannot_rediscover_saved_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); LOCK.create(root, "keep the plan", "detached-run"); SESSION.attach(root, "detached-run"); SESSION.stop(root)
            with self.assertRaisesRegex(ValueError, "routing is detached"):
                RESOLUTION.resolve_run(root, None, LOCK.show, states={"awaiting-approval"})

    def test_mcp_stop_requires_confirmation_and_matches_cli_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); LOCK.create(root, "keep the plan", "mcp-stop-run"); SESSION.attach(root, "mcp-stop-run")
            with self.assertRaisesRegex(ValueError, "confirmed: true"):
                MCP.call_tool("tailtrail_stop", {"root": str(root)})
            stopped = MCP.call_tool("tailtrail_stop", {"root": str(root), "confirmed": True})
            status = MCP.call_tool("tailtrail_session_status", {"root": str(root)})
            resumed = MCP.call_tool("tailtrail_resume", {"root": str(root), "run_id": "mcp-stop-run"})
        self.assertEqual(stopped["result"]["state"], "detached")
        self.assertEqual(status["result"]["state"], "detached")
        self.assertEqual(resumed["result"]["state"], "resumed-awaiting-approval")
        self.assertFalse(resumed["execution"]["execution_advanced"])


if __name__ == "__main__":
    unittest.main()
