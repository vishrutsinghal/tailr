from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import navigator_scope  # noqa: E402


def _edge(edge_id, candidate_id, kind="defines symbol"):
    return {
        "edge_id": edge_id,
        "strength": "strong",
        "kind": kind,
        "from_candidate_id": candidate_id,
        "to_candidate_id": candidate_id,
    }


def _candidate(path, candidate_id, edge_ids):
    return {
        "path": path,
        "candidate_id": candidate_id,
        "role": "implementation-owner",
        "status": "included",
        "confidence": "high",
        "reason_codes": ["bounded-static-owner-evidence"],
        "evidence_edge_ids": list(edge_ids),
        "seed_sources": ["lexical-path"],
        "content_fingerprint": "sha256:" + "c" * 64,
    }


def _packet(requirements, candidates, edges):
    packet = {
        "packet_version": 1,
        "route": {"state": "unavailable"},
        "requirements": requirements,
        "candidates": candidates,
        "edges": edges,
    }
    body = {key: value for key, value in packet.items() if key != "packet_fingerprint"}
    packet["packet_fingerprint"] = navigator_scope.fingerprint(body)
    return packet


def _requirement(req_id, display):
    return {
        "requirement_id": req_id,
        "display_id": display,
        "scope_state": "ambiguous",
        "query_terms": [],
    }


class ResolveUnavailableScopeAnswersTests(unittest.TestCase):
    def setUp(self):
        self._orig_investigate = navigator_scope.investigate
        self._orig_from_seeds = navigator_scope.candidates_from_seeds
        self._rows = []
        navigator_scope.candidates_from_seeds = lambda root, seeds, tasks=(): []
        navigator_scope.investigate = lambda *args, **kwargs: (
            list(self._rows), [], {"state": "not-run"},
        )

    def tearDown(self):
        navigator_scope.investigate = self._orig_investigate
        navigator_scope.candidates_from_seeds = self._orig_from_seeds

    def _resolve(self, root, goal, answers, packet):
        return navigator_scope.resolve_unavailable_scope_answers(
            root, goal, [], packet, answers, 1,
        )

    def test_per_requirement_answers_resolve_split_owners(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "b.py").write_text("VALUE = 2\n", encoding="utf-8")
            candidates = [
                _candidate("a.py", "cand-a", ["e-a"]),
                _candidate("b.py", "cand-b", ["e-b"]),
            ]
            edges = [_edge("e-a", "cand-a"), _edge("e-b", "cand-b", "calls function")]
            packet = _packet(
                [_requirement("req-1", "REQ-01"), _requirement("req-2", "REQ-02")],
                candidates, edges,
            )
            self._rows = [dict(row) for row in candidates]
            document, errors = self._resolve(root, "Do A and do B", ["REQ-01=a.py", "REQ-02=b.py"], packet)
        self.assertEqual(errors, [])
        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(document["state"], "resolved")
        by_id = {row["display_id"]: row for row in document["requirements"]}
        self.assertEqual(by_id["REQ-01"]["implementation_owners"], ["a.py"])
        self.assertEqual(by_id["REQ-02"]["implementation_owners"], ["b.py"])
        self.assertTrue(navigator_scope.verify_decision_fingerprint(document))

    def test_bare_path_with_two_requirements_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.py").write_text("VALUE = 1\n", encoding="utf-8")
            packet = _packet(
                [_requirement("req-1", "REQ-01"), _requirement("req-2", "REQ-02")], [], [],
            )
            document, errors = self._resolve(root, "Do A and do B", ["a.py"], packet)
        self.assertIsNone(document)
        self.assertTrue(any(code.startswith("answer-needs-requirement") for code in errors))

    def test_duplicate_requirement_answer_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "b.py").write_text("VALUE = 2\n", encoding="utf-8")
            packet = _packet(
                [_requirement("req-1", "REQ-01"), _requirement("req-2", "REQ-02")], [], [],
            )
            document, errors = self._resolve(
                root, "Do A and do B", ["REQ-01=a.py", "REQ-01=b.py"], packet,
            )
        self.assertIsNone(document)
        self.assertTrue(any("duplicate-requirement-answer" in code for code in errors))

    def test_incomplete_answers_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.py").write_text("VALUE = 1\n", encoding="utf-8")
            packet = _packet(
                [_requirement("req-1", "REQ-01"), _requirement("req-2", "REQ-02")], [], [],
            )
            document, errors = self._resolve(root, "Do A and do B", ["REQ-01=a.py"], packet)
        self.assertIsNone(document)
        self.assertTrue(any(code.startswith("answer-incomplete") for code in errors))

    def test_unqualified_answer_empties_row_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "c.py").write_text("VALUE = 3\n", encoding="utf-8")
            candidates = [_candidate("a.py", "cand-a", ["e-a"])]
            edges = [_edge("e-a", "cand-a")]
            packet = _packet([_requirement("req-1", "REQ-01")], candidates, edges)
            self._rows = [dict(row) for row in candidates]
            document, errors = self._resolve(root, "Do A", ["REQ-01=c.py"], packet)
        self.assertEqual(errors, [])
        self.assertIsNotNone(document)
        assert document is not None
        # c.py exists but never qualified as a candidate: no minted ownership.
        self.assertEqual(document["requirements"][0]["implementation_owners"], [])
        self.assertNotEqual(document["state"], "resolved")

    def test_proposed_new_path_preserves_declared_owner_without_same_directory_owner(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "anchor.py").write_text("VALUE = 1\n", encoding="utf-8")
            candidate = _candidate("src/anchor.py", "cand-anchor", ["e-anchor"])
            packet = _packet(
                [_requirement("req-1", "REQ-01")],
                [candidate],
                [_edge("e-anchor", "cand-anchor")],
            )
            self._rows = [dict(candidate)]
            document, errors = self._resolve(
                root,
                "Add a new schema",
                ["REQ-01=new:schemas/host-question-flow.schema.json"],
                packet,
            )

        self.assertEqual(errors, [])
        self.assertIsNotNone(document)
        assert document is not None
        requirement = document["requirements"][0]
        self.assertEqual(
            requirement["implementation_owners"],
            ["schemas/host-question-flow.schema.json"],
        )
        self.assertEqual(requirement["owner_kind"], "declared-new")
        self.assertEqual(document["state"], "resolved")
        self.assertEqual(document["answer_dispositions"][0]["status"], "declared-new")


if __name__ == "__main__":
    unittest.main()
