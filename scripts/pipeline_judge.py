#!/usr/bin/env python3
"""The Deterministic Judge for Sequential Worker Enforcement."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import navigator_scope
from pipeline_manager import PipelineManager

class PipelineJudge:
    """Enforces the Sequential Badge constraints on every action."""
    
    def __init__(self, root: Path, run_id: str):
        self.root = root
        self.run_id = run_id
        self.manager = PipelineManager(root, run_id)

    def validate_write_access(self, path: str) -> tuple[bool, str | None]:
        """
        Verify if the current active worker has permission to edit the given path.
        Returns (is_allowed, error_message).
        """
        # 1. Get the active contract (Badge)
        contract = self.manager.get_active_contract()
        
        # 2. Determine the repository role of the target path
        role, _ = navigator_scope.classify_repository_role(self.root, path)
        
        # 3. check Prohibited Roles (Hard Block)
        if role in contract.prohibited_write_roles:
            return False, f"Write access denied: Path `{path}` is a `{role}`, which is prohibited for the active stage `{self.manager.get_current_stage()}`."
        
        # 4. Check Allowed Roles
        if role not in contract.allowed_write_roles:
            return False, f"Write access denied: Path `{path}` is a `{role}`, which is not in the allowed write-set for the active stage `{self.manager.get_current_stage()}`."
        
        return True, None

    def verify_stage_transition(self, from_stage: str, to_stage: str, evidence: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validates the transition between stages. 
        For TESTING -> INFRA, it must perform a Drift Analysis check.
        """
        if from_stage == "TESTING" and to_stage == "INFRA":
            return self._check_drift_gate(evidence)
        
        return True, None

    def _check_drift_gate(self, evidence: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Ensures that the implementation hasn't drifted from requirements 
        just to pass the tests.
        """
        # Primary check: drift analysis module
        try:
            import drift_analysis
            result = drift_analysis.analyze(self.root, self.run_id)
            if result.get("drift_detected"):
                return False, f"Stage transition blocked: Requirement drift detected. The current fix violates original requirements."
        except ImportError:
            pass
        
        # Fallback check: ensure requirement_pointers are present in evidence
        # This prevents "coding for the test" without genuine requirement implementation
        requirement_pointers = evidence.get("requirement_pointers", [])
        if not requirement_pointers:
            return False, "Stage transition blocked: Drift detected - no requirement pointers present for TESTING -> INFRA transition."
        
        return True, None
