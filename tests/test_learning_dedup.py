from __future__ import annotations

import importlib.util
import json
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


refresh = load("tailtrail_learning_dedup_refresh_test", "scripts/learning-refresh.py")
receipts = load("tailtrail_learning_dedup_receipts_test", "scripts/learning-use-receipt.py")
v3 = load("tailtrail_learning_dedup_v3_test", "scripts/learning-v3.py")


def _capture(root: Path, learning_id: str, advice: str, tags=None) -> dict:
    import hashlib
    digest = hashlib.sha256(learning_id.encode()).hexdigest()
    record = v3.build_record(
        root, learning_id=learning_id, learning_class="positive-pattern",
        summary=f"Summary {learning_id}", advice=advice,
        source_kind="test", source_ref="test", source_fingerprint=f"sha256:{digest}",
        captured_by="test", tags=list(tags or ["t"]),
    )
    return v3.append_record(root, record)




class ExactDuplicateCollapseTests(unittest.TestCase):
    def test_execute_merge_supersedes_duplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = _capture(root, "lrn-aaa", "Do not declare victory early.", ["a"])
            _capture(root, "lrn-bbb", "Do not declare victory early.", ["a"])
            _capture(root, "lrn-ccc", "Something entirely different here.", ["b"])
            groups = refresh.exact_duplicate_v3_groups(
                list(v3.latest_records(v3.read_records(root)).values()))
            self.assertEqual(len(groups), 1)
            key = next(iter(groups))
            self.assertEqual(sorted(groups[key]), ["lrn-aaa", "lrn-bbb"])
            result = refresh.execute_merge_group(
                root, "lrn-aaa", ["lrn-bbb"], "approved exact-duplicate collapse", True)
            self.assertEqual(result["superseded"], ["lrn-bbb"])
            latest = v3.latest_records(v3.read_records(root))
            self.assertEqual(latest["lrn-bbb"]["freshness"]["status"], "superseded")
            self.assertEqual(
                latest["lrn-bbb"]["lifecycle"]["replacement_learning_id"], "lrn-aaa")
            self.assertEqual(latest["lrn-aaa"]["freshness"]["status"], "current")
            self.assertEqual(latest["lrn-ccc"]["freshness"]["status"], "current")

    def test_execute_merge_requires_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "--approved"):
                refresh.execute_merge_group(
                    Path(temp), "lrn-aaa", ["lrn-bbb"], "reason", False)

    def test_terminal_records_excluded_from_groups(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _capture(root, "lrn-aaa", "Same advice twice.", ["a"])
            _capture(root, "lrn-bbb", "Same advice twice.", ["a"])
            refresh.execute_merge_group(
                root, "lrn-aaa", ["lrn-bbb"], "collapse", True)
            groups = refresh.exact_duplicate_v3_groups(
                list(v3.latest_records(v3.read_records(root)).values()))
            # latest_records returns the superseded version of lrn-bbb, whose
            # status is terminal, so no group reforms around it.
            self.assertNotIn("lrn-bbb", [item for ids in groups.values() for item in ids])

    def test_equivalent_advice_groups_allow_contextual_tags_but_not_different_classes(self):
        records = [
            {
                "learning_id": "lrn-aaa",
                "learning_class": "positive-pattern",
                "freshness": {"status": "current"},
                "content": {"advice": "Keep completion evidence current."},
                "applicability": {"tags": ["closure"]},
            },
            {
                "learning_id": "lrn-bbb",
                "learning_class": "positive-pattern",
                "freshness": {"status": "current"},
                "content": {"advice": "  keep completion evidence CURRENT.  "},
                "applicability": {"tags": ["proof"]},
            },
            {
                "learning_id": "lrn-ccc",
                "learning_class": "avoid-history",
                "freshness": {"status": "current"},
                "content": {"advice": "Keep completion evidence current."},
                "applicability": {"tags": ["closure"]},
            },
        ]
        groups = refresh.equivalent_advice_v3_groups(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(next(iter(groups.values())), ["lrn-aaa", "lrn-bbb"])

    def test_execute_merge_aggregates_observations_context_and_source_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root / ".tailtrail" / "learning-events.jsonl"
            legacy.parent.mkdir(parents=True)
            events = [
                {"id": "event-1", "source_run_id": "run-a"},
                {"id": "event-2", "source_run_id": "run-a"},
                {"id": "event-3", "source_run_id": "run-b"},
            ]
            legacy.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")

            for index, (learning_id, tags, paths) in enumerate((
                ("lrn-aaa", ["closure"], ["scripts/a.py"]),
                ("lrn-bbb", ["proof"], ["scripts/b.py"]),
                ("lrn-ccc", ["closure", "proof"], ["tests/test_c.py"]),
            ), start=1):
                event = events[index - 1]
                record = v3.build_record(
                    root,
                    learning_id=learning_id,
                    learning_class="positive-pattern",
                    summary=f"Observation {index}",
                    advice="Keep completion evidence current.",
                    source_kind="legacy-candidate-reference",
                    source_ref=f".tailtrail/learning-events.jsonl#line={index}",
                    source_fingerprint="sha256:" + v3.sha256(event),
                    captured_by="test",
                    task_types=["completion-feedback"],
                    tags=tags,
                    path_patterns=paths,
                    confidence_score=26,
                )
                v3.append_record(root, record)

            result = refresh.execute_merge_group(
                root,
                "lrn-aaa",
                ["lrn-bbb", "lrn-ccc"],
                "approved equivalent-advice consolidation",
                True,
            )
            self.assertEqual(result["observation_count"], 3)
            self.assertEqual(result["source_run_count"], 2)
            self.assertEqual(result["source_run_ids"], ["run-a", "run-b"])

            latest = v3.latest_records(v3.read_records(root))
            canonical = latest["lrn-aaa"]
            self.assertEqual(canonical["freshness"]["status"], "current")
            self.assertEqual(canonical["utility"]["observation_count"], 3)
            self.assertEqual(canonical["applicability"]["tags"], ["closure", "proof"])
            self.assertEqual(
                canonical["applicability"]["path_patterns"],
                ["scripts/a.py", "scripts/b.py", "tests/test_c.py"],
            )
            self.assertEqual(
                canonical["provenance"]["evidence_refs"],
                [
                    ".tailtrail/learning-events.jsonl#line=1",
                    ".tailtrail/learning-events.jsonl#line=2",
                    ".tailtrail/learning-events.jsonl#line=3",
                ],
            )
            self.assertIn("3 observations across 2 source runs", canonical["content"]["summary"])
            self.assertEqual(latest["lrn-bbb"]["freshness"]["status"], "superseded")
            self.assertEqual(latest["lrn-ccc"]["freshness"]["status"], "superseded")

    def test_execute_merge_rejects_different_advice(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _capture(root, "lrn-aaa", "Keep completion evidence current.", ["closure"])
            _capture(root, "lrn-bbb", "Prefer a different implementation pattern.", ["closure"])
            with self.assertRaisesRegex(ValueError, "equivalent advice"):
                refresh.execute_merge_group(root, "lrn-aaa", ["lrn-bbb"], "merge", True)


class NearDuplicateProposalTests(unittest.TestCase):
    def _record(self, learning_id, advice, tags):
        return {
            "learning_id": learning_id,
            "freshness": {"status": "current"},
            "content": {"advice": advice},
            "applicability": {"tags": list(tags)},
        }

    def test_related_records_proposed(self):
        records = [
            self._record("lrn-1", "Do not declare completion while drift remains open", ["closure"]),
            self._record("lrn-2", "Do not declare completion while drift remains unresolved", ["closure"]),
            self._record("lrn-3", "Prefer greenfield modules for new endpoints", ["design"]),
        ]
        proposals = refresh.near_duplicate_proposals(records)
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["status"], "proposed")
        self.assertIn("closure", proposals[0]["shared_tags"])

    def test_exact_pairs_not_reproposed(self):
        records = [
            self._record("lrn-1", "Identical advice text here", ["a"]),
            self._record("lrn-2", "Identical advice text here", ["a"]),
        ]
        self.assertEqual(refresh.near_duplicate_proposals(records), [])

    def test_unrelated_records_silent(self):
        records = [
            self._record("lrn-1", "Alpha beta gamma delta epsilon", ["a"]),
            self._record("lrn-2", "Zebra yak xray wolf violet", ["b"]),
        ]
        self.assertEqual(refresh.near_duplicate_proposals(records), [])


class ProofOfLifeTouchTests(unittest.TestCase):
    def test_touch_records_applied_decision(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = receipts.touch_on_use(root, "lrn-use", "run-1", "rid-1", "applied")
            self.assertEqual(result["status"], "recorded")
            self.assertEqual(result["receipt_id"], "rid-1")

    def test_non_use_decisions_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = receipts.touch_on_use(root, "lrn-use", "run-1", "rid-1", "ignored")
            self.assertEqual(result["status"], "not-applicable")

    def test_touch_never_mints_versions(self):
        # Proof of life lives in the receipt stream, never in a V3 amend:
        # amending would rotate record identity out from under in-flight
        # proposals pinned to it (proposal validation requires current).
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = list((root / ".tailtrail").rglob("*")) if (root / ".tailtrail").exists() else []
            receipts.touch_on_use(root, "lrn-use", "run-1", "rid-1", "applied")
            after = list((root / ".tailtrail").rglob("*")) if (root / ".tailtrail").exists() else []
            self.assertEqual(before, after)


class PhaseThreeDecidersTests(unittest.TestCase):
    def _capture(self, root, learning_id, advice="Helpful advice here.", tags=None,
                 revalidate_after=None, evidence=None):
        import hashlib
        record = v3.build_record(
            root, learning_id=learning_id, learning_class="positive-pattern",
            summary=f"Summary {learning_id}", advice=advice,
            source_kind="test", source_ref="test",
            source_fingerprint="sha256:" + hashlib.sha256(learning_id.encode()).hexdigest(),
            captured_by="test", tags=list(tags or ["t"]),
            evidence_refs=list(evidence or []),
            revalidate_after=revalidate_after,
        )
        return v3.append_record(root, record)

    def test_revalidate_due_refreshes_elapsed_deadline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "proof.txt").write_text("evidence", encoding="utf-8")
            self._capture(root, "lrn-due", "Timely advice here.",
                          revalidate_after="2000-01-01T00:00:00+00:00",
                          evidence=["proof.txt"])
            result = refresh.revalidate_due(root, True)
            self.assertEqual(result["revalidated"], ["lrn-due"])
            latest = v3.latest_records(v3.read_records(root))["lrn-due"]
            self.assertGreater(len(v3.read_records(root)), 1)

    def test_revalidate_due_requires_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "--approved"):
                refresh.revalidate_due(Path(temp), False)

    def test_sweep_output_carries_usefulness(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, "lrn-scored", "Scored advice here.")
            result = refresh.sweep_v3(root)
            self.assertIn("usefulness", result)
            self.assertIn("lrn-scored", result["usefulness"])
            self.assertIn(result["usefulness"]["lrn-scored"]["band"],
                          {"strong", "usable", "weak", "do-not-use"})

    def test_delete_requires_snapshot_and_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, "lrn-doomed", "Doomed advice here.")
            with self.assertRaisesRegex(ValueError, "snapshot"):
                refresh.delete_learning(root, "lrn-doomed", "reason", True)
            with self.assertRaisesRegex(ValueError, "--approved"):
                refresh.delete_learning(root, "lrn-doomed", "reason", False)

    def test_delete_revokes_with_tombstone(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, "lrn-doomed", "Doomed advice here.")
            refresh.snapshot_store(root)
            result = refresh.delete_learning(root, "lrn-doomed", "superseded by sweep", True)
            self.assertEqual(result["status"], "revoked")
            latest = v3.latest_records(v3.read_records(root))["lrn-doomed"]
            self.assertEqual(latest["freshness"]["status"], "revoked")

    def test_decide_merge_requires_approval_and_reason(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "--approved"):
                refresh.decide_merge_proposal(root, "lrn-aaaa", "approved", "reason", False)
            with self.assertRaisesRegex(ValueError, "reason"):
                refresh.decide_merge_proposal(root, "lrn-aaaa", "approved", "  ", True)

    def test_snapshot_restore_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, "lrn-keep", "Kept advice here.")
            manifest = refresh.snapshot_store(root)
            self.assertIn("record_count", manifest)
            stamp = Path(manifest["snapshot"]).name
            before = (root / ".tailtrail" / "learning-v3" / "events.jsonl").read_bytes()
            (root / ".tailtrail" / "learning-v3" / "events.jsonl").write_bytes(b"corrupted\n")
            restored = refresh.restore_snapshot(root, stamp)
            self.assertIn("events.jsonl", restored["restored"])
            self.assertEqual(
                (root / ".tailtrail" / "learning-v3" / "events.jsonl").read_bytes(), before)

    def test_scores_by_id_maps_bands(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, "lrn-scored", "Scored advice here.")
            scores = receipts.scores_by_id(root)
            self.assertIn("lrn-scored", scores)
            self.assertIn(scores["lrn-scored"]["band"],
                          {"strong", "usable", "weak", "do-not-use"})


class PhaseFourCadenceTests(unittest.TestCase):
    def test_gap_signals_from_drift_and_tiers(self):
        closure_learning = load("tailtrail_phase4_closure_test",
                                "scripts/closure-learning.py")
        report = {
            "requirement_status": {"requirements": [{
                "requirement_uid": "req-1", "display_id": "REQ-01",
                "drift": [
                    {"classification": "new-drift", "message": "edit outside scope",
                     "requirement_uid": "req-1"},
                    {"classification": "unchanged", "message": "nothing",
                     "requirement_uid": "req-1"},
                ],
            }]},
            "tests": {
                "passed_tiers": ["unit"],
                "required_checks": [{
                    "requirement_uids": ["req-1"], "tiers": ["unit", "contract"],
                }],
            },
        }
        signals = closure_learning.gap_signals(report)
        kinds = sorted(item["kind"] for item in signals)
        self.assertEqual(kinds, ["drift-finding", "unproven-tier"])
        tier = next(item for item in signals if item["kind"] == "unproven-tier")
        self.assertIn("contract", tier["text"])

    def test_sweep_threshold_fires_and_rests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            quiet = refresh.check_sweep_threshold(root, 10, 0.5)
            self.assertFalse(quiet["triggered"])
            self.assertEqual(quiet["evaluated"], 0)

    def test_usefulness_tiebreak_orders_without_suppressing(self):
        retrieval = load("tailtrail_phase4_retrieval_test",
                         "scripts/learning-retrieval.py")
        record = {
            "applicability": {"task_types": ["closure"], "tags": ["t"],
                              "requirement_ids": [], "path_patterns": [],
                              "exclusions": []},
            "utility": {"confidence_score": 50, "curated": False},
            "privacy": {"sensitivity": "normal"},
            "freshness": {"status": "current"},
            "provenance": {"source_ref": "x", "source_fingerprint": "y"},
        }
        frame = {"task_types": ["closure"], "tags": ["t"],
                 "requirement_ids": [], "paths": []}
        plain, _ = retrieval.applicability(record, frame)
        boosted, reasons = retrieval.applicability(
            record, frame, usefulness_band="strong")
        demoted, _ = retrieval.applicability(
            record, frame, usefulness_band="do-not-use")
        self.assertEqual(boosted - plain, 3)
        self.assertEqual(plain - demoted, 2)
        self.assertTrue(any("usefulness band" in reason for reason in reasons))


class PhaseTwoSupervisionTests(unittest.TestCase):
    def _capture(self, root, learning_id, advice="Helpful advice here."):
        import hashlib
        record = v3.build_record(
            root, learning_id=learning_id, learning_class="positive-pattern",
            summary=f"Summary {learning_id}", advice=advice,
            source_kind="test", source_ref="test",
            source_fingerprint="sha256:" + hashlib.sha256(learning_id.encode()).hexdigest(),
            captured_by="test", tags=["t"],
        )
        return v3.append_record(root, record)

    def test_snapshot_and_restore_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, "lrn-keep", "Kept advice here.")
            manifest = refresh.snapshot_store(root)
            self.assertGreater(manifest["record_count"], 0)
            stamp = Path(manifest["snapshot"]).name
            journal = root / ".tailtrail" / "learning-v3" / "events.jsonl"
            before = journal.read_bytes()
            journal.write_bytes(b"tampered\n")
            restored = refresh.restore_snapshot(root, stamp)
            self.assertIn("events.jsonl", restored["restored"])
            self.assertEqual(journal.read_bytes(), before)

    def test_queue_dedupes_decided_pairs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proposal = {"canonical_learning_id": "lrn-aaaa",
                        "merged_learning_ids": ["lrn-bbbb"],
                        "similarity": 0.7, "shared_tags": ["t"]}
            first = refresh.queue_merge_proposals(root, [proposal])
            self.assertEqual((first["queued"], first["skipped"]), (1, 0))
            refresh.decide_merge_proposal(
                root, "lrn-aaaa", "rejected", "different nuance", True)
            again = refresh.queue_merge_proposals(root, [proposal])
            self.assertEqual((again["queued"], again["skipped"]), (0, 1))

    def test_decide_rejected_retires_pair(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, "lrn-aaaa", "Advice alpha here.")
            self._capture(root, "lrn-bbbb", "Advice alpha here now.")
            refresh.queue_merge_proposals(root, [{
                "canonical_learning_id": "lrn-aaaa", "merged_learning_ids": ["lrn-bbbb"],
                "similarity": 0.8, "shared_tags": ["t"]}])
            result = refresh.decide_merge_proposal(
                root, "lrn-aaaa", "rejected", "different nuance", True)
            self.assertEqual(result["decision"], "rejected")
            latest = v3.latest_records(v3.read_records(root))
            self.assertEqual(latest["lrn-bbbb"]["freshness"]["status"], "current")

    def test_decide_approved_executes_merge(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, "lrn-aaaa", "Same words here.")
            self._capture(root, "lrn-bbbb", "Same words here.")
            refresh.queue_merge_proposals(root, [{
                "canonical_learning_id": "lrn-aaaa", "merged_learning_ids": ["lrn-bbbb"],
                "similarity": 1.0, "shared_tags": ["t"]}])
            result = refresh.decide_merge_proposal(
                root, "lrn-aaaa", "approved", "exact duplicate", True)
            self.assertEqual(result["executed"][0]["superseded"], ["lrn-bbbb"])
            latest = v3.latest_records(v3.read_records(root))
            self.assertEqual(latest["lrn-bbbb"]["freshness"]["status"], "superseded")

    def test_delete_requires_snapshot_and_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, "lrn-doomed", "Doomed advice here.")
            with self.assertRaisesRegex(ValueError, "snapshot"):
                refresh.delete_learning(root, "lrn-doomed", "reason", True)
            with self.assertRaisesRegex(ValueError, "--approved"):
                refresh.delete_learning(root, "lrn-doomed", "reason", False)
            refresh.snapshot_store(root)
            result = refresh.delete_learning(root, "lrn-doomed", "superseded content", True)
            self.assertEqual(result["status"], "revoked")


if __name__ == "__main__":
    unittest.main()
