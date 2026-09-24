"""Phase 0 visual requirement plumbing: contract shape only.

Nothing here is wired into Start yet: these tests pin the vocabulary,
bounds-free hashing, attachment states, and the observation validator so
Phase 1 can gate on them. Planning behavior is byte-identical with or
without this module.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "tailtrail_visual_requirement_test", ROOT / "scripts" / "visual_requirement.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_product_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PNG_BYTES = bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 64


class VisualRequirementPhase0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_attachment_states(self) -> None:
        self.assertEqual(self.module.attachment_state([], []), "none")
        self.assertEqual(
            self.module.attachment_state(["./mockup.png"], ["./mockup.png"]), "bound"
        )
        self.assertEqual(
            self.module.attachment_state(["./mockup.png"], []), "unbound"
        )
        self.assertEqual(
            self.module.attachment_state(
                ["./mockup.png", "./flow2.png"], ["./mockup.png"]
            ),
            "unbound",
        )
        # Remote references are not attachments and never bind.
        self.assertEqual(
            self.module.attachment_state(["https://example.invalid/a.png"], []),
            "none",
        )

    def test_remote_and_missing_paths_never_hash(self) -> None:
        self.assertIsNone(
            self.module.normalize_attachment("https://example.invalid/a.png")
        )
        self.assertIsNone(
            self.module.normalize_attachment("data:image/png;base64,AAAA")
        )
        with tempfile.TemporaryDirectory() as temp:
            missing = self.module.hash_visual_artifact(Path(temp) / "gone.png")
        self.assertEqual(missing["status"], "unavailable")

    def test_hash_is_stable_and_streamed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "a.png"
            second = Path(temp) / "b.png"
            first.write_bytes(PNG_BYTES)
            second.write_bytes(PNG_BYTES)
            left = self.module.hash_visual_artifact(first)
            right = self.module.hash_visual_artifact(second)
        self.assertEqual(left["sha256"], right["sha256"])
        self.assertTrue(left["sha256"].startswith("sha256:"))
        self.assertEqual(left["size_bytes"], len(PNG_BYTES))
        self.assertNotIn("bytes", left)

    def test_valid_observation_record(self) -> None:
        self.assertEqual(
            self.module.validate_observations(
                {
                    "locator": "./mockup.png",
                    "summary": "ECG section with Account Name dropdown and table.",
                    "open_questions": ["What are the exact headers?"],
                    "complete": False,
                }
            ),
            [],
        )
        self.assertEqual(
            self.module.validate_observations(
                {
                    "locator": "./mockup.png",
                    "summary": "Fully legible mockup; all controls visible.",
                    "open_questions": [],
                    "complete": True,
                }
            ),
            [],
        )

    def test_observation_shape_violations(self) -> None:
        self.assertIn(
            "visual-observations-require-summary",
            self.module.validate_observations(
                {
                    "locator": "./mockup.png",
                    "summary": "  ",
                    "open_questions": ["What are the headers?"],
                    "complete": False,
                }
            ),
        )
        # Incomplete claims must carry questions, not silent confidence.
        self.assertIn(
            "visual-incomplete-requires-open-questions",
            self.module.validate_observations(
                {
                    "locator": "./mockup.png",
                    "summary": "Something visible.",
                    "open_questions": [],
                    "complete": False,
                }
            ),
        )
        # Complete claims must carry no questions.
        self.assertIn(
            "visual-complete-forbids-open-questions",
            self.module.validate_observations(
                {
                    "locator": "./mockup.png",
                    "summary": "Fully legible.",
                    "open_questions": ["What are the headers?"],
                    "complete": True,
                }
            ),
        )

    def test_embedded_data_uris_are_rejected(self) -> None:
        self.assertIn(
            "visual-observations-must-not-embed-data",
            self.module.validate_observations(
                {
                    "locator": "./mockup.png",
                    "summary": "See data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                    "open_questions": ["What are the headers?"],
                    "complete": False,
                }
            ),
        )

    def test_binding_matches_observations_to_inspected_hashes(self) -> None:
        module = load_module()
        inspected = [
            {
                "input_id": "IN-02",
                "locator": "./mockup.png",
                "status": "inspected",
                "sha256": "sha256:abc",
                "size_bytes": 80,
                "media_type": "image/png",
            }
        ]
        bound, issues = module.bind_observations(
            {
                "locator": "./mockup.png",
                "summary": "ECG section with dropdown and table.",
                "open_questions": ["What are the exact headers?"],
                "complete": False,
            },
            inspected,
        )
        self.assertEqual(issues, [])
        self.assertEqual(bound[0]["input_id"], "IN-02")
        self.assertEqual(bound[0]["sha256"], "sha256:abc")
        self.assertEqual(bound[0]["open_questions"], ["What are the exact headers?"])
        # Unknown locator fails closed instead of binding the wrong bytes.
        _, issues = module.bind_observations(
            {
                "locator": "./other.png",
                "summary": "Something.",
                "open_questions": ["What is this?"],
                "complete": False,
            },
            inspected,
        )
        self.assertEqual(issues, ["visual-observations-reference-unknown-artifact"])
        # Locator-free payloads bind only in the unambiguous single case.
        bound, issues = module.bind_observations(
            {
                "summary": "ECG section.",
                "open_questions": ["What are the headers?"],
                "complete": False,
            },
            inspected,
        )
        self.assertEqual(issues, [])
        self.assertEqual(bound[0]["sha256"], "sha256:abc")

    def test_phantom_reference_blocks_nothing(self) -> None:
        # Documented non-goal: words about an image that exists nowhere,
        # with no session attachment, change nothing at this layer.
        self.assertEqual(self.module.attachment_state([], []), "none")
        self.assertEqual(
            self.module.validate_observations("just prose"),  # type: ignore[arg-type]
            ["visual-observations-must-be-an-object"],
        )


class VisualGatePhase1Tests(unittest.TestCase):
    """A host-declared unbound visual blocks scope through existing gates.

    No new gating machinery: a visual `question` clause becomes a material
    decision in the sufficiency contract, which the scope precondition
    already refuses. These tests pin that composition.
    """

    def test_vis_decision_helper_shape(self) -> None:
        module = load_module()
        decision = module.visual_material_decision(
            "What are the exact table column headers in the attached image?"
        )
        self.assertEqual(decision["id"], "VIS-01")
        self.assertEqual(decision["decision_class"], module.VISUAL_DECISION_CLASS)
        self.assertIn("headers", decision["question"])
        with self.assertRaises(ValueError):
            module.visual_material_decision("   ")

    def visual_clauses(self):
        return [
            {
                "clause_id": "C-01",
                "role": "outcome",
                "text": "Add a table with the columns shown in the attached image.",
            }
        ]

    def visual_requirements(self):
        return [
            {
                "display_id": "REQ-01",
                "statement": "Add a table with the columns shown in the attached image.",
                "kind": "change",
                "source_clause_ids": ["C-01"],
                "intent_terms": ["table", "columns"],
                "quoted_literals": [],
                "intent_class": "general",
                "confidence": "medium",
            }
        ]

    def test_visual_question_defers_scope_precondition(self) -> None:
        discovery = load_product_module(
            "tailtrail_requirement_discovery_visual", "scripts/requirement_discovery.py"
        )
        task_start = load_product_module(
            "tailtrail_task_start_visual", "scripts/task-start.py"
        )
        question = (
            "What are the exact table column headers in the attached image, "
            "which is visible to the host but unbound to this Start request?"
        )
        sufficiency = discovery.requirement_sufficiency_contract(
            self.visual_clauses(),
            self.visual_requirements(),
            [question],
            source="host-assisted",
        )
        self.assertEqual(sufficiency["state"], "clarification-required")
        self.assertTrue(
            any(
                row.get("question") == question
                for row in sufficiency["material_decisions"]
            )
        )
        precondition = task_start.scope_question_precondition(
            {"sufficiency": sufficiency}
        )
        self.assertEqual(precondition["state"], "deferred")
        self.assertFalse(precondition["scope_question_allowed"])
        self.assertEqual(
            precondition["reason_code"],
            "requirements-must-be-resolved-before-scope-question",
        )

    def test_no_visual_question_keeps_scope_eligible(self) -> None:
        discovery = load_product_module(
            "tailtrail_requirement_discovery_visual2", "scripts/requirement_discovery.py"
        )
        task_start = load_product_module(
            "tailtrail_task_start_visual2", "scripts/task-start.py"
        )
        sufficiency = discovery.requirement_sufficiency_contract(
            self.visual_clauses(), self.visual_requirements(), [],
            source="host-assisted",
        )
        self.assertEqual(sufficiency["state"], "sufficient")
        precondition = task_start.scope_question_precondition(
            {"sufficiency": sufficiency}
        )
        self.assertEqual(precondition["state"], "eligible")
        self.assertTrue(precondition["scope_question_allowed"])


class VisualStartEndToEndTests(unittest.TestCase):
    """Bound image plus open visual questions stop before scope and lock."""

    def test_bound_visual_with_questions_returns_clarification(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            png = root / "mockup.png"
            png.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 64)
            observations = {
                "locator": png.as_posix(),
                "summary": "ECG Event Configuration section with Account Name dropdown and table.",
                "open_questions": ["What are the exact table column headers?"],
                "complete": False,
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "tailtrail.py"),
                    "start",
                    "Add a table with columns shown in the attached image",
                    "--root",
                    str(root),
                    "--visual-artifact",
                    png.as_posix(),
                    "--visual-observations",
                    json.dumps(observations),
                    "--format",
                    "json",
                    "--no-planning-lock",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        decisions = payload["requirement_sufficiency"]["material_decisions"]
        self.assertTrue(
            any(
                row.get("decision_class") == "visual-artifact-required"
                for row in decisions
            )
        )
        self.assertIn(
            "What are the exact table column headers?", payload["material_questions"]
        )
        self.assertNotIn("planning_lock", payload)
        bound = payload["visual_requirements"][0]
        self.assertEqual(bound["media_type"], "image/png")
        self.assertTrue(bound["sha256"].startswith("sha256:"))

    def test_complete_visual_observations_keep_no_open_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            png = root / "mockup.png"
            png.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 64)
            observations = {
                "locator": png.as_posix(),
                "summary": "Fully legible single-section mockup; all controls visible.",
                "open_questions": [],
                "complete": True,
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "tailtrail.py"),
                    "start",
                    "Add the section shown in the attached image",
                    "--root",
                    str(root),
                    "--visual-artifact",
                    png.as_posix(),
                    "--visual-observations",
                    json.dumps(observations),
                    "--format",
                    "json",
                    "--no-planning-lock",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        # Requirements are sufficient (no VIS decision), but scope cannot
        # resolve inside an empty directory, so the scope gate still holds.
        self.assertEqual(result.returncode, 2, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(
            payload.get("scope_question_precondition", {}).get("scope_question_allowed")
        )
        self.assertEqual(payload["visual_requirements"][0]["media_type"], "image/png")
        self.assertTrue(
            payload["visual_requirements"][0]["sha256"].startswith("sha256:")
        )


if __name__ == "__main__":
    unittest.main()
