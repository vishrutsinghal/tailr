# PM-L0 Learning Inventory And Ownership Design

## Architecture

The existing `maturity` command remains the single product-maturity control
plane. Its new `learning-inventory` subcommand builds the PM-L0 view from
declarative ownership tables in `scripts/product-maturity.py`. The committed
`tailtrail-meta/product-maturity-learning-inventory-v1.json` is the sealed
review and release artifact; `schemas/product-maturity-learning-inventory.schema.json`
is its closed interchange contract. This adds no top-level command, host, MCP
tool, dependency, or learning-store writer.

The model separates four concepts:

1. A **fact owner** controls the semantic record for one of the six PM-L0 fact
   classes.
2. An **artifact owner** controls mutation and lifecycle of a physical store.
3. A **writer** is an implementation caller and does not gain semantic
   ownership by delegating a write.
4. A **source-by-reference** or **domain-evidence** artifact remains owned by
   its producing subsystem and is never copied into learning as if learning
   owned the evidence.

## Canonical decisions

| Fact | Owner | Artifact | Delivery state |
| --- | --- | --- | --- |
| Candidate | Learning Agent | `.tailtrail/learning-events.jsonl` | Current |
| Curated learning | Learning Governance | `.tailtrail/learnings.md` | Current |
| Use receipt | Durable Workflow Runtime | run-local learning receipt stream | PM-L3 |
| Freshness action | Learning Refresh | `.tailtrail/learning-refresh-actions.json` | Current |
| Conflict | Learning Governance | `.tailtrail/learning-conflicts.jsonl` | PM-L4 |
| Observed outcome | Outcome Telemetry | `.tailtrail/outcome-events.jsonl` | Current |

The legacy `learnings.py` writer retains the same physical curated store and is
a compatibility route, not another owner. Closure learning preserves its
immutable run-local candidate and appends a sanitized candidate event. Debug,
graph, Quality Loop, Evaluation Harness, Meta-Harness, outcome, and workflow
artifacts retain their domain owners and are joined by reference in later
contracts.

## Validation and failure behavior

Validation is deterministic and offline. It checks the identity and seal,
exact fact and system sets, source/writer existence, unique artifact IDs,
single ownership per mutable path, resolvable migrations, semantic alias
protections, two-release windows, and preservation flags. PM-0 validation
includes PM-L0, so release assurance cannot pass while the ownership inventory
is missing or invalid.

The committed artifact, schema, lifecycle documents, command, and tests are
included in package and registry metadata. PM-L1 can therefore evolve the data
contract from an explicit owner and preservation boundary without rediscovering
or discarding legacy stores.
