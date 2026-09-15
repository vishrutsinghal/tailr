#!/usr/bin/env python3
"""High-level orchestrator for Sequential Worker Slicing and Loop Control."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict

import planning_lock as pl
from pipeline_manager import PipelineManager, HandoffManifest
from pipeline_judge import PipelineJudge

ROOT = Path(__file__).resolve().parents[1]

# Design §10.1: classify a test failure before routing it. Mechanical
# failures (syntax/compile) get a direct handoff to the Implementation
# Worker without consuming the regression budget; behavioral failures
# contradict expected behavior and consume a loop iteration; environmental
# failures are diagnosed read-only with no stage change.
MECHANICAL_MARKERS = ("SYNTAX", "PARSE", "COMPILE", "INDENT")
_BUDGET_CLASSIFICATIONS = {"code", "unknown"}
_REGRESSION_LIMIT = 3


def _execution_failure_classify(error_code: str) -> dict[str, str]:
    """Reuse scripts/execution-failure.py's keyword classification when loadable."""
    try:
        import execution_failure  # type: ignore

        return execution_failure.classify(error_code)
    except Exception:
        pass
    try:
        spec = importlib.util.spec_from_file_location(
            "pipeline_execution_failure", ROOT / "scripts" / "execution-failure.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to load scripts/execution-failure.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module.classify(error_code)
    except Exception:
        return {
            "classification": "unknown",
            "confidence": "unknown",
            "basis": "classifier-unavailable",
        }


def classify_test_failure(error_code: str) -> dict[str, Any]:
    """Route a test failure before any regression (design §10.1).

    - `mechanical` (syntax/compile): handoff to the Implementation Worker
      without consuming the regression budget — rerunning the test is
      pointless until the code compiles.
    - `regression` (behavioral): the implementation contradicts expected
      behavior; consumes a regression-loop iteration.
    - `diagnose` (environment/infra/permission): no drift and no stage
      change; diagnose read-only before retrying.
    """
    code = str(error_code).strip().upper()
    if any(marker in code for marker in MECHANICAL_MARKERS):
        return {
            "classification": "mechanical",
            "route": "mechanical",
            "burns_regression_budget": False,
            "basis": "mechanical-marker",
        }
    observed = _execution_failure_classify(code)
    classification = str(observed.get("classification") or "unknown")
    if classification in _BUDGET_CLASSIFICATIONS:
        return {
            "classification": classification,
            "route": "regression",
            "burns_regression_budget": True,
            "basis": str(observed.get("basis") or "stable-error-code"),
        }
    return {
        "classification": classification,
        "route": "diagnose",
        "burns_regression_budget": False,
        "basis": str(observed.get("basis") or "stable-error-code"),
    }

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

    def handle_regression(
        self,
        reason: str,
        evidence: list[dict[str, Any]],
        error_code: str | None = None,
    ) -> str:
        """Classify a test failure and route it (design §10.1)."""
        if error_code:
            decision = classify_test_failure(error_code)
        else:
            # Backward-compatible default: unclassified failures stay
            # conservative and consume the regression budget.
            decision = {
                "classification": "unknown",
                "route": "regression",
                "burns_regression_budget": True,
                "basis": "no-error-code-supplied",
            }

        lock = pl.show(self.root, self.run_id)

        if decision["route"] == "diagnose":
            # Environmental/infra/permission failure: no drift, no stage
            # change. Diagnose read-only before rerunning the tests.
            lock["pipeline"]["last_regression"] = {
                "reason": reason,
                "evidence": evidence,
                "route": "diagnose",
                "classification": decision["classification"],
            }
            pl.L.atomic_json(self.manager.lock_path, lock)
            return (
                f"Diagnosis required before retry: {reason} "
                f"(classified `{decision['classification']}`). "
                "Stage unchanged; diagnose read-only before rerunning the tests."
            )

        if decision["route"] == "mechanical":
            # Syntax/compile failure: the fix belongs to the Implementation
            # Worker (test-badge cannot edit production), but it is a
            # mechanical fix, not a design regression — no budget consumed.
            self.manager.set_stage("IMPLEMENTATION")
            lock = pl.show(self.root, self.run_id)
            lock["pipeline"]["last_regression"] = {
                "reason": reason,
                "evidence": evidence,
                "route": "mechanical",
                "classification": decision["classification"],
            }
            pl.L.atomic_json(self.manager.lock_path, lock)
            return (
                f"Mechanical fix handoff: {reason}. Returned to IMPLEMENTATION "
                "without consuming the regression budget."
            )

        # Regression route: behavioral failure contradicting expected behavior.
        regressions = lock.get("pipeline", {}).get("regression_count", 0)
        if regressions >= _REGRESSION_LIMIT:
            return "CIRCUIT BREAKER TRIGGERED: Too many implementation-testing loops. Manual design review required."

        # Increment regression count
        lock["pipeline"]["regression_count"] = regressions + 1
        pl.L.atomic_json(self.manager.lock_path, lock)

        next_stage = self.manager.trigger_regression(reason, evidence)
        # trigger_regression records {reason, evidence}; tag the route for audit.
        lock = pl.show(self.root, self.run_id)
        last = lock["pipeline"].get("last_regression")
        if isinstance(last, dict):
            last["route"] = "regression"
            last["classification"] = decision["classification"]
            pl.L.atomic_json(self.manager.lock_path, lock)
        return f"Regression triggered: {reason}. Returning to {next_stage} for correction."
