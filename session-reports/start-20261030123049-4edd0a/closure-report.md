# TailTrail Closure Report - Full Execution Record

| Field | Value |
|---|---|
| Run ID | `start-20261030123049-4edd0a` |
| Generated after finalization | `2026-10-30T18:11:00.576398` |
| Overall status | `complete` |
| Closure record | `closure-2bbd8515e7c67875` |
| Finalizer | `finalizer-44fd784680906dd4` |

## Changes And Locations

| Path / location | Recorded status |
|---|---|
| `scripts/verbose-reporting.py` | recorded changed path |
| `tests/test_planning_revision.py` | recorded changed path |
| `tests/test_start_plan_presentation.py` | recorded changed path |

## Requirement Verification

```json
{
  "complete": 3,
  "requirements": [
    {
      "display_id": "REQ-01",
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-6da1ecb1b21f"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.json",
          "asserted_behavior": "Both human-readable plans list the input locator, its read-only role, access and status, and its recorded SHA-256 when present without adding it to editable scope.; The refactor changes internal structure without changing approved observable behaviour.; Each authoritative transition is observable in order through the customer/API surface.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
          "command_label": "bound planning-input normal and revision rendering proof",
          "duration_ms": 14679,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-30T12:39:40.755966+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-6da1ecb1b21f",
            "req-fb08049a6282"
          ],
          "scenario_ids": [
            "BHV-01",
            "BHV-02",
            "BHV-REQ-01"
          ],
          "started_at": "2026-10-30T12:39:26.075759+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stderr.txt",
          "stderr_sha256": "sha256:e0bdf20ecd9afabd8e377e1211fed3005d1e776eea1bb9bdc181f2bb3dca9541",
          "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
          "tier": "behaviour",
          "tiers": [
            "behaviour",
            "integration",
            "unit"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "implemented",
      "requirement_uid": "req-6da1ecb1b21f",
      "statement": "Render every bound planning input in both the initial Start Plan and every pending revision view",
      "status": "complete",
      "verification_status": "pass"
    },
    {
      "display_id": "REQ-02",
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-fb08049a6282"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.json",
          "asserted_behavior": "Both human-readable plans list the input locator, its read-only role, access and status, and its recorded SHA-256 when present without adding it to editable scope.; The refactor changes internal structure without changing approved observable behaviour.; Each authoritative transition is observable in order through the customer/API surface.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
          "command_label": "bound planning-input normal and revision rendering proof",
          "duration_ms": 14679,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-30T12:39:40.755966+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-6da1ecb1b21f",
            "req-fb08049a6282"
          ],
          "scenario_ids": [
            "BHV-01",
            "BHV-02",
            "BHV-REQ-01"
          ],
          "started_at": "2026-10-30T12:39:26.075759+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stderr.txt",
          "stderr_sha256": "sha256:e0bdf20ecd9afabd8e377e1211fed3005d1e776eea1bb9bdc181f2bb3dca9541",
          "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
          "tier": "behaviour",
          "tiers": [
            "behaviour",
            "integration",
            "unit"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "implemented",
      "requirement_uid": "req-fb08049a6282",
      "statement": "preserve each input's path, role, access, status, and recorded SHA-256 provenance",
      "status": "complete",
      "verification_status": "pass"
    },
    {
      "display_id": "REQ-03",
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-c52158c1818f"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.json",
          "asserted_behavior": "never promote a read-only input to editable scope or hide unavailable integrity",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
          "command_label": "bound planning-input scope-safety proof",
          "duration_ms": 14603,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-30T12:39:58.386927+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-c52158c1818f"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-30T12:39:43.782739+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.stderr.txt",
          "stderr_sha256": "sha256:75d316046923823cfafde2bddccbc79ee7000b1dff37ffd6fba0a26dad4b2f3d",
          "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
          "tier": "unit",
          "tiers": [
            "unit"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "implemented",
      "requirement_uid": "req-c52158c1818f",
      "statement": "never promote a read-only input to editable scope or hide unavailable integrity",
      "status": "complete",
      "verification_status": "pass"
    }
  ],
  "total": 3
}
```

## Execution Timeline And Evidence

| Kind | Command / action | Outcome | Exit code | Duration ms | Requirements | Tiers |
|---|---|---|---|---|---|---|
| command-result | `python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v` | pass | 0 | 14679 | ["req-6da1ecb1b21f", "req-fb08049a6282"] | ["unit", "behaviour", "integration"] |
| command-result | `python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v` | pass | 0 | 14603 | ["req-c52158c1818f"] | ["unit"] |

## Tests, Harnesses, Health, Drift, And Failures

```json
{
  "architecture": {
    "findings": [],
    "required": false,
    "status": "not-assessed"
  },
  "assessments": {
    "Behaviour Harness": {
      "artifact": null,
      "complete": true
    }
  },
  "behaviour": {
    "findings": [],
    "required": true,
    "status": "pass"
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
        "requirement_uid": "req-6da1ecb1b21f",
        "tier": "integration"
      },
      {
        "requirement_uid": "req-fb08049a6282",
        "tier": "integration"
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
      "behaviour",
      "integration",
      "unit"
    ],
    "receipt_refs": [
      ".tailtrail/runs/start-20261030123049-4edd0a/validation-receipts/closure-2bbd8515e7c67875-1.json",
      ".tailtrail/runs/start-20261030123049-4edd0a/validation-receipts/closure-2bbd8515e7c67875-2.json"
    ],
    "receipts": [
      {
        "artifact_path": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.json",
        "asserted_behavior": "Both human-readable plans list the input locator, its read-only role, access and status, and its recorded SHA-256 when present without adding it to editable scope.; The refactor changes internal structure without changing approved observable behaviour.; Each authoritative transition is observable in order through the customer/API surface.",
        "closure_record_id": "closure-2bbd8515e7c67875",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
        "command_label": "bound planning-input normal and revision rendering proof",
        "duration_ms": 14679,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-30T12:39:40.755966+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:601e431c01248189504fb7273de22af1c136be998fc13f11f7b6e2b0b789331a",
        "requirement_uids": [
          "req-6da1ecb1b21f",
          "req-fb08049a6282"
        ],
        "scenario_ids": [
          "BHV-01",
          "BHV-02",
          "BHV-REQ-01"
        ],
        "schema_version": "2",
        "started_at": "2026-10-30T12:39:26.075759+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stderr.txt",
        "stderr_sha256": "sha256:e0bdf20ecd9afabd8e377e1211fed3005d1e776eea1bb9bdc181f2bb3dca9541",
        "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stdout.txt",
        "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
        "tier": "behaviour",
        "tiers": [
          "behaviour",
          "integration",
          "unit"
        ],
        "type": "tailtrail-validation-evidence-receipt"
      },
      {
        "artifact_path": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.json",
        "asserted_behavior": "never promote a read-only input to editable scope or hide unavailable integrity",
        "closure_record_id": "closure-2bbd8515e7c67875",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
        "command_label": "bound planning-input scope-safety proof",
        "duration_ms": 14603,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-30T12:39:58.386927+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:601e431c01248189504fb7273de22af1c136be998fc13f11f7b6e2b0b789331a",
        "requirement_uids": [
          "req-c52158c1818f"
        ],
        "scenario_ids": [],
        "schema_version": "2",
        "started_at": "2026-10-30T12:39:43.782739+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.stderr.txt",
        "stderr_sha256": "sha256:75d316046923823cfafde2bddccbc79ee7000b1dff37ffd6fba0a26dad4b2f3d",
        "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.stdout.txt",
        "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
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
      "behaviour": "pass",
      "integration": "pass",
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
    "estimated_reduction_percent": 94.12,
    "estimated_saved_tokens": 67433,
    "forecast_confidence": "medium",
    "learning_evidence_references": [],
    "planned_working_set_tokens": 4214,
    "repository_ceiling_tokens": 2344251,
    "repository_file_count": 983,
    "saving_techniques": [
      "Code Graph slice reuse",
      "Navigator scope narrowing",
      "Focused validation selection"
    ],
    "scoped_file_ceiling_tokens": 71647,
    "scoped_tokens": 4214,
    "status": "estimated"
  },
  "planning_estimate_tokens": 4214,
  "status": "unavailable",
  "telemetry_records": 0
}
```
Measured values are shown only when linked host/provider telemetry exists. Estimates retain their saved provenance; missing measurements remain unavailable.

## Command Reference Registry

Single-source-of-truth reference for all proof commands.

| ID | Kind | Command |
|---|---|---|
| `cmd-39aabc` | proof | `python3 -m unittest tests.test_planning_revision tests.test_start_plan...` |
| `cmd-dcb44d` | proof | `python3 -m unittest discover -s tests -p test_start_plan_presentation....` |


## TailTrail Lifecycle And Audit Events

```json
[
  {
    "created_at": "2026-10-30T12:31:02+00:00",
    "event_id": "evt-0001-b9d46041bd2cd938",
    "event_type": "run_created",
    "payload": {
      "goal": "Render every bound planning input in both the initial Start Plan and every pending revision view, preserve each input's path, role, access, status, and recorded SHA-256 provenance, and never promote a read-only input to editable scope or hide unavailable integrity."
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 1,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:31:02+00:00",
    "event_id": "evt-0002-88157524cbb8574a",
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
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 2,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:31:02+00:00",
    "event_id": "evt-0003-a4c8a54220fc305a",
    "event_type": "target_resolution_recorded",
    "payload": {
      "policy_status": "not-configured",
      "target_resolution_receipt": ".tailtrail/runs/start-20261030123049-4edd0a/planning/target-resolution-receipt-v1.json"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 3,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:31:02+00:00",
    "event_id": "evt-0004-11df31ec76df6eff",
    "event_type": "start_report_saved",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/planning/start-report-v1.json"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 4,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:31:02+00:00",
    "event_id": "evt-0005-f4556bbdab7f5778",
    "event_type": "start_plan_verbose_generated",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/verbose-reports/start-plan-verbose-v1.md",
      "mandatory": true,
      "markdown_size": 9239,
      "status": "verified",
      "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261030123049-4edd0a/start-plan.md",
      "visible_artifact": "session-reports/start-20261030123049-4edd0a/start-plan.md"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 5,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:31:02+00:00",
    "event_id": "evt-0006-3d848df58e957d06",
    "event_type": "tailtrail_session_attached",
    "payload": {
      "context_key_hash": "sha256:8f7ea5b4e0bf204739b270db4b34f3ff3560126663ca15a47c97490c5a4c8b70",
      "fingerprint": "sha256:e5fef193538fdc5acc73106d509215977a297499cb91410eb0b1aec928dde74d",
      "generation": 293,
      "reason_code": "tailtrail-start"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 6,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:31:06+00:00",
    "event_id": "evt-0007-63208497cec30f27",
    "event_type": "planning_audit_completed",
    "payload": {
      "finding_count": 2,
      "revision_cycles": 0,
      "status": "gaps-found",
      "total_review_cycles": 1
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 7,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:31:30+00:00",
    "event_id": "evt-0008-62335314e1f405f1",
    "event_type": "planning_revision_proposed",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/revision-v2.json",
      "base_revision": 1,
      "requirement_uids": [
        "req-6da1ecb1b21f",
        "req-fb08049a6282",
        "req-c52158c1818f"
      ],
      "revision": 2
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 8,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:31:35+00:00",
    "event_id": "evt-0009-0bda88a6e575aec7",
    "event_type": "planning_audit_completed",
    "payload": {
      "finding_count": 1,
      "revision_cycles": 1,
      "status": "gaps-found",
      "total_review_cycles": 2
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 9,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:31:54+00:00",
    "event_id": "evt-0010-74c0a7bd9fcfba66",
    "event_type": "planning_revision_superseded",
    "payload": {
      "replacement_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/revision-v3.json",
      "revision": 2,
      "superseded_by": 3
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 10,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:31:54+00:00",
    "event_id": "evt-0011-38421930afbb3003",
    "event_type": "planning_revision_proposed",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/revision-v3.json",
      "base_revision": 1,
      "requirement_uids": [
        "req-6da1ecb1b21f",
        "req-fb08049a6282",
        "req-c52158c1818f",
        "req-6da1ecb1b21f"
      ],
      "revision": 3
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 11,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:32:00+00:00",
    "event_id": "evt-0012-bed1d553d2825f27",
    "event_type": "planning_audit_completed",
    "payload": {
      "finding_count": 0,
      "revision_cycles": 2,
      "status": "clean",
      "total_review_cycles": 3
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 12,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:35+00:00",
    "event_id": "evt-0013-02f71548f0a9d4b9",
    "event_type": "anchor_drafted",
    "payload": {
      "fingerprint": "sha256:47cab6513e22335f248b0027e84450c0937cea80fe2e2464d624c1a4afc8a85f",
      "proposal_version": 1,
      "requirements": [
        "req-6da1ecb1b21f",
        "req-fb08049a6282",
        "req-c52158c1818f"
      ]
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 13,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:35+00:00",
    "event_id": "evt-0014-4216ad7c1a31add7",
    "event_type": "anchor_approved",
    "payload": {
      "fingerprint": "sha256:40b10e59d0ac0d158ff1e2752dcd81e501597c2610fffcff258fa4c2b84bdfd5",
      "path": ".tailtrail/runs/start-20261030123049-4edd0a/anchors/approved-v1.json",
      "requirements": [
        "req-6da1ecb1b21f",
        "req-fb08049a6282",
        "req-c52158c1818f"
      ]
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 14,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:35+00:00",
    "event_id": "evt-0015-e0fe520ee2ebdf9c",
    "event_type": "planning_lock_approved",
    "payload": {
      "artifact": "planning/lock-v1.json",
      "audit": {
        "report_fingerprint": "sha256:af98059211464620fd8b965545a180e456c3b0f28cee3c6f1a6fbf91c5745bd5",
        "run_id": "start-20261030123049-4edd0a",
        "source": "active-start-report",
        "status": "clean"
      },
      "writes_allowed": true
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 15,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:36+00:00",
    "event_id": "evt-0016-b4c963a047bd3d1e",
    "event_type": "workflow_ownership_bound",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-0c4f1fcb0f39/ownership-v1.json",
      "requirement_uids": [
        "req-6da1ecb1b21f",
        "req-fb08049a6282",
        "req-c52158c1818f"
      ],
      "workflow_id": "ttw-0c4f1fcb0f39"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 16,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:37+00:00",
    "event_id": "evt-0017-3e8fc74180ae0fdd",
    "event_type": "workflow_capability_plan_declared",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-0c4f1fcb0f39/capability-plan-v1.json",
      "capability_ids": [
        "code-graph-mapper",
        "guardrails",
        "navigator",
        "review",
        "testing"
      ],
      "plan_fingerprint": "sha256:f9cea60b2e05113a98231b1d582bac94183fe66e5e5d5e2a5aba71dc743e1084",
      "workflow_id": "ttw-0c4f1fcb0f39"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 17,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:39+00:00",
    "event_id": "evt-0018-fdf12c185ca531a6",
    "event_type": "workflow_storage_initialized",
    "payload": {
      "journal": ".tailtrail/workflows/ttw-0c4f1fcb0f39/journal-v1.jsonl",
      "projection": ".tailtrail/workflows/ttw-0c4f1fcb0f39/projection-v1.json",
      "workflow_id": "ttw-0c4f1fcb0f39"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 18,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:39+00:00",
    "event_id": "evt-0019-b8115170524194e4",
    "event_type": "workflow_state_created",
    "payload": {
      "journal": ".tailtrail/workflows/ttw-0c4f1fcb0f39/journal-v1.jsonl",
      "sequence": 2,
      "workflow_id": "ttw-0c4f1fcb0f39"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 19,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:48+00:00",
    "event_id": "evt-0020-646c46800e7a24ab",
    "event_type": "workflow_compiler_plan_created",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-0c4f1fcb0f39/compiler-plan-v1.json",
      "plan_fingerprint": "sha256:a888c3f966768f520845bbcf3bda4a945f7542482b01fbe4c9735dfd8f52d88f",
      "revision": 1,
      "template_id": "small-change",
      "workflow_id": "ttw-0c4f1fcb0f39"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 20,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:48+00:00",
    "event_id": "evt-0021-9f4c092052ff8c26",
    "event_type": "workflow_stage_approval_recorded",
    "payload": {
      "action_classes": [
        "write_tailtrail_state"
      ],
      "approval_id": "wfauth-941ae9af34c0ebfc6929e8c0",
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
      "workflow_id": "ttw-0c4f1fcb0f39"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 21,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:48+00:00",
    "event_id": "evt-0022-cb401947135a9c17",
    "event_type": "workflow_stage_approval_recorded",
    "payload": {
      "action_classes": [
        "execute_project",
        "read_local",
        "write_project",
        "write_tailtrail_state"
      ],
      "approval_id": "wfauth-9b20bc048b7069a561ae5f4b",
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
      "workflow_id": "ttw-0c4f1fcb0f39"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 22,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:48+00:00",
    "event_id": "evt-0023-040294e9398e45e3",
    "event_type": "workflow_runtime_activated",
    "payload": {
      "binding": ".tailtrail/workflows/ttw-0c4f1fcb0f39/ownership-v1.json",
      "capability_plan": ".tailtrail/workflows/ttw-0c4f1fcb0f39/capability-plan-v1.json",
      "compiler_plan": ".tailtrail/workflows/ttw-0c4f1fcb0f39/compiler-plan-v1.json",
      "compiler_plan_fingerprint": "sha256:a888c3f966768f520845bbcf3bda4a945f7542482b01fbe4c9735dfd8f52d88f",
      "workflow_id": "ttw-0c4f1fcb0f39"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 23,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:48+00:00",
    "event_id": "evt-0024-ae2813f37b89bbea",
    "event_type": "planning_activated",
    "payload": {
      "activation_audit": {
        "report_fingerprint": "sha256:af98059211464620fd8b965545a180e456c3b0f28cee3c6f1a6fbf91c5745bd5",
        "run_id": "start-20261030123049-4edd0a",
        "source": "active-start-report",
        "status": "clean"
      },
      "anchor": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/anchors/approved-v1.json",
        "requirements": [
          "req-6da1ecb1b21f",
          "req-fb08049a6282",
          "req-c52158c1818f"
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
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 24,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:48+00:00",
    "event_id": "evt-0025-36de705e16f69fb0",
    "event_type": "start_plan_verbose_generated",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/verbose-reports/start-plan-verbose-v1.md",
      "mandatory": true,
      "markdown_size": 10447,
      "status": "verified",
      "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261030123049-4edd0a/start-plan.md",
      "visible_artifact": "session-reports/start-20261030123049-4edd0a/start-plan.md"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 25,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:33:48+00:00",
    "event_id": "evt-0026-6ff05e5f1298c0ba",
    "event_type": "planning_revision_approved",
    "payload": {
      "active_report": ".tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/start-report-v3.json",
      "anchor": ".tailtrail/runs/start-20261030123049-4edd0a/anchors/approved-v1.json",
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/revision-v3.json",
      "audit": {
        "report_fingerprint": "sha256:af98059211464620fd8b965545a180e456c3b0f28cee3c6f1a6fbf91c5745bd5",
        "run_id": "start-20261030123049-4edd0a",
        "source": "active-start-report",
        "status": "clean"
      },
      "revision": 3
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 26,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:39:42+00:00",
    "event_id": "evt-0027-1de869b286db6288",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/evidence-stream.jsonl",
      "fingerprint": "26fb969f9dab9d7e",
      "kind": "command-result",
      "sequence": 1
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 27,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:39:59+00:00",
    "event_id": "evt-0028-d3e4e1be13dba359",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/evidence-stream.jsonl",
      "fingerprint": "390506106172b0c2",
      "kind": "command-result",
      "sequence": 2
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 28,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:40:08+00:00",
    "event_id": "evt-0029-28907be5d1d25378",
    "event_type": "harness_checkpoint",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/checkpoints/checkpoint-1.json",
      "checkpoint": 1,
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-6da1ecb1b21f"
        },
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-fb08049a6282"
        },
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-c52158c1818f"
        }
      ],
      "requirement_states": {
        "req-6da1ecb1b21f": "validated",
        "req-c52158c1818f": "validated",
        "req-fb08049a6282": "validated"
      }
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 29,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:40:16+00:00",
    "event_id": "evt-0030-2be9dde6cadb7ed8",
    "event_type": "completion_review",
    "payload": {
      "artifact": "reviews/review-1.json",
      "checkpoint": 1,
      "complete": true,
      "findings": 0
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 30,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:40:16+00:00",
    "event_id": "evt-0031-6f12422bdc0ba4aa",
    "event_type": "completion_gate",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/completion-gates/gate-1.json",
      "complete": true,
      "findings": []
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 31,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:40:16+00:00",
    "event_id": "evt-0032-b86b7e21dfe37793",
    "event_type": "closure_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/closure-records/closure-2bbd8515e7c67875.json",
      "checkpoint": 1,
      "gate_complete": true,
      "receipt_count": 2,
      "record_id": "closure-2bbd8515e7c67875",
      "review_complete": true
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 32,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:40:25+00:00",
    "event_id": "evt-0033-65ecb3653900496b",
    "event_type": "behavior_assessed",
    "payload": {
      "artifact": "behavior/assessment-1.json",
      "complete": true,
      "findings": 0
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 33,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:40:25+00:00",
    "event_id": "evt-0034-7c67a8dfdaccf6a9",
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
          "status": "pass",
          "used": true
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
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 34,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-30T12:40:33+00:00",
    "event_id": "evt-0035-df9ab0ea3929591a",
    "event_type": "navigator_graph_lifecycle_recorded",
    "payload": {
      "action": "refresh",
      "cache_fingerprint": "sha256:f3a8e15a819845b0e386bc387bc06976a087d576010051c75dccc9bf2ce8f1b4",
      "mapping_fingerprint": "sha256:51c96306546ea1c85f626a8afa65d33026b26d07cc514aee7a7bcbcc0d4ba2ca",
      "phase": "closure"
    },
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "sequence": 35,
    "type": "tailtrail-run-event"
  }
]
```

## Complete Saved Closure Payload

```json
{
  "assessments": {
    "Behaviour Harness": {
      "artifact": null,
      "complete": true
    }
  },
  "boundary": "Finalized deterministic local control evidence only. No receipt command, deployment, recovery action, or external environment was executed.",
  "changed_paths": [
    "scripts/verbose-reporting.py",
    "tests/test_planning_revision.py",
    "tests/test_start_plan_presentation.py"
  ],
  "closure_record": {
    "boundary": "Recorded validated evidence. Managed-command receipts were executed and captured by TailTrail; declared host receipts remain explicitly unverified.",
    "changed_paths": [
      "scripts/verbose-reporting.py",
      "tests/test_planning_revision.py",
      "tests/test_start_plan_presentation.py"
    ],
    "checkpoint": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261030123049-4edd0a/checkpoints/checkpoint-1.json",
    "completion_gate": {
      "complete": true,
      "findings": [],
      "rule": "Only trusted managed-command or attested artifact-backed evidence can pass a tier; any reported non-pass blocks and authoritative failure dominates pass.",
      "run_artifact": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261030123049-4edd0a/completion-gates/gate-1.json",
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "2",
      "type": "tailtrail-requirement-completion-gate"
    },
    "completion_policy": {
      "boundary": "Policy derived from the persisted host contract. Missing or stale artifacts are never reported as complete.",
      "implementation_applicable": true,
      "missing": [],
      "recovery": "",
      "request_mode": "implementation",
      "required_artifacts": [
        "source-edit-receipt"
      ],
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "source_edit_required": true,
      "status": "pass",
      "type": "tailtrail-completion-policy"
    },
    "completion_review": {
      "checkpoint": 1,
      "complete": true,
      "findings": [],
      "next_action": "none",
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "type": "tailtrail-completion-review"
    },
    "next_action": "Run the selected harness assessments: Behaviour Harness; then run tailtrail completion-report.",
    "proof_amendment_artifact": null,
    "receipt_artifacts": [
      ".tailtrail/runs/start-20261030123049-4edd0a/validation-receipts/closure-2bbd8515e7c67875-1.json",
      ".tailtrail/runs/start-20261030123049-4edd0a/validation-receipts/closure-2bbd8515e7c67875-2.json"
    ],
    "record_id": "closure-2bbd8515e7c67875",
    "reused": true,
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "selected_harnesses": [
      "Canonical requirements",
      "Question Orchestrator",
      "Requirement Completion Harness",
      "Requirement-to-Impact Map",
      "Evidence-Aware Testing",
      "Test Precision Planner",
      "Behaviour Harness"
    ],
    "type": "tailtrail-closure-record",
    "validated_input": "execution/evidence-stream.jsonl"
  },
  "closure_record_id": "closure-2bbd8515e7c67875",
  "command_registry": {
    "cmd-39aabc": {
      "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
      "kind": "proof"
    },
    "cmd-dcb44d": {
      "command": "python3 -m unittest discover -s tests -p test_start_plan_presentation.py -v",
      "kind": "proof"
    }
  },
  "completion_report": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261030123049-4edd0a/completion-reports/report-1.json",
  "completion_report_payload": {
    "architecture": {
      "findings": [],
      "required": false,
      "status": "not-assessed"
    },
    "behaviour": {
      "findings": [],
      "required": true,
      "status": "pass"
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
          "fingerprint": "sha256:2ab42af86480f52cc04e963ade6e90497968b8d76dd6b65c7155b3a67654bbad",
          "path": "scripts/verbose-reporting.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:6c4ac9b9fba7155eb32ee6e177216c48be3d5f33732ce48cd5b1bbca728acf0b",
          "path": "tests/test_planning_revision.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:396c8fcf5e402a870a5d7e95f800d3036516f293e92c5d6b51cba964566f3cea",
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
          "action": "tailtrail execution-evidence record --root . --run-id start-20261030123049-4edd0a --event '{\"kind\":\"source-edit\",\"requirement_uids\":[\"req-6da1ecb1b21f\",\"req-c52158c1818f\",\"req-fb08049a6282\"],\"changed_paths\":[\"scripts/verbose-reporting.py\",\"tests/test_planning_revision.py\",\"tests/test_start_plan_presentation.py\"]}' --approved",
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
      "request_mode": "implementation",
      "required_artifacts": [
        "source-edit-receipt"
      ],
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "source_edit_required": true,
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
      "approval_id": "wfauth-9b20bc048b7069a561ae5f4b",
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
        "artifact": "behavior/assessment-1.json",
        "basis": "recorded approved-scenario assessment",
        "name": "Behaviour Harness",
        "status": "pass",
        "used": true
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
          "fingerprint": "sha256:2ab42af86480f52cc04e963ade6e90497968b8d76dd6b65c7155b3a67654bbad",
          "path": "scripts/verbose-reporting.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:6c4ac9b9fba7155eb32ee6e177216c48be3d5f33732ce48cd5b1bbca728acf0b",
          "path": "tests/test_planning_revision.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:396c8fcf5e402a870a5d7e95f800d3036516f293e92c5d6b51cba964566f3cea",
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
          "artifact": "planning/revisions/start-report-v3.json",
          "kind": "approved-plan-revision",
          "revision": 3
        }
      ],
      "base_plan": {
        "artifact": "planning/start-report-v1.json",
        "revision": 1
      },
      "boundary": "The base plan remains immutable; approved revisions and additive proof amendments are reported as separate effective-plan inputs.",
      "effective_plan": {
        "active_artifact": "planning/revisions/start-report-v3.json",
        "active_revision": 3,
        "base_is_immutable": true
      }
    },
    "plan_evidence": {
      "boundary": "Receipts stamped with a superseded plan fingerprint prove nothing about the approved plan; re-run them after re-approval. Fingerprint-less legacy receipts keep historical behavior.",
      "current": 2,
      "current_fingerprint": "sha256:601e431c01248189504fb7273de22af1c136be998fc13f11f7b6e2b0b789331a",
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
      "complete": 3,
      "requirements": [
        {
          "display_id": "REQ-01",
          "drift": [
            {
              "category": "evidence",
              "classification": "resolved",
              "requirement_uid": "req-6da1ecb1b21f"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.json",
              "asserted_behavior": "Both human-readable plans list the input locator, its read-only role, access and status, and its recorded SHA-256 when present without adding it to editable scope.; The refactor changes internal structure without changing approved observable behaviour.; Each authoritative transition is observable in order through the customer/API surface.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
              "command_label": "bound planning-input normal and revision rendering proof",
              "duration_ms": 14679,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-30T12:39:40.755966+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-6da1ecb1b21f",
                "req-fb08049a6282"
              ],
              "scenario_ids": [
                "BHV-01",
                "BHV-02",
                "BHV-REQ-01"
              ],
              "started_at": "2026-10-30T12:39:26.075759+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stderr.txt",
              "stderr_sha256": "sha256:e0bdf20ecd9afabd8e377e1211fed3005d1e776eea1bb9bdc181f2bb3dca9541",
              "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stdout.txt",
              "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
              "tier": "behaviour",
              "tiers": [
                "behaviour",
                "integration",
                "unit"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "implemented",
          "requirement_uid": "req-6da1ecb1b21f",
          "statement": "Render every bound planning input in both the initial Start Plan and every pending revision view",
          "status": "complete",
          "verification_status": "pass"
        },
        {
          "display_id": "REQ-02",
          "drift": [
            {
              "category": "evidence",
              "classification": "resolved",
              "requirement_uid": "req-fb08049a6282"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.json",
              "asserted_behavior": "Both human-readable plans list the input locator, its read-only role, access and status, and its recorded SHA-256 when present without adding it to editable scope.; The refactor changes internal structure without changing approved observable behaviour.; Each authoritative transition is observable in order through the customer/API surface.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
              "command_label": "bound planning-input normal and revision rendering proof",
              "duration_ms": 14679,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-30T12:39:40.755966+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-6da1ecb1b21f",
                "req-fb08049a6282"
              ],
              "scenario_ids": [
                "BHV-01",
                "BHV-02",
                "BHV-REQ-01"
              ],
              "started_at": "2026-10-30T12:39:26.075759+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stderr.txt",
              "stderr_sha256": "sha256:e0bdf20ecd9afabd8e377e1211fed3005d1e776eea1bb9bdc181f2bb3dca9541",
              "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stdout.txt",
              "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
              "tier": "behaviour",
              "tiers": [
                "behaviour",
                "integration",
                "unit"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "implemented",
          "requirement_uid": "req-fb08049a6282",
          "statement": "preserve each input's path, role, access, status, and recorded SHA-256 provenance",
          "status": "complete",
          "verification_status": "pass"
        },
        {
          "display_id": "REQ-03",
          "drift": [
            {
              "category": "evidence",
              "classification": "resolved",
              "requirement_uid": "req-c52158c1818f"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.json",
              "asserted_behavior": "never promote a read-only input to editable scope or hide unavailable integrity",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
              "command_label": "bound planning-input scope-safety proof",
              "duration_ms": 14603,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-30T12:39:58.386927+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-c52158c1818f"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-30T12:39:43.782739+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.stderr.txt",
              "stderr_sha256": "sha256:75d316046923823cfafde2bddccbc79ee7000b1dff37ffd6fba0a26dad4b2f3d",
              "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.stdout.txt",
              "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
              "tier": "unit",
              "tiers": [
                "unit"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "implemented",
          "requirement_uid": "req-c52158c1818f",
          "statement": "never promote a read-only input to editable scope or hide unavailable integrity",
          "status": "complete",
          "verification_status": "pass"
        }
      ],
      "total": 3
    },
    "run_artifact": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261030123049-4edd0a/completion-reports/report-1.json",
    "run_id": "start-20261030123049-4edd0a",
    "schema_version": "1",
    "session_reports": {
      "closure": {
        "absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261030123049-4edd0a/closure-report.md",
        "exists": false,
        "workspace_path": "session-reports/start-20261030123049-4edd0a/closure-report.md"
      },
      "start": {
        "absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261030123049-4edd0a/start-plan.md",
        "exists": true,
        "workspace_path": "session-reports/start-20261030123049-4edd0a/start-plan.md"
      }
    },
    "source_artifacts": {
      "active_plan": "planning/revisions/start-report-v3.json",
      "approved_anchor": "anchors/approved-v1.json",
      "architecture": null,
      "base_plan": "planning/start-report-v1.json",
      "behaviour": "behavior/assessment-1.json",
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
        "detail": "3 changed path(s); 0 saved blocker(s)",
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
        "detail": "3 saved changed path(s)",
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
        "status": "pass"
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
        "detail": "4214 focused tokens",
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
        "behaviour",
        "integration",
        "unit"
      ],
      "receipt_refs": [
        ".tailtrail/runs/start-20261030123049-4edd0a/validation-receipts/closure-2bbd8515e7c67875-1.json",
        ".tailtrail/runs/start-20261030123049-4edd0a/validation-receipts/closure-2bbd8515e7c67875-2.json"
      ],
      "receipts": [
        {
          "artifact_path": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.json",
          "asserted_behavior": "Both human-readable plans list the input locator, its read-only role, access and status, and its recorded SHA-256 when present without adding it to editable scope.; The refactor changes internal structure without changing approved observable behaviour.; Each authoritative transition is observable in order through the customer/API surface.",
          "closure_record_id": "closure-2bbd8515e7c67875",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
          "command_label": "bound planning-input normal and revision rendering proof",
          "duration_ms": 14679,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-30T12:39:40.755966+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:601e431c01248189504fb7273de22af1c136be998fc13f11f7b6e2b0b789331a",
          "requirement_uids": [
            "req-6da1ecb1b21f",
            "req-fb08049a6282"
          ],
          "scenario_ids": [
            "BHV-01",
            "BHV-02",
            "BHV-REQ-01"
          ],
          "schema_version": "2",
          "started_at": "2026-10-30T12:39:26.075759+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stderr.txt",
          "stderr_sha256": "sha256:e0bdf20ecd9afabd8e377e1211fed3005d1e776eea1bb9bdc181f2bb3dca9541",
          "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
          "tier": "behaviour",
          "tiers": [
            "behaviour",
            "integration",
            "unit"
          ],
          "type": "tailtrail-validation-evidence-receipt"
        },
        {
          "artifact_path": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.json",
          "asserted_behavior": "never promote a read-only input to editable scope or hide unavailable integrity",
          "closure_record_id": "closure-2bbd8515e7c67875",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
          "command_label": "bound planning-input scope-safety proof",
          "duration_ms": 14603,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-30T12:39:58.386927+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:601e431c01248189504fb7273de22af1c136be998fc13f11f7b6e2b0b789331a",
          "requirement_uids": [
            "req-c52158c1818f"
          ],
          "scenario_ids": [],
          "schema_version": "2",
          "started_at": "2026-10-30T12:39:43.782739+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.stderr.txt",
          "stderr_sha256": "sha256:75d316046923823cfafde2bddccbc79ee7000b1dff37ffd6fba0a26dad4b2f3d",
          "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
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
        "behaviour": "pass",
        "integration": "pass",
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
        "estimated_reduction_percent": 94.12,
        "estimated_saved_tokens": 67433,
        "forecast_confidence": "medium",
        "learning_evidence_references": [],
        "planned_working_set_tokens": 4214,
        "repository_ceiling_tokens": 2344251,
        "repository_file_count": 983,
        "saving_techniques": [
          "Code Graph slice reuse",
          "Navigator scope narrowing",
          "Focused validation selection"
        ],
        "scoped_file_ceiling_tokens": 71647,
        "scoped_tokens": 4214,
        "status": "estimated"
      },
      "planning_estimate_tokens": 4214,
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
  "delivery_record": ".tailtrail/runs/start-20261030123049-4edd0a/delivery-record.md",
  "execution_events": [
    {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.json",
      "asserted_behavior": "Both human-readable plans list the input locator, its read-only role, access and status, and its recorded SHA-256 when present without adding it to editable scope.; The refactor changes internal structure without changing approved observable behaviour.; Each authoritative transition is observable in order through the customer/API surface.",
      "changed_paths": [
        "scripts/verbose-reporting.py",
        "tests/test_planning_revision.py",
        "tests/test_start_plan_presentation.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
      "command_label": "bound planning-input normal and revision rendering proof",
      "duration_ms": 14679,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "26fb969f9dab9d7e",
      "finished_at": "2026-10-30T12:39:40.755966+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:601e431c01248189504fb7273de22af1c136be998fc13f11f7b6e2b0b789331a",
      "requirement_uids": [
        "req-6da1ecb1b21f",
        "req-fb08049a6282"
      ],
      "run_id": "start-20261030123049-4edd0a",
      "scenario_assertion_fingerprint": "sha256:23ab3ce03ab2e9c8617ffb52cdddab437aabff57fb6df69f42882bed265f098c",
      "scenario_ids": [
        "BHV-01",
        "BHV-02",
        "BHV-REQ-01"
      ],
      "schema_version": "2",
      "sequence": 1,
      "started_at": "2026-10-30T12:39:26.075759+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stderr.txt",
      "stderr_sha256": "sha256:e0bdf20ecd9afabd8e377e1211fed3005d1e776eea1bb9bdc181f2bb3dca9541",
      "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-d1530b8796acc3cc.stdout.txt",
      "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
      "tier": "unit",
      "tiers": [
        "unit",
        "behaviour",
        "integration"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.json",
      "asserted_behavior": "never promote a read-only input to editable scope or hide unavailable integrity",
      "changed_paths": [
        "scripts/verbose-reporting.py",
        "tests/test_planning_revision.py",
        "tests/test_start_plan_presentation.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v",
      "command_label": "bound planning-input scope-safety proof",
      "duration_ms": 14603,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "390506106172b0c2",
      "finished_at": "2026-10-30T12:39:58.386927+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:601e431c01248189504fb7273de22af1c136be998fc13f11f7b6e2b0b789331a",
      "requirement_uids": [
        "req-c52158c1818f"
      ],
      "run_id": "start-20261030123049-4edd0a",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 2,
      "started_at": "2026-10-30T12:39:43.782739+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.stderr.txt",
      "stderr_sha256": "sha256:75d316046923823cfafde2bddccbc79ee7000b1dff37ffd6fba0a26dad4b2f3d",
      "stdout_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/command-artifacts/command-325820c212ff7ac9.stdout.txt",
      "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
      "tier": "unit",
      "tiers": [
        "unit"
      ],
      "type": "tailtrail-execution-evidence"
    }
  ],
  "finalizer_id": "finalizer-44fd784680906dd4",
  "graph_lifecycle": {
    "action": "refresh",
    "after_status": {
      "reasons": [
        "Cached graph scope and watched file hashes still match."
      ],
      "scope": [
        "schemas/host-input-contract.schema.json",
        "scripts/planning-aidlc-question.py",
        "tests/test_start_entrypoints.py",
        "tests/test_architecture_fitness.py",
        "scripts/mcp-server.py",
        "scripts/debug-host-diagnosis.py",
        "scripts/aidlc-init.py",
        "scripts/behaviour_planning.py",
        "scripts/architecture-fitness.py",
        "tests/test_navigator_scope.py",
        "scripts/architecture_planning.py",
        "tests/test_completion_report.py",
        "tests/test_start_plan_presentation.py",
        "scripts/aidlc-official-install.py",
        "scripts/completion-review.py",
        "tests/test_code_graph_cache.py",
        "tests/test_task_type_contract.py",
        "tests/test_debug_start_planning.py",
        "scripts/navigator-scope.py",
        "scripts/official-aidlc-state.py",
        "scripts/workflow_runtime/start_integration.py",
        "scripts/tailtrail.py",
        "scripts/aidlc-official-detect.py",
        "tests/test_workflow_ci_continuation.py",
        "tests/test_repository_path_policy.py",
        "scripts/run-ledger.py",
        "tests/test_workflow_ownership.py",
        "scripts/evidence-tiers.py",
        "tests/test_revision_proof_overlay.py",
        "tests/test_visual_requirement.py",
        "scripts/closure-recorder.py",
        "scripts/official-aidlc-requirements.py",
        "scripts/change-intent-anchor.py",
        "scripts/pipeline_orchestrator.py",
        "tests/test_sequential_pipeline.py",
        "tests/test_target_workspace.py",
        "scripts/intake_pipeline.py",
        "scripts/learning-use-receipt.py",
        "scripts/debug-harness-convergence.py",
        "scripts/check-tailtrail.py",
        "tests/test_navigator_graph_lifecycle.py",
        "scripts/task-start.py",
        "scripts/install-local.py",
        "scripts/completion-report.py",
        "scripts/planning-audit.py",
        "scripts/aidlc-official-bridge.py",
        "tests/test_host_adapter_conformance.py",
        "tests/test_mcp_server.py",
        "tests/test_planning_lock.py",
        "tests/test_workflow_phase7.py",
        "scripts/repository_path_policy.py",
        "tests/test_full_pipeline.py",
        "tests/test_host_question_flow_event_schema.py",
        "scripts/requirement_intake.py",
        "scripts/execution-evidence.py",
        "tests/test_delivery_record.py",
        "scripts/benchmark-tailtrail.py",
        "scripts/advanced-runtime.py",
        "tests/test_planning_audit.py",
        "tests/test_closure_recorder.py",
        "tests/test_write_guardian.py",
        "tests/test_host_input_contract_schema.py",
        "tests/test_navigator_installed_release.py",
        "pyproject.toml",
        "scripts/workflow-dashboard.py",
        "scripts/host-adapter-conformance.py",
        "tests/test_workflow_privacy.py",
        "scripts/greenfield_e2e_fixture.py",
        "scripts/workflow_runtime/enterprise_transport.py",
        "tests/test_task_recovery.py",
        "scripts/new_file_due_diligence.py",
        "scripts/workflow_runtime/storage.py",
        "scripts/closure-close.py",
        "tests/test_greenfield_e2e.py",
        "scripts/closure-contract.py",
        "release-manifest.json",
        "scripts/official-aidlc-checkpoint.py",
        "scripts/host_contract.py",
        "tests/test_task_type_gate.py",
        "scripts/docs-only.py",
        "scripts/aidlc-requirements.py",
        "tests/test_workflow_adapters.py",
        "tests/test_debug_harness.py",
        "scripts/delivery-record.py",
        "schemas/host-question-flow-event.schema.json",
        "scripts/requirement_discovery.py",
        "tests/test_canonical_statement_contract.py",
        "scripts/planning-revision.py",
        "scripts/review-graph.py",
        "tests/test_demo_prompt_book.py",
        "scripts/navigator_discovery.py",
        "scripts/verbose-reporting.py",
        "scripts/harness-checkpoint.py",
        "tests/test_evaluation_audit.py",
        "hooks/hooks.json",
        "tests/test_install_profiles.py",
        "scripts/adoption-validation.py",
        "scripts/debug-completion.py",
        "tests/test_workflow_dashboard.py",
        "scripts/learning-agent.py",
        "tests/test_public_route_gate.py",
        "scripts/host-decision.py",
        "tests/test_workflow_template_execution.py",
        "tests/test_review_graph.py",
        "scripts/navigator-scope-release.py",
        "scripts/aidlc-check.py",
        "scripts/code-graph-mapper.py",
        "scripts/debug-correction.py",
        "tests/test_workflow_documentation.py",
        "scripts/planning-discussion.py",
        "tests/test_requirement_discovery.py",
        "tests/test_intake_pipeline.py",
        "tests/test_completion_review.py",
        "tests/test_new_file_due_diligence.py",
        "scripts/navigator_scope.py",
        "tests/test_enterprise_host_adapters.py",
        "scripts/aidlc-official-host.py",
        "scripts/code_graph_cache.py",
        "scripts/learning-refresh.py",
        "scripts/update-copilot.py",
        "scripts/closure-finalizer.py",
        "scripts/closure-correction.py",
        "tests/test_aidlc_official_host.py",
        "tests/test_tailtrail_registry.py",
        "scripts/write_guardian.py",
        "scripts/question-orchestrator.py",
        "scripts/ast-map.py",
        "scripts/planning_lock.py",
        "tests/test_closure_finalizer.py",
        "tests/test_review_scope.py",
        "tests/test_question_orchestrator.py",
        "tests/test_workflow_contracts.py",
        "buildweek-demo-project/src/claims_api/validation.py",
        "tests/test_host_contract.py",
        "scripts/debug-preflight.py",
        "tests/test_planning_revision.py",
        "tests/test_navigator_core.py",
        "tests/test_requirement_routing_phase0.py",
        "scripts/install-copilot.py",
        "scripts/closure-learning.py",
        "tests/test_workflow_approvals.py",
        "tests/test_debug_host_integration.py",
        "tests/test_code_graph_inventory.py",
        "scripts/navigator.py",
        "tests/test_host_question_flow_phase0_artifacts.py",
        "tests/test_aidlc_official_bridge.py",
        "tests/test_execution_evidence.py",
        "tests/test_host_packet_tickets.py",
        "scripts/host-reply-validate.py",
        "demo-project-layout/tailtrail-demo-workspace/services/claims-api/tests/test_validation.py",
        "scripts/closure-evaluation.py",
        "scripts/meta-harness-analyze.py",
        "tests/test_workflow_start_integration.py",
        "scripts/requirement-completion.py"
      ],
      "status": "fresh"
    },
    "attempt_id": "start-20261030123049-4edd0a",
    "before_status": {
      "reasons": [
        "Relevant repository file inventory changed after the graph was created."
      ],
      "scope": [
        "schemas/host-input-contract.schema.json",
        "scripts/planning-aidlc-question.py",
        "tests/test_start_entrypoints.py",
        "tests/test_architecture_fitness.py",
        "scripts/mcp-server.py",
        "scripts/debug-host-diagnosis.py",
        "scripts/aidlc-init.py",
        "scripts/behaviour_planning.py",
        "scripts/architecture-fitness.py",
        "tests/test_navigator_scope.py",
        "scripts/architecture_planning.py",
        "tests/test_completion_report.py",
        "tests/test_start_plan_presentation.py",
        "scripts/aidlc-official-install.py",
        "scripts/completion-review.py",
        "tests/test_code_graph_cache.py",
        "tests/test_task_type_contract.py",
        "tests/test_debug_start_planning.py",
        "scripts/navigator-scope.py",
        "scripts/official-aidlc-state.py",
        "scripts/workflow_runtime/start_integration.py",
        "scripts/tailtrail.py",
        "scripts/aidlc-official-detect.py",
        "tests/test_workflow_ci_continuation.py",
        "tests/test_repository_path_policy.py",
        "scripts/run-ledger.py",
        "tests/test_workflow_ownership.py",
        "scripts/evidence-tiers.py",
        "tests/test_revision_proof_overlay.py",
        "tests/test_visual_requirement.py",
        "scripts/closure-recorder.py",
        "scripts/official-aidlc-requirements.py",
        "scripts/change-intent-anchor.py",
        "scripts/pipeline_orchestrator.py",
        "tests/test_sequential_pipeline.py",
        "tests/test_target_workspace.py",
        "scripts/intake_pipeline.py",
        "scripts/learning-use-receipt.py",
        "scripts/debug-harness-convergence.py",
        "scripts/check-tailtrail.py",
        "tests/test_navigator_graph_lifecycle.py",
        "scripts/task-start.py",
        "scripts/install-local.py",
        "scripts/completion-report.py",
        "scripts/planning-audit.py",
        "scripts/aidlc-official-bridge.py",
        "tests/test_host_adapter_conformance.py",
        "tests/test_mcp_server.py",
        "tests/test_planning_lock.py",
        "tests/test_workflow_phase7.py",
        "scripts/repository_path_policy.py",
        "tests/test_full_pipeline.py",
        "tests/test_host_question_flow_event_schema.py",
        "scripts/requirement_intake.py",
        "scripts/execution-evidence.py",
        "tests/test_delivery_record.py",
        "scripts/benchmark-tailtrail.py",
        "scripts/advanced-runtime.py",
        "tests/test_planning_audit.py",
        "tests/test_closure_recorder.py",
        "tests/test_write_guardian.py",
        "tests/test_host_input_contract_schema.py",
        "tests/test_navigator_installed_release.py",
        "pyproject.toml",
        "scripts/workflow-dashboard.py",
        "scripts/host-adapter-conformance.py",
        "tests/test_workflow_privacy.py",
        "scripts/greenfield_e2e_fixture.py",
        "scripts/workflow_runtime/enterprise_transport.py",
        "tests/test_task_recovery.py",
        "scripts/new_file_due_diligence.py",
        "scripts/workflow_runtime/storage.py",
        "scripts/closure-close.py",
        "tests/test_greenfield_e2e.py",
        "scripts/closure-contract.py",
        "release-manifest.json",
        "scripts/official-aidlc-checkpoint.py",
        "scripts/host_contract.py",
        "tests/test_task_type_gate.py",
        "scripts/docs-only.py",
        "scripts/aidlc-requirements.py",
        "tests/test_workflow_adapters.py",
        "tests/test_debug_harness.py",
        "scripts/delivery-record.py",
        "schemas/host-question-flow-event.schema.json",
        "scripts/requirement_discovery.py",
        "tests/test_canonical_statement_contract.py",
        "scripts/planning-revision.py",
        "scripts/review-graph.py",
        "tests/test_demo_prompt_book.py",
        "scripts/navigator_discovery.py",
        "scripts/verbose-reporting.py",
        "scripts/harness-checkpoint.py",
        "tests/test_evaluation_audit.py",
        "hooks/hooks.json",
        "tests/test_install_profiles.py",
        "scripts/adoption-validation.py",
        "scripts/debug-completion.py",
        "tests/test_workflow_dashboard.py",
        "scripts/learning-agent.py",
        "tests/test_public_route_gate.py",
        "scripts/host-decision.py",
        "tests/test_workflow_template_execution.py",
        "tests/test_review_graph.py",
        "scripts/navigator-scope-release.py",
        "scripts/aidlc-check.py",
        "scripts/code-graph-mapper.py",
        "scripts/debug-correction.py",
        "tests/test_workflow_documentation.py",
        "scripts/planning-discussion.py",
        "tests/test_requirement_discovery.py",
        "tests/test_intake_pipeline.py",
        "tests/test_completion_review.py",
        "tests/test_new_file_due_diligence.py",
        "scripts/navigator_scope.py",
        "tests/test_enterprise_host_adapters.py",
        "scripts/aidlc-official-host.py",
        "scripts/code_graph_cache.py",
        "scripts/learning-refresh.py",
        "scripts/update-copilot.py",
        "scripts/closure-finalizer.py",
        "scripts/closure-correction.py",
        "tests/test_aidlc_official_host.py",
        "tests/test_tailtrail_registry.py",
        "scripts/write_guardian.py",
        "scripts/question-orchestrator.py",
        "scripts/ast-map.py",
        "scripts/planning_lock.py",
        "tests/test_closure_finalizer.py",
        "tests/test_review_scope.py",
        "tests/test_question_orchestrator.py",
        "tests/test_workflow_contracts.py",
        "buildweek-demo-project/src/claims_api/validation.py",
        "tests/test_host_contract.py",
        "scripts/debug-preflight.py",
        "tests/test_planning_revision.py",
        "tests/test_navigator_core.py",
        "tests/test_requirement_routing_phase0.py",
        "scripts/install-copilot.py",
        "scripts/closure-learning.py",
        "tests/test_workflow_approvals.py",
        "tests/test_debug_host_integration.py",
        "tests/test_code_graph_inventory.py",
        "scripts/navigator.py",
        "tests/test_host_question_flow_phase0_artifacts.py",
        "tests/test_aidlc_official_bridge.py",
        "tests/test_execution_evidence.py",
        "tests/test_host_packet_tickets.py",
        "scripts/host-reply-validate.py",
        "demo-project-layout/tailtrail-demo-workspace/services/claims-api/tests/test_validation.py",
        "scripts/closure-evaluation.py",
        "scripts/meta-harness-analyze.py",
        "tests/test_workflow_start_integration.py",
        "scripts/requirement-completion.py"
      ],
      "status": "stale"
    },
    "boundary": "Navigator may create or refresh TailTrail graph metadata; current-source scope evidence and Planning Lock approval remain mandatory.",
    "cache_fingerprint": "sha256:f3a8e15a819845b0e386bc387bc06976a087d576010051c75dccc9bf2ce8f1b4",
    "cache_path": "tailtrail-meta/code-graph-cache.json",
    "cache_reuse_state": null,
    "cache_shape": "mapper",
    "cache_warnings": [
      "legacy v1 mapper shape; migrates to a v2 container on next Phase-1 write"
    ],
    "fingerprint": "sha256:6c8d6a9ff8dae393661b8822a7e7284abc64824530d51f00eb2c925acabc3a86",
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
      "scripts/verbose-reporting.py",
      "tests/test_planning_revision.py",
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
        "requirement_uid": "req-6da1ecb1b21f",
        "tier": "integration"
      },
      {
        "requirement_uid": "req-fb08049a6282",
        "tier": "integration"
      }
    ],
    "status": "pass"
  },
  "ledger_events": [
    {
      "created_at": "2026-10-30T12:31:02+00:00",
      "event_id": "evt-0001-b9d46041bd2cd938",
      "event_type": "run_created",
      "payload": {
        "goal": "Render every bound planning input in both the initial Start Plan and every pending revision view, preserve each input's path, role, access, status, and recorded SHA-256 provenance, and never promote a read-only input to editable scope or hide unavailable integrity."
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 1,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:31:02+00:00",
      "event_id": "evt-0002-88157524cbb8574a",
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
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 2,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:31:02+00:00",
      "event_id": "evt-0003-a4c8a54220fc305a",
      "event_type": "target_resolution_recorded",
      "payload": {
        "policy_status": "not-configured",
        "target_resolution_receipt": ".tailtrail/runs/start-20261030123049-4edd0a/planning/target-resolution-receipt-v1.json"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 3,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:31:02+00:00",
      "event_id": "evt-0004-11df31ec76df6eff",
      "event_type": "start_report_saved",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/planning/start-report-v1.json"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 4,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:31:02+00:00",
      "event_id": "evt-0005-f4556bbdab7f5778",
      "event_type": "start_plan_verbose_generated",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/verbose-reports/start-plan-verbose-v1.md",
        "mandatory": true,
        "markdown_size": 9239,
        "status": "verified",
        "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261030123049-4edd0a/start-plan.md",
        "visible_artifact": "session-reports/start-20261030123049-4edd0a/start-plan.md"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 5,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:31:02+00:00",
      "event_id": "evt-0006-3d848df58e957d06",
      "event_type": "tailtrail_session_attached",
      "payload": {
        "context_key_hash": "sha256:8f7ea5b4e0bf204739b270db4b34f3ff3560126663ca15a47c97490c5a4c8b70",
        "fingerprint": "sha256:e5fef193538fdc5acc73106d509215977a297499cb91410eb0b1aec928dde74d",
        "generation": 293,
        "reason_code": "tailtrail-start"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 6,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:31:06+00:00",
      "event_id": "evt-0007-63208497cec30f27",
      "event_type": "planning_audit_completed",
      "payload": {
        "finding_count": 2,
        "revision_cycles": 0,
        "status": "gaps-found",
        "total_review_cycles": 1
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 7,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:31:30+00:00",
      "event_id": "evt-0008-62335314e1f405f1",
      "event_type": "planning_revision_proposed",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/revision-v2.json",
        "base_revision": 1,
        "requirement_uids": [
          "req-6da1ecb1b21f",
          "req-fb08049a6282",
          "req-c52158c1818f"
        ],
        "revision": 2
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 8,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:31:35+00:00",
      "event_id": "evt-0009-0bda88a6e575aec7",
      "event_type": "planning_audit_completed",
      "payload": {
        "finding_count": 1,
        "revision_cycles": 1,
        "status": "gaps-found",
        "total_review_cycles": 2
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 9,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:31:54+00:00",
      "event_id": "evt-0010-74c0a7bd9fcfba66",
      "event_type": "planning_revision_superseded",
      "payload": {
        "replacement_artifact": ".tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/revision-v3.json",
        "revision": 2,
        "superseded_by": 3
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 10,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:31:54+00:00",
      "event_id": "evt-0011-38421930afbb3003",
      "event_type": "planning_revision_proposed",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/revision-v3.json",
        "base_revision": 1,
        "requirement_uids": [
          "req-6da1ecb1b21f",
          "req-fb08049a6282",
          "req-c52158c1818f",
          "req-6da1ecb1b21f"
        ],
        "revision": 3
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 11,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:32:00+00:00",
      "event_id": "evt-0012-bed1d553d2825f27",
      "event_type": "planning_audit_completed",
      "payload": {
        "finding_count": 0,
        "revision_cycles": 2,
        "status": "clean",
        "total_review_cycles": 3
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 12,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:35+00:00",
      "event_id": "evt-0013-02f71548f0a9d4b9",
      "event_type": "anchor_drafted",
      "payload": {
        "fingerprint": "sha256:47cab6513e22335f248b0027e84450c0937cea80fe2e2464d624c1a4afc8a85f",
        "proposal_version": 1,
        "requirements": [
          "req-6da1ecb1b21f",
          "req-fb08049a6282",
          "req-c52158c1818f"
        ]
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 13,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:35+00:00",
      "event_id": "evt-0014-4216ad7c1a31add7",
      "event_type": "anchor_approved",
      "payload": {
        "fingerprint": "sha256:40b10e59d0ac0d158ff1e2752dcd81e501597c2610fffcff258fa4c2b84bdfd5",
        "path": ".tailtrail/runs/start-20261030123049-4edd0a/anchors/approved-v1.json",
        "requirements": [
          "req-6da1ecb1b21f",
          "req-fb08049a6282",
          "req-c52158c1818f"
        ]
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 14,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:35+00:00",
      "event_id": "evt-0015-e0fe520ee2ebdf9c",
      "event_type": "planning_lock_approved",
      "payload": {
        "artifact": "planning/lock-v1.json",
        "audit": {
          "report_fingerprint": "sha256:af98059211464620fd8b965545a180e456c3b0f28cee3c6f1a6fbf91c5745bd5",
          "run_id": "start-20261030123049-4edd0a",
          "source": "active-start-report",
          "status": "clean"
        },
        "writes_allowed": true
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 15,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:36+00:00",
      "event_id": "evt-0016-b4c963a047bd3d1e",
      "event_type": "workflow_ownership_bound",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-0c4f1fcb0f39/ownership-v1.json",
        "requirement_uids": [
          "req-6da1ecb1b21f",
          "req-fb08049a6282",
          "req-c52158c1818f"
        ],
        "workflow_id": "ttw-0c4f1fcb0f39"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 16,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:37+00:00",
      "event_id": "evt-0017-3e8fc74180ae0fdd",
      "event_type": "workflow_capability_plan_declared",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-0c4f1fcb0f39/capability-plan-v1.json",
        "capability_ids": [
          "code-graph-mapper",
          "guardrails",
          "navigator",
          "review",
          "testing"
        ],
        "plan_fingerprint": "sha256:f9cea60b2e05113a98231b1d582bac94183fe66e5e5d5e2a5aba71dc743e1084",
        "workflow_id": "ttw-0c4f1fcb0f39"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 17,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:39+00:00",
      "event_id": "evt-0018-fdf12c185ca531a6",
      "event_type": "workflow_storage_initialized",
      "payload": {
        "journal": ".tailtrail/workflows/ttw-0c4f1fcb0f39/journal-v1.jsonl",
        "projection": ".tailtrail/workflows/ttw-0c4f1fcb0f39/projection-v1.json",
        "workflow_id": "ttw-0c4f1fcb0f39"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 18,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:39+00:00",
      "event_id": "evt-0019-b8115170524194e4",
      "event_type": "workflow_state_created",
      "payload": {
        "journal": ".tailtrail/workflows/ttw-0c4f1fcb0f39/journal-v1.jsonl",
        "sequence": 2,
        "workflow_id": "ttw-0c4f1fcb0f39"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 19,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:48+00:00",
      "event_id": "evt-0020-646c46800e7a24ab",
      "event_type": "workflow_compiler_plan_created",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-0c4f1fcb0f39/compiler-plan-v1.json",
        "plan_fingerprint": "sha256:a888c3f966768f520845bbcf3bda4a945f7542482b01fbe4c9735dfd8f52d88f",
        "revision": 1,
        "template_id": "small-change",
        "workflow_id": "ttw-0c4f1fcb0f39"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 20,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:48+00:00",
      "event_id": "evt-0021-9f4c092052ff8c26",
      "event_type": "workflow_stage_approval_recorded",
      "payload": {
        "action_classes": [
          "write_tailtrail_state"
        ],
        "approval_id": "wfauth-941ae9af34c0ebfc6929e8c0",
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
        "workflow_id": "ttw-0c4f1fcb0f39"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 21,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:48+00:00",
      "event_id": "evt-0022-cb401947135a9c17",
      "event_type": "workflow_stage_approval_recorded",
      "payload": {
        "action_classes": [
          "execute_project",
          "read_local",
          "write_project",
          "write_tailtrail_state"
        ],
        "approval_id": "wfauth-9b20bc048b7069a561ae5f4b",
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
        "workflow_id": "ttw-0c4f1fcb0f39"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 22,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:48+00:00",
      "event_id": "evt-0023-040294e9398e45e3",
      "event_type": "workflow_runtime_activated",
      "payload": {
        "binding": ".tailtrail/workflows/ttw-0c4f1fcb0f39/ownership-v1.json",
        "capability_plan": ".tailtrail/workflows/ttw-0c4f1fcb0f39/capability-plan-v1.json",
        "compiler_plan": ".tailtrail/workflows/ttw-0c4f1fcb0f39/compiler-plan-v1.json",
        "compiler_plan_fingerprint": "sha256:a888c3f966768f520845bbcf3bda4a945f7542482b01fbe4c9735dfd8f52d88f",
        "workflow_id": "ttw-0c4f1fcb0f39"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 23,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:48+00:00",
      "event_id": "evt-0024-ae2813f37b89bbea",
      "event_type": "planning_activated",
      "payload": {
        "activation_audit": {
          "report_fingerprint": "sha256:af98059211464620fd8b965545a180e456c3b0f28cee3c6f1a6fbf91c5745bd5",
          "run_id": "start-20261030123049-4edd0a",
          "source": "active-start-report",
          "status": "clean"
        },
        "anchor": {
          "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/anchors/approved-v1.json",
          "requirements": [
            "req-6da1ecb1b21f",
            "req-fb08049a6282",
            "req-c52158c1818f"
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
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 24,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:48+00:00",
      "event_id": "evt-0025-36de705e16f69fb0",
      "event_type": "start_plan_verbose_generated",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/verbose-reports/start-plan-verbose-v1.md",
        "mandatory": true,
        "markdown_size": 10447,
        "status": "verified",
        "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261030123049-4edd0a/start-plan.md",
        "visible_artifact": "session-reports/start-20261030123049-4edd0a/start-plan.md"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 25,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:33:48+00:00",
      "event_id": "evt-0026-6ff05e5f1298c0ba",
      "event_type": "planning_revision_approved",
      "payload": {
        "active_report": ".tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/start-report-v3.json",
        "anchor": ".tailtrail/runs/start-20261030123049-4edd0a/anchors/approved-v1.json",
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/revision-v3.json",
        "audit": {
          "report_fingerprint": "sha256:af98059211464620fd8b965545a180e456c3b0f28cee3c6f1a6fbf91c5745bd5",
          "run_id": "start-20261030123049-4edd0a",
          "source": "active-start-report",
          "status": "clean"
        },
        "revision": 3
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 26,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:39:42+00:00",
      "event_id": "evt-0027-1de869b286db6288",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/evidence-stream.jsonl",
        "fingerprint": "26fb969f9dab9d7e",
        "kind": "command-result",
        "sequence": 1
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 27,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:39:59+00:00",
      "event_id": "evt-0028-d3e4e1be13dba359",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/execution/evidence-stream.jsonl",
        "fingerprint": "390506106172b0c2",
        "kind": "command-result",
        "sequence": 2
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 28,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:40:08+00:00",
      "event_id": "evt-0029-28907be5d1d25378",
      "event_type": "harness_checkpoint",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/checkpoints/checkpoint-1.json",
        "checkpoint": 1,
        "drift": [
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-6da1ecb1b21f"
          },
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-fb08049a6282"
          },
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-c52158c1818f"
          }
        ],
        "requirement_states": {
          "req-6da1ecb1b21f": "validated",
          "req-c52158c1818f": "validated",
          "req-fb08049a6282": "validated"
        }
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 29,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:40:16+00:00",
      "event_id": "evt-0030-2be9dde6cadb7ed8",
      "event_type": "completion_review",
      "payload": {
        "artifact": "reviews/review-1.json",
        "checkpoint": 1,
        "complete": true,
        "findings": 0
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 30,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:40:16+00:00",
      "event_id": "evt-0031-6f12422bdc0ba4aa",
      "event_type": "completion_gate",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/completion-gates/gate-1.json",
        "complete": true,
        "findings": []
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 31,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:40:16+00:00",
      "event_id": "evt-0032-b86b7e21dfe37793",
      "event_type": "closure_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/closure-records/closure-2bbd8515e7c67875.json",
        "checkpoint": 1,
        "gate_complete": true,
        "receipt_count": 2,
        "record_id": "closure-2bbd8515e7c67875",
        "review_complete": true
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 32,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:40:25+00:00",
      "event_id": "evt-0033-65ecb3653900496b",
      "event_type": "behavior_assessed",
      "payload": {
        "artifact": "behavior/assessment-1.json",
        "complete": true,
        "findings": 0
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 33,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:40:25+00:00",
      "event_id": "evt-0034-7c67a8dfdaccf6a9",
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
            "status": "pass",
            "used": true
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
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 34,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-30T12:40:33+00:00",
      "event_id": "evt-0035-df9ab0ea3929591a",
      "event_type": "navigator_graph_lifecycle_recorded",
      "payload": {
        "action": "refresh",
        "cache_fingerprint": "sha256:f3a8e15a819845b0e386bc387bc06976a087d576010051c75dccc9bf2ce8f1b4",
        "mapping_fingerprint": "sha256:51c96306546ea1c85f626a8afa65d33026b26d07cc514aee7a7bcbcc0d4ba2ca",
        "phase": "closure"
      },
      "run_id": "start-20261030123049-4edd0a",
      "schema_version": "1",
      "sequence": 35,
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
  "run_id": "start-20261030123049-4edd0a",
  "run_mapping": {
    "closure_status": "complete",
    "goal_fingerprint": "sha256:14a4d09cad1f813b921d6312ad87b6be2e88ed1f5fe68892d9eaeb4adcd7c88e",
    "graph_cache_fingerprint": "sha256:f3a8e15a819845b0e386bc387bc06976a087d576010051c75dccc9bf2ce8f1b4",
    "mapping_fingerprint": "sha256:51c96306546ea1c85f626a8afa65d33026b26d07cc514aee7a7bcbcc0d4ba2ca",
    "path_hashes": {
      "scripts/closure-finalizer.py": "sha256:fb1f68154f9e4d6d740050714a135bdaa9b7969578222dbdf209ba57a42fa8bf",
      "scripts/planning_lock.py": "sha256:f0364ec83f2910228f8f6d444507aa9924ec46a9aae0c2e42cc67ea49f729799",
      "scripts/verbose-reporting.py": "sha256:2ab42af86480f52cc04e963ade6e90497968b8d76dd6b65c7155b3a67654bbad",
      "tests/test_planning_revision.py": "sha256:6c4ac9b9fba7155eb32ee6e177216c48be3d5f33732ce48cd5b1bbca728acf0b",
      "tests/test_start_plan_presentation.py": "sha256:396c8fcf5e402a870a5d7e95f800d3036516f293e92c5d6b51cba964566f3cea"
    },
    "query_terms": [
      "access",
      "and",
      "both",
      "bound",
      "each",
      "editable",
      "every",
      "hide",
      "initial",
      "input",
      "integrity",
      "never",
      "path",
      "pending",
      "plan",
      "planning",
      "preserve",
      "promote",
      "provenance",
      "read-only",
      "recorded",
      "render",
      "revision",
      "role",
      "scope",
      "sha-256",
      "start",
      "status",
      "the",
      "unavailable",
      "view"
    ],
    "recorded_at": "2026-10-30T12:40:33.818995+00:00",
    "run_id": "start-20261030123049-4edd0a",
    "scope_decision_fingerprint": "sha256:207b1f622345f17f2c0a1844b4576474664ec013f572dda8c77f00ff8027b56e"
  },
  "schema_version": "1",
  "selected_harnesses": [
    "Canonical requirements",
    "Question Orchestrator",
    "Requirement Completion Harness",
    "Requirement-to-Impact Map",
    "Evidence-Aware Testing",
    "Test Precision Planner",
    "Behaviour Harness"
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
    "artifact": ".tailtrail/runs/start-20261030123049-4edd0a/verbose-reports/closure-verbose-v1.md",
    "mandatory": true,
    "markdown_size": 117918,
    "run_id": "start-20261030123049-4edd0a",
    "status": "generated",
    "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261030123049-4edd0a/closure-report.md",
    "visible_artifact": "session-reports/start-20261030123049-4edd0a/closure-report.md"
  },
  "workflow_closure": {
    "artifact": ".tailtrail/workflows/ttw-0c4f1fcb0f39/completion-receipt-v1.json",
    "boundary": "Completion follows the canonical TailTrail Completion Report. An evidence-incomplete receipt is not a successful workflow completion and does not authorize a retry or recovery.",
    "completion_report": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261030123049-4edd0a/completion-reports/report-1.json",
    "completion_status": "complete",
    "evidence_fingerprint": "sha256:3dbd1383f26be50e0d9c87528cf0d33c68e4ac3d1cf1727dbaa41480fdb80958",
    "receipt_fingerprint": "sha256:65bae1e52dec8117edda458c972ea98017f42e470c9f6794f637d6605a95f788",
    "schema_version": "1",
    "state": "completed",
    "tailtrail_run_id": "start-20261030123049-4edd0a",
    "type": "tailtrail-workflow-completion-receipt",
    "workflow_id": "ttw-0c4f1fcb0f39"
  }
}
```

---

*End of full Closure execution record.*
