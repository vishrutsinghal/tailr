from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load() -> object:
    spec = importlib.util.spec_from_file_location("host_workspace_adapter_test", ROOT / "scripts" / "host-workspace-adapter.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


adapter = load()


class HostWorkspaceAdapterTests(unittest.TestCase):
    def test_declared_host_workspace_is_verified_locally(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = adapter.resolve("codex", temp, host_platform="windows")
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["host"], "codex")

    def test_wsl_mapping_and_unmapped_container_are_explicit(self) -> None:
        mapped, mapping = adapter.mapped_path("/mnt/d/work/service", "wsl", "windows")
        container = adapter.resolve("claude", "/workspace/service", host_platform="container", local_platform="windows")
        self.assertEqual(mapped.as_posix(), "D:/work/service")
        self.assertEqual(mapping, "wsl-to-windows")
        self.assertEqual(container["status"], "unmapped")

    def test_target_host_workspace_cli_and_start_use_host_workspace_before_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            owner = root / "src" / "service.py"; owner.parent.mkdir(); owner.write_text("def service():\n    return None\n", encoding="utf-8")
            host = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "target", "host-workspace", "--host", "copilot", "--workspace", root.as_posix(), "--format", "json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            goal = "plan a change in /missing/prompt-target"
            interpretation = {
                "schema_version": "1",
                "type": "tailtrail-host-requirement-interpretation",
                "host": "copilot",
                "goal": goal,
                "private_reasoning_excluded": True,
                "clauses": [{"clause_id": "C-01", "role": "outcome", "text": goal}],
                "requirements": [{
                    "display_id": "REQ-01",
                    "statement": goal,
                    "kind": "change",
                    "source_clause_ids": ["C-01"],
                    "intent_terms": ["plan", "change", "prompt-target"],
                    "quoted_literals": [],
                    "intent_class": "general",
                    "confidence": "medium",
                }],
                "material_questions": [],
            }
            started = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), goal, "--host", "copilot", "--host-workspace", root.as_posix(), "--changed", "src/service.py", "--planning-run-id", "host-workspace-run", "--requirement-interpretation", json.dumps(interpretation, separators=(",", ":"))],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            lock = json.loads((root / ".tailtrail" / "runs" / "host-workspace-run" / "planning" / "lock-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(host.returncode, 0, host.stderr)
        self.assertEqual(json.loads(host.stdout)["status"], "verified")
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertIn("Host workspace: `copilot` / `verified`", started.stdout)
        self.assertEqual(lock["host_workspace"]["host"], "copilot")
        self.assertEqual(lock["host_workspace"]["status"], "verified")


if __name__ == "__main__":
    unittest.main()
