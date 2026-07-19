# TailTrail Demo Project Layout

This folder is a planning scaffold for a future TailTrail demo project. It is not the demo application implementation.

The goal is to define a realistic enterprise-style project shape that can demonstrate TailTrail end to end without mixing demo code into the TailTrail product source.

## Demo Goal

Build a small but believable multi-service workspace that lets an audience see how TailTrail helps with:

- Navigator-first planning
- Code Graph Mapper and AST context reuse
- AIDLC lifecycle planning
- dependency decisions
- unit-test planning and validation confidence
- CI/Sonar-style issue triage
- vulnerability evidence parsing
- learning capture and guarded reuse
- token/value reporting
- handoff and review notes

## Proposed Demo Workspace

```text
tailtrail-demo-workspace/
  README.md
  DEMO-SCRIPT.md
  DEMO-DATA.md
  tailtrail/
  services/
    claims-api/
    eligibility-worker/
    notification-service/
  shared/
    validation-rules/
    sql/
  infra/
    terraform/
  ci/
    logs/
    scanner-results/
  docs/
    aidlc/
    architecture/
    handoff/
  .tailtrail/
```

## Why This Shape

The layout uses three small services plus shared SQL and Terraform because TailTrail is strongest when the task has enough surface area for planning, graphing, review, scanner triage, and handoff, but not so much code that the demo becomes hard to follow.

The services should be intentionally small. The demo should show decisions, workflow, and evidence quality rather than a large application.

## Demo Story

The primary story:

1. A user asks TailTrail Navigator to inspect the repo and plan a change.
2. Navigator recommends a compact path and asks for approval.
3. Code Graph Mapper creates or refreshes `tailtrail-meta/code-graph-cache.json`.
4. The user asks for a bug fix or quality-gate remediation.
5. TailTrail uses current source, graph context, policy, review lens, and test planner.
6. TailTrail prepares validation and handoff notes.
7. After acceptance, the user approves learning capture.
8. Reporting shows local value signals and token posture.

## Scope Boundaries

Do not build the application yet in this folder.

Do not vendor third-party code, generated scanner output from private systems, internal identifiers, real service names, real secrets, or real customer data.

When the demo is implemented later, keep all sample data synthetic and clearly marked as demo-only.

## Files In This Layout Folder

- `PROJECT-LAYOUT.md`: detailed folder-by-folder design.
- `DEMO-SCENARIOS.md`: demo scenarios and the TailTrail feature each scenario should exercise.
- `DATA-AND-EVIDENCE.md`: synthetic evidence files needed for scanner, CI, learning, and metrics demos.
- `BUILD-PHASES.md`: phased implementation plan for turning this layout into a working demo.
