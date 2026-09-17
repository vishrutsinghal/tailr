"""Phase 2 focused check: passive capture queues + batched Phase 1 flush.

Run: python -m unittest tests.test_capture_hooks -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import capture_hooks  # noqa: E402
import code_graph_cache  # noqa: E402


class PassiveCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (self.root / "src" / "b.py").write_text("import src.a\n\n\ndef g():\n    return 2\n", encoding="utf-8")
        capture_hooks.reset_for_tests()

    def tearDown(self) -> None:
        capture_hooks.reset_for_tests()
        self.tmp.cleanup()

    def test_hooks_queue_without_touching_disk(self) -> None:
        capture_hooks.on_file_read(self.root, "src/a.py")
        capture_hooks.on_file_read(self.root, "src/a.py")
        self.assertEqual(capture_hooks.pending(self.root), ["src/a.py"])
        self.assertIsNone(code_graph_cache.find_cache(self.root))

    def test_import_symbol_and_call_hooks_queue_files(self) -> None:
        capture_hooks.on_import_encountered(self.root, "src/a.py", "src/b.py", "direct")
        capture_hooks.on_symbol_observed(self.root, "src/a.py", "f", "function")
        capture_hooks.on_call_site_encountered(self.root, "src/a.py", "f", "src/b.py", "g")
        self.assertEqual(capture_hooks.pending(self.root), ["src/a.py", "src/b.py"])

    def test_traceback_hook_is_compatible_noop(self) -> None:
        capture_hooks.on_traceback_observed(self.root, ["a.f", "b.g"])
        self.assertEqual(capture_hooks.pending(self.root), [])

    def test_flush_merges_into_phase1_cache_and_drains_queue(self) -> None:
        capture_hooks.on_file_read(self.root, "src/a.py")
        capture_hooks.on_file_read(self.root, "src/b.py")
        summary = capture_hooks.flush(self.root)
        self.assertEqual(summary["updated"], 2)
        self.assertEqual(summary["errors"], [])
        self.assertEqual(capture_hooks.pending(self.root), [])
        data, error = code_graph_cache.load(code_graph_cache.default_cache_path(self.root))
        self.assertIsNone(error)
        self.assertIn("f", data["files"]["src/a.py"]["symbols"])
        self.assertIn("g", data["files"]["src/b.py"]["symbols"])

    def test_flush_empty_is_zero_summary(self) -> None:
        self.assertEqual(
            capture_hooks.flush(self.root),
            {"cache_path": None, "updated": 0, "pruned": 0, "total": 0, "errors": []},
        )

    def test_flush_never_raises_on_corrupt_cache(self) -> None:
        path = code_graph_cache.default_cache_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json", encoding="utf-8")
        capture_hooks.on_file_read(self.root, "src/a.py")
        summary = capture_hooks.flush(self.root)
        self.assertEqual(summary["updated"], 1)
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("src/a.py", on_disk["files"])

    def test_discard_drops_consumed_paths(self) -> None:
        capture_hooks.on_file_read(self.root, "src/a.py")
        capture_hooks.on_file_read(self.root, "src/b.py")
        self.assertEqual(capture_hooks.discard(self.root, ["src/a.py"]), 1)
        self.assertEqual(capture_hooks.pending(self.root), ["src/b.py"])

    def test_empty_inputs_are_ignored(self) -> None:
        capture_hooks.on_file_read(self.root, "")
        capture_hooks.on_import_encountered(self.root, "", "")
        self.assertEqual(capture_hooks.pending(self.root), [])

    def test_hooks_never_raise(self) -> None:
        capture_hooks.on_file_read(self.root, "")
        capture_hooks.on_file_edit(self.root, "", edit_count=3)
        capture_hooks.flush(self.root)  # nothing queued: no-op, no raise


if __name__ == "__main__":
    unittest.main()
