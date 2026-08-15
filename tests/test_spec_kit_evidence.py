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
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


importer = module("spec-kit-import.py", "spec_kit_evidence_import")
bridge = module("spec-kit-bridge.py", "spec_kit_evidence_bridge")
lock = module("planning-lock.py", "spec_kit_evidence_lock")
evidence = module("spec-kit-evidence.py", "spec_kit_evidence_test")


class SpecKitEvidenceTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8")

    def activated(self, root: Path) -> tuple[dict[str, object], str]:
        self.write(root, "specs/001-api/spec.md", """FR-001: Add the documented contracts/api.yaml endpoint.
FR-002: Preserve existing behavior.
## Acceptance Criteria
- The endpoint is available.
""")
        self.write(root, "specs/001-api/contracts/api.yaml", "openapi: 3.0.0\n")
        importer.import_feature(root, "001-api", "planning")
        source = bridge.load(root, "001-api")
        report = {"goal": "Use Spec Kit feature 001-api", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"requirement_matrix": bridge.requirement_matrix(source, ["src/api.py"])}, "spec_kit_source": source}
        lock.create(root, report["goal"], "evidence-run"); lock.save_start_report(root, "evidence-run", report)
        activated = lock.activate(root, "evidence-run", True)
        uid = activated["anchor"]["requirements"][0]
        return activated, uid

    def test_activation_creates_requirement_linked_harness_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); activated, uid = self.activated(root)
            plan = activated["spec_kit_evidence"]
            self.assertEqual(plan["state"], "created")
            active = next(item for item in plan["requirements"] if item["requirement_uid"] == uid)
            self.assertIn("Requirement Completion Harness", active["selected_controls"])
            self.assertIn("Architecture Fitness Harness", active["selected_controls"])

    def test_generic_checkpoint_cannot_complete_active_contract_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); _, uid = self.activated(root)
            checkpoint = root / "checkpoint.json"
            checkpoint.write_text(
                json.dumps(
                    {
                        "requirements": [
                            {
                                "requirement_uid": uid,
                                "state": "validated",
                                "evidence": [{"outcome": "pass"}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            incomplete = evidence.record(root, "evidence-run", checkpoint, None, None)
            active = next(item for item in incomplete["requirements"] if item["requirement_uid"] == uid)
            self.assertEqual(active["state"], "incomplete")
            self.assertIn("architecture assessment is required", active["blockers"])
            architecture = root / "architecture.json"; architecture.write_text(json.dumps({"complete": True, "findings": []}), encoding="utf-8")
            complete = evidence.record(root, "evidence-run", checkpoint, architecture, None)
            active = next(item for item in complete["requirements"] if item["requirement_uid"] == uid)
            self.assertEqual(active["state"], "complete")
            self.assertTrue(complete["complete"])


if __name__ == "__main__": unittest.main()
