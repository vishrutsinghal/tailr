from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "scripts").as_posix())
SPEC = importlib.util.spec_from_file_location("tailtrail_debug_preflight_test", ROOT / "scripts" / "debug-preflight.py")
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class DebugPreflightTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        (root / "tests" / "e2e").mkdir(parents=True)
        (root / "conftest.py").write_text(
            "def _feature_steps(feature, scenario):\n"
            "    steps = list(feature.background.steps)\n"
            "    steps.extend(scenario.steps)\n"
            "    return steps\n\n"
            "def pytest_html_results_table_row(report):\n"
            "    return report._bdd_steps\n",
            encoding="utf-8",
        )
        (root / "tests" / "e2e" / "conftest.py").write_text(
            "# Reporting hooks moved to the repository conftest.\n", encoding="utf-8"
        )
        (root / "tests" / "test_html_reporting.py").write_text(
            "import conftest\n\n"
            "def test_background_steps_are_not_duplicated():\n"
            "    assert ['Given a', 'When b', 'Then c'] == ['Given a', 'When b', 'Then c']\n",
            encoding="utf-8",
        )
        (root / "tests" / "e2e" / "test_pipeline_steps.py").write_text(
            "def test_background_steps_execute():\n    assert True\n", encoding="utf-8"
        )
        (root / "requirements.txt").write_text("pytest-bdd>=8.1.0\npytest-html>=4\n", encoding="utf-8")
        (root / "pyproject.toml").write_text(
            "[project]\ndependencies = ['pytest-bdd>=7.0,<8.0', 'pytest-html>=4']\n", encoding="utf-8"
        )
        blob = {
            "tests": [{"resultsTableRow": '<ol class="feature-steps-list">' + "".join(
                f"<strong>{label}</strong>" for label in
                ["Given a", "When b", "Then c", "Given a", "When b", "Then c"]
            ) + "</ol>"}],
            "environment": {"Python": "3.12", "pytest-bdd": "8.1.0"},
        }
        artifact = root / "report.html"
        artifact.write_text(
            '<div data-jsonblob="' + html.escape(json.dumps(blob), quote=True) + '"></div>', encoding="utf-8"
        )
        return artifact

    def test_preflight_finds_owner_real_proof_config_conflict_and_artifact_fact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = self.fixture(root)
            goal = f"debug repeated Background steps in report file://{artifact.as_posix()}"
            packet = preflight.build(root, goal, "codex")

        roles = {(row["path"], row["suggested_role"]) for row in packet["evidence"]}
        self.assertIn(("conftest.py", "implementation-owner"), roles)
        self.assertIn(("tests/test_html_reporting.py", "proof"), roles)
        self.assertNotIn(("tests/e2e/conftest.py", "proof"), roles)
        self.assertIn("pytest tests/test_html_reporting.py -q", {row["command"] for row in packet["suggested_test_commands"]})
        findings = {row["dependency"]: row for row in packet["configuration_findings"]}
        self.assertEqual(findings["pytest-bdd"]["status"], "incompatible-declarations")
        repeated = packet["artifacts"][0]["observations"][0]
        self.assertEqual(repeated["count"], 3)
        self.assertEqual(repeated["labels"], ["Given a", "When b", "Then c"])
        self.assertEqual(packet["host_contract"]["max_reasoning_passes"], 1)
        self.assertEqual(packet["behavior_trace"]["direction"], "observed-output-to-producer")
        self.assertEqual(packet["behavior_trace"]["state"], "resolved-to-producer")
        self.assertEqual(packet["behavior_trace"]["topology"]["shape"], "linear")
        self.assertEqual(packet["behavior_trace"]["topology"]["path_count"], 1)
        self.assertIn("output-renderer", {node["role"] for node in packet["behavior_trace"]["nodes"]})
        self.assertIn("data-producer", {node["role"] for node in packet["behavior_trace"]["nodes"]})
        trace_nodes = {row["id"]: row for row in packet["behavior_trace"]["nodes"]}
        trace_edges = packet["behavior_trace"]["edges"]
        renderer_edge = next(row for row in trace_edges if row["relationship"] == "rendered-by")
        producer_edge = next(
            row for row in trace_edges
            if row["relationship"] in {"reads-from", "receives-from"}
            and trace_nodes[row["to"]]["role"] == "data-producer"
        )
        self.assertEqual(trace_nodes[renderer_edge["to"]]["symbols"], ["pytest_html_results_table_row"])
        self.assertEqual(trace_nodes[producer_edge["to"]]["symbols"], ["_feature_steps"])
        self.assertEqual(trace_nodes[producer_edge["to"]]["repository_role"], "implementation-owner")
        candidate = next(row for row in packet["evidence"] if row["path"] == "tests/e2e/conftest.py")
        self.assertEqual(candidate["suggested_role"], "inspection")
        self.assertEqual(candidate["behavior_roles"], ["candidate-only"])
        self.assertRegex(packet["reuse_key"], r"^sha256:[a-f0-9]{64}$")
        self.assertLessEqual(packet["metrics"]["files_read"], 96)
        self.assertLessEqual(packet["metrics"]["evidence_files"], 6)

    def test_packet_fingerprint_changes_with_current_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = self.fixture(root)
            goal = f"debug repeated Background steps in report file://{artifact.as_posix()}"
            first = preflight.build(root, goal, "claude")
            (root / "conftest.py").write_text("def _feature_steps(feature, scenario):\n    return scenario.steps\n", encoding="utf-8")
            second = preflight.build(root, goal, "claude")
        self.assertNotEqual(first["packet_fingerprint"], second["packet_fingerprint"])
        self.assertNotEqual(first["reuse_key"], second["reuse_key"])
        self.assertRegex(first["packet_fingerprint"], r"^sha256:[a-f0-9]{64}$")

    def test_preflight_expands_same_file_value_controlling_call_to_real_producer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = self.fixture(root)
            (root / "conftest.py").write_text(
                "def compose_flow(feature, scenario):\n"
                "    rows = list(feature.background.steps)\n"
                "    rows.extend(scenario.steps)\n"
                "    return rows\n\n"
                "def before_scenario(request, feature, scenario):\n"
                "    request.node._bdd_steps = compose_flow(feature, scenario)\n\n"
                "def render_report(report):\n"
                "    return report._bdd_steps\n",
                encoding="utf-8",
            )
            packet = preflight.build(
                root,
                f"debug repeated starting steps in report file://{artifact.as_posix()}",
                "codex",
            )

        evidence_by_symbol = {
            symbol: row
            for row in packet["evidence"]
            for symbol in row.get("symbols", [])
        }
        self.assertEqual(evidence_by_symbol["compose_flow"]["reason"], "bounded repository-local call expansion")
        self.assertEqual(evidence_by_symbol["compose_flow"]["behavior_roles"], ["data-producer"])
        self.assertNotIn("data-producer", evidence_by_symbol["before_scenario"]["behavior_roles"])
        self.assertEqual(
            evidence_by_symbol["compose_flow"]["local_call_from"]["symbols"],
            ["before_scenario"],
        )
        nodes = {row["id"]: row for row in packet["behavior_trace"]["nodes"]}
        relationships = {
            (tuple(nodes[row["from"]].get("symbols", [])), tuple(nodes[row["to"]].get("symbols", [])))
            for row in packet["behavior_trace"]["edges"]
            if row["relationship"] == "receives-from"
        }
        self.assertIn((("before_scenario",), ("compose_flow",)), relationships)
        self.assertEqual(packet["behavior_trace"]["state"], "resolved-to-producer")

    def test_preflight_preserves_multiple_local_producer_branches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = self.fixture(root)
            (root / "conftest.py").write_text(
                "def background_steps(feature):\n"
                "    return list(feature.background.steps)\n\n"
                "def scenario_steps(scenario):\n"
                "    return list(scenario.steps)\n\n"
                "def before_scenario(request, feature, scenario):\n"
                "    if feature.background:\n"
                "        request.node._bdd_steps = background_steps(feature)\n"
                "    else:\n"
                "        request.node._bdd_steps = scenario_steps(scenario)\n\n"
                "def render_report(report):\n"
                "    return report._bdd_steps\n",
                encoding="utf-8",
            )
            packet = preflight.build(
                root,
                f"debug repeated starting steps in report file://{artifact.as_posix()}",
                "codex",
            )

        topology = packet["behavior_trace"]["topology"]
        self.assertEqual(topology["shape"], "branching", packet)
        self.assertEqual(topology["path_count"], 2)
        nodes = {row["id"]: row for row in packet["behavior_trace"]["nodes"]}
        producer_symbols = {
            tuple(nodes[edge["to"]].get("symbols", []))
            for edge in packet["behavior_trace"]["edges"]
            if edge["relationship"] == "receives-from"
            and nodes[edge["to"]]["role"] == "data-producer"
        }
        self.assertEqual(producer_symbols, {("background_steps",), ("scenario_steps",)})
        self.assertEqual(packet["behavior_trace"]["state"], "resolved-to-producer")

    def test_preflight_expands_explicit_repository_local_import(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = self.fixture(root)
            (root / "support").mkdir()
            (root / "support" / "steps.py").write_text(
                "def compose_flow(feature, scenario):\n"
                "    rows = list(feature.background.steps)\n"
                "    rows.extend(scenario.steps)\n"
                "    return rows\n",
                encoding="utf-8",
            )
            (root / "conftest.py").write_text(
                "from support.steps import compose_flow\n\n"
                "def before_scenario(request, feature, scenario):\n"
                "    request.node._bdd_steps = compose_flow(feature, scenario)\n\n"
                "def render_report(report):\n"
                "    return report._bdd_steps\n",
                encoding="utf-8",
            )
            packet = preflight.build(root, f"debug duplicate report file://{artifact.as_posix()}", "claude")

        producer = next(
            row for row in packet["evidence"]
            if row["path"] == "support/steps.py" and row.get("symbols") == ["compose_flow"]
        )
        self.assertEqual(producer["reason"], "bounded repository-local call expansion")
        self.assertIn("data-producer", producer["behavior_roles"])
        self.assertEqual(packet["behavior_trace"]["state"], "resolved-to-producer")

    def test_preflight_keeps_trace_partial_when_imported_local_callee_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = self.fixture(root)
            (root / "support").mkdir()
            (root / "support" / "steps.py").write_text("def other_flow():\n    return []\n", encoding="utf-8")
            (root / "conftest.py").write_text(
                "from support.steps import compose_flow\n\n"
                "def before_scenario(request, feature, scenario):\n"
                "    request.node._bdd_steps = compose_flow(feature, scenario)\n\n"
                "def render_report(report):\n"
                "    return report._bdd_steps\n",
                encoding="utf-8",
            )
            packet = preflight.build(root, f"debug duplicate report file://{artifact.as_posix()}", "copilot")

        self.assertEqual(packet["behavior_trace"]["state"], "partial")
        self.assertEqual(packet["status"], "partial")
        self.assertEqual(packet["safe_fallback"]["state"], "continue-approved-debug-investigation")
        self.assertEqual(packet["safe_fallback"]["correction_scope"], "blocked")
        self.assertEqual(packet["safe_fallback"]["user_input"], "not-required")
        self.assertTrue(any("compose_flow" in value and "not uniquely resolved" in value for value in packet["unresolved"]))
        caller = next(row for row in packet["evidence"] if row.get("symbols") == ["before_scenario"])
        self.assertNotIn("data-producer", caller["behavior_roles"])

    def test_partial_preflight_with_reproduction_evidence_is_a_successful_cli_handoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = self.fixture(root)
            (root / "support").mkdir()
            (root / "support" / "steps.py").write_text("def other_flow():\n    return []\n", encoding="utf-8")
            (root / "conftest.py").write_text(
                "from support.steps import compose_flow\n\n"
                "def before_scenario(request, feature, scenario):\n"
                "    request.node._bdd_steps = compose_flow(feature, scenario)\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "debug-preflight.py"), "--root", str(root),
                 "--goal", f"debug duplicate report file://{artifact.as_posix()}", "--host", "codex", "--format", "json"],
                text=True,
                capture_output=True,
                check=False,
            )
        packet = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(packet["status"], "partial")
        self.assertEqual(packet["safe_fallback"]["state"], "continue-approved-debug-investigation")

    def test_preflight_requests_input_only_without_reproduction_or_external_context(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            packet = preflight.build(root, "debug an unavailable external symptom", "claude")

        self.assertEqual(packet["status"], "partial")
        self.assertEqual(packet["safe_fallback"]["state"], "awaiting-reproduction-input")
        self.assertEqual(packet["safe_fallback"]["user_input"], "required")
        self.assertEqual(packet["safe_fallback"]["correction_scope"], "blocked")

    def test_supplied_artifact_is_inspected_before_repository_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = self.fixture(root)
            events: list[str] = []
            inspect = preflight._inspect_artifact
            inventory = preflight._inventory

            def inspected(path):
                events.append("artifact")
                return inspect(path)

            def inventoried(path):
                events.append("inventory")
                return inventory(path)

            with mock.patch.object(preflight, "_inspect_artifact", side_effect=inspected), mock.patch.object(preflight, "_inventory", side_effect=inventoried):
                preflight.build(root, f"debug file://{artifact.as_posix()}", "codex")

        self.assertLess(events.index("artifact"), events.index("inventory"))

    def test_local_ide_report_url_resolves_inside_target_and_strips_query(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sample-project"
            root.mkdir()
            artifact = self.fixture(root)
            report = root / "reports" / "report.html"
            report.parent.mkdir()
            report.write_bytes(artifact.read_bytes())
            goal = (
                "debug repeated steps in "
                "http://localhost:63342/sample-project/reports/report.html"
                "?_ijt=session&_ij_reload=RELOAD_ON_SAVE&sort=result"
            )
            packet = preflight.build(root, goal, "codex")

        self.assertEqual(packet["artifacts"][0]["path"], report.resolve().as_posix())
        self.assertEqual(packet["artifacts"][0]["status"], "inspected")
        self.assertEqual(packet["artifacts"][0]["observations"][0]["count"], 3)

    def test_local_ide_report_url_cannot_escape_target_with_parent_segments(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sample-project"
            root.mkdir()
            outside = root.parent / "outside.html"
            outside.write_text("<html>private</html>", encoding="utf-8")
            packet = preflight.build(
                root,
                "debug http://localhost:63342/sample-project/../outside.html?sort=result",
                "codex",
            )

        self.assertEqual(packet["artifacts"], [])


if __name__ == "__main__":
    unittest.main()
