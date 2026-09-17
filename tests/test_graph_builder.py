"""Phase 2 focused check: explicit graph build pipeline.

Run: python -m unittest tests.test_graph_builder -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import graph_builder  # noqa: E402


A_PY = '"""a module."""\nfrom src.b import func\n\n\ndef run(value):\n    return func(value)\n'
B_PY = '"""b module."""\n\n\ndef func(value):\n    return value * 2\n'
C_PY = '"""untouched residual module."""\n\n\ndef unused():\n    return 1\n'


class GraphBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "src" / "a.py").write_text(A_PY, encoding="utf-8")
        (self.root / "src" / "b.py").write_text(B_PY, encoding="utf-8")
        (self.root / "src" / "c.py").write_text(C_PY, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _warm(self) -> None:
        import capture_hooks
        capture_hooks.reset_for_tests()
        capture_hooks.on_file_read(self.root, "src/a.py")
        capture_hooks.on_file_read(self.root, "src/b.py")
        capture_hooks.on_import_encountered(self.root, "src/a.py", "src/b.py")
        capture_hooks.on_symbol_observed(self.root, "src/a.py", "run", "function")

    def test_shallow_commit_writes_imports_only_and_clears_passive(self) -> None:
        self._warm()
        summary = graph_builder.commit_graph(
            self.root,
            target_files=["src/a.py", "src/b.py"],
            depth="shallow",
            write_shared=False,
        )
        self.assertEqual(summary["status"], "committed")
        self.assertEqual(summary["errors"], [])
        self.assertEqual(summary["call_chains"], 0)
        self.assertGreater(summary["references"], 0)
        cache_path = self.root / ".tailtrail" / "code-graph-cache.json"
        self.assertTrue(cache_path.exists())
        # Built files drained, untouched residual preserved.
        self.assertEqual(summary["passive_cleared"], 2)
        self.assertEqual(summary["passive_residual"], 0)

    def test_residual_passive_data_is_preserved(self) -> None:
        self._warm()
        import capture_hooks
        capture_hooks.on_file_read(self.root, "src/c.py")
        summary = graph_builder.commit_graph(
            self.root, target_files=["src/a.py"], depth="medium", write_shared=False
        )
        self.assertEqual(summary["passive_cleared"], 1)
        self.assertEqual(summary["passive_residual"], 2)
        residual = capture_hooks.get_cache(self.root).file_entry("src/c.py")
        self.assertIsNotNone(residual)
        # b.py was not in the build scope, so it remains residual too.
        self.assertIsNotNone(capture_hooks.get_cache(self.root).file_entry("src/b.py"))

    def test_medium_commit_has_symbols_and_call_chains(self) -> None:
        summary = graph_builder.commit_graph(
            self.root,
            target_files=["src/a.py", "src/b.py"],
            depth="medium",
            write_shared=False,
        )
        self.assertEqual(summary["status"], "committed")
        self.assertGreater(summary["symbols"], 0)
        self.assertGreater(summary["call_chains"], 0)

    def test_scope_falls_back_to_warm_passive_cache(self) -> None:
        self._warm()
        summary = graph_builder.commit_graph(self.root, depth="medium", write_shared=False)
        self.assertEqual(summary["status"], "committed")
        self.assertEqual(sorted(summary["built_files"]), ["src/a.py", "src/b.py"])

    def test_no_scope_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            graph_builder.commit_graph(self.root, depth="medium")

    def test_invalid_depth_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            graph_builder.commit_graph(self.root, target_files=["src/a.py"], depth="extreme")

    def test_committed_cache_roundtrips_validation(self) -> None:
        graph_builder.commit_graph(
            self.root, target_files=["src/a.py", "src/b.py"], depth="medium", write_shared=False
        )
        cache, error = graph_builder.load_graph(self.root, write_shared=False)
        self.assertIsNone(error)
        self.assertIsNotNone(cache)
        self.assertEqual(graph_builder.validate_payload(cache), [])

    def test_validate_payload_reports_missing_fields(self) -> None:
        self.assertIn("missing required field: root", graph_builder.validate_payload({"graph": {}}))
        self.assertEqual(graph_builder.validate_payload("nope"), ["payload is not an object"])


if __name__ == "__main__":
    unittest.main()
