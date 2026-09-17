"""Phase 8 focused check: commit coverage prompt and reporting.

Run: python -m unittest tests.test_commit_prompt -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import code_graph_cache as cgc  # noqa: E402
import commit_prompt as cp  # noqa: E402


LINKED_PY = '"""Linked module."""\nfrom src.base import helper\n\n\ndef work(value):\n    return helper(value)\n'
BASE_PY = '"""Base module."""\nimport os\n\n\ndef helper(value):\n    return os.path.basename(str(value))\n'
LEAF_PY = '"""Leaf module, no imports."""\n\n\ndef lone():\n    return 1\n'
UTIL_PY = '"""Shared utilities."""\nimport os\n\n\ndef join(base, name):\n    return os.path.join(base, name)\n'


class CommitPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "linked.py").write_text(LINKED_PY, encoding="utf-8")
        (self.root / "src" / "base.py").write_text(BASE_PY, encoding="utf-8")
        (self.root / "src" / "leaf.py").write_text(LEAF_PY, encoding="utf-8")
        (self.root / "src" / "util.py").write_text(UTIL_PY, encoding="utf-8")
        cgc.update(self.root, ["src/linked.py", "src/base.py", "src/leaf.py", "src/util.py"])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_full_coverage_prompts_with_medium_depth(self) -> None:
        report = cp.assess(self.root, ["src/linked.py", "src/base.py"])
        self.assertEqual(report["decision"], "yes")
        self.assertEqual(report["coverage"], 1.0)
        self.assertEqual(report["suggested_depth"], "medium")
        # Nothing built yet: whole task is gap.
        self.assertEqual(sorted(report["suggested_scope"]), ["src/base.py", "src/linked.py"])

    def test_low_coverage_waits(self) -> None:
        report = cp.assess(self.root, ["src/leaf.py", "src/missing1.py", "src/missing2.py",
                                       "src/missing3.py", "src/missing4.py"])
        self.assertEqual(report["decision"], "no")
        self.assertLess(report["coverage"], 0.25)

    def test_mid_coverage_considers_only_large_tasks(self) -> None:
        small = cp.assess(self.root, ["src/linked.py", "src/leaf.py", "src/x.py"])
        self.assertEqual(small["decision"], "no")
        large_files = (["src/linked.py", "src/base.py", "src/util.py"]
                       + [f"src/x{i}.py" for i in range(7)])
        large = cp.assess(self.root, large_files)
        self.assertEqual(large["decision"], "consider")

    def test_sprawling_task_suggests_shallow(self) -> None:
        sprawling = [f"src/mod{i}.py" for i in range(20)]
        for i, rel in enumerate(sprawling):
            (self.root / rel).write_text(
                f'"""Module {i}."""\nimport os\n\n\ndef f{i}():\n    return os.name\n',
                encoding="utf-8",
            )
        cgc.update(self.root, sprawling)
        report = cp.assess(self.root, sprawling)
        self.assertEqual(report["decision"], "yes")
        self.assertEqual(report["suggested_depth"], "shallow")

    def test_recent_mapper_commit_suppresses(self) -> None:
        meta = self.root / "tailtrail-meta"
        meta.mkdir()
        (meta / "code-graph-cache.json").write_text(
            json.dumps({
                "schema_version": "1",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "scope": ["src/linked.py"],
                "graph": {"symbols": []},
            }),
            encoding="utf-8",
        )
        report = cp.assess(self.root, ["src/linked.py", "src/base.py"])
        self.assertEqual(report["decision"], "no")
        self.assertTrue(report["recent_commit"])

    def test_related_unread_surfaces_linked_files(self) -> None:
        report = cp.assess(self.root, ["src/linked.py"])
        self.assertIn("src/base.py", report["related_unread"])
        self.assertNotIn("src/linked.py", report["related_unread"])

    def test_empty_task_list_is_no(self) -> None:
        report = cp.assess(self.root, [])
        self.assertEqual(report["decision"], "no")
        self.assertEqual(report["coverage"], 0.0)

    def test_cli_always_exits_zero(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cp.main(["--root", self.root.as_posix(), "--file", "src/leaf.py"])
        self.assertEqual(code, 0)
        self.assertIn("Decision:", buffer.getvalue())
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cp.main(["--root", self.root.as_posix(), "--file", "src/linked.py",
                            "--file", "src/base.py", "--format", "json"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["decision"], "yes")
        self.assertIn("--depth medium", payload["suggested_command"])


if __name__ == "__main__":
    unittest.main()
