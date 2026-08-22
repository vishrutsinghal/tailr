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
