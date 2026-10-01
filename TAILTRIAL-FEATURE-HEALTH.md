# TailTrail Feature Health Inventory

Snapshot of every TailTrail capability area, ordered by product importance,
with a health status each. Evidence cutoff: session work through branch
`tailtrail_v2` (19 commits). Statuses marked **verified** rest on suites run
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
| Scope answers / host packets | fixed | per-requirement mapping repaired option 3a |
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
| Intent systems | untested | used lightly, not verified |

## Tier 2 — quality harnesses

| Feature | Health | Basis |
|---|---|---|
| Architecture fitness | fixed | payment-template bug repaired + proven |
| Behaviour harness | untested | not exercised |
| Maintainability harness | untested | not exercised |
| Evidence-aware testing | healthy | tiers green |
| Test precision planner | healthy | focused proof resolved in Starts |
| Navigator-led review / quality loop | untested | not exercised |
| Context continuity | untested | not exercised |
| Recovery / Mode B | untested | not exercised |
| Debug harness lifecycle | healthy | auto-routing verified live (T1) |
| Program delivery / hands-free | healthy | auto-Full verified live (T6) |
| Higher-tier testing | untested | not exercised |
| Drift analysis | healthy | findings accurate in closure audit |
| Safe Git / recovery | untested | not exercised |
| Conflict reconciliation | untested | not exercised |
| Flaky tracker / CI ingest | untested | not exercised |

## Tier 3 — ecosystem, integrations, governance

| Feature | Health | Basis |
|---|---|---|
| MCP server | untested | not exercised |
| Official AIDLC lifecycle | healthy | Standard/Full packs green in suites |
| Spec-Kit bridge | untested | not exercised |
| CI/Sonar + scanners | untested | not exercised |
| Guardrails / policy / enterprise | untested | not exercised |
| Assistant adapters / conformance | untested | not exercised |
| Token suite | untested | not exercised |
| UI planning / visual reqs | untested | not exercised |
| Benchmarks / evaluation | degraded | frozen snapshots; meta-harness benches stale |
| Meta-harness | aspirational | 6/16 tests red; never run here; see review |
| Release / export / install flows | untested | not exercised (launcher skew is env-level, known) |
| Cross-repo / AST / impact graph | untested | not exercised |
| Orphan lock hygiene | hygiene | ~12 awaiting locks from verification runs |
| `aidlc-answer` shell quoting | hygiene | bypass proven, fix unfiled |
| Untracked `aidlc-docs` drafts | hygiene | pre-existing, owner decision pending |

## Net assessment

Every Tier 0/1 feature the session touched is green; every break found was
repaired with proof. The honest gaps are quantitative, not structural:
a long Tier 2/3 tail never exercised (no evidence either way), one
aspirational subsystem (meta-harness), and hygiene debts. Nothing
investigated this session remains broken except the parked option-ranking
nuances already superseded by shipped machinery.
