from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

import metrics_extractor  # noqa: E402
import navigator_scope  # noqa: E402


class LoadThresholdsTests(unittest.TestCase):
    def test_defaults_returned_when_no_override_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            thresholds = metrics_extractor.load_thresholds(root)
        self.assertEqual(thresholds, metrics_extractor.DEFAULT_THRESHOLDS)
        # A copy, not the live dict: mutating the result must not corrupt defaults.
        thresholds["affected_files_standard"] = 1
        self.assertEqual(
            metrics_extractor.DEFAULT_THRESHOLDS["affected_files_standard"], 20
        )

    def test_project_override_file_is_merged_over_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / ".tailtrail"
            config_dir.mkdir()
            (config_dir / "aidlc-scope-thresholds.json").write_text(
                json.dumps({"affected_files_standard": 7}),
                encoding="utf-8",
            )
            thresholds = metrics_extractor.load_thresholds(root)
        self.assertEqual(thresholds["affected_files_standard"], 7)
        # Untouched keys keep their defaults.
        self.assertEqual(
            thresholds["cross_layer_edges_standard"],
            metrics_extractor.DEFAULT_THRESHOLDS["cross_layer_edges_standard"],
        )

    def test_malformed_override_file_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / ".tailtrail"
            config_dir.mkdir()
            (config_dir / "aidlc-scope-thresholds.json").write_text(
                "{not valid json", encoding="utf-8"
            )
            thresholds = metrics_extractor.load_thresholds(root)
        self.assertEqual(thresholds, metrics_extractor.DEFAULT_THRESHOLDS)

    def test_invalid_entries_dropped_with_warnings(self):
        clean, warnings = metrics_extractor.validate_thresholds({
            "affected_files_standard": 7,
            "call_chain_depth_stddev_standard": 2,  # int accepted for float key
            "affected_file_standard": 3,  # typo: unknown key
            "cross_layer_edges_standard": "many",
            "module_resolution_ambiguous_standard": -1,
            "behavior_chain_incomplete_standard": 1,  # not a strict bool
            "affected_files_lite_floor": True,  # bool is not a number
        })
        self.assertEqual(clean, {
            "affected_files_standard": 7,
            "call_chain_depth_stddev_standard": 2,
        })
        self.assertEqual(len(warnings), 5)

    def test_load_thresholds_keeps_defaults_for_invalid_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / ".tailtrail"
            config_dir.mkdir()
            (config_dir / "aidlc-scope-thresholds.json").write_text(
                json.dumps({
                    "affected_files_standard": 7,
                    "cross_layer_edges_standard": "many",
                    "bogus_key": 1,
                }),
                encoding="utf-8",
            )
            thresholds = metrics_extractor.load_thresholds(root)
        self.assertEqual(thresholds["affected_files_standard"], 7)
        self.assertEqual(
            thresholds["cross_layer_edges_standard"],
            metrics_extractor.DEFAULT_THRESHOLDS["cross_layer_edges_standard"],
        )
        self.assertNotIn("bogus_key", thresholds)


class CheapScopeMetricsTests(unittest.TestCase):
    def test_empty_list_is_unavailable_with_zeroed_metrics(self):
        metrics = metrics_extractor.cheap_scope_metrics([])
        self.assertFalse(metrics["available"])
        self.assertEqual(metrics["affected_files"], 0)
        self.assertEqual(metrics["changed_lines_estimate"], 0)
        self.assertEqual(metrics["source"], "likely_impacted_files_only")

    def test_populated_list_counts_files_lines_and_layers(self):
        files = [
            {"path": "src/claims_api/validation.py", "changed_lines_estimate": 30},
            {"path": "src/claims_api/models.py", "changed_lines_estimate": 12},
            {"path": "tests/test_validation.py", "changed_lines_estimate": 40},
        ]
        metrics = metrics_extractor.cheap_scope_metrics(files)
        self.assertTrue(metrics["available"])
        self.assertEqual(metrics["affected_files"], 3)
        self.assertEqual(metrics["changed_lines_estimate"], 82)
        self.assertEqual(metrics["layer_breakdown"]["src"], 2)
        self.assertEqual(metrics["layer_breakdown"]["test"], 1)
        self.assertIn("src/claims_api/validation.py", metrics["affected_paths"])


class GraphScopeMetricsTests(unittest.TestCase):
    def _scope_evidence(self):
        return {
            "candidates": [
                {
                    "candidate_id": "c1",
                    "path": "src/api.py",
                    "role": "implementation-owner",
                    "layer": "api",
                },
                {
                    "candidate_id": "c2",
                    "path": "src/service.py",
                    "role": "implementation-owner",
                    "layer": "service",
                },
                {
                    "candidate_id": "c3",
                    "path": "src/util.py",
                    "role": "inspection-only",
                    "layer": "service",
                },
            ],
            "edges": [
                {"from_candidate_id": "c1", "to_candidate_id": "c2"},
                {"from_candidate_id": "c1", "to_candidate_id": "c3"},
                {"from_candidate_id": "c2", "to_candidate_id": "c3"},
                {"from_candidate_id": "c1", "to_candidate_id": "missing"},
            ],
            "module_resolution": {
                "ambiguous_modules": [
                    {"module": "m1", "ambiguous": True},
                    {"module": "m2", "ambiguous": False},
                ]
            },
            "behavior_chains": [
                {"state": "complete", "depth": 2},
                {"state": "partial", "depth": 4},
                {"state": "broken", "depth": 2},
            ],
            "investigation": {"files_read": 5},
        }

    def test_cross_layer_edges_counted_only_between_known_distinct_layers(self):
        metrics = metrics_extractor.graph_scope_metrics(self._scope_evidence())
        # c1(api)->c2(service) and c1(api)->c3(service) are cross-layer;
        # c2->c3 is same-layer; the unknown-id edge is skipped.
        self.assertEqual(metrics["cross_layer_edges"], 2)

    def test_implementation_owner_files_only_counted_as_affected(self):
        metrics = metrics_extractor.graph_scope_metrics(self._scope_evidence())
        self.assertEqual(metrics["affected_files"], 2)
        self.assertEqual(
            metrics["affected_paths"], ["src/api.py", "src/service.py"]
        )


    def test_ambiguous_modules_incomplete_chains_and_depth_stddev(self):
        metrics = metrics_extractor.graph_scope_metrics(self._scope_evidence())
        self.assertEqual(metrics["module_resolution_ambiguous"], 1)
        self.assertTrue(metrics["behavior_chain_incomplete"])
        self.assertEqual(metrics["call_chain_depths"], [2, 4, 2])
        # Population stddev of [2, 4, 2] ≈ 0.9428
        self.assertAlmostEqual(metrics["call_chain_depth_stddev"], 0.9428, places=4)
        self.assertEqual(metrics["investigation_files_read"], 5)

    def test_non_dict_scope_evidence_is_unavailable(self):
        metrics = metrics_extractor.graph_scope_metrics("not-a-dict")
        self.assertFalse(metrics["available"])

    def test_empty_scope_evidence_yields_zeroed_but_available_metrics(self):
        metrics = metrics_extractor.graph_scope_metrics({})
        self.assertTrue(metrics["available"])
        self.assertEqual(metrics["affected_files"], 0)
        self.assertEqual(metrics["cross_layer_edges"], 0)
        self.assertFalse(metrics["behavior_chain_incomplete"])


class MapperScopeMetricsTests(unittest.TestCase):
    def test_symbols_endpoints_and_external_deps_counted_within_affected_paths(self):
        cache = {
            "graph": {
                "symbols": [
                    {"file": "src/api.py", "name": "validate_order"},
                    {"file": "src/api.py", "name": "reject_negative"},
                    {"file": "src/other.py", "name": "unrelated"},
                ],
                "endpoints": [
                    {"file": "src/api.py", "route": "/orders"},
                    {"file": "src/other.py", "route": "/other"},
                ],
                "edges": [
                    {"kind": "external_dep", "target": "requests"},
                    {"kind": "calls", "source": "src/api.py"},
                ],
            }
        }
        metrics = metrics_extractor.mapper_scope_metrics(cache, ["src/api.py"])
        self.assertTrue(metrics["available"])
        self.assertEqual(metrics["symbols_in_scope"], 2)
        self.assertEqual(metrics["endpoints_in_scope"], 1)
        self.assertEqual(metrics["external_dependency_edges"], 1)

    def test_mapper_service_edges_counted_when_in_scope(self) -> None:
        cache = {
            "graph": {
                "symbols": [],
                "endpoints": [],
                "edges": [],
                "service_edges": [
                    {"edge_type": "http-url", "source_file": "src/api.py", "target": "payments.example.com"},
                    {"edge_type": "service-config", "source_file": "src/api.py", "target": "stripe"},
                    {"edge_type": "http-url", "source_file": "src/other.py", "target": "other.example.com"},
                    {"edge_type": "dotnet-project-reference", "source_file": "src/api.py", "target": "../lib.csproj"},
                ],
            }
        }
        metrics = metrics_extractor.mapper_scope_metrics(cache, ["src/api.py"])
        # In-scope external types only; out-of-scope and repo-local refs excluded.
        self.assertEqual(metrics["external_dependency_edges"], 2)


class ComputeComplexityTests(unittest.TestCase):
    def test_tier1_only_when_no_scope_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            complexity = metrics_extractor.compute_complexity(
                [{"path": "src/a.py", "changed_lines_estimate": 10}],
                None,
                Path(tmp),
            )
        self.assertEqual(complexity["source"], "likely_impacted_files_only")
        self.assertEqual(complexity["affected_files"], 1)
        self.assertNotIn("cross_layer_edges", complexity)
        self.assertIn("thresholds", complexity)

    def test_tier2_scope_evidence_overrides_tier1(self):
        scope_evidence = {
            "candidates": [
                {"candidate_id": "c1", "path": "src/a.py", "role": "implementation-owner", "layer": "api"},
                {"candidate_id": "c2", "path": "src/b.py", "role": "implementation-owner", "layer": "service"},
            ],
            "edges": [{"from_candidate_id": "c1", "to_candidate_id": "c2"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            complexity = metrics_extractor.compute_complexity(
                [{"path": "src/a.py", "changed_lines_estimate": 10}],
                scope_evidence,
                Path(tmp),
            )
        self.assertEqual(complexity["source"], "scope_evidence")
        self.assertEqual(complexity["affected_files"], 2)
        self.assertEqual(complexity["cross_layer_edges"], 1)

    def test_tier3_mapper_enriches_when_cache_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = root / "tailtrail-meta"
            meta.mkdir()
            (meta / "code-graph-cache.json").write_text(
                json.dumps(
                    {
                        "graph": {
                            "symbols": [{"file": "src/a.py", "name": "f"}],
                            "endpoints": [],
                            "edges": [{"kind": "external_dep"}],
                        }
                    }
                ),
                encoding="utf-8",
            )
            scope_evidence = {
                "candidates": [
                    {"candidate_id": "c1", "path": "src/a.py", "role": "implementation-owner", "layer": "api"}
                ],
                "edges": [],
            }
            complexity = metrics_extractor.compute_complexity([], scope_evidence, root)
        self.assertEqual(complexity["source"], "scope_evidence+mapper")
        self.assertEqual(complexity["symbols_in_scope"], 1)
        self.assertEqual(complexity["external_dependency_edges"], 1)
        # Gate key consumed by evaluate_scope_signal (new_external_deps_standard).
        self.assertEqual(complexity["new_external_deps"], 1)

    def test_tier3_skipped_when_cached_file_changed(self) -> None:
        import hashlib

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "src" / "a.py"
            target.parent.mkdir()
            target.write_text("def f():\n    return 1\n", encoding="utf-8")
            sha = hashlib.sha256(target.read_bytes()).hexdigest()
            (root / "tailtrail-meta").mkdir()
            (root / "tailtrail-meta" / "code-graph-cache.json").write_text(
                json.dumps({
                    "source_files": {"src/a.py": {"sha256": sha, "mtime": 0, "size": 1}},
                    "graph": {"symbols": [{"file": "src/a.py", "name": "stale_name"}],
                              "endpoints": [], "edges": []},
                }),
                encoding="utf-8",
            )
            scope_evidence = {
                "candidates": [
                    {"candidate_id": "c1", "path": "src/a.py",
                     "role": "implementation-owner", "layer": "api"}
                ],
                "edges": [],
            }
            fresh = metrics_extractor.compute_complexity([], scope_evidence, root)
            self.assertEqual(fresh["source"], "scope_evidence+mapper")
            self.assertNotIn("tier3_skipped", fresh)
            target.write_text("def f():\n    return 2\n", encoding="utf-8")
            stale = metrics_extractor.compute_complexity([], scope_evidence, root)
            self.assertEqual(stale["source"], "scope_evidence")
            self.assertIn("src/a.py", stale["tier3_skipped"])
            self.assertNotIn("symbols_in_scope", stale)

    def test_tier3_skipped_when_cached_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tailtrail-meta").mkdir()
            (root / "tailtrail-meta" / "code-graph-cache.json").write_text(
                json.dumps({
                    "source_files": {"src/gone.py": {"sha256": "0" * 64}},
                    "graph": {"symbols": [], "endpoints": [], "edges": []},
                }),
                encoding="utf-8",
            )
            scope_evidence = {
                "candidates": [
                    {"candidate_id": "c1", "path": "src/gone.py",
                     "role": "implementation-owner", "layer": "api"}
                ],
                "edges": [],
            }
            complexity = metrics_extractor.compute_complexity([], scope_evidence, root)
            self.assertEqual(complexity["source"], "scope_evidence")
            self.assertIn("tier3_skipped", complexity)

    def test_new_external_deps_fires_scope_signal(self) -> None:
        complexity = {
            "affected_files": 1,
            "changed_lines_estimate": 5,
            "cross_layer_edges": 0,
            "call_chain_depth_stddev": 0.0,
            "module_resolution_ambiguous": 0,
            "new_external_deps": 1,
            "behavior_chain_incomplete": False,
            "thresholds": dict(metrics_extractor.DEFAULT_THRESHOLDS),
        }
        scope_signal, scope_floor_lite = metrics_extractor.evaluate_scope_signal(complexity)
        self.assertTrue(scope_signal)
        self.assertTrue(scope_floor_lite)

    def test_behavior_gate_respects_project_override(self) -> None:
        base = {
            "affected_files": 1,
            "changed_lines_estimate": 5,
            "cross_layer_edges": 0,
            "call_chain_depth_stddev": 0.0,
            "module_resolution_ambiguous": 0,
            "new_external_deps": 0,
            "behavior_chain_incomplete": True,
        }
        enabled = dict(base, thresholds=dict(metrics_extractor.DEFAULT_THRESHOLDS))
        self.assertTrue(metrics_extractor.evaluate_scope_signal(enabled)[0])
        disabled_thresholds = dict(metrics_extractor.DEFAULT_THRESHOLDS, behavior_chain_incomplete_standard=False)
        disabled = dict(base, thresholds=disabled_thresholds)
        self.assertFalse(metrics_extractor.evaluate_scope_signal(disabled)[0])


class ExtractScopeComplexityMetricsTests(unittest.TestCase):
    def test_non_dict_document_returns_unavailable_error_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = metrics_extractor.extract_scope_complexity_metrics(
                Path(tmp), "not-a-dict"  # type: ignore[arg-type]
            )
        self.assertFalse(result["available"])
        self.assertEqual(result["error"], "document-not-a-dict")
        self.assertIn("thresholds", result)

    def test_nested_scope_evidence_document_shape(self):
        document = {
            "likely_impacted_files": [{"path": "src/a.py", "changed_lines_estimate": 5}],
            "scope_evidence": {
                "candidates": [
                    {"candidate_id": "c1", "path": "src/a.py", "role": "implementation-owner", "layer": "api"}
                ],
                "edges": [],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = metrics_extractor.extract_scope_complexity_metrics(Path(tmp), document)
        self.assertEqual(result["source"], "scope_evidence")
        self.assertEqual(result["affected_files"], 1)

    def test_raw_scope_evidence_document_shape(self):
        document = {
            "candidates": [
                {"candidate_id": "c1", "path": "src/a.py", "role": "implementation-owner", "layer": "api"},
                {"candidate_id": "c2", "path": "src/b.py", "role": "implementation-owner", "layer": "service"},
            ],
            "edges": [{"from_candidate_id": "c1", "to_candidate_id": "c2"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = metrics_extractor.extract_scope_complexity_metrics(Path(tmp), document)
        self.assertEqual(result["source"], "scope_evidence")
        self.assertEqual(result["affected_files"], 2)
        self.assertEqual(result["cross_layer_edges"], 1)


class AssessScopeQualityComplexityIntegrationTests(unittest.TestCase):
    """Phase 4: assess_scope_quality(compute_complexity=True) must carry metrics."""

    def test_complexity_metrics_returned_even_when_scope_verdict_blocks(self):
        # A minimal document fails the fingerprint checks (blocking verdict),
        # but the complexity-metrics extraction must still run and be returned.
        document = {
            "candidates": [
                {"candidate_id": "c1", "path": "src/a.py", "role": "implementation-owner", "layer": "api"}
            ],
            "edges": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            assessment = navigator_scope.assess_scope_quality(
                Path(tmp),
                "fix a bug",
                ["bug"],
                document,
                compute_complexity=True,
            )
        self.assertTrue(assessment["blocking"])
        metrics = assessment["complexity_metrics"]
        self.assertEqual(metrics["source"], "scope_evidence")
        self.assertEqual(metrics["affected_files"], 1)
        self.assertIn("thresholds", metrics)

    def test_complexity_metrics_empty_when_not_requested(self):
        document = {"candidates": [], "edges": []}
        with tempfile.TemporaryDirectory() as tmp:
            assessment = navigator_scope.assess_scope_quality(
                Path(tmp),
                "fix a bug",
                ["bug"],
                document,
                compute_complexity=False,
            )
        self.assertEqual(assessment["complexity_metrics"], {})


class ModeDecisionLogTests(unittest.TestCase):
    """R1: calibration runway — bounded JSONL mode-decision log."""

    def _entry(self, **overrides):
        base = {
            "entry_version": 1,
            "ts": "2026-09-15T00:00:00+00:00",
            "goal_sha256": "abcdef0123456789",
            "goal_chars": 30,
            "requested_flag": None,
            "intent": "none",
            "hands_free": False,
            "keyword_signal": False,
            "scope_signal": True,
            "scope_floor_lite": False,
            "routing_selected": False,
            "selection": "scope-complexity-standard",
            "mode": "standard",
            "requested_mode": None,
            "mode_state": "local-lite",
            "metrics_source": "scope_evidence",
            "zero_metrics": False,
            "affected_files": 22,
            "changed_lines_estimate": 400,
            "cross_layer_edges": 3,
            "call_chain_depth_stddev": 1.5,
            "module_resolution_ambiguous": 0,
            "behavior_chain_incomplete": False,
            "thresholds": {"affected_files_standard": 20},
        }
        base.update(overrides)
        return base

    def test_build_entry_hashes_goal_and_never_carries_goal_text(self):
        entry = metrics_extractor.build_mode_decision_entry(
            "fix the validation bug in claims api",
            None,
            {
                "intent": "none",
                "hands_free": False,
                "keyword_signal": False,
                "scope_signal": False,
                "scope_floor_lite": True,
                "routing_selected": False,
                "complexity": {"source": "likely_impacted_files_only", "affected_files": 0},
            },
            {"selection": "default", "mode": "lite", "state": "local-lite"},
            ts="2026-09-15T00:00:00+00:00",
        )
        serialized = json.dumps(entry)
        self.assertNotIn("validation bug", serialized)
        self.assertEqual(len(entry["goal_sha256"]), 16)
        self.assertEqual(entry["goal_chars"], len("fix the validation bug in claims api"))
        self.assertTrue(entry["zero_metrics"])
        self.assertEqual(entry["mode"], "lite")

    def test_zero_metrics_false_when_scope_evidence_source(self):
        entry = metrics_extractor.build_mode_decision_entry(
            "refactor", None,
            {"intent": "none", "complexity": {"source": "scope_evidence", "affected_files": 0}},
            {"mode": "lite", "selection": "default"},
        )
        self.assertFalse(entry["zero_metrics"])


    def test_append_creates_log_and_reports_entry_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = metrics_extractor.append_mode_decision(root, self._entry())
            self.assertTrue(status["logged"])
            self.assertEqual(status["entries"], 1)
            status2 = metrics_extractor.append_mode_decision(root, self._entry())
            self.assertEqual(status2["entries"], 2)
            log = metrics_extractor.mode_decision_log_path(root)
            self.assertEqual(len(log.read_text(encoding="utf-8").strip().splitlines()), 2)

    def test_append_prunes_to_limit_keeping_most_recent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_limit = metrics_extractor.MODE_DECISION_LOG_LIMIT
            metrics_extractor.MODE_DECISION_LOG_LIMIT = 3
            try:
                for i in range(5):
                    metrics_extractor.append_mode_decision(root, self._entry(affected_files=i))
                lines = metrics_extractor.mode_decision_log_path(root).read_text(
                    encoding="utf-8"
                ).strip().splitlines()
            finally:
                metrics_extractor.MODE_DECISION_LOG_LIMIT = old_limit
            self.assertEqual(len(lines), 3)
            affected = [json.loads(line)["affected_files"] for line in lines]
            self.assertEqual(affected, [2, 3, 4])

    def test_append_survives_unwritable_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / ".tailtrail"
            blocker.write_text("not a directory", encoding="utf-8")
            status = metrics_extractor.append_mode_decision(Path(tmp), self._entry())
        self.assertFalse(status["logged"])
        self.assertIn("error", status)

    def test_summarize_empty_root_reports_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = metrics_extractor.summarize_mode_decisions(Path(tmp))
        self.assertFalse(summary["available"])
        self.assertEqual(summary["entry_count"], 0)

    def test_summarize_aggregates_calibration_critical_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entries = [
                self._entry(),
                self._entry(scope_signal=False, keyword_signal=True,
                            scope_floor_lite=False, mode="standard",
                            selection="explicit-natural-language-standard",
                            affected_files=2, thresholds={"a": 1}),
                self._entry(scope_signal=False, keyword_signal=True,
                            scope_floor_lite=True, mode="lite",
                            selection="default", affected_files=1,
                            thresholds={"a": 1}),
                self._entry(scope_signal=False, keyword_signal=False,
                            hands_free=True, mode="lite", selection="default",
                            zero_metrics=True, affected_files=0,
                            metrics_source="likely_impacted_files_only",
                            thresholds={"a": 1}),
            ]
            for entry in entries:
                metrics_extractor.append_mode_decision(root, entry)
            summary = metrics_extractor.summarize_mode_decisions(root)
        self.assertTrue(summary["available"])
        self.assertEqual(summary["entry_count"], 4)
        self.assertEqual(summary["scope_signal_count"], 1)
        self.assertEqual(summary["keyword_standard_count"], 1)
        self.assertEqual(summary["scope_floor_lite_count"], 1)
        self.assertEqual(summary["zero_metrics_count"], 1)
        self.assertEqual(summary["hands_free_count"], 1)
        self.assertEqual(summary["by_mode"], {"standard": 2, "lite": 2})
        self.assertEqual(summary["threshold_variants"], 2)

    def test_summarize_skips_malformed_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = metrics_extractor.mode_decision_log_path(root)
            log.parent.mkdir()
            log.write_text(
                "{not json}\n" + json.dumps(self._entry()) + "\n\n",
                encoding="utf-8",
            )
            summary = metrics_extractor.summarize_mode_decisions(root)
        self.assertTrue(summary["available"])
        self.assertEqual(summary["entry_count"], 1)


class ModeSelectionCalibrationWiringTests(unittest.TestCase):
    """R1: aidlc_mode_selection() must write the decision log on dual-gate paths."""

    def _load_task_start(self):
        import importlib.util

        module_path = SCRIPTS / "task-start.py"
        spec = importlib.util.spec_from_file_location("task_start_r1_test", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_dual_gate_path_appends_decision_log(self):
        task_start = self._load_task_start()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            selected = task_start.aidlc_mode_selection(
                "fix the validation bug", None, root, {"likely_impacted_files": []}, None
            )
            self.assertEqual(selected["mode"], "lite")
            log = metrics_extractor.mode_decision_log_path(root)
            self.assertTrue(log.exists())
            entry = json.loads(log.read_text(encoding="utf-8").strip())
        self.assertEqual(entry["intent"], "none")
        self.assertEqual(entry["mode"], "lite")
        self.assertIn("scope_signal", entry)
        self.assertIn("thresholds", entry)

    def test_explicit_flag_path_does_not_log(self):
        task_start = self._load_task_start()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_start.aidlc_mode_selection(
                "build the thing", "standard", root, {"likely_impacted_files": []}, None
            )
            log = metrics_extractor.mode_decision_log_path(root)
            self.assertFalse(log.exists())

    def test_selection_and_reevaluation_agree_when_behavior_gate_disabled(self):
        """Phase 6 single-definition: initial selection shares
        evaluate_scope_signal with compute_re_evaluation, so a project
        override disabling the behavior gate holds at both decision points."""
        task_start = self._load_task_start()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".tailtrail").mkdir()
            (root / ".tailtrail" / "aidlc-scope-thresholds.json").write_text(
                json.dumps({"behavior_chain_incomplete_standard": False}),
                encoding="utf-8",
            )
            plan = {
                "likely_impacted_files": [
                    {"path": "src/a.py", "changed_lines_estimate": 10}
                ],
                "scope_evidence": {
                    "candidates": [
                        {"candidate_id": "c1", "path": "src/a.py",
                         "role": "implementation-owner", "layer": "api"}
                    ],
                    "edges": [],
                    "behavior_chains": [{"state": "partial", "depth": 2}],
                },
            }
            selected = task_start.aidlc_mode_selection(
                "fix the validation bug", None, root, plan, None
            )
            # Behavior is the only signal and the project disabled its gate.
            self.assertEqual(selected["mode"], "lite")
            self.assertEqual(selected["selection"], "default")
            complexity = metrics_extractor.compute_complexity(
                plan["likely_impacted_files"], plan["scope_evidence"], root
            )
            self.assertTrue(complexity["behavior_chain_incomplete"])
            self.assertEqual(
                metrics_extractor.evaluate_scope_signal(complexity), (False, True)
            )
            self.assertIsNone(metrics_extractor.compute_re_evaluation(
                "lite", complexity, complexity_available=True
            ))


class CalibrationReviewCliTests(unittest.TestCase):
    def _run(self, root: Path, *argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = metrics_extractor.main(["--root", root.as_posix(), *argv])
        return code, buffer.getvalue()

    def test_thresholds_reports_effective_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".tailtrail").mkdir()
            (root / ".tailtrail" / "aidlc-scope-thresholds.json").write_text(
                json.dumps({"affected_files_standard": 7, "bogus_key": 1}),
                encoding="utf-8",
            )
            code, text = self._run(root, "thresholds")
            self.assertEqual(code, 0)
            self.assertIn("`affected_files_standard`: `7` (override)", text)
            self.assertIn("bogus_key", text)
            code, raw = self._run(root, "thresholds", "--format", "json")
            self.assertEqual(code, 0)
            payload = json.loads(raw)
            self.assertEqual(payload["effective_thresholds"]["affected_files_standard"], 7)
            self.assertTrue(payload["override_present"])
            self.assertTrue(
                any("bogus_key" in warning for warning in payload["override_warnings"])
            )

    def test_calibration_reviews_logged_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metrics_extractor.append_mode_decision(root, {
                "scope_signal": True, "keyword_signal": False,
                "scope_floor_lite": False, "mode": "standard",
            })
            code, text = self._run(root, "calibration")
            self.assertEqual(code, 0)
            self.assertIn("Decisions logged: `1`", text)
            self.assertIn("Scope-signal escalations: `1`", text)

    def test_calibration_empty_log_notes_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, text = self._run(Path(tmp), "calibration")
            self.assertEqual(code, 0)
            self.assertIn("Decisions logged: `0`", text)
            self.assertIn("No decisions logged yet", text)


if __name__ == "__main__":
    unittest.main()
