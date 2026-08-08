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
    if spec is None or spec.loader is None:
        raise RuntimeError(relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("phase1_run_ledger", "scripts/run-ledger.py")


class RunLedgerTests(unittest.TestCase):
    def test_init_appends_deterministic_event_and_projects_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = ledger.init_run(root, "run-demo", "change validation")
            second = ledger.append_event(root, "run-demo", "graph_receipt", {"requirement_uids": ["req-a"]})
            state = ledger.projection(root, "run-demo")
        self.assertEqual(manifest["run_id"], "run-demo")
        self.assertEqual(second["event_id"], ledger.event_id("run-demo", 2, "graph_receipt"))
        self.assertEqual(state["events"], 2)
        self.assertEqual(state["status"], "draft")

    def test_validation_rejects_non_deterministic_event_id(self) -> None:
        event = {"schema_version": "1", "type": "tailtrail-run-event", "run_id": "run", "sequence": 1, "event_id": "wrong", "created_at": "2026-01-01T00:00:00+00:00", "event_type": "run_created", "payload": {}}
        self.assertIn("event_id does not match deterministic value", ledger.validate_event(event, 1))

    def test_failure_event_is_accepted_and_projected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger.init_run(root, "run-failure", "fix validation")
            ledger.append_event(root, "run-failure", "execution_failure_recorded", {"failure_id": "failure-0001"})
            state = ledger.projection(root, "run-failure")
        self.assertEqual(state["activity"]["execution_failure_recorded"], 1)
