# TailTrail Closure Report - Full Execution Record

| Field | Value |
|---|---|
| Run ID | `start-20261027101501-5f1c2b` |
| Generated after finalization | `2026-10-30T17:16:50.761489` |
| Overall status | `complete` |
| Closure record | `closure-d708d8ef77e53a95` |
| Finalizer | `finalizer-37621ca5ffd45b0d` |

## Changes And Locations

| Path / location | Recorded status |
|---|---|
| unavailable | No changed-path evidence was recorded |

## Requirement Verification

```json
{
  "complete": 4,
  "requirements": [
    {
      "display_id": "REQ-01",
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-76fd0b4d5a49"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.json",
          "asserted_behavior": "Trace current Start, AIDLC, scope, proof, receipt, audit, report, and Closure paths.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
          "command_label": "phase0-trace",
          "duration_ms": 602,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-28T08:42:57.744952+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-76fd0b4d5a49"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-28T08:42:57.141769+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.stderr.txt",
          "stderr_sha256": "sha256:15f013d9dad1430a1a1566d2414c357ec40d6ffe61ef4981433ea85ae064daa6",
          "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "unit",
          "tiers": [
            "unit"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "not-evidenced",
      "requirement_uid": "req-76fd0b4d5a49",
      "statement": "Trace current Start, AIDLC, scope, proof, receipt, audit, report, and Closure paths.",
      "status": "complete",
      "verification_status": "pass"
    },
    {
      "display_id": "REQ-02",
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-5ff71737d19c"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.json",
          "asserted_behavior": "Map each requirement to its current schema, writer, reader, CLI route, tests, and identified gap.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_host_question_flow_phase0_artifacts tests.test_host_input_contract_schema tests.test_host_question_flow_event_schema tests.test_public_route_gate tests.test_start_plan_presentation tests.test_completion_policy",
          "command_label": "phase0-mapping",
          "duration_ms": 3720,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-28T08:43:04.343341+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-5ff71737d19c"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-28T08:43:00.622029+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.stderr.txt",
          "stderr_sha256": "sha256:88523b9cf24f5ac66b9b5686675064573fb420348a09c1414c469350281fb0d4",
          "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "contract",
          "tiers": [
            "contract"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "not-evidenced",
      "requirement_uid": "req-5ff71737d19c",
      "statement": "Map each requirement to its current schema, writer, reader, CLI route, tests, and identified gap.",
      "status": "complete",
      "verification_status": "pass"
    },
    {
      "display_id": "REQ-03",
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-fdd46f6d2653"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.json",
          "asserted_behavior": "Deliver a hash-bound Phase 0 inventory/map artifact.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_completion_policy",
          "command_label": "phase0-delivery-policy",
          "duration_ms": 177,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-28T08:43:07.456468+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-fdd46f6d2653"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-28T08:43:07.278723+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.stderr.txt",
          "stderr_sha256": "sha256:172358797007957d0034e0c9b59820dbb3926be31f1162ce892415cc9026c089",
          "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "contract",
          "tiers": [
            "contract"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "not-evidenced",
      "requirement_uid": "req-fdd46f6d2653",
      "statement": "Deliver a hash-bound Phase 0 inventory/map artifact.",
      "status": "complete",
      "verification_status": "pass"
    },
    {
      "display_id": "REQ-04",
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-629704e7144f"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.json",
          "asserted_behavior": "Make no source, scope-authority, receipt, or Meta-Harness behavior changes.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
          "command_label": "phase0-preservation",
          "duration_ms": 174,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-28T08:43:10.524739+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-629704e7144f"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-28T08:43:10.350397+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.stderr.txt",
          "stderr_sha256": "sha256:2427194493c40676324fa088e241afe15eebacfcdea1e08205d1f1ecb245a1a9",
          "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "unit",
          "tiers": [
            "unit"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "not-evidenced",
      "requirement_uid": "req-629704e7144f",
      "statement": "Make no source, scope-authority, receipt, or Meta-Harness behavior changes.",
      "status": "complete",
      "verification_status": "pass"
    }
  ],
  "total": 4
}
```

## Execution Timeline And Evidence

| Kind | Command / action | Outcome | Exit code | Duration ms | Requirements | Tiers |
|---|---|---|---|---|---|---|
| command-result | `python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v` | pass | 0 | 602 | ["req-76fd0b4d5a49"] | ["unit"] |
| command-result | `python3 -m unittest tests.test_host_question_flow_phase0_artifacts tests.test_host_input_contract_schema tests.test_host_question_flow_event_schema tests.test_public_route_gate tests.test_start_plan_presentation tests.test_completion_policy` | pass | 0 | 3720 | ["req-5ff71737d19c"] | ["contract"] |
| command-result | `python3 -m unittest tests.test_completion_policy` | pass | 0 | 177 | ["req-fdd46f6d2653"] | ["contract"] |
| command-result | `python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v` | pass | 0 | 174 | ["req-629704e7144f"] | ["unit"] |

## Tests, Harnesses, Health, Drift, And Failures

```json
{
  "architecture": {
    "findings": [],
    "required": false,
    "status": "not-assessed"
  },
  "assessments": {},
  "behaviour": {
    "findings": [],
    "required": false,
    "status": "not-assessed"
  },
  "correction": null,
  "drift": {
    "findings": [],
    "status": "none-unresolved"
  },
  "execution_failures": {
    "count": 0,
    "status": "none-recorded",
    "unresolved": []
  },
  "higher_tier_evidence": {
    "boundary": "The finalizer reads the current closure snapshot and accepts only trusted managed-command or attested artifact-backed higher-tier receipts.",
    "missing": [],
    "required": [
      {
        "requirement_uid": "req-5ff71737d19c",
        "tier": "contract"
      },
      {
        "requirement_uid": "req-fdd46f6d2653",
        "tier": "contract"
      }
    ],
    "status": "pass"
  },
  "maintainability": {},
  "pipeline": {
    "active_badge": "impl-badge",
    "active_stage": "IMPLEMENTATION",
    "completed_stages": [],
    "handoff_count": 0,
    "status": "badged",
    "unvisited_stages": [
      "TESTING",
      "INFRA"
    ]
  },
  "security": {},
  "tests": {
    "failed_or_unavailable_receipts": [],
    "findings": [],
    "passed_tiers": [
      "contract",
      "unit"
    ],
    "receipt_refs": [
      ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-1.json",
      ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-2.json",
      ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-3.json",
      ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-4.json"
    ],
    "receipts": [
      {
        "artifact_path": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.json",
        "asserted_behavior": "Trace current Start, AIDLC, scope, proof, receipt, audit, report, and Closure paths.",
        "closure_record_id": "closure-d708d8ef77e53a95",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
        "command_label": "phase0-trace",
        "duration_ms": 602,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-28T08:42:57.744952+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
        "requirement_uids": [
          "req-76fd0b4d5a49"
        ],
        "scenario_ids": [],
        "schema_version": "2",
        "started_at": "2026-10-28T08:42:57.141769+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.stderr.txt",
        "stderr_sha256": "sha256:15f013d9dad1430a1a1566d2414c357ec40d6ffe61ef4981433ea85ae064daa6",
        "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.stdout.txt",
        "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "tier": "unit",
        "tiers": [
          "unit"
        ],
        "type": "tailtrail-validation-evidence-receipt"
      },
      {
        "artifact_path": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.json",
        "asserted_behavior": "Map each requirement to its current schema, writer, reader, CLI route, tests, and identified gap.",
        "closure_record_id": "closure-d708d8ef77e53a95",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest tests.test_host_question_flow_phase0_artifacts tests.test_host_input_contract_schema tests.test_host_question_flow_event_schema tests.test_public_route_gate tests.test_start_plan_presentation tests.test_completion_policy",
        "command_label": "phase0-mapping",
        "duration_ms": 3720,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-28T08:43:04.343341+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
        "requirement_uids": [
          "req-5ff71737d19c"
        ],
        "scenario_ids": [],
        "schema_version": "2",
        "started_at": "2026-10-28T08:43:00.622029+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.stderr.txt",
        "stderr_sha256": "sha256:88523b9cf24f5ac66b9b5686675064573fb420348a09c1414c469350281fb0d4",
        "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.stdout.txt",
        "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "tier": "contract",
        "tiers": [
          "contract"
        ],
        "type": "tailtrail-validation-evidence-receipt"
      },
      {
        "artifact_path": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.json",
        "asserted_behavior": "Deliver a hash-bound Phase 0 inventory/map artifact.",
        "closure_record_id": "closure-d708d8ef77e53a95",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest tests.test_completion_policy",
        "command_label": "phase0-delivery-policy",
        "duration_ms": 177,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-28T08:43:07.456468+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
        "requirement_uids": [
          "req-fdd46f6d2653"
        ],
        "scenario_ids": [],
        "schema_version": "2",
        "started_at": "2026-10-28T08:43:07.278723+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.stderr.txt",
        "stderr_sha256": "sha256:172358797007957d0034e0c9b59820dbb3926be31f1162ce892415cc9026c089",
        "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.stdout.txt",
        "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "tier": "contract",
        "tiers": [
          "contract"
        ],
        "type": "tailtrail-validation-evidence-receipt"
      },
      {
        "artifact_path": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.json",
        "asserted_behavior": "Make no source, scope-authority, receipt, or Meta-Harness behavior changes.",
        "closure_record_id": "closure-d708d8ef77e53a95",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
        "command_label": "phase0-preservation",
        "duration_ms": 174,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-28T08:43:10.524739+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
        "requirement_uids": [
          "req-629704e7144f"
        ],
        "scenario_ids": [],
        "schema_version": "2",
        "started_at": "2026-10-28T08:43:10.350397+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.stderr.txt",
        "stderr_sha256": "sha256:2427194493c40676324fa088e241afe15eebacfcdea1e08205d1f1ecb245a1a9",
        "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.stdout.txt",
        "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "tier": "unit",
        "tiers": [
          "unit"
        ],
        "type": "tailtrail-validation-evidence-receipt"
      }
    ],
    "required_checks": [],
    "status": "pass",
    "tier_results": {
      "contract": "pass",
      "unit": "pass"
    },
    "unverified_receipts": []
  }
}
```

## Token Usage

```json
{
  "actual_tailtrail_tokens": null,
  "boundary": "Exact usage comes only from host/provider metadata linked to this run ID. Exact savings additionally require a paired loose-prompt or AIDLC baseline for the same provider and model.",
  "comparisons": {
    "aidlc": {
      "reason": "TailTrail host/API usage is not linked to this run.",
      "status": "unavailable"
    },
    "loose-prompt": {
      "reason": "TailTrail host/API usage is not linked to this run.",
      "status": "unavailable"
    }
  },
  "context_estimate": {
    "boundary": "Relevant source, test, manifest, and configuration files; dependency, VCS, generated, build, coverage, TailTrail state, and known vendor directories are excluded.",
    "comparison_basis": "legacy-repository-ceiling",
    "estimated_reduction_percent": null,
    "estimated_saved_tokens": 0,
    "forecast_confidence": "low",
    "learning_evidence_references": [],
    "planned_working_set_tokens": null,
    "repository_ceiling_tokens": 2343238,
    "repository_file_count": 983,
    "saving_techniques": [
      "Focused validation selection"
    ],
    "scoped_file_ceiling_tokens": 0,
    "scoped_tokens": 0,
    "status": "estimated"
  },
  "planning_estimate_tokens": 0,
  "status": "unavailable",
  "telemetry_records": 0
}
```
Measured values are shown only when linked host/provider telemetry exists. Estimates retain their saved provenance; missing measurements remain unavailable.

## Command Reference Registry

Single-source-of-truth reference for all proof commands.

| ID | Kind | Command |
|---|---|---|
| `cmd-103fc3` | proof | `python3 -m unittest discover -s tests -p test_host_question_flow_phase...` |
| `cmd-7432b4` | proof | `python3 -m unittest tests.test_host_question_flow_phase0_artifacts tes...` |
| `cmd-a06819` | proof | `python3 -m unittest tests.test_completion_policy` |


## TailTrail Lifecycle And Audit Events

```json
[
  {
    "created_at": "2026-10-27T10:15:13+00:00",
    "event_id": "evt-0001-7eec182eb8340c99",
    "event_type": "run_created",
    "payload": {
      "goal": "Complete Phase 0 \u2014 Inventory and Ownership for the Host\u2013TailTrail Evidence Validation Contract: trace the current Start, AIDLC, scope, proof, receipt, audit, report, Closure, and Meta-Harness paths; map every design requirement to its current schema, writer, reader, CLI route, focused test, and explicit reuse-or-gap decision; deliver a hash-bound Phase 0 inventory/map artifact; make no source, scope-authority, receipt, or Meta-Harness behavior changes."
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 1,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T10:15:13+00:00",
    "event_id": "evt-0002-031f3d89072faa28",
    "event_type": "planning_lock_created",
    "payload": {
      "artifact": "planning/lock-v1.json",
      "input_roles": {
        "read_only_inputs": 1
      },
      "reference_roots": [],
      "target_fingerprint": "sha256:791d2db9cecbfe080226bed62d29199fe85f5c3373391f50ee1ff9cbb63eda48",
      "writes_allowed": false
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 2,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T10:15:13+00:00",
    "event_id": "evt-0003-a933d5eeb1655a43",
    "event_type": "target_resolution_recorded",
    "payload": {
      "policy_status": "not-configured",
      "target_resolution_receipt": ".tailtrail/runs/start-20261027101501-5f1c2b/planning/target-resolution-receipt-v1.json"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 3,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T10:15:13+00:00",
    "event_id": "evt-0004-57edc3777ae33a76",
    "event_type": "start_report_saved",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/planning/start-report-v1.json"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 4,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T10:15:13+00:00",
    "event_id": "evt-0005-8b683b0e4811c346",
    "event_type": "start_plan_verbose_generated",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/verbose-reports/start-plan-verbose-v1.md",
      "mandatory": true,
      "markdown_size": 11609,
      "status": "verified",
      "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027101501-5f1c2b/start-plan.md",
      "visible_artifact": "session-reports/start-20261027101501-5f1c2b/start-plan.md"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 5,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T10:15:13+00:00",
    "event_id": "evt-0006-ff1ce897e3352213",
    "event_type": "tailtrail_session_attached",
    "payload": {
      "context_key_hash": "sha256:8f7ea5b4e0bf204739b270db4b34f3ff3560126663ca15a47c97490c5a4c8b70",
      "fingerprint": "sha256:2bedc30e20b1f08b8170f6c57a393ef69cb1468dbb97475cdece1cb2c6ee967d",
      "generation": 286,
      "reason_code": "tailtrail-start"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 6,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T10:15:23+00:00",
    "event_id": "evt-0007-25e0f147a6e6bd3b",
    "event_type": "planning_audit_completed",
    "payload": {
      "finding_count": 3,
      "revision_cycles": 0,
      "status": "gaps-found",
      "total_review_cycles": 1
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 7,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T10:16:45+00:00",
    "event_id": "evt-0008-72d8163be341b541",
    "event_type": "planning_revision_proposed",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/planning/revisions/revision-v2.json",
      "base_revision": 1,
      "requirement_uids": [
        "req-5ff71737d19c",
        "req-fdd46f6d2653"
      ],
      "revision": 2
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 8,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T10:16:50+00:00",
    "event_id": "evt-0009-529afc8527c405d6",
    "event_type": "planning_audit_completed",
    "payload": {
      "finding_count": 0,
      "revision_cycles": 1,
      "status": "clean",
      "total_review_cycles": 2
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 9,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:27+00:00",
    "event_id": "evt-0010-19a75277a03808b2",
    "event_type": "anchor_drafted",
    "payload": {
      "fingerprint": "sha256:c0daeb8feb97d70f942180344f79d8d45e848f3246dabf7517cda870fa1d9c89",
      "proposal_version": 1,
      "requirements": [
        "req-76fd0b4d5a49",
        "req-5ff71737d19c",
        "req-fdd46f6d2653",
        "req-629704e7144f"
      ]
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 10,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:27+00:00",
    "event_id": "evt-0011-2a794a7abe2917fb",
    "event_type": "anchor_approved",
    "payload": {
      "fingerprint": "sha256:95d776c1515b9cf4b6d717a8a07d76a404a2850fbb1c3d6d56e67e6dc2c4cd4a",
      "path": ".tailtrail/runs/start-20261027101501-5f1c2b/anchors/approved-v1.json",
      "requirements": [
        "req-76fd0b4d5a49",
        "req-5ff71737d19c",
        "req-fdd46f6d2653",
        "req-629704e7144f"
      ]
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 11,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:27+00:00",
    "event_id": "evt-0012-538d002355d0d167",
    "event_type": "planning_lock_approved",
    "payload": {
      "artifact": "planning/lock-v1.json",
      "audit": {
        "report_fingerprint": "sha256:987ba11e23c5cf307f2a3db111f44cabc571f4d9ed5f1fbf8f3e3799444efbf2",
        "run_id": "start-20261027101501-5f1c2b",
        "source": "active-start-report",
        "status": "clean"
      },
      "writes_allowed": true
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 12,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:28+00:00",
    "event_id": "evt-0013-593260d35c615133",
    "event_type": "workflow_ownership_bound",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-7c025caa2418/ownership-v1.json",
      "requirement_uids": [
        "req-76fd0b4d5a49",
        "req-5ff71737d19c",
        "req-fdd46f6d2653",
        "req-629704e7144f"
      ],
      "workflow_id": "ttw-7c025caa2418"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 13,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:30+00:00",
    "event_id": "evt-0014-faf75a92ccc4da5e",
    "event_type": "workflow_capability_plan_declared",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-7c025caa2418/capability-plan-v1.json",
      "capability_ids": [
        "code-graph-mapper",
        "guardrails",
        "navigator",
        "review",
        "testing"
      ],
      "plan_fingerprint": "sha256:44e439acdcfae5978360344bbe7a36739c5155d65cbb67fb15c8331570d63585",
      "workflow_id": "ttw-7c025caa2418"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 14,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:31+00:00",
    "event_id": "evt-0015-60f6fab8d41535a0",
    "event_type": "workflow_storage_initialized",
    "payload": {
      "journal": ".tailtrail/workflows/ttw-7c025caa2418/journal-v1.jsonl",
      "projection": ".tailtrail/workflows/ttw-7c025caa2418/projection-v1.json",
      "workflow_id": "ttw-7c025caa2418"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 15,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:31+00:00",
    "event_id": "evt-0016-39a5cb41882b6870",
    "event_type": "workflow_state_created",
    "payload": {
      "journal": ".tailtrail/workflows/ttw-7c025caa2418/journal-v1.jsonl",
      "sequence": 2,
      "workflow_id": "ttw-7c025caa2418"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 16,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:40+00:00",
    "event_id": "evt-0017-1c3c919edb03f41a",
    "event_type": "workflow_compiler_plan_created",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-7c025caa2418/compiler-plan-v1.json",
      "plan_fingerprint": "sha256:6e020f5ecf1c46c78340de10b609cad900e3ae2424d3a6a43a51e52df2e9890a",
      "revision": 1,
      "template_id": "small-change",
      "workflow_id": "ttw-7c025caa2418"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 17,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:40+00:00",
    "event_id": "evt-0018-9c4fc772b7a75eb2",
    "event_type": "workflow_stage_approval_recorded",
    "payload": {
      "action_classes": [
        "write_tailtrail_state"
      ],
      "approval_id": "wfauth-48e60b5e6835db5fe70d9ab3",
      "decision": "approved",
      "operation_kind": "initial-plan",
      "source": "interactive",
      "stage_ids": [
        "bootstrap",
        "discover",
        "focused-test",
        "fulfilment",
        "implement",
        "review"
      ],
      "workflow_id": "ttw-7c025caa2418"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 18,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:40+00:00",
    "event_id": "evt-0019-d5fbf65d66cac75c",
    "event_type": "workflow_stage_approval_recorded",
    "payload": {
      "action_classes": [
        "execute_project",
        "read_local",
        "write_project",
        "write_tailtrail_state"
      ],
      "approval_id": "wfauth-2157a88d84ccb1aa075db786",
      "decision": "approved",
      "operation_kind": "other-guarded",
      "source": "plan-derived",
      "stage_ids": [
        "bootstrap",
        "discover",
        "focused-test",
        "fulfilment",
        "implement",
        "review"
      ],
      "workflow_id": "ttw-7c025caa2418"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 19,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:40+00:00",
    "event_id": "evt-0020-fc0a9ffe2a1abca9",
    "event_type": "workflow_runtime_activated",
    "payload": {
      "binding": ".tailtrail/workflows/ttw-7c025caa2418/ownership-v1.json",
      "capability_plan": ".tailtrail/workflows/ttw-7c025caa2418/capability-plan-v1.json",
      "compiler_plan": ".tailtrail/workflows/ttw-7c025caa2418/compiler-plan-v1.json",
      "compiler_plan_fingerprint": "sha256:6e020f5ecf1c46c78340de10b609cad900e3ae2424d3a6a43a51e52df2e9890a",
      "workflow_id": "ttw-7c025caa2418"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 20,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:40+00:00",
    "event_id": "evt-0021-f597264eda7a6c23",
    "event_type": "planning_activated",
    "payload": {
      "activation_audit": {
        "report_fingerprint": "sha256:987ba11e23c5cf307f2a3db111f44cabc571f4d9ed5f1fbf8f3e3799444efbf2",
        "run_id": "start-20261027101501-5f1c2b",
        "source": "active-start-report",
        "status": "clean"
      },
      "anchor": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/anchors/approved-v1.json",
        "requirements": [
          "req-76fd0b4d5a49",
          "req-5ff71737d19c",
          "req-fdd46f6d2653",
          "req-629704e7144f"
        ],
        "status": "created"
      },
      "enterprise_policy_status": "not-configured",
      "handoff": "planning/execution-handoff-v1.json",
      "input_role_status": "matched",
      "official_aidlc_bridge_activation": null,
      "scope_decision_status": "legacy",
      "target_identity_status": "matched",
      "workflow_runtime": "compiled"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 21,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:40+00:00",
    "event_id": "evt-0022-75454411c6d8f669",
    "event_type": "start_plan_verbose_generated",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/verbose-reports/start-plan-verbose-v1.md",
      "mandatory": true,
      "markdown_size": 11972,
      "status": "verified",
      "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027101501-5f1c2b/start-plan.md",
      "visible_artifact": "session-reports/start-20261027101501-5f1c2b/start-plan.md"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 22,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:38:40+00:00",
    "event_id": "evt-0023-5de33274c72601ef",
    "event_type": "planning_revision_approved",
    "payload": {
      "active_report": ".tailtrail/runs/start-20261027101501-5f1c2b/planning/revisions/start-report-v2.json",
      "anchor": ".tailtrail/runs/start-20261027101501-5f1c2b/anchors/approved-v1.json",
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/planning/revisions/revision-v2.json",
      "audit": {
        "report_fingerprint": "sha256:987ba11e23c5cf307f2a3db111f44cabc571f4d9ed5f1fbf8f3e3799444efbf2",
        "run_id": "start-20261027101501-5f1c2b",
        "source": "active-start-report",
        "status": "clean"
      },
      "revision": 2
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 23,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:42:59+00:00",
    "event_id": "evt-0024-d7a53bc6f01803cb",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/evidence-stream.jsonl",
      "fingerprint": "8a08730fea065a15",
      "kind": "command-result",
      "sequence": 1
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 24,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:43:05+00:00",
    "event_id": "evt-0025-b7fd096ecee054df",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/evidence-stream.jsonl",
      "fingerprint": "06a641a01c76808d",
      "kind": "command-result",
      "sequence": 2
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 25,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:43:08+00:00",
    "event_id": "evt-0026-f0ad9ae0883d5b6a",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/evidence-stream.jsonl",
      "fingerprint": "d83cadf085490f45",
      "kind": "command-result",
      "sequence": 3
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 26,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:43:11+00:00",
    "event_id": "evt-0027-5cf9e8e2f66bd3cf",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/evidence-stream.jsonl",
      "fingerprint": "3a730c05fdd0462f",
      "kind": "command-result",
      "sequence": 4
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 27,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:43:25+00:00",
    "event_id": "evt-0028-7f68394e2b39dfec",
    "event_type": "validation_delivery_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/validation-delivery/delivery-v1.json",
      "artifact_path": "TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-PHASE0-INVENTORY.md",
      "artifact_sha256": "237e1a32e97561f1cccba693874890348b5244b3e88612298d075d5b42d3faf5"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 28,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:43:40+00:00",
    "event_id": "evt-0029-b7665d73ab9629a5",
    "event_type": "harness_checkpoint",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/checkpoints/checkpoint-1.json",
      "checkpoint": 1,
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-76fd0b4d5a49"
        },
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-5ff71737d19c"
        },
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-fdd46f6d2653"
        },
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-629704e7144f"
        }
      ],
      "requirement_states": {
        "req-5ff71737d19c": "validated",
        "req-629704e7144f": "validated",
        "req-76fd0b4d5a49": "validated",
        "req-fdd46f6d2653": "validated"
      }
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 29,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:43:40+00:00",
    "event_id": "evt-0030-0d587d0f80c98131",
    "event_type": "completion_review",
    "payload": {
      "artifact": "reviews/review-1.json",
      "checkpoint": 1,
      "complete": true,
      "findings": 0
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 30,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:43:40+00:00",
    "event_id": "evt-0031-a658c71ce22f5ca1",
    "event_type": "completion_gate",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/completion-gates/gate-1.json",
      "complete": true,
      "findings": []
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 31,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:43:40+00:00",
    "event_id": "evt-0032-8fe98892d8a0c75c",
    "event_type": "closure_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/closure-records/closure-d708d8ef77e53a95.json",
      "checkpoint": 1,
      "gate_complete": true,
      "receipt_count": 4,
      "record_id": "closure-d708d8ef77e53a95",
      "review_complete": true
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 32,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-28T08:43:59+00:00",
    "event_id": "evt-0033-ecc225b2789bdc47",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-1.json",
      "completion_learning": "not-triggered",
      "harnesses": [
        {
          "name": "Requirement Completion Harness",
          "status": "pass",
          "used": true
        },
        {
          "name": "Architecture Fitness Harness",
          "status": "not-selected",
          "used": false
        },
        {
          "name": "Behaviour Harness",
          "status": "not-selected",
          "used": false
        },
        {
          "name": "Maintainability Harness",
          "status": "not-selected",
          "used": false
        },
        {
          "name": "Evidence-Aware Testing",
          "status": "pass",
          "used": true
        }
      ],
      "learning_use": "no-receipts",
      "overall_status": "complete"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 33,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T11:33:22+00:00",
    "event_id": "evt-0034-b5bf3d3cc0288017",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-2.json",
      "completion_learning": "not-triggered",
      "harnesses": [
        {
          "name": "Requirement Completion Harness",
          "status": "pass",
          "used": true
        },
        {
          "name": "Architecture Fitness Harness",
          "status": "not-selected",
          "used": false
        },
        {
          "name": "Behaviour Harness",
          "status": "not-selected",
          "used": false
        },
        {
          "name": "Maintainability Harness",
          "status": "not-selected",
          "used": false
        },
        {
          "name": "Evidence-Aware Testing",
          "status": "pass",
          "used": true
        }
      ],
      "learning_use": "no-receipts",
      "overall_status": "complete"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 34,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T11:33:25+00:00",
    "event_id": "evt-0035-02fb47760f5c92b3",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-3.json",
      "completion_learning": "not-triggered",
      "harnesses": [
        {
          "name": "Requirement Completion Harness",
          "status": "pass",
          "used": true
        },
        {
          "name": "Architecture Fitness Harness",
          "status": "not-selected",
          "used": false
        },
        {
          "name": "Behaviour Harness",
          "status": "not-selected",
          "used": false
        },
        {
          "name": "Maintainability Harness",
          "status": "not-selected",
          "used": false
        },
        {
          "name": "Evidence-Aware Testing",
          "status": "pass",
          "used": true
        }
      ],
      "learning_use": "no-receipts",
      "overall_status": "complete"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 35,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T11:33:28+00:00",
    "event_id": "evt-0036-679a531ad05ef623",
    "event_type": "navigator_graph_lifecycle_recorded",
    "payload": {
      "action": "defer",
      "cache_fingerprint": "sha256:a2c9823b6760f6ffedeef00414f5821304829f67763981db8b2e36943624db80",
      "mapping_fingerprint": null,
      "phase": "closure"
    },
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "sequence": 36,
    "type": "tailtrail-run-event"
  }
]
```

## Complete Saved Closure Payload

```json
{
  "assessments": {},
  "boundary": "Finalized deterministic local control evidence only. No receipt command, deployment, recovery action, or external environment was executed.",
  "changed_paths": [],
  "closure_record": {
    "boundary": "Recorded validated evidence. Managed-command receipts were executed and captured by TailTrail; declared host receipts remain explicitly unverified.",
    "changed_paths": [],
    "checkpoint": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261027101501-5f1c2b/checkpoints/checkpoint-1.json",
    "completion_gate": {
      "complete": true,
      "findings": [],
      "rule": "Only trusted managed-command or attested artifact-backed evidence can pass a tier; any reported non-pass blocks and authoritative failure dominates pass.",
      "run_artifact": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261027101501-5f1c2b/completion-gates/gate-1.json",
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "2",
      "type": "tailtrail-requirement-completion-gate"
    },
    "completion_policy": {
      "boundary": "Policy derived from the persisted host contract. Missing or stale artifacts are never reported as complete.",
      "implementation_applicable": true,
      "missing": [],
      "recovery": "",
      "request_mode": null,
      "required_artifacts": [],
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "source_edit_required": false,
      "status": "not-applicable",
      "type": "tailtrail-completion-policy"
    },
    "completion_review": {
      "checkpoint": 1,
      "complete": true,
      "findings": [],
      "next_action": "none",
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "type": "tailtrail-completion-review"
    },
    "next_action": "Run tailtrail completion-report for this run.",
    "proof_amendment_artifact": null,
    "receipt_artifacts": [
      ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-1.json",
      ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-2.json",
      ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-3.json",
      ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-4.json"
    ],
    "record_id": "closure-d708d8ef77e53a95",
    "reused": true,
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "selected_harnesses": [
      "Canonical requirements",
      "Question Orchestrator",
      "Requirement Completion Harness",
      "Evidence-Aware Testing",
      "Test Precision Planner"
    ],
    "type": "tailtrail-closure-record",
    "validated_input": "execution/evidence-stream.jsonl"
  },
  "closure_record_id": "closure-d708d8ef77e53a95",
  "command_registry": {
    "cmd-103fc3": {
      "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
      "kind": "proof"
    },
    "cmd-7432b4": {
      "command": "python3 -m unittest tests.test_host_question_flow_phase0_artifacts tests.test_host_input_contract_schema tests.test_host_question_flow_event_schema tests.test_public_route_gate tests.test_start_plan_presentation tests.test_completion_policy",
      "kind": "proof"
    },
    "cmd-a06819": {
      "command": "python3 -m unittest tests.test_completion_policy",
      "kind": "proof"
    }
  },
  "completion_report": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261027101501-5f1c2b/completion-reports/report-3.json",
  "completion_report_payload": {
    "architecture": {
      "findings": [],
      "required": false,
      "status": "not-assessed"
    },
    "behaviour": {
      "findings": [],
      "required": false,
      "status": "not-assessed"
    },
    "boundary": "The report aggregates saved local artifacts. Missing or failed evidence is not reported as a pass.",
    "canonical_state": {
      "issues": [],
      "status": "valid",
      "valid": true
    },
    "changed_scope": {
      "changed_paths": [],
      "findings": [],
      "status": "approved"
    },
    "closure_guidance": {
      "managed_proof_passing": true,
      "missing": [
        {
          "action": "Record a `source-edit` execution-evidence event with the approved requirement UID and changed path, then rerun this Completion Report.",
          "artifact": "source-edit receipt"
        }
      ]
    },
    "completion_learning": {
      "artifact": null,
      "boundary": "No unresolved completion gap requires a learning candidate.",
      "event_id": null,
      "status": "not-triggered"
    },
    "completion_policy": {
      "boundary": "Policy derived from the persisted host contract. Missing or stale artifacts are never reported as complete.",
      "implementation_applicable": false,
      "missing": [],
      "recovery": "",
      "request_mode": "validation-only",
      "required_artifacts": [
        "validation-delivery"
      ],
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "source_edit_required": false,
      "status": "pass",
      "type": "tailtrail-completion-policy"
    },
    "debug": {
      "authority": "section-only",
      "confidence_state": null,
      "controls": [],
      "debug_status": "not-triggered",
      "domain_confidence_ceiling": null,
      "gaps": [],
      "reproduction_proof": {
        "approved_revision": null,
        "boundary": "Not a Debug Harness run.",
        "post_fix": null,
        "pre_fix": null,
        "status": "not-triggered",
        "steps": [],
        "trigger": null
      }
    },
    "drift": {
      "findings": [],
      "status": "none-unresolved"
    },
    "drift_learning": {
      "artifact": null,
      "boundary": "No unresolved drift was recorded.",
      "status": "none"
    },
    "evidence_label": "local-evidence",
    "execution_authority": {
      "approval_id": "wfauth-2157a88d84ccb1aa075db786",
      "auto_granted_action_classes": [
        "read_local",
        "write_tailtrail_state",
        "write_project",
        "execute_project"
      ],
      "boundary": "The approved Lite/Off plan grants only hash-bound safe local work inside the immutable anchor. Sensitive or materially divergent actions still require their designated authority.",
      "mode": "lite",
      "route": "approved-plan-auto-grant",
      "separate_gate_triggers": [
        "material-scope-change",
        "requirement-contradiction",
        "dependency",
        "recovery",
        "scan_local",
        "external_provider",
        "publish",
        "deploy",
        "merge"
      ],
      "status": "safe-local-execution-authorized"
    },
    "execution_failures": {
      "count": 0,
      "status": "none-recorded",
      "unresolved": []
    },
    "harnesses": [
      {
        "artifact": "checkpoints/checkpoint-1.json",
        "basis": "approved anchor + checkpoint + completion review + evidence gate",
        "name": "Requirement Completion Harness",
        "status": "pass",
        "used": true
      },
      {
        "artifact": null,
        "basis": "approved architecture contract or recorded architecture assessment",
        "name": "Architecture Fitness Harness",
        "status": "not-selected",
        "used": false
      },
      {
        "artifact": null,
        "basis": "recorded approved-scenario assessment",
        "name": "Behaviour Harness",
        "status": "not-selected",
        "used": false
      },
      {
        "artifact": null,
        "basis": "recorded refactor/maintainability assessment",
        "name": "Maintainability Harness",
        "status": "not-selected",
        "used": false
      },
      {
        "artifact": "completion-gates/gate-1.json",
        "basis": "completion gate and validation receipts",
        "name": "Evidence-Aware Testing",
        "status": "pass",
        "used": true
      }
    ],
    "implementation": {
      "blockers": [],
      "boundary": "Implementation presence is derived from saved changed-path evidence and approved scope. Verification is reported separately and only authoritative command evidence can establish correctness.",
      "changed_paths": [],
      "status": "not-applicable"
    },
    "learning_use": {
      "artifact": null,
      "associations": {},
      "attributed": 0,
      "boundary": "No learning use decision was recorded for this run; closure inferred no influence.",
      "decisions": 0,
      "status": "no-receipts",
      "undecided_proposals": []
    },
    "official_aidlc": {
      "evidence_checkpoint": null,
      "evidence_status": "not-triggered",
      "handoff_reference": null,
      "operations_references": [],
      "perspectives": [],
      "runtime": {
        "attached": false,
        "current_stage": null,
        "transition_count": 0
      }
    },
    "overall_status": "complete",
    "pipeline": {
      "active_badge": "impl-badge",
      "active_stage": "IMPLEMENTATION",
      "completed_stages": [],
      "handoff_count": 0,
      "status": "badged",
      "unvisited_stages": [
        "TESTING",
        "INFRA"
      ]
    },
    "plan": {
      "approved_additions": [
        {
          "artifact": "planning/revisions/start-report-v2.json",
          "kind": "approved-plan-revision",
          "revision": 2
        }
      ],
      "base_plan": {
        "artifact": "planning/start-report-v1.json",
        "revision": 1
      },
      "boundary": "The base plan remains immutable; approved revisions and additive proof amendments are reported as separate effective-plan inputs.",
      "effective_plan": {
        "active_artifact": "planning/revisions/start-report-v2.json",
        "active_revision": 2,
        "base_is_immutable": true
      }
    },
    "plan_evidence": {
      "boundary": "Receipts stamped with a superseded plan fingerprint prove nothing about the approved plan; re-run them after re-approval. Fingerprint-less legacy receipts keep historical behavior.",
      "current": 4,
      "current_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
      "legacy": 0,
      "stale": 0,
      "stale_commands": []
    },
    "positive_learning": {
      "artifact": null,
      "boundary": "Use tailtrail closure learn with explicit user or trusted-CI acceptance; completion alone never creates a reusable learning rule.",
      "status": "eligible-awaiting-acceptance"
    },
    "recovery_checkpoint": {
      "boundary": null,
      "status": "not-needed"
    },
    "requirement_status": {
      "complete": 4,
      "requirements": [
        {
          "display_id": "REQ-01",
          "drift": [
            {
              "category": "evidence",
              "classification": "resolved",
              "requirement_uid": "req-76fd0b4d5a49"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.json",
              "asserted_behavior": "Trace current Start, AIDLC, scope, proof, receipt, audit, report, and Closure paths.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
              "command_label": "phase0-trace",
              "duration_ms": 602,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-28T08:42:57.744952+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-76fd0b4d5a49"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-28T08:42:57.141769+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.stderr.txt",
              "stderr_sha256": "sha256:15f013d9dad1430a1a1566d2414c357ec40d6ffe61ef4981433ea85ae064daa6",
              "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.stdout.txt",
              "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              "tier": "unit",
              "tiers": [
                "unit"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "not-evidenced",
          "requirement_uid": "req-76fd0b4d5a49",
          "statement": "Trace current Start, AIDLC, scope, proof, receipt, audit, report, and Closure paths.",
          "status": "complete",
          "verification_status": "pass"
        },
        {
          "display_id": "REQ-02",
          "drift": [
            {
              "category": "evidence",
              "classification": "resolved",
              "requirement_uid": "req-5ff71737d19c"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.json",
              "asserted_behavior": "Map each requirement to its current schema, writer, reader, CLI route, tests, and identified gap.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_host_question_flow_phase0_artifacts tests.test_host_input_contract_schema tests.test_host_question_flow_event_schema tests.test_public_route_gate tests.test_start_plan_presentation tests.test_completion_policy",
              "command_label": "phase0-mapping",
              "duration_ms": 3720,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-28T08:43:04.343341+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-5ff71737d19c"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-28T08:43:00.622029+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.stderr.txt",
              "stderr_sha256": "sha256:88523b9cf24f5ac66b9b5686675064573fb420348a09c1414c469350281fb0d4",
              "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.stdout.txt",
              "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              "tier": "contract",
              "tiers": [
                "contract"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "not-evidenced",
          "requirement_uid": "req-5ff71737d19c",
          "statement": "Map each requirement to its current schema, writer, reader, CLI route, tests, and identified gap.",
          "status": "complete",
          "verification_status": "pass"
        },
        {
          "display_id": "REQ-03",
          "drift": [
            {
              "category": "evidence",
              "classification": "resolved",
              "requirement_uid": "req-fdd46f6d2653"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.json",
              "asserted_behavior": "Deliver a hash-bound Phase 0 inventory/map artifact.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_completion_policy",
              "command_label": "phase0-delivery-policy",
              "duration_ms": 177,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-28T08:43:07.456468+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-fdd46f6d2653"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-28T08:43:07.278723+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.stderr.txt",
              "stderr_sha256": "sha256:172358797007957d0034e0c9b59820dbb3926be31f1162ce892415cc9026c089",
              "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.stdout.txt",
              "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              "tier": "contract",
              "tiers": [
                "contract"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "not-evidenced",
          "requirement_uid": "req-fdd46f6d2653",
          "statement": "Deliver a hash-bound Phase 0 inventory/map artifact.",
          "status": "complete",
          "verification_status": "pass"
        },
        {
          "display_id": "REQ-04",
          "drift": [
            {
              "category": "evidence",
              "classification": "resolved",
              "requirement_uid": "req-629704e7144f"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.json",
              "asserted_behavior": "Make no source, scope-authority, receipt, or Meta-Harness behavior changes.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
              "command_label": "phase0-preservation",
              "duration_ms": 174,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-28T08:43:10.524739+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-629704e7144f"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-28T08:43:10.350397+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.stderr.txt",
              "stderr_sha256": "sha256:2427194493c40676324fa088e241afe15eebacfcdea1e08205d1f1ecb245a1a9",
              "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.stdout.txt",
              "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              "tier": "unit",
              "tiers": [
                "unit"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "not-evidenced",
          "requirement_uid": "req-629704e7144f",
          "statement": "Make no source, scope-authority, receipt, or Meta-Harness behavior changes.",
          "status": "complete",
          "verification_status": "pass"
        }
      ],
      "total": 4
    },
    "run_artifact": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261027101501-5f1c2b/completion-reports/report-3.json",
    "run_id": "start-20261027101501-5f1c2b",
    "schema_version": "1",
    "session_reports": {
      "closure": {
        "absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027101501-5f1c2b/closure-report.md",
        "exists": false,
        "workspace_path": "session-reports/start-20261027101501-5f1c2b/closure-report.md"
      },
      "start": {
        "absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027101501-5f1c2b/start-plan.md",
        "exists": true,
        "workspace_path": "session-reports/start-20261027101501-5f1c2b/start-plan.md"
      }
    },
    "source_artifacts": {
      "active_plan": "planning/revisions/start-report-v2.json",
      "approved_anchor": "anchors/approved-v1.json",
      "architecture": null,
      "base_plan": "planning/start-report-v1.json",
      "behaviour": null,
      "checkpoint": "checkpoints/checkpoint-1.json",
      "completion_gate": "completion-gates/gate-1.json",
      "completion_learning": null,
      "completion_review": "reviews/review-1.json",
      "debug_closure_section": null,
      "learning_use_receipts": null,
      "maintainability": null,
      "official_design": null,
      "official_evidence": null,
      "official_handoff": null,
      "positive_learning": null,
      "proof_amendments": null,
      "recovery_boundary": null
    },
    "stale_learnings": {
      "needs_backfill": [],
      "triggered": [
        "lrn-04fa0ce192147e05",
        "lrn-2bfef89b80f2713c",
        "lrn-2d2f1a18826c5009",
        "lrn-2dd27396c9cd3022",
        "lrn-39d6406267ee8097",
        "lrn-3efb535bedfa119f",
        "lrn-531e637cdff54461",
        "lrn-53f801a3afb6d044",
        "lrn-54e4c595d2d1f36a",
        "lrn-5a42321335867d06",
        "lrn-681b007f0c1878b8",
        "lrn-6ae0ccfc7ac706af",
        "lrn-7074aa8f8b7b72f4",
        "lrn-72e352d6459d61a6",
        "lrn-75278005a7c7933f",
        "lrn-761dc46db33a36e2",
        "lrn-88bc7405c5c9861b",
        "lrn-999c71f0d0ea5d33",
        "lrn-9d789ac8c51e41fe",
        "lrn-a51b56445a4ed47e",
        "lrn-b42849cb328383b2",
        "lrn-b4ad2c58bbfee975",
        "lrn-b4cd5b468eadb884",
        "lrn-c27205b641ae8ecf",
        "lrn-c87a2b40102c615c",
        "lrn-ca2c122985b53cbe",
        "lrn-d4c8de0a486a0658",
        "lrn-d55f5aa5acaf358e",
        "lrn-dbb0903d016b0fd2",
        "lrn-e0b4dff7e5164fed",
        "lrn-e6f01dfc34742102",
        "lrn-e7b3638c66416a3b",
        "lrn-eaf574a9914e6229",
        "lrn-ebe95e19a5a52ab1",
        "lrn-ebff1626a1e89a0a",
        "lrn-ef1b6215f75228f0",
        "lrn-f19f42c597a16824",
        "lrn-f1ac3e1ab969782e",
        "lrn-f5fb2273d6dde8ca",
        "lrn-f9de64deec05dafc",
        "lrn-faf5839d5bf36b12",
        "lrn-fba7ceebb6d0460c",
        "lrn-fea9e736d2e21f8d",
        "lrn-259ebf2b8ef50be9",
        "lrn-290ba31953fc95fe",
        "lrn-30a43e5473c971fa",
        "lrn-51d0a7a8ea56a393",
        "lrn-72ab394d5a1f0918",
        "lrn-79080742d6dce69f",
        "lrn-7dde6fde2466013e",
        "lrn-7e0a0277ef1a3330",
        "lrn-7f00bbbd63dced11",
        "lrn-880df29e7695055e",
        "lrn-9b3a3af35c17ed17",
        "lrn-a81b8c6c5ed15f0a",
        "lrn-ab5f4a34adece792",
        "lrn-af137a3e0b0582bf",
        "lrn-b3b5e4dde9fccbcd",
        "lrn-b85712947c2be35a",
        "lrn-c175272b91729c8d",
        "lrn-e906ba4d66bfcfee",
        "lrn-f7e3632ff0df7cad",
        "lrn-f8d3ded457c8a4f9"
      ]
    },
    "tailtrail_status": [
      {
        "control": "Planning Lock and approved anchor",
        "detail": "immutable approved requirement boundary",
        "status": "approved"
      },
      {
        "control": "Execution authority",
        "detail": "approved-plan-auto-grant; auto-granted: read_local, write_tailtrail_state, write_project, execute_project",
        "status": "safe-local-execution-authorized"
      },
      {
        "control": "Implementation delivery",
        "detail": "0 changed path(s); 0 saved blocker(s)",
        "status": "not-applicable"
      },
      {
        "control": "Official AI-DLC evidence checkpoint",
        "detail": "not triggered for this run",
        "status": "not-triggered"
      },
      {
        "control": "Canonical run state",
        "detail": "0 ownership or projection issue(s)",
        "status": "valid"
      },
      {
        "control": "Changed scope",
        "detail": "0 saved changed path(s)",
        "status": "approved"
      },
      {
        "control": "Requirement Completion Harness",
        "detail": "approved anchor + checkpoint + completion review + evidence gate",
        "status": "pass"
      },
      {
        "control": "Architecture Fitness Harness",
        "detail": "approved architecture contract or recorded architecture assessment",
        "status": "not-selected"
      },
      {
        "control": "Behaviour Harness",
        "detail": "recorded approved-scenario assessment",
        "status": "not-selected"
      },
      {
        "control": "Maintainability Harness",
        "detail": "recorded refactor/maintainability assessment",
        "status": "not-selected"
      },
      {
        "control": "Evidence-Aware Testing",
        "detail": "completion gate and validation receipts",
        "status": "pass"
      },
      {
        "control": "Drift control",
        "detail": "0 unresolved finding(s)",
        "status": "none-unresolved"
      },
      {
        "control": "Context Continuity Harness",
        "detail": "no unresolved drift required a correction-memory packet",
        "status": "not-triggered"
      },
      {
        "control": "Safe Git Recovery",
        "detail": "no recovery boundary was needed or recorded",
        "status": "not-needed"
      },
      {
        "control": "Execution failure handling",
        "detail": "0 saved failure record(s)",
        "status": "none-recorded"
      },
      {
        "control": "Debug Harness closure",
        "detail": "not a Debug Harness run",
        "status": "not-triggered"
      },
      {
        "control": "Gap learning",
        "detail": "No unresolved completion gap requires a learning candidate.",
        "status": "not-triggered"
      },
      {
        "control": "Guarded positive learning",
        "detail": "Use tailtrail closure learn with explicit user or trusted-CI acceptance; completion alone never creates a reusable learning rule.",
        "status": "eligible-awaiting-acceptance"
      },
      {
        "control": "Learning use attribution",
        "detail": "0 requirement-linked receipt(s); observed association only",
        "status": "no-receipts"
      },
      {
        "control": "Token estimate",
        "detail": "0 focused tokens",
        "status": "estimated"
      },
      {
        "control": "Actual model tokens",
        "detail": "host/provider telemetry was not linked to this run ID",
        "status": "unavailable"
      }
    ],
    "tests": {
      "failed_or_unavailable_receipts": [],
      "findings": [],
      "passed_tiers": [
        "contract",
        "unit"
      ],
      "receipt_refs": [
        ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-1.json",
        ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-2.json",
        ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-3.json",
        ".tailtrail/runs/start-20261027101501-5f1c2b/validation-receipts/closure-d708d8ef77e53a95-4.json"
      ],
      "receipts": [
        {
          "artifact_path": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.json",
          "asserted_behavior": "Trace current Start, AIDLC, scope, proof, receipt, audit, report, and Closure paths.",
          "closure_record_id": "closure-d708d8ef77e53a95",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
          "command_label": "phase0-trace",
          "duration_ms": 602,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-28T08:42:57.744952+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
          "requirement_uids": [
            "req-76fd0b4d5a49"
          ],
          "scenario_ids": [],
          "schema_version": "2",
          "started_at": "2026-10-28T08:42:57.141769+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.stderr.txt",
          "stderr_sha256": "sha256:15f013d9dad1430a1a1566d2414c357ec40d6ffe61ef4981433ea85ae064daa6",
          "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "unit",
          "tiers": [
            "unit"
          ],
          "type": "tailtrail-validation-evidence-receipt"
        },
        {
          "artifact_path": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.json",
          "asserted_behavior": "Map each requirement to its current schema, writer, reader, CLI route, tests, and identified gap.",
          "closure_record_id": "closure-d708d8ef77e53a95",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_host_question_flow_phase0_artifacts tests.test_host_input_contract_schema tests.test_host_question_flow_event_schema tests.test_public_route_gate tests.test_start_plan_presentation tests.test_completion_policy",
          "command_label": "phase0-mapping",
          "duration_ms": 3720,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-28T08:43:04.343341+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
          "requirement_uids": [
            "req-5ff71737d19c"
          ],
          "scenario_ids": [],
          "schema_version": "2",
          "started_at": "2026-10-28T08:43:00.622029+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.stderr.txt",
          "stderr_sha256": "sha256:88523b9cf24f5ac66b9b5686675064573fb420348a09c1414c469350281fb0d4",
          "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "contract",
          "tiers": [
            "contract"
          ],
          "type": "tailtrail-validation-evidence-receipt"
        },
        {
          "artifact_path": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.json",
          "asserted_behavior": "Deliver a hash-bound Phase 0 inventory/map artifact.",
          "closure_record_id": "closure-d708d8ef77e53a95",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_completion_policy",
          "command_label": "phase0-delivery-policy",
          "duration_ms": 177,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-28T08:43:07.456468+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
          "requirement_uids": [
            "req-fdd46f6d2653"
          ],
          "scenario_ids": [],
          "schema_version": "2",
          "started_at": "2026-10-28T08:43:07.278723+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.stderr.txt",
          "stderr_sha256": "sha256:172358797007957d0034e0c9b59820dbb3926be31f1162ce892415cc9026c089",
          "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "contract",
          "tiers": [
            "contract"
          ],
          "type": "tailtrail-validation-evidence-receipt"
        },
        {
          "artifact_path": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.json",
          "asserted_behavior": "Make no source, scope-authority, receipt, or Meta-Harness behavior changes.",
          "closure_record_id": "closure-d708d8ef77e53a95",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
          "command_label": "phase0-preservation",
          "duration_ms": 174,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-28T08:43:10.524739+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
          "requirement_uids": [
            "req-629704e7144f"
          ],
          "scenario_ids": [],
          "schema_version": "2",
          "started_at": "2026-10-28T08:43:10.350397+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.stderr.txt",
          "stderr_sha256": "sha256:2427194493c40676324fa088e241afe15eebacfcdea1e08205d1f1ecb245a1a9",
          "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "unit",
          "tiers": [
            "unit"
          ],
          "type": "tailtrail-validation-evidence-receipt"
        }
      ],
      "required_checks": [],
      "status": "pass",
      "tier_results": {
        "contract": "pass",
        "unit": "pass"
      },
      "unverified_receipts": []
    },
    "token_usage": {
      "actual_tailtrail_tokens": null,
      "boundary": "Exact usage comes only from host/provider metadata linked to this run ID. Exact savings additionally require a paired loose-prompt or AIDLC baseline for the same provider and model.",
      "comparisons": {
        "aidlc": {
          "reason": "TailTrail host/API usage is not linked to this run.",
          "status": "unavailable"
        },
        "loose-prompt": {
          "reason": "TailTrail host/API usage is not linked to this run.",
          "status": "unavailable"
        }
      },
      "context_estimate": {
        "boundary": "Relevant source, test, manifest, and configuration files; dependency, VCS, generated, build, coverage, TailTrail state, and known vendor directories are excluded.",
        "comparison_basis": "legacy-repository-ceiling",
        "estimated_reduction_percent": null,
        "estimated_saved_tokens": 0,
        "forecast_confidence": "low",
        "learning_evidence_references": [],
        "planned_working_set_tokens": null,
        "repository_ceiling_tokens": 2343238,
        "repository_file_count": 983,
        "saving_techniques": [
          "Focused validation selection"
        ],
        "scoped_file_ceiling_tokens": 0,
        "scoped_tokens": 0,
        "status": "estimated"
      },
      "planning_estimate_tokens": 0,
      "status": "unavailable",
      "telemetry_records": 0
    },
    "type": "tailtrail-completion-report"
  },
  "context_continuity": {
    "artifact": null,
    "boundary": "No unresolved drift was recorded.",
    "status": "none"
  },
  "correction": null,
  "debug_section": null,
  "delivery_record": ".tailtrail/runs/start-20261027101501-5f1c2b/delivery-record.md",
  "execution_events": [
    {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.json",
      "asserted_behavior": "Trace current Start, AIDLC, scope, proof, receipt, audit, report, and Closure paths.",
      "changed_paths": [],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
      "command_label": "phase0-trace",
      "duration_ms": 602,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "8a08730fea065a15",
      "finished_at": "2026-10-28T08:42:57.744952+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
      "requirement_uids": [
        "req-76fd0b4d5a49"
      ],
      "run_id": "start-20261027101501-5f1c2b",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 1,
      "started_at": "2026-10-28T08:42:57.141769+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.stderr.txt",
      "stderr_sha256": "sha256:15f013d9dad1430a1a1566d2414c357ec40d6ffe61ef4981433ea85ae064daa6",
      "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-d1175c9c99dfe56f.stdout.txt",
      "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "tier": "unit",
      "tiers": [
        "unit"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.json",
      "asserted_behavior": "Map each requirement to its current schema, writer, reader, CLI route, tests, and identified gap.",
      "changed_paths": [],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_host_question_flow_phase0_artifacts tests.test_host_input_contract_schema tests.test_host_question_flow_event_schema tests.test_public_route_gate tests.test_start_plan_presentation tests.test_completion_policy",
      "command_label": "phase0-mapping",
      "duration_ms": 3720,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "06a641a01c76808d",
      "finished_at": "2026-10-28T08:43:04.343341+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
      "requirement_uids": [
        "req-5ff71737d19c"
      ],
      "run_id": "start-20261027101501-5f1c2b",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 2,
      "started_at": "2026-10-28T08:43:00.622029+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.stderr.txt",
      "stderr_sha256": "sha256:88523b9cf24f5ac66b9b5686675064573fb420348a09c1414c469350281fb0d4",
      "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-b63866fa346ae376.stdout.txt",
      "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "tier": "contract",
      "tiers": [
        "contract"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.json",
      "asserted_behavior": "Deliver a hash-bound Phase 0 inventory/map artifact.",
      "changed_paths": [],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_completion_policy",
      "command_label": "phase0-delivery-policy",
      "duration_ms": 177,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "d83cadf085490f45",
      "finished_at": "2026-10-28T08:43:07.456468+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
      "requirement_uids": [
        "req-fdd46f6d2653"
      ],
      "run_id": "start-20261027101501-5f1c2b",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 3,
      "started_at": "2026-10-28T08:43:07.278723+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.stderr.txt",
      "stderr_sha256": "sha256:172358797007957d0034e0c9b59820dbb3926be31f1162ce892415cc9026c089",
      "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-6ccaec3afbf0e8ad.stdout.txt",
      "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "tier": "contract",
      "tiers": [
        "contract"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.json",
      "asserted_behavior": "Make no source, scope-authority, receipt, or Meta-Harness behavior changes.",
      "changed_paths": [],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v",
      "command_label": "phase0-preservation",
      "duration_ms": 174,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "3a730c05fdd0462f",
      "finished_at": "2026-10-28T08:43:10.524739+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:3517d8085db6b6a148b28ff0990988c28bea2d34e2a3f45e80476ddfde4247a3",
      "requirement_uids": [
        "req-629704e7144f"
      ],
      "run_id": "start-20261027101501-5f1c2b",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 4,
      "started_at": "2026-10-28T08:43:10.350397+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.stderr.txt",
      "stderr_sha256": "sha256:2427194493c40676324fa088e241afe15eebacfcdea1e08205d1f1ecb245a1a9",
      "stdout_artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/command-artifacts/command-a1fdde6301efade2.stdout.txt",
      "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "tier": "unit",
      "tiers": [
        "unit"
      ],
      "type": "tailtrail-execution-evidence"
    }
  ],
  "finalizer_id": "finalizer-37621ca5ffd45b0d",
  "graph_lifecycle": {
    "action": "defer",
    "after_status": {
      "reasons": [
        "Relevant repository file inventory changed after the graph was created."
      ],
      "scope": [
        "scripts/planning-revision.py",
        "tests/test_host_question_flow_event_schema.py",
        "tests/test_navigator_installed_release.py",
        "schemas/host-question-flow-event.schema.json",
        "scripts/completion-review.py",
        "scripts/tailtrail.py",
        "scripts/host-decision.py",
        "scripts/planning_lock.py",
        "scripts/code_graph_cache.py",
        "tests/test_question_orchestrator.py",
        "scripts/requirement_discovery.py",
        "scripts/ast-map.py",
        "tests/test_review_scope.py",
        "scripts/planning-discussion.py",
        "scripts/install-local.py",
        "tests/test_host_question_flow_phase0_artifacts.py",
        "scripts/workflow-dashboard.py",
        "tests/test_review_graph.py",
        "tests/test_execution_evidence.py",
        "tests/test_workflow_start_integration.py",
        "scripts/workflow_runtime/enterprise_transport.py",
        "scripts/greenfield_e2e_fixture.py",
        "tests/test_tailtrail_registry.py",
        "tests/test_code_graph_cache.py",
        "scripts/review-graph.py",
        "scripts/harness-checkpoint.py",
        "scripts/architecture_planning.py",
        "scripts/debug-preflight.py",
        "tests/test_workflow_documentation.py",
        "tests/test_workflow_privacy.py",
        "scripts/pipeline_orchestrator.py",
        "tests/test_host_contract.py",
        "scripts/official-aidlc-state.py",
        "tests/test_visual_requirement.py",
        "tests/test_closure_recorder.py",
        "scripts/closure-evaluation.py",
        "scripts/meta-harness-analyze.py",
        "tests/test_greenfield_e2e.py",
        "scripts/aidlc-official-detect.py",
        "scripts/adoption-validation.py",
        "scripts/task-start.py",
        "demo-project-layout/tailtrail-demo-workspace/services/claims-api/tests/test_validation.py",
        "scripts/official-aidlc-checkpoint.py",
        "tests/test_revision_proof_overlay.py",
        "scripts/closure-correction.py",
        "scripts/aidlc-init.py",
        "tests/test_code_graph_inventory.py",
        "scripts/aidlc-official-host.py",
        "tests/test_target_workspace.py",
        "scripts/question-orchestrator.py",
        "tests/test_requirement_routing_phase0.py",
        "scripts/closure-recorder.py",
        "scripts/aidlc-official-install.py",
        "scripts/learning-use-receipt.py",
        "tests/test_install_profiles.py",
        "hooks/hooks.json",
        "scripts/completion-report.py",
        "scripts/closure-finalizer.py",
        "tests/test_debug_start_planning.py",
        "tests/test_workflow_dashboard.py",
        "scripts/navigator_discovery.py",
        "tests/test_workflow_template_execution.py",
        "scripts/architecture-fitness.py",
        "tests/test_planning_audit.py",
        "tests/test_sequential_pipeline.py",
        "scripts/host_contract.py",
        "tests/test_navigator_graph_lifecycle.py",
        "tests/test_new_file_due_diligence.py",
        "scripts/run-ledger.py",
        "tests/test_architecture_fitness.py",
        "tests/test_aidlc_official_bridge.py",
        "scripts/execution-evidence.py",
        "scripts/debug-completion.py",
        "tests/test_task_recovery.py",
        "tests/test_delivery_record.py",
        "tests/test_navigator_core.py",
        "tests/test_host_adapter_conformance.py",
        "tests/test_task_type_gate.py",
        "tests/test_repository_path_policy.py",
        "scripts/official-aidlc-requirements.py",
        "scripts/closure-close.py",
        "tests/test_write_guardian.py",
        "tests/test_planning_lock.py",
        "tests/test_workflow_contracts.py",
        "scripts/workflow_runtime/start_integration.py",
        "tests/test_aidlc_official_host.py",
        "scripts/aidlc-requirements.py",
        "buildweek-demo-project/src/claims_api/validation.py",
        "scripts/closure-contract.py",
        "scripts/host-reply-validate.py",
        "schemas/host-input-contract.schema.json",
        "scripts/navigator-scope-release.py",
        "tests/test_full_pipeline.py",
        "tests/test_workflow_ci_continuation.py",
        "scripts/change-intent-anchor.py",
        "scripts/debug-host-diagnosis.py",
        "scripts/requirement_intake.py",
        "tests/test_start_entrypoints.py",
        "scripts/aidlc-official-bridge.py",
        "scripts/behaviour_planning.py",
        "scripts/navigator.py",
        "scripts/planning-audit.py",
        "scripts/update-copilot.py",
        "scripts/write_guardian.py",
        "tests/test_demo_prompt_book.py",
        "scripts/benchmark-tailtrail.py",
        "tests/test_requirement_discovery.py",
        "scripts/workflow_runtime/storage.py",
        "scripts/closure-learning.py",
        "scripts/verbose-reporting.py",
        "tests/test_workflow_approvals.py",
        "tests/test_intake_pipeline.py",
        "tests/test_workflow_adapters.py",
        "tests/test_workflow_ownership.py",
        "tests/test_planning_revision.py",
        "tests/test_completion_report.py",
        "scripts/host-adapter-conformance.py",
        "pyproject.toml",
        "scripts/learning-agent.py",
        "tests/test_closure_finalizer.py",
        "scripts/check-tailtrail.py",
        "scripts/docs-only.py",
        "tests/test_debug_host_integration.py",
        "scripts/requirement-completion.py",
        "scripts/navigator_scope.py",
        "scripts/mcp-server.py",
        "scripts/planning-aidlc-question.py",
        "tests/test_task_type_contract.py",
        "tests/test_enterprise_host_adapters.py",
        "tests/test_start_plan_presentation.py",
        "tests/test_completion_review.py",
        "scripts/new_file_due_diligence.py",
        "tests/test_host_packet_tickets.py",
        "tests/test_public_route_gate.py",
        "tests/test_workflow_phase7.py",
        "tests/test_canonical_statement_contract.py",
        "tests/test_host_input_contract_schema.py",
        "scripts/code-graph-mapper.py",
        "scripts/evidence-tiers.py",
        "scripts/install-copilot.py",
        "tests/test_evaluation_audit.py",
        "scripts/advanced-runtime.py",
        "scripts/delivery-record.py",
        "scripts/aidlc-check.py",
        "tests/test_debug_harness.py",
        "tests/test_navigator_scope.py",
        "scripts/debug-harness-convergence.py",
        "scripts/repository_path_policy.py",
        "scripts/debug-correction.py",
        "tests/test_mcp_server.py",
        "release-manifest.json",
        "scripts/intake_pipeline.py",
        "scripts/learning-refresh.py",
        "scripts/navigator-scope.py"
      ],
      "status": "stale"
    },
    "attempt_id": "start-20261027101501-5f1c2b",
    "before_status": {
      "reasons": [
        "Relevant repository file inventory changed after the graph was created."
      ],
      "scope": [
        "scripts/planning-revision.py",
        "tests/test_host_question_flow_event_schema.py",
        "tests/test_navigator_installed_release.py",
        "schemas/host-question-flow-event.schema.json",
        "scripts/completion-review.py",
        "scripts/tailtrail.py",
        "scripts/host-decision.py",
        "scripts/planning_lock.py",
        "scripts/code_graph_cache.py",
        "tests/test_question_orchestrator.py",
        "scripts/requirement_discovery.py",
        "scripts/ast-map.py",
        "tests/test_review_scope.py",
        "scripts/planning-discussion.py",
        "scripts/install-local.py",
        "tests/test_host_question_flow_phase0_artifacts.py",
        "scripts/workflow-dashboard.py",
        "tests/test_review_graph.py",
        "tests/test_execution_evidence.py",
        "tests/test_workflow_start_integration.py",
        "scripts/workflow_runtime/enterprise_transport.py",
        "scripts/greenfield_e2e_fixture.py",
        "tests/test_tailtrail_registry.py",
        "tests/test_code_graph_cache.py",
        "scripts/review-graph.py",
        "scripts/harness-checkpoint.py",
        "scripts/architecture_planning.py",
        "scripts/debug-preflight.py",
        "tests/test_workflow_documentation.py",
        "tests/test_workflow_privacy.py",
        "scripts/pipeline_orchestrator.py",
        "tests/test_host_contract.py",
        "scripts/official-aidlc-state.py",
        "tests/test_visual_requirement.py",
        "tests/test_closure_recorder.py",
        "scripts/closure-evaluation.py",
        "scripts/meta-harness-analyze.py",
        "tests/test_greenfield_e2e.py",
        "scripts/aidlc-official-detect.py",
        "scripts/adoption-validation.py",
        "scripts/task-start.py",
        "demo-project-layout/tailtrail-demo-workspace/services/claims-api/tests/test_validation.py",
        "scripts/official-aidlc-checkpoint.py",
        "tests/test_revision_proof_overlay.py",
        "scripts/closure-correction.py",
        "scripts/aidlc-init.py",
        "tests/test_code_graph_inventory.py",
        "scripts/aidlc-official-host.py",
        "tests/test_target_workspace.py",
        "scripts/question-orchestrator.py",
        "tests/test_requirement_routing_phase0.py",
        "scripts/closure-recorder.py",
        "scripts/aidlc-official-install.py",
        "scripts/learning-use-receipt.py",
        "tests/test_install_profiles.py",
        "hooks/hooks.json",
        "scripts/completion-report.py",
        "scripts/closure-finalizer.py",
        "tests/test_debug_start_planning.py",
        "tests/test_workflow_dashboard.py",
        "scripts/navigator_discovery.py",
        "tests/test_workflow_template_execution.py",
        "scripts/architecture-fitness.py",
        "tests/test_planning_audit.py",
        "tests/test_sequential_pipeline.py",
        "scripts/host_contract.py",
        "tests/test_navigator_graph_lifecycle.py",
        "tests/test_new_file_due_diligence.py",
        "scripts/run-ledger.py",
        "tests/test_architecture_fitness.py",
        "tests/test_aidlc_official_bridge.py",
        "scripts/execution-evidence.py",
        "scripts/debug-completion.py",
        "tests/test_task_recovery.py",
        "tests/test_delivery_record.py",
        "tests/test_navigator_core.py",
        "tests/test_host_adapter_conformance.py",
        "tests/test_task_type_gate.py",
        "tests/test_repository_path_policy.py",
        "scripts/official-aidlc-requirements.py",
        "scripts/closure-close.py",
        "tests/test_write_guardian.py",
        "tests/test_planning_lock.py",
        "tests/test_workflow_contracts.py",
        "scripts/workflow_runtime/start_integration.py",
        "tests/test_aidlc_official_host.py",
        "scripts/aidlc-requirements.py",
        "buildweek-demo-project/src/claims_api/validation.py",
        "scripts/closure-contract.py",
        "scripts/host-reply-validate.py",
        "schemas/host-input-contract.schema.json",
        "scripts/navigator-scope-release.py",
        "tests/test_full_pipeline.py",
        "tests/test_workflow_ci_continuation.py",
        "scripts/change-intent-anchor.py",
        "scripts/debug-host-diagnosis.py",
        "scripts/requirement_intake.py",
        "tests/test_start_entrypoints.py",
        "scripts/aidlc-official-bridge.py",
        "scripts/behaviour_planning.py",
        "scripts/navigator.py",
        "scripts/planning-audit.py",
        "scripts/update-copilot.py",
        "scripts/write_guardian.py",
        "tests/test_demo_prompt_book.py",
        "scripts/benchmark-tailtrail.py",
        "tests/test_requirement_discovery.py",
        "scripts/workflow_runtime/storage.py",
        "scripts/closure-learning.py",
        "scripts/verbose-reporting.py",
        "tests/test_workflow_approvals.py",
        "tests/test_intake_pipeline.py",
        "tests/test_workflow_adapters.py",
        "tests/test_workflow_ownership.py",
        "tests/test_planning_revision.py",
        "tests/test_completion_report.py",
        "scripts/host-adapter-conformance.py",
        "pyproject.toml",
        "scripts/learning-agent.py",
        "tests/test_closure_finalizer.py",
        "scripts/check-tailtrail.py",
        "scripts/docs-only.py",
        "tests/test_debug_host_integration.py",
        "scripts/requirement-completion.py",
        "scripts/navigator_scope.py",
        "scripts/mcp-server.py",
        "scripts/planning-aidlc-question.py",
        "tests/test_task_type_contract.py",
        "tests/test_enterprise_host_adapters.py",
        "tests/test_start_plan_presentation.py",
        "tests/test_completion_review.py",
        "scripts/new_file_due_diligence.py",
        "tests/test_host_packet_tickets.py",
        "tests/test_public_route_gate.py",
        "tests/test_workflow_phase7.py",
        "tests/test_canonical_statement_contract.py",
        "tests/test_host_input_contract_schema.py",
        "scripts/code-graph-mapper.py",
        "scripts/evidence-tiers.py",
        "scripts/install-copilot.py",
        "tests/test_evaluation_audit.py",
        "scripts/advanced-runtime.py",
        "scripts/delivery-record.py",
        "scripts/aidlc-check.py",
        "tests/test_debug_harness.py",
        "tests/test_navigator_scope.py",
        "scripts/debug-harness-convergence.py",
        "scripts/repository_path_policy.py",
        "scripts/debug-correction.py",
        "tests/test_mcp_server.py",
        "release-manifest.json",
        "scripts/intake_pipeline.py",
        "scripts/learning-refresh.py",
        "scripts/navigator-scope.py"
      ],
      "status": "stale"
    },
    "boundary": "Navigator may create or refresh TailTrail graph metadata; current-source scope evidence and Planning Lock approval remain mandatory.",
    "cache_fingerprint": "sha256:a2c9823b6760f6ffedeef00414f5821304829f67763981db8b2e36943624db80",
    "cache_path": "tailtrail-meta/code-graph-cache.json",
    "cache_reuse_state": null,
    "cache_shape": "mapper",
    "cache_warnings": [
      "legacy v1 mapper shape; migrates to a v2 container on next Phase-1 write"
    ],
    "fingerprint": "sha256:1568496d06ac55883254c71f5b08f0134c2a5bd4e7d47ea0a102d72827e20b49",
    "freshness": "stale",
    "implementation_authority": false,
    "metadata_only": true,
    "outside_slice_nominations": [],
    "phase": "closure",
    "reason_codes": [
      "bounded-goal-discovery",
      "fresh-prior-run-mapping",
      "requested-reuse-not-fresh"
    ],
    "relevance": "not-evaluated",
    "requested_mode": "reuse",
    "schema_version": "1",
    "target_paths": [
      "scripts/aidlc-requirements.py",
      "scripts/closure-evaluation.py",
      "scripts/closure-learning.py",
      "scripts/greenfield_e2e_fixture.py",
      "scripts/workflow-dashboard.py",
      "tests/test_completion_report.py",
      "tests/test_debug_start_planning.py",
      "tests/test_greenfield_e2e.py",
      "tests/test_host_adapter_conformance.py",
      "tests/test_navigator_core.py",
      "tests/test_navigator_scope.py",
      "tests/test_new_file_due_diligence.py",
      "tests/test_planning_lock.py",
      "tests/test_requirement_discovery.py",
      "tests/test_workflow_dashboard.py",
      "tests/test_workflow_phase7.py"
    ],
    "type": "tailtrail-navigator-graph-lifecycle",
    "written": false
  },
  "harness_review": {
    "recorded": true
  },
  "higher_tier_evidence": {
    "boundary": "The finalizer reads the current closure snapshot and accepts only trusted managed-command or attested artifact-backed higher-tier receipts.",
    "missing": [],
    "required": [
      {
        "requirement_uid": "req-5ff71737d19c",
        "tier": "contract"
      },
      {
        "requirement_uid": "req-fdd46f6d2653",
        "tier": "contract"
      }
    ],
    "status": "pass"
  },
  "ledger_events": [
    {
      "created_at": "2026-10-27T10:15:13+00:00",
      "event_id": "evt-0001-7eec182eb8340c99",
      "event_type": "run_created",
      "payload": {
        "goal": "Complete Phase 0 \u2014 Inventory and Ownership for the Host\u2013TailTrail Evidence Validation Contract: trace the current Start, AIDLC, scope, proof, receipt, audit, report, Closure, and Meta-Harness paths; map every design requirement to its current schema, writer, reader, CLI route, focused test, and explicit reuse-or-gap decision; deliver a hash-bound Phase 0 inventory/map artifact; make no source, scope-authority, receipt, or Meta-Harness behavior changes."
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 1,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T10:15:13+00:00",
      "event_id": "evt-0002-031f3d89072faa28",
      "event_type": "planning_lock_created",
      "payload": {
        "artifact": "planning/lock-v1.json",
        "input_roles": {
          "read_only_inputs": 1
        },
        "reference_roots": [],
        "target_fingerprint": "sha256:791d2db9cecbfe080226bed62d29199fe85f5c3373391f50ee1ff9cbb63eda48",
        "writes_allowed": false
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 2,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T10:15:13+00:00",
      "event_id": "evt-0003-a933d5eeb1655a43",
      "event_type": "target_resolution_recorded",
      "payload": {
        "policy_status": "not-configured",
        "target_resolution_receipt": ".tailtrail/runs/start-20261027101501-5f1c2b/planning/target-resolution-receipt-v1.json"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 3,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T10:15:13+00:00",
      "event_id": "evt-0004-57edc3777ae33a76",
      "event_type": "start_report_saved",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/planning/start-report-v1.json"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 4,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T10:15:13+00:00",
      "event_id": "evt-0005-8b683b0e4811c346",
      "event_type": "start_plan_verbose_generated",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/verbose-reports/start-plan-verbose-v1.md",
        "mandatory": true,
        "markdown_size": 11609,
        "status": "verified",
        "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027101501-5f1c2b/start-plan.md",
        "visible_artifact": "session-reports/start-20261027101501-5f1c2b/start-plan.md"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 5,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T10:15:13+00:00",
      "event_id": "evt-0006-ff1ce897e3352213",
      "event_type": "tailtrail_session_attached",
      "payload": {
        "context_key_hash": "sha256:8f7ea5b4e0bf204739b270db4b34f3ff3560126663ca15a47c97490c5a4c8b70",
        "fingerprint": "sha256:2bedc30e20b1f08b8170f6c57a393ef69cb1468dbb97475cdece1cb2c6ee967d",
        "generation": 286,
        "reason_code": "tailtrail-start"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 6,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T10:15:23+00:00",
      "event_id": "evt-0007-25e0f147a6e6bd3b",
      "event_type": "planning_audit_completed",
      "payload": {
        "finding_count": 3,
        "revision_cycles": 0,
        "status": "gaps-found",
        "total_review_cycles": 1
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 7,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T10:16:45+00:00",
      "event_id": "evt-0008-72d8163be341b541",
      "event_type": "planning_revision_proposed",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/planning/revisions/revision-v2.json",
        "base_revision": 1,
        "requirement_uids": [
          "req-5ff71737d19c",
          "req-fdd46f6d2653"
        ],
        "revision": 2
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 8,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T10:16:50+00:00",
      "event_id": "evt-0009-529afc8527c405d6",
      "event_type": "planning_audit_completed",
      "payload": {
        "finding_count": 0,
        "revision_cycles": 1,
        "status": "clean",
        "total_review_cycles": 2
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 9,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:27+00:00",
      "event_id": "evt-0010-19a75277a03808b2",
      "event_type": "anchor_drafted",
      "payload": {
        "fingerprint": "sha256:c0daeb8feb97d70f942180344f79d8d45e848f3246dabf7517cda870fa1d9c89",
        "proposal_version": 1,
        "requirements": [
          "req-76fd0b4d5a49",
          "req-5ff71737d19c",
          "req-fdd46f6d2653",
          "req-629704e7144f"
        ]
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 10,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:27+00:00",
      "event_id": "evt-0011-2a794a7abe2917fb",
      "event_type": "anchor_approved",
      "payload": {
        "fingerprint": "sha256:95d776c1515b9cf4b6d717a8a07d76a404a2850fbb1c3d6d56e67e6dc2c4cd4a",
        "path": ".tailtrail/runs/start-20261027101501-5f1c2b/anchors/approved-v1.json",
        "requirements": [
          "req-76fd0b4d5a49",
          "req-5ff71737d19c",
          "req-fdd46f6d2653",
          "req-629704e7144f"
        ]
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 11,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:27+00:00",
      "event_id": "evt-0012-538d002355d0d167",
      "event_type": "planning_lock_approved",
      "payload": {
        "artifact": "planning/lock-v1.json",
        "audit": {
          "report_fingerprint": "sha256:987ba11e23c5cf307f2a3db111f44cabc571f4d9ed5f1fbf8f3e3799444efbf2",
          "run_id": "start-20261027101501-5f1c2b",
          "source": "active-start-report",
          "status": "clean"
        },
        "writes_allowed": true
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 12,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:28+00:00",
      "event_id": "evt-0013-593260d35c615133",
      "event_type": "workflow_ownership_bound",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-7c025caa2418/ownership-v1.json",
        "requirement_uids": [
          "req-76fd0b4d5a49",
          "req-5ff71737d19c",
          "req-fdd46f6d2653",
          "req-629704e7144f"
        ],
        "workflow_id": "ttw-7c025caa2418"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 13,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:30+00:00",
      "event_id": "evt-0014-faf75a92ccc4da5e",
      "event_type": "workflow_capability_plan_declared",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-7c025caa2418/capability-plan-v1.json",
        "capability_ids": [
          "code-graph-mapper",
          "guardrails",
          "navigator",
          "review",
          "testing"
        ],
        "plan_fingerprint": "sha256:44e439acdcfae5978360344bbe7a36739c5155d65cbb67fb15c8331570d63585",
        "workflow_id": "ttw-7c025caa2418"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 14,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:31+00:00",
      "event_id": "evt-0015-60f6fab8d41535a0",
      "event_type": "workflow_storage_initialized",
      "payload": {
        "journal": ".tailtrail/workflows/ttw-7c025caa2418/journal-v1.jsonl",
        "projection": ".tailtrail/workflows/ttw-7c025caa2418/projection-v1.json",
        "workflow_id": "ttw-7c025caa2418"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 15,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:31+00:00",
      "event_id": "evt-0016-39a5cb41882b6870",
      "event_type": "workflow_state_created",
      "payload": {
        "journal": ".tailtrail/workflows/ttw-7c025caa2418/journal-v1.jsonl",
        "sequence": 2,
        "workflow_id": "ttw-7c025caa2418"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 16,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:40+00:00",
      "event_id": "evt-0017-1c3c919edb03f41a",
      "event_type": "workflow_compiler_plan_created",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-7c025caa2418/compiler-plan-v1.json",
        "plan_fingerprint": "sha256:6e020f5ecf1c46c78340de10b609cad900e3ae2424d3a6a43a51e52df2e9890a",
        "revision": 1,
        "template_id": "small-change",
        "workflow_id": "ttw-7c025caa2418"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 17,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:40+00:00",
      "event_id": "evt-0018-9c4fc772b7a75eb2",
      "event_type": "workflow_stage_approval_recorded",
      "payload": {
        "action_classes": [
          "write_tailtrail_state"
        ],
        "approval_id": "wfauth-48e60b5e6835db5fe70d9ab3",
        "decision": "approved",
        "operation_kind": "initial-plan",
        "source": "interactive",
        "stage_ids": [
          "bootstrap",
          "discover",
          "focused-test",
          "fulfilment",
          "implement",
          "review"
        ],
        "workflow_id": "ttw-7c025caa2418"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 18,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:40+00:00",
      "event_id": "evt-0019-d5fbf65d66cac75c",
      "event_type": "workflow_stage_approval_recorded",
      "payload": {
        "action_classes": [
          "execute_project",
          "read_local",
          "write_project",
          "write_tailtrail_state"
        ],
        "approval_id": "wfauth-2157a88d84ccb1aa075db786",
        "decision": "approved",
        "operation_kind": "other-guarded",
        "source": "plan-derived",
        "stage_ids": [
          "bootstrap",
          "discover",
          "focused-test",
          "fulfilment",
          "implement",
          "review"
        ],
        "workflow_id": "ttw-7c025caa2418"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 19,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:40+00:00",
      "event_id": "evt-0020-fc0a9ffe2a1abca9",
      "event_type": "workflow_runtime_activated",
      "payload": {
        "binding": ".tailtrail/workflows/ttw-7c025caa2418/ownership-v1.json",
        "capability_plan": ".tailtrail/workflows/ttw-7c025caa2418/capability-plan-v1.json",
        "compiler_plan": ".tailtrail/workflows/ttw-7c025caa2418/compiler-plan-v1.json",
        "compiler_plan_fingerprint": "sha256:6e020f5ecf1c46c78340de10b609cad900e3ae2424d3a6a43a51e52df2e9890a",
        "workflow_id": "ttw-7c025caa2418"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 20,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:40+00:00",
      "event_id": "evt-0021-f597264eda7a6c23",
      "event_type": "planning_activated",
      "payload": {
        "activation_audit": {
          "report_fingerprint": "sha256:987ba11e23c5cf307f2a3db111f44cabc571f4d9ed5f1fbf8f3e3799444efbf2",
          "run_id": "start-20261027101501-5f1c2b",
          "source": "active-start-report",
          "status": "clean"
        },
        "anchor": {
          "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/anchors/approved-v1.json",
          "requirements": [
            "req-76fd0b4d5a49",
            "req-5ff71737d19c",
            "req-fdd46f6d2653",
            "req-629704e7144f"
          ],
          "status": "created"
        },
        "enterprise_policy_status": "not-configured",
        "handoff": "planning/execution-handoff-v1.json",
        "input_role_status": "matched",
        "official_aidlc_bridge_activation": null,
        "scope_decision_status": "legacy",
        "target_identity_status": "matched",
        "workflow_runtime": "compiled"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 21,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:40+00:00",
      "event_id": "evt-0022-75454411c6d8f669",
      "event_type": "start_plan_verbose_generated",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/verbose-reports/start-plan-verbose-v1.md",
        "mandatory": true,
        "markdown_size": 11972,
        "status": "verified",
        "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027101501-5f1c2b/start-plan.md",
        "visible_artifact": "session-reports/start-20261027101501-5f1c2b/start-plan.md"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 22,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:38:40+00:00",
      "event_id": "evt-0023-5de33274c72601ef",
      "event_type": "planning_revision_approved",
      "payload": {
        "active_report": ".tailtrail/runs/start-20261027101501-5f1c2b/planning/revisions/start-report-v2.json",
        "anchor": ".tailtrail/runs/start-20261027101501-5f1c2b/anchors/approved-v1.json",
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/planning/revisions/revision-v2.json",
        "audit": {
          "report_fingerprint": "sha256:987ba11e23c5cf307f2a3db111f44cabc571f4d9ed5f1fbf8f3e3799444efbf2",
          "run_id": "start-20261027101501-5f1c2b",
          "source": "active-start-report",
          "status": "clean"
        },
        "revision": 2
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 23,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:42:59+00:00",
      "event_id": "evt-0024-d7a53bc6f01803cb",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/evidence-stream.jsonl",
        "fingerprint": "8a08730fea065a15",
        "kind": "command-result",
        "sequence": 1
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 24,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:43:05+00:00",
      "event_id": "evt-0025-b7fd096ecee054df",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/evidence-stream.jsonl",
        "fingerprint": "06a641a01c76808d",
        "kind": "command-result",
        "sequence": 2
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 25,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:43:08+00:00",
      "event_id": "evt-0026-f0ad9ae0883d5b6a",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/evidence-stream.jsonl",
        "fingerprint": "d83cadf085490f45",
        "kind": "command-result",
        "sequence": 3
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 26,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:43:11+00:00",
      "event_id": "evt-0027-5cf9e8e2f66bd3cf",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/execution/evidence-stream.jsonl",
        "fingerprint": "3a730c05fdd0462f",
        "kind": "command-result",
        "sequence": 4
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 27,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:43:25+00:00",
      "event_id": "evt-0028-7f68394e2b39dfec",
      "event_type": "validation_delivery_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/validation-delivery/delivery-v1.json",
        "artifact_path": "TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-PHASE0-INVENTORY.md",
        "artifact_sha256": "237e1a32e97561f1cccba693874890348b5244b3e88612298d075d5b42d3faf5"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 28,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:43:40+00:00",
      "event_id": "evt-0029-b7665d73ab9629a5",
      "event_type": "harness_checkpoint",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/checkpoints/checkpoint-1.json",
        "checkpoint": 1,
        "drift": [
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-76fd0b4d5a49"
          },
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-5ff71737d19c"
          },
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-fdd46f6d2653"
          },
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-629704e7144f"
          }
        ],
        "requirement_states": {
          "req-5ff71737d19c": "validated",
          "req-629704e7144f": "validated",
          "req-76fd0b4d5a49": "validated",
          "req-fdd46f6d2653": "validated"
        }
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 29,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:43:40+00:00",
      "event_id": "evt-0030-0d587d0f80c98131",
      "event_type": "completion_review",
      "payload": {
        "artifact": "reviews/review-1.json",
        "checkpoint": 1,
        "complete": true,
        "findings": 0
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 30,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:43:40+00:00",
      "event_id": "evt-0031-a658c71ce22f5ca1",
      "event_type": "completion_gate",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/completion-gates/gate-1.json",
        "complete": true,
        "findings": []
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 31,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:43:40+00:00",
      "event_id": "evt-0032-8fe98892d8a0c75c",
      "event_type": "closure_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/closure-records/closure-d708d8ef77e53a95.json",
        "checkpoint": 1,
        "gate_complete": true,
        "receipt_count": 4,
        "record_id": "closure-d708d8ef77e53a95",
        "review_complete": true
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 32,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-28T08:43:59+00:00",
      "event_id": "evt-0033-ecc225b2789bdc47",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-1.json",
        "completion_learning": "not-triggered",
        "harnesses": [
          {
            "name": "Requirement Completion Harness",
            "status": "pass",
            "used": true
          },
          {
            "name": "Architecture Fitness Harness",
            "status": "not-selected",
            "used": false
          },
          {
            "name": "Behaviour Harness",
            "status": "not-selected",
            "used": false
          },
          {
            "name": "Maintainability Harness",
            "status": "not-selected",
            "used": false
          },
          {
            "name": "Evidence-Aware Testing",
            "status": "pass",
            "used": true
          }
        ],
        "learning_use": "no-receipts",
        "overall_status": "complete"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 33,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T11:33:22+00:00",
      "event_id": "evt-0034-b5bf3d3cc0288017",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-2.json",
        "completion_learning": "not-triggered",
        "harnesses": [
          {
            "name": "Requirement Completion Harness",
            "status": "pass",
            "used": true
          },
          {
            "name": "Architecture Fitness Harness",
            "status": "not-selected",
            "used": false
          },
          {
            "name": "Behaviour Harness",
            "status": "not-selected",
            "used": false
          },
          {
            "name": "Maintainability Harness",
            "status": "not-selected",
            "used": false
          },
          {
            "name": "Evidence-Aware Testing",
            "status": "pass",
            "used": true
          }
        ],
        "learning_use": "no-receipts",
        "overall_status": "complete"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 34,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T11:33:25+00:00",
      "event_id": "evt-0035-02fb47760f5c92b3",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-3.json",
        "completion_learning": "not-triggered",
        "harnesses": [
          {
            "name": "Requirement Completion Harness",
            "status": "pass",
            "used": true
          },
          {
            "name": "Architecture Fitness Harness",
            "status": "not-selected",
            "used": false
          },
          {
            "name": "Behaviour Harness",
            "status": "not-selected",
            "used": false
          },
          {
            "name": "Maintainability Harness",
            "status": "not-selected",
            "used": false
          },
          {
            "name": "Evidence-Aware Testing",
            "status": "pass",
            "used": true
          }
        ],
        "learning_use": "no-receipts",
        "overall_status": "complete"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 35,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T11:33:28+00:00",
      "event_id": "evt-0036-679a531ad05ef623",
      "event_type": "navigator_graph_lifecycle_recorded",
      "payload": {
        "action": "defer",
        "cache_fingerprint": "sha256:a2c9823b6760f6ffedeef00414f5821304829f67763981db8b2e36943624db80",
        "mapping_fingerprint": null,
        "phase": "closure"
      },
      "run_id": "start-20261027101501-5f1c2b",
      "schema_version": "1",
      "sequence": 36,
      "type": "tailtrail-run-event"
    }
  ],
  "overall_status": "complete",
  "pipeline": {
    "active_badge": "impl-badge",
    "active_stage": "IMPLEMENTATION",
    "completed_stages": [],
    "handoff_count": 0,
    "status": "badged",
    "unvisited_stages": [
      "TESTING",
      "INFRA"
    ]
  },
  "recovery": {
    "boundary": null,
    "status": "not-needed"
  },
  "run_id": "start-20261027101501-5f1c2b",
  "run_mapping": null,
  "schema_version": "1",
  "selected_harnesses": [
    "Canonical requirements",
    "Question Orchestrator",
    "Requirement Completion Harness",
    "Evidence-Aware Testing",
    "Test Precision Planner"
  ],
  "stale_learnings": {
    "needs_backfill": [],
    "triggered": [
      "lrn-04fa0ce192147e05",
      "lrn-2bfef89b80f2713c",
      "lrn-2d2f1a18826c5009",
      "lrn-2dd27396c9cd3022",
      "lrn-39d6406267ee8097",
      "lrn-3efb535bedfa119f",
      "lrn-531e637cdff54461",
      "lrn-53f801a3afb6d044",
      "lrn-54e4c595d2d1f36a",
      "lrn-5a42321335867d06",
      "lrn-681b007f0c1878b8",
      "lrn-6ae0ccfc7ac706af",
      "lrn-7074aa8f8b7b72f4",
      "lrn-72e352d6459d61a6",
      "lrn-75278005a7c7933f",
      "lrn-761dc46db33a36e2",
      "lrn-88bc7405c5c9861b",
      "lrn-999c71f0d0ea5d33",
      "lrn-9d789ac8c51e41fe",
      "lrn-a51b56445a4ed47e",
      "lrn-b42849cb328383b2",
      "lrn-b4ad2c58bbfee975",
      "lrn-b4cd5b468eadb884",
      "lrn-c27205b641ae8ecf",
      "lrn-c87a2b40102c615c",
      "lrn-ca2c122985b53cbe",
      "lrn-d4c8de0a486a0658",
      "lrn-d55f5aa5acaf358e",
      "lrn-dbb0903d016b0fd2",
      "lrn-e0b4dff7e5164fed",
      "lrn-e6f01dfc34742102",
      "lrn-e7b3638c66416a3b",
      "lrn-eaf574a9914e6229",
      "lrn-ebe95e19a5a52ab1",
      "lrn-ebff1626a1e89a0a",
      "lrn-ef1b6215f75228f0",
      "lrn-f19f42c597a16824",
      "lrn-f1ac3e1ab969782e",
      "lrn-f5fb2273d6dde8ca",
      "lrn-f9de64deec05dafc",
      "lrn-faf5839d5bf36b12",
      "lrn-fba7ceebb6d0460c",
      "lrn-fea9e736d2e21f8d",
      "lrn-259ebf2b8ef50be9",
      "lrn-290ba31953fc95fe",
      "lrn-30a43e5473c971fa",
      "lrn-51d0a7a8ea56a393",
      "lrn-72ab394d5a1f0918",
      "lrn-79080742d6dce69f",
      "lrn-7dde6fde2466013e",
      "lrn-7e0a0277ef1a3330",
      "lrn-7f00bbbd63dced11",
      "lrn-880df29e7695055e",
      "lrn-9b3a3af35c17ed17",
      "lrn-a81b8c6c5ed15f0a",
      "lrn-ab5f4a34adece792",
      "lrn-af137a3e0b0582bf",
      "lrn-b3b5e4dde9fccbcd",
      "lrn-b85712947c2be35a",
      "lrn-c175272b91729c8d",
      "lrn-e906ba4d66bfcfee",
      "lrn-f7e3632ff0df7cad",
      "lrn-f8d3ded457c8a4f9"
    ]
  },
  "type": "tailtrail-closure-finalizer",
  "verbose_report": {
    "artifact": ".tailtrail/runs/start-20261027101501-5f1c2b/verbose-reports/closure-verbose-v1.md",
    "mandatory": true,
    "markdown_size": 132013,
    "run_id": "start-20261027101501-5f1c2b",
    "status": "generated",
    "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027101501-5f1c2b/closure-report.md",
    "visible_artifact": "session-reports/start-20261027101501-5f1c2b/closure-report.md"
  },
  "workflow_closure": {
    "artifact": ".tailtrail/workflows/ttw-7c025caa2418/completion-receipt-v1.json",
    "boundary": "Completion follows the canonical TailTrail Completion Report. An evidence-incomplete receipt is not a successful workflow completion and does not authorize a retry or recovery.",
    "completion_report": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261027101501-5f1c2b/completion-reports/report-3.json",
    "completion_status": "complete",
    "evidence_fingerprint": "sha256:74162de16484ffc60ac076af913b1c63a7fc455e424c5f212ea91b3c62384e67",
    "receipt_fingerprint": "sha256:f3edc24cec7290f8c3d51e7593322f0d7fe46fe50e6a51f0138cc8954879c171",
    "schema_version": "1",
    "state": "completed",
    "tailtrail_run_id": "start-20261027101501-5f1c2b",
    "type": "tailtrail-workflow-completion-receipt",
    "workflow_id": "ttw-7c025caa2418"
  }
}
```

---

*End of full Closure execution record.*
