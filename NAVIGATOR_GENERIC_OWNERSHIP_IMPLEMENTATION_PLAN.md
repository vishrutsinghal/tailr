# Navigator Generic Ownership Plan

## Objective

Make Navigator identify editable implementation boundaries from behavior evidence instead of matching generic words in paths or symbols. The change must be language-neutral: individual language extractors may differ, but Navigator consumes one normalized evidence contract.

## Problem statement

For the request `reject zero order quantity while preserving positive quantities`, Navigator currently asks the user to choose from:

- `infra/main.tf`
- `src/order_service/api.py`
- `src/order_service/models.py`

The actual decision boundary is `src/order_service/validation.py`, which contains the quantity guard and rejection. The incorrect candidates are promoted because `task-specific-definition` treats a matching term such as `order` in a symbol name as ownership evidence.

The current UI-specific behavior evidence only recognizes web-source suffixes. Backend files receive no equivalent behavior evidence, so the weaker definition-match fallback controls the decision. The three-option cap then hides additional candidates, including the actual validation file when it is ranked after earlier lexical paths.

## Intended outcome

Navigator should map the example to:

```text
Implementation owner:
- src/order_service/validation.py

Inspection context:
- src/order_service/api.py
- src/order_service/service.py
- src/order_service/models.py

Focused proof:
- tests/unit/test_validation.py

Excluded:
- infra/main.tf
```

Scope should be `resolved`; `SCOPE-Q1` should not be rendered.

## Design principles

1. A path or symbol name can prioritize a bounded read, but cannot itself grant editable-owner status.
2. Ownership requires behavior evidence that matches the requirement plus a decision, rejection, mutation, or response effect.
3. Language-specific parsing belongs in extractor adapters; Navigator operates on language-neutral normalized events.
4. Unsupported languages fail safely: they do not generate false editable owners.
5. Scope questions are reserved for genuine, evidence-backed behavior forks.

## Proposed architecture

### 1. Normalize behavior evidence

Introduce a shared event model, emitted by source extractors and consumed by Navigator:

```json
{
  "path": "src/order_service/validation.py",
  "symbol": "validate_order_request",
  "line": 16,
  "kind": "decision-guard",
  "subject_terms": ["quantity"],
  "outcome": "reject",
  "confidence": "static"
}
```

Supported event kinds:

- `decision-guard`: a conditional boundary such as an input or state check.
- `rejection`: an exception, error return, invalid response, or equivalent failure path.
- `state-mutation`: an operation that changes the named behavior's state.
- `response-mapping`: a boundary that maps a behavior to a public/API response.
- `schema-constraint`: a declarative validation rule in a supported schema format.
- `ui-action`: the existing UI interaction behavior, represented in the same format.

### 2. Keep language handling behind adapters

Each parser converts its native syntax into normalized events:

| Source type | Example native signal | Normalized evidence |
| --- | --- | --- |
| Python | `if quantity < 0: raise ...` | `decision-guard` + `rejection` |
| Java / C# | `if (...) throw ...` | `decision-guard` + `rejection` |
| Go | `if ... { return err }` | `decision-guard` + `rejection` |
| JavaScript / TypeScript | `if (...) throw ...` | `decision-guard` + `rejection` |
| SQL / schema | `CHECK (quantity > 0)` | `schema-constraint` |
| UI source | action binding, state update, render | `ui-action` |

Navigator must not contain one branch per language. It should consume only the event contract. A source type with no adapter produces no owner-qualifying behavior events.

### 3. Structure requirement intent

Split requirement vocabulary into roles before candidate qualification:

```text
Subject: quantity
Desired outcome: reject zero
Preservation: positive quantities remain valid
Context terms: order
```

Only subject and outcome terms can match behavior events. Context terms may be used for discovery and read ordering but cannot qualify an implementation owner.

### 4. Replace definition-only ownership

The current `task-specific-definition` path can remain as discovery evidence, but it must not populate `owner_qualifications`.

An implementation owner must satisfy all of the following:

1. It has a normalized event matching the requirement's subject and outcome.
2. The event represents a decision, rejection, mutation, response mapping, or schema constraint.
3. It has a supporting runtime-caller or directly linked proof-path edge.

The candidate role is then determined as follows:

| Evidence | Resulting role |
| --- | --- |
| Matching behavior event plus runtime/proof edge | implementation owner |
| Runtime caller only | inspection path |
| Data declaration only | inspection path |
| Direct requirement-linked test | proof path |
| Configuration without matching configuration requirement | excluded |

### 5. Resolve before asking a question

If exactly one candidate meets the owner contract, Navigator sets scope to `resolved` and creates the normal Planning Lock.

If two or more candidates independently meet the contract, Navigator emits `SCOPE-Q1`. Each choice must show the symbol, event kind, subject, outcome, caller path, and proof path. The UI must not render generic wording such as `task specific definition`.

If no candidate meets the contract, Navigator asks for a module, symbol, caller, or reproduction entry point without inventing choices.

## Implementation steps

1. Add the normalized behavior-event data model and validation rules.
2. Refactor the current UI behavior extraction into an adapter that emits normalized events.
3. Add backend and schema adapters incrementally, using existing static relationship extraction where available.
4. Update candidate qualification to consume normalized events and caller/proof edges.
5. Demote `task-specific-definition` to discovery/read-order evidence only.
6. Update scope-question rendering to include concrete normalized evidence and reject candidates lacking it.
7. Update scope diagnostics so reports distinguish behavior evidence, caller evidence, proof evidence, and discovery-only evidence.
8. Preserve existing UI ownership behavior through compatibility tests.

## Focused regression tests

Add tests that verify:

1. A zero-quantity validation fixture resolves `src/order_service/validation.py` as the sole implementation owner.
2. `api.py`, `service.py`, and `models.py` are context or inspection paths for that fixture.
3. `tests/unit/test_validation.py` is proof-only.
4. `infra/main.tf` is excluded when the requirement has no configuration or deployment scope.
5. A true two-validator scenario produces `SCOPE-Q1` with evidence-rich choices.
6. A definition-only or lexical path match never becomes an implementation owner.
7. An unsupported source format produces no false owner and requests a concrete clue instead.
8. Existing UI behavior-resolution fixtures remain resolved with the same owner paths.

## Acceptance criteria

- The zero-quantity example has a resolved scope and no owner-selection question.
- Every editable owner has a matching normalized behavior event and a caller or proof edge.
- Configuration, models, callers, and lexical-only matches cannot become owners without behavior evidence.
- Scope-question options show decision-useful evidence and contain no generic definition-only candidate.
- The existing test suite and newly added focused tests pass.
- The Start Report accurately separates editable owners, inspection paths, proof paths, and excluded paths.

## Validation plan

Run focused Navigator scope tests first, including the new regression fixture. Then run the relevant project test suite. Inspect the generated Start Report for the fixture and confirm that it has:

```text
Scope state: resolved
Implementation owner: src/order_service/validation.py
Proof path: tests/unit/test_validation.py
No SCOPE-Q1
```

## Out of scope

- Changing the zero-quantity product behavior itself.
- Adding a universal parser for every programming language in one change.
- Treating unsupported languages as safe to auto-scope without evidence.
- Changing TailTrail approval, Planning Lock, or execution-authority safeguards.
