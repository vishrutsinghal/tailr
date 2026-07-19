# Public Roadmap

This is the compressed public roadmap. The detailed internal planning history remains in `ROADMAP.md`.

## Now

- Source-only public release.
- One-command start flow through `python3 scripts/tailtrail.py start`.
- Local-first Navigator, AIDLC, guardrails, graph helpers, quality/vulnerability evidence summaries, learning governance, and reporting.
- Public release checks, claim guardrails, license/provenance metadata, and release mode separation.

## Next

- Fresh-clone smoke testing.
- Public issue and PR templates.
- Public documentation audit.
- Changelog and versioned tags.
- Public demo and architecture documentation.
- Support policy and security reporting finalization.

## Later

- Package distribution only if source-only usage shows demand.
- Optional deeper graph providers such as language-server, SCIP, Roslyn, or parser packages.
- Optional structured scanner formats beyond SARIF, Trivy JSON, and Grype JSON.
- Optional multi-repo report aggregation from user-supplied local reports.
- Optional exact token/cost reporting from user-provided measured telemetry.

## Not Planned By Default

- Hidden telemetry.
- Background service.
- Automatic prompt capture.
- Silent scanner execution.
- Hosted dashboard.
- Scanner replacement.
- Compliance or release approval replacement.
