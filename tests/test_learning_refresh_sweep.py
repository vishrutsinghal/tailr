from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V3 = load("refresh_sweep_v3", "scripts/learning-v3.py")
REFRESH = load("refresh_sweep_module", "scripts/learning-refresh.py")
RETRIEVAL = load("refresh_sweep_retrieval", "scripts/learning-retrieval.py")


def capture(root: Path, learning_id: str, path: str = "src/a.py") -> dict:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / path).write_text("v1\n", encoding="utf-8")
    record = V3.build_record(
        root, learning_id=learning_id, learning_class="general",
        summary="sweep fixture", advice="sweep advice",
        source_kind="test", source_ref="fixture.json",
        source_fingerprint="sha256:" + "0" * 64, captured_by="test",
        task_types=["test"], tags=[], path_patterns=[path], exclusions=[],
        invalidators=["source-change"], confidence_score=80,
    )
    return V3.append_record(root, record)


class RefreshSweepTests(unittest.TestCase):
    def test_sweep_flags_changed_content_and_agrees_with_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            capture(root, "lrn-sweep-triggered")
            (root / "src" / "a.py").write_text("v2 changed\n", encoding="utf-8")
            result = REFRESH.sweep_v3(root)
            triggered = [row["learning_id"] for row in result["triggered"]]
            self.assertEqual(triggered, ["lrn-sweep-triggered"])
            self.assertIn("source-change", result["triggered"][0]["reasons"][0])
            # Same verdict as the retrieval gate on the same record.
            records = {row["record_id"]: row for row in V3.read_records(root)}
            record = next(iter(V3.latest_records(V3.read_records(root)).values()))
            blocked, _ = RETRIEVAL.freshness_reasons(
                root, record, {}, {record["record_id"]: record})
            self.assertTrue(any("source-change" in reason for reason in blocked))

    def test_sweep_reports_clean_when_nothing_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            capture(root, "lrn-sweep-clean")
            result = REFRESH.sweep_v3(root)
            self.assertEqual(result["triggered"], [])
            self.assertEqual(result["clean"], 1)

    def test_sweep_flags_records_without_snapshot_for_backfill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src" / "a.py").write_text("v1\n", encoding="utf-8")
            record = V3.build_record(
                root, learning_id="lrn-sweep-legacy", learning_class="general",
                summary="legacy", advice="legacy advice",
                source_kind="test", source_ref="fixture.json",
                source_fingerprint="sha256:" + "0" * 64, captured_by="test",
            )
            del record["freshness"]["invalidator_snapshot"]
            V3.append_record(root, record)
            result = REFRESH.sweep_v3(root)
            self.assertEqual(result["needs_backfill"], ["lrn-sweep-legacy"])

    def test_sweep_on_missing_store_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = REFRESH.sweep_v3(Path(temp))
        self.assertEqual(result["state"], "no-store")


if __name__ == "__main__":
    unittest.main()
