# TailTrail Closure Report - Full Execution Record

| Field | Value |
|---|---|
| Run ID | `start-20261019102950-bc8789` |
| Generated after finalization | `2026-10-19T16:57:25.544171` |
| Overall status | `complete` |
| Closure record | `closure-717b25644d324265` |
| Finalizer | `finalizer-102fc6b780b8510e` |

## Changes And Locations

| Path / location | Recorded status |
|---|---|
| `scripts/closure-finalizer.py` | recorded changed path |
| `scripts/completion-report.py` | recorded changed path |
| `scripts/planning-audit.py` | recorded changed path |
| `scripts/planning-revision.py` | recorded changed path |
| `scripts/planning_lock.py` | recorded changed path |
| `scripts/verbose-reporting.py` | recorded changed path |
| `tests/test_closure_finalizer.py` | recorded changed path |
| `tests/test_completion_report.py` | recorded changed path |
| `tests/test_planning_audit.py` | recorded changed path |
| `tests/test_planning_lock.py` | recorded changed path |
| `tests/test_planning_revision.py` | recorded changed path |

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
          "classification": "unchanged",
          "requirement_uid": "req-725005193320"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.json",
          "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest discover -s tests -p test_planning_revision.py -v",
          "command_label": "visible report generation and canonical preservation",
          "duration_ms": 11995,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-19T11:26:07.325970+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-6f5a5f850524",
            "req-725005193320"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-19T11:25:55.329752+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stderr.txt",
          "stderr_sha256": "sha256:69f5e69d1d3e1f9e46a4df6bb9cbb1227224eef4a06f39ad035e826012021b3f",
          "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
          "tier": "unit",
          "tiers": [
            "unit"
          ]
        },
        {
          "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.json",
          "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
          "command_label": "planning, audit, and completion report regressions",
          "duration_ms": 13764,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-19T11:18:48.551394+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-6f5a5f850524",
            "req-725005193320",
            "req-92b0573b5b3e"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-19T11:18:34.786610+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stderr.txt",
          "stderr_sha256": "sha256:483b839ba7645daa9f6187408edc54e4027bd6888611d901e0d8695174b89398",
          "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "contract",
          "tiers": [
            "contract",
            "integration",
            "unit"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "implemented",
      "requirement_uid": "req-725005193320",
      "statement": "Generate visible full verbose session reports without fabricated metrics.",
      "status": "complete",
      "verification_status": "pass"
    },
    {
      "display_id": "REQ-02",
      "drift": [
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-ad541812658a"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.json",
          "asserted_behavior": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.; The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
          "command_label": "full Start and Closure lifecycle reports",
          "duration_ms": 23395,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-19T11:25:52.373076+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-92b0573b5b3e",
            "req-ad541812658a"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-19T11:25:28.976827+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stderr.txt",
          "stderr_sha256": "sha256:84f3805263b3d88605ecfd8140ac16688a1e85a40624386377e3ede7141ac9a7",
          "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
          "tier": "behaviour",
          "tiers": [
            "behaviour",
            "contract",
            "integration",
            "unit"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "implemented",
      "requirement_uid": "req-ad541812658a",
      "statement": "The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
      "status": "complete",
      "verification_status": "pass"
    },
    {
      "display_id": "REQ-03",
      "drift": [
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-92b0573b5b3e"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.json",
          "asserted_behavior": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.; The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
          "command_label": "full Start and Closure lifecycle reports",
          "duration_ms": 23395,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-19T11:25:52.373076+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-92b0573b5b3e",
            "req-ad541812658a"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-19T11:25:28.976827+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stderr.txt",
          "stderr_sha256": "sha256:84f3805263b3d88605ecfd8140ac16688a1e85a40624386377e3ede7141ac9a7",
          "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
          "tier": "behaviour",
          "tiers": [
            "behaviour",
            "contract",
            "integration",
            "unit"
          ]
        },
        {
          "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.json",
          "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
          "command_label": "planning, audit, and completion report regressions",
          "duration_ms": 13764,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-19T11:18:48.551394+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-6f5a5f850524",
            "req-725005193320",
            "req-92b0573b5b3e"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-19T11:18:34.786610+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stderr.txt",
          "stderr_sha256": "sha256:483b839ba7645daa9f6187408edc54e4027bd6888611d901e0d8695174b89398",
          "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "contract",
          "tiers": [
            "contract",
            "integration",
            "unit"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "implemented",
      "requirement_uid": "req-92b0573b5b3e",
      "statement": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
      "status": "complete",
      "verification_status": "pass"
    },
    {
      "display_id": "REQ-04",
      "drift": [
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-6f5a5f850524"
        }
      ],
      "evidence": [
        {
          "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.json",
          "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest discover -s tests -p test_planning_revision.py -v",
          "command_label": "visible report generation and canonical preservation",
          "duration_ms": 11995,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-19T11:26:07.325970+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-6f5a5f850524",
            "req-725005193320"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-19T11:25:55.329752+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stderr.txt",
          "stderr_sha256": "sha256:69f5e69d1d3e1f9e46a4df6bb9cbb1227224eef4a06f39ad035e826012021b3f",
          "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
          "tier": "unit",
          "tiers": [
            "unit"
          ]
        },
        {
          "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.json",
          "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
          "command_label": "planning, audit, and completion report regressions",
          "duration_ms": 13764,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-19T11:18:48.551394+00:00",
          "outcome": "pass",
          "requirement_uids": [
            "req-6f5a5f850524",
            "req-725005193320",
            "req-92b0573b5b3e"
          ],
          "scenario_ids": [],
          "started_at": "2026-10-19T11:18:34.786610+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stderr.txt",
          "stderr_sha256": "sha256:483b839ba7645daa9f6187408edc54e4027bd6888611d901e0d8695174b89398",
          "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "contract",
          "tiers": [
            "contract",
            "integration",
            "unit"
          ]
        }
      ],
      "findings": [],
      "implementation_status": "implemented",
      "requirement_uid": "req-6f5a5f850524",
      "statement": "Preserve canonical internal copies.",
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
| command-result | `python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v` | pass | 0 | 24769 | ["req-92b0573b5b3e", "req-ad541812658a"] | ["unit", "contract", "behaviour", "integration"] |
| command-result | `python3 -m unittest discover -s tests -p test_planning_revision.py -v` | pass | 0 | 12494 | ["req-6f5a5f850524", "req-725005193320"] | ["unit"] |
| command-result | `python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v` | fail | 1 | 13728 | ["req-6f5a5f850524", "req-725005193320", "req-92b0573b5b3e"] | ["unit", "contract", "integration"] |
| command-result | `python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v` | pass | 0 | 13492 | ["req-6f5a5f850524", "req-725005193320", "req-92b0573b5b3e"] | ["unit", "contract", "integration"] |
| command-result | `python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v` | pass | 0 | 13764 | ["req-6f5a5f850524", "req-725005193320", "req-92b0573b5b3e"] | ["unit", "contract", "integration"] |
| command-result | `python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v` | pass | 0 | 24092 | ["req-92b0573b5b3e", "req-ad541812658a"] | ["unit", "contract", "behaviour", "integration"] |
| source-edit | `unavailable` | unavailable | unavailable | unavailable | ["req-6f5a5f850524", "req-725005193320", "req-92b0573b5b3e", "req-ad541812658a"] | unavailable |
| command-result | `python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v` | pass | 0 | 23395 | ["req-92b0573b5b3e", "req-ad541812658a"] | ["unit", "contract", "behaviour", "integration"] |
| command-result | `python3 -m unittest discover -s tests -p test_planning_revision.py -v` | pass | 0 | 11995 | ["req-6f5a5f850524", "req-725005193320"] | ["unit"] |

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
        "requirement_uid": "req-ad541812658a",
        "tier": "contract"
      },
      {
        "requirement_uid": "req-ad541812658a",
        "tier": "integration"
      },
      {
        "requirement_uid": "req-92b0573b5b3e",
        "tier": "contract"
      },
      {
        "requirement_uid": "req-92b0573b5b3e",
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
      "contract",
      "integration",
      "unit"
    ],
    "receipt_refs": [
      ".tailtrail/runs/start-20261019102950-bc8789/validation-receipts/closure-717b25644d324265-1.json",
      ".tailtrail/runs/start-20261019102950-bc8789/validation-receipts/closure-717b25644d324265-2.json",
      ".tailtrail/runs/start-20261019102950-bc8789/validation-receipts/closure-717b25644d324265-3.json"
    ],
    "receipts": [
      {
        "artifact_path": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.json",
        "asserted_behavior": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.; The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
        "closure_record_id": "closure-717b25644d324265",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
        "command_label": "full Start and Closure lifecycle reports",
        "duration_ms": 23395,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-19T11:25:52.373076+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
        "proof_amendment_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/proof-amendments.jsonl",
        "requirement_uids": [
          "req-92b0573b5b3e",
          "req-ad541812658a"
        ],
        "scenario_ids": [],
        "schema_version": "2",
        "started_at": "2026-10-19T11:25:28.976827+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stderr.txt",
        "stderr_sha256": "sha256:84f3805263b3d88605ecfd8140ac16688a1e85a40624386377e3ede7141ac9a7",
        "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stdout.txt",
        "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
        "tier": "behaviour",
        "tiers": [
          "behaviour",
          "contract",
          "integration",
          "unit"
        ],
        "type": "tailtrail-validation-evidence-receipt"
      },
      {
        "artifact_path": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.json",
        "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.",
        "closure_record_id": "closure-717b25644d324265",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest discover -s tests -p test_planning_revision.py -v",
        "command_label": "visible report generation and canonical preservation",
        "duration_ms": 11995,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-19T11:26:07.325970+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
        "proof_amendment_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/proof-amendments.jsonl",
        "requirement_uids": [
          "req-6f5a5f850524",
          "req-725005193320"
        ],
        "scenario_ids": [],
        "schema_version": "2",
        "started_at": "2026-10-19T11:25:55.329752+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stderr.txt",
        "stderr_sha256": "sha256:69f5e69d1d3e1f9e46a4df6bb9cbb1227224eef4a06f39ad035e826012021b3f",
        "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stdout.txt",
        "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
        "tier": "unit",
        "tiers": [
          "unit"
        ],
        "type": "tailtrail-validation-evidence-receipt"
      },
      {
        "artifact_path": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.json",
        "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
        "closure_record_id": "closure-717b25644d324265",
        "collector": "tailtrail-managed-execution-v2",
        "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
        "command_label": "planning, audit, and completion report regressions",
        "duration_ms": 13764,
        "environment": "Darwin arm64 Python 3.12.6",
        "evidence_label": "managed-command",
        "evidence_quality": "trusted",
        "exit_code": 0,
        "finished_at": "2026-10-19T11:18:48.551394+00:00",
        "outcome": "pass",
        "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
        "proof_amendment_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/proof-amendments.jsonl",
        "requirement_uids": [
          "req-6f5a5f850524",
          "req-725005193320",
          "req-92b0573b5b3e"
        ],
        "scenario_ids": [],
        "schema_version": "2",
        "started_at": "2026-10-19T11:18:34.786610+00:00",
        "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stderr.txt",
        "stderr_sha256": "sha256:483b839ba7645daa9f6187408edc54e4027bd6888611d901e0d8695174b89398",
        "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stdout.txt",
        "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "tier": "contract",
        "tiers": [
          "contract",
          "integration",
          "unit"
        ],
        "type": "tailtrail-validation-evidence-receipt"
      }
    ],
    "required_checks": [
      {
        "candidate_paths": [
          "tests/test_planning_revision.py",
          "tests/test_closure_finalizer.py"
        ],
        "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
        "requirement_uids": [
          "req-ad541812658a",
          "req-92b0573b5b3e"
        ],
        "tiers": [
          "unit",
          "contract",
          "behaviour",
          "integration"
        ]
      }
    ],
    "status": "pass",
    "tier_results": {
      "behaviour": "pass",
      "contract": "pass",
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
    "estimated_reduction_percent": 94.29,
    "estimated_saved_tokens": 55662,
    "forecast_confidence": "medium",
    "learning_evidence_references": [],
    "planned_working_set_tokens": 3373,
    "repository_ceiling_tokens": 2313613,
    "repository_file_count": 980,
    "saving_techniques": [
      "Code Graph slice reuse",
      "Navigator scope narrowing",
      "Focused validation selection"
    ],
    "scoped_file_ceiling_tokens": 59035,
    "scoped_tokens": 3373,
    "status": "estimated"
  },
  "planning_estimate_tokens": 3373,
  "status": "unavailable",
  "telemetry_records": 0
}
```
Measured values are shown only when linked host/provider telemetry exists. Estimates retain their saved provenance; missing measurements remain unavailable.

## Command Reference Registry

Single-source-of-truth reference for all proof commands.

| ID | Kind | Command |
|---|---|---|
| `cmd-71ba4b` | proof | `python3 -m unittest discover -s tests -p test_planning_revision.py -v` |


## TailTrail Lifecycle And Audit Events

```json
[
  {
    "created_at": "2026-10-19T10:30:03+00:00",
    "event_id": "evt-0001-48758a803458296f",
    "event_type": "run_created",
    "payload": {
      "goal": "Generate visible full verbose session reports without fabricated metrics: the start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance; the closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers; preserve canonical internal copies."
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 1,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:30:03+00:00",
    "event_id": "evt-0002-0501e3a83b8d0785",
    "event_type": "planning_lock_created",
    "payload": {
      "artifact": "planning/lock-v1.json",
      "input_roles": {
        "read_only_inputs": 0
      },
      "reference_roots": [],
      "target_fingerprint": "sha256:0db1e1abf14c7efedec8229d88190380f977e2a75fd5e74d53df5292a2f2a06c",
      "writes_allowed": false
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 2,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:30:03+00:00",
    "event_id": "evt-0003-74f672e3ce167b58",
    "event_type": "target_resolution_recorded",
    "payload": {
      "policy_status": "not-configured",
      "target_resolution_receipt": ".tailtrail/runs/start-20261019102950-bc8789/planning/target-resolution-receipt-v1.json"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 3,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:30:03+00:00",
    "event_id": "evt-0004-268ec2714f991d63",
    "event_type": "start_report_saved",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/start-report-v1.json"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 4,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:30:03+00:00",
    "event_id": "evt-0005-a9e1f9636e66041d",
    "event_type": "tailtrail_session_attached",
    "payload": {
      "context_key_hash": "sha256:8f7ea5b4e0bf204739b270db4b34f3ff3560126663ca15a47c97490c5a4c8b70",
      "fingerprint": "sha256:2ea96280b391162e9b4daf1cc88c6be3e9d4f2da97c322b7eb25bc4940e4f568",
      "generation": 244,
      "reason_code": "tailtrail-start"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 5,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:31:17+00:00",
    "event_id": "evt-0006-270ec1aaf6d59153",
    "event_type": "planning_revision_proposed",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/revisions/revision-v2.json",
      "base_revision": 1,
      "requirement_uids": [
        "req-ad541812658a"
      ],
      "revision": 2
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 6,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:31:35+00:00",
    "event_id": "evt-0007-0282c28adfd368ff",
    "event_type": "planning_revision_superseded",
    "payload": {
      "replacement_artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/revisions/revision-v3.json",
      "revision": 2,
      "superseded_by": 3
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 7,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:31:35+00:00",
    "event_id": "evt-0008-c0088ddef2dc7469",
    "event_type": "planning_revision_proposed",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/revisions/revision-v3.json",
      "base_revision": 1,
      "requirement_uids": [
        "req-ad541812658a",
        "req-ad541812658a"
      ],
      "revision": 3
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 8,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:36:23+00:00",
    "event_id": "evt-0009-e832f85ac12f00f0",
    "event_type": "anchor_drafted",
    "payload": {
      "fingerprint": "sha256:6827a3bd6ce8f5e9a39d85a470cb2d8d57e19facecc015481b927adc62289628",
      "proposal_version": 1,
      "requirements": [
        "req-725005193320",
        "req-ad541812658a",
        "req-92b0573b5b3e",
        "req-6f5a5f850524"
      ]
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 9,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:36:23+00:00",
    "event_id": "evt-0010-ea4ec7a0fcdc3fdf",
    "event_type": "proposal_rejected",
    "payload": {
      "feedback": [
        {
          "comment": "Do not create a reconstructed summary. Generate the visible file from the actual complete verbose Start Plan at planning time, before implementation, regardless of the selected display verbosity.",
          "decision": "reject",
          "requirement_uid": "req-725005193320"
        },
        {
          "comment": "The actual Start Plan document must contain every saved planning detail: complete requirements, questions and answers, AIDLC stages and decisions when used, scope roles and evidence, controls, proof, risks, token provenance, open questions, and approval state.",
          "decision": "reject",
          "requirement_uid": "req-ad541812658a"
        },
        {
          "comment": "Do not create any closure document before closure is finalized. After real finalization, generate it from factual execution data including exact changes and locations, commands, outcomes, durations, evidence, harnesses, drift, token usage, failures, corrections, and unavailable markers.",
          "decision": "reject",
          "requirement_uid": "req-92b0573b5b3e"
        },
        {
          "comment": "Preserve canonical internal evidence, but the visible Start and Closure files must be lifecycle-authentic projections of that evidence rather than parallel summaries.",
          "decision": "reject",
          "requirement_uid": "req-6f5a5f850524"
        }
      ],
      "next_requirement_mode": "ask-targeted-questions-or-offer-aidlc",
      "proposal_version": 1,
      "rejected_requirement_uids": [
        "req-725005193320",
        "req-ad541812658a",
        "req-92b0573b5b3e",
        "req-6f5a5f850524"
      ]
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 10,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:36:23+00:00",
    "event_id": "evt-0011-e7460b52054211b6",
    "event_type": "host_decision_recorded",
    "payload": {
      "artifact": "decisions/decisions-v1.jsonl",
      "decision": "feedback-recorded",
      "decision_id": "sha256:1efce0b73af5076df9b21ba7031a37c4f7be0b9e195ae679ad1e5597bffe65a6",
      "verb": "revise"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 11,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:36:42+00:00",
    "event_id": "evt-0012-b9efbaff4d3d2d70",
    "event_type": "proposal_rejected",
    "payload": {
      "feedback": [
        {
          "comment": "User rejected reconstructed summaries and requires lifecycle-authentic full verbose Start and post-finalization Closure documents.",
          "decision": "reject",
          "requirement_uid": "req-725005193320"
        },
        {
          "comment": "User rejected reconstructed summaries and requires lifecycle-authentic full verbose Start and post-finalization Closure documents.",
          "decision": "reject",
          "requirement_uid": "req-ad541812658a"
        },
        {
          "comment": "User rejected reconstructed summaries and requires lifecycle-authentic full verbose Start and post-finalization Closure documents.",
          "decision": "reject",
          "requirement_uid": "req-92b0573b5b3e"
        },
        {
          "comment": "User rejected reconstructed summaries and requires lifecycle-authentic full verbose Start and post-finalization Closure documents.",
          "decision": "reject",
          "requirement_uid": "req-6f5a5f850524"
        }
      ],
      "next_requirement_mode": "aidlc-requirements-required",
      "proposal_version": 1,
      "rejected_requirement_uids": [
        "req-725005193320",
        "req-ad541812658a",
        "req-92b0573b5b3e",
        "req-6f5a5f850524"
      ]
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 12,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:36:42+00:00",
    "event_id": "evt-0013-10f91996e4300589",
    "event_type": "host_decision_recorded",
    "payload": {
      "artifact": "decisions/decisions-v1.jsonl",
      "decision": "feedback-recorded",
      "decision_id": "sha256:478ca019db64dcc5550d8963fc278d08d2b70c176d96ac21cb5b8cb22fa3de4b",
      "verb": "revise"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 13,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:44:39+00:00",
    "event_id": "evt-0014-e5e670979374d531",
    "event_type": "proposal_rejected",
    "payload": {
      "feedback": [
        {
          "comment": "AUTHORITATIVE FULL REQUIREMENT: Generate the visible Start Plan from the actual saved pre-approval plan, always in full verbose mode regardless of selected display verbosity. It must be the real plan artifact, never a later reconstruction or summary.",
          "decision": "reject",
          "requirement_uid": "req-725005193320"
        },
        {
          "comment": "AUTHORITATIVE START CONTENT: Include every saved planning detail: complete requirement statements and verification criteria, interpretation provenance, all AIDLC stages/questions/options/recommendations/answers/decisions when AIDLC is used, scope owners/inspection/proof/excluded roles and evidence, architecture and behavior contracts, selected and conditional TailTrail controls, proof commands and tiers, risks, dependencies, assumptions, open questions, approval history/state, plan revisions/audits, token estimates and provenance, and visible absolute/workspace-relative report path.",
          "decision": "reject",
          "requirement_uid": "req-ad541812658a"
        },
        {
          "comment": "AUTHORITATIVE CLOSURE TIMING AND CONTENT: Do not create any Closure Report until execution and real closure finalization are complete. Then include every factual execution detail: exact changes and where they occurred, files/symbols/locations, commands, outputs/outcomes/exit codes/durations, receipts/evidence, requirement-by-requirement verification and what was done, failures and corrections, tests and harness results, TailTrail controls/lifecycle/events, scope drift, architecture/behavior/maintainability/security health checks, token usage by phase when measured, estimates with provenance when not measured, unavailable markers, blockers, residual risks, overall status, final health summary, and visible absolute/workspace-relative report path. Never fabricate counts, coverage, tokens, pass states, or deployment readiness.",
          "decision": "reject",
          "requirement_uid": "req-92b0573b5b3e"
        },
        {
          "comment": "AUTHORITATIVE PRESERVATION: Preserve canonical internal TailTrail artifacts and evidence. Visible Start and Closure documents must be complete lifecycle-authentic projections from those records, redact secrets/private reasoning, and label unavailable facts rather than inventing them.",
          "decision": "reject",
          "requirement_uid": "req-6f5a5f850524"
        }
      ],
      "next_requirement_mode": "aidlc-requirements-required",
      "proposal_version": 1,
      "rejected_requirement_uids": [
        "req-725005193320",
        "req-ad541812658a",
        "req-92b0573b5b3e",
        "req-6f5a5f850524"
      ]
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 14,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:44:39+00:00",
    "event_id": "evt-0015-7805099864301c45",
    "event_type": "host_decision_recorded",
    "payload": {
      "artifact": "decisions/decisions-v1.jsonl",
      "decision": "feedback-recorded",
      "decision_id": "sha256:73b8316e745f0b3a788cc6f0f5b09c46aee6c1bde5ba10679012a3d313172cf4",
      "verb": "revise"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 15,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:47:09+00:00",
    "event_id": "evt-0016-47b0439c6da83870",
    "event_type": "planning_revision_superseded",
    "payload": {
      "reason": "AIDLC Requirements mode required after repeated requirement rejection",
      "replacement_artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/revisions/revision-v4.json",
      "revision": 3,
      "superseded_by": 4
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 16,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:47:09+00:00",
    "event_id": "evt-0017-c2810a77ed5714f7",
    "event_type": "planning_aidlc_mode_switch_proposed",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/revisions/revision-v4.json",
      "from_mode": "lite",
      "revision": 4,
      "to_mode": "standard"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 17,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:49:54+00:00",
    "event_id": "evt-0018-e495bb0e530f9d9c",
    "event_type": "planning_aidlc_mode_switch_fell_back",
    "payload": {
      "from_mode": "lite",
      "reason": "Official AIDLC Standard is unavailable because no compatible pinned pack is installed. TailTrail Lite remains available; no local AIDLC questionnaire will be presented as official.",
      "requested_mode": "standard",
      "revision": 4
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 18,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:51:32+00:00",
    "event_id": "evt-0019-61f0b4e98a30e777",
    "event_type": "question_context_prepared",
    "payload": {
      "aidlc_mode": "lite",
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/question-context-v1.json",
      "known_fact_count": 7,
      "question_authority": "local-lite",
      "unknown_count": 3
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 19,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:51:32+00:00",
    "event_id": "evt-0020-9a4f7e621b742a60",
    "event_type": "aidlc_requirements_requested",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-requirements-v1.json",
      "reason": "user-selected-aidlc-requirements",
      "rejection_number": 4,
      "revision_context_count": 0
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 20,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:55:53+00:00",
    "event_id": "evt-0021-ef6dd5acae662516",
    "event_type": "aidlc_correction_projection_blocked",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-observations-v1.json",
      "material_question_ids": [
        "Q3",
        "Q4"
      ],
      "reason_code": "validated-correction-projection-required",
      "state_artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-state.json",
      "version": 1
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 21,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:56:51+00:00",
    "event_id": "evt-0022-24cf0441b7520ad4",
    "event_type": "aidlc_requirements_answered",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-revised-requirements-v1.json",
      "changed_surfaces": [
        "requirements",
        "validation"
      ],
      "projection": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-projection-v1.json",
      "projection_version": 1,
      "question_ids": [
        "Q1",
        "Q2",
        "Q3",
        "Q4"
      ],
      "revision_version": 1,
      "state_artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-state.json",
      "status": "revision-ready"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 22,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T10:59:16+00:00",
    "event_id": "evt-0023-ffbc61868b9c193c",
    "event_type": "aidlc_requirements_answered",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-revised-requirements-v2.json",
      "changed_surfaces": [
        "requirements",
        "validation"
      ],
      "projection": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-projection-v2.json",
      "projection_version": 2,
      "question_ids": [
        "Q1",
        "Q2",
        "Q3",
        "Q4"
      ],
      "revision_version": 2,
      "state_artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-state.json",
      "status": "revision-ready"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 23,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:01:33+00:00",
    "event_id": "evt-0024-3e257b8cd66ad32c",
    "event_type": "anchor_drafted",
    "payload": {
      "fingerprint": "sha256:67edc1a807a90fa2a669ec3af5836cd699f845486d5a6cf94bef4f5b472abc10",
      "proposal_version": 2,
      "requirements": [
        "req-725005193320",
        "req-ad541812658a",
        "req-92b0573b5b3e",
        "req-6f5a5f850524"
      ]
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 24,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:01:33+00:00",
    "event_id": "evt-0025-6589c31a3f3cee96",
    "event_type": "anchor_approved",
    "payload": {
      "fingerprint": "sha256:b7aba596297b86b995574a7034e67f42c8d2131ea6fa969fa680ed373278691a",
      "path": ".tailtrail/runs/start-20261019102950-bc8789/anchors/approved-v1.json",
      "requirements": [
        "req-725005193320",
        "req-ad541812658a",
        "req-92b0573b5b3e",
        "req-6f5a5f850524"
      ]
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 25,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:26+00:00",
    "event_id": "evt-0026-506292416a503ec5",
    "event_type": "planning_lock_approved",
    "payload": {
      "artifact": "planning/lock-v1.json",
      "audit": {
        "report_fingerprint": "sha256:e0b0b546d8179b1cb7c1b7774d89ae463d792c2283086eb9fdb9b7b42118edb2",
        "run_id": "start-20261019102950-bc8789",
        "source": "validated-aidlc-revision",
        "status": "clean"
      },
      "writes_allowed": true
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 26,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:26+00:00",
    "event_id": "evt-0027-8cacf6b000608be2",
    "event_type": "host_decision_recorded",
    "payload": {
      "artifact": "decisions/decisions-v1.jsonl",
      "decision": "approved",
      "decision_id": "sha256:40a47aad16f8f5d9c8da64292f2856e53677a247fe1cc544d9098f483b250f14",
      "verb": "approve"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 27,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:32+00:00",
    "event_id": "evt-0028-02792a1be9b42939",
    "event_type": "workflow_ownership_bound",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-35991103ad64/ownership-v1.json",
      "requirement_uids": [
        "req-725005193320",
        "req-ad541812658a",
        "req-92b0573b5b3e",
        "req-6f5a5f850524"
      ],
      "workflow_id": "ttw-35991103ad64"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 28,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:33+00:00",
    "event_id": "evt-0029-096199217bb00680",
    "event_type": "workflow_capability_plan_declared",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-35991103ad64/capability-plan-v1.json",
      "capability_ids": [
        "code-graph-mapper",
        "guardrails",
        "navigator",
        "review",
        "testing"
      ],
      "plan_fingerprint": "sha256:67535af29c2e2f109c9ec823304a1e18096e215f42da1dc32d9289435973f52e",
      "workflow_id": "ttw-35991103ad64"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 29,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:34+00:00",
    "event_id": "evt-0030-520c6b3d81f19a39",
    "event_type": "workflow_storage_initialized",
    "payload": {
      "journal": ".tailtrail/workflows/ttw-35991103ad64/journal-v1.jsonl",
      "projection": ".tailtrail/workflows/ttw-35991103ad64/projection-v1.json",
      "workflow_id": "ttw-35991103ad64"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 30,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:34+00:00",
    "event_id": "evt-0031-3948a0df90c718b3",
    "event_type": "workflow_state_created",
    "payload": {
      "journal": ".tailtrail/workflows/ttw-35991103ad64/journal-v1.jsonl",
      "sequence": 2,
      "workflow_id": "ttw-35991103ad64"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 31,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:44+00:00",
    "event_id": "evt-0032-657f38e9362bf76c",
    "event_type": "workflow_compiler_plan_created",
    "payload": {
      "artifact": ".tailtrail/workflows/ttw-35991103ad64/compiler-plan-v1.json",
      "plan_fingerprint": "sha256:70488ba40735c1396f505579d8bc68142050eb1c8af84f61ed08835389e09d44",
      "revision": 1,
      "template_id": "small-change",
      "workflow_id": "ttw-35991103ad64"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 32,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:44+00:00",
    "event_id": "evt-0033-a64c5f32a66c59ed",
    "event_type": "workflow_stage_approval_recorded",
    "payload": {
      "action_classes": [
        "write_tailtrail_state"
      ],
      "approval_id": "wfauth-d858bc85117822842520a14e",
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
      "workflow_id": "ttw-35991103ad64"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 33,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:44+00:00",
    "event_id": "evt-0034-378913feff199d66",
    "event_type": "workflow_stage_approval_recorded",
    "payload": {
      "action_classes": [
        "execute_project",
        "read_local",
        "write_project",
        "write_tailtrail_state"
      ],
      "approval_id": "wfauth-3f39ecc2229a522a0b69ca68",
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
      "workflow_id": "ttw-35991103ad64"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 34,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:44+00:00",
    "event_id": "evt-0035-91f6c9b43820a2a7",
    "event_type": "workflow_runtime_activated",
    "payload": {
      "binding": ".tailtrail/workflows/ttw-35991103ad64/ownership-v1.json",
      "capability_plan": ".tailtrail/workflows/ttw-35991103ad64/capability-plan-v1.json",
      "compiler_plan": ".tailtrail/workflows/ttw-35991103ad64/compiler-plan-v1.json",
      "compiler_plan_fingerprint": "sha256:70488ba40735c1396f505579d8bc68142050eb1c8af84f61ed08835389e09d44",
      "workflow_id": "ttw-35991103ad64"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 35,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:44+00:00",
    "event_id": "evt-0036-57d7898fac880d6e",
    "event_type": "aidlc_requirements_approved",
    "payload": {
      "anchor": ".tailtrail/runs/start-20261019102950-bc8789/anchors/approved-v1.json",
      "handoff": ".tailtrail/runs/start-20261019102950-bc8789/planning/execution-handoff-v1.json",
      "revision": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-revised-requirements-v2.json"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 36,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:04:44+00:00",
    "event_id": "evt-0037-1a4d6beb3c92a59f",
    "event_type": "planning_activated",
    "payload": {
      "anchor": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/anchors/approved-v1.json",
        "status": "created-from-aidlc"
      },
      "workflow_runtime": "compiled"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 37,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:14:20+00:00",
    "event_id": "evt-0038-8c247bb3bef57b10",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
      "fingerprint": "cc763f6cb383ec6f",
      "kind": "command-result",
      "sequence": 1
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 38,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:14:43+00:00",
    "event_id": "evt-0039-9c11f34c6656374b",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
      "fingerprint": "b28db5d40b5033c4",
      "kind": "command-result",
      "sequence": 2
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 39,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:15:26+00:00",
    "event_id": "evt-0040-e68c84ca81d1ecb3",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
      "fingerprint": "3bad972b314686c0",
      "kind": "command-result",
      "sequence": 3
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 40,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:17:24+00:00",
    "event_id": "evt-0041-4d97c6ffad1c0190",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
      "fingerprint": "220fcc56a6eadcc7",
      "kind": "command-result",
      "sequence": 4
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 41,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:17:37+00:00",
    "event_id": "evt-0042-30fb55f1f892d38a",
    "event_type": "start_plan_verbose_generated",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/verbose-reports/start-plan-verbose-v1.md",
      "mandatory": true,
      "markdown_size": 1804882,
      "status": "verified",
      "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261019102950-bc8789/start-plan.md",
      "visible_artifact": "session-reports/start-20261019102950-bc8789/start-plan.md"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 42,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:17:58+00:00",
    "event_id": "evt-0043-ca2165da22e6f622",
    "event_type": "harness_checkpoint",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/checkpoints/checkpoint-1.json",
      "checkpoint": 1,
      "drift": [
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-725005193320"
        },
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-ad541812658a"
        },
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-92b0573b5b3e"
        },
        {
          "category": "evidence",
          "classification": "resolved",
          "requirement_uid": "req-6f5a5f850524"
        },
        {
          "category": "scope",
          "classification": "new-drift",
          "message": "actual edit `scripts/planning-audit.py` is outside approved editable scope",
          "path": "scripts/planning-audit.py",
          "requirement_uid": "req-725005193320"
        },
        {
          "category": "scope",
          "classification": "new-drift",
          "message": "actual edit `scripts/planning-revision.py` is outside approved editable scope",
          "path": "scripts/planning-revision.py",
          "requirement_uid": "req-725005193320"
        },
        {
          "category": "scope",
          "classification": "new-drift",
          "message": "actual edit `tests/test_completion_report.py` is outside approved editable scope",
          "path": "tests/test_completion_report.py",
          "requirement_uid": "req-725005193320"
        },
        {
          "category": "scope",
          "classification": "new-drift",
          "message": "actual edit `tests/test_planning_audit.py` is outside approved editable scope",
          "path": "tests/test_planning_audit.py",
          "requirement_uid": "req-725005193320"
        },
        {
          "category": "scope",
          "classification": "new-drift",
          "message": "actual edit `tests/test_planning_lock.py` is outside approved editable scope",
          "path": "tests/test_planning_lock.py",
          "requirement_uid": "req-725005193320"
        }
      ],
      "requirement_states": {
        "req-6f5a5f850524": "validated",
        "req-725005193320": "validated",
        "req-92b0573b5b3e": "validated",
        "req-ad541812658a": "validated"
      }
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 43,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:18:11+00:00",
    "event_id": "evt-0044-980b4efb14ed977d",
    "event_type": "completion_review",
    "payload": {
      "artifact": "reviews/review-1.json",
      "checkpoint": 1,
      "complete": false,
      "findings": 5
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 44,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:18:11+00:00",
    "event_id": "evt-0045-5c5736b82cb01c5b",
    "event_type": "completion_gate",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/completion-gates/gate-1.json",
      "complete": true,
      "findings": []
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 45,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:18:11+00:00",
    "event_id": "evt-0046-c9c4f615f34f0164",
    "event_type": "closure_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/closure-records/closure-517e4b006ea4ca92.json",
      "checkpoint": 1,
      "gate_complete": true,
      "receipt_count": 3,
      "record_id": "closure-517e4b006ea4ca92",
      "review_complete": false
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 46,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:18:50+00:00",
    "event_id": "evt-0047-bfe1be3f303524f2",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
      "fingerprint": "1c9afaed2c28e2c7",
      "kind": "command-result",
      "sequence": 5
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 47,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:18:58+00:00",
    "event_id": "evt-0048-95345542727a01f6",
    "event_type": "harness_checkpoint",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/checkpoints/checkpoint-2.json",
      "checkpoint": 2,
      "drift": [
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-725005193320"
        },
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-ad541812658a"
        },
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-92b0573b5b3e"
        },
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-6f5a5f850524"
        }
      ],
      "requirement_states": {
        "req-6f5a5f850524": "validated",
        "req-725005193320": "validated",
        "req-92b0573b5b3e": "validated",
        "req-ad541812658a": "validated"
      }
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 48,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:18:58+00:00",
    "event_id": "evt-0049-9fc8bc82ded68144",
    "event_type": "completion_review",
    "payload": {
      "artifact": "reviews/review-2.json",
      "checkpoint": 2,
      "complete": true,
      "findings": 0
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 49,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:18:58+00:00",
    "event_id": "evt-0050-8877f3e56601ab90",
    "event_type": "completion_gate",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/completion-gates/gate-2.json",
      "complete": true,
      "findings": []
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 50,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:18:58+00:00",
    "event_id": "evt-0051-86ea41358078e0ed",
    "event_type": "closure_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/closure-records/closure-a2eaa78720d86107.json",
      "checkpoint": 2,
      "gate_complete": true,
      "receipt_count": 3,
      "record_id": "closure-a2eaa78720d86107",
      "review_complete": true
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 51,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:19:07+00:00",
    "event_id": "evt-0052-e8efa1e88cda4968",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 52,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:19:17+00:00",
    "event_id": "evt-0053-68e48e3815582add",
    "event_type": "navigator_graph_lifecycle_recorded",
    "payload": {
      "action": "refresh",
      "cache_fingerprint": "sha256:abd54e1f4025baafe50fb720deb9701dbc1990caff61520d87d4cf7db72f4b7c",
      "mapping_fingerprint": "sha256:7890b30c8de2d94b9c2714410e3731d101d1ee4ee85a5e9f856439f1feda86aa",
      "phase": "closure"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 53,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:19:46+00:00",
    "event_id": "evt-0054-895e11973991c2ea",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 54,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:22:31+00:00",
    "event_id": "evt-0055-eeba8567e9ad24af",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
      "fingerprint": "a2455abb95524f99",
      "kind": "command-result",
      "sequence": 6
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 55,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:22:41+00:00",
    "event_id": "evt-0056-4b387dd8b0acf901",
    "event_type": "harness_checkpoint",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/checkpoints/checkpoint-3.json",
      "checkpoint": 3,
      "drift": [
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-725005193320"
        },
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-ad541812658a"
        },
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-92b0573b5b3e"
        },
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-6f5a5f850524"
        }
      ],
      "requirement_states": {
        "req-6f5a5f850524": "validated",
        "req-725005193320": "validated",
        "req-92b0573b5b3e": "validated",
        "req-ad541812658a": "validated"
      }
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 56,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:22:41+00:00",
    "event_id": "evt-0057-01885fbe99833129",
    "event_type": "completion_review",
    "payload": {
      "artifact": "reviews/review-3.json",
      "checkpoint": 3,
      "complete": true,
      "findings": 0
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 57,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:22:41+00:00",
    "event_id": "evt-0058-960744ff161c6491",
    "event_type": "completion_gate",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/completion-gates/gate-3.json",
      "complete": true,
      "findings": []
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 58,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:22:41+00:00",
    "event_id": "evt-0059-6f442757c6417a10",
    "event_type": "closure_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/closure-records/closure-f577e5823f4ec7bd.json",
      "checkpoint": 3,
      "gate_complete": true,
      "receipt_count": 3,
      "record_id": "closure-f577e5823f4ec7bd",
      "review_complete": true
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 59,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:22:44+00:00",
    "event_id": "evt-0060-c57803f109262678",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 60,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:22:47+00:00",
    "event_id": "evt-0061-52634dbc085c7f62",
    "event_type": "navigator_graph_lifecycle_recorded",
    "payload": {
      "action": "reuse",
      "cache_fingerprint": "sha256:abd54e1f4025baafe50fb720deb9701dbc1990caff61520d87d4cf7db72f4b7c",
      "mapping_fingerprint": "sha256:7890b30c8de2d94b9c2714410e3731d101d1ee4ee85a5e9f856439f1feda86aa",
      "phase": "closure"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 61,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:22:56+00:00",
    "event_id": "evt-0062-7f98f0b3d73e6ac3",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-4.json",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 62,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:23:23+00:00",
    "event_id": "evt-0063-c8ad0384ed957d4c",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-5.json",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 63,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:23:59+00:00",
    "event_id": "evt-0064-c7612e669f23e6c8",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
      "fingerprint": "a81f7a654fd44a46",
      "kind": "source-edit",
      "sequence": 7
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 64,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:24:12+00:00",
    "event_id": "evt-0065-bca3cbfac5d5f7ab",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-6.json",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 65,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:24:15+00:00",
    "event_id": "evt-0066-5f66651ec522029a",
    "event_type": "navigator_graph_lifecycle_recorded",
    "payload": {
      "action": "reuse",
      "cache_fingerprint": "sha256:abd54e1f4025baafe50fb720deb9701dbc1990caff61520d87d4cf7db72f4b7c",
      "mapping_fingerprint": "sha256:7890b30c8de2d94b9c2714410e3731d101d1ee4ee85a5e9f856439f1feda86aa",
      "phase": "closure"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 66,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:24:32+00:00",
    "event_id": "evt-0067-144b82cf05a0df59",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-7.json",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 67,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:24:47+00:00",
    "event_id": "evt-0068-66c4da76fd4911f4",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-8.json",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 68,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:24:54+00:00",
    "event_id": "evt-0069-65f7d6800a6c7719",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-9.json",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 69,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:25:02+00:00",
    "event_id": "evt-0070-6457a336ff9a59c9",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-10.json",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 70,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:25:08+00:00",
    "event_id": "evt-0071-6487780e9baa7cb6",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-11.json",
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
      "overall_status": "evidence-incomplete"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 71,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:25:53+00:00",
    "event_id": "evt-0072-d286c457abcddd20",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
      "fingerprint": "d73866a486126ba0",
      "kind": "command-result",
      "sequence": 8
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 72,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:26:08+00:00",
    "event_id": "evt-0073-fc6bbc73569ba5b1",
    "event_type": "execution_evidence_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
      "fingerprint": "22340099eeb1eb07",
      "kind": "command-result",
      "sequence": 9
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 73,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:26:18+00:00",
    "event_id": "evt-0074-c6d6352d856255b5",
    "event_type": "harness_checkpoint",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/checkpoints/checkpoint-4.json",
      "checkpoint": 4,
      "drift": [
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-725005193320"
        },
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-ad541812658a"
        },
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-92b0573b5b3e"
        },
        {
          "category": "evidence",
          "classification": "unchanged",
          "requirement_uid": "req-6f5a5f850524"
        }
      ],
      "requirement_states": {
        "req-6f5a5f850524": "validated",
        "req-725005193320": "validated",
        "req-92b0573b5b3e": "validated",
        "req-ad541812658a": "validated"
      }
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 74,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:26:18+00:00",
    "event_id": "evt-0075-4825052daf0aab9b",
    "event_type": "completion_review",
    "payload": {
      "artifact": "reviews/review-4.json",
      "checkpoint": 4,
      "complete": true,
      "findings": 0
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 75,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:26:18+00:00",
    "event_id": "evt-0076-99ecf5617cfc2211",
    "event_type": "completion_gate",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/completion-gates/gate-4.json",
      "complete": true,
      "findings": []
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 76,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:26:18+00:00",
    "event_id": "evt-0077-f69b869387a5c22d",
    "event_type": "closure_recorded",
    "payload": {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/closure-records/closure-717b25644d324265.json",
      "checkpoint": 4,
      "gate_complete": true,
      "receipt_count": 3,
      "record_id": "closure-717b25644d324265",
      "review_complete": true
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 77,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:26:28+00:00",
    "event_id": "evt-0078-a60532a074adffd1",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-12.json",
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
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 78,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:26:49+00:00",
    "event_id": "evt-0079-0bd4b7aa9a82a81e",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-13.json",
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
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 79,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:27:17+00:00",
    "event_id": "evt-0080-91ea7543f59e4591",
    "event_type": "completion_report_created",
    "payload": {
      "artifact": "completion-reports/report-14.json",
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
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 80,
    "type": "tailtrail-run-event"
  },
  {
    "created_at": "2026-10-19T11:27:19+00:00",
    "event_id": "evt-0081-a78a8a79ee0b6b47",
    "event_type": "navigator_graph_lifecycle_recorded",
    "payload": {
      "action": "reuse",
      "cache_fingerprint": "sha256:abd54e1f4025baafe50fb720deb9701dbc1990caff61520d87d4cf7db72f4b7c",
      "mapping_fingerprint": "sha256:1071bfc6f9d58f5ebdf32ed5921f9b9c5a330d2b5c327ab4dd423c3292a823dd",
      "phase": "closure"
    },
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "sequence": 81,
    "type": "tailtrail-run-event"
  }
]
```

## Complete Saved Closure Payload

```json
{
  "assessments": {},
  "boundary": "Finalized deterministic local control evidence only. No receipt command, deployment, recovery action, or external environment was executed.",
  "changed_paths": [
    "scripts/closure-finalizer.py",
    "scripts/completion-report.py",
    "scripts/planning-audit.py",
    "scripts/planning-revision.py",
    "scripts/planning_lock.py",
    "scripts/verbose-reporting.py",
    "tests/test_closure_finalizer.py",
    "tests/test_completion_report.py",
    "tests/test_planning_audit.py",
    "tests/test_planning_lock.py",
    "tests/test_planning_revision.py"
  ],
  "closure_record": {
    "boundary": "Recorded validated evidence. Managed-command receipts were executed and captured by TailTrail; declared host receipts remain explicitly unverified.",
    "changed_paths": [
      "scripts/closure-finalizer.py",
      "scripts/completion-report.py",
      "scripts/planning-audit.py",
      "scripts/planning-revision.py",
      "scripts/planning_lock.py",
      "scripts/verbose-reporting.py",
      "tests/test_closure_finalizer.py",
      "tests/test_completion_report.py",
      "tests/test_planning_audit.py",
      "tests/test_planning_lock.py",
      "tests/test_planning_revision.py"
    ],
    "checkpoint": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261019102950-bc8789/checkpoints/checkpoint-4.json",
    "completion_gate": {
      "complete": true,
      "findings": [],
      "rule": "Only trusted managed-command or attested artifact-backed evidence can pass a tier; any reported non-pass blocks and authoritative failure dominates pass.",
      "run_artifact": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261019102950-bc8789/completion-gates/gate-4.json",
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "2",
      "type": "tailtrail-requirement-completion-gate"
    },
    "completion_review": {
      "checkpoint": 4,
      "complete": true,
      "findings": [],
      "next_action": "none",
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "type": "tailtrail-completion-review"
    },
    "next_action": "Run tailtrail completion-report for this run.",
    "proof_amendment_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/proof-amendments.jsonl",
    "receipt_artifacts": [
      ".tailtrail/runs/start-20261019102950-bc8789/validation-receipts/closure-717b25644d324265-1.json",
      ".tailtrail/runs/start-20261019102950-bc8789/validation-receipts/closure-717b25644d324265-2.json",
      ".tailtrail/runs/start-20261019102950-bc8789/validation-receipts/closure-717b25644d324265-3.json"
    ],
    "record_id": "closure-717b25644d324265",
    "reused": true,
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "selected_harnesses": [
      "Canonical requirements",
      "Question Orchestrator",
      "Requirement Completion Harness",
      "Requirement-to-Impact Map",
      "Evidence-Aware Testing",
      "Test Precision Planner"
    ],
    "type": "tailtrail-closure-record",
    "validated_input": "execution/evidence-stream.jsonl"
  },
  "closure_record_id": "closure-717b25644d324265",
  "command_registry": {
    "cmd-71ba4b": {
      "command": "python3 -m unittest discover -s tests -p test_planning_revision.py -v",
      "kind": "proof"
    }
  },
  "completion_report": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261019102950-bc8789/completion-reports/report-14.json",
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
      "changed_paths": [
        {
          "fingerprint": "sha256:fb1f68154f9e4d6d740050714a135bdaa9b7969578222dbdf209ba57a42fa8bf",
          "path": "scripts/closure-finalizer.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:422dc7db9a50818d742b427d56c80ac1e687b996dca1084d2047a04ce479f372",
          "path": "scripts/completion-report.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:24fd4cc5f2506f44b36b4749fd1645b79a53ce790e0eaca0b759780fabfbfc7a",
          "path": "scripts/planning-audit.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:e6139b7f735ca79b1797d43cd35f231fb38c3e6747e9569870271926a9b11648",
          "path": "scripts/planning-revision.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:e540a21b7efd4f2538887730bbf42e35b426a597ba8eed436ed8cab847159240",
          "path": "scripts/planning_lock.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:db8e16758a2c0acce22eb9184685f4bb61ca2aa881c43119d053d6a7dbaa9ea1",
          "path": "scripts/verbose-reporting.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:ef69f55dd937bd2c582a4bf35f5854fbbfdc990019da7b03f77ac51e415215d5",
          "path": "tests/test_closure_finalizer.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:a0bfd34306204aaabb70c58b3708202b5025f8ed88448600df72b07d87a4421e",
          "path": "tests/test_completion_report.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:1f9c5ff0197d47f9ba1b7eb4b841dd7f0cb594d0106a5ea22c0e3fd69cbf3fab",
          "path": "tests/test_planning_audit.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:c2e78c3931ed6f795627040c752e5b019c4f4ce4c4cb32565f17cd010b7ad1e7",
          "path": "tests/test_planning_lock.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:ab6a53e7366b9fcfa05d54017283fdb568579226f3de6cacf99f7c2bde89f777",
          "path": "tests/test_planning_revision.py",
          "vcs_status": "modified",
          "verified": true
        }
      ],
      "findings": [],
      "status": "approved"
    },
    "closure_guidance": {
      "managed_proof_passing": true,
      "missing": []
    },
    "completion_learning": {
      "artifact": null,
      "boundary": "No unresolved completion gap requires a learning candidate.",
      "event_id": null,
      "status": "not-triggered"
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
      "approval_id": "wfauth-3f39ecc2229a522a0b69ca68",
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
        "artifact": "checkpoints/checkpoint-4.json",
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
        "artifact": "completion-gates/gate-4.json",
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
          "fingerprint": "sha256:fb1f68154f9e4d6d740050714a135bdaa9b7969578222dbdf209ba57a42fa8bf",
          "path": "scripts/closure-finalizer.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:422dc7db9a50818d742b427d56c80ac1e687b996dca1084d2047a04ce479f372",
          "path": "scripts/completion-report.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:24fd4cc5f2506f44b36b4749fd1645b79a53ce790e0eaca0b759780fabfbfc7a",
          "path": "scripts/planning-audit.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:e6139b7f735ca79b1797d43cd35f231fb38c3e6747e9569870271926a9b11648",
          "path": "scripts/planning-revision.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:e540a21b7efd4f2538887730bbf42e35b426a597ba8eed436ed8cab847159240",
          "path": "scripts/planning_lock.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:db8e16758a2c0acce22eb9184685f4bb61ca2aa881c43119d053d6a7dbaa9ea1",
          "path": "scripts/verbose-reporting.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:ef69f55dd937bd2c582a4bf35f5854fbbfdc990019da7b03f77ac51e415215d5",
          "path": "tests/test_closure_finalizer.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:a0bfd34306204aaabb70c58b3708202b5025f8ed88448600df72b07d87a4421e",
          "path": "tests/test_completion_report.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:1f9c5ff0197d47f9ba1b7eb4b841dd7f0cb594d0106a5ea22c0e3fd69cbf3fab",
          "path": "tests/test_planning_audit.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:c2e78c3931ed6f795627040c752e5b019c4f4ce4c4cb32565f17cd010b7ad1e7",
          "path": "tests/test_planning_lock.py",
          "vcs_status": "modified",
          "verified": true
        },
        {
          "fingerprint": "sha256:ab6a53e7366b9fcfa05d54017283fdb568579226f3de6cacf99f7c2bde89f777",
          "path": "tests/test_planning_revision.py",
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
          "artifact": "planning/revisions/start-report-v4.json",
          "kind": "approved-plan-revision",
          "revision": 4
        },
        {
          "artifact": "execution/proof-amendments.jsonl",
          "kind": "approved-additive-proof-amendments"
        }
      ],
      "base_plan": {
        "artifact": "planning/start-report-v1.json",
        "revision": 1
      },
      "boundary": "The base plan remains immutable; approved revisions and additive proof amendments are reported as separate effective-plan inputs.",
      "effective_plan": {
        "active_artifact": "planning/revisions/start-report-v4.json",
        "active_revision": 4,
        "base_is_immutable": true
      }
    },
    "plan_evidence": {
      "boundary": "Receipts stamped with a superseded plan fingerprint prove nothing about the approved plan; re-run them after re-approval. Fingerprint-less legacy receipts keep historical behavior.",
      "current": 3,
      "current_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
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
              "classification": "unchanged",
              "requirement_uid": "req-725005193320"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.json",
              "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest discover -s tests -p test_planning_revision.py -v",
              "command_label": "visible report generation and canonical preservation",
              "duration_ms": 11995,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-19T11:26:07.325970+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-6f5a5f850524",
                "req-725005193320"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-19T11:25:55.329752+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stderr.txt",
              "stderr_sha256": "sha256:69f5e69d1d3e1f9e46a4df6bb9cbb1227224eef4a06f39ad035e826012021b3f",
              "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stdout.txt",
              "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
              "tier": "unit",
              "tiers": [
                "unit"
              ]
            },
            {
              "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.json",
              "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
              "command_label": "planning, audit, and completion report regressions",
              "duration_ms": 13764,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-19T11:18:48.551394+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-6f5a5f850524",
                "req-725005193320",
                "req-92b0573b5b3e"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-19T11:18:34.786610+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stderr.txt",
              "stderr_sha256": "sha256:483b839ba7645daa9f6187408edc54e4027bd6888611d901e0d8695174b89398",
              "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stdout.txt",
              "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              "tier": "contract",
              "tiers": [
                "contract",
                "integration",
                "unit"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "implemented",
          "requirement_uid": "req-725005193320",
          "statement": "Generate visible full verbose session reports without fabricated metrics.",
          "status": "complete",
          "verification_status": "pass"
        },
        {
          "display_id": "REQ-02",
          "drift": [
            {
              "category": "evidence",
              "classification": "unchanged",
              "requirement_uid": "req-ad541812658a"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.json",
              "asserted_behavior": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.; The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
              "command_label": "full Start and Closure lifecycle reports",
              "duration_ms": 23395,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-19T11:25:52.373076+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-92b0573b5b3e",
                "req-ad541812658a"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-19T11:25:28.976827+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stderr.txt",
              "stderr_sha256": "sha256:84f3805263b3d88605ecfd8140ac16688a1e85a40624386377e3ede7141ac9a7",
              "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stdout.txt",
              "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
              "tier": "behaviour",
              "tiers": [
                "behaviour",
                "contract",
                "integration",
                "unit"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "implemented",
          "requirement_uid": "req-ad541812658a",
          "statement": "The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
          "status": "complete",
          "verification_status": "pass"
        },
        {
          "display_id": "REQ-03",
          "drift": [
            {
              "category": "evidence",
              "classification": "unchanged",
              "requirement_uid": "req-92b0573b5b3e"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.json",
              "asserted_behavior": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.; The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
              "command_label": "full Start and Closure lifecycle reports",
              "duration_ms": 23395,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-19T11:25:52.373076+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-92b0573b5b3e",
                "req-ad541812658a"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-19T11:25:28.976827+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stderr.txt",
              "stderr_sha256": "sha256:84f3805263b3d88605ecfd8140ac16688a1e85a40624386377e3ede7141ac9a7",
              "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stdout.txt",
              "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
              "tier": "behaviour",
              "tiers": [
                "behaviour",
                "contract",
                "integration",
                "unit"
              ]
            },
            {
              "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.json",
              "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
              "command_label": "planning, audit, and completion report regressions",
              "duration_ms": 13764,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-19T11:18:48.551394+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-6f5a5f850524",
                "req-725005193320",
                "req-92b0573b5b3e"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-19T11:18:34.786610+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stderr.txt",
              "stderr_sha256": "sha256:483b839ba7645daa9f6187408edc54e4027bd6888611d901e0d8695174b89398",
              "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stdout.txt",
              "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              "tier": "contract",
              "tiers": [
                "contract",
                "integration",
                "unit"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "implemented",
          "requirement_uid": "req-92b0573b5b3e",
          "statement": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
          "status": "complete",
          "verification_status": "pass"
        },
        {
          "display_id": "REQ-04",
          "drift": [
            {
              "category": "evidence",
              "classification": "unchanged",
              "requirement_uid": "req-6f5a5f850524"
            }
          ],
          "evidence": [
            {
              "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.json",
              "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest discover -s tests -p test_planning_revision.py -v",
              "command_label": "visible report generation and canonical preservation",
              "duration_ms": 11995,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-19T11:26:07.325970+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-6f5a5f850524",
                "req-725005193320"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-19T11:25:55.329752+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stderr.txt",
              "stderr_sha256": "sha256:69f5e69d1d3e1f9e46a4df6bb9cbb1227224eef4a06f39ad035e826012021b3f",
              "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stdout.txt",
              "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
              "tier": "unit",
              "tiers": [
                "unit"
              ]
            },
            {
              "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.json",
              "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
              "collector": "tailtrail-managed-execution-v2",
              "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
              "command_label": "planning, audit, and completion report regressions",
              "duration_ms": 13764,
              "environment": "Darwin arm64 Python 3.12.6",
              "evidence_label": "managed-command",
              "evidence_quality": "trusted",
              "exit_code": 0,
              "finished_at": "2026-10-19T11:18:48.551394+00:00",
              "outcome": "pass",
              "requirement_uids": [
                "req-6f5a5f850524",
                "req-725005193320",
                "req-92b0573b5b3e"
              ],
              "scenario_ids": [],
              "started_at": "2026-10-19T11:18:34.786610+00:00",
              "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stderr.txt",
              "stderr_sha256": "sha256:483b839ba7645daa9f6187408edc54e4027bd6888611d901e0d8695174b89398",
              "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stdout.txt",
              "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              "tier": "contract",
              "tiers": [
                "contract",
                "integration",
                "unit"
              ]
            }
          ],
          "findings": [],
          "implementation_status": "implemented",
          "requirement_uid": "req-6f5a5f850524",
          "statement": "Preserve canonical internal copies.",
          "status": "complete",
          "verification_status": "pass"
        }
      ],
      "total": 4
    },
    "run_artifact": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261019102950-bc8789/completion-reports/report-14.json",
    "run_id": "start-20261019102950-bc8789",
    "schema_version": "1",
    "session_reports": {
      "closure": {
        "absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261019102950-bc8789/closure-report.md",
        "exists": false,
        "workspace_path": "session-reports/start-20261019102950-bc8789/closure-report.md"
      },
      "start": {
        "absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261019102950-bc8789/start-plan.md",
        "exists": true,
        "workspace_path": "session-reports/start-20261019102950-bc8789/start-plan.md"
      }
    },
    "source_artifacts": {
      "active_plan": "planning/revisions/start-report-v4.json",
      "approved_anchor": "anchors/approved-v6.json",
      "architecture": null,
      "base_plan": "planning/start-report-v1.json",
      "behaviour": null,
      "checkpoint": "checkpoints/checkpoint-4.json",
      "completion_gate": "completion-gates/gate-4.json",
      "completion_learning": null,
      "completion_review": "reviews/review-4.json",
      "debug_closure_section": null,
      "learning_use_receipts": null,
      "maintainability": null,
      "official_design": null,
      "official_evidence": null,
      "official_handoff": null,
      "positive_learning": null,
      "proof_amendments": "execution/proof-amendments.jsonl",
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
        "lrn-ebe95e19a5a52ab1",
        "lrn-ebff1626a1e89a0a",
        "lrn-ef1b6215f75228f0",
        "lrn-f1ac3e1ab969782e",
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
        "detail": "11 changed path(s); 0 saved blocker(s)",
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
        "detail": "11 saved changed path(s)",
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
        "detail": "3373 focused tokens",
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
        "contract",
        "integration",
        "unit"
      ],
      "receipt_refs": [
        ".tailtrail/runs/start-20261019102950-bc8789/validation-receipts/closure-717b25644d324265-1.json",
        ".tailtrail/runs/start-20261019102950-bc8789/validation-receipts/closure-717b25644d324265-2.json",
        ".tailtrail/runs/start-20261019102950-bc8789/validation-receipts/closure-717b25644d324265-3.json"
      ],
      "receipts": [
        {
          "artifact_path": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.json",
          "asserted_behavior": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.; The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
          "closure_record_id": "closure-717b25644d324265",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
          "command_label": "full Start and Closure lifecycle reports",
          "duration_ms": 23395,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-19T11:25:52.373076+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
          "proof_amendment_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/proof-amendments.jsonl",
          "requirement_uids": [
            "req-92b0573b5b3e",
            "req-ad541812658a"
          ],
          "scenario_ids": [],
          "schema_version": "2",
          "started_at": "2026-10-19T11:25:28.976827+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stderr.txt",
          "stderr_sha256": "sha256:84f3805263b3d88605ecfd8140ac16688a1e85a40624386377e3ede7141ac9a7",
          "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
          "tier": "behaviour",
          "tiers": [
            "behaviour",
            "contract",
            "integration",
            "unit"
          ],
          "type": "tailtrail-validation-evidence-receipt"
        },
        {
          "artifact_path": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.json",
          "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.",
          "closure_record_id": "closure-717b25644d324265",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest discover -s tests -p test_planning_revision.py -v",
          "command_label": "visible report generation and canonical preservation",
          "duration_ms": 11995,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-19T11:26:07.325970+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
          "proof_amendment_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/proof-amendments.jsonl",
          "requirement_uids": [
            "req-6f5a5f850524",
            "req-725005193320"
          ],
          "scenario_ids": [],
          "schema_version": "2",
          "started_at": "2026-10-19T11:25:55.329752+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stderr.txt",
          "stderr_sha256": "sha256:69f5e69d1d3e1f9e46a4df6bb9cbb1227224eef4a06f39ad035e826012021b3f",
          "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stdout.txt",
          "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
          "tier": "unit",
          "tiers": [
            "unit"
          ],
          "type": "tailtrail-validation-evidence-receipt"
        },
        {
          "artifact_path": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.json",
          "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
          "closure_record_id": "closure-717b25644d324265",
          "collector": "tailtrail-managed-execution-v2",
          "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
          "command_label": "planning, audit, and completion report regressions",
          "duration_ms": 13764,
          "environment": "Darwin arm64 Python 3.12.6",
          "evidence_label": "managed-command",
          "evidence_quality": "trusted",
          "exit_code": 0,
          "finished_at": "2026-10-19T11:18:48.551394+00:00",
          "outcome": "pass",
          "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
          "proof_amendment_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/proof-amendments.jsonl",
          "requirement_uids": [
            "req-6f5a5f850524",
            "req-725005193320",
            "req-92b0573b5b3e"
          ],
          "scenario_ids": [],
          "schema_version": "2",
          "started_at": "2026-10-19T11:18:34.786610+00:00",
          "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stderr.txt",
          "stderr_sha256": "sha256:483b839ba7645daa9f6187408edc54e4027bd6888611d901e0d8695174b89398",
          "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stdout.txt",
          "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tier": "contract",
          "tiers": [
            "contract",
            "integration",
            "unit"
          ],
          "type": "tailtrail-validation-evidence-receipt"
        }
      ],
      "required_checks": [
        {
          "candidate_paths": [
            "tests/test_planning_revision.py",
            "tests/test_closure_finalizer.py"
          ],
          "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
          "requirement_uids": [
            "req-ad541812658a",
            "req-92b0573b5b3e"
          ],
          "tiers": [
            "unit",
            "contract",
            "behaviour",
            "integration"
          ]
        }
      ],
      "status": "pass",
      "tier_results": {
        "behaviour": "pass",
        "contract": "pass",
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
        "estimated_reduction_percent": 94.29,
        "estimated_saved_tokens": 55662,
        "forecast_confidence": "medium",
        "learning_evidence_references": [],
        "planned_working_set_tokens": 3373,
        "repository_ceiling_tokens": 2313613,
        "repository_file_count": 980,
        "saving_techniques": [
          "Code Graph slice reuse",
          "Navigator scope narrowing",
          "Focused validation selection"
        ],
        "scoped_file_ceiling_tokens": 59035,
        "scoped_tokens": 3373,
        "status": "estimated"
      },
      "planning_estimate_tokens": 3373,
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
  "delivery_record": ".tailtrail/runs/start-20261019102950-bc8789/delivery-record.md",
  "execution_events": [
    {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-275a3f67bf12d67a.json",
      "asserted_behavior": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.; The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
      "changed_paths": [
        "scripts/closure-finalizer.py",
        "scripts/completion-report.py",
        "scripts/planning_lock.py",
        "scripts/verbose-reporting.py",
        "tests/test_closure_finalizer.py",
        "tests/test_planning_revision.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
      "command_label": "full Start and Closure lifecycle reports",
      "duration_ms": 24769,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "cc763f6cb383ec6f",
      "finished_at": "2026-10-19T11:14:18.609960+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:4d1a0c91dea0cd252a316aa5fa638c20c28d84a4ec440e87ea972cfc82ff3f74",
      "requirement_uids": [
        "req-92b0573b5b3e",
        "req-ad541812658a"
      ],
      "run_id": "start-20261019102950-bc8789",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 1,
      "started_at": "2026-10-19T11:13:53.839668+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-275a3f67bf12d67a.stderr.txt",
      "stderr_sha256": "sha256:c4e11c4556b6605bd2ae99cffb4c90c20c8d233f8b92339c9903e2d3cb03375b",
      "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-275a3f67bf12d67a.stdout.txt",
      "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
      "tier": "unit",
      "tiers": [
        "unit",
        "contract",
        "behaviour",
        "integration"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-316c1f16e9c45c44.json",
      "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.",
      "changed_paths": [
        "scripts/closure-finalizer.py",
        "scripts/completion-report.py",
        "scripts/planning_lock.py",
        "scripts/verbose-reporting.py",
        "tests/test_closure_finalizer.py",
        "tests/test_planning_revision.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest discover -s tests -p test_planning_revision.py -v",
      "command_label": "visible report generation and canonical preservation",
      "duration_ms": 12494,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "b28db5d40b5033c4",
      "finished_at": "2026-10-19T11:14:42.154103+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:4d1a0c91dea0cd252a316aa5fa638c20c28d84a4ec440e87ea972cfc82ff3f74",
      "requirement_uids": [
        "req-6f5a5f850524",
        "req-725005193320"
      ],
      "run_id": "start-20261019102950-bc8789",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 2,
      "started_at": "2026-10-19T11:14:29.658841+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-316c1f16e9c45c44.stderr.txt",
      "stderr_sha256": "sha256:a5526b4d1efe5b6d87237a1a3edc863b6596f4d9a51046ff3b968e43603f208d",
      "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-316c1f16e9c45c44.stdout.txt",
      "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
      "tier": "unit",
      "tiers": [
        "unit"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-a283432b649af98e.json",
      "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
      "changed_paths": [
        "scripts/closure-finalizer.py",
        "scripts/completion-report.py",
        "scripts/planning-audit.py",
        "scripts/planning-revision.py",
        "scripts/planning_lock.py",
        "scripts/verbose-reporting.py",
        "tests/test_closure_finalizer.py",
        "tests/test_completion_report.py",
        "tests/test_planning_audit.py",
        "tests/test_planning_lock.py",
        "tests/test_planning_revision.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
      "command_label": "planning, audit, and completion report regressions",
      "duration_ms": 13728,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 1,
      "fingerprint": "3bad972b314686c0",
      "finished_at": "2026-10-19T11:15:24.848588+00:00",
      "kind": "command-result",
      "outcome": "fail",
      "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
      "requirement_uids": [
        "req-6f5a5f850524",
        "req-725005193320",
        "req-92b0573b5b3e"
      ],
      "run_id": "start-20261019102950-bc8789",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 3,
      "started_at": "2026-10-19T11:15:11.120157+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-a283432b649af98e.stderr.txt",
      "stderr_sha256": "sha256:4d8d172fa4c02c79124e8b3e5be244f7ca145d659e4614a791779d75e4b5ddc7",
      "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-a283432b649af98e.stdout.txt",
      "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "tier": "unit",
      "tiers": [
        "unit",
        "contract",
        "integration"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-ac05744b99d6321a.json",
      "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
      "changed_paths": [
        "scripts/closure-finalizer.py",
        "scripts/completion-report.py",
        "scripts/planning-audit.py",
        "scripts/planning-revision.py",
        "scripts/planning_lock.py",
        "scripts/verbose-reporting.py",
        "tests/test_closure_finalizer.py",
        "tests/test_completion_report.py",
        "tests/test_planning_audit.py",
        "tests/test_planning_lock.py",
        "tests/test_planning_revision.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
      "command_label": "planning, audit, and completion report regressions",
      "duration_ms": 13492,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "220fcc56a6eadcc7",
      "finished_at": "2026-10-19T11:17:22.630168+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
      "requirement_uids": [
        "req-6f5a5f850524",
        "req-725005193320",
        "req-92b0573b5b3e"
      ],
      "run_id": "start-20261019102950-bc8789",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 4,
      "started_at": "2026-10-19T11:17:09.136831+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-ac05744b99d6321a.stderr.txt",
      "stderr_sha256": "sha256:f9b223b889193842129eb4deef691b3ab977310bf12238085f462730ff008558",
      "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-ac05744b99d6321a.stdout.txt",
      "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "tier": "unit",
      "tiers": [
        "unit",
        "contract",
        "integration"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.json",
      "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.; The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.",
      "changed_paths": [
        "scripts/closure-finalizer.py",
        "scripts/completion-report.py",
        "scripts/planning-audit.py",
        "scripts/planning-revision.py",
        "scripts/planning_lock.py",
        "scripts/verbose-reporting.py",
        "tests/test_closure_finalizer.py",
        "tests/test_completion_report.py",
        "tests/test_planning_audit.py",
        "tests/test_planning_lock.py",
        "tests/test_planning_revision.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_planning_lock tests.test_planning_audit tests.test_completion_report -v",
      "command_label": "planning, audit, and completion report regressions",
      "duration_ms": 13764,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "1c9afaed2c28e2c7",
      "finished_at": "2026-10-19T11:18:48.551394+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
      "requirement_uids": [
        "req-6f5a5f850524",
        "req-725005193320",
        "req-92b0573b5b3e"
      ],
      "run_id": "start-20261019102950-bc8789",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 5,
      "started_at": "2026-10-19T11:18:34.786610+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stderr.txt",
      "stderr_sha256": "sha256:483b839ba7645daa9f6187408edc54e4027bd6888611d901e0d8695174b89398",
      "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-537c286c367ec130.stdout.txt",
      "stdout_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "tier": "unit",
      "tiers": [
        "unit",
        "contract",
        "integration"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-5cb73e92ec1fb5ad.json",
      "asserted_behavior": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.; The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
      "changed_paths": [
        "scripts/closure-finalizer.py",
        "scripts/completion-report.py",
        "scripts/planning_lock.py",
        "scripts/verbose-reporting.py",
        "tests/test_closure_finalizer.py",
        "tests/test_planning_revision.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
      "command_label": "full Start and Closure lifecycle reports",
      "duration_ms": 24092,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "a2455abb95524f99",
      "finished_at": "2026-10-19T11:22:24.997322+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
      "requirement_uids": [
        "req-92b0573b5b3e",
        "req-ad541812658a"
      ],
      "run_id": "start-20261019102950-bc8789",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 6,
      "started_at": "2026-10-19T11:22:00.904777+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-5cb73e92ec1fb5ad.stderr.txt",
      "stderr_sha256": "sha256:b354214d46a84a6b11f658e700847ae06c90e6057f4d886b59a01bbcbb33b2ed",
      "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-5cb73e92ec1fb5ad.stdout.txt",
      "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
      "tier": "unit",
      "tiers": [
        "unit",
        "contract",
        "behaviour",
        "integration"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "changed_paths": [
        "scripts/closure-finalizer.py",
        "scripts/completion-report.py",
        "scripts/planning-audit.py",
        "scripts/planning-revision.py",
        "scripts/planning_lock.py",
        "scripts/verbose-reporting.py",
        "tests/test_closure_finalizer.py",
        "tests/test_completion_report.py",
        "tests/test_planning_audit.py",
        "tests/test_planning_lock.py",
        "tests/test_planning_revision.py"
      ],
      "evidence_boundary": "Host-supplied execution fact. TailTrail did not execute, reinterpret, or infer this event.",
      "fingerprint": "a81f7a654fd44a46",
      "kind": "source-edit",
      "requirement_uids": [
        "req-6f5a5f850524",
        "req-725005193320",
        "req-92b0573b5b3e",
        "req-ad541812658a"
      ],
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "2",
      "sequence": 7,
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.json",
      "asserted_behavior": "The closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers.; The start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance.",
      "changed_paths": [
        "scripts/closure-finalizer.py",
        "scripts/completion-report.py",
        "scripts/planning_lock.py",
        "scripts/verbose-reporting.py",
        "tests/test_closure_finalizer.py",
        "tests/test_planning_revision.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest tests.test_planning_revision tests.test_closure_finalizer -v",
      "command_label": "full Start and Closure lifecycle reports",
      "duration_ms": 23395,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "d73866a486126ba0",
      "finished_at": "2026-10-19T11:25:52.373076+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
      "requirement_uids": [
        "req-92b0573b5b3e",
        "req-ad541812658a"
      ],
      "run_id": "start-20261019102950-bc8789",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 8,
      "started_at": "2026-10-19T11:25:28.976827+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stderr.txt",
      "stderr_sha256": "sha256:84f3805263b3d88605ecfd8140ac16688a1e85a40624386377e3ede7141ac9a7",
      "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-0b5be1dccf0e67c8.stdout.txt",
      "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
      "tier": "unit",
      "tiers": [
        "unit",
        "contract",
        "behaviour",
        "integration"
      ],
      "type": "tailtrail-execution-evidence"
    },
    {
      "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.json",
      "asserted_behavior": "Preserve canonical internal copies.; Generate visible full verbose session reports without fabricated metrics.",
      "changed_paths": [
        "scripts/closure-finalizer.py",
        "scripts/completion-report.py",
        "scripts/planning_lock.py",
        "scripts/verbose-reporting.py",
        "tests/test_closure_finalizer.py",
        "tests/test_planning_revision.py"
      ],
      "collector": "tailtrail-managed-execution-v2",
      "command": "python3 -m unittest discover -s tests -p test_planning_revision.py -v",
      "command_label": "visible report generation and canonical preservation",
      "duration_ms": 11995,
      "environment": "Darwin arm64 Python 3.12.6",
      "evidence_boundary": "TailTrail executed the exact approved validation command and captured its exit code, timing, and redacted output artifacts.",
      "evidence_label": "managed-command",
      "evidence_quality": "trusted",
      "exit_code": 0,
      "fingerprint": "22340099eeb1eb07",
      "finished_at": "2026-10-19T11:26:07.325970+00:00",
      "kind": "command-result",
      "outcome": "pass",
      "plan_fingerprint": "sha256:410b053b0240a889ec31959e2e6da0d5421ea9e538cf06b63030cd051dc96904",
      "requirement_uids": [
        "req-6f5a5f850524",
        "req-725005193320"
      ],
      "run_id": "start-20261019102950-bc8789",
      "scenario_ids": [],
      "schema_version": "2",
      "sequence": 9,
      "started_at": "2026-10-19T11:25:55.329752+00:00",
      "stderr_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stderr.txt",
      "stderr_sha256": "sha256:69f5e69d1d3e1f9e46a4df6bb9cbb1227224eef4a06f39ad035e826012021b3f",
      "stdout_artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/command-artifacts/command-064650b113becf17.stdout.txt",
      "stdout_sha256": "sha256:0f2a2ff2a1bfd7e64ae388a561b07497025998d1906f29b334748c0c95799249",
      "tier": "unit",
      "tiers": [
        "unit"
      ],
      "type": "tailtrail-execution-evidence"
    }
  ],
  "finalizer_id": "finalizer-102fc6b780b8510e",
  "graph_lifecycle": {
    "action": "reuse",
    "after_status": {
      "reasons": [
        "Cached graph scope and watched file hashes still match."
      ],
      "scope": [
        "tests/test_question_orchestrator.py",
        "scripts/harness-checkpoint.py",
        "scripts/aidlc-official-host.py",
        "scripts/workflow-dashboard.py",
        "scripts/closure-recorder.py",
        "tests/test_closure_recorder.py",
        "tests/test_workflow_documentation.py",
        "tests/test_navigator_graph_lifecycle.py",
        "tests/test_code_graph_inventory.py",
        "tests/test_execution_evidence.py",
        "tests/test_planning_lock.py",
        "tests/test_navigator_scope.py",
        "scripts/learning-use-receipt.py",
        "tests/test_task_type_contract.py",
        "tests/test_workflow_template_execution.py",
        "tests/test_public_route_gate.py",
        "tests/test_sequential_pipeline.py",
        "tests/test_tailtrail_registry.py",
        "scripts/meta-harness-analyze.py",
        "scripts/architecture-fitness.py",
        "tests/test_workflow_adapters.py",
        "scripts/aidlc-check.py",
        "scripts/execution-evidence.py",
        "scripts/closure-close.py",
        "tests/test_write_guardian.py",
        "scripts/host_contract.py",
        "scripts/task-start.py",
        "tests/test_code_graph_cache.py",
        "tests/test_workflow_phase7.py",
        "tests/test_host_adapter_conformance.py",
        "tests/test_review_scope.py",
        "tests/test_evaluation_audit.py",
        "tests/test_intake_pipeline.py",
        "scripts/closure-evaluation.py",
        "scripts/code_graph_cache.py",
        "tests/test_workflow_start_integration.py",
        "tests/test_workflow_ci_continuation.py",
        "scripts/navigator-scope-release.py",
        "scripts/navigator_discovery.py",
        "scripts/benchmark-tailtrail.py",
        "scripts/aidlc-official-install.py",
        "scripts/completion-report.py",
        "scripts/navigator.py",
        "hooks/hooks.json",
        "tests/test_requirement_routing_phase0.py",
        "tests/test_task_type_gate.py",
        "tests/test_host_question_flow_phase0_artifacts.py",
        "scripts/adoption-validation.py",
        "scripts/check-tailtrail.py",
        "scripts/host-adapter-conformance.py",
        "scripts/debug-host-diagnosis.py",
        "scripts/tailtrail.py",
        "tests/test_aidlc_official_bridge.py",
        "scripts/advanced-runtime.py",
        "tests/test_start_entrypoints.py",
        "scripts/change-intent-anchor.py",
        "tests/test_host_contract.py",
        "tests/test_host_input_contract_schema.py",
        "tests/test_greenfield_e2e.py",
        "scripts/official-aidlc-state.py",
        "scripts/install-local.py",
        "scripts/write_guardian.py",
        "tests/test_demo_prompt_book.py",
        "tests/test_workflow_contracts.py",
        "scripts/update-copilot.py",
        "tests/test_repository_path_policy.py",
        "tests/test_requirement_discovery.py",
        "tests/test_revision_proof_overlay.py",
        "scripts/debug-preflight.py",
        "scripts/planning-discussion.py",
        "scripts/planning-revision.py",
        "scripts/learning-agent.py",
        "tests/test_host_question_flow_event_schema.py",
        "tests/test_closure_finalizer.py",
        "tests/test_completion_review.py",
        "tests/test_aidlc_official_host.py",
        "scripts/architecture_planning.py",
        "tests/test_debug_start_planning.py",
        "scripts/planning-aidlc-question.py",
        "tests/test_debug_host_integration.py",
        "scripts/run-ledger.py",
        "tests/test_host_packet_tickets.py",
        "scripts/workflow_runtime/start_integration.py",
        "scripts/host-decision.py",
        "scripts/aidlc-requirements.py",
        "scripts/learning-refresh.py",
        "scripts/closure-contract.py",
        "tests/test_workflow_dashboard.py",
        "tests/test_workflow_privacy.py",
        "scripts/workflow_runtime/enterprise_transport.py",
        "tests/test_planning_revision.py",
        "scripts/closure-finalizer.py",
        "scripts/debug-completion.py",
        "schemas/host-input-contract.schema.json",
        "scripts/workflow_runtime/storage.py",
        "tests/test_enterprise_host_adapters.py",
        "scripts/behaviour_planning.py",
        "tests/test_mcp_server.py",
        "tests/test_new_file_due_diligence.py",
        "tests/test_install_profiles.py",
        "tests/test_full_pipeline.py",
        "scripts/debug-correction.py",
        "release-manifest.json",
        "tests/test_review_graph.py",
        "scripts/host-reply-validate.py",
        "scripts/verbose-reporting.py",
        "tests/test_navigator_core.py",
        "scripts/delivery-record.py",
        "scripts/aidlc-init.py",
        "scripts/code-graph-mapper.py",
        "scripts/install-copilot.py",
        "scripts/ast-map.py",
        "scripts/official-aidlc-checkpoint.py",
        "scripts/new_file_due_diligence.py",
        "tests/test_canonical_statement_contract.py",
        "tests/test_planning_audit.py",
        "scripts/planning_lock.py",
        "scripts/pipeline_orchestrator.py",
        "schemas/host-question-flow-event.schema.json",
        "scripts/official-aidlc-requirements.py",
        "scripts/planning-audit.py",
        "demo-project-layout/tailtrail-demo-workspace/services/claims-api/tests/test_validation.py",
        "scripts/navigator-scope.py",
        "tests/test_delivery_record.py",
        "tests/test_task_recovery.py",
        "tests/test_completion_report.py",
        "tests/test_workflow_approvals.py",
        "scripts/mcp-server.py",
        "scripts/navigator_scope.py",
        "pyproject.toml",
        "scripts/repository_path_policy.py",
        "scripts/aidlc-official-bridge.py",
        "scripts/question-orchestrator.py",
        "scripts/aidlc-official-detect.py",
        "scripts/docs-only.py",
        "scripts/debug-harness-convergence.py",
        "tests/test_navigator_installed_release.py",
        "scripts/review-graph.py",
        "buildweek-demo-project/src/claims_api/validation.py",
        "scripts/intake_pipeline.py",
        "scripts/greenfield_e2e_fixture.py",
        "tests/test_architecture_fitness.py"
      ],
      "status": "fresh"
    },
    "attempt_id": "start-20261019102950-bc8789",
    "before_status": {
      "reasons": [
        "Cached graph scope and watched file hashes still match."
      ],
      "scope": [
        "tests/test_question_orchestrator.py",
        "scripts/harness-checkpoint.py",
        "scripts/aidlc-official-host.py",
        "scripts/workflow-dashboard.py",
        "scripts/closure-recorder.py",
        "tests/test_closure_recorder.py",
        "tests/test_workflow_documentation.py",
        "tests/test_navigator_graph_lifecycle.py",
        "tests/test_code_graph_inventory.py",
        "tests/test_execution_evidence.py",
        "tests/test_planning_lock.py",
        "tests/test_navigator_scope.py",
        "scripts/learning-use-receipt.py",
        "tests/test_task_type_contract.py",
        "tests/test_workflow_template_execution.py",
        "tests/test_public_route_gate.py",
        "tests/test_sequential_pipeline.py",
        "tests/test_tailtrail_registry.py",
        "scripts/meta-harness-analyze.py",
        "scripts/architecture-fitness.py",
        "tests/test_workflow_adapters.py",
        "scripts/aidlc-check.py",
        "scripts/execution-evidence.py",
        "scripts/closure-close.py",
        "tests/test_write_guardian.py",
        "scripts/host_contract.py",
        "scripts/task-start.py",
        "tests/test_code_graph_cache.py",
        "tests/test_workflow_phase7.py",
        "tests/test_host_adapter_conformance.py",
        "tests/test_review_scope.py",
        "tests/test_evaluation_audit.py",
        "tests/test_intake_pipeline.py",
        "scripts/closure-evaluation.py",
        "scripts/code_graph_cache.py",
        "tests/test_workflow_start_integration.py",
        "tests/test_workflow_ci_continuation.py",
        "scripts/navigator-scope-release.py",
        "scripts/navigator_discovery.py",
        "scripts/benchmark-tailtrail.py",
        "scripts/aidlc-official-install.py",
        "scripts/completion-report.py",
        "scripts/navigator.py",
        "hooks/hooks.json",
        "tests/test_requirement_routing_phase0.py",
        "tests/test_task_type_gate.py",
        "tests/test_host_question_flow_phase0_artifacts.py",
        "scripts/adoption-validation.py",
        "scripts/check-tailtrail.py",
        "scripts/host-adapter-conformance.py",
        "scripts/debug-host-diagnosis.py",
        "scripts/tailtrail.py",
        "tests/test_aidlc_official_bridge.py",
        "scripts/advanced-runtime.py",
        "tests/test_start_entrypoints.py",
        "scripts/change-intent-anchor.py",
        "tests/test_host_contract.py",
        "tests/test_host_input_contract_schema.py",
        "tests/test_greenfield_e2e.py",
        "scripts/official-aidlc-state.py",
        "scripts/install-local.py",
        "scripts/write_guardian.py",
        "tests/test_demo_prompt_book.py",
        "tests/test_workflow_contracts.py",
        "scripts/update-copilot.py",
        "tests/test_repository_path_policy.py",
        "tests/test_requirement_discovery.py",
        "tests/test_revision_proof_overlay.py",
        "scripts/debug-preflight.py",
        "scripts/planning-discussion.py",
        "scripts/planning-revision.py",
        "scripts/learning-agent.py",
        "tests/test_host_question_flow_event_schema.py",
        "tests/test_closure_finalizer.py",
        "tests/test_completion_review.py",
        "tests/test_aidlc_official_host.py",
        "scripts/architecture_planning.py",
        "tests/test_debug_start_planning.py",
        "scripts/planning-aidlc-question.py",
        "tests/test_debug_host_integration.py",
        "scripts/run-ledger.py",
        "tests/test_host_packet_tickets.py",
        "scripts/workflow_runtime/start_integration.py",
        "scripts/host-decision.py",
        "scripts/aidlc-requirements.py",
        "scripts/learning-refresh.py",
        "scripts/closure-contract.py",
        "tests/test_workflow_dashboard.py",
        "tests/test_workflow_privacy.py",
        "scripts/workflow_runtime/enterprise_transport.py",
        "tests/test_planning_revision.py",
        "scripts/closure-finalizer.py",
        "scripts/debug-completion.py",
        "schemas/host-input-contract.schema.json",
        "scripts/workflow_runtime/storage.py",
        "tests/test_enterprise_host_adapters.py",
        "scripts/behaviour_planning.py",
        "tests/test_mcp_server.py",
        "tests/test_new_file_due_diligence.py",
        "tests/test_install_profiles.py",
        "tests/test_full_pipeline.py",
        "scripts/debug-correction.py",
        "release-manifest.json",
        "tests/test_review_graph.py",
        "scripts/host-reply-validate.py",
        "scripts/verbose-reporting.py",
        "tests/test_navigator_core.py",
        "scripts/delivery-record.py",
        "scripts/aidlc-init.py",
        "scripts/code-graph-mapper.py",
        "scripts/install-copilot.py",
        "scripts/ast-map.py",
        "scripts/official-aidlc-checkpoint.py",
        "scripts/new_file_due_diligence.py",
        "tests/test_canonical_statement_contract.py",
        "tests/test_planning_audit.py",
        "scripts/planning_lock.py",
        "scripts/pipeline_orchestrator.py",
        "schemas/host-question-flow-event.schema.json",
        "scripts/official-aidlc-requirements.py",
        "scripts/planning-audit.py",
        "demo-project-layout/tailtrail-demo-workspace/services/claims-api/tests/test_validation.py",
        "scripts/navigator-scope.py",
        "tests/test_delivery_record.py",
        "tests/test_task_recovery.py",
        "tests/test_completion_report.py",
        "tests/test_workflow_approvals.py",
        "scripts/mcp-server.py",
        "scripts/navigator_scope.py",
        "pyproject.toml",
        "scripts/repository_path_policy.py",
        "scripts/aidlc-official-bridge.py",
        "scripts/question-orchestrator.py",
        "scripts/aidlc-official-detect.py",
        "scripts/docs-only.py",
        "scripts/debug-harness-convergence.py",
        "tests/test_navigator_installed_release.py",
        "scripts/review-graph.py",
        "buildweek-demo-project/src/claims_api/validation.py",
        "scripts/intake_pipeline.py",
        "scripts/greenfield_e2e_fixture.py",
        "tests/test_architecture_fitness.py"
      ],
      "status": "fresh"
    },
    "boundary": "Navigator may create or refresh TailTrail graph metadata; current-source scope evidence and Planning Lock approval remain mandatory.",
    "cache_fingerprint": "sha256:abd54e1f4025baafe50fb720deb9701dbc1990caff61520d87d4cf7db72f4b7c",
    "cache_path": "tailtrail-meta/code-graph-cache.json",
    "cache_reuse_state": null,
    "cache_shape": "mapper",
    "cache_warnings": [
      "legacy v1 mapper shape; migrates to a v2 container on next Phase-1 write"
    ],
    "fingerprint": "sha256:6c7ff1b166da2ba52184aea47a9f64d98c3c6c54ee4a02a3a71acc8ede3511c8",
    "freshness": "fresh",
    "implementation_authority": false,
    "metadata_only": true,
    "outside_slice_nominations": [],
    "phase": "closure",
    "reason_codes": [
      "explicit-scope-paths",
      "fresh-relevant-graph-reused"
    ],
    "relevance": "not-evaluated",
    "requested_mode": "auto",
    "schema_version": "1",
    "target_paths": [
      "scripts/closure-finalizer.py",
      "scripts/completion-report.py",
      "scripts/planning-audit.py",
      "scripts/planning-revision.py",
      "scripts/planning_lock.py",
      "scripts/verbose-reporting.py",
      "tests/test_closure_finalizer.py",
      "tests/test_completion_report.py",
      "tests/test_planning_audit.py",
      "tests/test_planning_lock.py",
      "tests/test_planning_revision.py"
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
        "requirement_uid": "req-ad541812658a",
        "tier": "contract"
      },
      {
        "requirement_uid": "req-ad541812658a",
        "tier": "integration"
      },
      {
        "requirement_uid": "req-92b0573b5b3e",
        "tier": "contract"
      },
      {
        "requirement_uid": "req-92b0573b5b3e",
        "tier": "integration"
      }
    ],
    "status": "pass"
  },
  "ledger_events": [
    {
      "created_at": "2026-10-19T10:30:03+00:00",
      "event_id": "evt-0001-48758a803458296f",
      "event_type": "run_created",
      "payload": {
        "goal": "Generate visible full verbose session reports without fabricated metrics: the start report includes every saved planning field, AIDLC questions and answers when present, scope, requirements, controls, proof, and token estimates with provenance; the closure report includes changed files and locations, execution events, commands, outcomes, durations, evidence, harnesses, drift, token usage, and unavailable markers; preserve canonical internal copies."
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 1,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:30:03+00:00",
      "event_id": "evt-0002-0501e3a83b8d0785",
      "event_type": "planning_lock_created",
      "payload": {
        "artifact": "planning/lock-v1.json",
        "input_roles": {
          "read_only_inputs": 0
        },
        "reference_roots": [],
        "target_fingerprint": "sha256:0db1e1abf14c7efedec8229d88190380f977e2a75fd5e74d53df5292a2f2a06c",
        "writes_allowed": false
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 2,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:30:03+00:00",
      "event_id": "evt-0003-74f672e3ce167b58",
      "event_type": "target_resolution_recorded",
      "payload": {
        "policy_status": "not-configured",
        "target_resolution_receipt": ".tailtrail/runs/start-20261019102950-bc8789/planning/target-resolution-receipt-v1.json"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 3,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:30:03+00:00",
      "event_id": "evt-0004-268ec2714f991d63",
      "event_type": "start_report_saved",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/start-report-v1.json"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 4,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:30:03+00:00",
      "event_id": "evt-0005-a9e1f9636e66041d",
      "event_type": "tailtrail_session_attached",
      "payload": {
        "context_key_hash": "sha256:8f7ea5b4e0bf204739b270db4b34f3ff3560126663ca15a47c97490c5a4c8b70",
        "fingerprint": "sha256:2ea96280b391162e9b4daf1cc88c6be3e9d4f2da97c322b7eb25bc4940e4f568",
        "generation": 244,
        "reason_code": "tailtrail-start"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 5,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:31:17+00:00",
      "event_id": "evt-0006-270ec1aaf6d59153",
      "event_type": "planning_revision_proposed",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/revisions/revision-v2.json",
        "base_revision": 1,
        "requirement_uids": [
          "req-ad541812658a"
        ],
        "revision": 2
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 6,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:31:35+00:00",
      "event_id": "evt-0007-0282c28adfd368ff",
      "event_type": "planning_revision_superseded",
      "payload": {
        "replacement_artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/revisions/revision-v3.json",
        "revision": 2,
        "superseded_by": 3
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 7,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:31:35+00:00",
      "event_id": "evt-0008-c0088ddef2dc7469",
      "event_type": "planning_revision_proposed",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/revisions/revision-v3.json",
        "base_revision": 1,
        "requirement_uids": [
          "req-ad541812658a",
          "req-ad541812658a"
        ],
        "revision": 3
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 8,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:36:23+00:00",
      "event_id": "evt-0009-e832f85ac12f00f0",
      "event_type": "anchor_drafted",
      "payload": {
        "fingerprint": "sha256:6827a3bd6ce8f5e9a39d85a470cb2d8d57e19facecc015481b927adc62289628",
        "proposal_version": 1,
        "requirements": [
          "req-725005193320",
          "req-ad541812658a",
          "req-92b0573b5b3e",
          "req-6f5a5f850524"
        ]
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 9,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:36:23+00:00",
      "event_id": "evt-0010-ea4ec7a0fcdc3fdf",
      "event_type": "proposal_rejected",
      "payload": {
        "feedback": [
          {
            "comment": "Do not create a reconstructed summary. Generate the visible file from the actual complete verbose Start Plan at planning time, before implementation, regardless of the selected display verbosity.",
            "decision": "reject",
            "requirement_uid": "req-725005193320"
          },
          {
            "comment": "The actual Start Plan document must contain every saved planning detail: complete requirements, questions and answers, AIDLC stages and decisions when used, scope roles and evidence, controls, proof, risks, token provenance, open questions, and approval state.",
            "decision": "reject",
            "requirement_uid": "req-ad541812658a"
          },
          {
            "comment": "Do not create any closure document before closure is finalized. After real finalization, generate it from factual execution data including exact changes and locations, commands, outcomes, durations, evidence, harnesses, drift, token usage, failures, corrections, and unavailable markers.",
            "decision": "reject",
            "requirement_uid": "req-92b0573b5b3e"
          },
          {
            "comment": "Preserve canonical internal evidence, but the visible Start and Closure files must be lifecycle-authentic projections of that evidence rather than parallel summaries.",
            "decision": "reject",
            "requirement_uid": "req-6f5a5f850524"
          }
        ],
        "next_requirement_mode": "ask-targeted-questions-or-offer-aidlc",
        "proposal_version": 1,
        "rejected_requirement_uids": [
          "req-725005193320",
          "req-ad541812658a",
          "req-92b0573b5b3e",
          "req-6f5a5f850524"
        ]
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 10,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:36:23+00:00",
      "event_id": "evt-0011-e7460b52054211b6",
      "event_type": "host_decision_recorded",
      "payload": {
        "artifact": "decisions/decisions-v1.jsonl",
        "decision": "feedback-recorded",
        "decision_id": "sha256:1efce0b73af5076df9b21ba7031a37c4f7be0b9e195ae679ad1e5597bffe65a6",
        "verb": "revise"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 11,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:36:42+00:00",
      "event_id": "evt-0012-b9efbaff4d3d2d70",
      "event_type": "proposal_rejected",
      "payload": {
        "feedback": [
          {
            "comment": "User rejected reconstructed summaries and requires lifecycle-authentic full verbose Start and post-finalization Closure documents.",
            "decision": "reject",
            "requirement_uid": "req-725005193320"
          },
          {
            "comment": "User rejected reconstructed summaries and requires lifecycle-authentic full verbose Start and post-finalization Closure documents.",
            "decision": "reject",
            "requirement_uid": "req-ad541812658a"
          },
          {
            "comment": "User rejected reconstructed summaries and requires lifecycle-authentic full verbose Start and post-finalization Closure documents.",
            "decision": "reject",
            "requirement_uid": "req-92b0573b5b3e"
          },
          {
            "comment": "User rejected reconstructed summaries and requires lifecycle-authentic full verbose Start and post-finalization Closure documents.",
            "decision": "reject",
            "requirement_uid": "req-6f5a5f850524"
          }
        ],
        "next_requirement_mode": "aidlc-requirements-required",
        "proposal_version": 1,
        "rejected_requirement_uids": [
          "req-725005193320",
          "req-ad541812658a",
          "req-92b0573b5b3e",
          "req-6f5a5f850524"
        ]
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 12,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:36:42+00:00",
      "event_id": "evt-0013-10f91996e4300589",
      "event_type": "host_decision_recorded",
      "payload": {
        "artifact": "decisions/decisions-v1.jsonl",
        "decision": "feedback-recorded",
        "decision_id": "sha256:478ca019db64dcc5550d8963fc278d08d2b70c176d96ac21cb5b8cb22fa3de4b",
        "verb": "revise"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 13,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:44:39+00:00",
      "event_id": "evt-0014-e5e670979374d531",
      "event_type": "proposal_rejected",
      "payload": {
        "feedback": [
          {
            "comment": "AUTHORITATIVE FULL REQUIREMENT: Generate the visible Start Plan from the actual saved pre-approval plan, always in full verbose mode regardless of selected display verbosity. It must be the real plan artifact, never a later reconstruction or summary.",
            "decision": "reject",
            "requirement_uid": "req-725005193320"
          },
          {
            "comment": "AUTHORITATIVE START CONTENT: Include every saved planning detail: complete requirement statements and verification criteria, interpretation provenance, all AIDLC stages/questions/options/recommendations/answers/decisions when AIDLC is used, scope owners/inspection/proof/excluded roles and evidence, architecture and behavior contracts, selected and conditional TailTrail controls, proof commands and tiers, risks, dependencies, assumptions, open questions, approval history/state, plan revisions/audits, token estimates and provenance, and visible absolute/workspace-relative report path.",
            "decision": "reject",
            "requirement_uid": "req-ad541812658a"
          },
          {
            "comment": "AUTHORITATIVE CLOSURE TIMING AND CONTENT: Do not create any Closure Report until execution and real closure finalization are complete. Then include every factual execution detail: exact changes and where they occurred, files/symbols/locations, commands, outputs/outcomes/exit codes/durations, receipts/evidence, requirement-by-requirement verification and what was done, failures and corrections, tests and harness results, TailTrail controls/lifecycle/events, scope drift, architecture/behavior/maintainability/security health checks, token usage by phase when measured, estimates with provenance when not measured, unavailable markers, blockers, residual risks, overall status, final health summary, and visible absolute/workspace-relative report path. Never fabricate counts, coverage, tokens, pass states, or deployment readiness.",
            "decision": "reject",
            "requirement_uid": "req-92b0573b5b3e"
          },
          {
            "comment": "AUTHORITATIVE PRESERVATION: Preserve canonical internal TailTrail artifacts and evidence. Visible Start and Closure documents must be complete lifecycle-authentic projections from those records, redact secrets/private reasoning, and label unavailable facts rather than inventing them.",
            "decision": "reject",
            "requirement_uid": "req-6f5a5f850524"
          }
        ],
        "next_requirement_mode": "aidlc-requirements-required",
        "proposal_version": 1,
        "rejected_requirement_uids": [
          "req-725005193320",
          "req-ad541812658a",
          "req-92b0573b5b3e",
          "req-6f5a5f850524"
        ]
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 14,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:44:39+00:00",
      "event_id": "evt-0015-7805099864301c45",
      "event_type": "host_decision_recorded",
      "payload": {
        "artifact": "decisions/decisions-v1.jsonl",
        "decision": "feedback-recorded",
        "decision_id": "sha256:73b8316e745f0b3a788cc6f0f5b09c46aee6c1bde5ba10679012a3d313172cf4",
        "verb": "revise"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 15,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:47:09+00:00",
      "event_id": "evt-0016-47b0439c6da83870",
      "event_type": "planning_revision_superseded",
      "payload": {
        "reason": "AIDLC Requirements mode required after repeated requirement rejection",
        "replacement_artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/revisions/revision-v4.json",
        "revision": 3,
        "superseded_by": 4
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 16,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:47:09+00:00",
      "event_id": "evt-0017-c2810a77ed5714f7",
      "event_type": "planning_aidlc_mode_switch_proposed",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/revisions/revision-v4.json",
        "from_mode": "lite",
        "revision": 4,
        "to_mode": "standard"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 17,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:49:54+00:00",
      "event_id": "evt-0018-e495bb0e530f9d9c",
      "event_type": "planning_aidlc_mode_switch_fell_back",
      "payload": {
        "from_mode": "lite",
        "reason": "Official AIDLC Standard is unavailable because no compatible pinned pack is installed. TailTrail Lite remains available; no local AIDLC questionnaire will be presented as official.",
        "requested_mode": "standard",
        "revision": 4
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 18,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:51:32+00:00",
      "event_id": "evt-0019-61f0b4e98a30e777",
      "event_type": "question_context_prepared",
      "payload": {
        "aidlc_mode": "lite",
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/question-context-v1.json",
        "known_fact_count": 7,
        "question_authority": "local-lite",
        "unknown_count": 3
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 19,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:51:32+00:00",
      "event_id": "evt-0020-9a4f7e621b742a60",
      "event_type": "aidlc_requirements_requested",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-requirements-v1.json",
        "reason": "user-selected-aidlc-requirements",
        "rejection_number": 4,
        "revision_context_count": 0
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 20,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:55:53+00:00",
      "event_id": "evt-0021-ef6dd5acae662516",
      "event_type": "aidlc_correction_projection_blocked",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-observations-v1.json",
        "material_question_ids": [
          "Q3",
          "Q4"
        ],
        "reason_code": "validated-correction-projection-required",
        "state_artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-state.json",
        "version": 1
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 21,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:56:51+00:00",
      "event_id": "evt-0022-24cf0441b7520ad4",
      "event_type": "aidlc_requirements_answered",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-revised-requirements-v1.json",
        "changed_surfaces": [
          "requirements",
          "validation"
        ],
        "projection": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-projection-v1.json",
        "projection_version": 1,
        "question_ids": [
          "Q1",
          "Q2",
          "Q3",
          "Q4"
        ],
        "revision_version": 1,
        "state_artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-state.json",
        "status": "revision-ready"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 22,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T10:59:16+00:00",
      "event_id": "evt-0023-ffbc61868b9c193c",
      "event_type": "aidlc_requirements_answered",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-revised-requirements-v2.json",
        "changed_surfaces": [
          "requirements",
          "validation"
        ],
        "projection": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-projection-v2.json",
        "projection_version": 2,
        "question_ids": [
          "Q1",
          "Q2",
          "Q3",
          "Q4"
        ],
        "revision_version": 2,
        "state_artifact": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-correction-state.json",
        "status": "revision-ready"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 23,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:01:33+00:00",
      "event_id": "evt-0024-3e257b8cd66ad32c",
      "event_type": "anchor_drafted",
      "payload": {
        "fingerprint": "sha256:67edc1a807a90fa2a669ec3af5836cd699f845486d5a6cf94bef4f5b472abc10",
        "proposal_version": 2,
        "requirements": [
          "req-725005193320",
          "req-ad541812658a",
          "req-92b0573b5b3e",
          "req-6f5a5f850524"
        ]
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 24,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:01:33+00:00",
      "event_id": "evt-0025-6589c31a3f3cee96",
      "event_type": "anchor_approved",
      "payload": {
        "fingerprint": "sha256:b7aba596297b86b995574a7034e67f42c8d2131ea6fa969fa680ed373278691a",
        "path": ".tailtrail/runs/start-20261019102950-bc8789/anchors/approved-v1.json",
        "requirements": [
          "req-725005193320",
          "req-ad541812658a",
          "req-92b0573b5b3e",
          "req-6f5a5f850524"
        ]
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 25,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:26+00:00",
      "event_id": "evt-0026-506292416a503ec5",
      "event_type": "planning_lock_approved",
      "payload": {
        "artifact": "planning/lock-v1.json",
        "audit": {
          "report_fingerprint": "sha256:e0b0b546d8179b1cb7c1b7774d89ae463d792c2283086eb9fdb9b7b42118edb2",
          "run_id": "start-20261019102950-bc8789",
          "source": "validated-aidlc-revision",
          "status": "clean"
        },
        "writes_allowed": true
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 26,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:26+00:00",
      "event_id": "evt-0027-8cacf6b000608be2",
      "event_type": "host_decision_recorded",
      "payload": {
        "artifact": "decisions/decisions-v1.jsonl",
        "decision": "approved",
        "decision_id": "sha256:40a47aad16f8f5d9c8da64292f2856e53677a247fe1cc544d9098f483b250f14",
        "verb": "approve"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 27,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:32+00:00",
      "event_id": "evt-0028-02792a1be9b42939",
      "event_type": "workflow_ownership_bound",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-35991103ad64/ownership-v1.json",
        "requirement_uids": [
          "req-725005193320",
          "req-ad541812658a",
          "req-92b0573b5b3e",
          "req-6f5a5f850524"
        ],
        "workflow_id": "ttw-35991103ad64"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 28,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:33+00:00",
      "event_id": "evt-0029-096199217bb00680",
      "event_type": "workflow_capability_plan_declared",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-35991103ad64/capability-plan-v1.json",
        "capability_ids": [
          "code-graph-mapper",
          "guardrails",
          "navigator",
          "review",
          "testing"
        ],
        "plan_fingerprint": "sha256:67535af29c2e2f109c9ec823304a1e18096e215f42da1dc32d9289435973f52e",
        "workflow_id": "ttw-35991103ad64"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 29,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:34+00:00",
      "event_id": "evt-0030-520c6b3d81f19a39",
      "event_type": "workflow_storage_initialized",
      "payload": {
        "journal": ".tailtrail/workflows/ttw-35991103ad64/journal-v1.jsonl",
        "projection": ".tailtrail/workflows/ttw-35991103ad64/projection-v1.json",
        "workflow_id": "ttw-35991103ad64"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 30,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:34+00:00",
      "event_id": "evt-0031-3948a0df90c718b3",
      "event_type": "workflow_state_created",
      "payload": {
        "journal": ".tailtrail/workflows/ttw-35991103ad64/journal-v1.jsonl",
        "sequence": 2,
        "workflow_id": "ttw-35991103ad64"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 31,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:44+00:00",
      "event_id": "evt-0032-657f38e9362bf76c",
      "event_type": "workflow_compiler_plan_created",
      "payload": {
        "artifact": ".tailtrail/workflows/ttw-35991103ad64/compiler-plan-v1.json",
        "plan_fingerprint": "sha256:70488ba40735c1396f505579d8bc68142050eb1c8af84f61ed08835389e09d44",
        "revision": 1,
        "template_id": "small-change",
        "workflow_id": "ttw-35991103ad64"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 32,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:44+00:00",
      "event_id": "evt-0033-a64c5f32a66c59ed",
      "event_type": "workflow_stage_approval_recorded",
      "payload": {
        "action_classes": [
          "write_tailtrail_state"
        ],
        "approval_id": "wfauth-d858bc85117822842520a14e",
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
        "workflow_id": "ttw-35991103ad64"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 33,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:44+00:00",
      "event_id": "evt-0034-378913feff199d66",
      "event_type": "workflow_stage_approval_recorded",
      "payload": {
        "action_classes": [
          "execute_project",
          "read_local",
          "write_project",
          "write_tailtrail_state"
        ],
        "approval_id": "wfauth-3f39ecc2229a522a0b69ca68",
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
        "workflow_id": "ttw-35991103ad64"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 34,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:44+00:00",
      "event_id": "evt-0035-91f6c9b43820a2a7",
      "event_type": "workflow_runtime_activated",
      "payload": {
        "binding": ".tailtrail/workflows/ttw-35991103ad64/ownership-v1.json",
        "capability_plan": ".tailtrail/workflows/ttw-35991103ad64/capability-plan-v1.json",
        "compiler_plan": ".tailtrail/workflows/ttw-35991103ad64/compiler-plan-v1.json",
        "compiler_plan_fingerprint": "sha256:70488ba40735c1396f505579d8bc68142050eb1c8af84f61ed08835389e09d44",
        "workflow_id": "ttw-35991103ad64"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 35,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:44+00:00",
      "event_id": "evt-0036-57d7898fac880d6e",
      "event_type": "aidlc_requirements_approved",
      "payload": {
        "anchor": ".tailtrail/runs/start-20261019102950-bc8789/anchors/approved-v1.json",
        "handoff": ".tailtrail/runs/start-20261019102950-bc8789/planning/execution-handoff-v1.json",
        "revision": ".tailtrail/runs/start-20261019102950-bc8789/planning/aidlc-revised-requirements-v2.json"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 36,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:04:44+00:00",
      "event_id": "evt-0037-1a4d6beb3c92a59f",
      "event_type": "planning_activated",
      "payload": {
        "anchor": {
          "artifact": ".tailtrail/runs/start-20261019102950-bc8789/anchors/approved-v1.json",
          "status": "created-from-aidlc"
        },
        "workflow_runtime": "compiled"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 37,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:14:20+00:00",
      "event_id": "evt-0038-8c247bb3bef57b10",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
        "fingerprint": "cc763f6cb383ec6f",
        "kind": "command-result",
        "sequence": 1
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 38,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:14:43+00:00",
      "event_id": "evt-0039-9c11f34c6656374b",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
        "fingerprint": "b28db5d40b5033c4",
        "kind": "command-result",
        "sequence": 2
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 39,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:15:26+00:00",
      "event_id": "evt-0040-e68c84ca81d1ecb3",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
        "fingerprint": "3bad972b314686c0",
        "kind": "command-result",
        "sequence": 3
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 40,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:17:24+00:00",
      "event_id": "evt-0041-4d97c6ffad1c0190",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
        "fingerprint": "220fcc56a6eadcc7",
        "kind": "command-result",
        "sequence": 4
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 41,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:17:37+00:00",
      "event_id": "evt-0042-30fb55f1f892d38a",
      "event_type": "start_plan_verbose_generated",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/verbose-reports/start-plan-verbose-v1.md",
        "mandatory": true,
        "markdown_size": 1804882,
        "status": "verified",
        "visible_absolute_path": "/Users/vsingha7/Desktop/tailr/session-reports/start-20261019102950-bc8789/start-plan.md",
        "visible_artifact": "session-reports/start-20261019102950-bc8789/start-plan.md"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 42,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:17:58+00:00",
      "event_id": "evt-0043-ca2165da22e6f622",
      "event_type": "harness_checkpoint",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/checkpoints/checkpoint-1.json",
        "checkpoint": 1,
        "drift": [
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-725005193320"
          },
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-ad541812658a"
          },
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-92b0573b5b3e"
          },
          {
            "category": "evidence",
            "classification": "resolved",
            "requirement_uid": "req-6f5a5f850524"
          },
          {
            "category": "scope",
            "classification": "new-drift",
            "message": "actual edit `scripts/planning-audit.py` is outside approved editable scope",
            "path": "scripts/planning-audit.py",
            "requirement_uid": "req-725005193320"
          },
          {
            "category": "scope",
            "classification": "new-drift",
            "message": "actual edit `scripts/planning-revision.py` is outside approved editable scope",
            "path": "scripts/planning-revision.py",
            "requirement_uid": "req-725005193320"
          },
          {
            "category": "scope",
            "classification": "new-drift",
            "message": "actual edit `tests/test_completion_report.py` is outside approved editable scope",
            "path": "tests/test_completion_report.py",
            "requirement_uid": "req-725005193320"
          },
          {
            "category": "scope",
            "classification": "new-drift",
            "message": "actual edit `tests/test_planning_audit.py` is outside approved editable scope",
            "path": "tests/test_planning_audit.py",
            "requirement_uid": "req-725005193320"
          },
          {
            "category": "scope",
            "classification": "new-drift",
            "message": "actual edit `tests/test_planning_lock.py` is outside approved editable scope",
            "path": "tests/test_planning_lock.py",
            "requirement_uid": "req-725005193320"
          }
        ],
        "requirement_states": {
          "req-6f5a5f850524": "validated",
          "req-725005193320": "validated",
          "req-92b0573b5b3e": "validated",
          "req-ad541812658a": "validated"
        }
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 43,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:18:11+00:00",
      "event_id": "evt-0044-980b4efb14ed977d",
      "event_type": "completion_review",
      "payload": {
        "artifact": "reviews/review-1.json",
        "checkpoint": 1,
        "complete": false,
        "findings": 5
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 44,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:18:11+00:00",
      "event_id": "evt-0045-5c5736b82cb01c5b",
      "event_type": "completion_gate",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/completion-gates/gate-1.json",
        "complete": true,
        "findings": []
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 45,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:18:11+00:00",
      "event_id": "evt-0046-c9c4f615f34f0164",
      "event_type": "closure_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/closure-records/closure-517e4b006ea4ca92.json",
        "checkpoint": 1,
        "gate_complete": true,
        "receipt_count": 3,
        "record_id": "closure-517e4b006ea4ca92",
        "review_complete": false
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 46,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:18:50+00:00",
      "event_id": "evt-0047-bfe1be3f303524f2",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
        "fingerprint": "1c9afaed2c28e2c7",
        "kind": "command-result",
        "sequence": 5
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 47,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:18:58+00:00",
      "event_id": "evt-0048-95345542727a01f6",
      "event_type": "harness_checkpoint",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/checkpoints/checkpoint-2.json",
        "checkpoint": 2,
        "drift": [
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-725005193320"
          },
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-ad541812658a"
          },
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-92b0573b5b3e"
          },
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-6f5a5f850524"
          }
        ],
        "requirement_states": {
          "req-6f5a5f850524": "validated",
          "req-725005193320": "validated",
          "req-92b0573b5b3e": "validated",
          "req-ad541812658a": "validated"
        }
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 48,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:18:58+00:00",
      "event_id": "evt-0049-9fc8bc82ded68144",
      "event_type": "completion_review",
      "payload": {
        "artifact": "reviews/review-2.json",
        "checkpoint": 2,
        "complete": true,
        "findings": 0
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 49,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:18:58+00:00",
      "event_id": "evt-0050-8877f3e56601ab90",
      "event_type": "completion_gate",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/completion-gates/gate-2.json",
        "complete": true,
        "findings": []
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 50,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:18:58+00:00",
      "event_id": "evt-0051-86ea41358078e0ed",
      "event_type": "closure_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/closure-records/closure-a2eaa78720d86107.json",
        "checkpoint": 2,
        "gate_complete": true,
        "receipt_count": 3,
        "record_id": "closure-a2eaa78720d86107",
        "review_complete": true
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 51,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:19:07+00:00",
      "event_id": "evt-0052-e8efa1e88cda4968",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 52,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:19:17+00:00",
      "event_id": "evt-0053-68e48e3815582add",
      "event_type": "navigator_graph_lifecycle_recorded",
      "payload": {
        "action": "refresh",
        "cache_fingerprint": "sha256:abd54e1f4025baafe50fb720deb9701dbc1990caff61520d87d4cf7db72f4b7c",
        "mapping_fingerprint": "sha256:7890b30c8de2d94b9c2714410e3731d101d1ee4ee85a5e9f856439f1feda86aa",
        "phase": "closure"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 53,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:19:46+00:00",
      "event_id": "evt-0054-895e11973991c2ea",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 54,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:22:31+00:00",
      "event_id": "evt-0055-eeba8567e9ad24af",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
        "fingerprint": "a2455abb95524f99",
        "kind": "command-result",
        "sequence": 6
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 55,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:22:41+00:00",
      "event_id": "evt-0056-4b387dd8b0acf901",
      "event_type": "harness_checkpoint",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/checkpoints/checkpoint-3.json",
        "checkpoint": 3,
        "drift": [
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-725005193320"
          },
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-ad541812658a"
          },
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-92b0573b5b3e"
          },
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-6f5a5f850524"
          }
        ],
        "requirement_states": {
          "req-6f5a5f850524": "validated",
          "req-725005193320": "validated",
          "req-92b0573b5b3e": "validated",
          "req-ad541812658a": "validated"
        }
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 56,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:22:41+00:00",
      "event_id": "evt-0057-01885fbe99833129",
      "event_type": "completion_review",
      "payload": {
        "artifact": "reviews/review-3.json",
        "checkpoint": 3,
        "complete": true,
        "findings": 0
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 57,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:22:41+00:00",
      "event_id": "evt-0058-960744ff161c6491",
      "event_type": "completion_gate",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/completion-gates/gate-3.json",
        "complete": true,
        "findings": []
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 58,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:22:41+00:00",
      "event_id": "evt-0059-6f442757c6417a10",
      "event_type": "closure_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/closure-records/closure-f577e5823f4ec7bd.json",
        "checkpoint": 3,
        "gate_complete": true,
        "receipt_count": 3,
        "record_id": "closure-f577e5823f4ec7bd",
        "review_complete": true
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 59,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:22:44+00:00",
      "event_id": "evt-0060-c57803f109262678",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 60,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:22:47+00:00",
      "event_id": "evt-0061-52634dbc085c7f62",
      "event_type": "navigator_graph_lifecycle_recorded",
      "payload": {
        "action": "reuse",
        "cache_fingerprint": "sha256:abd54e1f4025baafe50fb720deb9701dbc1990caff61520d87d4cf7db72f4b7c",
        "mapping_fingerprint": "sha256:7890b30c8de2d94b9c2714410e3731d101d1ee4ee85a5e9f856439f1feda86aa",
        "phase": "closure"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 61,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:22:56+00:00",
      "event_id": "evt-0062-7f98f0b3d73e6ac3",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-4.json",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 62,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:23:23+00:00",
      "event_id": "evt-0063-c8ad0384ed957d4c",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-5.json",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 63,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:23:59+00:00",
      "event_id": "evt-0064-c7612e669f23e6c8",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
        "fingerprint": "a81f7a654fd44a46",
        "kind": "source-edit",
        "sequence": 7
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 64,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:24:12+00:00",
      "event_id": "evt-0065-bca3cbfac5d5f7ab",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-6.json",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 65,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:24:15+00:00",
      "event_id": "evt-0066-5f66651ec522029a",
      "event_type": "navigator_graph_lifecycle_recorded",
      "payload": {
        "action": "reuse",
        "cache_fingerprint": "sha256:abd54e1f4025baafe50fb720deb9701dbc1990caff61520d87d4cf7db72f4b7c",
        "mapping_fingerprint": "sha256:7890b30c8de2d94b9c2714410e3731d101d1ee4ee85a5e9f856439f1feda86aa",
        "phase": "closure"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 66,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:24:32+00:00",
      "event_id": "evt-0067-144b82cf05a0df59",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-7.json",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 67,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:24:47+00:00",
      "event_id": "evt-0068-66c4da76fd4911f4",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-8.json",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 68,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:24:54+00:00",
      "event_id": "evt-0069-65f7d6800a6c7719",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-9.json",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 69,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:25:02+00:00",
      "event_id": "evt-0070-6457a336ff9a59c9",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-10.json",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 70,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:25:08+00:00",
      "event_id": "evt-0071-6487780e9baa7cb6",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-11.json",
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
        "overall_status": "evidence-incomplete"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 71,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:25:53+00:00",
      "event_id": "evt-0072-d286c457abcddd20",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
        "fingerprint": "d73866a486126ba0",
        "kind": "command-result",
        "sequence": 8
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 72,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:26:08+00:00",
      "event_id": "evt-0073-fc6bbc73569ba5b1",
      "event_type": "execution_evidence_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/execution/evidence-stream.jsonl",
        "fingerprint": "22340099eeb1eb07",
        "kind": "command-result",
        "sequence": 9
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 73,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:26:18+00:00",
      "event_id": "evt-0074-c6d6352d856255b5",
      "event_type": "harness_checkpoint",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/checkpoints/checkpoint-4.json",
        "checkpoint": 4,
        "drift": [
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-725005193320"
          },
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-ad541812658a"
          },
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-92b0573b5b3e"
          },
          {
            "category": "evidence",
            "classification": "unchanged",
            "requirement_uid": "req-6f5a5f850524"
          }
        ],
        "requirement_states": {
          "req-6f5a5f850524": "validated",
          "req-725005193320": "validated",
          "req-92b0573b5b3e": "validated",
          "req-ad541812658a": "validated"
        }
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 74,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:26:18+00:00",
      "event_id": "evt-0075-4825052daf0aab9b",
      "event_type": "completion_review",
      "payload": {
        "artifact": "reviews/review-4.json",
        "checkpoint": 4,
        "complete": true,
        "findings": 0
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 75,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:26:18+00:00",
      "event_id": "evt-0076-99ecf5617cfc2211",
      "event_type": "completion_gate",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/completion-gates/gate-4.json",
        "complete": true,
        "findings": []
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 76,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:26:18+00:00",
      "event_id": "evt-0077-f69b869387a5c22d",
      "event_type": "closure_recorded",
      "payload": {
        "artifact": ".tailtrail/runs/start-20261019102950-bc8789/closure-records/closure-717b25644d324265.json",
        "checkpoint": 4,
        "gate_complete": true,
        "receipt_count": 3,
        "record_id": "closure-717b25644d324265",
        "review_complete": true
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 77,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:26:28+00:00",
      "event_id": "evt-0078-a60532a074adffd1",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-12.json",
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
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 78,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:26:49+00:00",
      "event_id": "evt-0079-0bd4b7aa9a82a81e",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-13.json",
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
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 79,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:27:17+00:00",
      "event_id": "evt-0080-91ea7543f59e4591",
      "event_type": "completion_report_created",
      "payload": {
        "artifact": "completion-reports/report-14.json",
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
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 80,
      "type": "tailtrail-run-event"
    },
    {
      "created_at": "2026-10-19T11:27:19+00:00",
      "event_id": "evt-0081-a78a8a79ee0b6b47",
      "event_type": "navigator_graph_lifecycle_recorded",
      "payload": {
        "action": "reuse",
        "cache_fingerprint": "sha256:abd54e1f4025baafe50fb720deb9701dbc1990caff61520d87d4cf7db72f4b7c",
        "mapping_fingerprint": "sha256:1071bfc6f9d58f5ebdf32ed5921f9b9c5a330d2b5c327ab4dd423c3292a823dd",
        "phase": "closure"
      },
      "run_id": "start-20261019102950-bc8789",
      "schema_version": "1",
      "sequence": 81,
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
  "run_id": "start-20261019102950-bc8789",
  "run_mapping": {
    "closure_status": "complete",
    "goal_fingerprint": "sha256:9bf81733eba0c6797eaf046124347e47e121b7b28272dc929ccbcb3ff17f1a49",
    "graph_cache_fingerprint": "sha256:abd54e1f4025baafe50fb720deb9701dbc1990caff61520d87d4cf7db72f4b7c",
    "mapping_fingerprint": "sha256:1071bfc6f9d58f5ebdf32ed5921f9b9c5a330d2b5c327ab4dd423c3292a823dd",
    "path_hashes": {
      "scripts/closure-finalizer.py": "sha256:fb1f68154f9e4d6d740050714a135bdaa9b7969578222dbdf209ba57a42fa8bf",
      "scripts/completion-report.py": "sha256:422dc7db9a50818d742b427d56c80ac1e687b996dca1084d2047a04ce479f372",
      "scripts/planning-audit.py": "sha256:24fd4cc5f2506f44b36b4749fd1645b79a53ce790e0eaca0b759780fabfbfc7a",
      "scripts/planning-revision.py": "sha256:e6139b7f735ca79b1797d43cd35f231fb38c3e6747e9569870271926a9b11648",
      "scripts/planning_lock.py": "sha256:e540a21b7efd4f2538887730bbf42e35b426a597ba8eed436ed8cab847159240",
      "scripts/verbose-reporting.py": "sha256:db8e16758a2c0acce22eb9184685f4bb61ca2aa881c43119d053d6a7dbaa9ea1",
      "tests/test_closure_finalizer.py": "sha256:ef69f55dd937bd2c582a4bf35f5854fbbfdc990019da7b03f77ac51e415215d5",
      "tests/test_completion_report.py": "sha256:a0bfd34306204aaabb70c58b3708202b5025f8ed88448600df72b07d87a4421e",
      "tests/test_planning_audit.py": "sha256:1f9c5ff0197d47f9ba1b7eb4b841dd7f0cb594d0106a5ea22c0e3fd69cbf3fab",
      "tests/test_planning_lock.py": "sha256:c2e78c3931ed6f795627040c752e5b019c4f4ce4c4cb32565f17cd010b7ad1e7",
      "tests/test_planning_revision.py": "sha256:ab6a53e7366b9fcfa05d54017283fdb568579226f3de6cacf99f7c2bde89f777"
    },
    "query_terms": [
      "aidlc",
      "and",
      "answers",
      "canonical",
      "changed",
      "closure",
      "commands",
      "controls",
      "copies",
      "drift",
      "durations",
      "estimates",
      "events",
      "every",
      "evidence",
      "execution",
      "fabricated",
      "field",
      "files",
      "full",
      "generate",
      "harnesses",
      "includes",
      "internal",
      "locations",
      "markers",
      "metrics",
      "outcomes",
      "planning",
      "present",
      "preserve",
      "proof",
      "provenance",
      "questions",
      "report",
      "reports",
      "requirements",
      "saved",
      "scope",
      "session",
      "start",
      "the",
      "token",
      "unavailable",
      "usage",
      "verbose",
      "visible"
    ],
    "recorded_at": "2026-10-19T11:27:19.641380+00:00",
    "run_id": "start-20261019102950-bc8789",
    "scope_decision_fingerprint": "sha256:423bf1f63b17d9b0f90d195c6574c60ac30c604c691ad15ab032cb9aab035c95"
  },
  "schema_version": "1",
  "selected_harnesses": [
    "Canonical requirements",
    "Question Orchestrator",
    "Requirement Completion Harness",
    "Requirement-to-Impact Map",
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
      "lrn-ebe95e19a5a52ab1",
      "lrn-ebff1626a1e89a0a",
      "lrn-ef1b6215f75228f0",
      "lrn-f1ac3e1ab969782e",
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
  "workflow_closure": {
    "artifact": ".tailtrail/workflows/ttw-35991103ad64/completion-receipt-v1.json",
    "boundary": "Completion follows the canonical TailTrail Completion Report. An evidence-incomplete receipt is not a successful workflow completion and does not authorize a retry or recovery.",
    "completion_report": "/Users/vsingha7/Desktop/tailr/.tailtrail/runs/start-20261019102950-bc8789/completion-reports/report-14.json",
    "completion_status": "complete",
    "evidence_fingerprint": "sha256:002fd605061076eb3047b25d0fd089193a43c687081373294f69d68d23625004",
    "receipt_fingerprint": "sha256:f197ac92ca66ba122400e16a51bde82e7da2c9e608fdc58ef14072edf86d0c3d",
    "schema_version": "1",
    "state": "completed",
    "tailtrail_run_id": "start-20261019102950-bc8789",
    "type": "tailtrail-workflow-completion-receipt",
    "workflow_id": "ttw-35991103ad64"
  }
}
```

---

*End of full Closure execution record.*
