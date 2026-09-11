#!/usr/bin/env python3
"""Generate and validate the versioned TailTrail host-composition surface."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
CONTRACTS_PATH = next(path for path in (ROOT / "tailtrail" / "hosts" / "contracts.py", ROOT / "hosts" / "contracts.py") if path.is_file())
_spec = importlib.util.spec_from_file_location("tailtrail_host_contracts_adapter", CONTRACTS_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError("unable to load TailTrail host contracts")
_contracts_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _contracts_module
_spec.loader.exec_module(_contracts_module)
load_contracts = _contracts_module.contracts
REQUIRED_SCENARIOS = {"small-bug", "hands-free-feature", "rejected-requirement", "evidence-failure", "recovery", "ci-wait"}
REQUIRED_SCOPE_SCENARIOS = {"resolved", "unresolved", "conflicting", "docs-only", "test-only", "debug-start"}
REQUIRED_REASONING_SCENARIOS = {"supported-selection", "invented-path", "unsupported-edge", "stale-packet", "authority-escalation"}
REQUIRED_REQUIREMENT_ROUTING_SCENARIOS = {
    "host-interpretation-required", "lite-intake", "standard-intake",
    "full-intake", "scope-disabled-requirements-open", "answered-intake",
    "eligible-scope-question",
}
SCOPE_EXPECTATIONS = {
    "resolved": ("build", "resolved", "pass", "implementation-owner"),
    "unresolved": ("build", "unresolved", "block", "none"),
    "conflicting": ("build", "ambiguous", "block", "none"),
    "docs-only": ("build", "resolved", "pass", "documentation"),
    "test-only": ("build", "resolved", "pass", "test"),
    "debug-start": ("debug", "unresolved", "orientation-only", "none"),
}
PRECEDENCE = ["host safety", "user request", "official stage rules", "tailtrail assurance rules"]
STALE_SCOPE_TEXT = "source discovery only after planning lock"

_scope_spec = importlib.util.spec_from_file_location("tailtrail_host_scope_contract", ROOT / "scripts" / "navigator_scope.py")
if _scope_spec is None or _scope_spec.loader is None:
    raise RuntimeError("unable to load Navigator scope contract")
_scope_module = importlib.util.module_from_spec(_scope_spec)
sys.modules[_scope_spec.name] = _scope_module
_scope_spec.loader.exec_module(_scope_module)


def load(root: Path) -> dict:
    payload = load_contracts(root)
    if payload.get("type") != "tailtrail-host-adapter-compatibility" or payload.get("adapter_version") != "v3":
        raise ValueError("host compatibility matrix must be a v3 TailTrail adapter matrix")
    if payload.get("precedence") != PRECEDENCE:
        raise ValueError("host compatibility precedence is not the required safety order")
    if {item.get("id") for item in payload.get("conformance_scenarios", [])} != REQUIRED_SCENARIOS:
        raise ValueError("host compatibility matrix must define the six required conformance scenarios")
    scope_contract = load_scope_contract(root)
    if payload.get("scope_scenarios") != "adapters/navigator-scope-scenarios-v2.json":
        raise ValueError("host compatibility matrix must bind the canonical v2 scope scenario contract")
    if payload.get("scope_scenario_schema") != "schemas/host-scope-conformance.schema.json":
        raise ValueError("host compatibility matrix must bind the v2 scope scenario schema")
    if {item.get("id") for item in scope_contract.get("scenarios", [])} != REQUIRED_SCOPE_SCENARIOS:
        raise ValueError("host scope contract must define the six required v2 scenarios")
    reasoning_contract = load_reasoning_contract(root)
    if payload.get("scope_reasoning_scenarios") != "adapters/navigator-host-reasoning-scenarios-v1.json":
        raise ValueError("host compatibility matrix must bind the canonical host reasoning scenarios")
    if payload.get("scope_reasoning_scenario_schema") != "schemas/host-scope-reasoning-conformance.schema.json":
        raise ValueError("host compatibility matrix must bind the host reasoning scenario schema")
    if {item.get("id") for item in reasoning_contract.get("scenarios", [])} != REQUIRED_REASONING_SCENARIOS:
        raise ValueError("host reasoning contract must define the five required scenarios")
    requirement_contract = load_requirement_routing_contract(root)
    if payload.get("requirement_routing_scenarios") != "adapters/requirement-routing-scenarios-v1.json":
        raise ValueError("host compatibility matrix must bind requirement-routing scenarios")
    if payload.get("requirement_routing_scenario_schema") != "schemas/host-requirement-routing-conformance.schema.json":
        raise ValueError("host compatibility matrix must bind the requirement-routing schema")
    if {item.get("id") for item in requirement_contract.get("scenarios", [])} != REQUIRED_REQUIREMENT_ROUTING_SCENARIOS:
        raise ValueError("host requirement-routing contract must define the seven required scenarios")
    return payload


def load_scope_contract(root: Path) -> dict:
    path = root / "adapters" / "navigator-scope-scenarios-v2.json"
    schema = root / "schemas" / "host-scope-conformance.schema.json"
    if not path.is_file() or not schema.is_file():
        raise ValueError("host scope scenario contract or schema is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "2" or payload.get("type") != "tailtrail-host-scope-conformance" or payload.get("contract_version") != "v2":
        raise ValueError("host scope scenario contract is incompatible")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 6:
        raise ValueError("host scope scenario contract must contain exactly six scenarios")
    for row in scenarios:
        if not isinstance(row, dict) or set(row) != {"id", "workflow", "expected_state", "scope_gate", "editable_role", "required_host_observations", "boundary"}:
            raise ValueError("host scope scenario entry is invalid")
        expected = SCOPE_EXPECTATIONS.get(str(row.get("id")))
        observed = (row.get("workflow"), row.get("expected_state"), row.get("scope_gate"), row.get("editable_role"))
        observations = row.get("required_host_observations")
        if expected != observed or not isinstance(observations, list) or len(observations) < 3 or len(observations) != len(set(observations)) or not all(isinstance(value, str) and value for value in observations) or not isinstance(row.get("boundary"), str) or not row["boundary"]:
            raise ValueError(f"host scope scenario `{row.get('id')}` violates its closed contract")
    return payload


def load_reasoning_contract(root: Path) -> dict:
    path = root / "adapters" / "navigator-host-reasoning-scenarios-v1.json"
    schema = root / "schemas" / "host-scope-reasoning-conformance.schema.json"
    if not path.is_file() or not schema.is_file():
        raise ValueError("host scope reasoning contract or schema is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1" or payload.get("type") != "tailtrail-host-scope-reasoning-conformance" or payload.get("contract_version") != "v1":
        raise ValueError("host scope reasoning scenario contract is incompatible")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 5:
        raise ValueError("host scope reasoning contract must contain exactly five scenarios")
    expected = {
        "supported-selection": ("accepted", "resolved", "host-proposal-evidence-validated"),
        "invented-path": ("rejected", "ambiguous", "unknown-paths"),
        "unsupported-edge": ("rejected", "ambiguous", "unknown-edges"),
        "stale-packet": ("rejected", "ambiguous", "stale-path-content"),
        "authority-escalation": ("rejected", "ambiguous", "host-authority-escalation-rejected"),
    }
    for row in scenarios:
        if not isinstance(row, dict) or set(row) != {"id", "proposal_status", "scope_state", "run_created", "reason_code", "boundary"}:
            raise ValueError("host scope reasoning scenario entry is invalid")
        observed = (row.get("proposal_status"), row.get("scope_state"), row.get("reason_code"))
        if expected.get(str(row.get("id"))) != observed or row.get("run_created") is not False or not row.get("boundary"):
            raise ValueError(f"host scope reasoning scenario `{row.get('id')}` violates its closed contract")
    return payload


def load_requirement_routing_contract(root: Path) -> dict:
    path = root / "adapters" / "requirement-routing-scenarios-v1.json"
    schema = root / "schemas" / "host-requirement-routing-conformance.schema.json"
    if not path.is_file() or not schema.is_file():
        raise ValueError("host requirement-routing scenario contract or schema is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        payload.get("schema_version") != "1"
        or payload.get("type") != "tailtrail-host-requirement-routing-conformance"
        or payload.get("contract_version") != "v1"
    ):
        raise ValueError("host requirement-routing scenario contract is incompatible")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 7:
        raise ValueError("host requirement-routing contract must contain exactly seven scenarios")
    expected = {
        "host-interpretation-required": ("host-interpretation-required", "host-interpretation", False, False),
        "lite-intake": ("clarification-required", "lite-questions", False, False),
        "standard-intake": ("standard-recommended", "aidlc-standard", False, False),
        "full-intake": ("full-recommended", "aidlc-full", False, False),
        "scope-disabled-requirements-open": ("clarification-required", "lite-questions", False, False),
        "answered-intake": ("sufficient", "scope", True, False),
        "eligible-scope-question": ("sufficient", "scope", True, False),
    }
    required_keys = {
        "id", "requirement_state", "route", "scope_question_allowed",
        "run_created", "boundary",
    }
    for row in scenarios:
        if not isinstance(row, dict) or set(row) != required_keys:
            raise ValueError("host requirement-routing scenario entry is invalid")
        observed = (
            row.get("requirement_state"), row.get("route"),
            row.get("scope_question_allowed"), row.get("run_created"),
        )
        if expected.get(str(row.get("id"))) != observed or not row.get("boundary"):
            raise ValueError(f"host requirement-routing scenario `{row.get('id')}` violates its closed contract")
    return payload


def scope_projection(host: str, value: dict) -> dict:
    """Expose one canonical scope decision without host reclassification."""
    return _scope_module.host_scope_contract(host, value)


def render(host: dict, matrix: dict, root: Path = ROOT) -> str:
    scenarios = "\n".join(f"- **{item['id']}:** {item['expected']}" for item in matrix["conformance_scenarios"])
    scope_contract = load_scope_contract(root)
    reasoning_contract = load_reasoning_contract(root)
    requirement_contract = load_requirement_routing_contract(root)
    scope_rows = "\n".join(
        f"- **{item['id']}:** `{item['expected_state']}` / `{item['scope_gate']}` / editable role `{item['editable_role']}`."
        for item in scope_contract["scenarios"]
    )
    scenarios += "\n\n## Scope evidence v2 host boundary\n\n- Consume the canonical normalized decision fingerprint and owner, inspection, proof, and excluded roles returned by CLI or MCP.\n- Host reasoning may explain public evidence-edge references, uncertainty, and alternatives; it cannot reclassify a path or promote unresolved/conflicting evidence.\n- Scope investigation occurs before Planning Lock persistence. Unresolved or conflicting Build scope creates no Planning Lock; Debug Start records command-free orientation only.\n- Normal Start lets Navigator transactionally reuse, create, refresh, or rebuild metadata-only graph state. Debug Start may only reuse a fresh graph before reproduction approval.\n- Graph suggestions and complete prior-run mappings remain advisory until hash and current-source relationship validation; no approval transfers between runs.\n- Closure refreshes actual changed graph scope and records an immutable run mapping for later relevant retrieval.\n- Planning Lock approval, Debug reproduction/correction approval, AIDLC authority, Intent Bridge authority, and closure drift remain separate gates.\n\n" + scope_rows
    reasoning_rows = "\n".join(
        f"- **{item['id']}:** `{item['proposal_status']}` / scope `{item['scope_state']}` / run created `{str(item['run_created']).lower()}`."
        for item in reasoning_contract["scenarios"]
    )
    scenarios += "\n\n## Active-host scope reasoning boundary\n\n- When deterministic evidence leaves two or more hash-bound strong owners, consume the requested packet and return one schema-v2 public-evidence proposal.\n- Bind every proposal to the exact packet, scope decision, target, goal, requirement statement, candidate identity, current content hash, and evidence edges.\n- Submit the proposal through CLI or MCP validation before Start persistence. Unsupported, stale, or authority-expanding proposals create no run and must not be rewritten as confidence.\n- Host identity is transport metadata: Codex, Copilot, and Claude must produce the same normalized decision for the same proposal.\n\n" + reasoning_rows
    requirement_rows = "\n".join(
        f"- **{item['id']}:** requirement `{item['requirement_state']}` / route `{item['route']}` / scope question `{str(item['scope_question_allowed']).lower()}` / run created `{str(item['run_created']).lower()}`."
        for item in requirement_contract["scenarios"]
    )
    scenarios += "\n\n## Requirement-before-scope host boundary\n\n- Consume MCP `requirement_route` directly; do not infer requirement state from rendered prose.\n- Preserve target identity, then requirement sufficiency, then implementation scope as the only question order.\n- A `deferred` requirement route forbids graph work, owner questions, and Planning Lock creation.\n- Scope release failure cannot preempt an unresolved requirement intake.\n- Only a typed `eligible` route permits bounded scope investigation or one validated scope question.\n- A missing route or deferred route combined with scope, host-refinement, or run authority is a conformance failure; never reinterpret it.\n\n" + requirement_rows
    scenarios += "\n\n## Interactive Plan boundary\n\n- Preserve the current run ID for questions and plan-update requests.\n- Explain saved evidence first; source investigation and plan revision require their separate approvals.\n- Do not start implementation after a why-question or a revision request.\n- Route AIDLC and Intent Bridge wording changes to their designated authority.\n\n## Debug next-action boundary\n\n- After every reproduction proposal, revision, show, or approval transition, return the canonical `Next actions` and `Route to a code fix` guidance.\n- Preserve the exact run ID and revision in compact natural-language prompts for approval, revision, explanation, rejection, status, stop, and resume as applicable.\n- Contract approval is not reproduction proof. Run only the approved bounded procedure, record factual command evidence, and record a typed pre-fix attempt.\n- A not-reproduced or inconclusive attempt keeps hypotheses and correction blocked and returns a sanitized `awaiting-reproduction-input` request after bounded difference checks.\n- New user evidence creates a separately approved reproduction revision. Post-fix closure requires a factual restored attempt against the same approved boundary.\n- A future correction prompt is staged guidance only; it never grants source-write authority or advances the lifecycle automatically.\n\n## Common stop and exact resume\n\n- `tailtrail stop` uses the common durable attachment control, preserves the exact run, and returns later ordinary prompts to the normal host agent.\n- `tailtrail resume --run-id <exact-run-id>` reattaches only that run without approving or advancing workflow execution."
    surface = f"""# TailTrail Composed Host Surface — {host['id'].title()}\n\n**Adapter version:** `{matrix['adapter_version']}`\n**Host source:** `{host['source']}`\n\n## Precedence\n\n1. Host safety\n2. User request\n3. Official AI-DLC stage rules for a verified Full-mode run\n4. TailTrail assurance rules\n\nA lower layer cannot weaken a higher layer. Official rules select lifecycle\nstages; TailTrail preserves the approved anchor, evidence, drift, recovery, and\nclosure boundaries.\n\n## Host contract\n\n- `tailtrail start` is planning-only and requires approval before implementation.\n- A rejected requirement preserves its run and routes to requirements/design.\n- Completion uses saved requirement-linked evidence; do not invent command or CI results.\n- `wait-ci` does not create learning. Linked CI acceptance may create a\n  candidate-only learning artifact and deterministic evaluation.\n- {host['official_full_mode']}.\n\n## Conformance scenarios\n\n{scenarios}\n\n## Durable Workflow MCP boundary\n\n- Use the same canonical workflow ID and approved run across status, evidence,\n  correction, resume, and closure.\n- Read-only workflow MCP tools inspect local state only; controlled workflow\n  tools require explicit approval and cannot invent Planning Lock, AIDLC,\n  dependency, recovery, or closure authority.\n- Host receipts are sanitized, linked evidence. They do not replace the\n  canonical workflow status or completion boundary.\n- CI continuation requires the exact approved CI policy plus run, target,\n  plan, scope, commit, artifact-hash, and trusted-provenance bindings. It may\n  advance validation/reporting metadata only; it never fixes source, changes\n  dependencies/infrastructure, scans, calls providers, publishes, deploys,\n  merges, recovers, or finalizes closure.\n- Negative assurance returns categorical issue and denial codes only; hosts must\n  not echo hostile prompts, source, logs, identities, credentials, or commands.\n- Retention is local, count-based, and manual. There is no background deletion\n  or upload; exact candidate and plan bindings plus explicit approval are required.\n\n## Boundary\n\nThis generated surface validates local instruction composition only. It does not\nguarantee runtime behavior by the host or replace host safety policy.\n"""
    surface = surface.replace(
        f"**Host source:** `{host['source']}`\n\n",
        f"**Host source:** `{host['source']}`\n**Qualification:** `{host['qualification']}` (not runtime-observed or supported)\n\n",
    )
    surface = surface.replace(
        "- Completion uses saved requirement-linked evidence; do not invent command or CI results.\n",
        "- Run approved local proof through `execution_evidence_run` so TailTrail captures exit code, duration, and redacted output; label-only results remain unverified.\n"
        "- Completion uses the current saved requirement-linked evidence snapshot; do not invent command or CI results.\n",
    )
    surface = surface.replace(
        f"- {host['official_full_mode']}.\n\n",
        f"- {host['official_full_mode']}.\n- First action in {host['first_action']['surface']}: `{host['first_action']['invocation']}`\n- Enforceable repository policy remains `{host['capabilities']['policy_enforcement']}`.\n- Global settings, network activity, and account changes are approval-required.\n\n",
    )
    natural_intent = (
        "- An explicit TailTrail task in ordinary language routes to planning-only Start; "
        "preserve the user's goal and let Navigator discover scope and controls.\n"
        "- A request asking only for an approach routes to `guide`; an active-run why, "
        "scope, file, or validation question routes to `discuss` on the same run.\n"
        "- `looks good`, `go ahead`, `proceed`, and similar wording never approve. Only "
        "explicit approval may reach an approval-controlled operation.\n"
        "- `tailtrail intent resolve` and MCP `intent_resolve` are read-only typed "
        "recommendations. They never create a run, infer approval, or execute work.\n"
        "- For ordinary Lite/Off Build Start, use host language understanding to classify "
        "exact-goal-bound context, outcome, constraint, evidence, scope, and question clauses. "
        "Keep quoted literals separate from semantic intent terms; send no private reasoning.\n"
        "- Pass every explicitly referenced local requirement file through `requirement_artifacts`. "
        "Consume its bounded inspection ID and SHA-256, bind artifact clauses with "
        "`source_input_id` and `artifact_evidence`, and never replace unread content with a generic requirement.\n"
        "- Pass the validated typed interpretation to `tailtrail_start`. Missing, unreadable, unsupported, "
        "truncated, or unbound required artifacts and material ambiguity stop before scope and Planning Lock; "
        "host interpretation never grants scope or execution authority.\n"
        "- For agent-host Standard/Full Build Start, consume `official_requirement_authority`, "
        "read every exact verified governing rule and required artifact, and resubmit with "
        "`authority: official-ai-dlc-pack`, the matching mode/Requirements stage, and identical "
        "`authority_references`. Official requirements must exist before Navigator scope discovery; "
        "TailTrail maps but never rewrites them.\n"
        "- Consume bounded static scope evidence with the active host's reasoning; "
        "compare owners, callers, proof, alternatives, preservation, and uncertainty.\n"
        "- Return typed evidence-edge references without private chain-of-thought. "
        "Never invent scope or override an unresolved/rejected proposal.\n"
        "- Treat target selection and scope quality as separate gates. A Scope Confirmation "
        "report is non-persisted: ask only SCOPE-Q1 when present, claim no run ID, and "
        "retain the exact v2 decision fingerprint after resolution.\n"
    )
    surface = surface.replace(
        "- `tailtrail start` is planning-only and requires approval before implementation.\n",
        "- `tailtrail start` is planning-only and requires approval before implementation.\n" + natural_intent,
    )
    release = "- Phase 11 release proof accepts only linked sanitized scenario, template, and host receipts. Missing evidence remains blocked.\n- A passing release gate never retires `--no-workflow`; separate exact-gate approval and a reviewed release change are required.\n\n"
    enterprise = "- Phase 12 enterprise continuation is optional, provider-neutral, and local-default. Hosts must require the passing Phase 11 gate, complete approved entry policy, per-workflow activation, tenant/actor authority, and current fencing token.\n- Enterprise receipts and observability are sanitized metadata shadows only; canonical local ownership, approvals, evidence, recovery, and closure always win. Hosts must not upload raw workflow/source/log data or infer provider readiness from local conformance.\n\n"
    return surface.replace("## Boundary\n\n", release + enterprise + "## Boundary\n\n")


def generate(root: Path, matrix: dict) -> list[str]:
    outputs = []
    for host in matrix["hosts"]:
        path = root / host["generated"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(host, matrix, root), encoding="utf-8")
        outputs.append(path.relative_to(root).as_posix())
    return outputs


def check(root: Path, matrix: dict) -> list[str]:
    errors = []
    for host in matrix["hosts"]:
        source = root / host["source"]
        generated = root / host["generated"]
        if not source.is_file(): errors.append(f"{host['id']}: source missing: {host['source']}")
        elif "Interactive Plan Mode" not in source.read_text(encoding="utf-8"):
            errors.append(f"{host['id']}: source does not preserve the Interactive Plan Mode host boundary")
        else:
            source_body = source.read_text(encoding="utf-8")
            if "Scope evidence v2 host boundary" not in source_body:
                errors.append(f"{host['id']}: source does not preserve the v2 scope host boundary")
            if "Requirement-before-scope host boundary" not in source_body:
                errors.append(f"{host['id']}: source does not preserve requirement-first question precedence")
            if "Requirement-routing negative assurance" not in source_body:
                errors.append(f"{host['id']}: source does not preserve requirement-routing negative assurance")
            if "canonical `Next actions` and `Route to a code fix` guidance" not in source_body:
                errors.append(f"{host['id']}: source does not preserve the Debug next-action boundary")
            if "awaiting-reproduction-input" not in source_body:
                errors.append(f"{host['id']}: source does not preserve the not-reproduced user-input boundary")
            if STALE_SCOPE_TEXT in source_body.lower():
                errors.append(f"{host['id']}: source contains stale post-lock discovery guidance")
        if not generated.is_file():
            errors.append(f"{host['id']}: generated surface missing: {host['generated']}")
        elif generated.read_text(encoding="utf-8") != render(host, matrix, root):
            errors.append(f"{host['id']}: generated surface is stale")
        elif STALE_SCOPE_TEXT in generated.read_text(encoding="utf-8").lower():
            errors.append(f"{host['id']}: generated surface contains stale post-lock discovery guidance")
        else:
            generated_body = generated.read_text(encoding="utf-8")
            if "Active-host scope reasoning boundary" not in generated_body or "exact packet, scope decision, target, goal" not in generated_body:
                errors.append(f"{host['id']}: generated surface does not preserve FSR-5 host reasoning")
            if "Requirement-before-scope host boundary" not in generated_body or "MCP `requirement_route`" not in generated_body:
                errors.append(f"{host['id']}: generated surface does not preserve Phase 8 requirement routing")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="Regenerate composed host surfaces from the versioned matrix.")
    args = parser.parse_args(); root = args.root.resolve()
    try:
        matrix = load(root)
        generated = generate(root, matrix) if args.write else []
        errors = check(root, matrix)
        if errors:
            for error in errors: print(f"Host adapter conformance failed: {error}")
            return 1
        scope_contract = load_scope_contract(root)
        reasoning_contract = load_reasoning_contract(root)
        requirement_contract = load_requirement_routing_contract(root)
        print(json.dumps({"status": "passed", "adapter_version": matrix["adapter_version"], "hosts": [item["id"] for item in matrix["hosts"]], "scenarios": [item["id"] for item in matrix["conformance_scenarios"]], "scope_contract_version": scope_contract["contract_version"], "scope_scenarios": [item["id"] for item in scope_contract["scenarios"]], "scope_reasoning_contract_version": reasoning_contract["contract_version"], "scope_reasoning_scenarios": [item["id"] for item in reasoning_contract["scenarios"]], "requirement_routing_contract_version": requirement_contract["contract_version"], "requirement_routing_scenarios": [item["id"] for item in requirement_contract["scenarios"]], "generated": generated, "boundary": matrix["boundary"]}, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Host adapter conformance error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
