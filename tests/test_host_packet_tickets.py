from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
import sys

if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

import navigator  # noqa: E402
import navigator_scope  # noqa: E402


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class HostPacketTicketTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        (self.root / "src").mkdir(parents=True)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def write(self, relative: str, body: str) -> Path:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return target

    def _ambiguous_flow(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Two-file ambiguous flow mirroring the thin-evidence regression test."""
        self.write("src/owner.py", "def serve():\n    return True\n")
        self.write("src/thin_owner.py", "def thin():\n    return True\n")
        original_budget = navigator_scope.LIMITS["initial_file_reads"]
        navigator_scope.LIMITS["initial_file_reads"] = 0
        try:
            seeds = [
                navigator_scope.seed("src/owner.py", "explicit-path", "user-provided-path"),
                navigator_scope.seed("src/thin_owner.py", "explicit-path", "user-provided-path"),
            ]
            candidates = navigator_scope.candidates_from_seeds(self.root, seeds, ["bug"])
            frames = [
                {"display_id": "REQ-01", "requirement_id": "REQ-01",
                 "statement": "Fix owner behavior.", "query_terms": ["owner", "behavior"]},
                {"display_id": "REQ-02", "requirement_id": "REQ-02",
                 "statement": "Fix thin owner behavior.", "query_terms": ["thin", "behavior"]},
            ]
            limits = navigator_scope.InvestigationLimits(
                initial_file_reads=0, escalation_file_reads=0, relationship_file_reads=0)
            investigated, edges, investigation = navigator_scope.investigate(
                self.root, frames, candidates, ["bug"], limits=limits)
        finally:
            navigator_scope.LIMITS["initial_file_reads"] = original_budget
        goal = "Fix owner behavior. Fix thin owner behavior."
        evidence = navigator_scope.evidence_document(
            self.root, goal, frames, investigated, edges=edges, investigation=investigation)
        self.assertEqual(evidence["state"], "ambiguous")
        packet = navigator_scope.host_reasoning_packet(evidence)
        self.assertEqual(packet["route"]["state"], "requested")
        proposal, errors = navigator_scope.proposal_from_scope_answers(
            self.root, packet,
            ["REQ-01=src/owner.py", "REQ-02=src/thin_owner.py"], 1, "codex")
        self.assertEqual(errors, [])
        assert proposal is not None
        return evidence, packet, proposal

    def _drifted(self, packet: dict[str, Any]) -> dict[str, Any]:
        """A packet as a second CLI call might recompute it: same goal, new identity."""
        drifted = copy.deepcopy(packet)
        drifted["candidates"] = [
            *drifted.get("candidates", []),
            {"path": "src/phantom.py", "role": "unknown", "status": "inspection-only"},
        ]
        drifted.pop("packet_fingerprint", None)
        drifted["packet_fingerprint"] = _fingerprint(drifted)
        self.assertNotEqual(drifted["packet_fingerprint"], packet["packet_fingerprint"])
        return drifted

    def test_ticket_save_load_roundtrip(self) -> None:
        _, packet, _ = self._ambiguous_flow()
        ticket = navigator_scope.save_host_packet(self.root, packet)
        self.assertEqual(ticket, packet["packet_fingerprint"])
        loaded = navigator_scope.load_host_packet(self.root, ticket)
        self.assertEqual(loaded, packet)

    def test_ticket_accepts_despite_fresh_packet_drift(self) -> None:
        """Call-2 drift must not reject a proposal built against the call-1 packet."""
        evidence, packet, proposal = self._ambiguous_flow()
        navigator_scope.save_host_packet(self.root, packet)
        # The old behavior, validated against a drifted recompute, rejects:
        drifted = self._drifted(packet)
        stale = navigator_scope.validate_host_proposal(self.root, drifted, proposal)
        self.assertEqual(stale["status"], "rejected")
        # The ticket path validates against the saved packet and accepts:
        decision = navigator_scope.host_proposal_decision(self.root, evidence, proposal)
        self.assertEqual(decision["status"], "accepted", decision["reason_codes"])
        self.assertFalse(any("mismatch" in code for code in decision["reason_codes"]))

    def test_consumed_ticket_is_single_use(self) -> None:
        evidence, packet, proposal = self._ambiguous_flow()
        ticket = navigator_scope.save_host_packet(self.root, packet)
        assert isinstance(ticket, str)
        first = navigator_scope.host_proposal_decision(self.root, evidence, proposal)
        self.assertEqual(first["status"], "accepted")
        ticket_file = navigator_scope.host_packet_dir(self.root) / (ticket.replace(":", "_") + ".json")
        self.assertTrue(json.loads(ticket_file.read_text(encoding="utf-8"))["consumed"])
        # A replay no longer sees a live ticket: with a drifted fresh packet it
        # falls back to the mismatch error naming both fingerprints.
        drifted = self._drifted(packet)
        with mock.patch.object(navigator_scope, "host_reasoning_packet", return_value=drifted):
            second = navigator_scope.host_proposal_decision(self.root, evidence, proposal)
        self.assertEqual(second["status"], "rejected")
        mismatch = next(
            code for code in second["reason_codes"]
            if code.startswith("evidence-packet-fingerprint-mismatch:"))
        self.assertIn(ticket, mismatch)
        self.assertIn(drifted["packet_fingerprint"], mismatch)

    def test_tampered_ticket_file_reads_as_miss(self) -> None:
        _, packet, _ = self._ambiguous_flow()
        ticket = navigator_scope.save_host_packet(self.root, packet)
        assert isinstance(ticket, str)
        path = navigator_scope.host_packet_dir(self.root) / (ticket.replace(":", "_") + ".json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["packet"]["candidates"] = []
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        self.assertIsNone(navigator_scope.load_host_packet(self.root, ticket))

    def test_expired_ticket_reads_as_miss(self) -> None:
        _, packet, _ = self._ambiguous_flow()
        ticket = navigator_scope.save_host_packet(self.root, packet)
        assert isinstance(ticket, str)
        path = navigator_scope.host_packet_dir(self.root) / (ticket.replace(":", "_") + ".json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["issued_at"] = time.time() - navigator_scope.HOST_PACKET_TTL_SECONDS - 1
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        self.assertIsNone(navigator_scope.load_host_packet(self.root, ticket))

    def test_mismatch_error_names_both_fingerprints(self) -> None:
        _, packet, proposal = self._ambiguous_flow()
        drifted = self._drifted(packet)
        result = navigator_scope.validate_host_proposal(self.root, drifted, proposal)
        self.assertEqual(result["status"], "rejected")
        mismatch = next(
            code for code in result["errors"]
            if code.startswith("evidence-packet-fingerprint-mismatch:"))
        self.assertIn(str(proposal["evidence_packet_fingerprint"]), mismatch)
        self.assertIn(drifted["packet_fingerprint"], mismatch)

    def test_live_ticket_does_not_bless_changed_files(self) -> None:
        evidence, packet, proposal = self._ambiguous_flow()
        navigator_scope.save_host_packet(self.root, packet)
        target = self.root / "src" / "thin_owner.py"
        target.write_text("def thin():\n    return False\n", encoding="utf-8")
        decision = navigator_scope.host_proposal_decision(self.root, evidence, proposal)
        self.assertEqual(decision["status"], "rejected")
        self.assertTrue(any("stale-path-content" in code for code in decision["reason_codes"]))

    def test_decide_issues_no_ticket_by_default(self) -> None:
        self.write("src/owner.py", "def serve():\n    return True\n")
        plan = navigator.decide("Fix owner behavior.", self.root, ["src/owner.py"], "tailtrail")
        self.assertFalse(navigator_scope.host_packet_dir(self.root).exists())
        self.assertIsInstance(plan.get("scope_host_packet"), dict)

    def test_decide_persists_ticket_only_when_asked(self) -> None:
        self.write("src/owner.py", "def serve():\n    return True\n")
        plan = navigator.decide(
            "Fix owner behavior.", self.root, ["src/owner.py"], "tailtrail",
            persist_host_packet=True)
        packet = plan.get("scope_host_packet")
        self.assertIsInstance(packet, dict)
        self.assertEqual(
            navigator_scope.load_host_packet(self.root, packet.get("packet_fingerprint")),
            packet)


if __name__ == "__main__":
    unittest.main()
