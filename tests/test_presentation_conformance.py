from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pm3_presentation", ROOT / "scripts" / "presentation.py")
presentation = importlib.util.module_from_spec(spec); assert spec and spec.loader
sys.modules[spec.name] = presentation; spec.loader.exec_module(presentation)


class PresentationConformanceTests(unittest.TestCase):
    def fixtures(self):
        for path in sorted((ROOT / "tests" / "fixtures" / "presentation").glob("*-report.json")):
            yield path, json.loads(path.read_text(encoding="utf-8"))

    def test_plan_debug_and_closure_are_semantically_complete(self):
        reports = list(self.fixtures())
        self.assertEqual({path.stem for path, _ in reports}, {"plan-report", "debug-report", "closure-report"})
        for _path, report in reports:
            checked = presentation.validate(report)
            self.assertEqual(checked["status"], "passed", checked["issues"])
            self.assertEqual(set(checked["section_ids"]), set(report["required_section_ids"]))

    def test_supported_hosts_receive_same_semantics(self):
        report = next(report for path, report in self.fixtures() if path.stem == "plan-report")
        expected = set(report["required_section_ids"])
        for host in presentation.HOSTS:
            surface = "json" if host == "mcp" else "markdown"
            rendered = presentation.render(report, surface)
            if surface == "json": self.assertEqual(set(json.loads(rendered)["required_section_ids"]), expected)
            else:
                for section in report["sections"]: self.assertIn(f"## {section['title']}", rendered)

    def test_narrow_output_wraps_without_dropping_sections(self):
        for _path, report in self.fixtures():
            rendered = presentation.render(report, "narrow", width=40)
            for section in report["sections"]: self.assertIn(f"## {section['title']}", rendered)

    def test_collapsed_output_fails_explicitly_instead_of_summarizing(self):
        for _path, report in self.fixtures():
            rendered = presentation.render(report, "collapsed")
            self.assertIn("cannot safely collapse", rendered)
            self.assertIn("No shortened report is a substitute", rendered)

    def test_verbose_validator_rejects_silent_omission(self):
        _path, report = next(self.fixtures())
        removed = report["sections"][0]["id"]
        report["sections"] = report["sections"][1:]
        checked = presentation.validate(report)
        self.assertEqual(checked["status"], "failed")
        self.assertIn(f"required-section-{removed}-missing", checked["issues"])

    def test_quick_guided_expert_keep_same_verbose_data(self):
        _path, report = next(self.fixtures())
        rendered_sections = []
        for mode in ("quick", "guided", "expert"):
            candidate = {**report, "mode": mode}
            checked = presentation.validate(candidate)
            self.assertEqual(checked["status"], "passed")
            rendered_sections.append(checked["section_ids"])
        self.assertEqual(rendered_sections[0], rendered_sections[1])
        self.assertEqual(rendered_sections[1], rendered_sections[2])

    def test_full_matrix_passes(self):
        result = presentation.conformance()
        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["scenario_count"], 3)

    def test_packaged_conformance_fixtures_match_test_fixtures(self):
        packaged = ROOT / "benchmarks" / "product-maturity" / "presentation-v1"
        for test_path, report in self.fixtures():
            self.assertEqual(json.loads((packaged / test_path.name).read_text(encoding="utf-8")), report)

    def test_cli_can_select_presentation_depth_without_mutating_fixture(self):
        fixture = ROOT / "tests" / "fixtures" / "presentation" / "plan-report.json"
        original = json.loads(fixture.read_text(encoding="utf-8"))
        for mode in ("quick", "guided", "expert"):
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "presentation", "render", "--input", fixture.as_posix(), "--surface", "json", "--mode", mode],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["mode"], mode)
        self.assertEqual(json.loads(fixture.read_text(encoding="utf-8")), original)

    def test_orchestration_projection_preserves_user_visible_details(self):
        value = {"verb":"discuss","run_id":"start-1","state":"awaiting-approval",
                 "workflow_id":"ttw-1","result":{"answer":{"direct":"Saved explanation."}},
                 "next_action":"Approve or revise.","boundary":"Planning only."}
        report = presentation.from_orchestration(value)
        rendered = presentation.render(report, "markdown")
        self.assertIn("Saved explanation.", rendered)
        self.assertIn("ttw-1", rendered)
        self.assertIn("Approve or revise.", rendered)


if __name__ == "__main__": unittest.main()
