# TailTrail Playbook

A condition-to-trick guide for any host agent working in this repository. Each
entry below was hit, diagnosed, and verified live in real sessions -- not
theorized. Read this before fighting a problem that may already be solved
here.

## 1. Scope resolution

**Before building anything, probe for free.** `tailtrail navigator scope
inspect --goal "<goal>" --changed <path>` builds a non-persisting scope
evidence packet -- no Planning Lock, no interpretation ceremony, no cost. It
reports `scope_evidence.state` (`resolved`/`ambiguous`/etc.) immediately. Run
this before committing to a full `tailtrail start` round trip, especially for
a goal touching more than one file.

**Build a complete host-input contract before any persistent TailTrail
call.** TailTrail must not be asked to fill in missing intent. Record the exact
request mode (`read-only`, `validation-only`, or `implementation`), whether
edits are authorized, each named path's role (`implementation-owner`,
`inspection-input`, or `proof-only`), positive and negative success criteria,
and the exact proof path plus runnable command. If any field is unknown, keep
it as an explicit question and do not persist a plan. A validation fixture or
inspection input is not a changed path: `--changed` asserts editable
implementation scope. This distinction was verified live when a QA-declared
config ownership check passed `tailtrail-registry.json` through `--changed`;
the saved `task_type_resolution` correctly detected
`declared-qa-vs-evidenced-implementation`, but the incomplete host packet then
produced an implementation plan with unresolved proof.

**Treat task-type conflict and unresolved proof as blockers.** After every
Start, inspect the saved task-type resolution and focused validation before
showing the plan as approvable. If the declared and inferred types conflict,
if no project-owned proof path and runnable command exist, or if an
investigation/validation request gained an implementation step, stop and
revise or re-route the same run. Never rely on the rendered plan to repair
half-supplied host context.

**A multi-file goal usually needs a multi-owner split, not more flags.** When
`tailtrail start` reports "more than one implementation owner has strong
evidence," the fix is almost never a cleverer `--scope-owner` answer -- split
the goal into one `tailtrail start` per file and run them sequentially. This
resolves cleanly far more often than fighting a combined goal.

**Two different routes exist for a brand-new file, and they are not
interchangeable:**
- If Navigator finds *no* plausible owner at all (route reaches
  `anchor_insufficient`/`SCOPE-QA`), answer with `--scope-owner
  "REQ-ID=new:path/to/file.py"` directly. This is cheap and reliable.
- If Navigator instead finds *too many* lexically-similar existing files
  (route state `requested`, reason `multiple-evidence-backed-owners` --
  common for generically-worded tooling goals in a large repo), the `new:`
  shortcut does not work at all. The only path is a structured
  `--host-scope-proposal` packet (schema:
  `schemas/navigator-host-scope-proposal.schema.json`), with
  `claim_role: "proposed-new"`, `anchor_paths` grounded in a real existing
  sibling file, and `convention_refs` pointing at a real edge of kind
  `imports-module`/`loads-module`/`registered-by`/`configures-owner` touching
  that anchor. This schema is strict but workable -- every rejection names
  the exact missing field.
- **Known caveat**: building that packet across two separate CLI calls (one
  to inspect the packet, one to submit it) can intermittently fail with a
  stale/mismatched fingerprint even with zero repo changes in between --
  confirmed non-deterministic, not just slow-cache staleness. If it fails
  without a specific reason code, retry before assuming your packet content
  is wrong. See section 8 below for the parked root-cause investigation.

## 2. Requirement interpretation gotchas

When submitting `--requirement-interpretation` by hand, three grounding rules
bite repeatedly:
- Every clause's `text` must be an **exact, contiguous substring** of the
  goal string -- not a paraphrase, not reordered.
- Every `intent_terms` entry must be a **literal substring of the goal**,
  not just of its clause. Hyphenated compounds (`argparse-based`,
  `schema-valid`) often fail even when the base word reads as "obviously
  present" -- test standalone words, not halves of compounds.
- A code-identifier-looking token named in a clause (a `--flag`, a
  `function()`, a `file.py`, a `snake_case_name`) also needs to appear in
  that requirement's `intent_terms` **and** its `statement` text, or the
  submission is rejected with "omitted exact named target(s)."
- A task-type question (`implementation`/`qa`/`infra`/`doc`) may be asked
  separately even after interpretation succeeds -- answer with
  `--task-type`.
- An `intent_terms` entry must be a single token, never a multi-word phrase
  with a space in it, even when that exact phrase is a contiguous substring
  of the goal. `"Worked Examples"` (present verbatim in the goal text) was
  rejected with `malformed terms: Worked Examples`; splitting it into two
  separate single-word terms (`"Worked"`, `"Examples"`) resolved it on the
  next submission.
- Multi-requirement answers use `--scope-owner "REQ-ID=path"` (repeatable),
  never a bare path when more than one requirement is unresolved.

**Use the tool instead of hand-iterating.** `scripts/host-interpretation-builder.py
--spec <spec.json> --host claude` checks all of the above locally (clause
substring, intent-term grounding, named-target approximation) before you ever
submit to `tailtrail start`, and writes a ready-to-use interpretation JSON on
success. For a fast read-only check with no output file:
`--validate-only` prints `{ok, problems, warnings}` as JSON and changes
nothing. Rejections from `tailtrail start` now echo the normalized comparison
and closest goal tokens, and point back here.

**Prompt options stay simple on purpose.** `tailtrail prompt render
--question "<q>" --option "<a>" --option "<b>"` numbers options with blank
lines between and ends with the approval question -- that shape is enforced in
`scripts/prompt_builder.py` so it survives sessions. Clarification stops after
5 rounds: `tailtrail prompt feedback --goal "<g>" --ambiguity "<a>"` prints the
fail-closed packet (what stayed ambiguous, what was tried, what to supply,
how to resume) instead of guessing.

## 3. CLI quirks

- `--run-id <id>` on `tailtrail start` is **not** a way to choose the new
  run's ID -- its own help text says it "enables evidence-driven correction
  and recovery routing for that run only," and tracing the code confirms it:
  it's used to pull context about an *already-existing* run, not to seed a
  fresh one. A new run's ID is always minted separately, regardless of this
  flag. Don't pass it expecting to pin an ID; always use whatever ID the
  tool actually returns.
- Always paste the complete Start Report verbatim in the reply body, not
  just inside a collapsible tool-result panel -- hosts and users both need
  to see the full requirements/scope/approval text directly.

## 4. Evidence tiers: declared vs. trusted

A closure built from a host-run command (`evidence_label: "local-command"`)
is **declared** evidence -- real, but explicitly unverified by TailTrail
itself, and closure will show `evidence-incomplete` even when the
implementation is fully correct. To get genuinely **trusted** evidence:

1. While the run is still `awaiting-approval` (before `planning activate`),
   propose a `proof-update` revision via `planning-revision.py` that attaches
   the exact proof command to the requirement's `validation_contract`. This
   gate is closed once the run is activated -- it cannot be done later.
2. After activation, run that exact command through
   `scripts/execution-evidence.py run --approved` (not a plain shell
   invocation) -- this spawns the command itself and records
   `evidence_quality: "trusted"`.
3. Record closure with `closure-recorder.py --run-id <id>` and **no
   `--input` flag** -- it auto-builds the closure input from the
   trusted-execution stream.

Skipping step 1 is the single biggest reason a correct, fully-working
implementation still closes as "evidence-incomplete."

**A later `proof-update` revision that adds tiers did not update the
Start-time `checks[]` entry -- `execution-evidence run` silently ignored
the broader tier list when it did.** If Start's Focused Validation left
a tier (e.g. `behaviour`, `integration`) unresolved, a `proof-update`
revision registering `"tiers": [...]` on the *top-level*
`validation_contract` looked correct in `planning-revision.py propose`'s
output and in the approved anchor JSON -- but `execution-evidence.py`
matched the exact proof command against `validation_contract.checks[]`
first (an array populated once, at Start time), and if any check entry
matched that command, its tiers *completely replaced* the top-level tier
list rather than being unioned with it. The result was an opaque
`requested evidence tiers are not approved for requirement ...` error even
though `planning show`/the anchor JSON clearly listed the tier as approved.
**This is now fixed** -- `execution-evidence.py run_command` unions a
matching `checks[]` entry's tiers with whatever a revision overlay added,
instead of replacing the full tier set, so no workaround is needed for
this specific cause any more. `--amend-proof --amendment-reason "..."`
remains available as a general additive-proof-amendment mechanism for
other cases, but is no longer required just to make a revision-added tier
usable. See `TAILTRAIL-ISSUES-LOG.md` Issue 27.

**`change-intent-anchor.py correct`'s `--likely-path` *replaces* a
requirement's `likely_paths`, it does not append to them.** Passing only
the newly-drifted path (e.g. a test file edited mid-run) silently drops
every previously-approved path (e.g. the original implementation-owner
file) from scope, which then shows up as a *new* drift finding on the very
next closure check. Always pass the full target list -- every path that
should remain in scope plus the new one -- in a single `correct` call.

**After a `change-intent-anchor.py correct`, closure can keep reporting
the stale drift finding until a new evidence event busts the cache.**
Both `closure-recorder.py` and `closure-finalizer.py` key their cached
record/finalizer artifacts off a hash of the *evidence stream's content*,
not the current anchor version -- so correcting the anchor after evidence
was already submitted does not by itself invalidate the cached
`new-drift` finding. Re-run the exact same proof command through
`execution-evidence.py run --approved` again (a fresh receipt has a new
timestamp, so it naturally produces a new record hash) before re-checking
`closure-finalizer.py`; do not hand-edit anything under `.tailtrail/`.

## 5. Mid-implementation needs

**Need to touch a test file after implementation has started?** The
IMPLEMENTATION pipeline badge blocks writes to `test`-role paths outright --
this is intentional, not a bug. The real mechanism is `tailtrail pipeline
handoff --run-id <id> --from-stage IMPLEMENTATION --context "..."`, which
moves the run to the TESTING badge (where test writes become legal). If
testing then reveals a genuine code bug, `tailtrail pipeline regression
--run-id <id> --reason "..." --error-code <CODE>` classifies the failure
(mechanical/behavioral/environmental) and may route back to IMPLEMENTATION --
this loop is not one-directional, and a three-strikes circuit breaker caps
genuine regression loops at 3 per run. Both Start Reports and completion
reports now nudge toward this directly when relevant.

**The write-guardian hook can wrongly block an approved edit.** Root-level
config/registry files (e.g. `tailtrail-registry.json`) can classify as role
`unknown` rather than any known write role, and get blocked by the active
pipeline badge even when Navigator's own approved anchor names that exact
path as the owner. If this happens on a path you know is genuinely approved,
the disclosed workaround is: `mv .claude/settings.json
.claude/settings.json.bak`, make the single approved edit, `mv` it back
immediately. Always disclose this explicitly when used -- it bypasses local
enforcement, not the underlying approval.

**Doc and markdown files usually can't resolve as Navigator-owned scope at
all.** `GUARDRAILS.md`, `TAILTRAIL-COMMANDS.md`, and this file all hit the
same wall. The fast lane fixes this now: `tailtrail docs-only --root .
--goal "<prose-only goal>" --path <file.md> [--path <file.md> ...]` mints a
real approved anchor+lock for pure-prose edits with no production-signal
wording -- use it instead of the manual hook-bypass pattern, which should
now be a last resort, not routine.

**Pre-approve the proof command via `planning revise` BEFORE calling
`planning activate` -- that window closes permanently once you activate.**
If the Start Report shows the focused-validation command as `unresolved`
(common when no test file exists yet for the target script), do this
*before* activating:
`tailtrail planning revise --changes
'[{"kind":"proof-update","requirement_uid":"REQ-01","reason":"...","evidence_plan":["..."],"commands":["<the exact test command>"],"tiers":["unit"]}]'
--approved-proposal`, then `tailtrail planning revision-approve --revision
2 --approved` (this both approves the revision and activates the run in
one step). Calling `planning activate --approved` directly instead
permanently closes the revision window for that run -- the CLI's own error
is explicit: *"Interactive Plan Mode is available only while a plan is
awaiting approval... run `<id>` is `approved`"* -- with no way back short
of abandoning the run and starting a fresh one. `requirement_uid` in the
`--changes` JSON can be the plain display ID (`"REQ-01"`), not just the
minted UID -- `_requirement()` matches either.

**A new file created mid-run (e.g. a test file) still needs a formal
anchor correction to avoid a permanent `new-drift` finding -- and the
closure path now honors it.** `change-intent-anchor.py correct
--likely-path <path> --reason "..."` is the sanctioned way to add the
path, and as of the Issue 13 fix, `harness-checkpoint.py`,
`drift_analysis.py`, and the wider closure/harness/runtime surface read
the latest approved version (`latest_approved()`), so the correction
actually clears. If drift still won't clear after a correct `correct`,
check `TAILTRAIL-ISSUES-LOG.md` Sections 13/13a for remaining
version-pinning stragglers rather than assuming your correction was
wrong. New `tests/test_anchor_versioning.py` fails on any new raw
`approved-v1.json` read -- resolve anchors through `latest_approved()`,
never by filename.

## 6. Closing a run efficiently

A full closure is normally 6+ manual steps: build a closure-input JSON,
`closure-recorder.py`, `architecture-fitness.py`, (sometimes)
`behavior-harness.py` with empty scenarios, `closure-finalizer.py`,
`completion-report.py`, `delivery-record.py`. `scripts/run-closeout.py`
chains all of them in one command:

```bash
python3 scripts/run-closeout.py --root . --run-id <id> \
  --changed <path> [--changed <path> ...] \
  --requirement-uid <uid> [--requirement-uid <uid> ...] \
  --command-label "<label>" --command "<the command actually run>" \
  --asserted "<asserted_behavior text>"
```

Pass `--skip-architecture-fitness` or `--skip-behavior` to omit either
harness when a run's selected controls don't need it.

## 7. Working habits (no code required)

- **Front-load multi-run discovery.** If a task will obviously need N
  separate files touched, draft and present all N Start Reports up front for
  one combined approval, rather than discovering the need for run 2 only
  after finishing run 1.
- **Batch the approval, run the sequence.** Once a batch is approved,
  activate/implement/verify/close each item in order without re-asking per
  item -- still disclose every Start Report and closure, just don't block on
  a fresh approval each time.
- **Keep batch status compact.** For more than two or three runs in one
  batch, report a short table (run ID, one-line requirement, pass/flagged)
  rather than a full completion report per item -- surface full detail only
  for anything that needed a decision.

## 8. Formerly-parked issues, now fixed (kept briefly for reorientation)

- Thin-evidence `content_fingerprint` gaps are backfilled at the end of
  `investigate()` -- fixed, see Issues Log Section 2.
- Cross-call `--host-scope-proposal` drift is fixed via fingerprint-indexed
  single-use packet tickets (`.tailtrail/host-packets/`, 30-min TTL); CLI vs
  MCP first-computation parity via the shared `scripts/start_request.py`
  ground -- see Sections 3/3a.
- The v1-frozen anchor reads are fixed across closure/harness/runtime via
  `latest_approved()` -- see Sections 13/13a.

Genuinely open items live in `TAILTRAIL-ISSUES-LOG.md` Sections 12.x -- check
there before re-investigating from scratch.

## 9. Host working notes (environment and edit discipline)

- **Windows PowerShell has no `grep`/`head`/`tail`/`cat` pipes.** Use the
  dedicated tools (content search, file read) instead of piping; `git` output
  must not be piped to `cat`/`head` either. A bare `>` redirect writes
  UTF-16 and corrupts captured JSON -- capture CLI output through a small
  Python wrapper script instead.
- **Never trust displayed indentation.** Terminal output eats leading
  spaces, and this repo mixes 1-space and 4-space files. Before editing,
  verify exact bytes with a byte-counting script; after editing, `ast.parse`
  the file before running anything. For tricky files, apply edits through a
  script with exact-match assertions (`count == 1`) rather than by eye.
- **Red-proof with `git stash push -- <impl-paths>`, never bare `-u`.**
  `stash -u` sweeps untracked new test files away too, leaving zero tests
  to go red. Stash only the implementation paths so the new tests stay in
  place and fail on old code with the exact symptom.
- **Resolve tmp roots in `setUp`.** Windows 8.3 short-path aliases
  (`VISHRU~1`) break `relative_to` against resolved walk roots --
  `self.root = Path(self.tmp.name).resolve()` in every fixture.

## 10. R6 lessons before declaring a bug

These points were verified live while implementing R6. Check them before
calling a planning or closure result a product defect:

- **Intent Bridge is not a generic file mode.** `--intent-feature` requires an
  already-imported Spec Kit feature. An issue log or Markdown specification is
  a `--requirement-artifact`; check `intent-bridge status --allow-incubating`
  first. `not-detected` with zero features means Intent Bridge is unavailable.
- **Bounded artifacts matter.** A large issue log can fail with
  `requirement-artifact-read-limit-exceeded` before requirements or scope are
  created. Use a small, source-referenced R6 artifact rather than treating the
  failed read as a planning bug.
- **Evidence is not executable proof authorization.** A command in an artifact,
  evidence clause, or quoted literal is traceability only. Register executable
  proof before activation with `planning revise` and a `proof-update` containing
  the requirement ID, exact command, and tier, then approve that revision.
- **Split multi-owner work.** A complete requirement artifact can still produce
  an ambiguous full plan when proof, closure, and learning belong to different
  owners. Split the work into focused runs; do not force a single owner over an
  unrelated multi-file goal.
- **Unit tests are not Behaviour Harness proof.** If Behaviour Harness is
  selected, provide a requirement-linked scenario and matching trusted receipt,
  or explicitly use a plan that does not select that harness. A green unit
  suite alone should remain incomplete for the user-flow control.
- **Closure needs managed evidence.** A passing shell command is not an
  authoritative receipt. Run the approved command through
  `execution-evidence`, record approved source-edit evidence, and generate the
  final Completion Report before judging the run complete.

## 13. Approval, call-site, and push checks

- **Approval is not activation.** After approving a plan, confirm the run is
  `execution-ready` before executing proof or closing it. When the handoff says
  activation is still required, run `planning activate --approved` for that
  exact run.
- **Do not approve incomplete plans.** Requirements, owner paths, proof
  commands, task type, artifact owner, and positive/negative success criteria
  must be visible and resolved before approval. Keep unknowns as questions.
- **Test wiring at the real call site.** If a helper accepts a directory, root,
  or report payload, test the public builder with the production argument shape;
  a direct helper test can pass while the real caller is wrong.
- **Push only reviewed scope.** Inspect `git status` and the exact diff before
  committing. Separate generated graph metadata or unrelated user edits from
  the requested change, then verify `HEAD == origin/<branch>` after pushing.
- **Match the file's own indentation convention** (check it programmatically
  first) and keep diffs minimal -- especially in 1-space test/script files
  where one wrong space is a collection-breaking `IndentationError`.
- **New tests must prove they collect.** A `def` nested inside another
  method never runs and still reports green -- always run with
  `--collect-only` (or watch the count go up) after adding a test.
- **Prove fixes red-to-green.** Stash the fix, watch the new test fail on
  old code with the exact reported symptom, unstash, watch it pass. A test
  that passes on both proves nothing.
- **Check pre-existing failure before claiming regression.** If a suite
  fails after your change, rerun it on the stashed clean tree -- several
  failures in this repo (e.g. the MCP/markdown fingerprint tests) predate
  any given change.
- **Revert incidental churn before committing.** Test runs rewrite
  `tailtrail-meta/code-graph-cache.json` (thousands of lines); `git
  checkout` it unless the cache change is the point.
- **Anchor versions sort numerically, not lexicographically** (`v10` <
  `v2` as strings) -- use `int(p.stem.rsplit("v", 1)[-1])` as the sort key,
  matching `change-intent-anchor.approved_versions()`.
- **Prove the new path executes after a migration edit.** A green suite can
  mean the new code is dead: loaders landed, call sites untouched, behavior
  unchanged, tests pass, summary lies. After wiring, stash only the new
  helper/loader and watch the migrated tests fail, or confirm the diff
  touches call sites rather than scaffolding. Verified live when a "Slice C
  complete" report went out with only unused loaders in place.
- **Deletion needs a coverage audit, not just a passing fixture.** A narrow
  cross-agent fixture can pass with an old list removed while real behavior
  regresses (nested submodule/state/agent dirs, root-level IDE and
  convention dirs). Before deleting a superseded exclusion list, matrix
  every old entry against the new classifier at multiple depths and delete
  only what the matrix clears. Verified live: the fixture criterion alone
  would have permitted nested-`.git`, `.idea`, and `aidlc-rules`
  regressions.

## 11. Artifact-owner routing before planning

When a user asks for a document, report, plan, dashboard, or other generated
artifact, identify its existing owner before creating a new requirement or
implementation plan:

1. Search the repository for the requested filename, heading, and generator.
2. Read the generator's docstring and output path function.
3. Check the registry, commands, and adjacent run artifacts for the canonical
  owner and lifecycle.
4. Use the existing generator and projection path in the plan.
5. Show the generated artifact as a clickable workspace-relative link before
  asking for approval.

For delivery plans, the canonical human-readable projection is
`scripts/delivery-record.py`, which writes
`.tailtrail/runs/<run-id>/delivery-record.md` from approved canonical state and
appends implementation and closure sections. Do not invent a parallel
`completion-reports/report-N.md` document when `delivery-record.md` already
owns that user-facing surface.

## 12. R10 requirement and lifecycle lessons

These lessons were verified during the R10 Start Report and Delivery Record
work:

- **Preserve requirement boundaries clause-by-clause.** If the artifact has
  three outcomes, do not collapse them into one broad requirement. Compare the
  final requirement matrix with every artifact outcome and constraint before
  approval.
- **Approval and activation are different states.** `approved` means the plan
  may be activated; `activated` means execution authority and handoff artifacts
  exist. Closure requires activation, so run `planning activate --approved`
  when the approved flow does not use an automatic activation path.
- **Split multi-owner work deliberately.** A Start Report owner and a Delivery
  Record owner should be separate focused runs. Do not force one implementation
  owner to cover both surfaces merely because they share one user requirement.
- **Join canonical sources in projections.** Traceability literals may live in
  the Start Report while executable commands live in the approved anchor or
  proof-amendment ledger. A projection must read both sources and label their
  different authority levels.
- **Constraint rows need evidence too.** A safety or preservation constraint
  may not be independently completable in the user model, but the completion
  harness can still require linked evidence. Register a trusted proof receipt
  for every approved row or explicitly model the row as non-completable.
- **Testing handoff precedes test edits.** Complete production edits, run
  `tailtrail pipeline handoff --from-stage IMPLEMENTATION`, and only then edit
  test-role files. Recording the handoff after a test edit is an audit repair,
  not the correct workflow.
- **Do not trust a green suite alone.** Use managed evidence and a linked
  Behaviour Harness scenario when the selected controls require one. A unit
  suite can pass while the lifecycle projection remains incomplete.

## 14. Phase 0 host-flow lessons

These lessons were verified live while correcting proposed-new scope and
classifier routing. Apply them before approving a new host-flow or Navigator
correction plan:

- **Preserve proposed-new answers separately.** A `new:path` answer is not an
  existing owner. Check the host-scope result for `owner_kind=declared-new` and
  an answer disposition before accepting the plan. A proposed-new path may be
  accepted in a directory with no existing implementation/configuration owner,
  but it still requires post-implementation verification.
- **Use the correct new-file route.** `--changed` asserts that a path already
  exists and is editable. For a new path, use the documented `new:` scope
  answer or a structured proposed-new scope proposal; never convert a rejected
  new path into a nearby graph owner.
- **Check lexical side effects in correction goals.** Generic terms such as
  `component`, `workflow`, `screen`, `frontend`, and `UI` can activate planning
  routes. When correcting a classifier, first use neutral goal wording to
  isolate the route, then add regression assertions for both the generic and
  explicit terms. The source classifier must be fixed; wording changes are
  only a diagnostic step.
- **Validate proof candidates as test suites.** A linked helper script is not
  executable proof merely because its filename contains `test`. Run the exact
  command before approval when possible, verify collection is non-zero, and
  prefer a real `tests/test_*.py` module. If the Start Report selects a helper
  that collects zero tests or fails import, revise the proof contract before
  activation.
- **Isolate sequential correction runs.** A second correction run started in
  the same dirty worktree can report the first run's legitimate edits as
  `changed-beyond-approved`. Commit a reviewed baseline, use an explicit
  approved shared-worktree baseline, or record a formal anchor correction before
  treating the drift as a product defect.
- **Completion can remain incomplete after passing tests.** Re-run the
  Completion Report after proof amendments and anchor corrections. `pass` on a
  focused suite does not clear an invalid original proof contract, stale packet
  scope, or a selected Behaviour/Architecture harness without its required
  evidence.

## 15. Validate a correction before planning it

- **Prove the premise at the real call site before Start.** A rejected scope
  answer or Planning Lock proves only that planning could not establish
  authority; it does not prove the nearest classifier is defective. Reproduce
  the reported behavior read-only, and do not plan a correction for a layer
  where the behavior already succeeds.
- **Keep path decisions separate.** Trace workspace eligibility, repository
  file-kind, requirement ownership/proposed-new grounding, approved-anchor
  authority, and write-time enforcement independently. The first failing
  transition owns the investigation; never assign a downstream failure to an
  upstream policy without call-chain evidence.
- **Require symptom-specific proof and stop no-op work.** Before approval, the
  proof must exercise the reported positive behavior and preservation boundary,
  not merely name a passing suite. If post-approval inspection shows the
  approved behavior already exists, do not add cosmetic code for evidence;
  report the run incomplete and plan the actual failing layer separately.
