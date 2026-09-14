#!/usr/bin/env python3
"""Pipeline Manager for Sequential Worker Orchestration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import planning_lock as pl




import navigator_scope

@dataclass
class HandoffManifest:
    """Structured data transferred between pipeline stages."""
    from_stage: str
    to_stage: str
    change_manifest: list[str]  # List of modified files/symbols
    requirement_pointers: list[str]
    context: str
    evidence: list[dict[str, Any]] = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

class PipelineManager:
    """Orchestrates transitions between Sequential Workers."""
    
    def __init__(self, root: Path, run_id: str):
        self.root = root
        self.run_id = run_id
        self.L = pl.L # Expose the ledger for the orchestrator
        self.lock_path = pl.lock_path(root, run_id)

    def get_current_stage(self) -> str:
        lock = pl.show(self.root, self.run_id)
        return lock.get("pipeline", {}).get("active_stage", "PENDING")

    def set_stage(self, stage: str) -> None:
        """Update the active stage in the Planning Lock."""
        lock = pl.show(self.root, self.run_id)
        lock["pipeline"]["active_stage"] = stage
        pl.L.atomic_json(self.lock_path, lock)

    def complete_stage(self, stage: str, manifest: HandoffManifest) -> str | None:
        """Mark a stage as complete and trigger handoff to the next."""
        lock = pl.show(self.root, self.run_id)
        pipeline = lock["pipeline"]
        
        if stage not in pipeline["completed_stages"]:
            pipeline["completed_stages"].append(stage)
        
        # Store handoffs as a history rather than a single current manifest
        if "handoff_history" not in pipeline:
            pipeline["handoff_history"] = []
        
        pipeline["handoff_history"].append({
            "stage": stage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "manifest": manifest.as_dict()
        })
        
        pipeline["last_handoff"] = manifest.as_dict()
        pl.L.atomic_json(self.lock_path, lock)
        
        # Determine next stage in sequence
        sequence = pipeline["stage_sequence"]
        try:
            current_idx = sequence.index(stage)
            if current_idx + 1 < len(sequence):
                next_stage = sequence[current_idx + 1]
                self.set_stage(next_stage)
                return next_stage
        except ValueError:
            pass
        
        return None

    def trigger_regression(self, reason: str, evidence: list[dict[str, Any]]) -> str:
        """Handle a test failure by returning to the Implementation stage."""
        # Regression always returns to the first logic stage: IMPLEMENTATION
        self.set_stage("IMPLEMENTATION")
        
        lock = pl.show(self.root, self.run_id)
        lock["pipeline"]["last_regression"] = {
            "reason": reason,
            "evidence": evidence
        }
        pl.L.atomic_json(self.lock_path, lock)
        return "IMPLEMENTATION"

    def get_active_contract(self) -> navigator_scope.WorkerContract:
        """Retrieve the permission contract for the current active stage."""
        stage = self.get_current_stage()
        if stage not in navigator_scope.WORKER_CONTRACTS:
            # Default to a very restrictive contract if stage is PENDING or unknown
            return navigator_scope.WorkerContract(
                allowed_write_roles=set(),
                prohibited_write_roles=navigator_scope.ROLES,
                read_access="all"
            )
        return navigator_scope.WORKER_CONTRACTS[stage]
