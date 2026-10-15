from __future__ import annotations

import base64
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import host_contract as HC  # noqa: E402


def _contract(**overrides):
    base = {
        "schema_version": "1",
        "type": "tailtrail-host-input-contract",
        "run_id": "",
        "contract_id": "ctr-01",
        "profile": "new feature",
        "change_intent": "new-capability",
        "request_mode": "implementation",
        "behavior_surface": "cli-contract",
        "paths": [
            {"path": "src/work.py", "role": "existing-implementation-owner"},
            {"path": "tests/test_work.py", "role": "existing-proof-path"},
        ],
        "criteria": {"positive": ["work ships"], "negative": ["nothing else breaks"]},
        "proof": {"command": "pytest tests/test_work.py", "tiers": ["unit"]},
        "private_reasoning_excluded": True,
    }
    base.update(overrides)
    return base


class ContractValidationTests(unittest.TestCase):
    def test_accepted_contract_binds_goal_and_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = HC.validate(_contract(), root=root, goal="ship work")
            second = HC.validate(_contract(), root=root, goal="ship other work")
        self.assertEqual(first["state"], "accepted")
        validated = first["validated"]
        self.assertTrue(validated["fingerprint"].startswith("sha256:"))
        self.assertNotEqual(first["validated"]["fingerprint"], second["validated"]["fingerprint"])
        self.assertEqual(validated["run_id_binding"], "unbound")

    def test_insufficient_when_fields_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = HC.validate({"type": "tailtrail-host-input-contract"}, root=Path(temp), goal="g")
        self.assertEqual(result["state"], "insufficient")
        self.assertIn("request_mode", result["open_fields"])
        self.assertIn("paths", result["open_fields"])

    def test_implementation_without_owner_is_insufficient(self) -> None:
        contract = _contract(paths=[{"path": "tests/test_work.py", "role": "existing-proof-path"}])
        with tempfile.TemporaryDirectory() as temp:
            result = HC.validate(contract, root=Path(temp), goal="g")
        self.assertEqual(result["state"], "insufficient")

    def test_read_only_with_owner_is_contradicted(self) -> None:
        contract = _contract(request_mode="read-only")
        with tempfile.TemporaryDirectory() as temp:
            result = HC.validate(contract, root=Path(temp), goal="g")
        self.assertEqual(result["state"], "contradicted")
        self.assertTrue(result["conflicts"])

    def test_same_path_both_authorities_is_contradicted(self) -> None:
        contract = _contract(paths=[
            {"path": "src/work.py", "role": "existing-implementation-owner"},
            {"path": "src/work.py", "role": "existing-proof-path"},
        ])
        with tempfile.TemporaryDirectory() as temp:
            result = HC.validate(contract, root=Path(temp), goal="g")
        self.assertEqual(result["state"], "contradicted")

    def test_correction_requires_premise(self) -> None:
        contract = _contract(change_intent="correction")
        with tempfile.TemporaryDirectory() as temp:
            result = HC.validate(contract, root=Path(temp), goal="g")
        self.assertEqual(result["state"], "insufficient")
        self.assertIn("correction_premise", result["open_fields"])


class ContractTransportTests(unittest.TestCase):
    def test_inline_file_base64_converge(self) -> None:
        payload = _contract()
        inline = HC.parse_transport(inline=json.dumps(payload))
        encoded = HC.parse_transport(encoded=base64.b64encode(json.dumps(payload).encode()).decode("ascii"))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "contract.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            from_file = HC.parse_transport(path=str(path))
        self.assertEqual(inline, encoded)
        self.assertEqual(inline["contract_id"], from_file["contract_id"])

    def test_exactly_one_transport(self) -> None:
        with self.assertRaises(ValueError):
            HC.parse_transport()
        with self.assertRaises(ValueError):
            HC.parse_transport(inline="{}", encoded="e30=")


class ContractTaskTypeConsistencyTests(unittest.TestCase):
    def _load_start(self):
        spec = importlib.util.spec_from_file_location(
            "contract_start_check", ROOT / "scripts" / "task-start.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def test_task_type_conflict_is_contradicted(self) -> None:
        start = self._load_start()
        with tempfile.TemporaryDirectory() as temp:
            args = SimpleNamespace(task_type="implementation", host_contract=json.dumps(_contract(request_mode="read-only")),
                                   host_contract_file=None, host_contract_base64=None)
            with self.assertRaises(start._HostContractBlocked) as blocked:
                start.resolve_host_contract(args, Path(temp), "goal")
        self.assertEqual(blocked.exception.result["state"], "contradicted")

    def test_accepted_contract_resolves(self) -> None:
        start = self._load_start()
        with tempfile.TemporaryDirectory() as temp:
            args = SimpleNamespace(task_type=None, host_contract=json.dumps(_contract()),
                                   host_contract_file=None, host_contract_base64=None)
            validated = start.resolve_host_contract(args, Path(temp), "goal")
        self.assertEqual(validated["request_mode"], "implementation")


class ContractProofProjectionTests(unittest.TestCase):
    def _load_start(self):
        spec = importlib.util.spec_from_file_location(
            "contract_proof_start", ROOT / "scripts" / "task-start.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def _validated(self, root: Path, **overrides):
        contract = _contract(**overrides)
        return {
            "contract_id": "ctr-01", "request_mode": "implementation",
            "paths": [
                {"path": item["path"], "role": item["role"]}
                for item in contract["paths"]
            ],
            "criteria": contract["criteria"],
            "proof": dict(contract["proof"]),
            "fingerprint": "sha256:" + "0" * 64,
        }

    def _row(self):
        return {
            "display_id": "REQ-01",
            "acceptance_criteria": ["Done."],
            "preserve_rules": ["Keep scope."],
            "likely_paths": ["src/work.py"],
            "validation_contract": {"state": "required", "tiers": ["unit"]},
        }

    def test_single_row_projects_command_and_criteria(self) -> None:
        start = self._load_start()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tests").mkdir()
            (root / "tests" / "test_work.py").write_text("x = 1\n", encoding="utf-8")
            rows = [self._row()]
            focused = [{
                "tier": "unit", "tiers": ["unit"], "candidate": "tests/test_work.py",
                "command": "pytest tests/test_work.py", "status": "planned",
                "candidate_state": "existing",
            }]
            out = start.apply_host_contract_proof(root, rows, focused, self._validated(root))
        self.assertEqual(len(out), 2)
        injected = out[1]
        self.assertEqual(injected["command"], "pytest tests/test_work.py")
        self.assertEqual(injected["tiers"], ["unit"])
        self.assertEqual(injected["candidate_state"], "existing")
        self.assertIn("work ships", rows[0]["acceptance_criteria"])
        self.assertIn("nothing else breaks", rows[0]["preserve_rules"])
        self.assertEqual(rows[0]["likely_paths"], ["src/work.py"])
        self.assertEqual(rows[0]["host_contract_proof"]["contract_id"], "ctr-01")

    def test_attach_compiles_contract_command_into_checks(self) -> None:
        start = self._load_start()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tests").mkdir()
            (root / "tests" / "test_work.py").write_text("x = 1\n", encoding="utf-8")
            rows = [self._row()]
            focused = [{
                "tier": "unit", "tiers": ["unit"], "candidate": "tests/test_work.py",
                "command": "pytest tests/test_other.py", "status": "planned",
                "candidate_state": "existing",
            }]
            out = start.apply_host_contract_proof(root, rows, focused, self._validated(root))
            start.attach_focused_validation_contracts(rows, out)
        contract = rows[0]["validation_contract"]
        self.assertIn("pytest tests/test_work.py", contract["commands"])
        self.assertTrue(any(
            check["command"] == "pytest tests/test_work.py" and check["tiers"] == ["unit"]
            for check in contract["checks"]
        ))

    def test_multi_row_plans_keep_contract_recorded_only(self) -> None:
        start = self._load_start()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = [self._row(), dict(self._row(), display_id="REQ-02")]
            focused = [{"tier": "unit"}]
            out = start.apply_host_contract_proof(root, rows, focused, self._validated(root))
        self.assertEqual(out, focused)
        self.assertNotIn("host_contract_proof", rows[0])

    def test_non_command_proof_and_none_are_noops(self) -> None:
        start = self._load_start()
        with tempfile.TemporaryDirectory() as temp:
            rows = [self._row()]
            focused = [{"tier": "unit"}]
            repro = self._validated(Path(temp))
            repro["proof"] = {"reproduction_binding": "r", "post_change_binding": "p"}
            self.assertEqual(start.apply_host_contract_proof(Path(temp), rows, focused, repro), focused)
            self.assertEqual(start.apply_host_contract_proof(Path(temp), rows, focused, None), focused)

    def test_missing_proof_file_is_proposed_not_existing(self) -> None:
        start = self._load_start()
        with tempfile.TemporaryDirectory() as temp:
            rows = [self._row()]
            out = start.apply_host_contract_proof(
                Path(temp), rows, [], self._validated(Path(temp),
                    paths=[{"path": "tests/test_new.py", "role": "proposed-proof-path"}]),
            )
        self.assertEqual(out[0]["candidate_state"], "proposed")


if __name__ == "__main__":
    unittest.main()
