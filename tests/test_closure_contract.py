from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("closure_contract_ledger_test", "scripts/run-ledger.py")
anchor = load("closure_contract_anchor_test", "scripts/change-intent-anchor.py")
contract = load("closure_contract_test", "scripts/closure-contract.py")


class ClosureContractTests(unittest.TestCase):
    def setup_run(self, root: Path) -> str:
        ledger.init_run(root, "run", "add cancellation")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{
            "statement": "Cancel an eligible order.",
            "acceptance_criteria": ["eligible order cancels"],
            "preserve_rules": ["shipped orders stay protected"],
            "likely_paths": ["src/orders/service.py"],
            "evidence_plan": ["integration proof"],
        }]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        return anchor.approve(root, "run")["requirements"][0]["requirement_uid"]

    def payload(self, uid: str) -> dict[str, object]:
        return {
            "schema_version": "1",
            "type": "tailtrail-execution-closure-input",
            "run_id": "run",
            "changed_paths": ["src/orders/service.py", "tests/integration/test_orders.py"],
            "receipts": [{
                "requirement_uids": [uid],
                "tier": "integration",
                "command_label": "order cancellation integration",
                "command": "python -m unittest tests.integration.test_orders -v",
                "outcome": "pass",
                "environment": "local",
                "asserted_behavior": "Eligible cancellation releases inventory once.",
            }],
        }

    def test_validates_a_requirement_linked_record_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            result = contract.validate_input(root, self.payload(uid))
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        self.assertEqual(result["contract_status"], "valid")
        self.assertEqual(result["receipts"][0]["requirement_uids"], [uid])
        self.assertEqual(before, after)

    def test_rejects_unknown_requirement_and_unsafe_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            unknown = self.payload("req-000000000000")
            unsafe = self.payload(uid)
            unsafe["changed_paths"] = ["../outside.py"]
            with self.assertRaisesRegex(ValueError, "unknown approved requirement"):
                contract.validate_input(root, unknown)
            with self.assertRaisesRegex(ValueError, "repository-relative"):
                contract.validate_input(root, unsafe)

    def test_rejects_raw_output_and_mismatched_token_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            raw_output = self.payload(uid)
            raw_output["receipts"][0]["command"] = "python -m unittest\nfull raw output"
            telemetry = self.payload(uid)
            telemetry["host_token_telemetry"] = {"task_id": "different-run", "artifact": "evidence/usage.json"}
            with self.assertRaisesRegex(ValueError, "single line"):
                contract.validate_input(root, raw_output)
            with self.assertRaisesRegex(ValueError, "must equal run_id"):
                contract.validate_input(root, telemetry)

    def test_public_cli_validates_without_writing_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            input_path = root / "closure-input.json"
            input_path.write_text(json.dumps(self.payload(uid)), encoding="utf-8")
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "closure", "validate", "--root", root.as_posix(), "--input", input_path.as_posix()],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["contract_status"], "valid")
        self.assertEqual(before, after)
