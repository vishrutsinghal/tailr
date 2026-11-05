from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


task_start = load("tailtrail_auto_routing_start_test", "scripts/task-start.py")
draft_engine = load("tailtrail_auto_routing_draft_test", "scripts/requirement-interpretation-draft.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compatible_pack(root: Path) -> None:
    pack = root / ".tailtrail" / "official-aidlc"
    pack.mkdir(parents=True)
    (pack / "LICENSE").write_text("MIT-0\n", encoding="utf-8")
    (pack / "core-workflow.md").write_text("# workflow\n", encoding="utf-8")
    official_rules = {
        "aws-aidlc-rules/core-workflow.md": "# Requirements Analysis\n",
        "aws-aidlc-rule-details/inception/requirements-analysis.md": "# Generate Clarifying Questions\n",
        "aws-aidlc-rule-details/common/question-format-guide.md": "# Other\n",
        "aws-aidlc-rule-details/common/content-validation.md": "# Content Validation\n",
        "aws-aidlc-rule-details/common/session-continuity.md": "# Session\n",
    }
    for relative, content in official_rules.items():
        path = pack / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    manifest = {
        "schema_version": "1", "type": "tailtrail-official-aidlc-pack",
        "official": {"source": "https://github.com/awslabs/aidlc-workflows", "revision": "v2.0.0", "license": {"spdx": "MIT-0", "file": "LICENSE"}},
        "host_adapter": {"host": "codex", "rules_path": "core-workflow.md"},
        "integrity": {
            "algorithm": "sha256",
            "files": [
                {"path": "LICENSE", "sha256": digest(pack / "LICENSE")},
                {"path": "core-workflow.md", "sha256": digest(pack / "core-workflow.md")},
            ] + [{"path": relative, "sha256": digest(pack / relative)} for relative in official_rules],
        },
    }
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def envelope(goal: str, host: str = "claude") -> str:
    draft = draft_engine.scaffold_draft(goal, host, [])
    regression = draft_engine.validate_draft(goal, [], draft, host)
    assert regression[1] == [], regression[1]
    return base64.b64encode(json.dumps(regression[0]).encode("utf-8")).decode()


def start_command(root: Path, *args: str) -> list[str]:
    return [sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(),
            "--root", root.as_posix(), *args]


class HandsFreeAutoFullTests(unittest.TestCase):
    def test_hands_free_without_project_pack_uses_bundled_full(self):
        with tempfile.TemporaryDirectory() as temp:
            selected = task_start.aidlc_mode_selection(
                "hands-free: add an API", None, Path(temp),
                {"risk_indicators": [], "requirement_sufficiency": {}},
                None,
            )
        self.assertEqual(selected["mode"], "full")
        self.assertEqual(selected["effective_mode"], "full")
        self.assertEqual(selected["selection"], "hands-free-full")
        self.assertEqual(
            selected["full_escalation"]["state"], "selected")

    def test_hands_free_with_interpretation_proceeds(self):
        goal = "End-to-end hands-free delivery of the notification feature"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            owner = root / "src" / "service.py"
            owner.parent.mkdir(parents=True, exist_ok=True)
            owner.write_text("def service():\n    return None\n", encoding="utf-8")
            compatible_pack(root)
            result = subprocess.run(
                start_command(root, "--host", "codex",
                              "--requirement-interpretation-base64", envelope(goal, "codex"),
                              "--format", "json", goal),
                cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertNotIn("requires official Requirements authority", result.stderr)
        self.assertIn("selecting Full mode automatically", result.stderr)


class DebugAutoRouteTests(unittest.TestCase):
    def test_debug_goal_with_interpretation_routes_not_refuses(self):
        goal = "Debug the failing login flow"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run(
                start_command(root, "--host", "claude",
                              "--requirement-interpretation-base64", envelope(goal),
                              "--format", "json", goal),
                cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertNotIn("only accepted for ordinary", result.stderr)
        self.assertIn("routes to the debug phase", result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("debug_diagnosis_boundary", payload)


if __name__ == "__main__":
    unittest.main()
