# Deferred Phase 11 Requirements

Implement every canonical Phase 11 requirement in
`DURABLE-WORKFLOW-RUNTIME-REVISED.md`: all 15 deterministic scenarios, one
sanitized real local-project proof for each of the six templates, Start-to-
closure host evidence, requirement/preservation proof, approval and false-
approval observations, stale/resume/duplicate/intervention/recovery/review/drift
metrics, estimated-versus-measured token coverage, migration and compatibility
assessment, and the seven-condition `--no-workflow` retirement gate.

The gate must remain blocked for missing, stale, incompatible, unlinked,
uncalibrated, or privacy-unsafe evidence. Existing commands and `.tailtrail`
artifacts remain authoritative; old history is not automatically migrated;
compatibility adapters and aliases cannot bypass authority. Retirement is a
separate explicit decision even after all evidence passes.

No dependency is required. Local JSON, standard-library hashing, existing host
conformance, workflow contracts, evidence, assurance, and installer/registry
helpers are the approved implementation basis.
