# Demo Project Layout Details

This file defines the proposed demo workspace. It is meant to be reviewed before any demo code is written.

## Root

```text
tailtrail-demo-workspace/
  README.md
  DEMO-SCRIPT.md
  DEMO-DATA.md
  tailtrail/
  services/
  shared/
  infra/
  ci/
  docs/
  .tailtrail/
```

Purpose:

- `README.md`: quick orientation for people cloning the demo.
- `DEMO-SCRIPT.md`: presenter walkthrough with prompts, expected Navigator output shape, and talking points.
- `DEMO-DATA.md`: explanation of synthetic data and why no real internal data is included.
- `tailtrail/`: installed TailTrail pack, managed by installer/update commands.
- `.tailtrail/`: generated local TailTrail state for the demo run.

## Services

```text
services/
  claims-api/
    README.md
    src/
    tests/
    config/
    sonar-project.properties
  eligibility-worker/
    README.md
    src/
    tests/
    config/
  notification-service/
    README.md
    src/
    tests/
    config/
```

Purpose:

- `claims-api`: primary service for demo tasks. It should contain a small validation flow, one endpoint, one dependency decision point, and one quality issue.
- `eligibility-worker`: background worker used for cross-service graph and handoff examples.
- `notification-service`: reference service used for cross-repo/reference-style pattern comparison.

Suggested languages:

- `claims-api`: Python FastAPI or Java Spring Boot.
- `eligibility-worker`: Java or .NET worker.
- `notification-service`: .NET minimal API or Python service.

Keep the first implementation to one primary language if demo time is limited. Add multi-language services only after the Navigator, graph, scanner, and learning flows are clear.

## Shared

```text
shared/
  validation-rules/
    README.md
    claim-rules.json
  sql/
    migrations/
    queries/
```

Purpose:

- demonstrate shared validation logic and reuse-first TailTrail guidance
- give Code Graph Mapper SQL/table/config context
- support a small data-integrity or validation bug scenario

## Infrastructure

```text
infra/
  terraform/
    README.md
    modules/
    envs/
```

Purpose:

- demonstrate Terraform detection in Code Graph Mapper
- support a small config or secret-handling review scenario
- show that TailTrail can include infra context without turning every task into a full infra review

## CI And Scanner Evidence

```text
ci/
  logs/
    github-actions-failing-test.log
    sonar-quality-gate.log
  scanner-results/
    codeql.sarif
    trivy.json
    grype.json
```

Purpose:

- provide local, synthetic evidence for CI/Sonar Intelligence
- provide SARIF and Trivy/Grype JSON inputs for vulnerability demos
- avoid calling real CI, SonarQube, scanners, or networked services during the demo

## Docs

```text
docs/
  aidlc/
    initial-state.md
    requirements.md
    implementation-plan.md
    validation-handoff.md
  architecture/
    service-map.md
    data-flow.md
  handoff/
    pr-handoff-template.md
```

Purpose:

- show AIDLC artifacts without requiring a real enterprise project
- support review, handoff, and release-story prompts
- make the demo explainable for non-coders in the audience

## TailTrail State

```text
.tailtrail/
  code-graph-cache.json
  graph-learning-index.json
  learning-events.jsonl
  outcome-events.jsonl
  token-usage-events.jsonl
  quality-summary.md
  value-report.md
```

Purpose:

- show which files are generated locally by TailTrail
- demonstrate what should usually stay local versus what can be shared
- support before/after value and learning demos

In the actual demo repo, decide carefully which `.tailtrail/` files are committed. Suggested committed demo fixtures:

- small synthetic graph cache fixture
- sample value report
- sample learning index

Suggested ignored runtime files:

- raw local events
- user-specific install state
- temporary scanner summaries

