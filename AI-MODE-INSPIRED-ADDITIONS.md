# AI Mode Inspiration: High-Value TailTrail Additions

Source reviewed: [ai-mode/ai-mode](https://github.com/ai-mode/ai-mode), accessed 2026-08-21.

AI Mode is an Emacs integration, so its completion UI, buffer chat, and provider
backends are not TailTrail features. TailTrail already has graph caching, context
receipts, requirement-linked execution evidence, and prompt-cache-safe context
ordering. The two additions below are the remaining ideas with clear delivery
value and a compatible privacy posture.

## 1. Opt-In Request Provenance Manifest

AI Mode's strongest transferable idea is inspectable, structured execution
context with a request identifier and audit trail. TailTrail should add an
optional, metadata-only manifest for each agent request in an approved run.

The manifest would record:

- run ID, request ID, timestamp, and host/adapter identity;
- the selected requirement IDs and action category;
- context artifact paths, content hashes, exactness classes, and token estimate;
- model/provider identity only when the host exposes it; and
- outcome category, duration, cancellation state, and links to existing evidence.

It must never capture prompt bodies, model responses, source snippets, secrets,
or hidden telemetry. The user enables it per run or repository, can inspect the
manifest before dispatch, and can delete it through a documented retention
command. This turns "what did the agent see and do?" into a reviewable fact
without weakening TailTrail's privacy and evidence boundaries.

**Why it adds value:** TailTrail records source edits and validation receipts
after they occur, while this supplies the missing provenance between a planning
decision and a host action. It makes incident review, unexpected context use,
and token-cost diagnosis substantially easier.

**Smallest viable slice:** define a versioned JSON schema and a CLI
`request-manifest show|delete`; have the Copilot/MCP adapter write one only when
the user explicitly enables it. Link manifests from execution evidence rather
than creating a parallel completion system.

## 2. Declarative, Capability-Constrained Task Recipes

AI Mode lets users add commands declaratively instead of modifying its core.
TailTrail can adopt that idea as repository-local task recipes for recurring
work, such as "API change", "dependency update", or "release note".

Each recipe should be a validated data file that declares only:

- a goal template and requirement categories;
- the TailTrail context slice and known policy references;
- allowed evidence types and focused validation *suggestions*; and
- the approval level required before any action.

Recipes must not execute shell commands, inject arbitrary prompt text, override
policy, reduce safeguards, or bypass the Planning Lock. The Navigator expands a
selected recipe into its normal plan, shows every derived setting, and still
requires approval. A strict schema and `recipe validate` command keep recipes
reviewable and portable across supported AI hosts.

**Why it adds value:** Teams repeat delivery shapes more often than they repeat
exact tasks. Recipes reduce setup variance, preserve agreed review and evidence
expectations, and avoid hard-coding organization workflow into TailTrail's
Python implementation.

**Smallest viable slice:** add a schema plus one example recipe, then support a
read-only `tailtrail recipe inspect <name>` command. Defer executing recipes or
adding custom command hooks until that surface proves useful.

## Explicitly Not Recommended

- AI code completion, editor-bound chat, and response buffers belong to editor
  integrations, not an approval-first delivery harness.
- Provider/back-end management duplicates host responsibilities and would add
  credential, privacy, and support risk.
- Raw request/response logging conflicts with TailTrail's no-hidden-telemetry
  and exactness/privacy posture.
- AI-generated project-summary indexes overlap with the existing Code Graph
  Mapper and would add uncertain cost and freshness behavior.