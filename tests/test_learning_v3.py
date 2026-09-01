from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_v3():
    path = ROOT / "scripts" / "learning-v3.py"
    spec = importlib.util.spec_from_file_location("learning_v3_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V3 = load_v3()


def load_script(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def candidate(event_id: str = "legacy-1", advice: str = "Run focused tests before closure") -> dict:
    return {
        "id": event_id,
        "timestamp": "2026-09-01T00:00:00+00:00",
        "task_type": "test",
        "tags": ["validation"],
        "files": ["tests/test_service.py"],
        "learning_candidate": advice,
        "stale_when": "the test command changes",
        "sensitivity": "normal",
        "learning_confidence": {"score": 82, "band": "trusted"},
    }


class LearningV3Tests(unittest.TestCase):
    def test_capture_creates_canonical_record_and_legacy_reader_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            event = candidate()
            record = V3.capture_legacy_event(root, event)
            V3.LEGACY_EVENTS.parent.joinpath("unused")
            legacy = root / V3.LEGACY_EVENTS
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text(json.dumps(event) + "\n", encoding="utf-8")

            records = V3.read_records(root)
            compatible = V3.compatible_events(root)

        self.assertEqual(records, [record])
        self.assertEqual(compatible[0]["id"], "legacy-1")
        self.assertEqual(compatible[0]["learning_v3_id"], record["learning_id"])
        self.assertNotIn("repo", record)

    def test_amendment_is_append_only_and_preserves_previous_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = V3.capture_legacy_event(root, candidate())
            before = (root / V3.STORE).read_bytes()
            second = V3.amend(root, first["learning_id"], reason="clarify scope", advice="Run only the focused service tests")
            records = V3.read_records(root)

        self.assertEqual(records[0], first)
        self.assertTrue((json.dumps(first, sort_keys=True) + "\n").encode("utf-8") in before)
        self.assertEqual(second["lifecycle"]["previous_record_id"], first["record_id"])
        self.assertEqual(second["sequence"], 2)

    def test_supersession_and_revocation_are_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = V3.capture_legacy_event(root, candidate("old"))
            replacement = V3.capture_legacy_event(root, candidate("new", "Use the replacement validation workflow"))
            transition = V3.terminal_transition(root, old["learning_id"], "supersede", "newer evidence", replacement["learning_id"])
            revoked = V3.terminal_transition(root, replacement["learning_id"], "revoke", "policy conflict")
            with self.assertRaisesRegex(V3.LearningV3Error, "terminal"):
                V3.amend(root, old["learning_id"], reason="not allowed")

        self.assertEqual(transition["freshness"]["status"], "superseded")
        self.assertEqual(revoked["freshness"]["status"], "revoked")

    def test_legacy_migration_is_idempotent_by_reference_and_preserves_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / V3.LEGACY_EVENTS
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(candidate()) + "\n", encoding="utf-8")
            before = path.read_bytes()

            first = V3.migrate_legacy(root, approved=True)
            second = V3.migrate_legacy(root, approved=True)
            records = V3.read_records(root)
            record = records[0]
            after = path.read_bytes()

        self.assertEqual(after, before)
        self.assertEqual(len(records), 1)
        self.assertEqual(first["migrated"], second["migrated"])
        self.assertEqual(record["provenance"]["source_ref"], ".tailtrail/learning-events.jsonl#line=1")

    def test_migration_skips_sensitive_and_non_candidate_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / V3.LEGACY_EVENTS
            path.parent.mkdir(parents=True)
            sensitive = candidate("sensitive", "token=do-not-copy")
            ordinary = {"id": "no-candidate", "sensitivity": "normal"}
            path.write_text(json.dumps(sensitive) + "\n" + json.dumps(ordinary) + "\n", encoding="utf-8")

            report = V3.migrate_legacy(root, approved=True)

        self.assertEqual(report["migrated"], [])
        self.assertEqual({item["legacy_id"] for item in report["skipped"]}, {"sensitive", "no-candidate"})

    def test_project_frame_and_digest_chain_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as first_temp, tempfile.TemporaryDirectory() as second_temp:
            first = Path(first_temp)
            second = Path(second_temp)
            V3.capture_legacy_event(first, candidate())
            target = second / V3.STORE
            target.parent.mkdir(parents=True)
            target.write_bytes((first / V3.STORE).read_bytes())
            with self.assertRaisesRegex(V3.LearningV3Error, "project-frame"):
                V3.read_records(second)

            record = json.loads((first / V3.STORE).read_text(encoding="utf-8"))
            record["content"]["advice"] = "tampered"
            (first / V3.STORE).write_text(json.dumps(record) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(V3.LearningV3Error, "digest"):
                V3.read_records(first)

    def test_privacy_and_relative_path_validation_reject_unsafe_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(V3.LearningV3Error, "sensitive"):
                V3.capture_legacy_event(root, candidate(advice="password=plain-text"))
            record = V3.build_record(
                root, learning_id="lrn-safe-record", learning_class="general", summary="safe summary", advice="safe advice",
                source_kind="test", source_ref="evidence.json", source_fingerprint="sha256:" + "0" * 64,
                captured_by="test", path_patterns=["../outside.py"],
            )
            with self.assertRaisesRegex(V3.LearningV3Error, "project-relative"):
                V3.append_record(root, record)
            self.assertFalse((root / V3.PROJECT_FRAME).exists())
            malformed = V3.build_record(
                root, learning_id="lrn-malformed", learning_class="general", summary="safe", advice="safe advice",
                source_kind="test", source_ref="evidence.json", source_fingerprint="sha256:" + "0" * 64,
                captured_by="test",
            )
            malformed["lifecycle"] = []
            self.assertIn("lifecycle must be an object", V3.validate_record(malformed))

    def test_cli_requires_approval_for_migration_and_terminal_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            command = [sys.executable, str(ROOT / "scripts" / "tailtrail.py"), "learn", "v3", "migrate", "--root", str(root)]
            blocked = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            dry_run = subprocess.run([*command, "--dry-run"], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(blocked.returncode, 2)
        self.assertIn("requires --approved", blocked.stdout)
        self.assertEqual(dry_run.returncode, 0)

    def test_public_capture_and_legacy_curated_add_both_write_v3(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            capture = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "tailtrail.py"), "learn", "capture", "--root", str(root),
                 "--summary", "Reusable validation", "--candidate", "Run focused validation before closure",
                 "--validation-outcome", "pass", "--acceptance", "accepted", "--format", "json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            curated = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "tailtrail.py"), "learn", "add", "Reuse the repository validator", "--root", str(root), "--section", "validation"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            records = V3.read_records(root)

        self.assertEqual(capture.returncode, 0, capture.stdout + capture.stderr)
        self.assertEqual(curated.returncode, 0, curated.stdout + curated.stderr)
        self.assertEqual(len(records), 2)
        self.assertTrue(any(record["utility"]["curated"] for record in records))

    def test_schema_is_closed_and_packaged_source_exists(self) -> None:
        schema = json.loads((ROOT / "schemas" / "learning-v3-record.schema.json").read_text(encoding="utf-8"))

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], "3")
        self.assertTrue((ROOT / "scripts" / "learning-v3.py").is_file())

    def test_existing_learning_consumers_use_terminal_aware_v3_projection(self) -> None:
        graph = load_script("learning_v3_graph_test", "scripts/graph-learning.py")
        refresh = load_script("learning_v3_refresh_test", "scripts/learning-refresh.py")
        review = load_script("learning_v3_review_test", "scripts/learning-review.py")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = V3.capture_legacy_event(root, candidate())
            V3.terminal_transition(root, record["learning_id"], "revoke", "invalidated by policy")

            graph_events = graph.read_events(root)
            refresh_events = refresh.read_events(root)
            review_events = review.read_events(root)

        self.assertEqual(graph_events, [])
        self.assertEqual(refresh_events, [])
        self.assertEqual(review_events, [])


if __name__ == "__main__":
    unittest.main()
