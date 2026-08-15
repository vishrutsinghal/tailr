from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def module(file: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


importer = module("spec-kit-import.py", "spec_kit_observability_import")
bridge = module("spec-kit-bridge.py", "spec_kit_observability_bridge")
lock = module("planning-lock.py", "spec_kit_observability_lock")
ci = module("ci-evidence-ingest.py", "spec_kit_observability_ci")
observability = module("spec-kit-observability.py", "spec_kit_observability_test")
gate = module("spec-kit-ci-gate.py", "spec_kit_observability_gate")


class SpecKitObservabilityTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8")

    def activate_complete_run(self, root: Path) -> None:
        self.write(root, "specs/001-orders/spec.md", """FR-001: Amend an order before fulfilment.
FR-002: Preserve cancellation behavior.
## Acceptance Criteria
- The service accepts a valid amendment.
""")
        importer.import_feature(root, "001-orders", "planning")
        source = bridge.load(root, "001-orders")
        report = {"goal": "Use Spec Kit feature 001-orders", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"requirement_matrix": bridge.requirement_matrix(source, ["src/orders.py"])}, "spec_kit_source": source}
        lock.create(root, report["goal"], "observe-run"); lock.save_start_report(root, "observe-run", report); activated = lock.activate(root, "observe-run", True)
        mapping = json.loads((root / activated["spec_kit_slices"]["artifacts"]["mapping"]).read_text(encoding="utf-8"))["mappings"]
        evidence = {"schema_version": "1", "type": "tailtrail-spec-kit-evidence", "run_id": "observe-run", "requirements": [{"requirement_uid": row["requirement_uid"], "external_id": row["external_id"], "state": "complete", "checkpoint": "checkpoints/checkpoint-1.json", "blockers": []} for row in mapping]}
        (root / ".tailtrail/runs/observe-run/spec-kit/evidence-v1.json").write_text(json.dumps(evidence), encoding="utf-8")
        receipt = {"provenance": {"run_id": "ci-1", "job": "tests"}, "results": [{"requirement_uid": row["requirement_uid"], "tier": "unit", "outcome": "pass", "command": "python -m unittest", "environment": "ci", "asserted_behavior": "approved requirement works"} for row in mapping]}
        path = root / "ci.json"; path.write_text(json.dumps(receipt), encoding="utf-8"); ci.ingest(root, "observe-run", path)

    def test_report_composes_governance_release_and_saved_baseline_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.activate_complete_run(root)
            baseline = root / "baseline.json"; baseline.write_text(json.dumps({"requirements_complete": 1, "unresolved_drift": 1}), encoding="utf-8")
            report = observability.report(root, "observe-run", baseline)
            self.assertEqual(report["governance"]["status"], "passed")
            self.assertEqual(report["release"]["state"], "advisory-ready")
            self.assertEqual(report["evaluation"]["comparison"]["requirement_completion_delta"], 1)
            self.assertTrue((root / report["artifact"]).is_file())
            self.assertEqual(gate.evaluate(root, "observe-run")["status"], "passed")


if __name__ == "__main__": unittest.main()
