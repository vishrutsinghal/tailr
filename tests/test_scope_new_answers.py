from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import navigator_scope  # noqa: E402


def _document(root: Path, goal: str):
    (root / "owner-a.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
    (root / "owner-b.py").write_text("def beta():\n    return 2\n", encoding="utf-8")
    _, _, hash_a = navigator_scope.safe_text(root, "owner-a.py")
    _, _, hash_b = navigator_scope.safe_text(root, "owner-b.py")
    candidates = [
        {"path": "owner-a.py", "candidate_id": "cand-aaaaaaaaaaaa", "role": "implementation-owner",
         "status": "included", "confidence": "high", "reason_codes": ["bounded-static-owner-evidence"],
         "evidence_edge_ids": ["edge-aaaaaaaaaaaa"], "content_fingerprint": hash_a, "seed_sources": ["explicit-path"]},
        {"path": "owner-b.py", "candidate_id": "cand-bbbbbbbbbbbb", "role": "implementation-owner",
         "status": "included", "confidence": "high", "reason_codes": ["bounded-static-owner-evidence"],
         "evidence_edge_ids": ["edge-bbbbbbbbbbbb"], "content_fingerprint": hash_b, "seed_sources": ["explicit-path"]},
    ]
    edges = [
        {"edge_id": "edge-aaaaaaaaaaaa", "kind": "imports-module", "from_candidate_id": "cand-aaaaaaaaaaaa",
         "to_candidate_id": "cand-bbbbbbbbbbbb", "strength": "strong", "reason_codes": ["static-relationship"]},
        {"edge_id": "edge-bbbbbbbbbbbb", "kind": "imports-module", "from_candidate_id": "cand-bbbbbbbbbbbb",
         "to_candidate_id": "cand-aaaaaaaaaaaa", "strength": "strong", "reason_codes": ["static-relationship"]},
    ]
    frames = [
        {"requirement_id": "req-frame-000000000001", "display_id": "REQ-01",
         "statement": "Use alpha plus owner-new.py.", "query_terms": ["alpha"]},
        {"requirement_id": "req-frame-000000000002", "display_id": "REQ-02",
         "statement": "Use beta.", "query_terms": ["beta"]},
    ]
    return navigator_scope.evidence_document(
        root, goal, frames, candidates, edges=edges, investigation={"state": "ambiguous"},
    )


def _packet(root: Path, goal: str):
    return navigator_scope.host_reasoning_packet(_document(root, goal))


GOAL = "Use alpha plus owner-new.py and beta."


class ScopeNewAnswerTests(unittest.TestCase):
    def test_new_prefix_converges_to_proposed_owner(self) -> None:
        # No goal supplied: the delegate re-resolution is skipped, so packet
        # candidates (consumer-only edges) apply and due diligence confirms.
        # Goal grounding is covered by test_prefix_is_stripped_before_grounding.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            packet = _packet(root, GOAL)
            self.assertEqual(packet["route"]["state"], "requested")
            proposal, errors = navigator_scope.proposal_from_scope_answers(
                root, packet, ["REQ-01=new:owner-new.py", "REQ-02=owner-b.py"], 1, "codex",
            )
            self.assertEqual(errors, [], errors)
            self.assertIsNotNone(proposal)
            assert proposal is not None
            validation = navigator_scope.validate_host_proposal(root, packet, proposal)
            self.assertEqual(validation["errors"], [], validation["errors"])
            recorded = navigator_scope.record_host_proposal(root, _document(root, GOAL), proposal)
        rows = {row["requirement_id"]: row for row in recorded["requirements"]}
        self.assertEqual(rows["req-frame-000000000001"]["implementation_owners"], ["owner-new.py"])
        self.assertEqual(rows["req-frame-000000000001"].get("owner_kind"), "declared-new")
        self.assertEqual(rows["req-frame-000000000002"]["implementation_owners"], ["owner-b.py"])

    def test_prefix_is_stripped_before_grounding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            packet = _packet(root, GOAL)
            _, errors = navigator_scope.proposal_from_scope_answers(
                root, packet, ["REQ-01=new:owner-new.py", "REQ-02=owner-b.py"], 1, "codex",
                goal="Unrelated goal with no paths.",
            )
        self.assertTrue(any(error.startswith("answer-new-path-ungrounded:owner-new.py") for error in errors),
                        errors)
        self.assertFalse(any("new:owner-new.py" in error for error in errors), errors)

    def test_new_existing_file_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            packet = _packet(root, GOAL)
            _, errors = navigator_scope.proposal_from_scope_answers(
                root, packet, ["REQ-01=new:owner-a.py", "REQ-02=owner-b.py"], 1, "codex",
                goal=GOAL,
            )
        self.assertTrue(any(error.startswith("declared-new-file-already-exists:owner-a.py") for error in errors),
                        errors)

    def test_necessity_question_fires_on_term_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, body in [
                ("alpha_store.py", "def get_alpha():\n    return 1\n"),
                ("beta_store.py", "def get_beta():\n    return 2\n"),
            ]:
                (root / name).write_text(body, encoding="utf-8")
            _, _, hash_a = navigator_scope.safe_text(root, "alpha_store.py")
            _, _, hash_b = navigator_scope.safe_text(root, "beta_store.py")
            candidates = [
                {"path": "alpha_store.py", "candidate_id": "cand-aaaaaaaaaaaa", "role": "implementation-owner",
                 "status": "included", "confidence": "high", "reason_codes": ["bounded-static-owner-evidence"],
                 "evidence_edge_ids": ["edge-aaaaaaaaaaaa"], "content_fingerprint": hash_a, "seed_sources": ["explicit-path"]},
                {"path": "beta_store.py", "candidate_id": "cand-bbbbbbbbbbbb", "role": "implementation-owner",
                 "status": "included", "confidence": "high", "reason_codes": ["bounded-static-owner-evidence"],
                 "evidence_edge_ids": ["edge-bbbbbbbbbbbb"], "content_fingerprint": hash_b, "seed_sources": ["explicit-path"]},
            ]
            edges = [
                {"edge_id": "edge-aaaaaaaaaaaa", "kind": "imports-module", "from_candidate_id": "cand-aaaaaaaaaaaa",
                 "to_candidate_id": "cand-bbbbbbbbbbbb", "strength": "strong", "reason_codes": ["static-relationship"]},
                {"edge_id": "edge-bbbbbbbbbbbb", "kind": "imports-module", "from_candidate_id": "cand-bbbbbbbbbbbb",
                 "to_candidate_id": "cand-aaaaaaaaaaaa", "strength": "strong", "reason_codes": ["static-relationship"]},
            ]
            frames = [
                {"requirement_id": "req-frame-000000000001", "display_id": "REQ-01",
                 "statement": "Handle alpha retries in alpha_handlers.py.", "query_terms": ["alpha"]},
                {"requirement_id": "req-frame-000000000002", "display_id": "REQ-02",
                 "statement": "Use beta.", "query_terms": ["beta"]},
            ]
            goal = "Handle alpha retries in alpha_handlers.py and beta."
            document = navigator_scope.evidence_document(
                root, goal, frames, candidates, edges=edges, investigation={"state": "ambiguous"},
            )
            packet = navigator_scope.host_reasoning_packet(document)
            self.assertEqual(packet["route"]["state"], "requested")
            _, errors = navigator_scope.proposal_from_scope_answers(
                root, packet, ["REQ-01=new:alpha_handlers.py", "REQ-02=beta_store.py"], 1, "codex",
            )
        self.assertTrue(
            any(error.startswith("answer-new-path-needs-extend-justification:alpha_handlers.py:alpha_store.py")
                for error in errors),
            errors,
        )

    def test_necessity_unit_cases(self) -> None:
        block = navigator_scope._new_necessity_blocker
        included_owner = {"path": "alpha_store.py", "role": "implementation-owner", "status": "included"}
        self.assertIsNone(block("sub/alpha_new.py", ["alpha"], {"alpha_store.py": included_owner}))
        excluded = {"path": "alpha_store.py", "role": "implementation-owner", "status": "excluded"}
        self.assertIsNone(block("alpha_new.py", ["alpha"], {"alpha_store.py": excluded}))
        test_role = {"path": "alpha_test.py", "role": "test", "status": "proof-only"}
        self.assertIsNone(block("alpha_new.py", ["alpha"], {"alpha_test.py": test_role}))
        self.assertIsNone(block("alpha_new.py", [], {"alpha_store.py": included_owner}))
        self.assertIsNone(block("alpha_new.py", ["al"], {"alpha_store.py": included_owner}))
        self.assertEqual(
            block("alpha_new.py", ["alpha"], {"alpha_store.py": included_owner}), "alpha_store.py",
        )

    def test_new_ineligible_path_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            packet = _packet(root, GOAL)
            _, errors = navigator_scope.proposal_from_scope_answers(
                root, packet, ["REQ-01=new:vendor/owner-new.py", "REQ-02=owner-b.py"], 1, "codex",
                goal="Use vendor/owner-new.py and beta.",
            )
        self.assertTrue(any(error.startswith("answer-new-path-collision-blocked:vendor/owner-new.py") for error in errors),
                        errors)


if __name__ == "__main__":
    unittest.main()
