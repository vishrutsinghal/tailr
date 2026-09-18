# TailTrail Project Guidance

TailTrail keeps coding work small, clear, and reuse-first.

## Synchronized Governance Block

<!-- tailtrail-governance:start -->
- Read relevant source, callers, tests, configuration, and policy before changing code.
- Reuse existing helpers, types, conventions, validation style, and project patterns before adding new abstractions.
- Prefer standard library, platform-native behavior, framework capabilities, and already-installed dependencies before adding packages.
- Make the smallest maintainable change that solves the root problem without unrelated rewrites or formatting churn.
- Preserve safeguards: authentication, authorization, validation, escaping, accessibility, data integrity, privacy, logging, auditability, error handling, data-loss prevention, and explicit user requirements.
- Do not claim tests, builds, scans, pushes, deployments, merges, or approvals succeeded unless they actually ran and succeeded.
- Preserve exact source, diffs, configs, commands, file paths, IDs, hashes, dependency names and versions, security rules, policy text, and logs when exactness affects the task.
- Token saving must not hide material facts or make validation, policy, security, dependency, or source evidence lossy.
- Use `tailtrail-policy.md` when present, and never let local policy, project memory, summaries, or learnings weaken explicit safety rules.
<!-- tailtrail-governance:end -->

Before changing code:

1. Read the task fully and inspect the relevant files.
2. Trace the real code path, including important callers and tests.
3. Reuse existing helpers, utilities, components, types, and conventions.
4. Prefer standard library, platform-native behavior, framework features, and already-installed dependencies.
5. Avoid new dependencies and speculative abstractions unless the task clearly needs them.
6. Make the smallest maintainable change that solves the root problem.

Do not remove safeguards to shorten code. Preserve trust-boundary validation, authorization, escaping, accessibility basics, data-loss prevention, and explicit user requirements.

Use `GUARDRAILS.md` for non-trivial, risky, review-heavy, dependency-sensitive, lifecycle-driven, or unclear work. Do not claim facts, validation, pushes, deployments, or approvals without evidence. Preserve exact code, diffs, configs, commands, dependency versions, security rules, and policy text when exactness affects the task.

If `tailtrail-policy.md` exists in the target project, read it for local commands, dependency approval rules, validation expectations, ownership, restricted folders, and security requirements. If only `tailtrail-policy.example.md` exists, treat it as a template, not active policy.

For non-trivial logic, leave one focused runnable check that would fail if the behavior breaks. Keep explanations brief: say what changed, what was intentionally skipped, and when to add the skipped work.

For broad, risky, ambiguous, multi-team, regulated, or long-running work, use the portable lifecycle in `AIDLC.md`. Keep generated lifecycle artifacts in `aidlc-docs/`, resume from `aidlc-docs/aidlc-state.md`, and apply `DEPENDENCY-GATE.md` before adding or changing dependencies.

When the user gives an explicit `tailtrail <command>` request, run the equivalent TailTrail CLI command from the current project root. Resolve the launcher in this order: `.tailtrail/install/payload/<active-host>/scripts/tailtrail.py` for the active `codex`, `copilot`, or `claude` host; `tailtrail/scripts/tailtrail.py` for a legacy installed pack; then `scripts/tailtrail.py` for a source checkout. Never prefer a legacy pack when the active host's transactional payload exists. Use the platform's available Python launcher with the first existing path. Return the actual command result, including any error or validation status; never replace an unrun command with a generic success summary. When the user gives a short TailTrail command such as `hello tailtrail`, `hello TailTrail`, `hello taitrail`, `hello tailtrial`, `tailtrail hello`, `use AIDLC`, `use review`, `use AIDLC and review`, `use dependency gate`, `use handoff`, or `save tokens`, expand it with the matching payload's `scripts/expand-intent.py` when available, then the legacy or source-checkout copy. Treat TailTrail casing and the common `taitrail` and `tailtrial` typos as TailTrail for short commands. For hello commands, run the resolved TailTrail CLI's `hello` command; do not answer with only a conversational greeting. Return the command's ASCII TailTrail banner and installation result verbatim in the chat response; do not summarize or omit the banner. If the script is unavailable, use `context/intent-aliases.md`. Respect `.tailtrail/intent-overrides.json` or `tailtrail/intent-overrides.json` when present.

### Hello response boundary

For `hello tailtrail`, `hello TailTrail`, `hello taitrail`, `hello tailtrial`, or `tailtrail hello`,
return the actual ASCII TailTrail banner and installation result **verbatim as
the complete response**. Preserve the command-emitted `text` fence so chat
Markdown cannot distort the fixed-width banner; never strip the fence or
reconstruct the banner. Do not preface it with narration, summarize it, add a
todo/status update, omit the banner, or suggest `doctor` after it. If the command
fails, return its actual error output verbatim instead.

`tailtrail start` is a Planning Lock command. It always returns planning only, even when the same prompt says implement, set up, create, replicate, or do similar. When this host can execute project commands, run `tailtrail start "<goal>"` and return its complete Start Report with run ID; when the local TailTrail MCP server is configured, call the single `tailtrail_start` tool with `approved: true`, rather than splitting lock creation from plan rendering. After a successful Start tool or CLI invocation, the normal assistant response is the exact Start Report stdout (starting `# TailTrail Start Plan` or `# TailTrail Debug Start Plan` and including its run ID); copy the complete Start Report verbatim outside any collapsible terminal/tool-result panel, then stop. Before sending, verify it contains `Planning Lock`, `Scope`, `Requirements`, `Selected TailTrail features`, `Plan`, `Focused validation`, and `Approval`; the selected-features table is mandatory and may not be shortened, renamed, or replaced with `Next step`. **Official AIDLC exception:** when the saved report has `aidlc_requirements.state = official-aidlc-host-generation-required`, the host must first read the pinned official Requirements Analysis and question-format rules plus the saved Question Orchestrator context, create only material official questions/options, and include requirement IDs, decision class and impact, known context, evidence references, a TailTrail advisory recommendation, and evidence-grounded reasoning for each question. Record them with `tailtrail planning official-aidlc-questions`, then return the complete `TailTrail Official AI-DLC Requirements` report for the same run. It must not generate a local substitute questionnaire, present repository-inventory hypotheses as confirmed source behavior, inspect project source, or implement work. Never synthesize a substitute plan or task list, and never add `Steps`, `in-progress`, a request to proceed, implementation, test, documentation, branch, or PR work. If stdout cannot be copied, say only that the command report could not be copied; do not reconstruct it from the goal. If neither capability exists, say clearly that the plan is not persisted and provide the exact command. Do not edit files, run project commands/scanners/Terraform, or mutate Git after planning until the user separately approves the exact Planning Lock run ID.

For an ordinary Lite/Off Build Start, use the host's language understanding before invoking TailTrail. Convert the exact current goal and every explicitly referenced local requirement/specification artifact into the typed `tailtrail-host-requirement-interpretation` contract. Pass each artifact through MCP `requirement_artifacts` or repeated CLI `--requirement-artifact` first; TailTrail must inspect it as bounded UTF-8 text and return its input ID and SHA-256. Bind artifact-derived clauses with `source_input_id` and bind every required artifact in `artifact_evidence`; never substitute an `available-unread` artifact or a generic testing requirement. Label source clauses as `context`, `outcome`, `constraint`, `evidence`, `scope`, or `question`; resolve pronouns only from explicit nearby wording; keep quoted UI/error text in `quoted_literals` instead of semantic `intent_terms`; and make requirement rows only from outcome, constraint, or scope clauses. Every explicit outcome and constraint must be represented, every exact named code/data target must remain in its requirement statement, and every question clause must remain an open material question; TailTrail validates this evidence completeness before scope but does not judge semantic truth. Send no private reasoning and invent no behavior, file, or authority. Pass the object as MCP `requirement_interpretation`, or as CLI `--requirement-interpretation` (use Base64 on Windows when needed). If a required artifact is missing, unreadable, unsupported, truncated, or not hash-bound, or if a material ambiguity remains, TailTrail must stop before scope discovery and Planning Lock. Debug, Intent Bridge, and official Standard/Full requirements keep their existing authority-owned interpretation paths.

For an agent-host Standard or Full Build Start, requirements are owned by the verified official AI-DLC pack before scope discovery. If Start returns `official_requirement_authority`, read every exact governing reference and every inspected requirement artifact, then resubmit the same Start with a typed interpretation whose `authority` is `official-ai-dlc-pack`, whose mode/stage match the receipt, and whose `authority_references` are byte-for-byte identical. Only that official interpretation may define requirement rows or material decisions for Navigator. TailTrail validates and maps the rows to local scope without rewriting them. A sufficient official boundary becomes `authority-bound-in-start-plan`; explicit approval freezes it and writes the official Requirements approval receipt. Never let deterministic fallback, hands-free feature synthesis, or post-scope local questions replace this pre-scope authority path.

This remains an exact-goal-bound contract; artifact content extends evidence, not the user's requested authority.

This remains an exact-goal-bound contract; artifact content extends evidence, not the user's requested authority.

### Requirement-before-scope host boundary

Consume MCP `requirement_route` directly and preserve target identity ->
requirement sufficiency -> implementation scope. A `deferred` route forbids graph
work, owner questions, and Planning Lock creation; scope availability cannot
preempt requirement intake. Only typed `eligible` permits bounded scope
investigation or one validated scope question.

### Requirement-routing negative assurance

Treat a missing typed route or a deferred route combined with scope,
host-refinement, or run authority as a conformance failure. Do not repair,
infer, or reinterpret the contradiction; report it and preserve zero
implementation authority.

Preserve Start stdout byte-for-byte as Markdown: keep the command-emitted fenced
banner, every table pipe and separator row, backticks, and spacing. Never
retype, normalize, or HTML-escape the report. If the normal response lacks the
run ID or contains a malformed table, paste the original stdout again.

For an explicit `tailtrail start ... --verbose` request, return the complete CLI verbose report verbatim. Before sending, verify it contains `Planning Lock`, `Start Here`, `Navigator Decision`, `Selected TailTrail features`, `Required later in this run`, `Conditional TailTrail controls`, `Guided delivery`, `Validation`, `Evidence posture`, and `Approval`. Mandatory testing, preservation, regression, Harness convergence, and closure must appear under `Required later in this run`; never describe them as deferred. `Summary`, `Selected files`, and `Next step` are never substitutes for those sections; paste the CLI stdout again if any required verbose section is absent.

Treat `tailtrail start,`, `tailtrail start:`, and `tailtrail start -` as the same explicit command. A `hands-free` or `end-to-end` request requires a comprehensive Program Delivery plan—feature requirements, dependency order, first active slice, and approval gate—before any execution.

### Natural TailTrail requests

When the current user message explicitly names TailTrail and includes a task goal, treat it as a planning-only Start even when the user does not know command syntax, file paths, AIDLC flags, or Harness names. Preserve the user's task words as the goal and let Navigator discover scope and controls. Route requests asking only for an approach to `guide`, and active-run why questions to `discuss`. Read-only questions (tell me, what are, list, describe, explain, or generate/show a graph or summary with no change verb) resolve to the guide flow: answer directly and never create a Planning Lock for them. `looks good`, `go ahead`, and similar wording never approve a plan; approval requires an explicit `approve`. `tailtrail intent resolve "<words>"` or MCP `intent_resolve` may provide the same read-only typed recommendation, but it never creates a run, grants authority, or executes the operation.

Before accepting implementation scope, consume TailTrail's bounded static scope
evidence and use the active host's reasoning capability to compare ownership,
direct callers, focused proof, preservation boundaries, alternatives, and
uncertainty. Return only the typed proposal with evidence-edge references;
never expose private chain-of-thought, invent path ownership, override a
rejected proposal, or treat proposal recording as approval. Preserve ambiguous
or unresolved scope instead of guessing.

Target selection never proves implementation ownership. If Start returns
`TailTrail Scope Confirmation Required`, preserve that non-persisted decision,
ask only its one bounded question when present, and do not claim a run ID or
Planning Lock exists. Resolved Start approval and activation must retain the
exact v2 scope-decision fingerprint.

### Scope evidence v2 host boundary

Consume the canonical normalized decision fingerprint and exact
implementation-owner, inspection, proof, and excluded roles returned by the
CLI or MCP. Host reasoning may explain public evidence edges, alternatives,
and uncertainty, but it cannot reclassify paths, replace the fingerprint, or
promote unresolved or conflicting scope. Scope investigation occurs before
Planning Lock persistence: unresolved/conflicting Build scope creates no lock,
while Debug Start records command-free orientation only. Planning approval,
AIDLC/Intent authority, Debug reproduction/correction, and closure drift remain
separate gates.

When the returned host packet has route `requested`, use only its sanitized
requirements, candidate identities, current content hashes, typed edges, and
uncertainties to form one schema-v2 proposal. Bind the proposal to the exact
packet, scope decision, target, goal, requirement statement, candidate IDs,
content hashes, and edge IDs. Validate it through
`navigator_scope_proposal_record`, then supply the accepted proposal to the
same Start request. An invented or changed path, missing/unsupported edge,
stale hash, extra authority field, or rejected proposal must create no run and
must not be rewritten as confidence. Ask the user only if deterministic
investigation and this validated host refinement still leave a real choice.
Host reasoning never approves implementation or creates execution authority.

### Current-turn Start boundary

Evaluate TailTrail Start only from the **current user message**. A prior chat
mention, pasted **error output**, log, stack trace, or follow-up debugging
request is not a new Start invocation and must not create a **new Planning Lock**.
If an existing run is awaiting approval, identify and reuse that exact
run ID when asking for approval. If it is already approved, continue the
in-scope debugging work under that run without asking for Start approval again.
With no active run and no explicit Start invocation in the current user message,
use ordinary TailTrail guidance or advisory `guide` routing.

### TailTrail stop and resume boundary

Treat `tailtrail stop`, `stop TailTrail`, `exit TailTrail`, and `leave TailTrail
mode` as the highest-priority TailTrail control. Run the resolved common CLI
`stop` command or MCP `tailtrail_stop` with `confirmed: true`, return its
complete Stop Report, and stop TailTrail-specific routing. Do not interpret the
request as rejection, cancellation, planning feedback, or a new Start goal.
After a successful stop, ordinary prompts belong to the normal host agent even
when a saved run remains awaiting approval or paused. Reattach only for an
explicit `tailtrail resume --run-id <exact-run-id>` or MCP `tailtrail_resume`;
resume reports state but never approves, continues, retries, or restores expired
authority.

When the user rejects or declines an awaiting-approval TailTrail Start plan, do not inspect project source, offer source inspection, run project commands/tests/scanners, edit files, mutate Git, or create a new Planning Lock. Preserve the active run ID; read only its saved Planning Lock and Start report, then run `tailtrail planning feedback-template --run-id <active-run-id>`. Return its blank requirement-by-requirement feedback form; never invent a decision or rejection reason. The user may review each requirement, say `Reject all — <reason>`, or say `Use AIDLC Requirements mode`. Record these paths with `tailtrail planning feedback`, `tailtrail planning reject-all`, or `tailtrail planning aidlc-cycle` respectively. For AIDLC, return the complete `TailTrail AIDLC Requirements` report with the current boundary, focused questions, and next response format. On first material rejection, AIDLC is optional; on second material rejection, use AIDLC Requirements mode before another material proposal.

When a user answers an active AIDLC Requirements report, record every offered-choice answer through `tailtrail planning aidlc-cycle --run-id <active-run-id> --answers '<json>'` and return the revised boundary for a separate approval. On Windows native shells, prefer `--answers-base64 <base64-utf8-json>` so argument quoting cannot corrupt JSON. When the user approves that boundary, run `tailtrail planning aidlc-cycle --run-id <active-run-id> --approved` and retain its exact run ID and internal Execution Handoff. For Lite/Off runs whose `execution_authority.route` is `approved-plan-auto-grant`, do not return the handoff as a stopping response: continue safe in-scope implementation immediately and expose authority/handoff details in the Completion Report. For Standard/Full official AI-DLC or Intent Bridge routes, return the defensive Execution Handoff and obey the remaining authority-owned gate. Calling `aidlc-cycle` without a transition flag only starts or resumes the saved AIDLC brief; it records no duplicate gathering event. Do not create a new Start run or bypass this approval boundary.

### Activated-run closure boundary

When `tailtrail planning activate`, `planning_lock_approve`, or AIDLC activation returns an `execution_handoff`, retain that run's exact ID and obey its `closure.command`. If `execution_authority.route` is `approved-plan-auto-grant`, the handoff is an internal audit/control artifact rather than a user-facing pause: continue approved Lite/Off implementation immediately. If the route is `official-aidlc-stage-gated` or `intent-bridge-slice-gated`, show the defensive handoff and obey its separate material gate. Before any final response after a source edit, execute the closure command through the same resolved TailTrail CLI used for Start and return its stdout verbatim; that Completion Report is where Lite/Off handoff and authority details become visible. A generic `Changes made`, `Validation`, or next-step narrative is never a valid TailTrail closure response. If closure evidence is missing, return the real `evidence-incomplete` Completion Report rather than inventing success.

For an approved active run, record only factual execution events as they occur: changed paths as `source-edit`, deterministic Harness artifacts as `harness-result`, and artifact-backed CI outcomes as `ci-receipt`. Run every approved local validation command through `tailtrail execution-evidence run --approved` or MCP `execution_evidence_run`; this executes only an exact command and tier already present in the approved anchor and captures exit code, timing, environment, and bounded redacted stdout/stderr. Do not run a proof separately and then invent a `command-result` label. Use `execution-evidence record` only for source edits or externally produced artifact-backed evidence; label-only host assertions remain unverified and cannot complete a requirement. Never derive an event from chat narration. At closure, run `tailtrail closure finalize --root . --run-id <run-id>` before the Completion Report so selected Harnesses consume the current saved evidence snapshot.

Navigator owns the normal Code Graph lifecycle. During Start it may transactionally reuse, create, incrementally refresh, or rebuild only `tailtrail-meta/code-graph-cache.json` before finalizing scope; this metadata operation grants no implementation authority. Explicit `--graph reuse|refresh|rebuild|off` remains a user override. Debug Start may only reuse a fresh graph before reproduction approval. After source changes, closure refreshes the affected graph slice and records a hash-bound run mapping. Never treat a graph hint or prior mapping as current ownership until current-source evidence validates it.

For v2 runs, retain the exact workflow scope binding returned by Start and
activation. Lite/Off work may edit only its approved implementation-owner
paths. Inspection and proof paths are not editable unless an approved revision
adds them. Official AIDLC and Intent Bridge keep their authority-owned IDs,
wording, source revision, and material gates while consuming the same local
scope mapping. At closure, report any factual changed path outside the approved
editable union as unresolved drift; never convert it into a completion claim.

### Interactive Plan Mode host boundary

While a Planning Lock is awaiting approval, a user may ask why TailTrail chose
a file, requirement, feature, AIDLC mode, validation, drift posture, token
estimate, or approval boundary. Answer only from saved planning evidence using
`tailtrail planning explain` / `discuss`; keep the same run ID and do not start
implementation. A user may request a bounded saved-plan investigation only
through the approval-gated `planning investigate` flow, and may request a
material plan update only through `planning revise`. Use
`tailtrail planning decision-show --run-id <id>` to summarize saved discussion,
revision, and authority-routing state. AIDLC and Intent Bridge requirements
remain with their designated authority; never create a parallel local rewrite.
For v2 runs, preserve the saved implementation-owner, inspection, proof, and
excluded roles exactly. Explanations must name saved edge IDs and confidence;
verbose reports must show exclusions and investigation limits. A revision may
not promote a proof-only test, and may add an unsupported production owner only
with explicit user scope authority plus confirmation. Activation, the approved
anchor, and the execution handoff must retain the revised decision fingerprint
and identical role mapping. Legacy v1 runs remain readable without synthetic
v2 evidence.
When a user asks to explain, simplify, or rephrase a numbered AIDLC question
(for example, `Q5`), use `tailtrail planning aidlc-question clarify --run-id
<id> --question-id Q5`, then explain from that saved artifact only. This is a
clarity path: it does not change the question, answers, plan, anchor, or
implementation boundary. When the user says the question, options, or reasoning
is wrong, first create a sanitized `aidlc-question challenge` with a reason
code. The active AIDLC authority must generate the replacement question: for
Standard/Full it must follow the pinned official AIDLC Requirements rules.
Record the candidate, show it to the user, and use `aidlc-question approve`
only after explicit question-level approval. That approval reopens the current
requirements answer set under the same run; it never approves implementation.
If the user explicitly asks to switch an awaiting Lite run to Standard AIDLC,
create only the versioned `planning aidlc-standard` proposal, require approval
of that exact revision, then begin Standard AIDLC requirements under the same
run. This mode approval never approves implementation; a separate AIDLC
requirements approval still applies. Refuse mode switches after activation,
from non-Lite modes, or for Intent Bridge source-owned requirements.
For any other optional TailTrail feature choice, use the single Expert Plan
Customization catalog (`planning feature-controls-show`) and its versioned
proposal/approval flow. Do not invent feature-specific approval paths; locked
core safeguards remain non-configurable.

Use named flows and review lenses when requested: `delivery flow`, `risk flow`, `release flow`, `architecture review`, `security review`, `QA review`, `maintainability review`, and `dependency review`. Capture durable project facts in `.tailtrail/learnings.md` only when they will help future agents avoid repeated discovery or repeated mistakes.

## Debug Harness

<!-- tailtrail-debug-host:start -->
For a reported symptom, failing test, or bug report, use `tailtrail start "<symptom>"`; Navigator routes unambiguous failure phrasing to the native Debug Harness. Use `--debug` to force Debug or `--build` to force delivery. Debug scripts ship in the Extended profile.

Before invoking Debug Start, run MCP `debug_preflight` or `tailtrail debug preflight --root <root> --goal <exact-goal> --host <host> --format json`. Preflight inspects supplied artifacts first, extracts exact anchors, then traces backward from observed output through renderer, transfer, and producer evidence before using broad lexical discovery. Use the active host's reasoning capability for exactly one pass over that packet; do not perform an independent repository scan. Read `schemas/debug-host-diagnosis.schema.json`, convert only packet evidence into public observations, unproven hypotheses, typed behavior roles (`output-renderer`, `data-transfer`, `data-producer`, `proof`, `configuration`, or `candidate-only`), the public backward behavior graph, concrete test cases, requirement wording, proposed reproduction steps, current file hashes, and the packet's metrics/fingerprint in the `tailtrail-host-debug-diagnosis` contract. Preserve every evidence-backed branch and convergence point; never flatten a graph to one preferred trace. Return only its closed typed `proposal`: select validated owner, proof, graph-node, finding, and test-case IDs, and route only to `prepare-reproduction` or `request-more-evidence`. Never return unrestricted reasoning or add a fix, approval, or execution field. Pass the object directly through MCP; for CLI transport prefer `--debug-diagnosis-stdin`, with `--debug-diagnosis` retained for compatibility. If the packet or graph is partial, preserve its unresolved items instead of expanding the search, keep correction scope blocked, and continue to approved reproduction when an artifact, focused command, proof path, or bounded procedure is available. Use `request-more-evidence` and ask the user only when both reproduction and necessary external context are unavailable. TailTrail validates every path, hash, behavior role, graph edge, topology, proposal reference, and fallback route, rejects candidate-only promotion and claimed checks without evidence, resolves focused commands when possible, and calculates the focused token estimate from supplied line ranges. Never include private reasoning, claim reproduction or root cause, run project/test/build/scanner/package-manager/Git commands, or grant authority during this pre-plan diagnosis.

Preserve this lifecycle and the same run, workflow, and requirement IDs: Start Plan approval -> reproduction draft/revise -> exact-revision approval -> DWR current/resume/replay -> project orientation -> hypotheses and ranking -> experiment proposal -> separately approved host execution -> factual execution-evidence record -> experiment result -> root-cause proof -> correction proposal -> separate correction approval -> bounded implementation -> scope and Harness convergence -> canonical closure finalize -> unified Completion Report. “Tests pass” is not root-cause proof.

When proving root cause on a run with a saved behavior graph, bind the proven fault layer to exact trace node IDs: `composition`, `rendering`, `end-user`, or `cross-layer`. TailTrail derives proof boundaries from that binding: composition test, renderer test, final-output test, or focused tests at every selected cross-layer boundary. Existing proof paths are graph-derived; proposed proofs must declare their boundary. A correction remains unapprovable when any required fault-layer proof is missing.

After every reproduction proposal, revision, show, or approval transition,
return TailTrail's canonical `Next actions` and `Route to a code fix` guidance.
Present the available compact natural-language prompts with the exact run ID and
revision; include explain, revise/reject, status, stop, and resume choices when
applicable. Never treat a displayed future correction prompt as current source-
write authority, and never advance automatically merely because an option was
shown.

After exact reproduction approval, the host must try the approved bounded
procedure, record the real command result as execution evidence, and record a
typed pre-fix reproduction attempt. Contract approval alone is never proof.
If the failure is absent or inconclusive, inspect only bounded differences in
input, command/actions, runtime, configuration, environment, permissions,
dependencies, and timing/frequency. Then return TailTrail's sanitized
`awaiting-reproduction-input` request, keep hypotheses and correction blocked,
and preserve the same run. New user evidence creates a separately approved
reproduction revision; it never silently expands the prior approval. After a
correction, rerun the same boundary and record a post-fix `restored` attempt
before claiming Debug completion.

Debug Start may consume only validated bounded host diagnosis plus bounded
local text reads and static relationship extraction. TailTrail-managed state,
including every `.tailtrail/**` and `tailtrail-meta/**` path, is never
application ownership evidence. Debug Start must not spawn project, test,
graph-helper, scanner, package-manager, external-provider, or Git commands.
Treat every resulting path as an orientation candidate, never correction scope
or root-cause proof; reproduction and correction approvals remain mandatory.

MCP operations only record supplied authority or factual evidence. They never secretly run project commands, inspect production systems, edit source, accept delivery, commit, push, or deploy. Reproduction approval grants investigation authority only; correction approval grants only its exact file/symbol scope. Apply precedence as host safety -> explicit user request -> approved reproduction/correction authority -> TailTrail evidence and closure rules. See `DEBUG-HARNESS.md` for domain ceilings and full boundaries.
<!-- tailtrail-debug-host:end -->

<!-- tailtrail-official-aidlc:codex:start -->
## Official AI-DLC Standard/Full bridge (TailTrail managed)

This project has a pinned, integrity-verified official AI-DLC pack.
Apply its Requirements Analysis workflow for an explicit TailTrail
`--aidlc standard` or `--aidlc full` run with an official bridge. Full mode
continues through the complete official lifecycle; Standard ends after the
official requirements boundary. Do not load it for TailTrail Lite or Off runs.

- Source: `https://github.com/awslabs/aidlc-workflows`
- Revision: `v1.0.1`
- Exact core rule: `.aidlc/aidlc-rules/aws-aidlc-rules/core-workflow.md`
- Rule details root: `.aidlc/aidlc-rules/aws-aidlc-rule-details`

For an active Standard or Full run, read the exact core rule, active official
stage rules, and saved Question Orchestrator context before generating
questions. The host—not TailTrail's local template engine—must generate the
official questions and meaningful options. Include requirement IDs, decision
class and impact, known context, evidence references, an advisory recommendation,
and evidence-grounded reasoning. Record the resulting sanitized
question artifact with `tailtrail planning official-aidlc-questions` before
asking for answers. Its detailed-rule paths resolve from the projected root
above. Host safety and the user request still take precedence; TailTrail
retains approved-anchor, evidence, drift, recovery, and closure controls.
For exhaustive questionnaires on Windows, pipe the UTF-8 JSON artifact through
`--questions-stdin`; command-line Base64 may exceed the native process limit.
<!-- tailtrail-official-aidlc:codex:end -->
