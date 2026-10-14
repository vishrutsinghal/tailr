# TailTrail Ground Rules

Where every kind of change gets recorded, and the rules that bind them.
Distilled from live sessions that hit each gap for real -- follow this
instead of rediscovering it.

## 1. The records and what belongs in each

| Change | Record it in | How |
|---|---|---|
| New command (`tailtrail <verb>...`) | `tailtrail-registry.json` (owning feature) + `scripts/tailtrail.py` dispatcher + help text | Add command + script + docs entries; run `tailtrail-registry.py validate` |
| New script | `tailtrail-registry.json` (best-fit feature's `scripts`) | Same validation; unclaimed scripts trip `registry_maturity` drift |
| New docs/prose | Owning feature's `docs` list if product-relevant | Keep the registry truthful, not exhaustive |
| Bug found live | `TAILTRAIL-ISSUES-LOG.md` (new section) | Symptom, root cause with file:line, repro, status; never re-derive twice |
| Host trick learned | `TAILTRAIL-PLAYBOOK.md` (condition → trick) | Verified-live only, with the exact command; theorized entries forbidden |
| Feature health change | `TAILTRIAL-FEATURE-HEALTH.md` | Status + basis (suites run, live proofs); `untested` means no evidence, not failure |
| Behavior contract | Tests, always | Red-to-green proof: fail on old code with the exact symptom, pass on new |

## 2. Binding rules

1. **Approval before implementation.** `tailtrail start` is planning-only.
   Never edit, run scanners, or push without a separate explicit `approve`
   (`looks good` / `go ahead` never approve). Split multi-owner goals into
   single-owner runs instead of fighting ambiguity.
2. **Scope is evidence, not assertion.** Explicit `--changed` naming is
   strong evidence; lexical proximity alone never owns. Config/data files
   resolve as owners only when explicitly named (single-target focus);
   prose files go through the docs-only lane, never the code-graph gate.
3. **Complete host input before persistence.** Before any operation that can
   save scope, a plan, approval, evidence, or closure, provide the exact
   request mode, edit authority, role of every named path, positive and
   negative success criteria, and a project-owned proof path plus runnable
   command; unknowns stay open and block persistence. Never use `--changed`
   for a validation fixture or inspection input because it asserts editable
   implementation scope. A declared/inferred task-type conflict, unresolved
   proof, or implementation step in a read-only/validation-only request blocks
   approval and requires revision or re-routing. Host input completeness is a
   binding responsibility, not something TailTrail may infer.
4. **Write-time enforcement is independent.** Navigator approval and the
   pipeline-badge guard are two systems: a path must be both approved AND
   badge-allowed. Configuration writes additionally require sole-entry
   approved scope (or an explicit mid-run correction).
5. **Anchors are append-only history.** Never edit `approved-vN.json`;
   amend with `correct()` (new version). Never read frozen v1 as current
   truth -- resolve via `latest_approved()`; versions sort numerically.
   New raw `approved-v1.json` reads fail `tests/test_anchor_versioning.py`.
6. **Grounding is exact.** Requirement text, intent terms, and named
   targets must be literal substrings of the goal -- paraphrase is drift.
   Keep the rules strict; fix the error messages, never loosen the check.
7. **No fabricated evidence.** Never invent edge IDs, fingerprints, or
   receipts. A missing evidence link fails closed with its real reason.
8. **Fail closed, loudly.** Unknown scope, missing anchor, malformed input:
   deny with the exact reason and both fingerprints/values, never silent
   fallback or silent guessing. Single-use tickets, 30-minute TTL.
9. **Docs lane limits.** The docs-only fast lane is for trivial prose
   (`.md`/`.rst`/`.txt`/`.adoc`) with no production-signal wording --
   strict all-prose check, one code path anywhere forces the full plan.
   Product-surface files (registry, manifests) go through full Starts.
10. **Verify before claiming.** New tests must fail on old code (stash
   check); pre-existing failures must be proven on the clean tree before
   calling anything a regression; incidental churn (graph cache) gets
   reverted before commit.
11. **Approval is not activation.** An approved plan may still require
   `planning activate --approved` before execution handoff, managed evidence,
   or closure. Do not treat `approved` and `execution-ready` as equivalent.
12. **Plan completeness is a gate.** Do not present a plan as approvable while
   requirements, owners, proof commands, task type, artifact ownership, or
   positive/negative success criteria remain unresolved.
13. **Validate the real call site.** When a finding concerns wiring or a
   projection, a direct helper test is insufficient. Add a regression through
   the public builder or CLI path that actually supplies the production
   arguments.
14. **Push hygiene is explicit.** Before commit or push, inspect `git status`,
   compare the exact intended diff, exclude generated metadata unless it is
   the requested change, report excluded files, and verify the remote branch
   after pushing.
15. **Proposed-new scope is a distinct authority.** A `new:path` answer must
   remain visibly `declared-new` with requirement lineage; it must never be
   discarded and replaced by a nearby inferred owner. Existing-owner evidence
   and post-creation verification are separate checks.
16. **Proof candidates must be executable suites.** A file named like a test is
   not proof until its exact command imports successfully and collects at least
   one test. Helper probes, zero-test paths, and import-failing scripts must be
   rejected or revised before approval.
17. **Classifier keywords require context.** Generic words such as
   `component` or `workflow` must not activate a specialized planning route by
   themselves. Preserve explicit route terms and path signals, and add paired
   positive/negative regressions when changing classifier vocabulary.
18. **Correction runs need a baseline.** Do not start sequential correction
   runs against an uncommitted worktree without an explicit shared baseline.
   Commit the reviewed prior correction, reference the approved prior run, or
   record an anchor correction so legitimate earlier edits are not reported as
   unexplained drift.
19. **Validate the correction premise before persistence.** A corrective Start
   requires current read-only evidence that the reported behavior fails at the
   real public route and that the proposed owner participates in that failure.
   A planning or scope rejection alone is not root-cause evidence.
20. **Do not conflate path-policy layers.** Workspace eligibility, repository
   file-kind, requirement ownership, approved-anchor authority, and write-time
   enforcement are separate decisions. Identify the first failing transition
   before naming an implementation owner.
21. **No cosmetic fixes for no-op plans.** Focused proof must exercise the
   reported symptom and preservation criteria. If approved behavior already
   exists, stop instead of manufacturing a source change; report the run
   incomplete and plan the actual failing layer separately.

## 3. Command wiring checklist

New user-facing command: dispatcher entry + help text in
`scripts/tailtrail.py` (same `run_script()` pattern), MCP schema entry if
host-reachable, registry claim, playbook line, tests. Miss one and the
meta-harness drift check will name it.
