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


importer = module("spec-kit-import.py", "spec_kit_converge_import")
bridge = module("spec-kit-bridge.py", "spec_kit_converge_bridge")
lock = module("planning-lock.py", "spec_kit_converge_lock")
converge = module("spec-kit-converge.py", "spec_kit_converge_test")
ci = module("ci-evidence-ingest.py", "spec_kit_converge_ci")


class SpecKitConvergenceTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def activate(self, root: Path) -> dict[str, object]:
        self.write(root, "specs/001-orders/spec.md", """FR-001: Amend an order before fulfilment.
FR-002: Preserve cancellation behavior.
## Acceptance Criteria
- The service accepts a valid amendment.
""")
        importer.import_feature(root, "001-orders", "planning")
        source = bridge.load(root, "001-orders")
        report = {"goal": "Use Spec Kit feature 001-orders", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"requirement_matrix": bridge.requirement_matrix(source, ["src/orders.py"])}, "spec_kit_source": source}
        lock.create(root, report["goal"], "converge-run")
        lock.save_start_report(root, "converge-run", report)
        return lock.activate(root, "converge-run", True)

    def test_convergence_reports_ready_only_with_complete_mapped_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); activated = self.activate(root)
            mapping = json.loads((root / activated["spec_kit_slices"]["artifacts"]["mapping"]).read_text(encoding="utf-8"))
            evidence = {"schema_version": "1", "type": "tailtrail-spec-kit-evidence", "run_id": "converge-run", "requirements": [{"requirement_uid": row["requirement_uid"], "external_id": row["external_id"], "state": "complete", "checkpoint": "checkpoints/checkpoint-1.json", "blockers": []} for row in mapping["mappings"]]}
            path = root / ".tailtrail/runs/converge-run/spec-kit/evidence-v1.json"; path.write_text(json.dumps(evidence), encoding="utf-8")
            report = converge.converge(root, "converge-run")
            self.assertEqual(report["closure_state"], "ready")
            self.assertEqual(len(report["requirements"]), 2)
            self.assertTrue((root / report["artifact"]).is_file())

    def test_convergence_blocks_when_source_changed_after_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.activate(root)
            self.write(root, "specs/001-orders/spec.md", """FR-001: Amend an order before fulfilment with idempotency.
FR-002: Preserve cancellation behavior.
## Acceptance Criteria
- The service accepts a valid amendment.
""")
            report = converge.converge(root, "converge-run")
            self.assertEqual(report["closure_state"], "blocked")
            self.assertEqual(report["requirements"][0]["state"], "needs-decision")

    def test_convergence_includes_supplied_ci_receipts_without_claiming_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); activated = self.activate(root)
            mapping = json.loads((root / activated["spec_kit_slices"]["artifacts"]["mapping"]).read_text(encoding="utf-8"))
            receipt = root / "ci.json"
            receipt.write_text(json.dumps({"provenance": {"run_id": "ci-1", "job": "tests"}, "results": [{"requirement_uid": mapping["mappings"][0]["requirement_uid"], "tier": "unit", "outcome": "pass", "command": "python -m unittest", "environment": "ci", "asserted_behavior": "order amendment is accepted"}]}), encoding="utf-8")
            ci.ingest(root, "converge-run", receipt)
            report = converge.converge(root, "converge-run")
            self.assertEqual(report["closure_state"], "gaps")
            self.assertEqual(len(report["validation_receipts"]), 1)


if __name__ == "__main__":
    unittest.main()
