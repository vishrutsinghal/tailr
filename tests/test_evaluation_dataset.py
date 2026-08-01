from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load() -> object:
    spec = importlib.util.spec_from_file_location("evaluation_dataset_test", ROOT / "scripts" / "evaluation-dataset.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dataset = load()


class EvaluationDatasetTests(unittest.TestCase):
    def test_curated_dataset_has_twelve_paired_multi_file_tasks(self) -> None:
        payload = dataset.read_dataset(dataset.DEFAULT_DATASET)
        self.assertEqual(dataset.errors(payload), [])
        self.assertEqual(len(payload["tasks"]), 12)
        self.assertTrue(all(len(task["files"]) >= 2 for task in payload["tasks"]))

    def test_report_exposes_all_delivery_metrics_and_boundaries(self) -> None:
        payload = dataset.report(dataset.read_dataset(dataset.DEFAULT_DATASET))
        self.assertEqual(payload["task_count"], 12)
        self.assertGreater(payload["tailtrail"]["requirements"]["completion_rate"], payload["baseline"]["requirements"]["completion_rate"])
        self.assertLess(payload["delta_tailtrail_minus_baseline"]["missed_callers"], 0)
        self.assertIn("not live-agent benchmark results", " ".join(payload["claim_boundaries"]))
        self.assertIn("Developer review time", dataset.render(payload))


if __name__ == "__main__":
    unittest.main()
