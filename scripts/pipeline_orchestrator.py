#!/usr/bin/env python3
"""High-level orchestrator for Sequential Worker Slicing and Loop Control."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict

import planning_lock as pl
from pipeline_manager import PipelineManager, HandoffManifest
from pipeline_judge import PipelineJudge

class PipelineOrchestrator:
    """Handles the execution of sequential slices and the circuit breaker."""
    
    def __init__(self, root: Path, run_id: str):
        self.root = root
        self.run_id = run_id
        self.manager = PipelineManager(root, run_id)
        self.judge = PipelineJudge(root, run_id)

    def resolve_next_slice(self) -> str:
        """Determine the current active slice for the agent."""
        return self.manager.get_current_stage()

    def request_handoff(self, from_stage: str, manifest_data: dict[str, Any]) -> str | None:
        """Process a request to move to the next stage."""
        # 1. Validate the manifest and transform to typed object
        try:
            manifest = HandoffManifest(
                from_stage=from_stage,
                to_stage=self.manager.get_current_stage(), # Simplified for now
                change_manifest=manifest_data.get("change_manifest", []),
                requirement_pointers=manifest_data.get("requirement_pointers", []),
                context=manifest_data.get("context", ""),
                evidence=manifest_data.get("evidence", [])
            )
        except Exception as e:
            return f"Handoff failed: Invalid manifest data - {str(e)}"

        # 2. If moving from TESTING -> INFRA, trigger the Drift Gate
        if from_stage == "TESTING":
            allowed, error = self.judge.verify_stage_transition("TESTING", "INFRA", manifest_data)
            if not allowed:
                return f"Stage transition blocked: {error}"

        # 3. Perform the transition
        next_stage = self.manager.complete_stage(from_stage, manifest)
        if next_stage:
            return f"Slicing successful. Transitioned to {next_stage}. New badge active."
        
        return "Pipeline complete. All stages verified."

    def handle_regression(self, reason: str, evidence: list[dict[str, Any]]) -> str:
        """Triggers the circuit-breaker logic and returns to Implementation."""
        # Check if we have exceeded the loop limit (3 iterations)
        lock = pl.show(self.root, self.run_id) # Use pl.show instead of manager.L.show
        regressions = lock.get("pipeline", {}).get("regression_count", 0)
        
        if regressions >= 3:
            return "CIRCUIT BREAKER TRIGGERED: Too many implementation-testing loops. Manual design review required."
        
        # Increment regression count
        lock["pipeline"]["regression_count"] = regressions + 1
        pl.L.atomic_json(self.manager.lock_path, lock)
        
        next_stage = self.manager.trigger_regression(reason, evidence)
        return f"Regression triggered: {reason}. Returning to {next_stage} for correction."
