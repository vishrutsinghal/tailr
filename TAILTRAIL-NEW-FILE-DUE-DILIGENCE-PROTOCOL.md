# TailTrail New-File Due Diligence Protocol

Status: draft for review

## Purpose

TailTrail currently resolves scope by searching the code graph for an
existing-file owner first, and only falls back to a host-declared new path
when that search is ambiguous or empty. This ordering is backwards for any
requirement that is genuinely new: a brand-new, domain-isolated file has zero
graph evidence by construction, so today's search either stalls as
"ambiguous" or hands ownership to an unrelated existing file that merely has
stronger (but irrelevant) relationship edges.

This was observed live, twice, in the same session: Navigator proposed
`scripts/intake_pipeline.py` as the owner for a brand-new, unrelated schema
file (`schemas/host-question-flow-event.schema.json`), purely because that
file had strong import/caller edges elsewhere in the graph. Both runs needed
a manual `new:` scope correction to proceed.

This document specifies the due-diligence protocol TailTrail must run
whenever a requirement proposes a new file -- so that "is this really a new
file?" is answered by evidence, not by trusting the host's assertion in
either direction, and not by graph-search leftovers.

This is a design document. Nothing here is implemented yet. See
`TAILTRAIL-ISSUES-LOG.md` for the live incidents this is based on and
`TAILTRAIL-HOST-QUESTION-FLOW-DESIGN.md` for the surrounding host-question
flow this slots into (its "Evidence-Check by Role" section already gestures
at this gap without specifying an algorithm).

## Why host assertion alone is not enough, in either direction

The host can be wrong two ways, not one:

1. **Host says "new file needed," but an existing file already owns this
   responsibility.** Accepting this blindly creates duplicate logic, forked
   behavior, and maintenance drift.
2. **Host says "just edit existing file X," but X is the wrong file** --
   unrelated responsibility, wrong domain, or already overloaded. Accepting
   this blindly produces exactly the over-stuffed, multi-responsibility files
   the host-input-contract's `existing-implementation-owner` role is
   supposed to prevent.

A due-diligence protocol must be symmetric: it distrusts both claims equally,
and resolves both the same way -- with repository evidence, not with
whichever claim happens to be easier to accept.

## The protocol: six checks, run in this order, first decisive result wins

Each check produces evidence (a fact, computed from the repository), never
an inferred verdict by itself. The verdict comes from combining all six.

### Check 1 -- Hard existence check

Does the exact proposed path already exist on disk right now?

- **Yes** -> the "new file" claim is simply false. Reject outright; route to
  an edit-existing-file requirement. No ambiguity, no host trust involved,
  no further checks needed.
- **No** -> continue to Check 2.

This check also covers case-insensitive collisions (`Foo.py` vs `foo.py` on
a case-insensitive filesystem) and path-separator normalization (`\\` vs
`/`), both using the same normalization `repository_path_policy.py` already
performs.

### Check 2 -- Path-eligibility check

Run the proposed path through the existing, shipped classifiers:

- `repository_path_policy.classify_path()` -- must resolve to `application`.
  A proposed path landing in `managed-worktree`, `agent-managed`,
  `tailtrail-managed`, `generated`, or `external` territory is rejected
  immediately: a "new file" cannot be proposed into vendor, generated,
  worktree, or excluded space.
- `navigator_scope.classify_repository_role()` -- the proposed role
  (`implementation-owner`, `test`, `configuration`, ...) must be consistent
  with what the requirement claims it is. A requirement claiming
  "proposed-implementation-owner" for a path that would classify as
  `documentation` (e.g. a `.md` file) is rejected here, not discovered later.

No new logic is needed for this check -- it reuses two classifiers that
already exist and are already tested.

### Check 3 -- Name/symbol collision check

This check has two independent sub-checks. They are evaluated separately
because they have very different false-positive rates and must not be
collapsed into one signal.

**3a. Filename/symbol collision (weak on its own).** Search the repository
for the same filename stem under an *unrelated* directory
(`user_validator.py` vs `validators/user.py`), and for the primary symbol(s)
the host says the new file will define (`def X` / `class X` / exported `X`),
repository-wide. On its own this is noisy: `utils.py`, `index.ts`,
`__init__.py`, and similar generic names legitimately repeat across many
unrelated directories in real codebases. A bare filename match with no other
corroborating signal does not block -- it is recorded as weak evidence and
only matters in combination with 3b or Check 4.

**3b. Directory near-duplication (strong on its own).** Independently of the
filename, check whether the *proposed directory itself* is a trivial variant
of an existing directory name: a numeric suffix (`validate` vs `validate2`),
a version/copy marker (`_v2`, `_new`, `-copy`, `-old`), or an edit distance
below a small fixed threshold against an existing sibling directory name.
This is a strong anti-pattern signal on its own, regardless of filename,
because it usually means a parallel structure is being forked instead of the
original being extended or reused.

**Combined result:** when 3a and 3b both fire for the same proposal --
*exactly* the case of proposing `validate2/user.py` while `validate/user.py`
already exists -- this is the strongest form of Check 3 evidence. It is
never silently approved. It always routes to an explicit host question
naming both findings: "`validate2` closely resembles the existing
`validate` directory, and `user.py` already exists there -- why does this
need to be separate, and why can't `validate/user.py` be extended or reused
instead?" The host's answer is then itself subject to Check 6's rationale
scrutiny, not accepted at face value.

When only 3a fires (generic filename match, unrelated directory, no
directory-name resemblance), the result is recorded as weak evidence and
folds into Check 4 rather than independently blocking.

When only 3b fires (near-duplicate directory name, but a genuinely different
filename), it still routes to a host question, but one scoped to the
directory-level question alone ("why does `validate2` need to exist
alongside `validate`?"), since there is no specific file-level collision to
name.

**Edge case -- stale/dead code:** if the only collision found (via 3a) is an
unused, dead function with the same name, that is still presented to the
host as a named candidate (never silently ignored), but the host's response
that it is dead code is accepted as resolving evidence, not as an unchecked
assertion -- TailTrail should independently confirm the candidate has zero
callers before accepting "it's dead" as true.

### Check 4 -- Existing-owner evidence search (same search Navigator already runs, polarity flipped)

Run the normal relationship-edge search (imports, callers, defines-matching-
symbol, directory convention) against the stated requirement -- exactly the
search Navigator performs today. The polarity of how the *result* is used
changes:

- **Strong existing owner found** (multiple strong edge types, as Navigator
  already scores them) -> evidence *against* the host's "new" claim. Do not
  auto-override the host's claim and do not silently accept it either.
  Surface the found candidate through the same `SCOPE-Q1`-style question
  Navigator already asks for existing-file disambiguation, but triggered by
  *contradicting* evidence, not only by an unanswered question.
- **Weak or no existing owner found** -> evidence *for* the new-file claim.
  This is the behavioral change from today: currently, weak/no evidence
  stalls as "ambiguous, more than one owner has weak evidence" or similar.
  It should instead count toward a `new-confirmed` verdict once combined
  with Check 5.

**Edge case -- partial domain overlap:** some existing files are related but
none is a strong qualifying owner (e.g. three loosely related helper
modules, none of which imports or is imported by anything matching the
requirement). This is still "weak evidence" for Check 4's purposes -- it
supports `new-confirmed`, but the found related files should still be
recorded as `inspection_paths` so the new file's author has them as context,
not as blocking evidence.

**Edge case -- chained proposed-new dependencies:** the requirement may
require a new file that depends on *another* proposed-new file in the same
packet (e.g. a new implementation file importing a new shared utility also
being created in the same approval). Check 4's search must treat sibling
proposed-new paths in the same packet as valid dependency targets, not as
missing evidence -- otherwise every multi-file new-feature requirement would
incorrectly fail this check against its own in-flight siblings.

### Check 5 -- Convention-precedent check

Does the target directory already establish a real "one file per concern"
pattern? Examples already observed in this repository:

- `schemas/*.schema.json` -- one schema per topic, confirmed by directory
  listing.
- `tests/test_*.py` -- one test file per module/concern.

This is the single strongest, cheapest, most objective signal available,
and it is what made both of this session's new schema files obviously
correct as new files -- no line-count or import-count threshold was needed;
the directory's existing contents were the evidence.

**Edge case -- directory does not exist yet.** For a genuinely new
subsystem (or a greenfield project with no files at all), there is no
directory to establish precedent from. Absence of precedent is not treated
as a negative signal here -- it falls through to Check 6's rationale check
instead of blocking. (This is the greenfield degenerate case; see below.)

**Edge case -- mixed/inconsistent existing convention.** If the target
directory contains both "one file per concern" examples and large
multi-concern files, this check is inconclusive (neither supports nor
contradicts); the verdict falls through to Check 6.

**Edge case -- precedent borrowed from an unrelated subsystem.** A
convention found in a different, unrelated directory (e.g. citing
`tests/test_*.py`'s convention to justify a new file under `scripts/`) does
not count as precedent for Check 5 -- precedent must come from the *same*
target directory, or an explicitly named sibling directory the host states
is the governing convention (and that statement is itself subject to Check
6's rationale scrutiny).

### Check 6 -- Domain-boundary rationale (host-supplied, evidence-checked, not trusted on faith)

The host must state why isolation is warranted: new integration, new data
entity, unrelated feature surface, or an explicitly named governing
convention. This statement is only decisive when Checks 3-5 did not already
produce a contradicting or confirming result -- it is the tie-breaker for
the `unverified` middle ground, not an independent override.

A rationale that contradicts already-found evidence (e.g. "this is
unrelated" when Check 4 found a strong existing owner) routes to
clarification; it does not get accepted because the host said so.

## Verdict taxonomy

Mirrors the Correction Premise pattern's style (state enum + required
route), for internal consistency with the rest of the Host Question Flow
design:

| Verdict | Meaning | Required route |
|---|---|---|
| `new-confirmed` | Existence check clean, no eligibility/collision block, weak-or-no existing-owner evidence, convention precedent supports isolation (or absence of precedent falls through cleanly) | Approve as new; proceed to post-implementation verification |
| `extend-recommended` | Strong existing-owner evidence contradicts the host's "new" claim | Route to host/user for an explicit decision naming the found candidate; never silently override either way |
| `collision-blocked` | Proposed path, or a conflicting symbol/name, already exists | Hard fail; host must name a different path or admit this is actually an edit |
| `unverified` | Signals conflict, or are too weak on both sides, after all six checks | Bounded clarification question naming the specific ambiguity (not a generic "which file?" question) |
| `not-applicable` | The requirement does not involve creating a new path at all | Skip this protocol; use the normal existing-file evidence path |

## Symmetry: the same protocol applies to "just edit existing file X" claims

Checks 2-6 apply with the claim inverted: before accepting an existing file
as the owner, confirm (via the same relationship-edge evidence) that its
actual role and responsibility genuinely match the requirement. A host
naming an existing file that has no qualifying relationship to the
requirement should produce the same `unverified`/clarification route as an
unsupported "new file" claim -- not a free pass because "existing" sounds
safer than "new."

## Fast path: host-declared evidence collapses round-trips, never skips verification

This is not a new mechanism -- it is
`TAILTRAIL-HOST-QUESTION-FLOW-DESIGN.md`'s existing "Hybrid Narration and
Question Flow" and "Authority by Input Type" sections, applied to these six
checks specifically. That design already establishes the general rule:
narration can fill a required field only through the same
evidence-checked candidate-answer path a direct question response would use
(`received -> normalized -> mapped-to-profile-field -> evidence-checked ->
accepted`); it never shortcuts straight to accepted authority. Nothing here
overrides that rule -- this section only specifies which fields a host can
pre-populate for new-file requirements, and which of the six checks each one
feeds.

The host-input-contract's `paths[]` entries may carry an optional
`new_file_evidence` object per proposed-new path:

```json
{
  "path": "schemas/host-question-flow-event.schema.json",
  "role": "proposed-implementation-owner",
  "new_file_evidence": {
    "collision_claim": "no existing file or symbol named this",
    "convention_cited": "schemas/ already holds one-schema-per-topic files",
    "no_owner_claim": "no existing file owns this responsibility"
  }
}
```

Each claim maps to exactly one check and is independently re-verified --
TailTrail never accepts a claim as true because it was stated:

| Host-supplied claim | Check it targets | Verification performed regardless of the claim |
|---|---|---|
| `collision_claim` | 3a/3b | Repository-wide filename/symbol search and directory near-duplication check, run exactly as if the claim had not been supplied |
| `convention_cited` | 5 | Directory listing confirms the cited convention actually holds in that directory |
| `no_owner_claim` | 4 | The normal relationship-edge search still runs; the claim is not a substitute for it |

These three checks are cheap and deterministic (a directory listing, a
repository-wide grep, a path classification) -- there is no cost trade-off
being made by re-verifying every time. If every supplied claim holds up and
Check 4 independently returns weak/no evidence, the verdict resolves to
`new-confirmed` in the same turn with zero clarification questions issued,
since there is no evidence gap left for a question to fill. If any claim
does not hold up (for example, a `collision_claim` of "no existing file" is
contradicted by Check 3b finding `validate2` next to `validate`), the normal
route (`extend-recommended`, `collision-blocked`, or `unverified`) still
applies exactly as if the host had supplied no evidence at all -- proactive
submission only ever earns speed, never a bypass.

## Mandatory regardless of verdict: post-implementation verification

Every `new-confirmed` and every accepted `extend-recommended` resolution
still requires, after the edit:

1. Confirm the file now exists at the approved path (for new files) or was
   genuinely modified at the approved path (for existing-file edits).
2. Confirm no symbol collision was introduced (the Check 3 search is
   re-run post-implementation; a newly introduced duplicate definition
   fails closure, not just planning).
3. Confirm the file is actually reachable by whatever discovery matters for
   its role -- a new test file must be collected by the test runner; a new
   schema must be loadable; a new implementation file must be importable
   without error.

This is not optional cleanup -- it is the safety net for every case where
the pre-approval checks above had incomplete information (a brand-new repo
has no graph to search; a dead-code collision might turn out to have a
caller the search missed).

## Greenfield / brand-new-project degenerate case

A project with no existing files, or only a handful, is not a special mode
-- it is what this protocol produces when Checks 3, 4, and 5 all return
"no evidence found" simultaneously, for every requirement, because there is
nothing yet to search. In that state:

- Check 1 (existence) trivially passes (nothing exists).
- Check 2 (eligibility) still applies -- a proposed path must still land in
  `application` territory, not e.g. directly under `.git/` or similar.
- Check 3 (collision) trivially passes (nothing to collide with).
- Check 4 (existing-owner search) returns "no evidence," which --under the
  flipped polarity above-- now counts *for* `new-confirmed`, not as a stall.
- Check 5 (convention precedent) has nothing to draw on; this is the
  "absence of precedent falls through cleanly" case already specified
  above, not a blocking failure.
- Check 6 (rationale) becomes load-bearing for nearly every requirement,
  since there is no repository evidence to lean on yet.

This means: no separate "hands-free mode" is needed. The existing approval
lifecycle (profile selection, question/answer, Planning Lock, approval)
still applies in full -- it simply resolves to `new-confirmed` far more
often, because that is the correct and expected outcome for a project that
does not yet have a codebase to search. The profile that should route here
is a dedicated Phase 2 profile (e.g. `greenfield-new-project`), not a
reduced-governance fast lane.

**This case is load-bearing on fixing Issue 25 first.** A greenfield
project's first requirement is, by definition, all-new-files (the
implementation file and its proof/test file both). If the proof-only test
file still cannot join the approved anchor's scope after creation (Issue
25's unresolved gap), a greenfield run would fail to reach a clean closure
on its very first requirement, every time.

## Worked examples

### Example A -- this session's actual schema files (retrospective)

Requirement: add `schemas/host-question-flow-event.schema.json`.

- Check 1: path did not exist. Continue.
- Check 2: `schemas/*.json` classifies as `application`; role would be
  `configuration`/schema, consistent with the requirement's claim. Continue.
- Check 3: no filename-stem or symbol collision (JSON Schema files have no
  code symbols to collide on in the traditional sense; the `$id` field is
  checked for uniqueness instead). Continue.
- Check 4: graph search found `scripts/intake_pipeline.py` with strong
  edges -- but that file is an *importer/consumer* of the shape being
  defined, not an owner of the schema itself. Under today's un-flipped
  polarity, this produced the wrong `scripts/intake_pipeline.py` proposal
  seen live. Under the flipped polarity, this evidence is correctly
  classified as weak-for-new (a consumer relationship, not an ownership
  relationship) -- a refinement this protocol must encode explicitly:
  *consumer* edges (imports, is-imported-by) do not count as ownership
  evidence the way *defines-matching-symbol* or *declares-edit-boundary*
  edges do.
- Check 5: `schemas/` already holds `host-input-contract.schema.json`,
  `requirement-intake.schema.json`, and others, one schema per topic.
  Strong precedent for isolation.
- Verdict: `new-confirmed`, without needing a manual `new:` correction.

### Example B -- host wrongly claims "new file" when one exists

Requirement states: "add a new file for validating user registration email
format." Suppose `scripts/validators/email.py` already defines
`validate_email_format()`.

- Check 3 finds the exact symbol name. Routes to Check 4 question:
  "`validate_email_format()` already exists at
  `scripts/validators/email.py` -- extend it, or state why this must be
  isolated?"
- If the host cannot name a conflicting constraint, verdict is
  `extend-recommended`, not `new-confirmed`.

### Example C -- host wrongly claims "just edit existing file X"

Requirement: "add CryptoPayments support; edit `scripts/payments.py`."
Suppose `scripts/payments.py` only ever handled Stripe-specific webhook
parsing, with no generic payment-provider abstraction.

- Symmetry check (existing-file claim inverted): relationship-edge search
  shows `scripts/payments.py` has no qualifying relationship to crypto
  payment concepts, and its existing responsibility is Stripe-specific.
- Verdict: `unverified` -> clarification naming the mismatch, same as an
  unsupported new-file claim would receive.

### Example D -- near-duplicate directory, Check 3's two sub-checks both fire

Requirement: "add email validation; create `validate2/user.py`." Suppose
`validate/user.py` already exists and defines the same kind of validation
logic.

- Check 1: `validate2/user.py` does not exist yet. Continue.
- Check 2: `validate2/` would classify as `application`. Continue.
- Check 3a (filename/symbol): `user.py` already exists under `validate/`.
  Recorded as weak-on-its-own evidence.
- Check 3b (directory near-duplication): `validate2` is a numeric-suffix
  variant of the existing `validate` directory. Recorded as strong evidence
  on its own.
- Combined 3a+3b: both fired for the same proposal -- the strongest form of
  Check 3 evidence. Routes immediately to a host question naming both
  findings, regardless of what Checks 4-6 would otherwise show.
- Verdict: `extend-recommended` -- never silently approved as `new-confirmed`,
  even if Check 5 (precedent) or Check 6 (host rationale) would otherwise
  have looked favorable.

Contrast: if the requirement instead proposed `payments/user.py` (an
unrelated directory, no near-duplication of `validate`) while `validate/
user.py` existed, only Check 3a would fire (generic filename match, no
directory resemblance) -- that alone does not block; it folds into Check 4
as weak evidence and can still resolve to `new-confirmed` if Checks 4-5
otherwise support isolation.

## Implementation Phases

Mirrors `TAILTRAIL-HOST-QUESTION-FLOW-IMPLEMENTATION-PLAN.md`'s
Purpose/Deliverables/Tests/Exit-criteria format and its "ship independently
useful value every phase" rule. Ordered so each phase only depends on data
shapes the previous phase already produced -- no phase requires the whole
protocol to exist before it can be tested on its own.

### Phase N1 -- Deterministic local checks (1, 2, 3a, 3b, 5)

**Purpose:** Ship every check that needs no code graph and no Navigator
integration -- pure filesystem and string operations. This alone fixes the
concrete `validate2`/`validate` collision case and most duplicate-file risk,
independent of everything else in this document.

**Deliverables:**
- A standalone module exposing one pure function per check (existence,
  path-eligibility via the existing `repository_path_policy`/
  `navigator_scope` classifiers, filename/symbol collision, directory
  near-duplication, convention precedent).
- A typed finding/evidence record shared by all five checks, for Phase N2-N3
  to consume without redefining it.

**Tests:**
- Existence collision (path already exists).
- Eligibility rejection (proposed path lands in generated/excluded territory).
- Check 3a only (generic filename match, unrelated directory) -- does not
  block.
- Check 3b only (directory near-duplication, different filename).
- Check 3a+3b combined -- the `validate2`/`validate` worked example
  (Example D), as a permanent regression.
- Convention precedent present, absent, and mixed/inconsistent.

**Exit criteria:** All five checks are independently callable and
documented; Example D passes as an automated regression, not just a
worked-through example in prose.

### Phase N2 -- Flipped-polarity existing-owner search (Check 4)

**Purpose:** Integrate with Navigator's existing relationship-edge search,
correcting the polarity so weak/no evidence supports `new-confirmed` instead
of stalling as ambiguous, and resolving Open Question 2 (distinguishing
consumer edges from ownership edges).

**Deliverables:**
- Edge-type classification added to the existing relationship-edge
  vocabulary if it does not already distinguish consumer edges
  (imports, is-imported-by) from ownership edges (defines-matching-symbol,
  declares-edit-boundary).
- A flipped-polarity scoring function consuming Phase N1's finding record
  plus this edge classification.

**Tests:**
- A reproduction of the actual observed bug: a schema file's requirement
  must not propose an unrelated importer (like `scripts/intake_pipeline.py`
  was wrongly proposed live) as its owner, because an import/consumer edge
  alone is not ownership evidence.
- A genuine strong existing owner (defines-matching-symbol, direct caller)
  still resolves toward `extend-recommended`, not `new-confirmed`.

**Exit criteria:** The literal live incident from this session is captured
as a permanent regression test and passes.

### Phase N3 -- Rationale, verdict combination, and host-facing wiring (Check 6 + taxonomy)

**Purpose:** Combine Phase N1 and N2's findings into the five-state verdict
taxonomy, wire `extend-recommended`/`unverified` into Navigator's existing
question/clarification mechanism, and implement Check 6 (rationale) as a
tie-breaker only.

**Deliverables:**
- A verdict combinator consuming all six checks' findings.
- Navigator question templates for each verdict that needs host input,
  reusing the existing `SCOPE-Q1`-style mechanism rather than a parallel one.
- The symmetry check (existing-file claim inverted, Example C).

**Tests:** Worked Examples A-D from this document, each as an automated
end-to-end regression, plus Example C's symmetry case.

**Exit criteria:** All four worked examples pass as regressions, including
the symmetry case.

### Phase N4 -- Fast path and mandatory post-implementation verification

**Purpose:** Implement the `new_file_evidence` optional fields on the
host-input-contract and the independent re-verification of each claim
(the "Fast path" section above), plus the mandatory post-implementation
verification step.

**Deliverables:**
- Schema addition for `new_file_evidence` (host-input-contract.schema.json
  or a companion schema).
- A verification runner invoked after implementation: file exists at the
  approved path, no new symbol collision was introduced, and the file is
  reachable by whatever discovery matters for its role.

**Tests:**
- A host submitting correct evidence resolves to `new-confirmed` in one pass
  with zero clarification questions issued.
- A host submitting a false claim (e.g. `collision_claim: "none"` when one
  exists) is still blocked identically to submitting no evidence at all.
- Post-implementation verification independently catches a collision that
  pre-approval evidence missed.

**Exit criteria:** Proactive evidence submission measurably reduces
round-trips without ever weakening the verdict compared to the same inputs
discovered the slow way.

### Phase N5 -- Greenfield profile integration

**Purpose:** Wire this protocol into the `greenfield-new-project` profile
(main implementation plan, Phase 2), confirming the degenerate near-empty-
repository case resolves correctly end-to-end.

**Dependency:** Requires Issue 25 (proof-only test files joining approved
anchor scope) fixed first -- a greenfield run's first requirement is, by
definition, all new files, including its proof file. Note this is a
dependency, not a byproduct: Issue 25's fix (a `proof-path-add` revision
kind writing to `scope_evidence.proof_paths`) is independent plumbing at a
different layer than this protocol. This protocol decides *whether* a path
is new; Issue 25's fix is *how* an approved proof path actually gets
persisted into the anchor, including for paths added mid-run after initial
approval, which this protocol's upfront-declaration fast path does not
cover.

**Deliverables:**
- Profile definition and question-set decision (resolves Open Question 5).
- An end-to-end test against a synthetic near-empty repository fixture.

**Tests:** A first requirement in an empty repository reaches
`new-confirmed` for both its implementation file and its test file, and
closes cleanly (`overall_status: complete`), not just `implemented-
unverified`.

**Exit criteria:** The synthetic greenfield fixture closes cleanly end to
end, proving this protocol and the Issue 25 fix interact correctly together.

## Open questions for review

1. Should Check 3's symbol search be scoped by language (only compare
   Python symbols against Python files, etc.), or should it stay
   language-agnostic for simplicity at the cost of some false positives?
2. For Check 4's edge-type distinction (consumer edges vs. ownership
   edges), does the existing code graph's edge-type vocabulary already
   support this distinction, or does it need a new edge classification?
3. Should `extend-recommended` ever be allowed to auto-resolve without a
   host/user round-trip when the existing-owner evidence is overwhelming
   (e.g. an exact symbol-name match with a direct caller in the same
   function), or should every `extend-recommended` always require an
   explicit human decision?
4. What is the minimum evidence required to accept a host's Check 6
   rationale when Checks 3-5 are all inconclusive (`unverified` territory)
   -- is a stated rationale alone sufficient, or does it need to cite a
   specific existing convention/document?
5. Does the `greenfield-new-project` profile need its own distinct
   question set (per Phase 2's per-profile question design), or does it
   reuse the `new feature` profile's questions with this protocol's
   evidence model swapped underneath?
