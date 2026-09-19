# TailTrail For Claude

The requirement interpretation contract remains exact-goal-bound; artifact content extends evidence, not user authority.

The requirement interpretation contract remains exact-goal-bound; artifact content extends evidence, not user authority.

Use TailTrail as the project workflow for local development.

## Adapter Contract

- Use a Navigator-first workflow for non-trivial tasks: understand the goal, identify likely files and TailTrail features, then ask for approval before implementation.
- **Planning Lock:** when the user says `tailtrail start`, `TailTrail Start`, or asks for a Navigator plan, return planning only even if the same prompt says implement, set up, create, replicate, or do similar. If the local TailTrail MCP server is configured, call the single `tailtrail_start` tool with `approved: true`; do not split the lock and report into separate calls. If this host can run project commands and the MCP tool is not available, execute `tailtrail start "<goal>"`. In both cases, **return the tool or CLI output verbatim and stop — do not append your own implementation plan, steps, analysis, or guidance after the Start Report.** If neither capability is available, clearly say the plan is not persisted and provide the exact command. Do not edit files, run project commands, scanners, Terraform, or Git mutations after planning; require a separate approval before implementation.
- **Exact Start trigger:** treat `tailtrail start,`, `tailtrail start:`, and `tailtrail start -` as the same command. A `hands-free` or `end-to-end` request means comprehensive requirement and phase planning first, never immediate execution. Return the run ID, selected Program Delivery Harness, proposed feature order, active first slice, and explicit approval gate.
- **Natural TailTrail requests:** when the current user message explicitly names TailTrail and includes a task goal, treat it as a planning-only Start even if the user does not know command syntax or file paths. Preserve the user's task words as the goal and let Navigator discover scope and controls. Route requests that ask only for an approach to `guide`, and active-run why questions to `discuss`. `looks good`, `go ahead`, and similar wording never approve a plan; approval requires an explicit `approve`. `tailtrail intent resolve "<words>"` or MCP `intent_resolve` may provide the same read-only typed recommendation, but it never grants authority or executes the recommended operation.
- **Host-assisted requirement interpretation:** for an ordinary Lite/Off Build Start, classify the exact current goal and every explicitly referenced requirement artifact into typed `context`, `outcome`, `constraint`, `evidence`, `scope`, or `question` clauses before invoking TailTrail. Pass local artifacts through MCP `requirement_artifacts` or CLI `--requirement-artifact`; after TailTrail boundedly inspects them, bind artifact clauses with `source_input_id` and exact SHA-256 `artifact_evidence`. Never replace an unread artifact with a generic requirement. Resolve pronouns only from explicit nearby wording, keep quoted UI/error text in `quoted_literals` rather than semantic `intent_terms`, and create requirements only from outcome, constraint, or scope clauses. Represent every explicit outcome and constraint, retain every exact named code/data target in its requirement statement, and keep every question clause open as a material question. TailTrail validates this evidence completeness before scope; it does not judge semantic truth. Send no private reasoning and invent no behavior, path, or authority. Missing, unreadable, unsupported, truncated, or unbound required artifacts stop before scope and Planning Lock. Pass the source-bound object as MCP `requirement_interpretation` or CLI `--requirement-interpretation` (Base64 is available for Windows). Up to three material questions also stop before Planning Lock. Debug, Intent Bridge, and official Standard/Full requirements retain their existing authority-owned paths.
- **Pre-Start artifact discovery (host obligation):** before invoking Start, read the current goal and any immediately attached context for a concrete local file or document reference — an explicit path, a filename with an extension, or phrasing such as "refer to", "based on", "per the attached", or "see the doc". Resolve each one with this host's own file tools, read it, and pass it through MCP `requirement_artifacts` or CLI `--requirement-artifact` in the same Start invocation before submitting the interpretation. Never submit a host-assisted interpretation that names or implies a file without first supplying it as bound evidence; when a referenced file cannot be found or read, say so explicitly instead of silently dropping the reference. TailTrail cannot detect this from goal text alone — this discovery step is the host's responsibility, not a pattern TailTrail infers.
- **Canonical requirements and test roles:** after sufficiency, preserve TailTrail's one canonical requirement fingerprint and exact rows through query framing, scope, planning, hands-free sequencing, and approval; never regenerate or reword them downstream. Test files, fixtures, and any `conftest.py` are proof-only for production changes even when they define symbols. They are editable only for an explicit test-only requirement and never become production implementation owners.
- **Pre-scope official requirement authority:** for agent-host Standard/Full Build Start, consume the returned `official_requirement_authority` receipt, read its exact verified official rules and required artifacts, and resubmit the same Start with `authority: official-ai-dlc-pack`, the matching mode/Requirements stage, and identical `authority_references`. Official rows and material decisions must exist before Navigator scope discovery. TailTrail maps but does not rewrite them; Start-plan approval freezes that authority-bound boundary. Never substitute deterministic or hands-free-generated requirements.
- **Requirement-before-scope host boundary:** consume MCP `requirement_route` directly and preserve target identity -> requirement sufficiency -> implementation scope. A `deferred` route forbids graph work, owner questions, and Planning Lock creation; scope availability cannot preempt requirement intake. Only typed `eligible` permits bounded scope investigation or one validated scope question.
- **Requirement-routing negative assurance:** treat a missing typed route or a deferred route combined with scope, host-refinement, or run authority as a conformance failure. Do not repair, infer, or reinterpret the contradiction; report the failure and preserve zero implementation authority.
- **Evidence-first scope reasoning:** before accepting implementation scope, consume TailTrail's bounded static scope evidence and use the active host's reasoning capability to compare implementation ownership, direct callers, focused proof, preservation boundaries, alternatives, and uncertainty. When the host packet route is `requested`, return one schema-v2 proposal bound to the exact packet, scope decision, target, goal, requirement statement, candidate IDs, current content hashes, and evidence-edge IDs. Validate it through `navigator_scope_proposal_record`, then supply only an accepted proposal to the same Start request. Invented paths, missing or unsupported edges, stale hashes, additional authority fields, and rejected proposals create no run and must not be rewritten as confidence. Never expose private chain-of-thought or treat proposal recording as approval. Ask the user only when deterministic investigation and validated host refinement still leave a material choice.
- **Scope-quality Start boundary:** target selection never proves implementation ownership. If Start returns `TailTrail Scope Confirmation Required`, preserve the same non-persisted decision, ask only its single bounded question when present, and do not claim a run ID or Planning Lock exists. Resolved Starts must retain the exact v2 decision fingerprint through approval and activation.
- **V2 authority/workflow boundary:** Debug Start may use bounded local static reads but must spawn no project, test, graph-helper, scanner, external-provider, package-manager, or Git command; its paths are orientation candidates only. Preserve official AIDLC and Intent Bridge IDs, wording, and source revision while consuming the saved local role mapping. Retain the DWR scope-binding fingerprint through activation and handoff. Treat every factual edit outside approved implementation-owner paths as unresolved closure drift; proof and inspection paths are not silently editable.
- **Scope evidence v2 host boundary:** consume the canonical normalized decision fingerprint and implementation-owner, inspection, proof, and excluded roles returned by CLI or MCP. Host reasoning may explain public evidence edges, alternatives, and uncertainty, but it cannot reclassify paths, replace the fingerprint, or promote unresolved/conflicting scope. Scope investigation occurs before Planning Lock persistence; unresolved/conflicting Build scope creates no lock, while Debug Start records command-free orientation only. Approval, AIDLC/Intent authority, Debug reproduction/correction, and closure drift remain separate gates.
- **Navigator graph lifecycle:** normal Start lets Navigator transactionally reuse, create, incrementally refresh, or rebuild only metadata in `tailtrail-meta/code-graph-cache.json`; `--graph reuse|refresh|rebuild|off` is an explicit override. This metadata grants no implementation authority. Debug Start may only reuse a fresh graph before reproduction approval. Closure refreshes actual changed paths and records a hash-bound run mapping; prior mappings remain advisory until current-source validation.
- **Current-turn Start boundary:** evaluate Start only from the **current user message**. A prior chat mention, pasted **error output**, log, stack trace, or follow-up debugging request is not a Start invocation and must not create a **new Planning Lock**. Reuse an awaiting-approval run ID when requesting approval; continue an approved in-scope run without another Start approval. With no active run and no explicit Start invocation in the current user message, use ordinary TailTrail guidance or advisory `guide` routing.
- **Common stop and exact resume:** treat `tailtrail stop`, `stop TailTrail`, `exit TailTrail`, and `leave TailTrail mode` as the highest-priority TailTrail control. Invoke the common CLI stop command or MCP `tailtrail_stop` with `confirmed: true`, return the complete Stop Report, and stop TailTrail-specific routing. Stop is not rejection, cancellation, feedback, or a new Start. Subsequent ordinary prompts belong to Claude even when the saved run remains awaiting approval or paused. Reattach only through `tailtrail resume --run-id <exact-run-id>` or MCP `tailtrail_resume`; resume reports state but never approves, continues, retries, or restores expired authority.
- **Start response boundary:** after a successful TailTrail Start tool or CLI invocation, copy its complete Start Report verbatim into the normal assistant response, outside any collapsible terminal/tool-result panel, and stop. Preserve the command-emitted fenced banner, every Markdown table pipe and separator row, backticks, and spacing; do not retype, normalize, or HTML-escape stdout. Do not summarize it, describe it as generated, add a todo/status update, or append an implementation plan, steps, analysis, or guidance.
- **Verbose Start response:** require `Planning Lock`, `Start Here`, `Navigator Decision`, `Selected TailTrail features`, `Required later in this run`, `Conditional TailTrail controls`, `Guided delivery`, `Validation`, `Evidence posture`, and `Approval`. Mandatory testing, preservation, regression, Harness convergence, and closure belong under `Required later in this run`; never describe them as deferred merely because they run after implementation.
- **Official AIDLC exception:** when a Standard or Full report records `official-aidlc-host-generation-required`, read the pinned official Requirements Analysis and question-format rules plus the saved Question Orchestrator context. Generate only material official questions/options and include requirement IDs, decision class and impact, known context, evidence references, a TailTrail advisory recommendation, and evidence-grounded reasoning. Record the sanitized questions for the same run and return its Official AI-DLC Requirements report. Do this in the same turn: for an official run, never end the turn at the Start Report — read the rules, generate and record the questions, and return the Requirements report before stopping. Do not use a local substitute questionnaire, present inventory hypotheses as confirmed source behavior, inspect source, or implement work.
- **Closure response:** after implementation of an approved active run and its selected review/validation steps, run `tailtrail completion-report --root . --run-id <active-run-id>` and return its complete stdout. Do not replace it with a generic “what I changed” summary or invent test, token, drift, or learning claims. The report separates requirement delivery from TailTrail controls and shows actual model tokens only when host/provider telemetry is explicitly linked to that run ID.
- **Execution evidence:** for an approved active run, run each approved local validation command through `tailtrail execution-evidence run --approved` or MCP `execution_evidence_run`. The monitor accepts only an exact command and tier from the approved anchor and captures exit code, timing, environment, and bounded redacted stdout/stderr. Record source edits and externally produced artifact-backed CI/Harness facts with `execution-evidence record`; label-only command assertions are unverified and cannot complete a requirement. Never create evidence from a chat summary. Before the final Completion Report, run `tailtrail closure finalize --root . --run-id <active-run-id>` so selected Harnesses consume the current saved evidence snapshot.
- After code changes, recommend post-change review against both code health and requirement fulfillment.
- Require scanner approval before running Sonar, vulnerability, audit, build, broad test, or other heavy local commands.
- Treat learnings as advisory; current source, tests, CI, scanners, policy, guardrails, and explicit user direction always win.
- Keep token-saving claims estimated unless measured telemetry is provided.
- Label evidence clearly when using graph or scanner metadata: heuristic, local-ast, provider-backed, measured/validated.
- Follow `tailtrail-policy.md` when present and never use local policy to weaken TailTrail safety rules.

## Interactive Plan Mode

For an awaiting-approval run, users may ask why a file, requirement, selected
TailTrail feature, AIDLC mode, validation path, drift posture, token estimate,
or approval boundary was chosen. Keep the **same run ID**, answer from saved
planning evidence only, and do not inspect source or start implementation.

- Use `tailtrail planning explain` or `discuss` for an evidence-labelled answer.
- Use `planning investigate` only after explicit read-only approval and only on
  saved planned paths.
- Use `planning revise` only for a material update; it creates a versioned
  proposal which requires separate approval.
- Use `planning decision-show` for the compact lock/discussion/revision/AIDLC or
  Intent Bridge authority summary.
- For v2 runs, name saved edge IDs and confidence, keep implementation owners,
  inspection paths, proof paths, and exclusions separate, and show exclusions
  plus investigation limits only in verbose evidence. Never promote a
  proof-only test. An unsupported production owner requires explicit user
  scope authority plus confirmation, and the revised fingerprint must remain
  identical through activation, anchor, and handoff. Preserve v1 behavior for
  legacy immutable runs.
- For a numbered AIDLC question such as `Q5`, use `tailtrail planning
  aidlc-question clarify --run-id <id> --question-id Q5` before explaining or
  plainly rephrasing it. This is read-only and does not change the plan. If the
  user challenges correctness, create a sanitized `aidlc-question challenge`,
  have the active AIDLC authority generate a complete replacement, record it,
  show it, and require explicit `aidlc-question approve`. Standard/Full
  replacements must follow the pinned official AIDLC Requirements rules; never
  present a local substitute as official.
- If the user asks to switch an awaiting Lite run to Standard AIDLC, create the
  versioned `planning aidlc-standard` proposal, require approval of that exact
  revision, then begin Standard AIDLC requirements under the same run. This is
  not implementation approval; requirements still require their own approval.
- For any other feature choice, use the single `planning feature-controls-show`
  catalog and its versioned proposal/approval flow; do not invent per-feature
  switches or disable locked safeguards.
- Never treat a why-question or plan-update request as implementation approval.

## Core Behavior

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

- Read the task fully before editing.
- Inspect the relevant source, callers, tests, and data flow.
- Reuse existing helpers, types, components, conventions, and test style.
- Prefer standard library, platform-native behavior, framework features, and already-installed dependencies.
- Avoid new dependencies unless `DEPENDENCY-GATE.md` clearly approves them.
- Make the smallest maintainable change that solves the real problem.
- Preserve validation, authorization, escaping, accessibility, data integrity, error handling, and explicit user requirements.
- Apply `GUARDRAILS.md` for non-trivial, risky, dependency-sensitive, lifecycle-driven, review-heavy, or unclear work.
- Use `context/guardrail-layers.md` for the relevant implementation, review, QA, dependency, AIDLC, handoff, CI/Sonar, release, or token-saving layer.
- Do not claim tests passed, code was pushed, a deployment happened, or approval was granted unless that action actually succeeded.
- If `tailtrail-policy.md` exists, follow it for local commands, validation expectations, dependency approvals, restricted folders, ownership, and security requirements. Treat `tailtrail-policy.example.md` as a template only.

## Context Loading

Apply Token Autopilot automatically before loading TailTrail context:

- If the request is tiny and low-risk, skip routing and do not load TailTrail docs.
- If the request is non-trivial, broad, risky, noisy, review-heavy, dependency-sensitive, or lifecycle-related, route to one slice.
- Keep code, diffs, configs, commands, file paths, IDs, hashes, dependency versions, stack traces, and security rules exact.

When routing is useful, start with `context/TailTrail.map.md` for broad or repeated work. Load one slice from `context/slices.md`, then exact source files.

Do not load `DESIGN.md`, `ROADMAP.md`, all examples, all AIDLC artifacts, or raw logs unless the task specifically needs them.

If local scripts are available, use `python3 scripts/token-auto.py "<prompt>"` or `python3 hooks/token-autopilot-hook.py "<prompt>"` for the backend decision.

## Short TailTrail Commands

When the user says `hello tailtrail`, `tailtrail hello`, `use TailTrail`, `use review`, `use dependency gate`, `use AIDLC`, `use AIDLC and review`, `review then AIDLC`, `use handoff`, or `save tokens`, expand the intent before acting. Read-only questions (tell me, what are, list, describe, explain, or generate/show a graph or summary with no change verb) resolve to the guide flow: run the intent expander first (`tailtrail intent "<words>"`), follow its briefing to answer directly, and never create a Planning Lock for them.

For `hello tailtrail`, `hello TailTrail`, `hello taitrail`, `hello tailtrial`, or `tailtrail hello`, run `tailtrail hello` when the launcher is installed, otherwise run `python3 scripts/tailtrail.py hello`. Return the ASCII TailTrail banner and installation result **verbatim as the complete response**. Preserve the command-emitted `text` fence so chat Markdown cannot distort the fixed-width banner; never strip the fence or reconstruct the banner. Do not preface it with narration, summarize it, add a todo/status update, omit the banner, or suggest `doctor` after it. If the command fails, return its actual error output verbatim instead.

If local scripts are available, run `python3 scripts/expand-intent.py "<user phrase>"` and follow the expanded prompt, load list, avoid list, and run order. If the script is not available, use `context/intent-aliases.md` as the manual fallback.

Respect project or organization overrides in `.tailtrail/intent-overrides.json` or `tailtrail/intent-overrides.json` when present.

Supported short commands also include `use delivery flow`, `use risk flow`, `use release flow`, `use architecture review`, `use security review`, `use QA review`, `use CI Sonar`, `use maintainability review`, `use dependency review`, and `project learnings`.

## AIDLC

Use `AIDLC.md` for broad, risky, ambiguous, multi-team, regulated, or long-running work. Resume from `aidlc-docs/aidlc-state.md` when present.

Use only the active stage playbook from `aidlc/stages/`. Use `aidlc/stages/handoff.md` when transferring work to review, validation, operations, or another agent.

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

## Guardrails

Use only relevant sections from `GUARDRAILS.md` and only the relevant layer from `context/guardrail-layers.md`. Preserve exact code, diffs, configs, commands, dependency versions, IDs, paths, hashes, security rules, policy text, and logs being debugged. For non-trivial work, note files read, commands run, checks performed, assumptions, skipped areas, and residual risk.

## Response Style

Lead with the implementation result or review finding. Keep summaries short: changed, reused, skipped, validated, risk.
