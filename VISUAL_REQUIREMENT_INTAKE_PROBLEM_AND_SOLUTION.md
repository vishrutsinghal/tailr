# Visual Requirement Intake: Problem and Proposed Solution

## Purpose

This document records the observed TailTrail planning failure for UI requests that reference an attached image, explains its root cause, and proposes a language- and host-neutral solution. It is a review document only; no source behavior is changed by this file.

## Observed user request

The request was broadly:

```text
Add an “ECG Event Configuration” section inside file configuration.
Add an “Account Name” dropdown.
Add “+ Add ECG Consumer”.
Add a table with columns shown in the attached image.
```

The Start response did not ask for the image or the missing table details. It immediately searched the repository and stopped with a scope question offering three source files:

```text
src/pages/actionExecutionHistory/ActionExecutionHistoryMainContent.tsx
src/pages/addRuleConfiguration/AddRuleConfigurationPage.tsx
src/pages/fileRuleConfiguration/AddFileRuleConfigurationPage.tsx
```

## Why the response is wrong

The request is incomplete before repository scope discovery can safely begin.

The phrase `check the attached image` makes the image part of the requirement source. Without inspecting that image, TailTrail does not know:

- the exact table headers;
- the visual placement and hierarchy of the new section;
- whether the table is editable, removable, sortable, or read-only;
- whether `+ Add ECG Consumer` adds a row, opens a modal, navigates, or invokes a service;
- the option source, default, validation, and required state of `Account Name`.

These are product requirements, not code-scope details. A code-file selection cannot resolve them.

The scope question therefore asks the wrong question at the wrong time. It asks the user to choose a React file before TailTrail knows what UI behavior must be implemented.

## Current flow

```text
User prompt references image
        |
        v
Text requirement normalization accepts prompt as sufficient
        |
        v
Navigator searches repository for related UI files
        |
        v
Several pages match terms such as “configuration” and “add”
        |
        v
TailTrail asks user to choose a source file
```

This makes the user perform internal code ownership selection despite lacking the requirement detail needed to make that decision.

## Root cause

### 1. Requirement artifacts are text-only

`scripts/target_workspace.py` currently prepares requirement artifacts by:

1. checking that the input is a local file;
2. allowing only configured text suffixes;
3. reading bounded UTF-8 content;
4. hashing normalized text; and
5. returning it as a planning input.

An image attachment is not represented as a supported requirement artifact. Even if the conversational host shows an image to the user and assistant, TailTrail's Start input does not receive a hash-bound visual requirement record.

### 2. The prompt’s visual reference is not treated as a material decision

The current requirement route can decide that requirements are `sufficient` when no explicit material decisions have been recorded. The words `attached image`, `screenshot`, `as shown`, and `following columns` do not automatically create an unresolved requirement decision.

As a result, `scope_question_precondition()` receives a sufficient requirement state and authorizes scope work.

### 3. Scope discovery runs before visual specification is known

Once scope work is authorized, Navigator searches for files related to generic UI terms. It can find multiple plausible pages. This is expected repository evidence, but it cannot determine the intended page without first understanding the visual specification.

### 4. The host does not bind conversational images into the Start request

The Start skill and command path need a contract for transferring an attachment from the host into TailTrail. Merely leaving the phrase `check the attached image` in the goal text does not make the image inspectable or auditable by the TailTrail runtime.

## Required behavior

The correct planning sequence is:

```text
User request references a visual artifact
        |
        v
Verify that a bound visual artifact is available
        |
        +-- absent/unreadable --> ask for image or equivalent textual details
        |
        v
Extract only visible UI facts from the artifact
        |
        v
Identify material details not visible in the artifact
        |
        +-- unresolved --> ask product clarification questions
        |
        v
Requirements become sufficient
        |
        v
Discover implementation scope and create a Planning Lock
```

The critical ordering rule is:

> A visual-reference requirement must be resolved before source discovery, scope questions, graph writes, or Planning Lock creation.

## Proposed solution

### A. Introduce a visual requirement artifact type

Add a schema such as:

```text
schemas/tailtrail-visual-requirement-artifact.schema.json
```

The artifact should contain only bounded metadata and sanitized visual observations:

```json
{
  "schema_version": "1",
  "type": "tailtrail-visual-requirement-artifact",
  "input_id": "requirement-artifact-2",
  "media_type": "image/png",
  "sha256": "sha256:<original-byte-digest>",
  "size_bytes": 182304,
  "observations": {
    "section_titles": ["ECG Event Configuration"],
    "controls": [
      {"label": "Account Name", "control_type": "dropdown"},
      {"label": "+ Add ECG Consumer", "control_type": "action"}
    ],
    "table_headers": ["<visible column labels>"],
    "uncertainties": [
      "The Account Name option source is not visible.",
      "Table row edit and deletion behavior is not visible."
    ]
  },
  "boundary": "Visible artifact facts only; no inferred hidden product behavior."
}
```

The host may inspect the image, but must not invent product behavior from visual appearance. Any invisible behavior is recorded as an uncertainty.

### B. Extend bounded artifact preparation

Extend `scripts/target_workspace.py` so `inspect_requirement_artifacts()` dispatches by media type:

| Input type | Handling |
| --- | --- |
| Supported text | Existing bounded UTF-8 inspection and SHA-256 receipt |
| Supported image | Bounded byte, dimension, and format validation; host visual observation contract |
| PDF | Bounded page rendering/extraction path with page-count limits |
| Unsupported media | Explicit unavailable/unsupported boundary response |

Required security and privacy controls:

- hash original bytes, rather than a rendered or compressed derivative;
- enforce file-size, image-dimension, and PDF-page limits;
- reject arbitrary remote URLs and inaccessible paths;
- do not persist raw image bytes in TailTrail state, run artifacts, logs, or rendered reports;
- persist only the source hash, metadata, and sanitized observations;
- bind all observations to the exact artifact input ID and hash.

### C. Detect visual references during requirement intake

Before `navigator_requirement_route()` in `scripts/task-start.py`, detect visual-reference language such as:

```text
attached image
attached screenshot
see attachment
as shown
as per mockup
following columns
this design
reference image
```

If the goal contains a visual reference but no inspected visual artifact is bound, create a material decision:

```json
{
  "id": "VIS-01",
  "kind": "visual-artifact-required",
  "state": "open",
  "reason": "The goal refers to a visual requirement source that was not supplied as an inspectable, hash-bound artifact."
}
```

The requirements state is then not sufficient. Scope discovery cannot begin.

### D. Integrate visual facts into requirement interpretation

Update `scripts/requirement_intake.py` so it combines:

- explicit user text;
- inspected text requirement artifacts;
- sanitized, hash-bound visual observations.

For the ECG request, the normalized requirements should be separated rather than retained as one sentence:

```text
REQ-01: Add an ECG Event Configuration section to the identified file-configuration workflow.
REQ-02: Add an Account Name dropdown with a defined option source, default, and validation state.
REQ-03: Add a + Add ECG Consumer action with a defined behavior.
REQ-04: Render the table with the visual artifact's verified column headers.
REQ-05: Preserve the existing file-configuration behavior outside the new section.
```

### E. Ask product questions before scope questions

When the image does not answer material questions, TailTrail should ask requirement questions such as:

```text
Q1. What system or API provides the Account Name dropdown options?
Q2. Is Account Name mandatory before an ECG Consumer can be added?
Q3. What are the exact table column headers?
Q4. Does + Add ECG Consumer add a row inline, open a modal, or navigate elsewhere?
Q5. Are consumer rows editable, removable, or read-only?
```

These questions are about the requested product behavior. They are valid before repository scope discovery.

### F. Enforce the requirement-before-scope boundary

`scope_question_precondition()` in `scripts/task-start.py` already checks that requirements are sufficient. Extend its input and callers so an open visual decision makes the result:

```json
{
  "state": "deferred",
  "scope_question_allowed": false,
  "reason_code": "visual-requirements-must-be-resolved-before-scope-question"
}
```

When deferred, the runtime must not:

- invoke Navigator source discovery;
- reuse, refresh, or write the graph cache;
- render candidate implementation owners;
- create a target receipt, workflow, or Planning Lock;
- grant implementation authority.

### G. Bind host attachments into Start

Update the Codex/TailTrail Start integration so a visible host attachment is passed into TailTrail as a requirement artifact rather than being represented only by prose.

Supported paths should include:

- MCP: pass the visual artifact metadata and host-produced visual observation contract to `tailtrail_start`.
- CLI: allow a local visual path through the existing requirement-artifact concept, for example:

```text
tailtrail start "<goal>" --requirement-artifact ./ecg-configuration-mockup.png
```

- Host skill: when a user says `attached image`, ensure the attachment is either bound to the Start request or report it as unavailable before planning continues.

### H. Preserve the existing Navigator role

Navigator should still decide source ownership, but only after visual requirements are sufficient. For the ECG case, it may then use visual section labels and resolved product behavior to distinguish the file-configuration workflow from other configuration pages.

If multiple source owners remain after requirements are complete, a scope question is appropriate. That question must explain the behavior-specific distinction between candidates rather than asking the user to infer it from file names.

## Expected user-facing responses

### Missing image

```text
# TailTrail Visual Requirement Required

Planning stopped before source discovery.

The request references an attached image, but no inspectable visual artifact was bound to this Start request.

Attach the image again, or provide the table headers, dropdown source/default/validation, Add ECG Consumer behavior, and row actions in text.

No source files were searched. No scope question or Planning Lock was created.
```

### Image present, details still ambiguous

```text
# TailTrail Requirements Clarification Required

Visible facts extracted:
- ECG Event Configuration section
- Account Name dropdown
- + Add ECG Consumer action
- table headers: <visible headers>

Questions:
- What is the Account Name option source?
- What does + Add ECG Consumer do?
- Are table rows editable or removable?

No source scope has been selected yet.
```

### Requirements sufficient

```text
# TailTrail Start Plan

Requirements are sufficient and artifact-bound.
Navigator may now identify the file-configuration implementation owner, focused UI proof, and preservation boundaries.
```

## Implementation sequence

1. Define the visual artifact schema and validation helpers.
2. Extend requirement-artifact preparation with a secure media-type dispatcher.
3. Add visual-reference detection and the `VIS-01` material-decision path.
4. Update requirement intake to merge visual observations into typed requirements and open questions.
5. Enforce the deferred scope precondition for unresolved visual requirements.
6. Add MCP, CLI, and host-skill attachment binding.
7. Update rendered reports with visual-artifact and clarification sections.
8. Add regression, security, and compatibility tests.
9. Run focused tests, then the full affected test suite.

## Test plan

### Functional tests

- A prompt containing `attached image` without a visual artifact returns the visual-requirement boundary response.
- The same prompt does not invoke graph discovery or create a Planning Lock.
- A valid image artifact produces hash-bound visible observations.
- Visible table headers become requirements.
- Non-visible row behavior becomes a question rather than an inferred requirement.
- Once visual questions are answered, source scope discovery proceeds normally.
- A genuine post-requirement UI ambiguity can still produce one evidence-rich scope question.

### Safety tests

- Remote URLs are rejected.
- Oversized files, excessive image dimensions, and excessive PDF pages are rejected.
- Raw image bytes never appear in state, logs, reports, or serialized planning receipts.
- A changed artifact hash invalidates prior visual observations.
- An artifact cannot be referenced by a different input ID or target workspace.

### Compatibility tests

- Existing text-only requirement artifacts behave unchanged.
- Existing UI, backend, Debug, Lite, Standard, and Full planning flows remain unchanged when no visual reference is present.
- Existing scope questions continue to work when requirements are otherwise sufficient.

## Acceptance criteria

The solution is complete when all of the following are true:

1. A prompt that references an image cannot reach source scope discovery without a bound visual artifact or an explicit equivalent textual specification.
2. TailTrail asks requirement questions before it asks the user to choose source files.
3. Visual facts are hash-bound, bounded, sanitized, and privacy-safe.
4. The runtime never infers hidden interaction behavior solely from visual appearance.
5. Scope discovery begins only after visual requirements are sufficient.
6. The ECG request can produce a normal Start Plan with a clearly identified page, section, controls, table requirements, preservation rules, and focused proof path.
7. Text-only planning behavior remains compatible.

## Out of scope

- Automatically implementing the requested ECG UI.
- Persisting images inside TailTrail run records.
- Fetching arbitrary web-hosted images.
- Universal pixel-perfect design reproduction.
- Replacing product-owner decisions with model-inferred assumptions.
