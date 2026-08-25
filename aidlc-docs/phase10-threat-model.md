# Deferred Phase 10 Threat Model

Untrusted inputs include MCP arguments, adapter results, CI receipts,
approvals, policies, workflow journals, completion/evidence links, telemetry,
learning/evaluation artifacts, host receipts, and local runtime JSON supplied
or modified after approval.

Protected assets are project source and manifests, approved requirements and
anchors, target/workflow identity, append-only state, authority records,
evidence and completion truth, credentials/private data, host stop rules,
retained local history, and the absence of unauthorized network/provider
activity.

Controls must reject or categorically quarantine hostile inputs, preserve the
last valid projection, record sanitized denial metadata only when a canonical
workflow already exists, and never reconstruct executable authority from
untrusted text.

## E7 STRIDE mapping and executable evidence

This section closes the "no formal threat model" gap identified for Phase E7
(`ENT-E7-002`). Each row names a concrete threat against the assets above, the
control that mitigates it, and the executable fixture that proves the control
fails closed. This is evidence, not aspiration: every "Proof" cell names a test
that actually runs in this repository. `tests/test_threat_model_stride.py`
re-exercises the highest-value cases as one consolidated E7 fixture pack;
the other proofs already existed and are cited rather than duplicated.

| STRIDE category | Concrete threat against a protected asset | Mitigating control | Proof |
| --- | --- | --- | --- |
| Spoofing | A forged or replayed approval/authority record is presented for a stage or workflow it was never issued for. | `workflow_runtime.approvals.authorize_stage` validates the approval belongs to the exact workflow, stage, and frozen plan fingerprint. | `tests/test_workflow_security.py::test_cases_1_3_4_forgery_annotation_and_cross_workflow_authority`, `tests/test_threat_model_stride.py::test_spoofed_cross_workflow_approval_is_rejected` |
| Tampering | The append-only journal is edited in place (sequence gap, duplicate line, hash rewrite, or truncated/interrupted write). | `workflow_runtime.storage._validate_events` verifies deterministic event IDs, hash chaining, and sequence continuity before any append or replay is trusted; corruption fails closed and the last valid projection is preserved. | `tests/test_workflow_negative.py::test_case_5_gap_duplicate_hash_and_interrupted_journals_preserve_projection`, `tests/test_workflow_storage.py::test_interrupted_journal_is_blocked_without_losing_last_projection`, `tests/test_threat_model_stride.py::test_tampered_journal_hash_fails_closed_and_preserves_projection` |
| Repudiation | An operator denies that a blocked action ever happened, or a denial audit is used to leak the hostile payload that triggered it. | `workflow_runtime.denials.record`/`show` persist only a categorical `reason_code` and `operation`, never the raw hostile input, so the audit trail is attributable without exposing sensitive content. | `tests/test_workflow_security.py::test_denied_mcp_action_records_only_categorical_audit`, `tests/test_threat_model_stride.py::test_denial_audit_never_retains_the_hostile_payload` |
| Information disclosure | A secret-shaped value (bearer token, GitHub PAT, private key) reaches an evidence artifact, denial audit, or exported report. | `scripts/repository-enforcement.py` redaction rule plus `workflow_runtime.denials`/`assurance` categorical-only recording. | `tests/test_repository_enforcement.py::test_every_core_rule_has_a_negative_fixture`, `tests/test_threat_model_stride.py::test_secret_shaped_value_is_never_persisted_in_evidence` |
| Denial of service | An oversized or malformed artifact (unbounded JSON, unknown schema type) is fed to a workflow contract to exhaust storage or crash validation. | `workflow_runtime.contracts` enforces closed schema types and a maximum artifact size and fails closed rather than partially processing the input. | `tests/test_workflow_contracts.py::test_malformed_unknown_private_unsafe_and_oversized_artifacts_fail_closed`, `tests/test_spec_kit_detect.py::test_oversized_artifact_is_incompatible_without_read_or_write_side_effects` |
| Elevation of privilege | An installed managed file is replaced with a symlink that points outside the install target, or a path-traversal string escapes the sandboxed root. | The transactional installer rejects symlinked managed paths and traversal-shaped targets before staging or applying any change. | `tests/test_transactional_installer.py::test_symlink_traversal_and_inaccessible_targets_fail_closed`, `tests/test_threat_model_stride.py::test_symlink_escape_and_path_traversal_fail_closed` |

## Residual risk (explicit, not hidden)

- These fixtures are deterministic unit-level proofs, not adversarial fuzzing,
  a third-party penetration test, or a human security review sign-off. They
  reduce known-shape risk; they do not certify the absence of unknown attack
  classes.
- Local concurrency is proven for same-process, same-host contention
  (`tests/test_workflow_concurrency.py`). Multi-host/multi-tenant concurrency
  (fencing, lease takeover) remains an Extended enterprise-provider concern
  covered separately by `tests/test_workflow_enterprise_transport.py`.
- This mapping documents Core-path threats only. Extended capabilities
  (graph mapping, learning, MCP transports beyond the Core surface) require
  their own threat-model addendum before they can claim the same status.
