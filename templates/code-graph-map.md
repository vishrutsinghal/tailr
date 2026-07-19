# TailTrail Code Graph Map

Use this shape when sharing Code Graph Mapper output in a review, handoff, or Navigator plan.

## Cache

- Cache path:
- Status:
- Mode:
- Confidence:
- Created:
- Updated:

## Scope

- Changed or target files:
- Scanner evidence files:
- Watched manifests/configs:

## Suggested Read Order

1. Exact changed or scanner-reported files.
2. Likely tests.
3. Likely callers.
4. Nearby manifests/configs.

## Graph Hints

- Symbols:
- References:
- Call-chain hints:
- Type hierarchy hints:
- Endpoints:
- DB tables:
- Config usage:
- Workspace overlays:

## Freshness

- Fresh when cached file hashes, watched manifests, scanner evidence, and task scope still match.
- Stale when any watched file changed, disappeared, moved, or falls outside the requested scope.
- Invalid when the cache cannot be parsed or required schema fields are missing.

## Boundaries

- This is metadata only, not a complete semantic graph.
- It does not store source snippets, secrets, raw prompts, full assistant responses, or raw scanner logs.
- It does not run Sonar, vulnerability scanners, tests, or CI commands.
- Exact source files must still be read before editing.
