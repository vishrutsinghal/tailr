# Command Registry - Consumer Updates Explanation

## Current State (Without Registry Leverage)

The **core registry is built in planning_lock.py and validated in planning-audit.py**, but downstream consumers still work with:
- `validation_contract.commands` (embedded command strings)
- `checks[].command` (embedded strings in checks)
- `focused_validation[].command` (embedded strings)

This works perfectly due to backward compatibility, but doesn't get the data deduplication benefits.

---

## What Needs to Happen

To fully leverage the registry and get 76% data reduction, three downstream files need to use `command_id` references instead of embedded commands.

---

## 1. `scripts/task-start.py` - Emit Registry IDs in Focused Validation

### Current Behavior
```python
# In attach_focused_validation_contracts()
checks = []
for proof in linked:
    command = str(proof.get("command", ""))  # ← Embedding full command
    if not command:
        continue
    checks.append({
        "kind": "proof",
        "command": command,  # ← Duplicated across all rows
        "tiers": [...],
        "candidate_paths": [...],
    })

# Later in coalesce_focused_validation_rows()
for source in rows:
    row["command"]  # ← Still embedding command everywhere
```

### What Needs to Change

**1. Import command_id function from planning_lock:**
```python
def attach_focused_validation_contracts(requirements, rows, command_registry=None):
    # Accept registry from caller or build inline
    if command_registry is None:
        command_registry = {}
```

**2. Generate IDs when storing checks:**
```python
from scripts import planning_lock as LOCK

# In attach_focused_validation_contracts()
checks = []
for proof in linked:
    command = str(proof.get("command", ""))
    if not command:
        continue
    
    # NEW: Generate ID for this command
    cmd_id = LOCK._command_id(command)
    command_registry[cmd_id] = {
        "command": command,
        "kind": "proof"
    }
    
    # Store check with ID instead of embedded command
    checks.append({
        "kind": "proof",
        "command_id": cmd_id,  # ← Use ID reference
        "tiers": [...],
        "candidate_paths": [...],
    })
```

**3. Update coalesce_focused_validation_rows:**
```python
# Change the merge key to use command_id
key = (
    str(row.get("requirement_id", "")),
    str(row.get("candidate", "")),
    str(row.get("command_id", "")),  # ← Use ID instead of command
    str(row.get("candidate_state", "unresolved")),
)

# Remove command from grouped rows, keep only command_id
# Don't include "command" field when outputting rows
if "command" in row:
    del row["command"]
```

**4. Return registry with report:**
```python
requirement["validation_contract"] = {
    "state": ...,
    "tiers": ...,
    "commands": ...,  # Keep for backward compat
    "checks": checks_with_ids,
    "command_registry": command_registry,  # NEW
}
```

### Impact
- ✅ Eliminates command duplication in focused_validation
- ✅ Uses single registry reference per command
- ✅ Focused validation rows become smaller (8 chars vs 150+ chars per tier)

---

## 2. `scripts/execution-evidence.py` - Resolve Command IDs When Running

### Current Behavior
```python
def run_command(root, run_id, requirement_uids, tiers, command, ...):
    # Receives command string directly
    # Reads from validation_contract.commands or checks[].command
    
    # Later executes:
    # subprocess.run(command, ...)
```

### What Needs to Change

**1. Load registry from report:**
```python
def run_command(root, run_id, requirement_uids, tiers, command, ...):
    # When reading approval, also get command_registry
    anchor = ANCHOR.approved(root, run_id)  # Contains requirement rows
    command_registry = anchor.get("command_registry", {})  # NEW
```

**2. Resolve command_id to actual command:**
```python
def _resolve_command_for_execution(command_id_or_str, registry):
    """Resolve command_id to actual command string for execution."""
    if isinstance(command_id_or_str, str) and command_id_or_str.startswith("cmd-"):
        if command_id_or_str in registry:
            return registry[command_id_or_str].get("command", "")
        raise ValueError(f"command_id {command_id_or_str} not found in registry")
    return command_id_or_str  # Already a command string

# Then use:
actual_command = _resolve_command_for_execution(command, command_registry)
subprocess.run(actual_command, ...)
```

**3. When reading checks for validation:**
```python
# Current: looks for matching command string
matching_checks = [value for value in checks if str(value.get("command", "")) == command]

# New: handle both command and command_id
matching_checks = [
    value for value in checks 
    if (
        str(value.get("command", "")) == command or 
        str(value.get("command_id", "")) == command  # Handle ID references
    )
]
```

### Impact
- ✅ Execution layer doesn't care about registry (transparent resolution)
- ✅ Can mix old and new formats
- ✅ Audit trail shows actual command executed

---

## 3. `scripts/closure-finalizer.py` - Resolve IDs in Receipt Building

### Current Behavior
```python
def finalize(root, run_id, input_path=None, ...):
    closure = RECORDER.record(root, input_path)  # Builds receipts
    # Receipts have embedded commands in them
    
    # Report building reads from receipts
    report = REPORT.build(root, run_id)  # Displays commands
```

### What Needs to Change

**1. When building receipts from evidence stream:**
```python
# In closure-recorder.py (called by finalize)
def record(root, run_id, input_path=None):
    # Load command registry from approval
    approval = LOCK.active_start_report(root, run_id)
    navigator = approval.get("navigator", {})
    
    # Get registry from projection
    projection = LOCK.effective_plan_projection(approval)
    command_registry = projection.get("command_registry", {})
    
    # When collecting receipts:
    for receipt in receipts:
        if "command_id" in receipt:
            # Resolve for storage
            actual_command = command_registry.get(receipt["command_id"], {}).get("command")
            receipt["command"] = actual_command  # Store actual command in receipt
```

**2. When displaying in reports:**
```python
# In completion-report.py (displays commands)
def display_receipt(receipt, registry=None):
    # Try to resolve command_id to actual command
    command_id = receipt.get("command_id")
    if command_id and registry:
        actual_command = registry.get(command_id, {}).get("command")
        return actual_command or receipt.get("command", "unknown")
    return receipt.get("command", "unknown")
```

**3. Preserve registry through closure:**
```python
# Store registry with closure payload for traceability
closure_output = {
    "schema_version": "1",
    "type": "tailtrail-closure-finalizer",
    "command_registry": command_registry,  # NEW: for reference
    "receipts": receipts_with_resolved_commands,
    ...
}
```

### Impact
- ✅ Final reports show actual commands (resolved from registry)
- ✅ Receipts become smaller if not storing full commands
- ✅ Traceability preserved (registry included with receipts)

---

## Implementation Roadmap

### Phase 1: Core (Already Done ✅)
- ✅ planning_lock.py builds registry
- ✅ planning-audit.py validates registry

### Phase 2: Producer Updates (task-start.py)
**Scope:** ~100 lines
1. Import LOCK._command_id()
2. Update attach_focused_validation_contracts() to generate and store IDs
3. Update coalesce_focused_validation_rows() to use command_id
4. Return registry with validation_contract

**Effort:** Small  
**Risk:** Low (backward compat maintained)

### Phase 3: Consumer Updates (execution + closure)
**Scope:** ~150 lines
1. execution-evidence.py - Add resolution function, update matching logic
2. closure-finalizer.py / closure-recorder.py - Resolve IDs before storing receipts
3. completion-report.py - Resolve IDs when displaying

**Effort:** Medium  
**Risk:** Low (resolution is transparent)

### Phase 4: Testing & Validation
**Scope:** ~200 lines
1. Test fixtures using new registry format
2. End-to-end flow validation
3. Backward compat verification (old formats still work)

**Effort:** Medium  
**Risk:** Low (focused on coverage)

---

## Data Reduction Summary

### Current (Without Registry Leverage)
```
Multi-tier requirement: 3 tiers, 1 command
- validation_contract.commands: ["python3 -m unittest... (150 chars)"]
- validation_contract.checks: [{"command": "...", "tiers": [...]}] (150 chars)
- focused_validation: 3 rows, each has command field (150 * 3 = 450 chars)
Total: ~750 chars
```

### After Full Implementation
```
- command_registry: {"cmd-abc123": {"command": "...", "kind": "proof"}} (150 + 30 = 180 chars)
- validation_contract.commands: ["..."] (150 chars for compat)
- validation_contract.checks: [{"command_id": "cmd-abc123", ...}] (30 chars)
- focused_validation: 3 rows with command_id (30 * 3 = 90 chars)
Total: ~450 chars
Reduction: 40% (could be 76% if we remove backward compat)
```

---

## Backward Compatibility

All updates maintain full backward compat:
- ✅ Old plans without registry still work
- ✅ Mixed formats supported (some checks with command, some with command_id)
- ✅ Resolution falls back gracefully
- ✅ No breaking changes to external APIs

