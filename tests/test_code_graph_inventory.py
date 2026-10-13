"""Phase 3: repository inventory honors the shared workspace path policy.

Run: python -m unittest tests.test_code_graph_inventory -v
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import code_graph_inventory as inv  # noqa: E402


class InventoryPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "src").mkdir()
        (self.root / "src" / "real.py").write_text("VALUE = 1\n", encoding="utf-8")
        nested = self.root / ".codex" / "worktrees" / "stale" / "src" / "ghost.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("VALUE = 2\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_relevant_files_excludes_nested_worktrees_but_keeps_real_files(self) -> None:
        rels = {path.relative_to(self.root).as_posix() for path in inv.relevant_files(self.root)}
        self.assertIn("src/real.py", rels)
        self.assertNotIn(".codex/worktrees/stale/src/ghost.py", rels)

    def test_snapshot_fingerprint_ignores_worktree_ghosts(self) -> None:
        with_ghost = inv.snapshot(self.root)
        shutil.rmtree(self.root / ".codex")
        without_ghost = inv.snapshot(self.root)
        self.assertEqual(with_ghost["algorithm"], without_ghost["algorithm"])
        self.assertEqual(with_ghost["fingerprint"], without_ghost["fingerprint"])

    def test_policy_excluded_carries_reasons(self) -> None:
        records = {row["path"]: row for row in inv.policy_excluded(self.root)}
        self.assertNotIn("src/real.py", records)
        self.assertIn(".codex/worktrees/stale/src/ghost.py", records)
        ghost = records[".codex/worktrees/stale/src/ghost.py"]
        self.assertEqual(ghost["role"], "managed-worktree")
        self.assertTrue(ghost["reason_codes"])


if __name__ == "__main__":
    unittest.main()
