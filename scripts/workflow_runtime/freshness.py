"""Classify Phase 6 input drift and preserve versioned operational checkpoints."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from workflow_runtime import adapters, compiler, contracts, ownership, storage, task_scope, transitions


LEDGER = ownership.LEDGER
CHANGE_TYPES = {"source-edit", "manifest-change", "policy-change", "graph-stale", "doc-only-edit", "branch-change", "dependency-add", "security-finding", "reproduction-change"}
DOC_SUFFIXES = {".md", ".rst", ".txt", ".adoc"}
DEPENDENCY_NAMES = {"pyproject.toml", "requirements.txt", "poetry.lock", "pdm.lock", "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "go.mod", "go.sum", "cargo.toml", "cargo.lock", "pom.xml", "build.gradle", "gradle.lockfile"}
MANIFEST_SUFFIXES = {".tf", ".tfvars", ".yaml", ".yml", ".toml", ".ini", ".cfg"}
IGNORED_PARTS = {".git", ".tailtrail", "node_modules", ".venv", "venv", "vendor", "dist", "build", "__pycache__"}


def _hash(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _directory(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "freshness"


def checkpoint_path(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "operational-checkpoint-v1.json"


def _safe_files(root: Path) -> list[Path]:
    rows: list[Path] = []
    for path in root.rglob("*"):
        if len(rows) >= 5000: break
        try: relative = path.relative_to(root)
        except ValueError: continue
        if any(part in IGNORED_PARTS for part in relative.parts) or path.is_symlink() or not path.is_file(): continue
        rows.append(path)
    return rows


def _repository_inventories(root: Path) -> tuple[dict[str, str], dict[str, str], dict[str, str], list[str]]:
    dependencies: dict[str, str] = {}; manifests: dict[str, str] = {}; policies: dict[str, str] = {}; inventory: list[str] = []
    for path in _safe_files(root):
        name = path.name.lower(); relative = _relative(root, path); selected: dict[str, str] | None = None
        if path.suffix.lower() not in DOC_SUFFIXES: inventory.append(relative)
        if name in DEPENDENCY_NAMES: selected = dependencies
        elif path.name in {"tailtrail-policy.md", "GUARDRAILS.md", "workflow-compiler-policy-v1.json"}: selected = policies
        elif path.suffix.lower() in MANIFEST_SUFFIXES or name in {"dockerfile", "makefile"}: selected = manifests
        if selected is not None: selected[relative] = _file(path)
    return dependencies, manifests, policies, sorted(inventory)


def _scoped(root: Path, workflow_id: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    scope = task_scope.show(root, workflow_id); states: dict[str, str] = {}; owners: dict[str, list[str]] = {}
    for requirement in scope.get("requirements", []):
        uid = str(requirement.get("requirement_uid", ""))
        for row in requirement.get("paths", []):
            relative = str(row.get("path", "")); current = task_scope._path_state(root, relative)
            states[relative] = current["fingerprint"]; owners.setdefault(relative, []).append(uid)
    return states, owners


def _adapter_fingerprint(root: Path, workflow_id: str, adapter_ids: set[str]) -> str:
    plan = compiler.show(root, workflow_id); rows = []
    for stage in plan["stages"]:
        if stage.get("adapter_id") not in adapter_ids: continue
        status = adapters.show(root, workflow_id, stage["stage_id"]); output = status.get("output")
        if output: rows.append({"stage_id": stage["stage_id"], "artifact": output["artifact"], "idempotency_key": output["idempotency_key"], "outcome": output["outcome"]})
    return _hash(rows)


def snapshot(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); scoped, owners = _scoped(root, workflow_id); plan = compiler.show(root, workflow_id)
    dependencies, manifests, policies, repository_inventory = _repository_inventories(root)
    docs = {path: value for path, value in scoped.items() if Path(path).suffix.lower() in DOC_SUFFIXES}
    sources = {path: value for path, value in scoped.items() if Path(path).suffix.lower() not in DOC_SUFFIXES}
    binding = ownership.show(root, workflow_id)
    reproduction = root / ".tailtrail" / "runs" / str(binding["tailtrail_run_id"]) / "debug" / "reproduction" / "approved-v1.json"
    return {"scoped_sources": sources, "scoped_docs": docs, "path_owners": owners, "manifests": manifests, "dependencies": dependencies, "policies": policies, "repository_identity": compiler._repository_identity_fingerprint(root, binding), "graph_fingerprint": _hash({"inventory":repository_inventory,"provider":_adapter_fingerprint(root, workflow_id, {"graph-discovery"})}), "security_fingerprint": _adapter_fingerprint(root, workflow_id, {"security", "quality"}), "debug_reproduction_fingerprint": _file(reproduction) if reproduction.is_file() else _hash(None), "plan_fingerprint": plan["plan_fingerprint"]}


def checkpoint(root: Path, workflow_id: str, reason: str) -> dict[str, Any]:
    if re.fullmatch(r"(?:execution-baseline|approved-baseline|manual-checkpoint|(?:stage|retry)-passed:[a-z0-9-]+)", reason) is None:
        raise ValueError("checkpoint reason must be a registered sanitized Phase 6 reason")
    root = root.resolve(); destination = checkpoint_path(root, workflow_id); prior = json.loads(destination.read_text(encoding="utf-8")) if destination.is_file() else None
    revision = int((prior or {}).get("revision", 0)) + 1; current = snapshot(root, workflow_id); binding = ownership.show(root, workflow_id)
    archive = _directory(root, workflow_id) / f"checkpoint-{revision}.json"
    payload = {"schema_version":"1","type":"tailtrail-workflow-operational-checkpoint","workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"revision":revision,"reason":reason,"snapshot":current,"snapshot_fingerprint":_hash(current),"previous_checkpoint_ref":(prior or {}).get("artifact_ref"),"artifact_ref":_relative(root, archive),"boundary":"Versioned local fingerprints only. This checkpoint does not approve, execute, retry, recover, or overwrite source."}
    contracts.require_valid(payload); LEDGER.atomic_json(destination, payload); LEDGER.atomic_json(archive, payload)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_operational_checkpoint_recorded", {"workflow_id":workflow_id,"revision":revision,"reason":reason,"artifact":_relative(root, archive),"snapshot_fingerprint":payload["snapshot_fingerprint"]})
    return {"artifact": _relative(root, archive), **payload}


def ensure(root: Path, workflow_id: str) -> dict[str, Any]:
    path = checkpoint_path(root.resolve(), workflow_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else checkpoint(root, workflow_id, "execution-baseline")


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    """Read the current checkpoint and latest assessment without creating state."""
    root = root.resolve(); saved = checkpoint_path(root, workflow_id); directory = _directory(root, workflow_id)
    assessments = sorted(directory.glob("assessment-*.json")) if directory.is_dir() else []
    return {
        "type":"tailtrail-workflow-freshness-status",
        "workflow_id":workflow_id,
        "checkpoint":json.loads(saved.read_text(encoding="utf-8")) if saved.is_file() else None,
        "latest_assessment":json.loads(assessments[-1].read_text(encoding="utf-8")) if assessments else None,
        "boundary":"Read-only status. No checkpoint, assessment, transition, retry, or correction was created.",
    }


def _changed(before: dict[str, Any], after: dict[str, Any], key: str) -> bool:
    return before.get(key) != after.get(key)


def _requirements_for_change(before: dict[str, Any], after: dict[str, Any], key: str, all_uids: list[str]) -> list[str]:
    if key not in {"scoped_sources", "scoped_docs"}: return all_uids
    prior = before.get(key, {}); current = after.get(key, {}); owners = {**before.get("path_owners", {}), **after.get("path_owners", {})}
    changed = {path for path in set(prior) | set(current) if prior.get(path) != current.get(path)}
    selected = {uid for path in changed for uid in owners.get(path, [])}
    return sorted(selected) or all_uids


def _roots(stages: list[dict[str, Any]], change_type: str) -> set[str]:
    names = {row["stage_id"] for row in stages}
    if change_type == "doc-only-edit": return set()
    if change_type in {"branch-change", "policy-change"}: return names
    if change_type == "reproduction-change": return names & {"d-02-reproduction"}
    if change_type in {"manifest-change", "dependency-add", "graph-stale"}: return names & {"bootstrap","discover","graph-impact","graph-freshness","bounded-discovery","graph-overlay","d-03-project-orientation"}
    if change_type == "source-edit": return names & {"implement", "d-03-project-orientation", "d-08-correction-implementation"}
    if change_type == "security-finding": return names & ({"security"} if "security" in names else {"review","root-cause"})
    return set()


def _downstream(stages: list[dict[str, Any]], roots: set[str]) -> set[str]:
    selected = set(roots)
    while True:
        expanded = selected | {row["stage_id"] for row in stages if set(row.get("prerequisites", [])) & selected}
        if expanded == selected: return selected
        selected = expanded


def assess(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); baseline = ensure(root, workflow_id); before = baseline["snapshot"]; after = snapshot(root, workflow_id); plan = compiler.show(root, workflow_id)
    detected: list[str] = []
    mapping = (("source-edit","scoped_sources"),("manifest-change","manifests"),("policy-change","policies"),("graph-stale","graph_fingerprint"),("branch-change","repository_identity"),("dependency-add","dependencies"),("security-finding","security_fingerprint"),("reproduction-change","debug_reproduction_fingerprint"))
    for change_type, key in mapping:
        if _changed(before, after, key): detected.append(change_type)
    if _changed(before, after, "scoped_docs") and not detected: detected.append("doc-only-edit")
    impacted = sorted(set().union(*(_downstream(plan["stages"], _roots(plan["stages"], item)) for item in detected), set()))
    binding = ownership.show(root, workflow_id); all_uids = binding["requirement_uids"]
    details = [{"change_type":item,"before_hash":_hash(before.get(dict(mapping).get(item, "scoped_docs"))),"after_hash":_hash(after.get(dict(mapping).get(item, "scoped_docs"))),"affected_stage_ids":sorted(_downstream(plan["stages"], _roots(plan["stages"], item))),"requirement_uids":_requirements_for_change(before, after, dict(mapping).get(item, "scoped_docs"), all_uids)} for item in detected]
    affected_uids = sorted({uid for row in details for uid in row["requirement_uids"]}) or all_uids
    payload = {"schema_version":"1","type":"tailtrail-workflow-freshness-assessment","workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"checkpoint_revision":baseline["revision"],"checkpoint_fingerprint":baseline["snapshot_fingerprint"],"status":"fresh" if not detected else "documentation-only" if detected == ["doc-only-edit"] else "stale","change_types":detected,"changes":details,"affected_stage_ids":impacted,"requirement_uids":affected_uids,"boundary":"Automatic fingerprint comparison only. Assessment does not edit source, retry work, apply recovery, or treat changed input as approved."}
    contracts.require_valid(payload); directory = _directory(root, workflow_id); artifact = directory / f"assessment-{len(list(directory.glob('assessment-*.json'))) + 1}.json"; LEDGER.atomic_json(artifact, payload)
    return {"artifact":_relative(root, artifact), **payload}


def apply(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); result = assess(root, workflow_id)
    if result["status"] in {"fresh", "documentation-only"}: return result
    projection = storage.status(root, workflow_id)["last_valid_projection"]
    if projection["workflow_status"] in {"completed", "cancelled", "superseded"}:
        result["terminal_boundary"] = "Terminal workflow history is immutable; create an approved follow-up workflow for changed inputs."
        return result
    newly_stale: list[str] = []
    for stage_id in result["affected_stage_ids"]:
        if projection.get("stages", {}).get(stage_id, {}).get("status") == "passed":
            transitions.stage(root, workflow_id, stage_id, "stale", "input-stale")
            newly_stale.append(stage_id)
    binding = ownership.show(root, workflow_id); LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_freshness_classified", {"workflow_id":workflow_id,"artifact":result["artifact"],"change_types":result["change_types"],"affected_stage_ids":result["affected_stage_ids"]})
    if newly_stale:
        from workflow_runtime import correction
        result["correction"] = correction.route(root, workflow_id, newly_stale[0], "new-drift")
    return result


def operational_scope_matches(root: Path, workflow_id: str) -> bool:
    path = checkpoint_path(root.resolve(), workflow_id)
    if not path.is_file(): return False
    saved = json.loads(path.read_text(encoding="utf-8")); current, _owners = _scoped(root.resolve(), workflow_id)
    expected = {**saved.get("snapshot", {}).get("scoped_sources", {}), **saved.get("snapshot", {}).get("scoped_docs", {})}
    return current == expected
