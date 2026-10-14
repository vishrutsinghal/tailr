"""Write-guardian enforcement: deny-by-default, explicit guard, proposal gate.

Run: python -m unittest tests.test_write_guardian -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import planning_lock as pl  # noqa: E402
from write_guardian import (  # noqa: E402
    SecurityBoundaryError,
    WriteGuardian,
    anchor_aware_write_check,
    guard_write,
    run_hook,
    validate_planned_paths,
)


class WriteGuardianTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("print('hello')", encoding="utf-8")
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_app.py").write_text("def test_pass(): pass", encoding="utf-8")
        self.run_id = "write-guardian-test-1"
        pl.L.init_run(self.root, self.run_id, "Test goal")
        self._set_stage("IMPLEMENTATION")
        os.environ.pop("TAILTRAIL_ACTIVE_RUN_ID", None)

    def tearDown(self) -> None:
        os.environ.pop("TAILTRAIL_ACTIVE_RUN_ID", None)
        self.tmp.cleanup()

    def _set_stage(self, stage: str) -> None:
        path = Path(pl.lock_path(self.root, self.run_id))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema_version": "2",
            "type": "tailtrail-planning-lock",
            "run_id": self.run_id,
            "status": "approved",
            "pipeline": {
                "active_stage": stage,
                "completed_stages": [],
                "stage_sequence": ["IMPLEMENTATION", "TESTING", "INFRA"],
                "handoff_manifest": None,
            },
        }), encoding="utf-8")

    def test_no_run_without_flag_denies(self) -> None:
        guardian = WriteGuardian(self.root)
        with self.assertRaisesRegex(SecurityBoundaryError, "no active pipeline run"):
            guardian.validate_write(self.root / "src" / "app.py")

    def test_declared_permissive_passes(self) -> None:
        guardian = WriteGuardian(self.root, permissive=True)
        guardian.validate_write(self.root / "src" / "app.py")

    def test_enforcing_run_blocks_out_of_badge(self) -> None:
        self._set_stage("TESTING")
        guardian = WriteGuardian(self.root, self.run_id)
        with self.assertRaises(SecurityBoundaryError):
            guardian.validate_write(self.root / "src" / "app.py")
        guardian.validate_write(self.root / "tests" / "test_app.py")

    def test_guard_write_is_explicit(self) -> None:
        self._set_stage("TESTING")
        with self.assertRaises(SecurityBoundaryError):
            guard_write(self.root, self.root / "src" / "app.py", run_id=self.run_id)
        guard_write(self.root, self.root / "src" / "app.py", permissive=True)

    def test_validate_planned_paths_rows(self) -> None:
        rows = validate_planned_paths(self.root, self.run_id, ["src/app.py", "tests/test_app.py"])
        by_path = {row["path"]: row for row in rows}
        self.assertTrue(by_path["src/app.py"]["allowed"])
        self.assertFalse(by_path["tests/test_app.py"]["allowed"])
        self.assertTrue(by_path["tests/test_app.py"]["reason"])

    def _write_anchor(self, requirements: list[dict]) -> None:
        anchors = self.root / ".tailtrail" / "runs" / self.run_id / "anchors"
        anchors.mkdir(parents=True, exist_ok=True)
        (anchors / "approved-v1.json").write_text(json.dumps({
            "schema_version": "1",
            "type": "tailtrail-change-intent-anchor",
            "run_id": self.run_id,
            "status": "approved",
            "requirements": requirements,
        }), encoding="utf-8")

    def test_sole_config_owner_allowed_in_implementation(self) -> None:
        (self.root / "registry.json").write_text("{}", encoding="utf-8")
        self._write_anchor([{"likely_paths": ["registry.json"]}])
        allowed, error = anchor_aware_write_check(self.root, self.run_id, "registry.json")
        self.assertTrue(allowed, error)

    def test_bundled_config_context_denied_in_implementation(self) -> None:
        (self.root / "registry.json").write_text("{}", encoding="utf-8")
        self._write_anchor([{"likely_paths": ["src/app.py", "registry.json"]}])
        allowed, error = anchor_aware_write_check(self.root, self.run_id, "registry.json")
        self.assertFalse(allowed)
        self.assertIn("bundled", error or "")

    def test_unapproved_config_denied_in_implementation(self) -> None:
        (self.root / "registry.json").write_text("{}", encoding="utf-8")
        self._write_anchor([{"likely_paths": ["src/app.py"]}])
        allowed, error = anchor_aware_write_check(self.root, self.run_id, "registry.json")
        self.assertFalse(allowed)
        self.assertIn("not in run", error or "")

    def test_codex_apply_patch_allows_only_approved_paths(self) -> None:
        self._write_anchor([{"likely_paths": ["src/app.py"]}])
        allowed = run_hook({
            "tool_name": "apply_patch",
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: src/app.py\n@@\n-print(\"old\")\n+print(\"new\")\n*** End Patch",
            },
            "cwd": str(self.root),
        })
        self.assertIsNone(allowed)

        denied = run_hook({
            "tool_name": "apply_patch",
            "tool_input": {
                "command": (
                    "*** Begin Patch\n"
                    "*** Update File: src/app.py\n"
                    "@@\n-old\n+new\n"
                    "*** Update File: tests/test_app.py\n"
                    "@@\n-old\n+new\n"
                    "*** End Patch"
                ),
            },
            "cwd": str(self.root),
        })
        self.assertEqual("deny", denied["hookSpecificOutput"]["permissionDecision"])
        self.assertIn("tests/test_app.py", denied["hookSpecificOutput"]["permissionDecisionReason"])

    def test_copilot_camel_case_json_args_are_normalized(self) -> None:
        self._write_anchor([{"likely_paths": ["src/app.py"]}])
        response = run_hook({
            "toolName": "edit",
            "toolArgs": json.dumps({"path": str(self.root / "src" / "app.py")}),
            "cwd": str(self.root),
        })
        self.assertIsNone(response)

    def test_copilot_native_denial_uses_top_level_decision_envelope(self) -> None:
        self._write_anchor([{"likely_paths": ["src/app.py"]}])
        response = run_hook({
            "toolName": "edit",
            "toolArgs": {"path": str(self.root / "tests" / "test_app.py")},
            "cwd": str(self.root),
        })
        self.assertEqual("deny", response["permissionDecision"])
        self.assertIn("tests/test_app.py", response["permissionDecisionReason"])
        self.assertNotIn("hookSpecificOutput", response)

    def test_copilot_pascal_case_alias_is_normalized(self) -> None:
        self._write_anchor([{"likely_paths": ["src/app.py"]}])
        response = run_hook({
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": str(self.root / "tests" / "test_app.py")},
            "cwd": str(self.root),
        })
        self.assertEqual("deny", response["hookSpecificOutput"]["permissionDecision"])

    def test_active_run_denies_malformed_write_payload(self) -> None:
        response = run_hook({
            "tool_name": "apply_patch",
            "tool_input": {"command": "not a complete patch"},
            "cwd": str(self.root),
        })
        self.assertEqual("deny", response["hookSpecificOutput"]["permissionDecision"])
        self.assertIn("no complete edited-path set", response["hookSpecificOutput"]["permissionDecisionReason"])

    def test_non_edit_tool_is_unchanged(self) -> None:
        response = run_hook({
            "tool_name": "Read",
            "tool_input": {"file_path": str(self.root / "tests" / "test_app.py")},
            "cwd": str(self.root),
        })
        self.assertIsNone(response)

    def test_codex_hook_config_is_synchronous(self) -> None:
        config = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        groups = config["hooks"]["PreToolUse"]
        self.assertEqual("Edit|Write", groups[0]["matcher"])
        handler = groups[0]["hooks"][0]
        self.assertEqual("command", handler["type"])
        self.assertIn("scripts/write_guardian.py", handler["command"])
        self.assertIsNot(handler.get("async"), True)


if __name__ == "__main__":
    unittest.main()
