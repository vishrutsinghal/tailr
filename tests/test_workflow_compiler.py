from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lock = load("workflow_compiler_lock_test", "scripts/planning-lock.py")
from workflow_runtime import capabilities, compiler, ownership, templates


class WorkflowCompilerTests(unittest.TestCase):
    def _workflow(self, root: Path, run_id: str = "compiler-run", workflow_id: str = "ttw-compiler-run", feature_ids: list[str] | None = None) -> str:
        lock.create(root, "description does not belong in compiler hash", run_id)
        lock.save_start_report(root, run_id, {"goal": "description does not belong in compiler hash", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"requirement_matrix": [{"display_id": "REQ-01", "statement": "Reject invalid values", "kind": "change", "acceptance_criteria": ["Invalid values are rejected"], "preserve_rules": ["Valid values remain valid"], "likely_paths": ["src/validation.py"], "evidence_plan": ["focused test"]}]}})
        lock.activate(root, run_id, True); ownership.bind(root, run_id, workflow_id)
        capabilities.propose(root, workflow_id, feature_ids or ["code-graph-mapper", "requirement-completion-harness", "evidence-aware-testing", "review"])
        return workflow_id

    def test_compiler_schemas_are_closed(self) -> None:
        plan = json.loads((ROOT / "schemas" / "workflow-compiler-plan.schema.json").read_text(encoding="utf-8"))
        policy = json.loads((ROOT / "schemas" / "workflow-compiler-policy.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(plan["additionalProperties"]); self.assertFalse(policy["additionalProperties"])
        self.assertEqual(plan["properties"]["type"]["const"], "tailtrail-workflow-compiler-plan")

    def test_all_twelve_steps_compile_a_frozen_small_change_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._workflow(root)
            result = compiler.compile(root, workflow_id); validation = compiler.validate(root, workflow_id)

        self.assertEqual(result["template_id"], "small-change")
        self.assertEqual(len(result["compiler_trace"]), 12)
        self.assertEqual(result["stages"][0]["stage_id"], "bootstrap")
        self.assertEqual(result["stages"][0]["adapter_id"], "bootstrap")
        self.assertEqual(result["stages"][0]["adapter_action_class"], "read_local")
        self.assertEqual(next(row for row in result["stages"] if row["stage_id"] == "implement")["adapter_action_class"], "write_project")
        self.assertTrue(all(stage["execution_authority"] == "typed-adapter-executor" for stage in result["stages"]))
        self.assertTrue(validation["valid"])

    def test_each_compiler_step_has_a_stable_trace_slot(self) -> None:
        expected = ["validate-plan", "resolve-features", "reject-conflicts", "select-template", "apply-policy", "resolve-graph", "merge-duplicates", "approval-classes", "attach-references", "freeze-hash", "approval-questions", "execution-boundary"]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._workflow(root)
            trace = compiler.compile(root, workflow_id)["compiler_trace"]
        for step in expected:
            with self.subTest(step=step): self.assertIn(step, trace)

    def test_unknown_or_policy_forbidden_capability_fails_closed(self) -> None:
        registry = {"review": {"status": "implemented"}}
        with self.assertRaisesRegex(ValueError, "unavailable"):
            compiler._validate_features({"unknown"}, registry, {"required_capabilities": [], "forbidden_capabilities": [], "stage_prerequisites": {}})
        with self.assertRaisesRegex(ValueError, "forbids"):
            compiler._validate_features({"review"}, registry, {"required_capabilities": [], "forbidden_capabilities": ["review"], "stage_prerequisites": {}})

    def test_graph_cycle_and_incompatible_duplicate_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "cycle"):
            templates.resolve_graph([{"stage_id": "one", "prerequisites": ["two"]}, {"stage_id": "two", "prerequisites": ["one"]}])
        with self.assertRaisesRegex(ValueError, "incompatible"):
            templates.merge_stages([{"stage_id": "review", "capability_id": "review", "prerequisites": [], "evidence": ["a"]}, {"stage_id": "review", "capability_id": "testing", "prerequisites": [], "evidence": ["b"]}])

    def test_compatible_duplicate_merges_evidence_deterministically(self) -> None:
        merged = templates.merge_stages([{"stage_id": "review", "capability_id": "review", "prerequisites": ["tests"], "evidence": ["a"]}, {"stage_id": "review", "capability_id": "review", "prerequisites": ["tests"], "evidence": ["b", "a"]}])
        self.assertEqual(merged[0]["evidence"], ["a", "b"])

    def test_contradictory_features_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "contradictory"):
            compiler._validate_features({"aidlc-off", "aidlc-standard"}, {}, {"required_capabilities": [], "forbidden_capabilities": [], "stage_prerequisites": {}})

    def test_policy_stage_change_creates_revision_while_description_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._workflow(root)
            first = compiler.compile(root, workflow_id)
            saved_lock = root / ".tailtrail" / "runs" / "compiler-run" / "planning" / "lock-v1.json"
            payload = json.loads(saved_lock.read_text(encoding="utf-8")); payload["goal"] = "a different description only"; saved_lock.write_text(json.dumps(payload), encoding="utf-8")
            unchanged = compiler.compile(root, workflow_id)
            policy = {"schema_version": "1", "type": "tailtrail-workflow-compiler-policy", "required_capabilities": ["aidlc"], "forbidden_capabilities": [], "stage_prerequisites": {}}
            compiler.policy_path(root).parent.mkdir(parents=True, exist_ok=True); compiler.policy_path(root).write_text(json.dumps(policy), encoding="utf-8")
            revised = compiler.compile(root, workflow_id)

        self.assertEqual(first["plan_fingerprint"], unchanged["plan_fingerprint"])
        self.assertEqual(unchanged["status"], "unchanged")
        self.assertNotEqual(first["plan_fingerprint"], revised["plan_fingerprint"])
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(revised["template_id"], "delivery")

    def test_public_cli_compiles_and_validates_without_project_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._workflow(root, "compiler-cli", "ttw-compiler-cli")
            plan = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "compile", "plan", "--root", root.as_posix(), "--workflow-id", workflow_id], cwd=ROOT, text=True, capture_output=True, check=False)
            validate = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "compile", "validate", "--root", root.as_posix(), "--workflow-id", workflow_id], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
        self.assertEqual(json.loads(plan.stdout)["status"], "compiled")
        self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
        self.assertTrue(json.loads(validate.stdout)["valid"])
        body = (ROOT / "scripts" / "workflow_runtime" / "compiler.py").read_text(encoding="utf-8")
        self.assertNotIn("subprocess", body); self.assertNotIn("run_script(", body)


if __name__ == "__main__":
    unittest.main()
