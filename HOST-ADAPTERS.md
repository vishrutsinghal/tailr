# TailTrail Host Adapter Contract

Phase E4 gives Codex, GitHub Copilot, and Claude the same versioned repository
adapter contract over the E3 transactional installer. The machine-readable
authority is `adapters/host-compatibility-v1.json`; its closed schema is
`schemas/host-adapter-contract.schema.json`.

Validation: `python3 scripts/tailtrail.py adapters conformance` checks the
versioned local composition contract; real-host and support evidence remain the
separate gates below.

NS-7 also binds `adapters/navigator-scope-scenarios-v2.json` through
`schemas/host-scope-conformance.schema.json`. Its resolved, unresolved,
conflicting, docs-only, test-only, and Debug Start fixtures require every host
to retain the CLI/MCP normalized decision fingerprint and exact path roles.
Hosts may explain public evidence, but cannot reclassify it or grant stronger
scope or execution authority.

All three hosts consume the same Navigator graph decision. Normal Start may
atomically reuse, create, incrementally refresh, rebuild, or defer the
metadata-only cache; Debug Start is reuse-only before reproduction approval.
Closure records immutable hash-bound run mappings for related future tasks.
Host reasoning may enrich the scope explanation, but graph hints and prior-run
mappings remain advisory until current-source evidence proves ownership.

FSR-5 adds the shared active-host reasoning contract in
`adapters/navigator-host-reasoning-scenarios-v1.json`, validated by
`schemas/host-scope-reasoning-conformance.schema.json`. When deterministic
evidence leaves at least two strong, hash-bound owners, Start returns a
sanitized requested packet without creating a run. The active host may choose
only one supplied alternative and must bind its schema-v2 proposal to the exact
packet, scope decision, target, goal, requirement statement, candidate IDs,
content hashes, and typed edges. CLI and MCP use the same validator and
host-neutral normalized fingerprint. Invented paths, unsupported edges, stale
content, and authority-expanding fields fail closed with no Planning Lock.
Only after a supported proposal is revalidated against a fresh Start decision
may the normal awaiting-approval lock be created.

For ordinary Lite/Off Build Start, Codex, Copilot, and Claude first project the
exact current goal and every explicitly declared requirement artifact into the
closed host requirement-interpretation contract. TailTrail boundedly reads
local UTF-8 artifacts before requirement sufficiency, records only their
SHA-256 inspection receipts in durable state, and requires artifact-derived
clauses to reference the matching input ID and hash. Missing, unreadable,
unsupported, truncated, or unbound required artifacts stop before scope.
For an ordinary Lite/Off Build Start, this contract is mandatory whenever an
active Codex, Copilot, or Claude host is declared. TailTrail returns an
`awaiting-host-interpretation` boundary before graph or scope discovery when
the active host omits it. Deterministic fallback is reserved for clients that
do not declare an agent host. Debug, Intent Bridge, and official Standard/Full
requirements retain their authority-owned interpretation paths.

For agent-host Standard and Full Build Start, TailTrail returns a verified
`official_requirement_authority` receipt before scope discovery. The active
host reads the receipt's exact official Requirements Analysis rules and every
required artifact, then returns one typed interpretation bound to the same
mode, Requirements stage, and `authority_references`. Those official rows own
the requirement boundary. Navigator may map them to repository roles but may
not regenerate or rewrite them. Start-plan approval freezes the official rows
and local scope mapping and records a durable official Requirements approval.
They classify source clauses as context, outcome, constraint, evidence, scope,
or question; resolve pronouns only from explicit nearby wording; and keep quoted
UI/error strings as literal evidence rather than semantic ownership terms.
TailTrail validates the exact goal, host identity, source-clause grounding,
reverse coverage of every explicit outcome and constraint, exact retention of
named code/data targets, requirement linkage, and absence of private reasoning
before Navigator runs. Its typed sufficiency dimensions validate evidence
completeness rather than semantic truth; question clauses cannot silently pass
as sufficient.
Material ambiguity stops before Planning Lock. This host intelligence can
improve wording and query framing, but it cannot invent files, approve scope, or
grant execution authority. Debug, Intent Bridge, and official Standard/Full
requirements retain their designated authority paths.

Every sufficient Build interpretation is frozen as one typed canonical
requirement set before scope discovery. Its stable IDs, statements, source
links, and fingerprint are reused by the query frame, requirement matrix,
hands-free program sequencing, saved Start report, and approval anchor.
Downstream planners and Program Delivery may enrich proof or ordering, but they
must reject any attempted requirement replacement or rewording.

Repository roles are equally strict: production changes require a non-test
implementation owner. Test modules, fixtures, and root or nested `conftest.py`
remain proof-only even when they define symbols or are strongly connected to a
candidate. They become editable test scope only when the current requirement
explicitly asks for test-only work; that permission never makes them production
owners.

An unresolved requirement boundary now returns a durable pre-lock intake ID.
Codex, Copilot, and Claude may read that intake and record explicit user answers
through the same typed CLI or MCP contract. Each answer creates an append-only
revision; it never creates graph metadata, a scope decision, a Planning Lock, or
execution authority. The host must re-evaluate the answered boundary before
requesting scope discovery.

Before presenting those questions, TailTrail may inspect one bounded,
decision-specific static repository slice for relevant conventions. The saved
evidence packet contains only hashes, locations, typed findings, limits, and an
optional advisory recommendation; it never runs project commands, scans
TailTrail state, proves implementation ownership, or answers for the user.
Conflicting, absent, unsupported, or limit-truncated evidence remains an
explicit question. The same evidence and fingerprint are available through the
CLI and MCP requirement-intake surfaces on every supported host.

An answered intake resumes through `tailtrail_start` with its exact
`requirement_intake_id`; the host must not rewrite the goal or switch its saved
AIDLC route. For a Standard route, this consumes the resolved pre-lock decisions
before scope discovery and then enters the verified, host-generated official
Requirements Analysis stage under the newly created run. The Navigator intake
is never labelled as an official questionnaire, and its answers never approve
the Planning Lock or the official requirements boundary.

All hosts preserve the same question precedence: target identity first,
requirement intake or official requirements second, and implementation-owner
scope only after a typed `sufficient` result. A host must not surface, infer, or
answer a scope question while TailTrail reports that precondition as `deferred`.
Phase 9 negative assurance rejects mutated scenario contracts, premature scope
permission, authority-bearing deferred results, and scope state without a typed
requirement route. These denials create no Planning Lock or execution authority.

## Qualification truth

Each E4 adapter is `contract-tested`: local tests cover its exact Core files,
instruction composition, first action, diagnostics, update, repair, rollback,
uninstall, migration, conflict handling, and receipt preparation. This does not
mean `runtime-observed` or `supported`.

- `runtime-observed` requires six fresh, sanitized, canonical-run-linked
  receipts for one exact host version.
- `supported` additionally requires the E5 platform matrix and E10 real-host
  release matrix. E4 declares no supported host versions.
- A missing executable is `not-detected`, not a failure of installed adapter
  integrity. Copilot versions are host-reported because IDE and service
  versions cannot be inferred safely from a repository.

## Exact Core surfaces

| Host | Managed Core files | First action |
| --- | --- | --- |
| Codex | `AGENTS.md`, `.codex-plugin/plugin.json`, and the `tailtrail`, `tailtrail-review`, and `tailtrail-start` skills | `tailtrail start "<your task>"` in Codex chat |
| GitHub Copilot | `.github/copilot-instructions.md`, `.github/prompts/tailtrail-start.prompt.md` | `/tailtrail-start <your task>` in Copilot Chat |
| Claude | `CLAUDE.md`, `.claude/commands/tailtrail-start.md` | `/tailtrail-start <your task>` in Claude Code |

Core is the default. Extended adds one complete versioned runtime under
`.tailtrail/install/payload/common/<version>/` and a small compatible launcher
under `.tailtrail/install/payload/<host>/` without changing the host-native
entry surface.

Every contract includes mandatory reload guidance. Codex starts a new task,
Copilot starts a new chat, and Claude starts a new Code session; each contract
also defines the stronger restart fallback when the first refresh is stale.

## Composition and enforcement

The fixed precedence is host safety, user request, verified official AI-DLC
stage rules, then TailTrail assurance rules. `doctor` checks ownership hashes,
the exact Core manifest, adapter version, required host files, and host-specific
composition markers from the installed target.

Host instruction loading and workflow invocation are host-assisted. CI remains
authoritative for enforceable repository policy, especially for Copilot where
instruction loading cannot guarantee a full workflow invocation. Global host
settings, network activity, and account changes are never part of install or
doctor; all remain separately approval-required.

## Lifecycle

```text
tailtrail install --host <codex|copilot|claude> --profile core --target .
tailtrail setup --host <codex|copilot|claude> --profile core --target .
tailtrail verify --host <host> --target .
tailtrail doctor --host <host> --target . --format json
tailtrail update --host <host> --target .
tailtrail rollback --to <transaction-id> --target .
tailtrail uninstall --host <host> --target .
```

Adapter metadata migrations use the same E3 staging, ownership, backup,
automatic restoration, and rollback path as file updates. Modified or unrelated
user files are preserved unless the user explicitly selects the existing
`--force` backup path.

## Portable runtime receipts

Prepare an immutable bundle containing six lifecycle receipt scenarios and six
scope-v2 contract fixtures without claiming either ran:

```text
tailtrail adapters runtime prepare --host <host> --root .
```

Recording remains separate. Receipts contain sanitized observations and local
artifact references; they cannot replace canonical state or turn missing,
failed, stale, or incompatible evidence into success.

`tailtrail qualify report` is the single support gate. It requires instruction
conformance, six current real-host receipts for every selected host, the exact
hosted OS/Python matrix report, and an observed identity-verified publication
receipt. The aggregate verifies GitHub attestations for the report, wheel, and
publication receipt. Any missing input is `evidence-incomplete` with a nonzero
exit.

## E4/E5/E10 boundary

E4 qualifies adapter contracts on the current local development platform. E5
owns Windows, macOS, Linux, Python, artifact, path, and permission matrices.
E10 owns real executions in named host versions. Neither is implied by E4.

## FSR-6 host release assurance

`tailtrail eval scope release-proof --root . --format json` now includes the
same generated-adapter conformance result for Codex, Copilot, and Claude that is
used by the standalone adapter checker. It also binds host conformance to the
executable Navigator calibration fingerprint. Contract success is still not a
hosted-runtime receipt; FSR-7 owns installed real-host validation.

## FSR-7 installed payload conformance

The artifact-driven proof exercises the actual Extended launchers written by
the transactional installer. Codex runs graph refresh and the sealed Start
scenario. Copilot and Claude run the same packaged adapter conformance command
through their installed launchers. Every host requires distinct completed
Core-install and Extended-update transactions, current verification, an
Extended ownership manifest, and matching source, wheel, source-distribution,
installed, and manifest hashes.

This is installed-payload evidence on the proof machine. It is not a receipt
from a hosted Codex, Copilot, or Claude session and does not upgrade support.
