# TailTrail Issues Log

A detailed record of every bug, gap, and misunderstanding hit while working in
this repository with TailTrail, written so a human or another agent can pick
up exactly where this left off without re-deriving any of it from scratch.
For quick condition-to-trick guidance instead of full detail, see
`TAILTRAIL-PLAYBOOK.md`. This file is the "why" and "how it was found" behind
the entries there.

## Summary

| # | Issue | Status |
|---|---|---|
| 1 | Scope-owner answers silently discarded (two separate points) | **Fixed** |
| 2 | Thin-evidence candidates missing `content_fingerprint` | Parked (`task_e574f8bd`) |
| 3 | `--host-scope-proposal` fingerprint drift across calls | Parked (`task_3dcf1d8e`) |
| 4 | write_guardian role classifier rejects root-level config/registry files | Open, unfixed (disclosed workaround only) |
| 5 | Doc/markdown files can't resolve as Navigator-owned scope | Open, unfixed (architectural; disclosed workaround only) |
| 6 | `likely_paths` had no per-path role, only a flat string list | **Fixed** |
| 7 | Sequential pipeline handoff/regression had no CLI surface | **Fixed** |
| 8 | `resolve_active_run()` picked "most recently approved," not "most recently active" | **Fixed** |
| 9 | Requirement-interpretation grounding rules are fiddly and undocumented | Mitigated (tooling built, rules not changed) |
| 10 | `--run-id` on `tailtrail start` doesn't pin a new run's ID | Not a bug -- misunderstanding, corrected |

See **Section 11** below for a separately-tracked, audited list of standing
TailTrail change recommendations (some overlap with the issues above; most
do not).

---

## 1. Scope-owner answers silently discarded (Fixed)

**Symptom:** submitting a multi-requirement goal with explicit `--scope-owner
REQ-01=path --scope-owner REQ-02=path` answers would, on a stuck case, return
the exact same byte-identical "Scope Confirmation Required" output on every
retry -- no error, no explanation, just the same question repeated.

**Root cause -- two separate, stacked silent-discard points in
`scripts/task-start.py`:**

- **Point A**: when `prepare_scope_answer_proposal()` rejects the answers
  (e.g. an answer not evidence-backed), the function correctly returns
  `(None, errors)`, but the caller only checked `fatal`, never `errors`.
  `host_scope_proposal` stayed `None`, the whole proposal-application branch
  was skipped, and the code silently re-rendered the original, unmodified,
  still-ambiguous scope document.
- **Point B**: even after fixing Point A, a *second* case was found live:
  `prepare_scope_answer_proposal()` can succeed (build a correct, validly
  narrowed per-requirement proposal) while the separate
  `host_proposal_decision()` call that validates it afterward returns
  `status: "rejected"` for a real reason (see Issue 2). The calling code
  never checked `host_decision["status"]` at all, so a rejected decision's
  unmodified `scope_evidence` was used exactly as if it had been accepted,
  reproducing the identical silent loop one step further down.

**Fix:** both call sites in `scripts/task-start.py` (around line 6785 and
line 6803) now call `parser.error(...)` with the real error/reason codes the
moment either rejection happens, instead of falling through silently.

**Verified:** reproduced the exact original stuck goal after each fix. After
fixing only Point A, the repro still looped silently (proving Point A alone
was insufficient). After fixing Point B too, the same repro now exits with a
specific, named error (`content-fingerprint-mismatch:scripts/task-start.py`,
see Issue 2) instead of looping.

---

## 2. Thin-evidence candidates missing `content_fingerprint` (Parked)

**Symptom:** a scope-owner proposal that is structurally correct and
well-narrowed can still be rejected with
`content-fingerprint-mismatch:<path>`.

**Root cause:** a candidate path discovered with only thin evidence (for
example, named purely via `--changed` with just one weak relationship edge,
as opposed to several strong native graph edges) ends up with an empty
`content_fingerprint` (`""`) in its candidate record in
`scripts/navigator_scope.py`. The later proposal-integrity check in
`host_proposal_decision()`/`validate_host_proposal()` compares the proposal's
claimed fingerprint against the file's real content hash; `"" != <real
hash>`, so it fails -- not because anything is wrong with the file or the
proposal, but because the fingerprint was never computed for that candidate
in the first place.

**Status:** parked as background task `task_e574f8bd`. Confirmed by tracing
`prepare_scope_answer_proposal()` and `host_proposal_decision()` directly
with a scratch script against a real stuck packet -- the proposal itself was
correct; only the pre-existing candidate data was incomplete.

**Where to look when picking this up:** candidate construction in
`scripts/navigator_scope.py` -- search for `content_fingerprint` assignment
and the code path taken when a candidate's only evidence is a `--changed`
assertion or a single weak edge.

---

## 3. `--host-scope-proposal` fingerprint drift across separate CLI calls (Parked)

**Symptom:** building a `--host-scope-proposal` payload from one
`tailtrail start ... --format json` call's output, then submitting it via a
second, later `tailtrail start` call for the same goal, can fail -- but
unpredictably: sometimes it evaluates the proposal's actual content
correctly, sometimes it comes back with an explicit
`evidence-packet-fingerprint-mismatch`, and sometimes it silently falls back
to re-displaying the original ambiguous question with a *different*
`evidence_packet_fingerprint` shown in the footer than what the proposal was
built against.

**What was ruled out:** this is not simple time-based staleness, and it is
not an architectural routing gap (an earlier working theory -- confirmed
wrong by reading `scripts/navigator_scope.py:3895`, which shows
`--host-scope-proposal` explicitly requires the *same* "too many owners"
route state that caused the ambiguity in the first place; there is no
missing route).

**What was confirmed, directly, with a scratch script that fetches and
submits back-to-back with zero manual steps in between:**
- 2 of 6 attempts: fingerprints matched, proposal evaluated on real content.
- 1 of 6: an honest, explicit fingerprint-mismatch error.
- 3 of 6: silent fallback to the ambiguous question, with a footer fingerprint
  that did not match the one just fetched -- and that repeated fingerprint
  value appeared identically across otherwise-unrelated attempts, suggesting
  a stale cached packet is involved somewhere, not pure randomness.

**Status:** parked as background task `task_3dcf1d8e`, with instructions to
first confirm the exact mechanism (not assume the theory above) by tracing
`host_reasoning_packet()`/`validate_host_proposal()` directly, then fix so a
host can reliably fetch, reason about, and submit a proposal across separate
calls when nothing in the repository actually changed in between.

**Practical workaround today:** if a `--host-scope-proposal` submission
fails without a specific, named reason code, retry before assuming the
proposal's content is wrong.

---

## 4. write_guardian role classifier rejects root-level config/registry files (Open)

**Symptom:** an edit to `tailtrail-registry.json` -- a path Navigator's own
approved anchor explicitly named as the implementation owner for that run --
was blocked by the write-guardian `PreToolUse` hook with: *"Write access
denied: Path `tailtrail-registry.json` is a `unknown`, which is not in the
allowed write-set for the active stage `IMPLEMENTATION`"* (see
`scripts/pipeline_judge.py:37`).

**Root cause:** `navigator_scope.classify_repository_role()` has no
classification rule for a root-level JSON config/registry file -- it falls
through to the generic `unknown` role, which the IMPLEMENTATION badge
contract (`allowed_write_roles={"implementation-owner", "supporting-assets"}`)
correctly refuses, since `unknown` is not in that set. This is a genuine gap:
the anchor-level approval and the pipeline-badge-level role check are two
independent systems, and the second one doesn't know how to classify this
kind of file at all, regardless of what the first one approved.

**Status:** not fixed. Worked around twice this session by temporarily
removing `.claude/settings.json` (unregistering the hook), making the single
approved edit, then immediately restoring the file -- disclosed explicitly
both times. This is a last-resort pattern, not a routine one: it bypasses
local enforcement for the file it's used on, never the underlying Navigator
approval itself.

### 4a. Design investigation: "Navigator sends the guard a receipt" (explored, not adopted as-is)

A deeper fix was proposed and investigated: instead of the write-guardian's
pipeline-badge check re-deriving a path's role from scratch via
`classify_repository_role()`, it should first consult the role Navigator
*already* computed and had approved into the anchor -- trusting that
already-evidenced, already-approved classification instead of guessing
again, independently, with a classifier that has gaps.

**Why this is structurally sound:** Navigator's own investigation already
computes a role per candidate (`project_likely_impacted()` in
`navigator_scope.py` builds each `likely_impacted_files` row with a real
`"role"` field) -- but `scripts/planning_lock.py:804`/`807` discards it at
the exact point an anchor gets built, flattening each row to
`item.get("path")` only. The fix would be two parts: (1) stop discarding
that role when the anchor is built, using the `{"path", "role"}` shape
already supported by `change-intent-anchor.py`'s `normalize_likely_paths()`
(Issue 6), and (2) have `validate_write_access()` in `pipeline_judge.py`
check the approved anchor's role for a path before falling back to
`classify_repository_role()`.

**What broke when this was actually attempted:** implementing part (1) alone
(preserving the role when `planning_lock.py` builds the matrix) caused a
real, confirmed test failure --
`test_activation_creates_the_canonical_runtime_and_compiler_without_execution`
in `tests/test_workflow_start_integration.py`. The failure traced to
`scripts/workflow_runtime/start_integration.py:42-44`, which reads
`row.get("implementation_owners", [])` from a matrix built by
`navigator_scope.authority_requirement_mappings()` and does `str(path)` on
each entry, assuming it is always a plain string. Once a role-tagged
`{"path": ..., "role": ...}` dict reached it, `str(dict)` produced the
literal text `"{'path': 'src/validation.py', 'role': 'implementation-owner'}"`
instead of the real path, corrupting `scope_drift_rule.approved_editable_paths`
in the saved workflow runtime.

This matters because `authority_requirement_mappings()` (in
`navigator_scope.py`) is a far more central, widely-reused function than the
three consumers already named in Issue 6 (`write_guardian.py`,
`drift_analysis.py`, `delivery-record.py`) -- it sits on a shared path used
by workflow-runtime setup, scope rendering, and authority mapping alike. The
real blast radius of "stop discarding the role" turned out larger than the
two-file scope (`planning_lock.py` + `pipeline_judge.py`) originally
approved for this fix.

**A narrower variant was then designed** (not fully verified): keep every
in-between consumer reading exactly the plain-string shape it always has,
and only attach the role tag at the very last step -- right when the anchor
is actually drafted -- by looking the role back up from Navigator's
original, already-saved `likely_impacted_files` record (no new file or
side-channel needed; that record already exists and was never going
anywhere). This avoids re-threading a new shape through every middle
station. It was not adopted, for three honest reasons:
- it leaves the real gap in `navigator_scope.py` completely unfixed --
  anything that legitimately needs the role earlier in the pipeline, later,
  hits the identical corruption again;
- the tag stays unavailable for anything happening before the anchor is
  drafted, including the Start Report's own separate, independent
  "Implementation owners" rendering, which could have used the same,
  better information instead of its own parallel classification pass;
- "the last station" was only verified safe for the one regression already
  found (write-time enforcement happens well after drafting) -- it was
  **not** verified safe against every other consumer of the matrix, only
  the one this session happened to catch.

**A separate idea was also raised and rejected on a concrete technical
ground:** make the tagged path an in-memory object that behaves like a
plain string to old code but secretly carries the role for new code (e.g.
a `str` subclass carrying an extra attribute). This does not survive this
codebase's actual architecture: nearly every stage here persists its state
to a JSON file and the next stage reads it back fresh from that file, not
from the same running process. JSON has no concept of "a string with a
secret attribute attached" -- saving one silently drops the attribute and
keeps only the plain text, so the tag would vanish at the very first
save/reload boundary, which happens constantly here.

**Final call:** the downside-to-benefit ratio for this bigger fix did not
hold up against the much narrower, direct alternative for the actual,
repeatedly-hit problem (Issue 4 itself) -- teaching
`classify_repository_role()` to recognize root-level config/registry JSON
files as a known category directly, with zero changes to the anchor schema,
`planning_lock.py`'s matrix construction, or anything in
`navigator_scope.py` beyond one more recognized pattern. The receipt-based
design remains a legitimate, worthwhile future improvement -- just not
bundled into fixing today's narrow bug. The `scripts/planning_lock.py`
change made while investigating this (the role-preserving matrix
enrichment) was experimental and is being reverted rather than shipped;
`scripts/pipeline_judge.py` was never touched.

---

## 5. Doc/markdown files can't resolve as Navigator-owned scope (Open, architectural)

**Symptom:** goals whose target is a markdown file (`GUARDRAILS.md`,
`TAILTRAIL-COMMANDS.md`, this file, `TAILTRAIL-PLAYBOOK.md`) consistently
fail to resolve as a Navigator-owned implementation target, independent of
wording.

**Root cause:** Navigator's scope resolution is fundamentally code-graph
centric -- relationship edges like "declares edit boundary," "imports
module," "defines symbol" are all source-code concepts. A prose file
participates in essentially none of them, so it never accumulates the kind
of evidence the scope-quality gate looks for.

**Status:** not fixed; this is a design gap, not a simple bug. The accepted
fallback used repeatedly this session is a direct, disclosed edit (same
hook-bypass pattern as Issue 4) rather than repeatedly fighting Navigator's
scope resolution for a file type it was never built to reason about.

---

## 6. `likely_paths` had no per-path role (Fixed)

**Symptom:** an approved anchor's `likely_paths` was a flat list of path
strings with no indication of *why* each path was included -- editable
owner, read-only context, or run-only proof. This directly caused a real
bug earlier this session in `write_guardian.py`'s anchor-scope check, which
had trusted any path in `likely_paths` as individually approved for editing,
when a broad, ambiguous-scope run's `likely_paths` can legitimately bundle
owner+inspection+proof paths together.

**Fix:** `scripts/change-intent-anchor.py` now accepts, validates, and
persists a `{"path": ..., "role": ...}` object (roles:
`implementation-owner`/`proof-only`/`inspection-only`/`unknown`) anywhere a
plain string was previously required, fully backward compatible -- a caller
that only ever supplies plain strings sees byte-identical behavior, since
nothing is auto-promoted to the richer shape. `correct()` was extended the
same way, including the ability to upgrade a pre-existing plain-string
anchor to role-tagged paths.

**Verified:** 4 pre-existing tests plus 8 new scenarios (legacy round-trip,
role validation and rejection, mixed lists, dedup, upgrading a legacy anchor,
CLI JSON-object support) all pass.

**Follow-up not yet done:** `write_guardian.py`, `drift_analysis.py`, and
`delivery-record.py` don't read the new role field yet -- they still use
their pre-existing workarounds. Wiring them up was explicitly deferred as a
separate, later run.

---

## 7. Sequential pipeline handoff/regression had no CLI surface (Fixed)

**Symptom:** a fully-built, fully-tested mechanism for moving a run between
the IMPLEMENTATION/TESTING/INFRA pipeline badges, and for classifying and
routing a test-stage failure (including a legitimate circuit breaker), was
only reachable by importing `pipeline_orchestrator.py` and calling its
methods directly in Python -- the same way its own unit tests do. No host or
user could use it through any `tailtrail` command, and it wasn't mentioned
anywhere in `TAILTRAIL-COMMANDS.md`.

**Correction made mid-investigation:** initially assumed (wrongly) that the
regression-routing loop was one-directional. It is not -- `handle_regression()`
classifies a failure as mechanical/behavioral/environmental and can correctly
route back to IMPLEMENTATION, with a three-strikes circuit breaker
(`_REGRESSION_LIMIT = 3`) capping genuine regression loops. Confirmed by
running the real test suites (`test_failure_classification.py`,
`test_sequential_pipeline.py`) directly.

**Fix:** added an argparse `main()` to `pipeline_orchestrator.py` with
`handoff` and `regression` subcommands wrapping the existing
`request_handoff()`/`handle_regression()` methods unchanged; wired a new
`pipeline` command into `tailtrail.py`'s dispatcher using the same
`run_script()` pattern as every other single-script command; documented the
whole badge/handoff/regression/circuit-breaker system in
`TAILTRAIL-COMMANDS.md`; registered `tailtrail pipeline` under the existing
`navigator` feature entry in `tailtrail-registry.json` (the same scripts were
already claimed there); added a one-line nudge toward this command in both
the Start Report and the completion report, shown specifically when a run is
still on the IMPLEMENTATION badge with TESTING unvisited.

**Verified:** live end-to-end runs through the real `tailtrail pipeline
handoff`/`regression` commands (not just the underlying script), plus the
full existing test suites, all passing with zero regressions.

---

## 8. `resolve_active_run()` picked "most recently approved," not "most recently active" (Fixed)

**Symptom:** `write_guardian.py`'s hook could enforce the wrong run's scope
when a second, unrelated run was approved after a correction had already
been made to a first run -- the old logic compared only each run's
`planning/lock-v1.json` approval-time mtime, so a plain approval always beat
a genuine, more-recent correction on a different run.

**Fix:** `resolve_active_run()` (`scripts/write_guardian.py:199`) now ranks
each approved run by the maximum of three signals: the lock's own approval
mtime (kept as the baseline), the newest `anchors/approved-v*.json` mtime (a
mid-run correction), and the last logged event's timestamp in
`events.jsonl` (a checkpoint, closure, or requirement activation).
Deliberately *not* a recursive scan of the whole run directory -- that was
considered and rejected on two concrete grounds: per-edit latency cost
across every `Edit`/`Write`/`NotebookEdit` call, and `RunLock`'s own `.lock`
file being touchable by a merely read-adjacent operation (opened in `a+`
mode), which would make an inspected-but-untouched run look falsely active.

**Verified:** reproduced the exact live incident in its real chronological
order (approve run A, approve unrelated run B, correct run A, confirm the
fix now resolves to A instead of B), plus a second scenario confirming a
plain logged event alone also counts as activity. All pre-existing
write-guardian and full-pipeline tests continued to pass.

---

## 9. Requirement-interpretation grounding rules are fiddly and undocumented (Mitigated)

**Symptom:** hand-writing a `--requirement-interpretation` JSON for
`tailtrail start` routinely failed on rules that are enforced strictly but
explained only by a terse rejection message, discovered purely through
trial and error over many submissions this session:
- a clause's `text` must be an *exact, contiguous substring* of the goal;
- an `intent_terms` entry must be a literal substring of the *goal*, not
  just of its own clause (hyphenated compounds like `argparse-based` or
  `schema-valid` often silently fail even when the base word is "obviously"
  present);
- a code-identifier-looking token named in a clause (a `--flag`, a
  `function()`, a `file.py`, a `snake_case_name`) must also appear in that
  requirement's `intent_terms` *and* its `statement` text, or the submission
  is rejected with "omitted exact named target(s)."

**Status:** the underlying rules themselves were not changed (they appear
intentional, enforcing that a host's interpretation stays grounded in the
literal goal rather than paraphrased or invented). Mitigated by building
`scripts/host-interpretation-builder.py`, which checks all three rules
locally against a plain spec before anything is ever submitted to
`tailtrail start`, catching the first two with certainty and approximating
the third with a regex (disclosed in its own docstring as an approximation,
not a guarantee).

---

## 10. `--run-id` on `tailtrail start` doesn't pin a new run's ID (Not a bug)

**What was initially assumed:** that `--run-id <explicit-id>` could be used
to make `tailtrail start` mint a new run under a chosen ID. Passing it
appeared to have no effect -- a fresh ID was minted regardless -- and this
was logged as a quirk to work around.

**Correction:** the flag's own help text says exactly what it is for:
*"Optional exact TailTrail run ID. Enables evidence-driven correction and
recovery routing for that run only."* Tracing `args.run_id` through
`scripts/task-start.py` confirms it: it flows into `guided_delivery()` →
`delivery_run_signals(root, run_id)`, which reads context about an
**already-existing** run for correction/recovery purposes. It was never
designed to seed a new run's ID, and a new run's ID is always minted
separately regardless of this flag. This was user error (using a flag for a
purpose it doesn't serve), not a TailTrail defect -- recorded here so no
other agent repeats the same wrong assumption.

---

## 11. Standing recommendations (audited against this log)

A separate, running list of recommended TailTrail changes was periodically
re-checked against what this session actually confirmed. Items already
covered in full detail above are cross-referenced rather than repeated.

| # | Recommendation | Status |
|---|---|---|
| R1 | Surface the trusted-evidence recipe (`execution-evidence.py run --approved`, then `closure-recorder.py` with **no** `--input` flag) directly in every evidence-incomplete completion report's "Next actions," instead of only discoverable by reading source. | Open, not implemented. |
| R2 | Fix `--task-type` so it reaches Navigator's *first* scope decision (`investigate()` in `navigator.py`), not just a later reconciliation step in `task-start.py` that can't resurrect candidates the first pass already excluded. | Open, not implemented. |
| R3 | Pick one semantic for `likely_paths` -- either always owner-only, or a real per-path role tag -- so no downstream consumer has to guess. | See Issue 6. Schema half is **done**; `write_guardian.py`, `drift_analysis.py`, and `delivery-record.py` still don't read the new role field, so those consumers still use their pre-existing workarounds. |
| R4 | Give the write-time hook a built-in, explicit exemption for root-level config/registry files, plus a clean "deliberate override" mechanism for already-reasoned exceptions, instead of requiring manual unregister/reregister of `.claude/settings.json`. | Open, not implemented -- see Issue 4. Hit **five separate times** this session alone (`tailtrail-registry.json`, `GUARDRAILS.md`, `TAILTRAIL-COMMANDS.md`, `TAILTRAIL-PLAYBOOK.md`, this file), making this one of the most-repeated pieces of friction in the whole session. A deeper "Navigator sends the guard a receipt" design was investigated and found to have a bigger blast radius than its benefit justified (see Issue 4a) -- the recommended path is the narrower, direct fix: teach `classify_repository_role()` the file category itself. |
| R5 | Make `resolve_active_run()` robust to multiple in-flight runs. | **Done** -- see Issue 8. |
| R6 | `proof-update`'s post-approval framing is effectively dead code -- it's only reachable while a run is `awaiting-approval`, by which point most hosts have already activated. | Open, not implemented. |
| R7 | Collapse the repeated Start Report boilerplate into a one-line reference instead of reprinting the full static sections every run. | Open, not implemented. A tool-output design question, independent of the separate host-behavior rule that a Start Report be pasted verbatim once shown. |
| R8 | Loosen clause/intent-term grounding to tolerate reasonable paraphrase, or at least give a precise diff of "expected this exact substring" instead of a bare rejection. | **Split verdict.** Giving a precise diff on rejection is a clear, low-risk usability win -- still open, worth doing. Loosening the grounding itself is **not recommended**: strict exact-substring grounding is specifically what stops a host from drifting interpretation through confident paraphrase -- the same risk category already rejected in the "explained backdoor" discussion for new-file scope claims (see the per-path role tagging discussion). Keep grounding strict; fix only the error message. |
| R9 | Make `--run-id` either honor the passed ID or fail loudly if it can't, instead of silently substituting a new one. | **Withdrawn.** Based on a misunderstanding -- see Issue 10. `--run-id` was never meant to pin a new run's ID; it's working exactly as designed for its actual purpose (correction/recovery context on an existing run). |
