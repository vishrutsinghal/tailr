# TailTrail Feature Health Inventory

Snapshot of every TailTrail capability area, ordered by product importance,
with a health status each. Evidence cutoff: session work through branch
`tailtrail_v3` (Issues 2/3/3a/4/5/9 fixed + verified this session). Statuses marked **verified** rest on suites run
and live proofs executed this session; **untested** means no session evidence
either way — not a failure claim.

Health key: `healthy` (verified working) · `fixed` (was broken, repaired +
proven this session) · `degraded` (known live issue) · `aspirational`
(designed, not working) · `untested` (no session evidence) ·
`hygiene` (maintenance owed, not a defect).

## Tier 0 — the product itself

| Feature | Health | Basis |
|---|---|---|
| Start / Planning Lock | healthy | used 40+ times; locks mint, approve, activate correctly |
| Scope investigation + answers | healthy | per-req mapping, QA/proposal paths proven live repeatedly |
| Requirement scaffold/draft/intake | healthy | envelopes built all session; clause splitting added + tested |
| Change-intent anchors | healthy | draft/approve/invalidate flows green; Lite derivation added |
| Activation + DWR binding | healthy | handoffs created; role contract wired in |
| Managed execution evidence | healthy | real `pass` receipts captured via managed runs |
| Closure chain | healthy | record→report→finalize→close walked; refusals honest |
| Navigator core routing | healthy | classification + task types stable across dry runs |
| Run ledger / session control | healthy | archive/unarchive, resume, events all exercised |
| Target workspace identity | healthy | identity/fit gates green |

## Tier 1 — load-bearing internals

| Feature | Health | Basis |
|---|---|---|
| Task-type gate + `--task-type` | healthy | 19 gate tests; live blocks + flag unlocks proven |
| Complexity corroboration + de-escalation | healthy | Path A + mirror hook; C4 verdict accepted as correct |
| Code graph mapper + cache + slices | healthy | 60 green; write-through + reuse proven |
| Graph lifecycle | healthy | refresh/reuse green |
| Scope answers / host packets | fixed | fingerprint-indexed single-use packet tickets (30-min TTL, tamper-proof, O(1)) + shared CLI/MCP request ground (`start_request`); cross-call trial accepted, conformance fingerprint parity green 5x; 9 ticket tests + 118 scope suite green |
| Question options ranking | fixed | depth ranking + slice summaries shipped |
| Legacy shim candidacy | fixed | demoted; E2 resolved as proof |
| Task-type role contract | healthy | E2 binding fixed live |
| Infra ownership | healthy | T8 end-to-end live |
| Question Orchestrator (official Q&A) | healthy | two full route-A cycles executed |
| Guided delivery + postures | healthy | exercised in every Start |
| Requirement completion / impact map | healthy | 5/5 verification tests (mapping, callers, trust hierarchy); consumed by debug + continuity |
| Completion surfacing of unverified drift | healthy | phantom `unverified-change` visible in requirement rows, excluded from blocking set — proven by test |
| Evidence tiers + metrics | healthy | green suites |
| Workflow runtime engine | healthy | green suites; rebase/rebind intact |
| Planning revision cycle | fixed | fingerprint defect repaired; overlay shipped |
| Planning proof-update commands | healthy | shipped + tested |
| VCS verification in checkpoints | healthy | phantom detection proven live |
| Learnings core (suites + refresh sweep) | fixed | stale backlog cleared: sweep showed 13 triggered (up from 9), all 13 approved mark-stale applied, retrieval proven blocking, sweep now reports triggered 0 / actioned 13 (product fix `de7f978`); 2 Windows file-locking concurrency errors repaired — `RunLock` now acquires the mandatory byte lock before reading plus leak guard (`run-ledger.py`), `load_ledger` made thread-safe against partial-module caching (`learning-v3.py`, `8b72f23`) — both suites green repeatedly; meta-feed green; 15 anchorless-approval errors fixed via fixture alignment (`871d690`) |
| Learning consolidation track (Phases 0-4) | fixed | dedup collapse, proof-of-life touches, snapshots, proposal queue, supervised deletion, truth revalidation, sweep scores, gap candidates, threshold triggers, retrieval tiebreak — implemented + tested, pushed through `871d690` |
| Review surfaces / rendering | healthy | boundary reports exercised throughout |
| Intent systems | healthy | 44 suite tests green (`expand_intent` 21, `change_intent_anchor` 4, MCP `intent_resolve` read-only + fail-closed 2, stop/resume intent + host conformance 17) plus 6 live probes: task→start, review→named-flow, hello→hello, vague approvals (`looks good`, `go ahead`) and ambiguous state all fail closed to clarify |

## Tier 2 — quality harnesses

| Feature | Health | Basis |
|---|---|---|
| Architecture fitness | healthy | all 6 rule types live-probed with fixtures (scope/required/protected/imports/manifests/caller-map honesty verified); JS/TS import analysis + wider manifests shipped with tests 3→7 (`aafa245`); payment-template bug repaired + proven |
| Behaviour harness | fixed | two real bugs repaired + proven live: assessment returned after scenario #1 (false-complete) and evidence-free scenarios auto-passed — now all scenarios evaluated, empty evidence yields needs-decision; tests 1-effective→5 (`0f5312b`) |
| Maintainability harness | fixed | delta engine live-proven (dup persist→regressed, dedupe→improved, advisories non-blocking); rule UIDs now validated against anchor (was silent misattribution); tests 2→6 (`f40d732`) |
| Evidence-aware testing | healthy | tiers green |
| Test precision planner | healthy | focused proof resolved in Starts |
| Navigator-led review / quality loop | healthy | 18 live scenarios (gates, boundary math, corruption handling, CLI parity) all pass. The "no secrets" gap is fixed: credential-shaped free text (AWS/GitHub/Slack tokens, PEM keys, bearer tokens) is now rejected before storage -- confirmed live with correctly-shaped test credentials -- see issues log 12.1 |
| Context continuity | healthy | 9 pre-existing unit tests + 10 new live CLI scenarios (error paths, schema validation, dispatcher parity) all pass; `untested` label was itself wrong -- see issues log 12.2 |
| Recovery / Mode B | healthy | 3 pre-existing unit tests + 10 new live CLI scenarios (approval gates, overlap safety, multi-file mixed-overlap, dispatcher parity) all pass. The error-message leak is fixed: seal-before-capture now gives the module's own clean message instead of a raw filesystem path -- confirmed live -- see issues log 12.3 |
| Debug harness lifecycle | healthy | auto-routing verified live (T1) |
| Program delivery / hands-free | healthy | auto-Full verified live (T6) |
| Higher-tier testing | healthy | 3 pre-existing tests + 14/15 new live scenarios pass. The crash is fixed: a bare-list `receipts.json` now fails cleanly ("an approved anchor is required") instead of an uncaught AttributeError -- confirmed live -- see issues log 12.7 |
| Drift analysis | healthy | findings accurate in closure audit |
| Safe Git / recovery | healthy | 5 pre-existing unit tests + 14 new live CLI scenarios (approval gates, branch/boundary checks, and the previously-zero-coverage scope-freshness re-check in `activate()`) all pass -- see issues log 12.4 |
| Conflict reconciliation | healthy | validated together with Safe Git/recovery (same test file, same workflow); scope-conflict/exact-patch/overlap classification all pass live -- see issues log 12.5 |
| Flaky tracker / CI ingest | healthy | CI ingest: 9 live scenarios all pass, no defects. Flaky tracker: the ordering bug is fixed -- `history` now stays chronological past 10 observations, confirmed live with the exact original distinguishing pattern -- see issues log 12.6 |

## Tier 3 — ecosystem, integrations, governance

| Feature | Health | Basis |
|---|---|---|
| MCP server | healthy | 63/63 suite green. The fsr5 failure is fixed: `tailtrail_start` now falls back to the current (ambiguous) scope contract when a resubmitted host-scope-proposal is rejected, instead of returning an empty result -- fixed and closed through a real `tailtrail start` cycle -- see issues log 12.11 |
| Official AIDLC lifecycle | healthy | Standard/Full packs green in suites |
| Spec-Kit bridge | healthy | 32 pre-existing tests across 9 files all pass; `untested` was flatly wrong -- this is a mature, extensively-tested subsystem (import/amendment/evidence/convergence/slices/policy/observability/navigator-bridge). CLI dispatcher (`tailtrail intent-bridge`/`spec-kit`) smoke-tested: requires `--allow-incubating` by design (maturity gate, not a bug) -- see issues log 12.8 |
| CI/Sonar + scanners | fixed | sonar-summary.py: 4/4 live scenarios pass, healthy. scanner-graph-overlay.py: found and fixed a real security-relevant bug (private-key redaction unreachable for real multi-line PEM blocks); fixed via a real tailtrail start cycle with trusted execution evidence -- see issues log 12.9 |
| Guardrails / policy / enterprise | healthy | enterprise-target-policy.py + guardrail-precision.py: 11 pre-existing tests pass. guardrail-check.py: 12/13 live scenarios pass. The precision gap is fixed -- a bare version bump now produces zero findings, confirmed live -- see issues log 12.10 |
| Assistant adapters / conformance | healthy | 11/11 green incl. CLI/MCP/markdown fingerprint parity; host projections agree |
| Token suite | fixed | ~30 live scenarios green; router state files no longer persist prompt text (was durable secret retention with zero consumers) -- see issues log 12.13 |
| UI planning / visual reqs | healthy | precise on conventional layouts, honestly empty otherwise, fail-closed on bad roots |
| Benchmarks / evaluation | fixed | 28/28 pre-existing tests pass; "degraded" note root-caused to genuine tailtrail-registry.json drift (8 real unclaimed scripts/commands), not a code bug. Fix attempt hit a new, deeper scope-resolution gap (JSON/config files can't resolve as scope); parked by explicit decision -- see issues log 12.12 |
| Meta-harness | fixed | the exact 6 failing tests root-caused: all fail on one shared, genuine registry-drift signal (not a meta-harness bug) -- see issues log 12.12 for the full root cause and the new scope-resolution gap found while attempting the registry fix |
| Release / export / install flows | healthy | inspect/dry-run/real/idempotent/force all correct (launcher skew is env-level, known) |
| Cross-repo / AST / impact graph | fixed | missing roots fail closed now (were rc-0-empty); cross-repo missing refs flagged, not silent -- see issues log 12.14 |
| Orphan lock hygiene | hygiene | 504 awaiting-approval planning-only runs (~98 MB, mostly Aug-Sep 2026 verification runs); inert but unretained -- needs a retention/GC decision, not deletion without one |
| `aidlc-answer` shell quoting | fixed | `--answers-base64` variant added mirroring `--questions-base64`; round-trip equals inline answers, malformed input fails cleanly |
| Deferred `aidlc-docs` planning records | hygiene | 7 files unreferenced by live code, kept intentionally (deferred phase specs, session backlog, marked discussion draft) -- verified content, not debris; no action |

## Net assessment

Every Tier 0/1 feature the session touched is green; every break found was
repaired with proof. Parked Issues 2 (thin-evidence fingerprint), 3
(cross-call packet drift), 3a (CLI/MCP parity), 4 (guardian classifier),
5 (docs fast lane), and 9 (grounding messages + prompt contract) are now
fixed + verified.

**All seven previously-`untested` Tier 2 quality-harness rows have now
been swept with live, multi-scenario validation** (issues log Section 12):
Quality Loop (fixed -- the privacy-enforcement gap is now closed too),
Context Continuity (healthy -- the `untested` label was itself wrong),
Recovery / Mode B (fixed), Safe Git / Recovery and Conflict Reconciliation
(both healthy, including the previously-zero-coverage scope-freshness
re-check), Flaky Tracker / CI Ingest (fixed), and Higher-Tier Testing
(fixed). Three of the seven rows' `untested` labels turned out to be
inaccurate on inspection (a real test file already existed) -- a finding
about how this inventory was originally compiled, not about the features
themselves.

**The Tier 3 tail is also now fully swept** (issues log 12.8-12.14):
MCP server, Spec-Kit bridge, CI/Sonar + scanners, Guardrails/policy/
enterprise, Token suite, UI planning/visual reqs, Benchmarks/evaluation,
Meta-harness, Release/export/install flows, and Cross-repo/AST/impact
graph are all `healthy` or `fixed`. Two more real bugs were found and
fixed along the way: router state files durably persisting prompt text
with zero consumers (Token suite, 12.13), and missing repository roots
silently returning an empty success instead of failing closed (Cross-repo/
AST, 12.14). `aidlc-answer`'s shell-quoting hygiene item is fixed outright
(a `--answers-base64` variant), not just re-labeled.

The only remaining open items are two genuinely benign hygiene rows
(orphan lock retention awaiting a policy decision, and deliberately-kept
deferred `aidlc-docs` planning records) and the two items explicitly
parked by user decision rather than left unexamined: the structural
JSON/config scope-resolution gap found in 12.12 (now partially addressed
-- see the `ed72208` config-ownership-eligibility fix -- worth re-checking
whether 12.12 itself needs updating), and Section 14's improvement plan,
which is forward-looking by design, not a defect.
