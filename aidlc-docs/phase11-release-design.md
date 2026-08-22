# Deferred Phase 11 Release-Proof Design

The runtime stores only sanitized, fingerprinted release evidence beneath
`.tailtrail/release-proof/`. Scenario observations are checked against a closed
15-scenario catalog and local canonical references. Real-run receipts bind one
workflow, approved run, target, compiler plan, template, completion receipt,
host receipts, requirement/preservation results, and calibrated categorical or
count metrics. They never execute a project or call a host/provider.

A read-only evaluator produces a release-gate report. It requires all scenarios,
all six templates, passed Codex/Copilot/Claude runtime conformance, no material
false-approval/duplicate/privacy/recovery issue, synchronized installed guidance,
documented compatibility and rollback, and a concise compatible Start surface.
The evaluator cannot retire compatibility. A controlled retirement decision is
accepted only against the exact current passing gate fingerprint and explicit
approval; otherwise `--no-workflow` remains available.

Migration assessment is read-only. It reports existing artifacts as authoritative
and records that automatic history migration and background conversion are off.
