# Demo Data And Evidence Plan

The demo project should use only synthetic evidence. This protects the demo from leaking real internal system names, customer data, secrets, scanner findings, or proprietary implementation details.

## Synthetic Data Needed

```text
demo-data/
  claims.csv
  eligibility-response.json
  invalid-claim-examples.json
```

Purpose:

- show realistic validation scenarios
- support unit-test examples
- avoid any real customer or production data

## CI Logs

```text
ci/logs/
  github-actions-failing-test.log
  sonar-quality-gate.log
  lint-output.log
```

Purpose:

- demonstrate CI/Sonar Intelligence
- keep the demo offline and deterministic
- let Navigator ask for approval before running any actual scan

## Structured Scanner Results

```text
ci/scanner-results/
  codeql.sarif
  trivy.json
  grype.json
```

Purpose:

- demonstrate SARIF parsing
- demonstrate Trivy/Grype parsing
- link findings to manifests, packages, services, or source files through graph overlays

## TailTrail Generated Evidence

```text
.tailtrail/
  code-graph-cache.json
  graph-learning-index.json
  learning-events.jsonl
  outcome-events.jsonl
  token-usage-events.jsonl
  value-report.md
```

Purpose:

- show how TailTrail reuses graph context
- show guarded learning capture
- show adoption and value signals

Keep runtime event files local by default. Commit only curated, synthetic fixtures that help the demo run.

## Privacy Rules

- no real names
- no real repo URLs
- no real service identifiers
- no secrets or fake secrets that look valid
- no raw prompts from real users
- no scanner output from real company systems
- no private dependency names

