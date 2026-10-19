# Command Registry Refactoring Plan

## Objective
Replace duplicate command references across `checks`, `focused_validation`, and execution layers with a single command registry that all consumers reference by ID.

## Current Problem
```
validation_contract: {
  commands: ["python3 -m unittest..."],
  checks: [{ command: "python3 -m unittest...", tiers: [...] }]
}
focused_validation: [
  { tier: "unit", command: "python3 -m unittest..." },
  { tier: "contract", command: "python3 -m unittest..." },
  { tier: "behaviour", command: "python3 -m unittest..." }
]
```

Same command string duplicated 5+ times.

## Proposed Schema

### In Start Report / Anchor / Approval
```json
{
  "command_registry": {
    "cmd-1a2b3c": {
      "command": "python3 -m unittest tests.test_planning_audit",
      "kind": "proof",
      "label": "unit test suite"
    }
  },
  "validation_contract": {
    "tiers": ["unit", "contract", "behaviour"],
    "commands": ["python3 -m unittest tests.test_planning_audit"],
    "checks": [{
      "command_id": "cmd-1a2b3c",
      "tiers": ["unit", "contract", "behaviour"]
    }]
  },
  "focused_validation": [
    { "requirement_id": "req-abc", "tier": "unit", "command_id": "cmd-1a2b3c" },
    { "requirement_id": "req-abc", "tier": "contract", "command_id": "cmd-1a2b3c" },
    { "requirement_id": "req-abc", "tier": "behaviour", "command_id": "cmd-1a2b3c" }
  ]
}
```

### Command ID Generation
```python
def command_id(command: str) -> str:
    # Short hash of command for readability + uniqueness
    return "cmd-" + hashlib.sha256(command.encode()).hexdigest()[:6]
```

## Files Impacted & Changes Required

### 1. **scripts/planning_lock.py** (Core - HIGH IMPACT)
- `effective_plan_projection()` - Build registry, emit command_id in checks
- `_aidlc_plan_fingerprints()` - Include registry in fingerprint
- Update all places that emit `checks` with `command` field → use `command_id`

### 2. **scripts/planning-audit.py** (Validation - HIGH IMPACT)
- `_audit_convergence()` - Pass registry and resolve command_id in checks
- `_focused_covers()` - Match by command_id instead of command string
- `_normalize_check()` - Work with command_id, resolve to validate

### 3. **scripts/execution-evidence.py** (Execution - MEDIUM IMPACT)
- `run()` - Resolve command_id to actual command before execution
- `amend_proof()` - Handle command_id in amendments

### 4. **scripts/task-start.py** (Focused validation - HIGH IMPACT)
- `coalesce_focused_validation_rows()` - Emit command_id instead of command
- `focused_validation_plan()` - Use registry when available

### 5. **scripts/closure-finalizer.py** (Closure - MEDIUM IMPACT)
- Resolve command_id before emitting in closure reports

### 6. **scripts/closure-recorder.py** (Recording - MEDIUM IMPACT)
- Record command_id in receipts

### 7. **scripts/completion-report.py** (Reporting - MEDIUM IMPACT)
- Resolve command_id when displaying command in report

### 8. **Tests** - Update fixtures to use new schema (HIGH IMPACT)
- 30+ test files with hardcoded `commands` and `checks` arrays

## Implementation Strategy

### Phase 1: Core (planning_lock + audit)
- Add command_id field support to checks
- Build registry in planning_lock
- Update audit to handle both old (embedded) and new (referenced) formats for compatibility

### Phase 2: Execution Path (execution-evidence + closure)
- Implement command resolution logic
- Update execution-evidence and closure layers

### Phase 3: Presentation (reports)
- Update all report/display code to resolve command_id

### Phase 4: Tests
- Migrate test fixtures to new schema

### Phase 5: Cleanup (optional future)
- Remove support for old embedded format
- Simplify all readers

## Backward Compatibility Strategy

**Keep supporting old format temporarily:**
```python
def resolve_command(checks, registry, command_id_or_string):
    if command_id_or_string.startswith("cmd-"):
        return registry.get(command_id_or_string, {}).get("command")
    return command_id_or_string  # Fallback to embedded command
```

This allows old plans to still work while new plans use registry.

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|-----------|
| Registry building in planning_lock | Medium | Add defensive checks, test extensively |
| Audit resolution logic | Medium | Support both formats initially |
| Execution path changes | Low | Resolve just before execution |
| Test updates | Low | Systematic, file-by-file |

## Success Criteria
- ✅ Single command embedded in checks (no duplication in focused_validation)
- ✅ Audit passes with registry structure
- ✅ Execution-evidence resolves and runs command correctly
- ✅ All existing tests pass with new schema
- ✅ No duplicate command strings in output

## Estimated Scope
- **planning_lock.py**: 150-200 lines
- **planning-audit.py**: 100-150 lines
- **execution-evidence.py**: 50-100 lines
- **task-start.py**: 50-100 lines
- **closure/report files**: 100-150 lines total
- **Tests**: 300-400 lines
- **Total**: ~750-1100 lines of code changes + test updates

