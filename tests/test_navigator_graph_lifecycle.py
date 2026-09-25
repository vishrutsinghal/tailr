from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

from workflow_runtime import contracts  # noqa: E402


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


graph = load("navigator_graph_lifecycle_test", "scripts/navigator_graph_lifecycle.py")
scope = load("navigator_graph_scope_test", "scripts/navigator_scope.py")


class NavigatorGraphLifecycleTests(unittest.TestCase):
    def write(self, root: Path, relative: str, body: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_auto_creates_reuses_and_incrementally_refreshes_typescript_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            owner = self.write(
                root,
                "src/trace/deploymentService.ts",
                'export function trace() { throw new Error("CloudWatch trace endpoint is not configured."); }\n',
            )
            self.write(root, "src/trace/Page.tsx", "import { trace } from './deploymentService';\nexport function Page(){ return trace(); }\n")
            goal = "remove the banner **CloudWatch trace endpoint is not configured.**"

            created = graph.manage(root, goal, mode="auto", attempt_id="run-1")
            cache_path = root / "tailtrail-meta" / "code-graph-cache.json"
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            reused = graph.manage(root, goal, mode="auto", attempt_id="run-2")
            owner.write_text('export function trace() { throw new Error("CloudWatch trace endpoint is disabled."); }\n', encoding="utf-8")
            refreshed = graph.manage(root, goal, ["src/trace/deploymentService.ts"], mode="auto", attempt_id="run-3")

        self.assertEqual(created["action"], "create")
        lifecycle_schema = json.loads((ROOT / "schemas" / "navigator-graph-lifecycle.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(contracts.validate_document(created, lifecycle_schema), [])
        self.assertTrue(created["written"])
        self.assertEqual(created["target_paths"], ["src/trace/deploymentService.ts"])
        self.assertEqual(cached["language_profiles"]["typescript"]["files"], 1)
        self.assertEqual(reused["action"], "reuse")
        self.assertFalse(reused["written"])
        self.assertEqual(refreshed["action"], "refresh")
        self.assertTrue(refreshed["written"])
        self.assertEqual(refreshed["after_status"]["status"], "fresh")

    def test_anchor_slice_reuse_records_fresh_relevant(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "src/a.py", "from src.b import thing\ndef run():\n    return thing()\n")
            self.write(root, "src/b.py", "def thing():\n    return 1\n")
            anchors = [
                {"anchor_id": "anchor:entrypoint:src/a.py", "role": "entrypoint",
                 "path": "src/a.py", "confidence": "high", "reason_codes": ["anchor-exact"],
                 "evidence_refs": {}},
            ]
            aslice = scope.anchor_slice(anchors)
            created = graph.manage(root, "run thing", ["src/a.py"], mode="auto", attempt_id="run-1", anchor_slice=aslice)
            reused = graph.manage(
                root, "run thing", ["src/a.py"], mode="auto", attempt_id="run-2", anchor_slice=aslice
            )
        self.assertEqual(created["cache_reuse_state"], "missing-missing")
        self.assertEqual(reused["action"], "reuse")
        self.assertEqual(reused["cache_reuse_state"], "fresh-relevant")
        self.assertEqual(reused["freshness"], "fresh")
        self.assertEqual(reused["relevance"], "relevant")
        lifecycle_schema = json.loads((ROOT / "schemas" / "navigator-graph-lifecycle.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(contracts.validate_document(reused, lifecycle_schema), [])

    def test_fresh_insufficient_extends_without_unconnected_lexical(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "src/a.py", "from src.b import thing\ndef run():\n    return thing()\n")
            self.write(root, "src/b.py", "def thing():\n    return 1\n")
            self.write(root, "src/c.py", "def solo():\n    return 0\n")
            self.write(root, "src/other.py", "def wobble():\n    return 2\n")
            graph.manage(root, "run thing", ["src/a.py"], mode="auto", attempt_id="run-1")
            anchors = [
                {"anchor_id": "anchor:entrypoint:src/c.py", "role": "entrypoint",
                 "path": "src/c.py", "confidence": "high", "reason_codes": ["anchor-exact"],
                 "evidence_refs": {}},
            ]
            aslice = scope.anchor_slice(anchors)
            extended = graph.manage(
                root, "fix the wobble", mode="auto", attempt_id="run-2", anchor_slice=aslice
            )
        self.assertEqual(extended["cache_reuse_state"], "fresh-insufficient")
        self.assertEqual(extended["action"], "refresh")
        self.assertEqual(sorted(extended["target_paths"]), ["src/c.py"])
        self.assertNotIn("src/other.py", extended["target_paths"])
        lifecycle_schema = json.loads((ROOT / "schemas" / "navigator-graph-lifecycle.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(contracts.validate_document(extended, lifecycle_schema), [])

    def test_fresh_unrelated_slice_defers_instead_of_reusing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "src/a.py", "def a():\n    return 1\n")
            self.write(root, "src/c.py", "def solo():\n    return 0\n")
            home = scope.anchor_slice([{
                "anchor_id": "anchor:entrypoint:src/a.py", "role": "entrypoint",
                "path": "src/a.py", "confidence": "high", "reason_codes": ["anchor-exact"],
                "evidence_refs": {},
            }])
            graph.manage(root, "cover a", ["src/a.py"], mode="auto", attempt_id="run-1", anchor_slice=home)
            away = scope.anchor_slice([{
                "anchor_id": "anchor:entrypoint:src/c.py", "role": "entrypoint",
                "path": "src/c.py", "confidence": "high", "reason_codes": ["anchor-exact"],
                "evidence_refs": {},
            }])
            held = graph.manage(root, "cover a", ["src/a.py"], mode="reuse", attempt_id="run-2", anchor_slice=away)
        self.assertEqual(held["cache_reuse_state"], "fresh-insufficient")
        self.assertEqual(held["action"], "defer")
        self.assertNotIn("src/a.py", held["target_paths"])

    def test_partial_slice_extends_cached_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "src/a.py", "def a():\n    return 1\n")
            self.write(root, "src/c.py", "def solo():\n    return 0\n")
            home = scope.anchor_slice([{
                "anchor_id": "anchor:entrypoint:src/a.py", "role": "entrypoint",
                "path": "src/a.py", "confidence": "high", "reason_codes": ["anchor-exact"],
                "evidence_refs": {},
            }])
            graph.manage(root, "cover a", ["src/a.py"], mode="auto", attempt_id="run-1", anchor_slice=home)
            away = scope.anchor_slice([{
                "anchor_id": "anchor:entrypoint:src/c.py", "role": "entrypoint",
                "path": "src/c.py", "confidence": "high", "reason_codes": ["anchor-exact"],
                "evidence_refs": {},
            }])
            extended = graph.manage(root, "cover c", mode="auto", attempt_id="run-2", anchor_slice=away)
            import code_graph_cache
            final, _ = code_graph_cache.read_container(root / "tailtrail-meta" / "code-graph-cache.json")
        self.assertEqual(extended["action"], "refresh")
        self.assertEqual(sorted(extended["target_paths"]), ["src/c.py"])
        self.assertIn("src/a.py", final["mapper_graph"]["scope"])
        self.assertIn("src/c.py", final["mapper_graph"]["scope"])

    def test_outside_slice_nomination_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "src/a.py", "def a():\n    return 1\n")
            self.write(root, "src/outside.py", "def outside():\n    return 9\n")
            home = scope.anchor_slice([{
                "anchor_id": "anchor:entrypoint:src/a.py", "role": "entrypoint",
                "path": "src/a.py", "confidence": "high", "reason_codes": ["anchor-exact"],
                "evidence_refs": {},
            }])
            graph.manage(root, "cover a", ["src/a.py"], mode="auto", attempt_id="run-1", anchor_slice=home)
            result = graph.manage(
                root, "cover a", ["src/a.py", "src/outside.py"],
                mode="auto", attempt_id="run-2", anchor_slice=home,
            )
        self.assertEqual(result["outside_slice_nominations"],
                         [{"path": "src/outside.py", "reason": "outside-anchor-slice"}])
        self.assertNotIn("src/outside.py", result["target_paths"])
        lifecycle_schema = json.loads((ROOT / "schemas" / "navigator-graph-lifecycle.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(contracts.validate_document(result, lifecycle_schema), [])

    def test_receipt_reports_cache_shape_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "src/a.py", "def a():\n    return 1\n")
            created = graph.manage(root, "cover a with a test", ["src/a.py"], mode="auto", attempt_id="run-1")
            reused = graph.manage(root, "cover a with a test", ["src/a.py"], mode="auto", attempt_id="run-2")
        for receipt in (created, reused):
            self.assertIn(receipt["cache_shape"], {"missing", "phase1", "mapper", "combined", "invalid"})
            self.assertIsInstance(receipt["cache_warnings"], list)
        self.assertEqual(reused["cache_shape"], "mapper")
        lifecycle_schema = json.loads((ROOT / "schemas" / "navigator-graph-lifecycle.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(contracts.validate_document(created, lifecycle_schema), [])
        self.assertEqual(contracts.validate_document(reused, lifecycle_schema), [])

    def test_plain_error_clause_is_treated_as_an_exact_literal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(
                root,
                "src/deploymentService.ts",
                'throw new Error("CloudWatch trace endpoint is not configured.");\n',
            )
            result = graph.manage(
                root,
                "there is a banner CloudWatch trace endpoint is not configured. we need to remove it",
                mode="auto",
            )
        self.assertEqual(result["target_paths"], ["src/deploymentService.ts"])
        self.assertIn("exact-user-literal-match", result["reason_codes"])

    def test_markdown_literal_variants_select_the_same_graph_scope(self) -> None:
        variants = [
            "*CloudWatch trace endpoint is not configured.*",
            "_CloudWatch trace endpoint is not configured._",
            "**CloudWatch trace endpoint is not configured.**",
            "__CloudWatch trace endpoint is not configured.__",
            "`CloudWatch trace endpoint is not configured.`",
            "'CloudWatch trace endpoint is not configured.'",
            '"CloudWatch trace endpoint is not configured."',
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(
                root,
                "src/deploymentService.ts",
                'throw new Error("CloudWatch trace endpoint is not configured.");\n',
            )
            results = [
                graph.manage(
                    root,
                    f"there is a banner {literal} we need to remove it",
                    mode="auto",
                )
                for literal in variants
            ]

        self.assertTrue(all(
            result["target_paths"] == ["src/deploymentService.ts"]
            for result in results
        ))
        self.assertTrue(all(
            "exact-user-literal-match" in result["reason_codes"]
            for result in results
        ))

    def test_off_never_writes_graph_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "src/service.py", "def service():\n    return True\n")
            result = graph.manage(root, "change service", mode="off")
            exists = (root / "tailtrail-meta" / "code-graph-cache.json").exists()
        self.assertEqual(result["action"], "off")
        self.assertFalse(result["written"])
        self.assertFalse(exists)

    def test_auto_defers_creation_when_navigator_has_no_relevant_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "src/service.py", "def service():\n    return True\n")
            result = graph.manage(root, "investigate the unusual concern", mode="auto")
            exists = (root / "tailtrail-meta" / "code-graph-cache.json").exists()
        self.assertEqual(result["action"], "defer")
        self.assertIn("no-relevant-graph-scope", result["reason_codes"])
        self.assertFalse(result["written"])
        self.assertFalse(exists)

    def test_debug_start_auto_is_reuse_only_and_does_not_scan_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(
                root,
                "src/deploymentService.ts",
                'throw new Error("CloudWatch trace endpoint is not configured.");\n',
            )
            result = graph.manage(
                root,
                "debug CloudWatch trace endpoint is not configured",
                mode="reuse",
                phase="debug-start",
            )
        self.assertEqual(result["action"], "defer")
        self.assertEqual(result["target_paths"], [])
        self.assertIn("debug-start-reuse-only", result["reason_codes"])
        self.assertFalse(result["written"])

    def test_only_complete_hash_fresh_run_mappings_are_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.write(root, "src/orders/service.py", "def submit():\n    return True\n")
            evidence = {
                "decision_fingerprint": "sha256:" + "a" * 64,
                "requirements": [{"implementation_owners": ["src/orders/service.py"], "inspection_paths": [], "proof_paths": []}],
            }
            lifecycle = {"cache_fingerprint": "sha256:" + "b" * 64}
            graph.record_run_mapping(root, "complete", "change order submit", evidence, ["src/orders/service.py"], "complete", lifecycle)
            graph.record_run_mapping(root, "incomplete", "change order submit", evidence, ["src/orders/service.py"], "evidence-incomplete", lifecycle)
            graph.record_run_mapping(root, "complete", "change order submit", evidence, ["src/orders/service.py"], "evidence-incomplete", lifecycle)
            repeated = graph.record_run_mapping(root, "complete", "change order submit", evidence, ["src/orders/service.py"], "complete", lifecycle)
            mapping_index = json.loads((root / "tailtrail-meta" / "navigator-run-mappings-v1.json").read_text(encoding="utf-8"))
            mapping_schema = json.loads((ROOT / "schemas" / "navigator-run-mapping-index.schema.json").read_text(encoding="utf-8"))
            fresh = graph.relevant_mapping_paths(root, "fix order submit")
            path.write_text("def submit():\n    return False\n", encoding="utf-8")
            stale = graph.relevant_mapping_paths(root, "fix order submit")
        self.assertEqual(fresh, ["src/orders/service.py"])
        self.assertEqual(stale, [])
        self.assertEqual(len(mapping_index["mappings"]), 3)
        self.assertEqual(repeated, mapping_index["mappings"][0])
        self.assertEqual(contracts.validate_document(mapping_index, mapping_schema), [])

    def test_start_auto_graph_traces_bold_ui_literal_to_renderer_and_binds_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(
                root,
                "src/trace/deploymentService.ts",
                'export function trace() { throw new Error("CloudWatch trace endpoint is not configured."); }\n',
            )
            self.write(
                root,
                "src/trace/TracePage.tsx",
                "import { useState } from 'react';\n"
                "import { trace } from './deploymentService';\n"
                "export function TracePage() {\n"
                "  const [error, setError] = useState('');\n"
                "  function load() { try { trace(); } catch (value) { setError(value instanceof Error ? value.message : 'Trace unavailable'); } }\n"
                "  return <main><button onClick={load}>Load</button>{error && <aside>{error}</aside>}</main>;\n"
                "}\n",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "task-start.py").as_posix(),
                    "remove banner **CloudWatch trace endpoint is not configured.**",
                    "--root", root.as_posix(), "--planning-run-id", "graph-start", "--format", "json",
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["graph_lifecycle"]["action"], "create")
        self.assertEqual(
            payload["navigator"]["scope_evidence"]["requirements"][0]["implementation_owners"],
            ["src/trace/TracePage.tsx"],
        )
        self.assertEqual(
            payload["navigator"]["scope_evidence"]["requirements"][0]["inspection_paths"],
            ["src/trace/deploymentService.ts"],
        )
        self.assertEqual(
            payload["planning_lock"]["scope_decision"]["graph_lifecycle"]["fingerprint"],
            payload["graph_lifecycle"]["fingerprint"],
        )

    def test_graph_seed_without_task_specific_relationship_is_not_an_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "src/unrelated.ts", "export function unrelated() { return true; }\n")
            candidates = scope.candidates_from_seeds(
                root,
                [scope.seed("src/unrelated.ts", "fresh-graph", "review-graph-suggested-read")],
                ["bug"],
            )
        self.assertEqual(candidates[0]["status"], "inspection-only")
        self.assertEqual(candidates[0]["confidence"], "medium")
        self.assertIn("graph-seed-needs-task-specific-evidence", candidates[0]["reason_codes"])

    def test_large_persistent_graph_uses_only_the_current_task_slice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = "src/trace/deploymentService.ts"
            self.write(
                root,
                target,
                'export function trace() { throw new Error("CloudWatch trace endpoint is not configured."); }\n',
            )
            paths = [target]
            for index in range(45):
                relative = f"src/unrelated/module_{index:02d}.ts"
                self.write(root, relative, f"export const module{index} = {index};\n")
                paths.append(relative)
            graph.manage(root, "build repository graph", paths, mode="rebuild")
            frames = [{
                "requirement_id": "req-cloudwatch",
                "display_id": "REQ-01",
                "statement": "Remove banner **CloudWatch trace endpoint is not configured.**",
                "query_terms": ["cloudwatch", "trace", "endpoint", "configured"],
            }]
            candidates = scope.candidates_from_seeds(
                root,
                [scope.seed(target, "lexical-body", "exact-phrase-in-bounded-body")],
                ["bug"],
            )
            rows, _edges, investigation = scope.investigate(root, frames, candidates, ["bug"])
            evidence = scope.evidence_document(
                root,
                frames[0]["statement"],
                frames,
                rows,
                investigation=investigation,
            )
            evidence_schema = json.loads(
                (ROOT / "schemas" / "navigator-scope-evidence.schema.json").read_text(encoding="utf-8")
            )

        owners = [row["path"] for row in rows if row.get("status") == "included"]
        self.assertEqual(owners, [target])
        self.assertEqual(investigation["cache"]["status"], "fresh")
        self.assertLessEqual(investigation["cache"]["selected_paths"], 2)
        self.assertNotEqual(investigation["stop_reason"], "file-read-limit-reached")
        self.assertEqual(contracts.validate_document(evidence, evidence_schema), [])


if __name__ == "__main__":
    unittest.main()
