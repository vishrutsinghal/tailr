from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V3 = load("pm_l4_v3", "scripts/learning-v3.py")
GOV = load("pm_l4_governance", "scripts/learning-governance.py")
RETRIEVAL = load("pm_l4_retrieval", "scripts/learning-retrieval.py")
RECEIPTS = load("pm_l4_receipts", "scripts/learning-use-receipt.py")
LOCK = load("pm_l4_lock", "scripts/planning-lock.py")
ANCHOR = load("pm_l4_anchor", "scripts/change-intent-anchor.py")


def add_learning(root: Path, learning_id: str, *, tasks: list[str] | None = None, paths: list[str] | None = None) -> dict:
    record = V3.build_record(
        root, learning_id=learning_id, learning_class="positive-pattern", summary=f"Summary {learning_id}",
        advice=f"Advice {learning_id}", source_kind="pm-l4-test", source_ref="evidence.json",
        source_fingerprint="sha256:" + "0" * 64, captured_by="PM-L4 test",
        task_types=tasks or ["test"], tags=["validation"], path_patterns=paths or ["tests/service.py"],
        confidence_score=90,
    )
    return V3.append_record(root, record)


def prepare(root: Path) -> None:
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "service.py").write_text("value = 1\n", encoding="utf-8")
    (root / "evidence.json").write_text("{}\n", encoding="utf-8")


def proposal(root: Path) -> dict:
    return RETRIEVAL.build_proposal(root, task_types=["test"], tags=["validation"], paths=["tests/service.py"], requirement_ids=[], mode="lite")


def rejected_receipt(root: Path, learning: dict, run_id: str) -> None:
    use_proposal = proposal(root)
    LOCK.create(root, "reject stale learning", run_id)
    LOCK.save_start_report(root, run_id, {"goal": "reject stale learning", "navigator": {"learning_use_proposal": use_proposal}})
    LOCK.approve(root, run_id, True)
    source = root / f"{run_id}-anchor.json"
    source.write_text(json.dumps({"requirements": [{"statement": "review learning", "acceptance_criteria": ["decision saved"], "preserve_rules": ["keep evidence"], "likely_paths": ["tests/service.py"], "evidence_plan": ["review"]}]}), encoding="utf-8")
    ANCHOR.draft(root, run_id, source)
    uid = ANCHOR.approve(root, run_id)["requirements"][0]["requirement_uid"]
    RECEIPTS.record_decision(root, run_id, learning_id=learning["learning_id"], decision="rejected", decision_type="review", requirement_uids=[uid], rationale="Current evidence rejects this guidance", approved=True)


class LearningGovernanceTests(unittest.TestCase):
    def test_challenge_blocks_advice_and_confirm_appends_revalidation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); prepare(root); learning = add_learning(root, "lrn-challenge")
            opened = GOV.open_challenge(root, learning["learning_id"], reason="Current validation contradicts the advice", evidence_refs=["evidence.json"], approved=True)
            blocked = proposal(root)
            resolved = GOV.resolve_challenge(root, opened["entity_id"], action="confirm", reason="Focused validation confirms the scoped advice", evidence_refs=["evidence.json"], approved=True)
            latest = V3.latest_records(V3.read_records(root))[learning["learning_id"]]
            after = proposal(root)

        self.assertEqual(blocked["matches"], [])
        self.assertIn("open governance challenge", blocked["blocked"][0]["reasons"][0])
        self.assertEqual(resolved["previous_event_id"], opened["event_id"])
        self.assertEqual(latest["lifecycle"]["operation"], "revalidate")
        self.assertEqual([item["learning_id"] for item in after["matches"]], [learning["learning_id"]])

    def test_conflict_blocks_both_and_winner_resolution_revokes_loser(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); prepare(root)
            first = add_learning(root, "lrn-conflict-first"); second = add_learning(root, "lrn-conflict-second")
            conflict = GOV.open_conflict(root, [first["learning_id"], second["learning_id"]], reason="The recommendations prescribe contradictory validation order", evidence_refs=["evidence.json"], approved=True)
            self.assertEqual(proposal(root)["matches"], [])
            GOV.resolve_conflict(root, conflict["entity_id"], action="learning-a-wins", reason="Current focused validation supports the first learning", evidence_refs=["evidence.json"], approved=True)
            latest = V3.latest_records(V3.read_records(root))
            after = proposal(root)

        self.assertEqual(latest[second["learning_id"]]["freshness"]["status"], "revoked")
        self.assertEqual([item["learning_id"] for item in after["matches"]], [first["learning_id"]])

    def test_scoped_coexistence_requires_disjoint_project_applicability(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); prepare(root)
            first = add_learning(root, "lrn-scope-one"); second = add_learning(root, "lrn-scope-two")
            conflict = GOV.open_conflict(root, [first["learning_id"], second["learning_id"]], reason="Potential overlap", evidence_refs=["evidence.json"], approved=True)
            with self.assertRaisesRegex(ValueError, "disjoint"):
                GOV.resolve_conflict(root, conflict["entity_id"], action="scoped-coexistence", reason="Keep both", evidence_refs=["evidence.json"], approved=True)

    def test_content_fingerprint_invalidators_cover_manifest_symbol_policy_graph_and_owner(self) -> None:
        cases = {
            "manifest-change": "pyproject.toml",
            "symbol-change": "tests/service.py",
            "policy-change": "GUARDRAILS.md",
            "graph-change": ".tailtrail/code-graph-cache.json",
            "ownership-change": ".github/CODEOWNERS",
        }
        for invalidator, relative in cases.items():
            with self.subTest(invalidator=invalidator), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); prepare(root)
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_text("before\n", encoding="utf-8")
                learning = V3.build_record(root, learning_id=f"lrn-{invalidator}", learning_class="general", summary="snapshot", advice="use snapshot", source_kind="test", source_ref="evidence.json", source_fingerprint="sha256:" + "0" * 64, captured_by="test", task_types=["test"], tags=["validation"], path_patterns=["tests/service.py"], invalidators=[invalidator], confidence_score=90)
                V3.append_record(root, learning); target.write_text("after\n", encoding="utf-8")
                result = proposal(root)
            reasons = " ".join(reason for item in result["blocked"] for reason in item["reasons"])
            self.assertIn(f"{invalidator} invalidator triggered", reasons)

    def test_repeated_rejection_blocks_then_promotes_sanitized_avoid_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); prepare(root); learning = add_learning(root, "lrn-repeated-rejection")
            rejected_receipt(root, learning, "reject-one"); rejected_receipt(root, learning, "reject-two")
            blocked = proposal(root); candidates = GOV.record_negative_candidates(root, approved=True)
            promoted = GOV.resolve_negative(root, candidates[0]["entity_id"], action="promote", reason="Repeated review evidence rejects this approach", evidence_refs=["evidence.json"], approved=True, summary="Avoid the rejected validation order", advice="Use current validation evidence instead of the rejected order")
            latest = V3.latest_records(V3.read_records(root))

        self.assertEqual(blocked["matches"], [])
        self.assertIn("repeated adverse learning evidence", " ".join(blocked["blocked"][0]["reasons"]))
        self.assertEqual(promoted["action"], "promote")
        self.assertEqual(latest[learning["learning_id"]]["freshness"]["status"], "revoked")
        self.assertEqual(latest[promoted["promoted_learning_id"]]["learning_class"], "avoid-history")
        serialized = json.dumps(candidates)
        self.assertNotIn("raw_failure", serialized.replace('"raw_failure": false', ""))

    def test_dismissed_negative_candidate_unblocks_the_exact_reviewed_signal_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); prepare(root); learning = add_learning(root, "lrn-dismissed-negative")
            rejected_receipt(root, learning, "dismiss-one"); rejected_receipt(root, learning, "dismiss-two")
            candidate = GOV.record_negative_candidates(root, approved=True)[0]
            GOV.resolve_negative(root, candidate["entity_id"], action="dismiss", reason="The two receipts concern an obsolete task frame", evidence_refs=["evidence.json"], approved=True)
            result = proposal(root)
        self.assertEqual([item["learning_id"] for item in result["matches"]], [learning["learning_id"]])

    def test_corrupt_governance_ledger_fails_retrieval_closed_without_advice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); prepare(root); add_learning(root, "lrn-corrupt-ledger", paths=[])
            path = root / GOV.LEDGER; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("{broken\n", encoding="utf-8")
            result = proposal(root); rendered = RETRIEVAL.render(result)
        self.assertEqual(result["matches"], [])
        self.assertNotIn("Advice lrn-corrupt-ledger", rendered)
        self.assertIn("governance evidence is invalid", " ".join(result["blocked"][0]["reasons"]))

    def test_v3_and_governance_append_streams_are_concurrency_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); prepare(root)
            def create(index: int): return add_learning(root, f"lrn-parallel-{index}", paths=[])
            with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(create, range(8)))
            records = V3.read_records(root)
        self.assertEqual(len(records), 8)
        self.assertEqual([item["sequence"] for item in records], list(range(1, 9)))

    def test_cli_schema_and_approval_boundaries_are_exposed(self) -> None:
        schema = json.loads((ROOT / "schemas" / "learning-governance-event.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); prepare(root); add_learning(root, "lrn-cli-governance")
            command = [sys.executable, str(ROOT / "scripts" / "tailtrail.py"), "learn", "governance", "challenge", "--root", str(root), "--learning-id", "lrn-cli-governance", "--reason", "contradicted", "--evidence-ref", "evidence.json"]
            blocked = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("requires --approved", blocked.stdout)


if __name__ == "__main__":
    unittest.main()
