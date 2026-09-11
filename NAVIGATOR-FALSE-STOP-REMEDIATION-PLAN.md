# Navigator False-Stop Remediation Plan

Status: FSR-0 through FSR-7 implemented and validated. FSR-7 real-run evidence
captured 2026-09-04 at
`fsr7-real-run-evidence/copilot-2026-09-04/installed-release-proof-report.json`
(`tailtrail eval scope installed-release-proof`, all thirteen checks passed
against a real wheel/sdist built from this checkout).
Owner: `tailtrail-core`
Primary area: Navigator requirement-to-scope resolution
Affected boundary: requirement framing -> graph selection -> bounded investigation -> scope-quality gate -> Planning Lock

## 1. Purpose

This document records every confirmed issue behind the false scope stop produced
for the following class of request:

```text
in the push to dom page there is a banner CloudWatch trace endpoint is not
configured. we need to remove it
```

The immediate incident occurred in a TypeScript/React repository, but the fix
must be repository-independent. TailTrail must resolve project-native module
references, follow behavior from a strong anchor to its implementation owner,
and distinguish a genuinely ambiguous request from a failure in its own static
analysis.

TailTrail must continue to stop when the available evidence is genuinely
ambiguous. The goal is to eliminate **false stops**, misleading scope questions,
and unsupported implementation-owner candidates. It is not to weaken the
scope-quality gate.

This plan supplements `NAVIGATOR-EVIDENCE-FIRST-SCOPE-IMPLEMENTATION-PLAN.md`.
That broader plan describes the desired evidence-first architecture. This file
captures the remaining defects exposed by a real repository after the earlier
implementation was reported complete.

## 2. Observed result

The latest Start attempt correctly normalized the request into one requirement:

```text
REQ-01: Remove the "CloudWatch trace endpoint is not configured." banner from
the push to dom page.
```

However, Navigator returned:

- scope state: `ambiguous`;
- stop reason: `file-read-limit-reached`;
- graph cache: `fresh` and `reuse`;
- files read: 20;
- bytes read: 324,746;
- included implementation owners: 10;
- no Planning Lock or implementation authority.

The owner choices included unrelated components and pages as well as the actual
page, the JSON helper, and the deployment service. The requirement correction
therefore worked, while implementation ownership remained incorrect.

## 3. Confirmed real behavior chain

The repository uses a TypeScript path alias:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

The relevant runtime flow is:

```text
deploymentService.ts
  getDeploymentTrace() throws the exact configuration message
        |
        v
PipelineAuditEventsGeneratorPage.tsx
  refreshTrace() catches the error
        |
        v
  setTraceError(error.message) stores UI state
        |
        v
  PushToDomPage renders traceError in a warning Callout
        |
        v
PipelineAuditEventsGeneratorPage.cy.tsx
  is the focused page-level proof boundary
```

For the stated UI-only outcome, the expected classification is:

- implementation owner:
  `src/pages/pipelineAuditEventsGenerator/PipelineAuditEventsGeneratorPage.tsx`;
- inspection-only literal emitter:
  `src/pages/pipelineAuditEventsGenerator/deploymentService.ts`;
- focused proof:
  `src/pages/pipelineAuditEventsGenerator/PipelineAuditEventsGeneratorPage.cy.tsx`;
- unrelated repository candidates: excluded with explicit reason codes.

The service could become an editable owner only if a revised requirement asks
to change the service contract or configuration behavior. Importing or emitting
the text alone does not grant that authority for a UI visibility change.

## 4. Confirmed defects

### FSR-01 — Project-native TypeScript aliases are not resolved

`scripts/navigator_scope.py::_resolve_reference` resolves relative paths,
absolute-looking repository paths, module identities, and symbol names. It does
not read and apply `compilerOptions.baseUrl` and `compilerOptions.paths` from
`tsconfig.json` or referenced TypeScript configurations.

Consequences:

- `@/pages/pipelineAuditEventsGenerator/deploymentService` does not resolve to
  `src/pages/pipelineAuditEventsGenerator/deploymentService.ts`;
- the static `imports-module` edge from the page to the service is absent;
- the UI renderer cannot receive the strong renderer-owner score;
- the exact literal emitter cannot be demoted reliably to inspection-only;
- unrelated candidates survive to the scope question.

Required correction:

- add a bounded, deterministic module-resolution layer;
- load the nearest applicable `tsconfig.json` or `jsconfig.json` plus supported
  `extends` chains within the repository;
- support `baseUrl`, exact path mappings, wildcard mappings, relative imports,
  configured source roots, and conventional index/suffix resolution;
- validate every resolved path through the existing repository path and
  sensitive-path controls;
- return typed failure reasons such as `module-alias-config-missing`,
  `module-alias-unresolved`, and `module-alias-ambiguous`;
- add no runtime package dependency.

### FSR-02 — A fresh graph is used as a read hint, not decisive ownership evidence

The fresh cache selected a relevant task slice, but the bounded investigation
re-extracted source relationships and failed to resolve the aliased import. The
report presented graph freshness correctly, yet freshness did not ensure that
the decisive relationship was usable.

Consequences:

- users reasonably interpret “fresh graph” as meaning that TailTrail knows the
  relevant code relationships, while ownership still fails;
- the graph can find the right files without proving the relation between them;
- graph lifecycle success can mask relationship-resolution failure.

Required correction:

- define whether cached graph edges are authoritative, advisory, or only read
  hints;
- persist normalized module edges when graph mapping supports them;
- consume fresh, hash-bound edges during scope investigation;
- otherwise clearly label the cache as `fresh-read-hints-only`;
- never equate cache freshness with resolved ownership;
- expose which decisive edge was reused, rebuilt, or remained unresolved.

### FSR-03 — Discovery seeds receive owner weight before proving ownership

Initial candidates with role `implementation-owner` and status `included` are
assigned an owner score before the investigation proves a task-specific symbol,
behavior, or relationship edge. Candidate generation and ownership selection
are therefore still partially coupled.

Consequences:

- repository-structure, graph-hint, lexical-body, and symbol-name seeds can tie
  with real owners;
- later weak signals do not need to overcome a neutral baseline—they inherit an
  ownership presumption;
- ten candidates can become “evidence-backed” options even when only one has a
  complete behavior chain.

Required correction:

- seed status must never grant implementation ownership;
- discovered candidates begin as `inspection-candidate` or equivalent;
- only explicit user scope or a qualifying evidence rule may promote a path;
- graph hints, lexical matches, and repository structure remain read-order
  inputs;
- owner eligibility must be rule-based, not inferred from a generic numeric
  tie.

### FSR-04 — Structural query words create false path matches

The normalized query contains words such as `page`, `remove`, `push`, `dom`,
and `banner`. The definition-owner check searches these terms across the whole
repository-relative path.

`page` therefore matches the common directory `src/pages`, while `remove`
matches a generic `RemoveButton` component. These matches receive a strong
`defines-symbol` edge even when the definition is unrelated to the requested
behavior.

Consequences:

- nearly every source file beneath `src/pages` can be promoted;
- common action and architecture words overwhelm behavior-specific evidence;
- unrelated files are labelled high confidence;
- the scope question contradicts its claim that lexical evidence was excluded.

Required correction:

- separate semantic behavior terms from structural, action, and location terms;
- maintain language- and framework-neutral low-signal categories;
- do not match a term against generic path segments such as `src`, `pages`,
  `components`, `services`, `lib`, `app`, `test`, or `tests`;
- require symbol-level or local basename relevance for a definition claim;
- never emit a strong `defines-symbol` edge merely because a directory contains
  a query term;
- retain low-signal matches only for bounded read ranking.

### FSR-05 — Literal-emitter classification can be overridden

The role projection checks selected `owner_paths` before checking whether a path
is an exact literal emitter for a UI-visibility request. If the emitter remains
in the top-score owner set, it is rendered as an implementation owner rather
than inspection-only.

Consequences:

- `deploymentService.ts` is shown as an editable owner even though the current
  requirement concerns banner rendering;
- the strong reason `ui-literal-source-needs-render-owner` is recorded but not
  enforced in the final role;
- the evidence contract contradicts itself.

Required correction:

- make disqualifying role rules precede generic score projection;
- a UI literal emitter remains inspection-only unless evidence also proves that
  it controls presentation or the requirement explicitly changes its contract;
- add a deterministic invariant preventing one candidate from carrying
  contradictory owner and non-owner reason codes.

### FSR-06 — The investigation does not follow the complete UI data flow

Current ownership logic recognizes direct module imports and some generic UI
patterns. It does not explicitly connect:

```text
throw/return literal -> function call -> catch -> state setter -> rendered prop
```

Consequences:

- a page importing a helper may still be treated as only a caller;
- renamed handlers such as `refreshTrace` can be missed when the action terms do
  not name the function exactly;
- rendering through a state variable is not tied back to the originating
  literal;
- the correct owner depends too heavily on proximity and naming.

Required correction:

- add bounded intra-file evidence for calls, catch assignments, state setters,
  returned values, and rendered JSX/template expressions;
- connect those facts to inter-file import/call edges;
- represent the chain with typed edges such as `calls-symbol`, `catches-error`,
  `writes-ui-state`, and `renders-ui-state`;
- require a complete or sufficiently strong partial chain before selecting a UI
  renderer;
- preserve uncertainty when dynamic dispatch prevents deterministic proof.

### FSR-07 — The file-read limit is reported as the cause instead of a symptom

The investigation stops at the initial 20-file limit when an exact anchor is
present. Because alias resolution failed and weak candidates remained tied, the
final report uses `file-read-limit-reached` as the visible stop reason.

Consequences:

- the user is told to solve a capacity problem when the actual defect is missing
  relationship support;
- increasing the limit would read more unrelated files without repairing the
  missing alias edge;
- product diagnostics do not identify the failed reasoning stage.

Required correction:

- separate loop termination from the scope decision reason;
- record both `investigation_limit_state` and `resolution_failure_reason`;
- prefer precise reasons such as `renderer-edge-unresolved-module-alias` or
  `multiple-evidence-backed-owners`;
- when a complete owner chain resolves before the cap, return `owner-resolved`
  even if additional inventory remains unread;
- when an exact anchor exists but its immediate relationship cannot resolve,
  spend a reserved targeted budget on configuration and direct neighbors rather
  than broad scanning.

### FSR-08 — Exact anchors disable useful targeted escalation

When an exact literal anchor exists, the investigation stays within the initial
read budget. This is efficient only when the resolver can follow the anchor's
relationships. It offers no reserved budget for alias configuration, direct
callers, or renderer confirmation.

Required correction:

- introduce a small relationship-resolution reserve independent of broad scan
  limits;
- use it only for nearest config files, direct import candidates, exact symbol
  references, and focused tests;
- keep total file and byte ceilings deterministic;
- do not turn targeted escalation into an unrestricted repository scan.

### FSR-09 — The generated scope question contains unsupported choices

The report says only behavior-specific or explicit evidence can appear as an
option, but the choices include repository-structure and generic path matches.
Ten choices are neither bounded nor useful to a user who asked TailTrail to
investigate the repository.

Required correction:

- a scope question may list only genuinely competing, evidence-backed owners;
- exclude read hints, callers, emitters, proof paths, and lexical candidates;
- show at most a small bounded set of real alternatives;
- when no owner is evidence-backed, ask for a module, symbol, reproduction clue,
  or host investigation rather than presenting guessed paths;
- include concise evidence and the missing discriminator for each option;
- validate question claims against candidate provenance before rendering.

### FSR-10 — Host-agent reasoning is prepared but not completing the decision

Navigator emits a sanitized host reasoning packet with state `requested`, but
the normal Start path can still stop and push repository analysis back to the
user without an evidence-grounded host proposal. This fails to fully use the
reasoning capability of Codex, Claude, or Copilot.

Required correction:

- after deterministic investigation, invoke the active host reasoning contract
  when two or more plausible candidates remain;
- provide only sanitized requirements, paths, symbols, typed edges, confidence,
  and explicit uncertainty—not raw private reasoning or unrestricted source;
- require the host to reference evidence edge IDs for every material claim;
- validate the returned proposal deterministically;
- never allow host reasoning to invent a path, bypass safety, approve work, or
  turn weak lexical evidence into authority;
- ask the user only after deterministic investigation and host reasoning both
  leave a material choice unresolved;
- preserve equivalent contracts across Codex, Claude, Copilot, CLI, and MCP.

### FSR-11 — The regression fixture was too idealized

The existing renderer-over-emitter test uses:

- a tiny two-file repository;
- a relative `./deploymentService` import;
- no `tsconfig` or `jsconfig` alias;
- no common `src/pages` directory noise;
- no unrelated components matching `remove` or `page`;
- a direct return-to-render flow rather than catch/state/render propagation.

It therefore proved the simple algorithm but not the production-shaped case.

Required correction:

- add a realistic TypeScript/React fixture with `@/* -> src/*`;
- include an exact error emitter, page-level catch/state/render flow, and focused
  component test;
- include at least ten unrelated pages, services, tests, and generic controls;
- ensure the fixture reaches the same normal Start/Navigator entry point as the
  installed product;
- assert candidate roles, evidence edges, question absence, final scope state,
  and stop reason—not only the selected filename.

### FSR-12 — Cross-language module resolution lacks an explicit contract

The current incident is TypeScript-specific, but hard-coding `@/` would create
another narrow fix. TailTrail needs a generic resolver boundary with language
profiles.

Required initial profiles:

- JavaScript/TypeScript: relative imports, `baseUrl`, `paths`, package exports,
  index files, and supported source suffixes;
- Python: absolute and relative package imports, package `__init__`, and source
  roots such as `src/` without importing or executing project code;
- Java/Kotlin: package declarations and source roots;
- C#/.NET: namespaces, project references, and conventional source identity;
- Go: module path and package imports;
- Rust: `mod`, `use`, crate modules, and workspace members.

Each profile must be deterministic, bounded, dependency-free where practical,
and safely fall back to unresolved evidence rather than guessing.

### FSR-13 — Diagnostics do not distinguish graph, resolver, scoring, and gate failures

The current report combines freshness, read limits, ambiguity, and candidate
advice without identifying which subsystem prevented resolution.

Required correction:

- record separate states for requirement interpretation, graph lifecycle,
  reference resolution, evidence-chain construction, owner selection, limits,
  host reasoning, and scope-quality gate;
- expose compact user-facing explanations while retaining verbose diagnostics;
- ensure the primary reason identifies the earliest decisive failure;
- do not describe weak candidates as evidence-backed;
- preserve exact reason codes in JSON/MCP receipts.

### FSR-14 — Calibration does not contain a real noisy-repository false-stop metric

Unit correctness alone is insufficient for owner resolution. The release gate
must measure whether Navigator resolves realistic tasks without unsafe guesses
or unnecessary user questions.

Required correction:

- add labeled noisy-repository cases across supported language profiles;
- measure owner precision, owner recall, false-stop rate, unsafe-lock rate,
  irrelevant-option rate, and reason-code accuracy;
- make unsafe locks a hard zero-tolerance release failure;
- set a committed maximum false-stop threshold for supported fixtures;
- retain negative cases where stopping is the correct behavior.

### FSR-15 — Installation proof can pass while behavior remains wrong

The source and installed FAMAS payload hashes match. This proves transactional
installation integrity, not behavioral correctness. Reinstalling the same
payload cannot fix an algorithmic defect.

Required correction:

- keep package/hash verification as supply-chain evidence;
- add installed-payload functional smoke tests using representative scope
  fixtures;
- distinguish `installation-current` from `behavior-verified`;
- require a real installed Start proof before closing this remediation.

## 5. Required product invariants

1. A fresh graph never implies resolved ownership by itself.
2. A candidate seed is never implementation authority.
3. Directory-name or generic action-word matches never produce strong owner
   evidence.
4. Every implementation owner has a task-specific symbol, behavior, or
   relationship evidence chain.
5. UI literal emitters are not UI presentation owners unless the requirement or
   evidence proves that role.
6. Resolver configuration is read safely and deterministically; project code is
   never executed during Planning Lock.
7. A complete evidence chain wins over broad candidate count and stops further
   reads.
8. Limits remain enforced, but diagnostics identify the actual unresolved edge.
9. User questions contain only genuine evidence-backed alternatives.
10. Host reasoning can refine supported evidence but cannot create evidence or
    authority.
11. CLI, MCP, Codex, Claude, and Copilot produce conformant decisions from the
    same target state.
12. TailTrail still fails closed when ambiguity is real.

## 6. Implementation phases

### Phase FSR-0 — Freeze the failing baseline

Status: **implemented** on 2026-09-03.

Deliverables:

- create an anonymized production-shaped fixture matching the observed flow;
- capture the current wrong result: ten owners, ambiguous scope, and misleading
  file-limit reason;
- record expected roles and edges;
- add the case to Navigator calibration as a known false stop;
- ensure the fixture contains no proprietary source or raw repository content.

Exit criteria:

- the fixture deterministically fails on the current implementation;
- the failure reproduces through `navigator.decide`, CLI Start integration, and
  the scope-quality gate;
- a negative control with two genuine renderers still stops as ambiguous.

Implementation evidence:

- `tests/fixtures/navigator-scope/typescript-alias-ui-literal-false-stop.json`
  provides a synthetic TypeScript/React repository with a `tsconfig` alias,
  exact literal emitter, catch/state/render flow, focused component proof, and
  more than twenty noisy repository files;
- `tests/fixtures/navigator-scope/typescript-genuine-renderer-ambiguity.json`
  preserves the safe stop for two equally supported renderers;
- `tailtrail-meta/navigator-scope-baseline-v1.json` records the current and
  desired results, fingerprints, known-false-stop calibration, irrelevant
  option count, safe-stop control, and zero unsafe locks;
- `schemas/navigator-scope-baseline.schema.json` closes the FSR-0 extension and
  calibration contract;
- `tests/test_navigator_scope.py` executes the false stop through
  `navigator.decide` and the actual `task-start.py` boundary, proves fresh graph
  creation followed by reuse, and proves that neither blocked case creates a
  Planning Lock run;
- `scripts/navigator-scope-calibration.py` and its report schema expose the
  sealed FSR-0 baseline through `tailtrail eval scope report` as one open false
  stop, one safe-stop control, nine irrelevant options, zero unsafe locks, and
  explicitly `release ready: false`;
- focused validation passed: 56 Navigator scope, graph lifecycle, and
  calibration tests, plus 10 self-contained package tests.

FSR-0 intentionally preserves the historical failure. FSR-1 closes its missing
module-resolution edge; owner scoring, richer evidence chaining, and diagnostic
improvements continue in FSR-2 and later phases.

### Phase FSR-1 — Add configuration-aware module resolution

Status: **implemented** on 2026-09-03.

Deliverables:

- introduce a resolver interface and TypeScript/JavaScript profile;
- parse bounded `tsconfig`/`jsconfig` configuration and `extends` safely;
- normalize alias, suffix, and index resolution;
- emit typed resolution evidence and failure reasons;
- connect fresh graph edges to the same normalized identities.

Exit criteria:

- `@/pages/.../deploymentService` resolves to exactly one repository path;
- traversal, out-of-root mappings, malformed JSON, cycles, and ambiguous
  wildcards fail safely;
- relative import behavior remains unchanged;
- no new dependency is introduced.

Implementation evidence:

- `scripts/module_resolution.py` provides the shared, dependency-free resolver
  interface and JavaScript/TypeScript profile. It bounds configuration files,
  bytes, alias targets, and `extends` depth; parses JSONC comments and trailing
  commas; and supports repository-local `baseUrl`, exact and wildcard `paths`,
  source suffixes, and index files;
- resolver results are typed as `resolved`, `unresolved`, `ambiguous`, or
  `not-applicable` and retain configuration paths plus stable reason codes for
  success, invalid configuration, cycles, unsupported inheritance, limits,
  ambiguity, and out-of-root targets;
- `scripts/navigator_scope.py` recognizes `tsconfig*.json` and
  `jsconfig*.json` as configuration, uses the shared resolver before legacy
  symbol matching, records a closed module-resolution summary in scope
  evidence, and labels configured alias/base-url edges explicitly;
- `scripts/code-graph-mapper.py` uses that same resolver and persists both the
  raw import and its normalized repository target, resolution state,
  configuration paths, and reason codes;
- `schemas/navigator-scope-evidence.schema.json` defines the closed typed
  resolver evidence while retaining compatibility with already-saved v2 scope
  artifacts that predate FSR-1;
- `tests/test_module_resolution.py` covers exact and wildcard aliases,
  `baseUrl`, suffix and index lookup, JSONC, local `extends`, relative imports,
  ambiguity, malformed configuration, cycles, depth limits, out-of-root
  targets, and graph persistence;
- the sealed FSR-0 failure fixture now resolves through `navigator.decide` and
  the real `task-start.py` boundary to one page owner, one inspection-only
  literal emitter, one focused component proof, `owner-resolved`, and an
  awaiting-approval Planning Lock. The historical FSR-0 baseline remains
  unchanged, and the two-renderer negative control remains safely ambiguous.

### Phase FSR-2 — Separate candidates from owners

Status: **implemented** on 2026-09-03.

Deliverables:

- remove initial owner scoring based on seed role/status;
- split read ranking from owner eligibility;
- classify low-signal query terms and generic path segments;
- require qualifying evidence rules for owner promotion;
- enforce literal-emitter demotion for UI visibility requests.

Exit criteria:

- unrelated `src/pages/*` files remain excluded;
- `RemoveButton.tsx` does not become an owner from `remove` alone;
- no weak seed appears in a scope question;
- explicit user paths retain their documented candidate authority without being
  silently treated as proven owners.

Implementation evidence:

- `scripts/navigator_scope.py` no longer initializes or selects owners from a
  generic numeric score. Discovery sources, graph freshness, Git observations,
  lexical matches, and repository structure remain read-ranking evidence only;
- production paths supplied explicitly begin as high-confidence
  `inspection-only` owner candidates. Investigation records a typed
  `declares-edit-boundary` edge before the explicit-scope qualification can
  promote them;
- owner selection now uses a deterministic qualification precedence contract:
  explicit user scope, UI renderer behavior, task-specific behavior, a unique
  exact literal for non-UI work, a task-specific relationship, or a
  task-specific local definition;
- low-signal action and structural terms are excluded from ownership matching,
  and generic path segments such as `src`, `pages`, `components`, `services`,
  `lib`, and `tests` cannot create a definition-owner edge;
- definition qualification uses only behavior-specific query terms matched to
  an extracted definition or the local basename. It no longer searches the
  complete repository-relative path;
- UI requests may qualify only UI implementation surfaces through inferred
  definition or relationship rules; a similarly named backend module remains
  inspection-only when the repository has no UI surface. Explicit user scope
  remains separately auditable;
- exact UI literal emitters are removed from the owner-qualification set unless
  they independently prove presentation behavior, and final role projection
  applies this disqualification before generic owner projection;
- investigation evidence now includes the selected qualification rule, counts
  for every rule tier, selected/qualified candidate counts, and a stable reason
  code. The v2 schema defines this closed structure while remaining compatible
  with saved pre-FSR-2 artifacts;
- focused tests prove structural/action terms produce no owners, a
  behavior-specific local identity can qualify one owner, explicit scope is
  promoted only during investigation, UI emitters remain inspection-only, weak
  candidates do not enter scope questions, and genuine equal behavior evidence
  remains safely ambiguous;
- the production-shaped alias fixture continues to resolve one page owner, one
  inspection-only literal emitter, and one focused proof path, now with
  `ui-renderer-behavior` as the auditable selection rule.

### Phase FSR-3 — Add bounded behavior-chain tracing

Deliverables:

- extract call, catch, state-write, and render-use facts;
- join intra-file facts with normalized module edges;
- define UI renderer selection and preservation rules;
- select focused proof through direct test-to-owner evidence.

Exit criteria:

- the incident fixture produces exactly one owner, one inspection-only emitter,
  and one focused proof path;
- a service-contract request can still select the service when appropriate;
- indirect, dynamic, or conflicting flows remain explicitly uncertain.

Implementation completed on 2026-09-04:

- the shared dependency-free JavaScript/TypeScript extractor emits sanitized
  `import-binding`, `call`, `call-result`, `catch-binding`, `state-binding`,
  `state-write`, and `render-use` facts. It retains identifiers, static module
  references, line numbers, and enclosing named-function scope only; it neither
  executes project code nor persists source expressions. Cross-function facts
  cannot be joined accidentally, while nested handlers share their outer UI
  component boundary;
- Navigator joins those facts to the configuration-aware normalized module
  edge. A UI renderer is qualified only by one of three bounded static flows:
  imported call -> returned value -> render, imported call -> caught error ->
  state write -> render, or imported call -> caught error -> direct render;
- incomplete import/call chains cannot be rescued by filename, definition, or
  generic relationship matching. Explicit user scope and separately proven
  direct UI behavior remain higher-authority preservation boundaries;
- investigation evidence exposes a closed `behavior_chains` contract with a
  deterministic state (`not-exercised`, `complete`, `partial`, `conflicting`,
  or `unresolved`), source/renderer paths, supported variant, fact classes,
  and reason codes. The evidence contains no source bodies;
- strong evidence edges now describe `calls-symbol`, `captures-returned-value`,
  `catches-error`, `writes-ui-state`, and the applicable render use instead of
  claiming that an import alone renders a value;
- focused proof selection prefers direct test module/registration edges and
  uses same-module naming only when no direct proof edge exists;
- focused regression coverage proves the production-shaped alias incident,
  extractor privacy, direct proof selection, service-contract preservation,
  safe uncertainty for indirect and dynamic invocation, and genuine conflict
  between two complete renderers. The complete v2 evidence validates against
  the updated closed schema.

### Phase FSR-4 — Correct limits, reasons, and questions

Deliverables:

- reserve a bounded nearest-neighbor/configuration investigation budget;
- split termination reason from decision reason;
- make owner resolution terminate investigation successfully;
- validate scope-question options and claims;
- render concise default diagnostics and complete verbose diagnostics.

Exit criteria:

- the incident returns `owner-resolved`, not `file-read-limit-reached`;
- genuine limit failures identify the missing relationship or evidence class;
- questions list only genuine alternatives and never more than the configured
  small option cap;
- no Planning Lock is created for unresolved scope.

Implementation completed on 2026-09-04:

- broad discovery, cache freshness validation, direct-neighbor relationship
  reads, and resolver configuration reads now have separate deterministic
  counters and ceilings. Cache validation no longer consumes the broad
  source-fact counter, and an eight-file targeted reserve remains available for
  same-boundary modules, configured graph hints, exact module identities, and
  focused tests;
- the evidence contract records `limit_state.termination_reason` separately
  from `decision_reason` and `resolution_failure_reason`. The compatibility
  `stop_reason` now projects the decision reason, so a completed chain reports
  `owner-resolved` even if broad inventory reached its cap;
- unresolved decisions identify the earliest supported missing evidence class:
  conflicting owners, conflicting renderer chains, incomplete behavior chains,
  ambiguous or unresolved module aliases, a missing renderer/caller edge, or
  owner evidence not found before an applicable limit;
- resolver diagnostics expose bounded configuration file/byte counts and their
  independent limits without retaining configuration bodies;
- scope questions are derived through a validation gate. At most three
  included, high-confidence implementation owners may be offered, and every
  option must cite a strong edge plus an explicit owner-qualification rule.
  Callers, literal emitters, tests, graph/read hints, and lexical-only paths are
  rejected. When nothing qualifies, TailTrail asks for a module, symbol,
  caller, or reproduction clue without suggesting a path;
- standard blocked reports show the actionable decision, requirements, and one
  bounded question. `--verbose` adds the exact scope/cache/resolver/limit reason
  codes, separate read counters, behavior state, option-validation result, and
  retained candidate diagnostics;
- focused tests prove owner resolution after the broad cap, precise failure
  before a chain can be read, cache/broad/relationship/config accounting,
  three-option truncation with valid edge references, unsupported-option
  exclusion, concise/default versus complete/verbose rendering, and zero
  Planning Lock persistence for blocked scope.

### Phase FSR-5 — Complete host reasoning and MCP conformance

Deliverables:

- route unresolved-but-supported evidence packets to the active host agent;
- validate proposals against exact paths, hashes, requirements, and edges;
- preserve one deterministic decision contract across host adapters and MCP;
- add negative tests for invented paths, unsupported claims, stale packets, and
  attempted authority escalation.

Exit criteria:

- host reasoning resolves only evidence-supported alternatives;
- unsupported proposals are rejected without a lock;
- CLI and MCP expose equivalent status, reasons, roles, and run-creation
  behavior;
- Codex, Claude, and Copilot conformance fixtures pass.

Implementation completed on 2026-09-04:

- Navigator now classifies host reasoning as `requested` only when an
  unresolved decision retains at least two included, high-confidence,
  hash-bound owners with strong evidence edges. Resolved decisions are
  `not-required`; evidence without supported alternatives is `unavailable`;
- the sanitized packet carries the exact scope-decision, target, goal,
  requirement statement, candidate identity, content hash, edge, limit, and
  route bindings. It contains no raw source body or private reasoning;
- the host proposal contract is schema v2 and closed. Every material path has
  a candidate/hash/role/edge claim, every requirement is covered exactly once,
  and the proposal declares evidence-refinement-only authority;
- validation recomputes packet integrity and current file hashes, enforces
  requirement and candidate identities, checks that every cited edge touches
  its claimed path, and rejects unsupported roles, paths, edges, fields,
  confidence promotion, stale content, and authority escalation;
- accepted host reasoning may select one already-supported owner. It never
  creates repository evidence: unselected supported owners become
  inspection-only alternatives, the canonical requirement mapping is updated,
  and host identity is excluded from the normalized decision fingerprint;
- `task-start.py` accepts a host-bound proposal and reapplies it only after a
  fresh deterministic investigation. Unsupported proposals remain blocked and
  create no Planning Lock; a current accepted proposal proceeds to the normal
  awaiting-approval lock without implementation authority;
- CLI and MCP share the same packet validator and in-memory refinement
  functions. MCP exposes the requested packet and explicit `run_created`
  result even when its user-facing result is Markdown, then accepts the same
  proposal on a repeated explicit Start request;
- the common Codex, Copilot, and Claude adapter contract now includes five
  FSR-5 scenarios: supported selection, invented path, unsupported edge, stale
  packet, and authority escalation. Generated surfaces and host sources retain
  the same instructions and authority boundary;
- focused tests prove cross-host normalized-fingerprint equivalence, CLI/MCP
  result equivalence, atomic no-run rejection, successful pre-lock refinement,
  original-evidence immutability, current-hash validation, and zero authority
  transfer from proposal validation.

### Phase FSR-6 — Calibration, negative assurance, and release proof

Deliverables:

- run focused tests, Navigator suite, parallel full unit suite, package checks,
  adapter conformance, and release proof;
- publish calibration metrics and deltas;
- test both safe resolution and correct stopping;
- update relevant Navigator, graph, host, MCP, install, and workflow docs;
- add rollback guidance that preserves fail-closed behavior.

Exit criteria:

- zero unsafe locks across committed fixtures;
- false-stop and irrelevant-option thresholds pass;
- all supported language-profile fixtures pass their declared contract;
- release artifacts contain the changed code, tests, schemas, and documentation;
- no generated local runtime state is committed accidentally.

Implementation completed on 2026-09-04:

- the existing Navigator scope calibration now executes the sealed noisy
  TypeScript incident, Python wrong-owner regression, and genuine two-renderer
  safe-stop control through both Navigator decision and atomic Start paths;
- committed zero-tolerance gates cover false-stop rate, irrelevant-option rate,
  unsafe-lock count, reason-code accuracy, owner precision/recall, and supported
  language-profile pass rate;
- calibration publishes an immutable comparison with FSR-0: false stops move
  from `1` to `0`, irrelevant options from `9` to `0`, and unsafe locks remain
  `0`;
- six executable synthetic language profiles cover Python, JavaScript,
  TypeScript, Java, C#, and Go with twelve unrelated files per profile. Reports
  retain only categorical contract results and fixture digests, not source;
- release proof now joins calibration thresholds, CLI/MCP parity, Codex,
  Copilot, and Claude adapter conformance, migration immutability, Planning
  Lock/closure evidence, source-release test inventory, packaged runtime
  inventory, and tracked local-runtime hygiene;
- the release gate fails closed for a missing artifact, failed profile,
  false stop, irrelevant option, reason-code mismatch, unsafe lock, adapter
  divergence, or tracked runtime artifact;
- Navigator, graph, host, MCP, install, and end-to-end workflow documentation
  now describes the release checkpoint and the approval-gated rollback route.

Validation completed on 2026-09-04:

- the focused Navigator/release matrix passed `10` modules and `187` tests,
  including isolated wheel and source-distribution execution;
- the complete dependency-free parallel suite passed `169` modules and `1237`
  tests with four workers;
- executable calibration passed all three resolution/safe-stop scenarios and
  all six supported language profiles with `0` false stops, `0` irrelevant
  options, `0` unsafe locks, and `1.0` reason accuracy, owner precision, and
  owner recall;
- release proof passed all thirteen gates, including CLI/MCP lifecycle parity,
  Codex/Copilot/Claude adapter conformance, all `28` source-release artifacts,
  all `24` package-applicable artifacts, migration immutability, and tracked
  runtime-state hygiene;
- adapter synchronization, feature-registry validation, enterprise-registry
  validation, product-maturity validation, JSON parsing, and `git diff --check`
  all passed. Hosted installed-product observation remains explicitly assigned
  to FSR-7 and is not claimed by this phase.

### Phase FSR-7 — Installed real-run validation

Deliverables:

- update a clean external fixture transactionally;
- verify source/package/installed hashes;
- generate or reuse a fresh graph;
- run the exact incident-style Start request through the installed Codex
  payload;
- repeat adapter-level conformance for Copilot and Claude packaging;
- capture the complete Start result as release evidence.

Exit criteria:

- the installed run creates a Planning Lock with the page as the sole editable
  owner;
- the service is inspection-only and the page component test is proof-only;
- no scope question is generated;
- the report states how graph evidence and bounded investigation resolved the
  owner;
- installation integrity and behavioral proof are reported separately.

## 7. Required regression matrix

The implementation is incomplete unless all of these cases are covered:

1. Relative TypeScript import, single renderer — resolve.
2. TypeScript `paths` alias, single renderer — resolve.
3. Extended `tsconfig`, single renderer — resolve.
4. Alias with two valid targets — stop as ambiguous.
5. Alias escaping the repository — reject safely.
6. Exact literal in service, caught and rendered by page — page owns UI change.
7. Exact literal returned directly by component — component owns UI change.
8. Request explicitly changes service error contract — service may own change.
9. Multiple pages render the same error — use location/caller evidence or ask a
   genuine bounded question.
10. Unrelated `src/pages` files — exclude.
11. Generic `RemoveButton` — exclude for remove-banner request.
12. Stale graph with current source — refresh before relying on cached edges.
13. Fresh graph with missing edge — rebuild targeted evidence and report the
    distinction.
14. No graph — build bounded ephemeral evidence without persisting during Start.
15. File limit reached after a complete chain — resolve successfully.
16. File limit reached before any chain — stop with the exact unresolved reason.
17. Host proposal invents a path — reject.
18. Host proposal cites no evidence edge — reject.
19. CLI and MCP receive identical input — equivalent scope decision.
20. Installed payload run — same result as source checkout.

Equivalent fixtures are required for other supported language profiles as their
resolvers are introduced. Unsupported profiles must return an explicit
`resolver-profile-unavailable` posture rather than silently falling back to
lexical ownership.

## 8. Validation commands

Exact commands should be finalized with the implementation, but the minimum
proof set is expected to include:

```bash
python3 -m unittest tests.test_requirement_discovery -v
python3 -m unittest tests.test_navigator_scope -v
python3 -m unittest tests.test_navigator_graph_lifecycle -v
python3 -m unittest tests.test_start_entrypoints -v
python3 -m unittest tests.test_mcp_server -v
python3 -m unittest tests.test_host_adapter_conformance -v
python3 scripts/run-tests.py
python3 scripts/run-tests.py --jobs 1 --include test_self_contained_package
python3 scripts/tailtrail.py adapters conformance
git diff --check
```

Commands must be recorded as actual evidence with their exit status. Declared,
planned, or duplicated commands are not passing proof.

## 9. Security and privacy boundaries

- Never execute project modules to resolve imports.
- Never follow an alias outside the verified repository root.
- Reject configuration cycles and excessive `extends` depth.
- Keep file, byte, hop, configuration, and result limits explicit.
- Do not persist raw source bodies in graph or planning receipts.
- Persist normalized paths, bounded symbols, typed edges, fingerprints, and
  reason codes only.
- Exclude dependencies, generated files, secrets, local runtime state, managed
  TailTrail payloads, and ignored content according to existing policy.
- Host reasoning receives sanitized evidence and cannot grant approval or
  execution authority.

## 10. Observability requirements

Every scope attempt should expose, in machine-readable form:

- requirement interpretation source and confidence;
- graph decision: create, reuse, refresh, ephemeral, off, or defer;
- graph evidence actually consumed;
- resolver profile and configuration files used;
- resolved, unresolved, and ambiguous references;
- files and bytes read by broad and targeted budgets separately;
- candidate counts by role and evidence strength;
- selected owner chain;
- discarded alternatives and reason codes;
- host reasoning requested, accepted, rejected, or unavailable;
- scope-quality result and whether a Planning Lock was created.

The default human report should show the actionable reason and outcome. The
verbose report may expose the complete diagnostics without duplicating noisy
rows.

## 11. Definition of done

This remediation is complete only when:

- the real defect shape is reproduced by a committed, non-proprietary fixture;
- project-native aliases resolve safely;
- candidate ranking and owner authority are separate;
- the complete emitter-to-renderer evidence chain is represented;
- the expected page is the sole editable owner for the incident request;
- unrelated pages and generic controls are excluded;
- the focused page test is selected as proof-only;
- no misleading scope question is produced;
- limit diagnostics identify the true cause;
- genuine ambiguity still stops without creating a run;
- host and MCP contracts are conformant;
- calibration, negative assurance, package proof, and the parallel test suite
  pass;
- the installed payload reproduces the corrected behavior;
- documentation no longer claims this ownership problem is fully resolved
  before the preceding evidence exists.

## 12. Current disposition

The existing installation is current; source and installed copies of
`navigator_scope.py` and `requirement_discovery.py` have matching SHA-256
hashes. Reinstallation alone will not correct this incident.

The requirement-normalization portion is working. The remaining blocker is an
algorithmic gap spanning module resolution, candidate promotion, behavior-chain
evidence, limit diagnostics, realistic testing, and host reasoning integration.
Until this plan is implemented and validated, this class of Start request must
be treated as an open Navigator false-stop defect.
