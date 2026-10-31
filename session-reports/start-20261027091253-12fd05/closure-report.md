# TailTrail Closure Report - Full Execution Record

| Field | Value |
|---|---|
| Run ID | `start-20261027091253-12fd05` |
| Generated after finalization | `2026-10-27T14:56:49.097709` |
| Overall status | `complete` |
| Closure record | `closure-8e81a801b7db9d26` |
| Finalizer | `finalizer-448906644f550704` |

## Changes And Locations

| Path / location | Recorded status |
|---|---|
| `scripts/task-start.py` | recorded changed path |
| `tests/test_start_plan_presentation.py` | recorded changed path |

## Requirement Verification

```json
{
  "complete": 2,
  "requirements": [
    {
      "display_id": "REQ-01",
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-51177d1dd2be"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.json",
          "asserted_behavior": "Implement generic Start Plan projection for validation-only host contracts",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
          "command_label": "validation-only host-contract projection regression",
          "duration_ms": 3248,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-27T09:25:39.415709+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-51177d1dd2be"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-27T09:25:36.167575+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.stderr.txt",
          "stderr_sha256": "sha256:e5766a12a9b9962bddebf6d7b305230a341d28ce3f29ab48fc37eb1c70626a99",
          "stdout_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "contract",
          "tiers": [
            "contract"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "implemented",
      "requirement_uid": "req-51177d1dd2be",
      "statement": "Implement generic Start Plan projection for validation-only host contracts",
      "status": "complete",
      "verification_status": "pass"
    },
    {
      "display_id": "REQ-02",
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-71470147cd10"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.json",
          "asserted_behavior": "do not grant implementation authority, auto-credit proof, or alter completion semantics.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
          "command_label": "validation-only host-contract projection safety regression",
          "duration_ms": 3439,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-27T09:25:54.067529+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-71470147cd10"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-27T09:25:50.628392+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.stderr.txt",
          "stderr_sha256": "sha256:031d9168b7a48fdf28914b24ad124a5b1a79d360abce562507590dece2cf9b70",
          "stdout_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "unit",
          "tiers": [
            "unit"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "implemented",
      "requirement_uid": "req-71470147cd10",
      "statement": "do not grant implementation authority, auto-credit proof, or alter completion semantics.",
      "status": "complete",
      "verification_status": "pass"
    }
  ],
  "total": 2
}
```

## Execution Timeline And Evidence

| Kind | Command / action | Outcome | Exit code | Duration ms | Requirements | Tiers |
|---|---|---|---|---|---|---|
| command-result | `python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate` | pass | 0 | 3248 | ["req-51177d1dd2be"] | ["contract"] |
| command-result | `python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate` | pass | 0 | 3439 | ["req-71470147cd10"] | ["unit"] |

## Tests, Harnesses, Health, Drift, And Failures

```json
{
  "architecture": {
    "findings": [],
    "required": true,
    "status": "pass"
  },
  "assessments": {
    "Architecture Fitness Harness": {
      "artifact": null,
      "complete": true
    }
  },
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
        "requirement_uid": "req-51177d1dd2be",
        "tier": "contract"
      }
    ],
    "status": "pass"
  },
  "maintainability": {},
  "pipeline": {
    "active_badge": "test-badge",
    "active_stage": "TESTING",
    "completed_stages": [
      "IMPLEMENTATION"
    ],
    "handoff_count": 1,
    "status": "badged",
    "unvisited_stages": [
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
      ".tailtrail/runs/start-20261027091253-12fd05/validation-receipts/closure-8e81a801b7db9d26-1.json",
      ".tailtrail/runs/start-20261027091253-12fd05/validation-receipts/closure-8e81a801b7db9d26-2.json"
    ],
    "receipts": [
      {
        "artifact_path": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.json",
        "asserted_behavior": "Implement generic Start Plan projection for validation-only host contracts",
        "closure_record_id": "closure-8e81a801b7db9d26",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
        "command_label": "validation-only host-contract projection regression",
        "duration_ms": 3248,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-27T09:25:39.415709+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:df50d833d177067f491988ce6fb6f0bb47b1906b7cafdc3a521b9cc3e257cedc",
        "requirement_uids": [
          "req-51177d1dd2be"
        ],
        "scenario_ids": [],
        "schema_version": "2",
        "started_at": "2026-10-27T09:25:36.167575+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.stderr.txt",
        "stderr_sha256": "sha256:e5766a12a9b9962bddebf6d7b305230a341d28ce3f29ab48fc37eb1c70626a99",
        "stdout_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.stdout.txt",
        "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "tier": "contract",
        "tiers": [
          "contract"
        ],
        "type": "tailtrail-validation-evidence-receipt"
      },
      {
        "artifact_path": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.json",
        "asserted_behavior": "do not grant implementation authority, auto-credit proof, or alter completion semantics.",
        "closure_record_id": "closure-8e81a801b7db9d26",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
        "command_label": "validation-only host-contract projection safety regression",
        "duration_ms": 3439,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-27T09:25:54.067529+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:df50d833d177067f491988ce6fb6f0bb47b1906b7cafdc3a521b9cc3e257cedc",
        "requirement_uids": [
          "req-71470147cd10"
        ],
        "scenario_ids": [],
        "schema_version": "2",
        "started_at": "2026-10-27T09:25:50.628392+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.stderr.txt",
        "stderr_sha256": "sha256:031d9168b7a48fdf28914b24ad124a5b1a79d360abce562507590dece2cf9b70",
        "stdout_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.stdout.txt",
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
    "comparison_basis": "scoped-files",
    "estimated_reduction_percent": 88.12,
    "estimated_saved_tokens": 94794,
    "forecast_confidence": "medium",
    "learning_evidence_references": [],
    "planned_working_set_tokens": 12774,
    "repository_ceiling_tokens": 2341252,
    "repository_file_count": 983,
    "saving_techniques": [
      "Navigator scope narrowing",
      "Focused validation selection"
    ],
    "scoped_file_ceiling_tokens": 107568,
    "scoped_tokens": 12774,
    "status": "estimated"
  },
  "planning_estimate_tokens": 12774,
  "status": "unavailable",
  "telemetry_records": 0
}
```
Measured values are shown only when linked host/provider telemetry exists. Estimates retain their saved provenance; missing measurements remain unavailable.

## Command Reference Registry

Single-source-of-truth reference for all proof commands.

| ID | Kind | Command |
|---|---|---|
| `cmd-62b3f5` | proof | `python3 -m unittest tests.test_start_plan_presentation tests.test_publ...` |
| `cmd-dcb44d` | proof | `python3 -m unittest discover -s tests -p test_start_plan_presentation....` |


## TailTrail Lifecycle And Audit Events

```json
[
  {
    "created_at": "2026-10-27T09:13:05+00:00",
    "event_id": "evt-0001-b01c4cf3d0b40530",
    "event_type": "run_created",
    "payload": {
      "goal": "Implement generic Start Plan projection for validation-only host contracts: preserve every accepted inspection-input and proof-only path; retain the global proof command as unbound context; require explicit requirement-level proof bindings before readiness; do not grant implementation authority, auto-credit proof, or alter completion semantics."
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 1,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:13:05+00:00",
    "event_id": "evt-0002-daa2da8a460e23bf",
    "event_type": "planning_lock_created",
    "payload": {
      "artifact": "planning/lock-v1.json",
      "input_roles": {
        "read_only_inputs": 0
      },
      "reference_roots": [],
      "target_fingerprint": "sha256:791d2db9cecbfe080226bed62d29199fe85f5c3373391f50ee1ff9cbb63eda48",
      "writes_allowed": false
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 2,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:13:05+00:00",
    "event_id": "evt-0003-a99641c2d9862bfc",
    "event_type": "target_resolution_recorded",
    "payload": {
      "policy_status": "not-configured",
      "target_resolution_receipt": ".tailtrail/runs/start-20261027091253-12fd05/planning/target-resolution-receipt-v1.json"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 3,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:13:05+00:00",
    "event_id": "evt-0004-1b860ffa22b908cf",
    "event_type": "start_report_saved",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/planning/start-report-v1.json"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 4,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:13:05+00:00",
    "event_id": "evt-0005-33077bac5ae00812",
    "event_type": "start_plan_verbose_generated",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/verbose-reports/start-plan-verbose-v1.md",
      "mandatory": true,
      "markdown_size": 7291,
      "status": "verified",
      "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027091253-12fd05/start-plan.md",
      "visible_artifact": "session-reports/start-20261027091253-12fd05/start-plan.md"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 5,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:13:05+00:00",
    "event_id": "evt-0006-7a3ad6218699f640",
    "event_type": "tailtrail_session_attached",
    "payload": {
      "context_key_hash": "sha256:8f7ea5b4e0bf204739b270db4b34f3ff3560126663ca15a47c97490c5a4c8b70",
      "fingerprint": "sha256:da89beeb88a56ac4797da92cf7d3c6f05faac33323722a8147df56ca58e4bb6a",
      "generation": 285,
      "reason_code": "tailtrail-start"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 6,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:13:15+00:00",
    "event_id": "evt-0007-e07c51d04831e3f7",
    "event_type": "planning_audit_completed",
    "payload": {
      "finding_count": 3,
      "revision_cycles": 0,
      "status": "gaps-found",
      "total_review_cycles": 1
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 7,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:14:05+00:00",
    "event_id": "evt-0008-d55ab234c2381078",
    "event_type": "planning_revision_proposed",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/planning/revisions/revision-v2.json",
      "base_revision": 1,
      "requirement_uids": [
        "req-51177d1dd2be",
        "req-71470147cd10"
      ],
      "revision": 2
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 8,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:14:05+00:00",
    "event_id": "evt-0009-99667dd1092320b2",
    "event_type": "planning_audit_completed",
    "payload": {
      "finding_count": 0,
      "revision_cycles": 1,
      "status": "clean",
      "total_review_cycles": 2
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 9,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:00+00:00",
    "event_id": "evt-0010-ba412520541252b2",
    "event_type": "anchor_drafted",
    "payload": {
      "fingerprint": "sha256:e4c328a36becdc05bba6dfa9a16e2eaba2886bc4e932e7b9df3ccad61895fb23",
      "proposal_version": 1,
      "requirements": [
        "req-51177d1dd2be",
        "req-71470147cd10"
      ]
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 10,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:00+00:00",
    "event_id": "evt-0011-00c4d075861f2093",
    "event_type": "anchor_approved",
    "payload": {
      "fingerprint": "sha256:caec26e264767d23acfea4e17410937b36544305853a31e4f73391121958b5c8",
      "path": ".tailtrail/runs/start-20261027091253-12fd05/anchors/approved-v1.json",
      "requirements": [
        "req-51177d1dd2be",
        "req-71470147cd10"
      ]
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 11,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:00+00:00",
    "event_id": "evt-0012-36e9073c953e6919",
    "event_type": "planning_lock_approved",
    "payload": {
      "artifact": "planning/lock-v1.json",
      "audit": {
        "report_fingerprint": "sha256:43ee792a8d5eb022de5fbc19bec674caece5337f6ac65a7ff805e9dfe544d338",
        "run_id": "start-20261027091253-12fd05",
        "source": "active-start-report",
        "status": "clean"
      },
      "writes_allowed": true
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 12,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:02+00:00",
    "event_id": "evt-0013-0e939678975f479e",
    "event_type": "workflow_ownership_bound",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-ce45b404e02d/ownership-v1.json",
      "requirement_uids": [
        "req-51177d1dd2be",
        "req-71470147cd10"
      ],
      "workflow_id": "ttw-ce45b404e02d"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 13,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:03+00:00",
    "event_id": "evt-0014-b762c9a13ec51b87",
    "event_type": "workflow_capability_plan_declared",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-ce45b404e02d/capability-plan-v1.json",
      "capability_ids": [
        "navigator",
        "quality-signals",
        "review",
        "testing"
      ],
      "plan_fingerprint": "sha256:ea7e054495586cb7574c93dd2a19edb5b8e9ab9248bb697041c12b5b46881d3b",
      "workflow_id": "ttw-ce45b404e02d"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 14,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:04+00:00",
    "event_id": "evt-0015-d4ffb516d0015759",
    "event_type": "workflow_storage_initialized",
    "payload": {
      "journal": ".tailtrail/workflows/ttw-ce45b404e02d/journal-v1.jsonl",
      "projection": ".tailtrail/workflows/ttw-ce45b404e02d/projection-v1.json",
      "workflow_id": "ttw-ce45b404e02d"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 15,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:04+00:00",
    "event_id": "evt-0016-7d7032c1e7da6ba9",
    "event_type": "workflow_state_created",
    "payload": {
      "journal": ".tailtrail/workflows/ttw-ce45b404e02d/journal-v1.jsonl",
      "sequence": 2,
      "workflow_id": "ttw-ce45b404e02d"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 16,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:14+00:00",
    "event_id": "evt-0017-546fe1fa6763113b",
    "event_type": "workflow_compiler_plan_created",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-ce45b404e02d/compiler-plan-v1.json",
      "plan_fingerprint": "sha256:f4fac53f44ab8fdbb6c663669d1d1dd4f58368e8b733b9771a2946b344db7726",
      "revision": 1,
      "template_id": "small-change",
      "workflow_id": "ttw-ce45b404e02d"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 17,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:14+00:00",
    "event_id": "evt-0018-d4fc7db8e6f4988c",
    "event_type": "workflow_stage_approval_recorded",
    "payload": {
      "action_classes": [
        "write_tailtrail_state"
      ],
      "approval_id": "wfauth-4aeeb4e953b6f150f7a78f8f",
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
      "workflow_id": "ttw-ce45b404e02d"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 18,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:14+00:00",
    "event_id": "evt-0019-c837756a626690da",
    "event_type": "workflow_stage_approval_recorded",
    "payload": {
      "action_classes": [
        "execute_project",
        "read_local",
        "write_project",
        "write_tailtrail_state"
      ],
      "approval_id": "wfauth-625dbbcb8d5c56bef5e78aad",
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
      "workflow_id": "ttw-ce45b404e02d"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 19,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:14+00:00",
    "event_id": "evt-0020-27a15b8fec1c537c",
    "event_type": "workflow_runtime_activated",
    "payload": {
      "binding": ".tailtrail/workflows/ttw-ce45b404e02d/ownership-v1.json",
      "capability_plan": ".tailtrail/workflows/ttw-ce45b404e02d/capability-plan-v1.json",
      "compiler_plan": ".tailtrail/workflows/ttw-ce45b404e02d/compiler-plan-v1.json",
      "compiler_plan_fingerprint": "sha256:f4fac53f44ab8fdbb6c663669d1d1dd4f58368e8b733b9771a2946b344db7726",
      "workflow_id": "ttw-ce45b404e02d"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 20,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:14+00:00",
    "event_id": "evt-0021-a1462d4035957316",
    "event_type": "planning_activated",
    "payload": {
      "activation_audit": {
        "report_fingerprint": "sha256:43ee792a8d5eb022de5fbc19bec674caece5337f6ac65a7ff805e9dfe544d338",
        "run_id": "start-20261027091253-12fd05",
        "source": "active-start-report",
        "status": "clean"
      },
      "anchor": {
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/anchors/approved-v1.json",
        "requirements": [
          "req-51177d1dd2be",
          "req-71470147cd10"
        ],
        "status": "created"
      },
      "enterprise_policy_status": "not-configured",
      "handoff": "planning/execution-handoff-v1.json",
      "input_role_status": "matched",
      "official_aidlc_bridge_activation": null,
      "scope_decision_status": "matched-revision",
      "target_identity_status": "matched",
      "workflow_runtime": "compiled"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 21,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:14+00:00",
    "event_id": "evt-0022-1524d7cd8dd77aaf",
    "event_type": "start_plan_verbose_generated",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/verbose-reports/start-plan-verbose-v1.md",
      "mandatory": true,
      "markdown_size": 7351,
      "status": "verified",
      "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027091253-12fd05/start-plan.md",
      "visible_artifact": "session-reports/start-20261027091253-12fd05/start-plan.md"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 22,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:17:14+00:00",
    "event_id": "evt-0023-cab3dba7d2171a3e",
    "event_type": "planning_revision_approved",
    "payload": {
      "active_report": ".tailtrail/runs/start-20261027091253-12fd05/planning/revisions/start-report-v2.json",
      "anchor": ".tailtrail/runs/start-20261027091253-12fd05/anchors/approved-v1.json",
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/planning/revisions/revision-v2.json",
      "audit": {
        "report_fingerprint": "sha256:43ee792a8d5eb022de5fbc19bec674caece5337f6ac65a7ff805e9dfe544d338",
        "run_id": "start-20261027091253-12fd05",
        "source": "active-start-report",
        "status": "clean"
      },
      "revision": 2
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 23,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:25:40+00:00",
    "event_id": "evt-0024-193b57a2cc1ffffd",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/evidence-stream.jsonl",
      "fingerprint": "6d9942ff217b890d",
      "kind": "command-result",
      "sequence": 1
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 24,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:25:55+00:00",
    "event_id": "evt-0025-06fccc46595620b5",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/evidence-stream.jsonl",
      "fingerprint": "6eddbf4b153ed8a6",
      "kind": "command-result",
      "sequence": 2
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 25,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:26:04+00:00",
    "event_id": "evt-0026-b6453d4365742090",
    "event_type": "harness_checkpoint",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/checkpoints/checkpoint-1.json",
      "checkpoint": 1,
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-51177d1dd2be"
        },
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-71470147cd10"
        }
      ],
      "requirement_states": {
        "req-51177d1dd2be": "validated",
        "req-71470147cd10": "validated"
      }
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 26,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:26:08+00:00",
    "event_id": "evt-0027-d76bab7c760a9516",
    "event_type": "completion_review",
    "payload": {
      "artifact": "reviews/review-1.json",
      "checkpoint": 1,
      "complete": true,
      "findings": 0
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 27,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:26:08+00:00",
    "event_id": "evt-0028-2facafa6dce6cce2",
    "event_type": "completion_gate",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/completion-gates/gate-1.json",
      "complete": true,
      "findings": []
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 28,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:26:08+00:00",
    "event_id": "evt-0029-8ecaa42c786b0f3c",
    "event_type": "closure_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/closure-records/closure-8e81a801b7db9d26.json",
      "checkpoint": 1,
      "gate_complete": true,
      "receipt_count": 2,
      "record_id": "closure-8e81a801b7db9d26",
      "review_complete": true
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 29,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:26:16+00:00",
    "event_id": "evt-0030-0cc126160b4e64da",
    "event_type": "architecture_assessed",
    "payload": {
      "artifact": "architecture/assessment-1.json",
      "complete": true,
      "findings": 0
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 30,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:26:17+00:00",
    "event_id": "evt-0031-6b6cdc8fe209da13",
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
          "status": "pass",
          "used": true
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
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 31,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-27T09:26:25+00:00",
    "event_id": "evt-0032-406bf421a8e48717",
    "event_type": "navigator_graph_lifecycle_recorded",
    "payload": {
      "action": "refresh",
      "cache_fingerprint": "sha256:faf082af00cf735bf0488146427fbe47b12fc08284fd9efe6df77c240162f6a4",
      "mapping_fingerprint": "sha256:4796f4388472790680c74e1191ca24128c6906bac838d4b78dbc8c305f5a5b2d",
      "phase": "closure"
    },
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "sequence": 32,
    "type": "tailtrail-run-event"
  }
]
```

## Complete Saved Closure Payload

```json
{
  "assessments": {
    "Architecture Fitness Harness": {
      "artifact": null,
      "complete": true
    }
  },
  "boundary": "Finalized deterministic local control evidence only. No receipt command, deployment, recovery action, or external environment was executed.",
  "changed_paths": [
    "scripts/task-start.py",
    "tests/test_start_plan_presentation.py"
  ],
  "closure_record": {
    "boundary": "Recorded validated evidence. Managed-command receipts were executed and captured by TailTrail; declared host receipts remain explicitly unverified.",
    "changed_paths": [
      "scripts/task-start.py",
      "tests/test_start_plan_presentation.py"
    ],
    "checkpoint": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261027091253-12fd05/checkpoints/checkpoint-1.json",
    "completion_gate": {
      "complete": true,
      "findings": [],
      "rule": "Only trusted managed-command or attested artifact-backed evidence can pass a tier; any reported non-pass blocks and authoritative failure dominates pass.",
      "run_artifact": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261027091253-12fd05/completion-gates/gate-1.json",
      "run_id": "start-20261027091253-12fd05",
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
      "run_id": "start-20261027091253-12fd05",
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
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "type": "tailtrail-completion-review"
    },
    "next_action": "Run the selected harness assessments: Architecture Fitness Harness; then run tailtrail completion-report.",
    "proof_amendment_artifact": null,
    "receipt_artifacts": [
      ".tailtrail/runs/start-20261027091253-12fd05/validation-receipts/closure-8e81a801b7db9d26-1.json",
      ".tailtrail/runs/start-20261027091253-12fd05/validation-receipts/closure-8e81a801b7db9d26-2.json"
    ],
    "record_id": "closure-8e81a801b7db9d26",
    "reused": true,
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "selected_harnesses": [
      "Canonical requirements",
      "Question Orchestrator",
      "Requirement Completion Harness",
      "Requirement-to-Impact Map",
      "Evidence-Aware Testing",
      "Test Precision Planner",
      "Architecture Fitness Harness"
    ],
    "type": "tailtrail-closure-record",
    "validated_input": "execution/evidence-stream.jsonl"
  },
  "closure_record_id": "closure-8e81a801b7db9d26",
  "command_registry": {
    "cmd-62b3f5": {
      "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
      "kind": "proof"
    },
    "cmd-dcb44d": {
      "command": "python3 -m unittest discover -s tests -p test_start_plan_presentation.py -v",
      "kind": "proof"
    }
  },
  "completion_report": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261027091253-12fd05/completion-reports/report-1.json",
  "completion_report_payload": {
    "architecture": {
      "findings": [],
      "required": true,
      "status": "pass"
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
      "changed_paths": [
        {
          "fingerprint": "sha256:fa55c47d253cbac1f7fa8c2b663867f066494ad3d65f2ffdaea6a8166d64e2ff",
          "path": "scripts/task-start.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:435d1ded61687f78ba8e9b10f3f3ac0f2df84c74cc5a4aa472e725f0c0e3ccdd",
          "path": "tests/test_start_plan_presentation.py",
          "vcs_status": "modified",
          "verified": true
        }
      ],
      "findings": [],
      "status": "approved"
    },
    "closure_guidance": {
      "managed_proof_passing": true,
      "missing": [
        {
          "action": "tailtrail execution-evidence record --root . --run-id start-20261027091253-12fd05 --event '{\"kind\":\"source-edit\",\"requirement_uids\":[\"req-51177d1dd2be\",\"req-71470147cd10\"],\"changed_paths\":[\"scripts/task-start.py\",\"tests/test_start_plan_presentation.py\"]}' --approved",
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
      "implementation_applicable": true,
      "missing": [],
      "recovery": "",
      "request_mode": null,
      "required_artifacts": [],
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "source_edit_required": false,
      "status": "not-applicable",
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
      "approval_id": "wfauth-625dbbcb8d5c56bef5e78aad",
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
        "artifact": "architecture/assessment-1.json",
        "basis": "approved architecture contract or recorded architecture assessment",
        "name": "Architecture Fitness Harness",
        "status": "pass",
        "used": true
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
      "changed_paths": [
        {
          "fingerprint": "sha256:fa55c47d253cbac1f7fa8c2b663867f066494ad3d65f2ffdaea6a8166d64e2ff",
          "path": "scripts/task-start.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:435d1ded61687f78ba8e9b10f3f3ac0f2df84c74cc5a4aa472e725f0c0e3ccdd",
          "path": "tests/test_start_plan_presentation.py",
          "vcs_status": "modified",
          "verified": true
        }
      ],
      "status": "implemented"
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
      "active_badge": "test-badge",
      "active_stage": "TESTING",
      "completed_stages": [
        "IMPLEMENTATION"
      ],
      "handoff_count": 1,
      "status": "badged",
      "unvisited_stages": [
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
      "current": 2,
      "current_fingerprint": "sha256:df50d833d177067f491988ce6fb6f0bb47b1906b7cafdc3a521b9cc3e257cedc",
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
      "complete": 2,
      "requirements": [
        {
          "display_id": "REQ-01",
          "drift": [
            {
              "category": "evidence",
              "classification": "resolved",
              "requirement_uid": "req-51177d1dd2be"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.json",
              "asserted_behavior": "Implement generic Start Plan projection for validation-only host contracts",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
              "command_label": "validation-only host-contract projection regression",
              "duration_ms": 3248,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-27T09:25:39.415709+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-51177d1dd2be"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-27T09:25:36.167575+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.stderr.txt",
              "stderr_sha256": "sha256:e5766a12a9b9962bddebf6d7b305230a341d28ce3f29ab48fc37eb1c70626a99",
              "stdout_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.stdout.txt",
              "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              "tier": "contract",
              "tiers": [
                "contract"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "implemented",
          "requirement_uid": "req-51177d1dd2be",
          "statement": "Implement generic Start Plan projection for validation-only host contracts",
          "status": "complete",
          "verification_status": "pass"
        },
        {
          "display_id": "REQ-02",
          "drift": [
            {
              "category": "evidence",
              "classification": "resolved",
              "requirement_uid": "req-71470147cd10"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.json",
              "asserted_behavior": "do not grant implementation authority, auto-credit proof, or alter completion semantics.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
              "command_label": "validation-only host-contract projection safety regression",
              "duration_ms": 3439,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-27T09:25:54.067529+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-71470147cd10"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-27T09:25:50.628392+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.stderr.txt",
              "stderr_sha256": "sha256:031d9168b7a48fdf28914b24ad124a5b1a79d360abce562507590dece2cf9b70",
              "stdout_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.stdout.txt",
              "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              "tier": "unit",
              "tiers": [
                "unit"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "implemented",
          "requirement_uid": "req-71470147cd10",
          "statement": "do not grant implementation authority, auto-credit proof, or alter completion semantics.",
          "status": "complete",
          "verification_status": "pass"
        }
      ],
      "total": 2
    },
    "run_artifact": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261027091253-12fd05/completion-reports/report-1.json",
    "run_id": "start-20261027091253-12fd05",
    "schema_version": "1",
    "session_reports": {
      "closure": {
        "absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027091253-12fd05/closure-report.md",
        "exists": false,
        "workspace_path": "session-reports/start-20261027091253-12fd05/closure-report.md"
      },
      "start": {
        "absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027091253-12fd05/start-plan.md",
        "exists": true,
        "workspace_path": "session-reports/start-20261027091253-12fd05/start-plan.md"
      }
    },
    "source_artifacts": {
      "active_plan": "planning/revisions/start-report-v2.json",
      "approved_anchor": "anchors/approved-v1.json",
      "architecture": "architecture/assessment-1.json",
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
        "detail": "2 changed path(s); 0 saved blocker(s)",
        "status": "implemented"
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
        "detail": "2 saved changed path(s)",
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
        "status": "pass"
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
        "detail": "12774 focused tokens",
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
        ".tailtrail/runs/start-20261027091253-12fd05/validation-receipts/closure-8e81a801b7db9d26-1.json",
        ".tailtrail/runs/start-20261027091253-12fd05/validation-receipts/closure-8e81a801b7db9d26-2.json"
      ],
      "receipts": [
        {
          "artifact_path": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.json",
          "asserted_behavior": "Implement generic Start Plan projection for validation-only host contracts",
          "closure_record_id": "closure-8e81a801b7db9d26",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
          "command_label": "validation-only host-contract projection regression",
          "duration_ms": 3248,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-27T09:25:39.415709+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:df50d833d177067f491988ce6fb6f0bb47b1906b7cafdc3a521b9cc3e257cedc",
          "requirement_uids": [
            "req-51177d1dd2be"
          ],
          "scenario_ids": [],
          "schema_version": "2",
          "started_at": "2026-10-27T09:25:36.167575+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.stderr.txt",
          "stderr_sha256": "sha256:e5766a12a9b9962bddebf6d7b305230a341d28ce3f29ab48fc37eb1c70626a99",
          "stdout_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "contract",
          "tiers": [
            "contract"
          ],
          "type": "tailtrail-validation-evidence-receipt"
        },
        {
          "artifact_path": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.json",
          "asserted_behavior": "do not grant implementation authority, auto-credit proof, or alter completion semantics.",
          "closure_record_id": "closure-8e81a801b7db9d26",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
          "command_label": "validation-only host-contract projection safety regression",
          "duration_ms": 3439,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-27T09:25:54.067529+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:df50d833d177067f491988ce6fb6f0bb47b1906b7cafdc3a521b9cc3e257cedc",
          "requirement_uids": [
            "req-71470147cd10"
          ],
          "scenario_ids": [],
          "schema_version": "2",
          "started_at": "2026-10-27T09:25:50.628392+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.stderr.txt",
          "stderr_sha256": "sha256:031d9168b7a48fdf28914b24ad124a5b1a79d360abce562507590dece2cf9b70",
          "stdout_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.stdout.txt",
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
        "comparison_basis": "scoped-files",
        "estimated_reduction_percent": 88.12,
        "estimated_saved_tokens": 94794,
        "forecast_confidence": "medium",
        "learning_evidence_references": [],
        "planned_working_set_tokens": 12774,
        "repository_ceiling_tokens": 2341252,
        "repository_file_count": 983,
        "saving_techniques": [
          "Navigator scope narrowing",
          "Focused validation selection"
        ],
        "scoped_file_ceiling_tokens": 107568,
        "scoped_tokens": 12774,
        "status": "estimated"
      },
      "planning_estimate_tokens": 12774,
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
  "delivery_record": ".tailtrail/runs/start-20261027091253-12fd05/delivery-record.md",
  "execution_events": [
    {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.json",
      "asserted_behavior": "Implement generic Start Plan projection for validation-only host contracts",
      "changed_paths": [
        "scripts/task-start.py",
        "tests/test_start_plan_presentation.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
      "command_label": "validation-only host-contract projection regression",
      "duration_ms": 3248,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "6d9942ff217b890d",
      "finished_at": "2026-10-27T09:25:39.415709+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:df50d833d177067f491988ce6fb6f0bb47b1906b7cafdc3a521b9cc3e257cedc",
      "requirement_uids": [
        "req-51177d1dd2be"
      ],
      "run_id": "start-20261027091253-12fd05",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 1,
      "started_at": "2026-10-27T09:25:36.167575+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.stderr.txt",
      "stderr_sha256": "sha256:e5766a12a9b9962bddebf6d7b305230a341d28ce3f29ab48fc37eb1c70626a99",
      "stdout_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-0844ee8516afcafa.stdout.txt",
      "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "tier": "contract",
      "tiers": [
        "contract"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.json",
      "asserted_behavior": "do not grant implementation authority, auto-credit proof, or alter completion semantics.",
      "changed_paths": [
        "scripts/task-start.py",
        "tests/test_start_plan_presentation.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate",
      "command_label": "validation-only host-contract projection safety regression",
      "duration_ms": 3439,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "6eddbf4b153ed8a6",
      "finished_at": "2026-10-27T09:25:54.067529+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:df50d833d177067f491988ce6fb6f0bb47b1906b7cafdc3a521b9cc3e257cedc",
      "requirement_uids": [
        "req-71470147cd10"
      ],
      "run_id": "start-20261027091253-12fd05",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 2,
      "started_at": "2026-10-27T09:25:50.628392+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.stderr.txt",
      "stderr_sha256": "sha256:031d9168b7a48fdf28914b24ad124a5b1a79d360abce562507590dece2cf9b70",
      "stdout_artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/command-artifacts/command-5f27ed2b9ec9299e.stdout.txt",
      "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "tier": "unit",
      "tiers": [
        "unit"
      ],
      "type": "tailtrail-execution-evidence"
    }
  ],
  "finalizer_id": "finalizer-448906644f550704",
  "graph_lifecycle": {
    "action": "refresh",
    "after_status": {
      "reasons": [
        "Cached graph scope and watched file hashes still match."
      ],
      "scope": [
        "tests/test_review_graph.py",
        "scripts/repository_path_policy.py",
        "scripts/workflow_runtime/storage.py",
        "scripts/harness-checkpoint.py",
        "tests/test_review_scope.py",
        "tests/test_task_recovery.py",
        "tests/test_question_orchestrator.py",
        "release-manifest.json",
        "scripts/completion-report.py",
        "scripts/aidlc-official-host.py",
        "scripts/behaviour_planning.py",
        "tests/test_completion_report.py",
        "scripts/aidlc-official-install.py",
        "scripts/review-graph.py",
        "scripts/closure-close.py",
        "scripts/meta-harness-analyze.py",
        "tests/test_install_profiles.py",
        "tests/test_navigator_graph_lifecycle.py",
        "tests/test_mcp_server.py",
        "buildweek-demo-project/src/claims_api/validation.py",
        "scripts/docs-only.py",
        "scripts/learning-use-receipt.py",
        "scripts/navigator_scope.py",
        "tests/test_tailtrail_registry.py",
        "scripts/host-reply-validate.py",
        "tests/test_workflow_adapters.py",
        "scripts/host-decision.py",
        "scripts/aidlc-requirements.py",
        "scripts/delivery-record.py",
        "scripts/debug-host-diagnosis.py",
        "scripts/execution-evidence.py",
        "scripts/adoption-validation.py",
        "scripts/requirement_intake.py",
        "tests/test_workflow_start_integration.py",
        "scripts/navigator.py",
        "scripts/navigator-scope-release.py",
        "tests/test_aidlc_official_host.py",
        "scripts/debug-correction.py",
        "tests/test_new_file_due_diligence.py",
        "tests/test_workflow_contracts.py",
        "tests/test_full_pipeline.py",
        "scripts/completion-review.py",
        "tests/test_planning_audit.py",
        "scripts/host_contract.py",
        "tests/test_workflow_phase7.py",
        "tests/test_closure_recorder.py",
        "tests/test_host_input_contract_schema.py",
        "tests/test_workflow_approvals.py",
        "scripts/closure-learning.py",
        "scripts/evidence-tiers.py",
        "tests/test_revision_proof_overlay.py",
        "tests/test_code_graph_inventory.py",
        "tests/test_workflow_documentation.py",
        "scripts/planning-revision.py",
        "scripts/aidlc-official-bridge.py",
        "scripts/pipeline_orchestrator.py",
        "tests/test_planning_lock.py",
        "scripts/closure-correction.py",
        "tests/test_execution_evidence.py",
        "scripts/planning-audit.py",
        "scripts/write_guardian.py",
        "scripts/learning-refresh.py",
        "tests/test_closure_finalizer.py",
        "tests/test_host_packet_tickets.py",
        "scripts/task-start.py",
        "scripts/requirement_discovery.py",
        "tests/test_debug_start_planning.py",
        "scripts/debug-preflight.py",
        "tests/test_canonical_statement_contract.py",
        "scripts/official-aidlc-checkpoint.py",
        "demo-project-layout/tailtrail-demo-workspace/services/claims-api/tests/test_validation.py",
        "scripts/official-aidlc-state.py",
        "tests/test_requirement_discovery.py",
        "tests/test_start_entrypoints.py",
        "scripts/new_file_due_diligence.py",
        "scripts/workflow_runtime/enterprise_transport.py",
        "scripts/navigator_discovery.py",
        "scripts/intake_pipeline.py",
        "tests/test_repository_path_policy.py",
        "tests/test_intake_pipeline.py",
        "tests/test_host_question_flow_phase0_artifacts.py",
        "scripts/planning_lock.py",
        "tests/test_sequential_pipeline.py",
        "scripts/verbose-reporting.py",
        "tests/test_workflow_dashboard.py",
        "tests/test_evaluation_audit.py",
        "scripts/debug-completion.py",
        "scripts/check-tailtrail.py",
        "tests/test_task_type_contract.py",
        "tests/test_demo_prompt_book.py",
        "tests/test_task_type_gate.py",
        "tests/test_workflow_privacy.py",
        "scripts/aidlc-init.py",
        "scripts/tailtrail.py",
        "tests/test_target_workspace.py",
        "scripts/advanced-runtime.py",
        "scripts/greenfield_e2e_fixture.py",
        "tests/test_greenfield_e2e.py",
        "scripts/install-local.py",
        "scripts/closure-contract.py",
        "scripts/architecture_planning.py",
        "scripts/architecture-fitness.py",
        "scripts/debug-harness-convergence.py",
        "tests/test_enterprise_host_adapters.py",
        "tests/test_start_plan_presentation.py",
        "tests/test_planning_revision.py",
        "tests/test_write_guardian.py",
        "scripts/aidlc-check.py",
        "scripts/closure-evaluation.py",
        "scripts/learning-agent.py",
        "hooks/hooks.json",
        "scripts/planning-aidlc-question.py",
        "tests/test_host_contract.py",
        "scripts/ast-map.py",
        "tests/test_public_route_gate.py",
        "scripts/requirement-completion.py",
        "scripts/code_graph_cache.py",
        "tests/test_architecture_fitness.py",
        "tests/test_debug_harness.py",
        "tests/test_aidlc_official_bridge.py",
        "tests/test_delivery_record.py",
        "tests/test_workflow_ci_continuation.py",
        "tests/test_workflow_ownership.py",
        "tests/test_navigator_scope.py",
        "scripts/run-ledger.py",
        "tests/test_workflow_template_execution.py",
        "scripts/workflow_runtime/start_integration.py",
        "scripts/host-adapter-conformance.py",
        "scripts/code-graph-mapper.py",
        "scripts/navigator-scope.py",
        "tests/test_navigator_core.py",
        "scripts/closure-recorder.py",
        "tests/test_requirement_routing_phase0.py",
        "tests/test_host_question_flow_event_schema.py",
        "scripts/question-orchestrator.py",
        "scripts/aidlc-official-detect.py",
        "scripts/install-copilot.py",
        "tests/test_navigator_installed_release.py",
        "scripts/workflow-dashboard.py",
        "scripts/update-copilot.py",
        "tests/test_host_adapter_conformance.py",
        "pyproject.toml",
        "scripts/mcp-server.py",
        "tests/test_code_graph_cache.py",
        "scripts/planning-discussion.py",
        "scripts/official-aidlc-requirements.py",
        "scripts/benchmark-tailtrail.py",
        "schemas/host-question-flow-event.schema.json",
        "schemas/host-input-contract.schema.json",
        "tests/test_debug_host_integration.py",
        "tests/test_completion_review.py",
        "scripts/closure-finalizer.py",
        "tests/test_visual_requirement.py",
        "scripts/change-intent-anchor.py"
      ],
      "status": "fresh"
    },
    "attempt_id": "start-20261027091253-12fd05",
    "before_status": {
      "reasons": [
        "Relevant repository file inventory changed after the graph was created."
      ],
      "scope": [
        "tests/test_review_graph.py",
        "scripts/repository_path_policy.py",
        "scripts/workflow_runtime/storage.py",
        "scripts/harness-checkpoint.py",
        "tests/test_review_scope.py",
        "tests/test_task_recovery.py",
        "tests/test_question_orchestrator.py",
        "release-manifest.json",
        "scripts/completion-report.py",
        "scripts/aidlc-official-host.py",
        "scripts/behaviour_planning.py",
        "tests/test_completion_report.py",
        "scripts/aidlc-official-install.py",
        "scripts/review-graph.py",
        "scripts/closure-close.py",
        "scripts/meta-harness-analyze.py",
        "tests/test_install_profiles.py",
        "tests/test_navigator_graph_lifecycle.py",
        "tests/test_mcp_server.py",
        "buildweek-demo-project/src/claims_api/validation.py",
        "scripts/docs-only.py",
        "scripts/learning-use-receipt.py",
        "scripts/navigator_scope.py",
        "tests/test_tailtrail_registry.py",
        "scripts/host-reply-validate.py",
        "tests/test_workflow_adapters.py",
        "scripts/host-decision.py",
        "scripts/aidlc-requirements.py",
        "scripts/delivery-record.py",
        "scripts/debug-host-diagnosis.py",
        "scripts/execution-evidence.py",
        "scripts/adoption-validation.py",
        "scripts/requirement_intake.py",
        "tests/test_workflow_start_integration.py",
        "scripts/navigator.py",
        "scripts/navigator-scope-release.py",
        "tests/test_aidlc_official_host.py",
        "scripts/debug-correction.py",
        "tests/test_new_file_due_diligence.py",
        "tests/test_workflow_contracts.py",
        "tests/test_full_pipeline.py",
        "scripts/completion-review.py",
        "tests/test_planning_audit.py",
        "scripts/host_contract.py",
        "tests/test_workflow_phase7.py",
        "tests/test_closure_recorder.py",
        "tests/test_host_input_contract_schema.py",
        "tests/test_workflow_approvals.py",
        "scripts/closure-learning.py",
        "scripts/evidence-tiers.py",
        "tests/test_revision_proof_overlay.py",
        "tests/test_code_graph_inventory.py",
        "tests/test_workflow_documentation.py",
        "scripts/planning-revision.py",
        "scripts/aidlc-official-bridge.py",
        "scripts/pipeline_orchestrator.py",
        "tests/test_planning_lock.py",
        "scripts/closure-correction.py",
        "tests/test_execution_evidence.py",
        "scripts/planning-audit.py",
        "scripts/write_guardian.py",
        "scripts/learning-refresh.py",
        "tests/test_closure_finalizer.py",
        "tests/test_host_packet_tickets.py",
        "scripts/task-start.py",
        "scripts/requirement_discovery.py",
        "tests/test_debug_start_planning.py",
        "scripts/debug-preflight.py",
        "tests/test_canonical_statement_contract.py",
        "scripts/official-aidlc-checkpoint.py",
        "demo-project-layout/tailtrail-demo-workspace/services/claims-api/tests/test_validation.py",
        "scripts/official-aidlc-state.py",
        "tests/test_requirement_discovery.py",
        "tests/test_start_entrypoints.py",
        "scripts/new_file_due_diligence.py",
        "scripts/workflow_runtime/enterprise_transport.py",
        "scripts/navigator_discovery.py",
        "scripts/intake_pipeline.py",
        "tests/test_repository_path_policy.py",
        "tests/test_intake_pipeline.py",
        "tests/test_host_question_flow_phase0_artifacts.py",
        "scripts/planning_lock.py",
        "tests/test_sequential_pipeline.py",
        "scripts/verbose-reporting.py",
        "tests/test_workflow_dashboard.py",
        "tests/test_evaluation_audit.py",
        "scripts/debug-completion.py",
        "scripts/check-tailtrail.py",
        "tests/test_task_type_contract.py",
        "tests/test_demo_prompt_book.py",
        "tests/test_task_type_gate.py",
        "tests/test_workflow_privacy.py",
        "scripts/aidlc-init.py",
        "scripts/tailtrail.py",
        "tests/test_target_workspace.py",
        "scripts/advanced-runtime.py",
        "scripts/greenfield_e2e_fixture.py",
        "tests/test_greenfield_e2e.py",
        "scripts/install-local.py",
        "scripts/closure-contract.py",
        "scripts/architecture_planning.py",
        "scripts/architecture-fitness.py",
        "scripts/debug-harness-convergence.py",
        "tests/test_enterprise_host_adapters.py",
        "tests/test_start_plan_presentation.py",
        "tests/test_planning_revision.py",
        "tests/test_write_guardian.py",
        "scripts/aidlc-check.py",
        "scripts/closure-evaluation.py",
        "scripts/learning-agent.py",
        "hooks/hooks.json",
        "scripts/planning-aidlc-question.py",
        "tests/test_host_contract.py",
        "scripts/ast-map.py",
        "tests/test_public_route_gate.py",
        "scripts/requirement-completion.py",
        "scripts/code_graph_cache.py",
        "tests/test_architecture_fitness.py",
        "tests/test_debug_harness.py",
        "tests/test_aidlc_official_bridge.py",
        "tests/test_delivery_record.py",
        "tests/test_workflow_ci_continuation.py",
        "tests/test_workflow_ownership.py",
        "tests/test_navigator_scope.py",
        "scripts/run-ledger.py",
        "tests/test_workflow_template_execution.py",
        "scripts/workflow_runtime/start_integration.py",
        "scripts/host-adapter-conformance.py",
        "scripts/code-graph-mapper.py",
        "scripts/navigator-scope.py",
        "tests/test_navigator_core.py",
        "scripts/closure-recorder.py",
        "tests/test_requirement_routing_phase0.py",
        "tests/test_host_question_flow_event_schema.py",
        "scripts/question-orchestrator.py",
        "scripts/aidlc-official-detect.py",
        "scripts/install-copilot.py",
        "tests/test_navigator_installed_release.py",
        "scripts/workflow-dashboard.py",
        "scripts/update-copilot.py",
        "tests/test_host_adapter_conformance.py",
        "pyproject.toml",
        "scripts/mcp-server.py",
        "tests/test_code_graph_cache.py",
        "scripts/planning-discussion.py",
        "scripts/official-aidlc-requirements.py",
        "scripts/benchmark-tailtrail.py",
        "schemas/host-question-flow-event.schema.json",
        "schemas/host-input-contract.schema.json",
        "tests/test_debug_host_integration.py",
        "tests/test_completion_review.py",
        "scripts/closure-finalizer.py",
        "tests/test_visual_requirement.py",
        "scripts/change-intent-anchor.py"
      ],
      "status": "stale"
    },
    "boundary": "Navigator may create or refresh TailTrail graph metadata; current-source scope evidence and Planning Lock approval remain mandatory.",
    "cache_fingerprint": "sha256:faf082af00cf735bf0488146427fbe47b12fc08284fd9efe6df77c240162f6a4",
    "cache_path": "tailtrail-meta/code-graph-cache.json",
    "cache_reuse_state": null,
    "cache_shape": "mapper",
    "cache_warnings": [
      "legacy v1 mapper shape; migrates to a v2 container on next Phase-1 write"
    ],
    "fingerprint": "sha256:e63cfdc058d8120e55cbf0e39090549ec937988ad178aa9758a80177c3289480",
    "freshness": "stale",
    "implementation_authority": false,
    "metadata_only": true,
    "outside_slice_nominations": [],
    "phase": "closure",
    "reason_codes": [
      "explicit-scope-paths",
      "persistent-graph-stale"
    ],
    "relevance": "not-evaluated",
    "requested_mode": "auto",
    "schema_version": "1",
    "target_paths": [
      "scripts/task-start.py",
      "tests/test_start_plan_presentation.py"
    ],
    "type": "tailtrail-navigator-graph-lifecycle",
    "written": true
  },
  "harness_review": {
    "recorded": true
  },
  "higher_tier_evidence": {
    "boundary": "The finalizer reads the current closure snapshot and accepts only trusted managed-command or attested artifact-backed higher-tier receipts.",
    "missing": [],
    "required": [
      {
        "requirement_uid": "req-51177d1dd2be",
        "tier": "contract"
      }
    ],
    "status": "pass"
  },
  "ledger_events": [
    {
      "created_at": "2026-10-27T09:13:05+00:00",
      "event_id": "evt-0001-b01c4cf3d0b40530",
      "event_type": "run_created",
      "payload": {
        "goal": "Implement generic Start Plan projection for validation-only host contracts: preserve every accepted inspection-input and proof-only path; retain the global proof command as unbound context; require explicit requirement-level proof bindings before readiness; do not grant implementation authority, auto-credit proof, or alter completion semantics."
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 1,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:13:05+00:00",
      "event_id": "evt-0002-daa2da8a460e23bf",
      "event_type": "planning_lock_created",
      "payload": {
        "artifact": "planning/lock-v1.json",
        "input_roles": {
          "read_only_inputs": 0
        },
        "reference_roots": [],
        "target_fingerprint": "sha256:791d2db9cecbfe080226bed62d29199fe85f5c3373391f50ee1ff9cbb63eda48",
        "writes_allowed": false
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 2,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:13:05+00:00",
      "event_id": "evt-0003-a99641c2d9862bfc",
      "event_type": "target_resolution_recorded",
      "payload": {
        "policy_status": "not-configured",
        "target_resolution_receipt": ".tailtrail/runs/start-20261027091253-12fd05/planning/target-resolution-receipt-v1.json"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 3,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:13:05+00:00",
      "event_id": "evt-0004-1b860ffa22b908cf",
      "event_type": "start_report_saved",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/planning/start-report-v1.json"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 4,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:13:05+00:00",
      "event_id": "evt-0005-33077bac5ae00812",
      "event_type": "start_plan_verbose_generated",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/verbose-reports/start-plan-verbose-v1.md",
        "mandatory": true,
        "markdown_size": 7291,
        "status": "verified",
        "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027091253-12fd05/start-plan.md",
        "visible_artifact": "session-reports/start-20261027091253-12fd05/start-plan.md"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 5,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:13:05+00:00",
      "event_id": "evt-0006-7a3ad6218699f640",
      "event_type": "tailtrail_session_attached",
      "payload": {
        "context_key_hash": "sha256:8f7ea5b4e0bf204739b270db4b34f3ff3560126663ca15a47c97490c5a4c8b70",
        "fingerprint": "sha256:da89beeb88a56ac4797da92cf7d3c6f05faac33323722a8147df56ca58e4bb6a",
        "generation": 285,
        "reason_code": "tailtrail-start"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 6,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:13:15+00:00",
      "event_id": "evt-0007-e07c51d04831e3f7",
      "event_type": "planning_audit_completed",
      "payload": {
        "finding_count": 3,
        "revision_cycles": 0,
        "status": "gaps-found",
        "total_review_cycles": 1
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 7,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:14:05+00:00",
      "event_id": "evt-0008-d55ab234c2381078",
      "event_type": "planning_revision_proposed",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/planning/revisions/revision-v2.json",
        "base_revision": 1,
        "requirement_uids": [
          "req-51177d1dd2be",
          "req-71470147cd10"
        ],
        "revision": 2
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 8,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:14:05+00:00",
      "event_id": "evt-0009-99667dd1092320b2",
      "event_type": "planning_audit_completed",
      "payload": {
        "finding_count": 0,
        "revision_cycles": 1,
        "status": "clean",
        "total_review_cycles": 2
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 9,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:00+00:00",
      "event_id": "evt-0010-ba412520541252b2",
      "event_type": "anchor_drafted",
      "payload": {
        "fingerprint": "sha256:e4c328a36becdc05bba6dfa9a16e2eaba2886bc4e932e7b9df3ccad61895fb23",
        "proposal_version": 1,
        "requirements": [
          "req-51177d1dd2be",
          "req-71470147cd10"
        ]
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 10,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:00+00:00",
      "event_id": "evt-0011-00c4d075861f2093",
      "event_type": "anchor_approved",
      "payload": {
        "fingerprint": "sha256:caec26e264767d23acfea4e17410937b36544305853a31e4f73391121958b5c8",
        "path": ".tailtrail/runs/start-20261027091253-12fd05/anchors/approved-v1.json",
        "requirements": [
          "req-51177d1dd2be",
          "req-71470147cd10"
        ]
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 11,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:00+00:00",
      "event_id": "evt-0012-36e9073c953e6919",
      "event_type": "planning_lock_approved",
      "payload": {
        "artifact": "planning/lock-v1.json",
        "audit": {
          "report_fingerprint": "sha256:43ee792a8d5eb022de5fbc19bec674caece5337f6ac65a7ff805e9dfe544d338",
          "run_id": "start-20261027091253-12fd05",
          "source": "active-start-report",
          "status": "clean"
        },
        "writes_allowed": true
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 12,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:02+00:00",
      "event_id": "evt-0013-0e939678975f479e",
      "event_type": "workflow_ownership_bound",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-ce45b404e02d/ownership-v1.json",
        "requirement_uids": [
          "req-51177d1dd2be",
          "req-71470147cd10"
        ],
        "workflow_id": "ttw-ce45b404e02d"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 13,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:03+00:00",
      "event_id": "evt-0014-b762c9a13ec51b87",
      "event_type": "workflow_capability_plan_declared",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-ce45b404e02d/capability-plan-v1.json",
        "capability_ids": [
          "navigator",
          "quality-signals",
          "review",
          "testing"
        ],
        "plan_fingerprint": "sha256:ea7e054495586cb7574c93dd2a19edb5b8e9ab9248bb697041c12b5b46881d3b",
        "workflow_id": "ttw-ce45b404e02d"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 14,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:04+00:00",
      "event_id": "evt-0015-d4ffb516d0015759",
      "event_type": "workflow_storage_initialized",
      "payload": {
        "journal": ".tailtrail/workflows/ttw-ce45b404e02d/journal-v1.jsonl",
        "projection": ".tailtrail/workflows/ttw-ce45b404e02d/projection-v1.json",
        "workflow_id": "ttw-ce45b404e02d"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 15,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:04+00:00",
      "event_id": "evt-0016-7d7032c1e7da6ba9",
      "event_type": "workflow_state_created",
      "payload": {
        "journal": ".tailtrail/workflows/ttw-ce45b404e02d/journal-v1.jsonl",
        "sequence": 2,
        "workflow_id": "ttw-ce45b404e02d"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 16,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:14+00:00",
      "event_id": "evt-0017-546fe1fa6763113b",
      "event_type": "workflow_compiler_plan_created",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-ce45b404e02d/compiler-plan-v1.json",
        "plan_fingerprint": "sha256:f4fac53f44ab8fdbb6c663669d1d1dd4f58368e8b733b9771a2946b344db7726",
        "revision": 1,
        "template_id": "small-change",
        "workflow_id": "ttw-ce45b404e02d"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 17,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:14+00:00",
      "event_id": "evt-0018-d4fc7db8e6f4988c",
      "event_type": "workflow_stage_approval_recorded",
      "payload": {
        "action_classes": [
          "write_tailtrail_state"
        ],
        "approval_id": "wfauth-4aeeb4e953b6f150f7a78f8f",
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
        "workflow_id": "ttw-ce45b404e02d"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 18,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:14+00:00",
      "event_id": "evt-0019-c837756a626690da",
      "event_type": "workflow_stage_approval_recorded",
      "payload": {
        "action_classes": [
          "execute_project",
          "read_local",
          "write_project",
          "write_tailtrail_state"
        ],
        "approval_id": "wfauth-625dbbcb8d5c56bef5e78aad",
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
        "workflow_id": "ttw-ce45b404e02d"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 19,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:14+00:00",
      "event_id": "evt-0020-27a15b8fec1c537c",
      "event_type": "workflow_runtime_activated",
      "payload": {
        "binding": ".tailtrail/workflows/ttw-ce45b404e02d/ownership-v1.json",
        "capability_plan": ".tailtrail/workflows/ttw-ce45b404e02d/capability-plan-v1.json",
        "compiler_plan": ".tailtrail/workflows/ttw-ce45b404e02d/compiler-plan-v1.json",
        "compiler_plan_fingerprint": "sha256:f4fac53f44ab8fdbb6c663669d1d1dd4f58368e8b733b9771a2946b344db7726",
        "workflow_id": "ttw-ce45b404e02d"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 20,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:14+00:00",
      "event_id": "evt-0021-a1462d4035957316",
      "event_type": "planning_activated",
      "payload": {
        "activation_audit": {
          "report_fingerprint": "sha256:43ee792a8d5eb022de5fbc19bec674caece5337f6ac65a7ff805e9dfe544d338",
          "run_id": "start-20261027091253-12fd05",
          "source": "active-start-report",
          "status": "clean"
        },
        "anchor": {
          "artifact": ".tailtrail/runs/start-20261027091253-12fd05/anchors/approved-v1.json",
          "requirements": [
            "req-51177d1dd2be",
            "req-71470147cd10"
          ],
          "status": "created"
        },
        "enterprise_policy_status": "not-configured",
        "handoff": "planning/execution-handoff-v1.json",
        "input_role_status": "matched",
        "official_aidlc_bridge_activation": null,
        "scope_decision_status": "matched-revision",
        "target_identity_status": "matched",
        "workflow_runtime": "compiled"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 21,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:14+00:00",
      "event_id": "evt-0022-1524d7cd8dd77aaf",
      "event_type": "start_plan_verbose_generated",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/verbose-reports/start-plan-verbose-v1.md",
        "mandatory": true,
        "markdown_size": 7351,
        "status": "verified",
        "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027091253-12fd05/start-plan.md",
        "visible_artifact": "session-reports/start-20261027091253-12fd05/start-plan.md"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 22,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:17:14+00:00",
      "event_id": "evt-0023-cab3dba7d2171a3e",
      "event_type": "planning_revision_approved",
      "payload": {
        "active_report": ".tailtrail/runs/start-20261027091253-12fd05/planning/revisions/start-report-v2.json",
        "anchor": ".tailtrail/runs/start-20261027091253-12fd05/anchors/approved-v1.json",
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/planning/revisions/revision-v2.json",
        "audit": {
          "report_fingerprint": "sha256:43ee792a8d5eb022de5fbc19bec674caece5337f6ac65a7ff805e9dfe544d338",
          "run_id": "start-20261027091253-12fd05",
          "source": "active-start-report",
          "status": "clean"
        },
        "revision": 2
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 23,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:25:40+00:00",
      "event_id": "evt-0024-193b57a2cc1ffffd",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/evidence-stream.jsonl",
        "fingerprint": "6d9942ff217b890d",
        "kind": "command-result",
        "sequence": 1
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 24,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:25:55+00:00",
      "event_id": "evt-0025-06fccc46595620b5",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/execution/evidence-stream.jsonl",
        "fingerprint": "6eddbf4b153ed8a6",
        "kind": "command-result",
        "sequence": 2
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 25,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:26:04+00:00",
      "event_id": "evt-0026-b6453d4365742090",
      "event_type": "harness_checkpoint",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/checkpoints/checkpoint-1.json",
        "checkpoint": 1,
        "drift": [
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-51177d1dd2be"
          },
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-71470147cd10"
          }
        ],
        "requirement_states": {
          "req-51177d1dd2be": "validated",
          "req-71470147cd10": "validated"
        }
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 26,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:26:08+00:00",
      "event_id": "evt-0027-d76bab7c760a9516",
      "event_type": "completion_review",
      "payload": {
        "artifact": "reviews/review-1.json",
        "checkpoint": 1,
        "complete": true,
        "findings": 0
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 27,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:26:08+00:00",
      "event_id": "evt-0028-2facafa6dce6cce2",
      "event_type": "completion_gate",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/completion-gates/gate-1.json",
        "complete": true,
        "findings": []
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 28,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:26:08+00:00",
      "event_id": "evt-0029-8ecaa42c786b0f3c",
      "event_type": "closure_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261027091253-12fd05/closure-records/closure-8e81a801b7db9d26.json",
        "checkpoint": 1,
        "gate_complete": true,
        "receipt_count": 2,
        "record_id": "closure-8e81a801b7db9d26",
        "review_complete": true
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 29,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:26:16+00:00",
      "event_id": "evt-0030-0cc126160b4e64da",
      "event_type": "architecture_assessed",
      "payload": {
        "artifact": "architecture/assessment-1.json",
        "complete": true,
        "findings": 0
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 30,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:26:17+00:00",
      "event_id": "evt-0031-6b6cdc8fe209da13",
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
            "status": "pass",
            "used": true
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
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 31,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-27T09:26:25+00:00",
      "event_id": "evt-0032-406bf421a8e48717",
      "event_type": "navigator_graph_lifecycle_recorded",
      "payload": {
        "action": "refresh",
        "cache_fingerprint": "sha256:faf082af00cf735bf0488146427fbe47b12fc08284fd9efe6df77c240162f6a4",
        "mapping_fingerprint": "sha256:4796f4388472790680c74e1191ca24128c6906bac838d4b78dbc8c305f5a5b2d",
        "phase": "closure"
      },
      "run_id": "start-20261027091253-12fd05",
      "schema_version": "1",
      "sequence": 32,
      "type": "tailtrail-run-event"
    }
  ],
  "overall_status": "complete",
  "pipeline": {
    "active_badge": "test-badge",
    "active_stage": "TESTING",
    "completed_stages": [
      "IMPLEMENTATION"
    ],
    "handoff_count": 1,
    "status": "badged",
    "unvisited_stages": [
      "INFRA"
    ]
  },
  "recovery": {
    "boundary": null,
    "status": "not-needed"
  },
  "run_id": "start-20261027091253-12fd05",
  "run_mapping": {
    "closure_status": "complete",
    "goal_fingerprint": "sha256:0eb72aae5b9cde83c8a773253218738a93f1ec1b3edd035b302c847152d7c928",
    "graph_cache_fingerprint": "sha256:faf082af00cf735bf0488146427fbe47b12fc08284fd9efe6df77c240162f6a4",
    "mapping_fingerprint": "sha256:4796f4388472790680c74e1191ca24128c6906bac838d4b78dbc8c305f5a5b2d",
    "path_hashes": {
      "tests/test_public_route_gate.py": "sha256:3fcf41386e0c9b0c1a242fc5471fc03b00dbb18c744db415a1ea6482ed1596fb",
      "tests/test_start_plan_presentation.py": "sha256:435d1ded61687f78ba8e9b10f3f3ac0f2df84c74cc5a4aa472e725f0c0e3ccdd"
    },
    "query_terms": [
      "accepted",
      "alter",
      "and",
      "authority",
      "auto-credit",
      "bindings",
      "command",
      "completion",
      "context",
      "contracts",
      "every",
      "explicit",
      "for",
      "generic",
      "global",
      "grant",
      "host",
      "implement",
      "implementation",
      "inspection-input",
      "not",
      "path",
      "plan",
      "preserve",
      "projection",
      "proof",
      "proof-only",
      "readiness",
      "require",
      "requirement-level",
      "retain",
      "semantics",
      "start",
      "the",
      "unbound",
      "validation-only"
    ],
    "recorded_at": "2026-10-27T09:26:25.717133+00:00",
    "run_id": "start-20261027091253-12fd05",
    "scope_decision_fingerprint": "sha256:8c8f5f26152cb5e6ed838fcfe9f91cc5263a2fab0ea10490bdf29549edf465eb"
  },
  "schema_version": "1",
  "selected_harnesses": [
    "Canonical requirements",
    "Question Orchestrator",
    "Requirement Completion Harness",
    "Requirement-to-Impact Map",
    "Evidence-Aware Testing",
    "Test Precision Planner",
    "Architecture Fitness Harness"
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
    "artifact": ".tailtrail/runs/start-20261027091253-12fd05/verbose-reports/closure-verbose-v1.md",
    "mandatory": true,
    "markdown_size": 105488,
    "run_id": "start-20261027091253-12fd05",
    "status": "generated",
    "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261027091253-12fd05/closure-report.md",
    "visible_artifact": "session-reports/start-20261027091253-12fd05/closure-report.md"
  },
  "workflow_closure": {
    "artifact": ".tailtrail/workflows/ttw-ce45b404e02d/completion-receipt-v1.json",
    "boundary": "Completion follows the canonical TailTrail Completion Report. An evidence-incomplete receipt is not a successful workflow completion and does not authorize a retry or recovery.",
    "completion_report": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261027091253-12fd05/completion-reports/report-1.json",
    "completion_status": "complete",
    "evidence_fingerprint": "sha256:04da26cba02a3c1b9d95fba5a1fa417e6752dcbc1bf6b704e32a72c9f21414a6",
    "receipt_fingerprint": "sha256:d5ad44a9e0f6b6fafcec85ae6fe1674c6757164bb88841a596c8123d5a25bc24",
    "schema_version": "1",
    "state": "completed",
    "tailtrail_run_id": "start-20261027091253-12fd05",
    "type": "tailtrail-workflow-completion-receipt",
    "workflow_id": "ttw-ce45b404e02d"
  }
}
```

---

*End of full Closure execution record.*
