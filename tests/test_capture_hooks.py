"""Phase 1 focused check: passive capture cache + hooks.

Run: python -m pytest tests/test_capture_hooks.py -v
(under scripts/ root, or python -m unittest from the repo root)
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import capture_cache  # noqa: E402
import capture_hooks  # noqa: E402


class PassiveCaptureCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        capture_hooks.reset_for_tests()

    def tearDown(self) -> None:
        capture_hooks.reset_for_tests()
        self.tmp.cleanup()

    def test_record_file_read_upserts_and_counts(self) -> None:
        cache = capture_hooks.get_cache(self.root)
        capture_hooks.on_file_read(self.root, "src/a.py")
        capture_hooks.on_file_read(self.root, "src/a.py")
        entry = cache.file_entry("src/a.py")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["times_seen"], 2)
        self.assertEqual(len(cache.data["files_touched"]), 1)

    def test_file_edit_increments_edit_count(self) -> None:
        capture_hooks.on_file_edit(self.root, "src/a.py")
        capture_hooks.on_file_edit(self.root, "src/a.py")
        entry = capture_hooks.get_cache(self.root).file_entry("src/a.py")
        self.assertEqual(entry["edit_count"], 2)
        self.assertEqual(entry["times_seen"], 2)

    def test_import_and_symbol_dedupe(self) -> None:
        capture_hooks.on_import_encountered(self.root, "src/a.py", "src/b.py", "direct")
        capture_hooks.on_import_encountered(self.root, "src/a.py", "src/b.py", "direct")
        capture_hooks.on_symbol_observed(self.root, "src/a.py", "validate", "function")
        capture_hooks.on_symbol_observed(self.root, "src/a.py", "validate", "function")
        cache = capture_hooks.get_cache(self.root)
        self.assertEqual(len(cache.data["import_edges_captured"]), 1)
        self.assertEqual(len(cache.data["symbols_observed"]), 1)
        self.assertEqual(cache.data["import_edges_captured"][0]["times_seen"], 2)

    def test_call_and_traceback_recording(self) -> None:
        capture_hooks.on_call_site_encountered(self.root, "src/a.py", "f", "src/b.py", "g")
        capture_hooks.on_traceback_observed(self.root, ["a.f", "b.g", "c.h"])
        cache = capture_hooks.get_cache(self.root)
        self.assertEqual(len(cache.data["call_edges_captured"]), 1)
        self.assertEqual(
            cache.data["call_edges_captured"][0]["to"], "src/b.py:g"
        )
        self.assertEqual(len(cache.data["traceback_chains_captured"]), 1)

    def test_has_imports_and_symbols_gate(self) -> None:
        capture_hooks.on_import_encountered(self.root, "src/a.py", "src/b.py")
        cache = capture_hooks.get_cache(self.root)
        self.assertFalse(cache.has_imports_and_symbols("src/a.py"))
        capture_hooks.on_symbol_observed(self.root, "src/a.py", "f")
        self.assertTrue(cache.has_imports_and_symbols("src/a.py"))
        self.assertFalse(cache.has_imports_and_symbols("src/b.py"))

    def test_persists_and_reload_roundtrip(self) -> None:
        capture_hooks.on_file_read(self.root, "src/a.py")
        capture_hooks.on_symbol_observed(self.root, "src/a.py", "f")
        path = self.root / ".tailtrail" / "capture-cache.json"
        self.assertTrue(path.exists())
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["files_touched"][0]["path"], "src/a.py")
        reloaded = capture_cache.PassiveCaptureCache(self.root)
        self.assertEqual(reloaded.file_entry("src/a.py")["path"], "src/a.py")

    def test_clear_resets_all_sections(self) -> None:
        capture_hooks.on_file_read(self.root, "src/a.py")
        cache = capture_hooks.get_cache(self.root)
        cache.clear()
        self.assertEqual(cache.data["files_touched"], [])
        self.assertFalse(cache.path.exists() and json.loads(cache.path.read_text(encoding="utf-8"))["files_touched"])

    def test_hooks_never_raise(self) -> None:
        # Corrupt the cache file; hooks must still be safe.
        path = self.root / ".tailtrail" / "capture-cache.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json", encoding="utf-8")
        capture_hooks.reset_for_tests()
        capture_hooks.on_file_read(self.root, "src/a.py")
        self.assertEqual(
            capture_hooks.get_cache(self.root).file_entry("src/a.py")["path"],
            "src/a.py",
        )

    def test_empty_inputs_are_ignored(self) -> None:
        cache = capture_hooks.get_cache(self.root)
        capture_hooks.on_file_read(self.root, "")
        capture_hooks.on_import_encountered(self.root, "", "b.py")
        self.assertEqual(cache.data["files_touched"], [])
        self.assertEqual(cache.data["import_edges_captured"], [])


if __name__ == "__main__":
    unittest.main()
