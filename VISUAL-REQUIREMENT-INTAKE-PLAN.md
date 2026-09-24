# Visual Requirement Intake: Implementation Design

## Status

Review document only. No source behavior is changed by this file.

## 1. Problem

A Start goal referencing a visual source (mockup, screenshot, photo) flows
to repository scope search with no product understanding: the image is never
bound as evidence, no material decision records its absence, requirements
resolve `sufficient` on text alone, and the user is asked to choose source
files before TailTrail knows what must be built. Verified live against the
codebase: `.png` artifacts are rejected as `unsupported`, an image-
referencing goal yields zero material decisions, and the scope precondition
returns `eligible`.

## 2. Architecture: hosts see, TailTrail enforces

Visual understanding lives entirely with the host agent, which already sees
attached images natively. TailTrail's runtime never parses a pixel. The
division follows the repo's established pattern (debug diagnosis,
requirement interpretation, scope proposals: host judges, TailTrail binds
and gates).

| Host (already capable) | TailTrail (only it can enforce) |
|---|---|
| Sees attached images, extracts visible facts | Detects unbound attachments via transport state (VIS-01 gate) |
| Records uncertainties (what is *not* visible) | SHA-256 of original image bytes; binds observations to hash + input ID |
| Passes a typed observations payload | Enforces byte cap, rejects remote URLs and embedded blobs |
| Answers product questions from context | Converts uncertainties to tracked open questions; gates sufficiency |

No image-parsing dependency is introduced. No PDF renderer. Format checks
do not exist: bytes are hashed, never interpreted.

## 3. Observation contract

One bound artifact carries exactly one observation record:

```json
{
  "artifact_id": "requirement-artifact-2",
  "artifact_sha256": "sha256:9f2c…",
  "summary": "ECG Event Configuration section inside file configuration: Account Name dropdown, '+ Add ECG Consumer' action, and a table. Headers not legible at this resolution.",
  "open_questions": [
    "What are the exact table column headers?",
    "What provides the Account Name dropdown options?"
  ],
  "complete": false
}
```

Field rules:

- `artifact_id` binds to the requirement-artifact input ID. A Start may
  carry a list of these records (multi-screen flows); each is gated
  independently.
- `artifact_sha256` is written by TailTrail after re-hashing the supplied
  path. A host-supplied digest is never trusted. Hash change voids prior
  observations.
- `summary` is host free prose: visible facts only. It must carry the
  boundary note "visible artifact facts only; no inferred hidden product
  behavior" in the stored record.
- `open_questions` is a non-empty string list whenever `complete` is
  false. Every uncertainty the host holds must appear here rather than
  dissolving into confident prose.
- `complete: true` is permitted only with zero open questions. It is an
  explicit, auditable host claim. There is no mechanical check against
  over-claiming; the mitigation is the stored boundary note plus
  Navigator's scope question acting as backstop when scope still
  ambiguates.
- Privacy: any `data:` URI or base64 blob anywhere in the payload is
  rejected at validation. Image bytes travel once (for hashing) and are
  never persisted in state, logs, receipts, or reports.

Trust posture: observations are host-asserted, low-trust input — advisory
like `intent_resolve`, never authority. The check-and-balance is the
question pipeline plus the human's answers, not the model's confidence.

## 4. Attachment awareness (no keyword tables)

The Start path answers one question from transport state, not text
scanning: were files attached to this session, and are they bound?

- MCP: the server observes session attachments; an unbound image attachment
  raises VIS-01.
- CLI: an image path passed via `--visual-artifact` counts as declared;
  a goal mentioning an image with no path supplied is reported unavailable
  before planning continues.
- Skill: the pre-start discovery rule gains one clause — an attached image
  is a concrete reference and must be passed via the visual flags; an image
  the host cannot access is declared unavailable, never silently dropped.

Phantom references (words about an image that exists nowhere, with no
session attachment) are an explicit non-goal: conversational competence
owns that case, same as any vague goal today. This is documented, not
built.

## 5. Bounds

No TailTrail-side size caps. Attachment size is already bounded upstream by
the host platform's own upload limits (tens of megabytes), far below any
dangerous size — a second, smaller cap here would only reject legitimate
input without adding safety. The one robustness rule: hash by streaming
the file in fixed-size chunks, never whole-file reads, so a large
attachment degrades to slow rather than crashing on memory. Question volume
is governed by the existing generic requirement-question flow; format
allow-listing does not exist.

## 6. Sufficiency computation

- Attachment exists in session but unbound → `VIS-01` open → requirements
  not sufficient → scope precondition `deferred` with
  `visual-requirements-must-be-resolved-before-scope-question`. No graph
  work, no scope question, no lock, no authority.
- Bound + observations + `complete: false` with questions → not sufficient
  until each question is answered through the existing requirement
  answer/approve flow (no parallel mechanism is invented).
- Bound + `complete: true` + zero questions → sufficient; scope may
  proceed.
- No attachment anywhere → today's behavior exactly.

## 7. Transports

- MCP: `visual_observations` field on `tailtrail_start` (list of records
  above, minus the hash which TailTrail computes). Single atomic call,
  same discipline as `approved: true`.
- CLI: `tailtrail start "<goal>" --visual-artifact ./mockup.png
  --visual-observations '<json>'`, plus a `--visual-observations-base64`
  twin because Windows quoting mangles inline JSON (mirrors
  `--answers-base64`). `--requirement-artifact` keeps its text-only
  meaning so the two evidence types never mix.
- Skill: pre-start discovery bullet extended for image binding (see §4).

## 8. Reports and validator

- Missing image: `# TailTrail Visual Requirement Required` — planning
  stopped before source discovery, what to attach or describe instead,
  explicit no-search/no-lock statement.
- Ambiguous details: `# TailTrail Requirements Clarification Required` —
  visible facts, questions, no scope selected yet.
- The reply validator gains the new report kinds so compliant replies are
  not flagged; a stopping-early official-style reply scores
  `official-questions-missing`-analogous `visual-questions-missing`.
- Completion reports list bound visual artifact IDs in the evidence
  section so the audit trail survives planning.

## 9. Known limitations (accepted, not built)

- Figma/remote links are rejected (unverifiable bytes). Blessed path:
  host exports PNG and binds locally. Documented, not silently failing.
- `complete: true` over-claims have no mechanical check; mitigation is
  the stored boundary plus scope-question backstop.
- Phantom references rely on host conversational competence (see §4).

## 10. Implementation phases

### Phase 0 — Vocabulary-free plumbing, no behavior change

Transport attachment awareness (attached? bound?), `VISUAL_MAX_BYTES` +
`hash_visual_artifact()`, observation-contract validator, negative
fixtures (unbound blocks nothing yet; phantom blocks nothing — documents
the non-goal). Planning behavior byte-identical. Gate: all asserted
green, zero behavior delta.

### Phase 1 — Detect and defer

VIS-01 decision, deferred precondition + reason code, the two boundary
responses, validator awareness for new report kinds. Gate: the ECG prompt
stops before source discovery; text-only flows byte-identical; fixture
suite covers both responses.

### Phase 2 — Bind and gate

Schema + hash-bind + caps + blob rejection; MCP/CLI/skill transport;
uncertainties-to-questions pipeline on the existing answer/approve flow;
closure traceability. Gate: functional suite (bound artifact → questions
→ answers → sufficiency → scope), safety suite (remote URL, oversize,
blob-in-payload, hash-change invalidation, cross-ID reference), and the
compatibility suite (text-only flows unchanged).

### Phase 3 — Intake merge and closeout

Split requirements from text + bound observations; restamp; registry and
docs updates; full suite green; this file marked as-built.

## 11. Test plan

- Functional: unbound attachment blocks scope; bound + questions blocks
  until answered; bound + complete proceeds; multi-artifact gating is
  per-artifact; hash change voids observations.
- Safety: remote URL rejected; oversize rejected; base64/`data:` URI in
  payload rejected; cross-input-ID reference rejected; raw bytes absent
  from state, logs, receipts, reports.
- Compatibility: text-only artifacts, UI/backend/Debug/Lite/Standard/Full
  flows, and existing scope questions behave exactly as today when no
  visual is involved.
- Validator: golden transcripts for stop-early (violation) and
  requirements-appended (clean) official-style visual replies.

## 12. Acceptance criteria

1. A prompt with an unbound session image cannot reach source scope
   discovery.
2. Requirement questions precede source-file questions, always.
3. Visual facts are hash-bound, bounded, sanitized, and privacy-safe.
4. The runtime never infers hidden interaction behavior from appearance.
5. Scope discovery begins only after visual requirements are sufficient.
6. The ECG request can reach a normal Start Plan with identified page,
   section, controls, table requirements, preservation rules, and proof.
7. Text-only planning behavior is byte-identical.

## 13. Out of scope

- Implementing the ECG UI itself.
- Persisting images in run records.
- Fetching remote-hosted images.
- Pixel-perfect reproduction or design diffing.
- Overriding product-owner decisions with model assumptions.
- PDF-specific handling (hosts read PDFs natively; same contract applies).

## 14. Implementation status

Implemented as built (Phases 0–2; Phase 3 closeout pending full-suite
sign-off):

- `scripts/visual_requirement.py`: attachment states, streaming SHA-256,
  magic-byte media sniffing, observation validation with `data:`-URI ban,
  locator binding, VIS decision helper.
- `scripts/target_workspace.py`: visual dispatch inside
  `inspect_requirement_artifacts` (hash-bound metadata receipts, no
  content); text path byte-identical.
- `scripts/requirement_discovery.py`: `visual_decisions` merge into the
  deterministic sufficiency contract (dedup via existing question matching).
- `scripts/task-start.py`: `--visual-artifact`, `--visual-observations`,
  `--visual-observations-base64`; binding + VIS decisions +
  `visual_requirements` on every report shape including boundary reports.
- `scripts/mcp-server.py`: `visual_artifacts` + `visual_observations`
  schema params forwarded to the CLI flags.
- Host bullet in all six core instruction files: unbound attached images
  are material open questions.
- `tests/test_visual_requirement.py`: contract, gate, binding, and CLI
  end-to-end tests; `tests/test_mcp_server.py`: forwarder test.

Deviations from the draft above, all deliberate: no keyword tables
(transport-declared attachments instead), no size caps (upstream
platforms bound uploads; chunked hashing only), no per-control typing
in the contract (locator + summary + questions + completeness suffice),
PDF needs no code (host-native reading under the same contract).
