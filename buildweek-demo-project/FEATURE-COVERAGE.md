# TailTrail Feature Coverage For Build Week

This page explains what the clean Build Week demo shows live and what TailTrail can do beyond the 3-minute walkthrough.

The demo intentionally focuses on one understandable workflow. TailTrail itself is broader.

## Live Demo Features

These are the features recommended for the main demo video.

| Feature | What The Demo Shows | Local Command |
|---|---|---|
| Navigator-first workflow | TailTrail plans before implementation and asks for approval. | `python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py` |
| Code Graph / Semantic V2 | TailTrail maps the target file, likely tests, references, and changed-symbol impact before editing. | `python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2` |
| Evidence labels | Graph output labels facts as `heuristic` or `local-ast`. | same graph command |
| Optional Semantic V3 | TailTrail ingests approved local provider JSON and labels facts as `provider-backed`. | `python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v3 --provider-output buildweek-demo-project/tailtrail-meta/providers/sample-semantic.json --approved` |
| Focused validation | The demo starts with one failing test and ends with that test passing after the fix. | `python3 -m unittest discover -s buildweek-demo-project/tests` |
| CI summary | TailTrail summarizes the exact failing command, test, and assertion from a CI log. | `python3 scripts/tailtrail.py ci summarize --file buildweek-demo-project/logs/ci-failure.log` |
| Post-change review | TailTrail review checks code health and requirement fulfillment after implementation. | `python3 scripts/tailtrail.py review --root buildweek-demo-project` |
| Evaluation Harness proof | TailTrail turns the Build Week story into a repeatable saved-artifact scenario with explicit claim boundaries. | `python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation` |
| Token/value honesty | TailTrail separates local estimates from measured model/API telemetry. | `python3 scripts/tailtrail.py report value --root buildweek-demo-project` |
| Local policy | The demo repo has `tailtrail-policy.md` with validation and dependency rules. | `buildweek-demo-project/tailtrail-policy.md` |

## Implemented Capabilities Not Shown In The Main Video

These features are implemented in TailTrail but should be mentioned briefly in the submission page or README, not forced into the 3-minute demo.

| Capability | Why It Matters | Example Command |
|---|---|---|
| AIDLC lifecycle | Helps broad, risky, regulated, or multi-team work move through requirements, design, implementation, validation, and handoff. | `python3 scripts/tailtrail.py aidlc init --root buildweek-demo-project --depth standard` |
| Dependency Gate | Prevents unnecessary packages and forces standard-library/platform-first reasoning. | `python3 scripts/tailtrail.py intent "use dependency gate"` |
| Guardrails | Catches weak claims, unsafe simplification, missing validation, and policy drift. | `python3 scripts/tailtrail.py guard check` |
| Guardrail precision benchmark | Measures false-positive behavior for guardrail rules. | `python3 scripts/tailtrail.py guardrail precision` |
| Test Precision Planner | Recommends focused test placement and plain-English test cases. | `python3 scripts/tailtrail.py test plan --root buildweek-demo-project --changed src/claims_api/validation.py --goal "fix zero amount validation"` |
| Quality Signal Scanner | Recommends local quality checks from repo manifests and runs only approved commands. | `python3 scripts/tailtrail.py quality scan --root buildweek-demo-project --changed src/claims_api/validation.py` |
| Vulnerability Intelligence | Summarizes scanner output and can plan or run approved vulnerability scans. | `python3 scripts/tailtrail.py vulnerability summarize --file buildweek-demo-project/logs/trivy-sample.json` |
| Code Graph Mapper cache | Stores shared graph context so future tasks can avoid starting from zero. | `python3 scripts/tailtrail.py graph map --root buildweek-demo-project --changed src/claims_api/validation.py` |
| Cross-Repo Reference Mode | Lets a target repo safely learn patterns from a sibling/reference repo without editing the reference repo. | `python3 scripts/tailtrail.py reference --target /path/to/target --reference /path/to/reference --goal "match validation style"` |
| Learning Agent V2 | Captures approved reusable repo learnings with confidence gates. | `python3 scripts/tailtrail.py learn review --root buildweek-demo-project` |
| Learning Refresh | Detects stale, noisy, or low-confidence learning patterns. | `python3 scripts/tailtrail.py learn refresh --root buildweek-demo-project` |
| Meta-Harness | Reviews TailTrail behavior after tasks and can propose evidence-gated product improvements. | `python3 scripts/tailtrail.py harness quick --root buildweek-demo-project` |
| Token Harness | Provides reversible receipts, structured reducers, append-only ledger, proof, and safe optional compression bridge. | `python3 scripts/tailtrail.py token-harness route --path buildweek-demo-project/logs/ci-failure.log` |
| Measured token telemetry | Imports real model/API usage so TailTrail can report exact measured savings when provided. | `python3 scripts/tailtrail.py telemetry manual --task-id demo-001 --provider openai --model gpt-5.6 --baseline-total 45000 --tailtrail-total 20500` |
| Evaluation Harness | Consolidates benchmark, scenario, portfolio, token, workflow, and report evidence under one `eval ...` umbrella. | `python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation` |
| Enterprise reporting | Summarizes local outcomes, quality, learning, token, and value evidence. | `python3 scripts/tailtrail.py report value --root buildweek-demo-project` |
| Feature Registry | Tracks implemented features, commands, docs, tests, surfaces, and drift. | `python3 scripts/tailtrail.py registry list` |
| Registry drift gate | Catches stale docs, missing changelog entries, missing command docs, and unsupported public claims. | `python3 scripts/tailtrail.py registry drift --strict` |
| Assistant adapters | Gives validated instruction coverage for Codex, Claude, Cursor, Copilot, ChatGPT, and Gemini. | `python3 scripts/tailtrail.py adapters check` |
| MCP Guardrail Server | Optional read-only MCP surface for tool-based guardrail access. | `python3 scripts/tailtrail.py mcp tools` |
| Install and update helpers | Helps teams install, update, inspect, and repair TailTrail packs in local repos. | `python3 scripts/tailtrail.py install local --inspect` |

## Optional Advanced Demo Commands

Use these only if judges ask for deeper proof.

### Build Week Evaluation Harness Scenario

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation --format json
```

Shows:

- committed baseline-vs-TailTrail scenario evidence
- deterministic local scoring
- TailTrail variant winning against conservative thresholds
- claim boundaries for live model performance, production outcomes, and token savings
- no live agent execution, scanner execution, package manager run, CI run, or model/API call

### Semantic V3 Provider-Backed Graph

```bash
python3 scripts/tailtrail.py graph ast \
  --root buildweek-demo-project \
  --changed src/claims_api/validation.py \
  --depth v3 \
  --provider-output buildweek-demo-project/tailtrail-meta/providers/sample-semantic.json \
  --approved
```

Shows:

- provider-backed evidence labels
- explicit approval gate
- no provider execution
- no network calls

### Vulnerability Summary

```bash
python3 scripts/tailtrail.py vulnerability summarize --file buildweek-demo-project/logs/trivy-sample.json
```

Shows:

- structured scanner-aware summarization
- no automatic scanner execution
- scanner evidence remains local

### Registry Drift

```bash
python3 scripts/tailtrail.py registry drift --strict
```

Shows:

- TailTrail validates its own feature inventory
- docs and commands are checked for drift
- public claims are kept within evidence boundaries

### Assistant Adapter Contract

```bash
python3 scripts/tailtrail.py adapters check
```

Shows:

- assistant files are synced
- each adapter includes required behavior:
  - Navigator-first
  - approval before implementation
  - post-change review
  - scanner approval
  - advisory learnings
  - measured-token claim boundary
  - evidence labels
  - local policy behavior

## Enterprise Capabilities

TailTrail is designed for local enterprise development teams that need Codex to operate with more discipline.

It helps teams with:

- safer AI-assisted code changes
- smaller diffs
- reuse of existing project patterns
- dependency discipline
- approval gates
- scanner-aware workflows
- focused test planning
- post-change review
- local evidence capture
- token budgeting and context reduction
- learning governance
- multi-assistant portability
- release and documentation drift control

## What Judges Can Test Locally

Run these from the TailTrail repo root:

```bash
python3 scripts/tailtrail.py doctor
python3 scripts/tailtrail.py adapters check
python3 scripts/tailtrail.py registry validate --strict
python3 scripts/tailtrail.py registry drift --strict
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
python3 -m unittest discover tests
python3 -m unittest discover -s buildweek-demo-project/tests
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
```

The demo test intentionally fails before the fix. That is expected.

## What Requires User-Provided Evidence

These features are implemented, but they need local user-provided data for meaningful output:

- exact token savings require measured model/API telemetry
- Evaluation Harness scenario evidence proves committed saved artifacts only, not live model performance
- vulnerability findings require scanner output or an approved local scanner command
- Sonar/quality findings require logs or approved local commands
- provider-backed Semantic V3 requires approved local provider JSON
- learning quality improves only after approved learning events exist
- Meta-Harness product improvement proposals require accumulated local task metadata

## What TailTrail Does Not Claim

TailTrail does not claim:

- exact token savings without measured telemetry
- live model performance from saved scenario artifacts
- scanner replacement
- test replacement
- CI replacement
- security approval
- production approval
- identical behavior across all assistants
- automatic provider execution
- automatic learning capture without approval
- background monitoring by default

The strongest claim is narrower and more defensible:

```text
TailTrail provides a local, Codex-first control layer that makes AI-assisted development more structured, reviewable, evidence-aware, token-conscious, and repeatably demonstrable through deterministic Evaluation Harness scenarios.
```
