from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.intake_pipeline import IntakeError, IntakePipeline


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


class IntakeEvidenceStateTests(unittest.TestCase):
    def _candidate(self, pipeline: IntakePipeline, run_id: str, field: str, value: object) -> str:
        question = pipeline.issue_question(run_id, field, f"Which value for {field}?")
        answer = pipeline.record_answer(
            run_id, field, value, source="host-observation", question_id=question["payload"]["question_id"]
        )
        return str(answer["payload"]["answer_id"])

    def _state(self, pipeline: IntakePipeline, run_id: str, answer_id: str) -> dict:
        records = pipeline.replay(run_id)["answer_states"]
        return next(record for record in records if record["answer_id"] == answer_id)

    def _setup(self, temp: str) -> tuple[IntakePipeline, str, Path]:
        root = Path(temp)
        evidence = root / "scripts" / "example.py"
        evidence.parent.mkdir(parents=True)
        evidence.write_text("VALUE = 1\n", encoding="utf-8")
        pipeline = IntakePipeline(root)
        run = pipeline.create_run("collect host context", "new-feature")
        return pipeline, run["run_id"], evidence

    def _accept(self, pipeline: IntakePipeline, run_id: str, answer_id: str, refs: list[dict]) -> dict:
        return pipeline.accept_answer(
            run_id,
            answer_id,
            {"outcome": "accepted", "verified_by": "navigator", "evidence_refs": refs},
        )

    def test_accepted_answer_keeps_validated_evidence_refs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline, run_id, evidence = self._setup(temp)
            answer_id = self._candidate(pipeline, run_id, "implementation-owner", "scripts/example.py")
            self._accept(
                pipeline, run_id, answer_id,
                [{"path": "scripts/example.py", "content_fingerprint": _fingerprint(evidence)}],
            )
            state = self._state(pipeline, run_id, answer_id)
            self.assertEqual(state["state"], "accepted")
            self.assertEqual(state["evidence_refs"][0]["path"], "scripts/example.py")

    def test_changed_evidence_marks_accepted_answer_stale_and_blocks_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline, run_id, evidence = self._setup(temp)
            answer_id = self._candidate(pipeline, run_id, "implementation-owner", "scripts/example.py")
            self._accept(
                pipeline, run_id, answer_id,
                [{"path": "scripts/example.py", "content_fingerprint": _fingerprint(evidence)}],
            )
            self.assertEqual(pipeline.refresh_source_evidence(run_id), [])

            evidence.write_text("VALUE = 2\n", encoding="utf-8")
            self.assertEqual(pipeline.refresh_source_evidence(run_id), [answer_id])
            self.assertEqual(self._state(pipeline, run_id, answer_id)["state"], "stale")
            # Already-stale answers are not re-reported: the refresh is idempotent.
            self.assertEqual(pipeline.refresh_source_evidence(run_id), [])

            with self.assertRaises(IntakeError):
                self._accept(
                    pipeline, run_id, answer_id,
                    [{"path": "scripts/example.py", "content_fingerprint": _fingerprint(evidence)}],
                )

    def test_missing_evidence_file_marks_accepted_answer_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline, run_id, evidence = self._setup(temp)
            answer_id = self._candidate(pipeline, run_id, "implementation-owner", "scripts/example.py")
            self._accept(
                pipeline, run_id, answer_id,
                [{"path": "scripts/example.py", "content_fingerprint": _fingerprint(evidence)}],
            )
            evidence.unlink()
            self.assertEqual(pipeline.refresh_source_evidence(run_id), [answer_id])

    def test_rejects_unsafe_or_mismatched_evidence_refs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline, run_id, evidence = self._setup(temp)
            answer_id = self._candidate(pipeline, run_id, "implementation-owner", "scripts/example.py")
            good = _fingerprint(evidence)
            bad_refs = [
                [{"path": str(evidence.resolve()), "content_fingerprint": good}],
                [{"path": "../outside.py", "content_fingerprint": good}],
                [{"path": "scripts/example.py", "content_fingerprint": "sha256:" + "0" * 64}],
                [{"path": "scripts/example.py"}],
                ["scripts/example.py"],
            ]
            for refs in bad_refs:
                with self.subTest(refs=refs), self.assertRaises(IntakeError):
                    self._accept(pipeline, run_id, answer_id, refs)
            self.assertEqual(self._state(pipeline, run_id, answer_id)["state"], "candidate")

    def test_secret_bearing_answer_cannot_be_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline, run_id, evidence = self._setup(temp)
            answer_id = self._candidate(pipeline, run_id, "implementation-owner", "token: abc123")
            with self.assertRaises(IntakeError):
                self._accept(pipeline, run_id, answer_id, [])
            self.assertEqual(self._state(pipeline, run_id, answer_id)["state"], "candidate")
            stored = (Path(temp) / ".tailtrail" / "intake" / run_id / "events.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("abc123", stored)

    def test_oversized_and_malformed_input_is_rejected_before_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline, run_id, evidence = self._setup(temp)
            question = pipeline.issue_question(run_id, "implementation-owner", "Which value?")
            events_path = Path(temp) / ".tailtrail" / "intake" / run_id / "events.jsonl"
            before = events_path.read_text(encoding="utf-8")

            with self.assertRaises(IntakeError):
                pipeline.record_answer(
                    run_id, "implementation-owner", "x" * (70 * 1024),
                    source="host-observation", question_id=question["payload"]["question_id"],
                )
            with self.assertRaises(IntakeError):
                pipeline.record_answer(run_id, "", "value", source="host-observation", question_id="q")
            with self.assertRaises(IntakeError):
                pipeline.record_answer(run_id, "implementation-owner", "value", source="host-observation")
            self.assertEqual(events_path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
