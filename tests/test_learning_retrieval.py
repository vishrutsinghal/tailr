from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V3 = load_script("pm_l2_learning_v3", "scripts/learning-v3.py")
RETRIEVAL = load_script("pm_l2_learning_retrieval", "scripts/learning-retrieval.py")


def add_learning(
    root: Path,
    learning_id: str,
    *,
    advice: str | None = None,
    task_types: list[str] | None = None,
    tags: list[str] | None = None,
    paths: list[str] | None = None,
    exclusions: list[str] | None = None,
    confidence: int = 90,
    sensitivity: str = "normal",
    revalidate_after: str | None = None,
) -> dict:
    record = V3.build_record(
        root,
        learning_id=learning_id,
        learning_class="positive-pattern",
        summary=f"Summary for {learning_id}",
        advice=advice or f"Advice for {learning_id}",
        source_kind="pm-l2-fixture",
        source_ref="fixture.json",
        source_fingerprint="sha256:" + "0" * 64,
        captured_by="PM-L2 test",
        task_types=task_types or ["test"],
        tags=tags or ["validation"],
        path_patterns=paths or ["tests/test_service.py"],
        exclusions=exclusions or [],
        invalidators=["source-change", "policy-change", "validation-change"],
        confidence_score=confidence,
        sensitivity=sensitivity,
    )
    record["freshness"]["revalidate_after"] = revalidate_after
    return V3.append_record(root, record)


def proposal(root: Path, **overrides):
    values = {
        "task_types": ["test"],
        "tags": ["validation"],
        "paths": ["tests/test_service.py"],
        "requirement_ids": [],
        "mode": "lite",
    }
    values.update(overrides)
    return RETRIEVAL.build_proposal(root, **values)


class LearningRetrievalTests(unittest.TestCase):
    def prepare(self, root: Path) -> None:
        path = root / "tests" / "test_service.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_service(): pass\n", encoding="utf-8")

    def test_retrieval_requires_project_and_task_framing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "task frame"):
                RETRIEVAL.build_proposal(root, task_types=[], tags=[], paths=[], requirement_ids=[], mode="lite")

    def test_applicability_ranking_is_deterministic_and_hard_capped_at_three(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            for index in range(5):
                add_learning(root, f"lrn-ranked-{index}", confidence=95 - index)
            result = proposal(root)

        self.assertEqual(result["state"], "proposed")
        self.assertEqual(result["result_cap"], 3)
        self.assertEqual(len(result["matches"]), 3)
        self.assertEqual([item["learning_id"] for item in result["matches"]], ["lrn-ranked-0", "lrn-ranked-1", "lrn-ranked-2"])
        self.assertTrue(all(item["match_explanations"] for item in result["matches"]))

    def test_lite_is_quiet_when_no_high_value_match_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            add_learning(root, "lrn-unrelated", task_types=["release"], tags=["supply-chain"], paths=["release/proof.json"])
            result = proposal(root)

        self.assertEqual(result["state"], "quiet")
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["blocked"], [])

    def test_stale_deadline_and_refresh_action_cannot_surface_advice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            add_learning(root, "lrn-expired", advice="EXPIRED ADVICE", revalidate_after="2020-01-01T00:00:00+00:00")
            add_learning(root, "lrn-suppressed", advice="SUPPRESSED ADVICE")
            refresh = root / ".tailtrail" / "learning-refresh-actions.json"
            refresh.write_text(json.dumps({"actions": [{"learning_id": "lrn-suppressed", "action": "suppress"}]}), encoding="utf-8")
            result = proposal(root)
            rendered = RETRIEVAL.render(result)

        self.assertEqual(result["state"], "blocked")
        self.assertEqual(result["matches"], [])
        self.assertNotIn("EXPIRED ADVICE", rendered)
        self.assertNotIn("SUPPRESSED ADVICE", rendered)
        reasons = " ".join(reason for item in result["blocked"] for reason in item["reasons"])
        self.assertIn("revalidation deadline", reasons)
        self.assertIn("suppress", reasons)

    def test_declared_source_and_validation_invalidators_detect_post_capture_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            add_learning(root, "lrn-changed-after-capture")
            target = root / "tests" / "test_service.py"
            future = time.time() + 5
            os.utime(target, (future, future))
            result = proposal(root)

        self.assertEqual(result["matches"], [])
        item = next(item for item in result["blocked"] if item["learning_id"] == "lrn-changed-after-capture")
        self.assertIn("source-change invalidator triggered", item["reasons"])
        self.assertIn("validation-change invalidator triggered", item["reasons"])
        self.assertEqual({check["state"] for check in item["invalidator_checks"]}, {"not-triggered", "triggered"})

    def test_explicit_learning_contradiction_blocks_both_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            add_learning(root, "lrn-conflict-a", exclusions=["learning:lrn-conflict-b"])
            add_learning(root, "lrn-conflict-b")
            result = proposal(root)

        self.assertEqual(result["state"], "blocked")
        self.assertEqual(result["matches"], [])
        self.assertEqual({item["learning_id"] for item in result["blocked"]}, {"lrn-conflict-a", "lrn-conflict-b"})
        self.assertTrue(all(any("contradiction" in reason for reason in item["reasons"]) for item in result["blocked"]))

    def test_terminal_conflict_target_does_not_block_current_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            current = add_learning(root, "lrn-current", exclusions=["learning:lrn-revoked"])
            revoked = add_learning(root, "lrn-revoked")
            V3.terminal_transition(root, revoked["learning_id"], "revoke", "contradiction resolved")
            result = proposal(root)

        self.assertIn(current["learning_id"], {item["learning_id"] for item in result["matches"]})

    def test_exclusions_privacy_and_missing_source_path_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            add_learning(root, "lrn-excluded", exclusions=["task:test"])
            add_learning(root, "lrn-internal", sensitivity="internal")
            add_learning(root, "lrn-missing-path", paths=["src/removed.py"])
            result = proposal(root)

        self.assertEqual(result["matches"], [])
        reasons = {item["learning_id"]: " ".join(item["reasons"]) for item in result["blocked"]}
        self.assertIn("task exclusion", reasons["lrn-excluded"])
        self.assertIn("sensitivity", reasons["lrn-internal"])
        self.assertIn("source-change", reasons["lrn-missing-path"])

    def test_cli_and_navigator_expose_proposal_not_silent_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            add_learning(root, "lrn-navigator", advice="Run the focused service test")
            command = [
                sys.executable, str(ROOT / "scripts" / "tailtrail.py"), "learn", "retrieve", "--root", str(root),
                "--task-types", "test", "--tags", "validation", "--path", "tests/test_service.py", "--format", "json",
            ]
            cli = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            navigator = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "navigator.py"), "add validation tests", "--root", str(root),
                 "--changed", "tests/test_service.py"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

        self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
        self.assertEqual(json.loads(cli.stdout)["state"], "proposed")
        self.assertEqual(navigator.returncode, 0, navigator.stdout + navigator.stderr)
        self.assertIn("## Learning Use Proposal", navigator.stdout)
        self.assertIn("Proposed advice (not instruction)", navigator.stdout)
        self.assertNotIn("## Graph-Aware Learnings", navigator.stdout)

    def test_proposal_schema_is_closed_and_packaged(self) -> None:
        schema = json.loads((ROOT / "schemas" / "learning-use-proposal.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["result_cap"]["const"], 3)
        self.assertEqual(schema["properties"]["matches"]["maxItems"], 3)
        self.assertTrue((ROOT / "scripts" / "learning-retrieval.py").is_file())

    def test_labeled_precision_fixtures_pass(self) -> None:
        fixture = json.loads((ROOT / "benchmarks" / "product-maturity" / "pm-l2-retrieval-fixtures-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(fixture["type"], "tailtrail-pm-l2-retrieval-fixtures")
        self.assertEqual(len({case["id"] for case in fixture["cases"]}), len(fixture["cases"]))
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.prepare(root)
                for item in case["records"]:
                    add_learning(
                        root,
                        item["learning_id"],
                        task_types=item["task_types"],
                        tags=item["tags"],
                        paths=item["paths"],
                        exclusions=item.get("exclusions"),
                        confidence=item["confidence"],
                        sensitivity=item["sensitivity"],
                        revalidate_after=item.get("revalidate_after"),
                    )
                result = RETRIEVAL.build_proposal(root, requirement_ids=[], **case["input"])
                expected = case["expected"]
                self.assertEqual(result["state"], expected["state"])
                self.assertEqual([item["learning_id"] for item in result["matches"]], expected["matches"])
                self.assertEqual([item["learning_id"] for item in result["blocked"]], expected["blocked"])
                rendered = RETRIEVAL.render(result)
                for item in case["records"]:
                    if item["learning_id"] in expected["blocked"]:
                        self.assertNotIn(f"Advice for {item['learning_id']}", rendered)


if __name__ == "__main__":
    unittest.main()
