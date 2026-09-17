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
    guard_write,
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


if __name__ == "__main__":
    unittest.main()
