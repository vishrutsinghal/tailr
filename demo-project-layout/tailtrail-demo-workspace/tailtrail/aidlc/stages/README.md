# AIDLC Stage Playbooks

These playbooks harden TailTrail AIDLC without making `AIDLC.md` huge. Load only the playbook for the active phase or stage.

## Stage Order

Use this order as a default, then skip conditional stages that do not reduce risk or ambiguity:

1. `workspace-detection.md`
2. `reverse-engineering.md` for brownfield or unclear systems
3. `requirements.md`
4. `workflow-planning.md`
5. `design.md` for new boundaries, NFRs, data changes, or multi-unit work
6. `implementation.md`
7. `build-test.md`
8. `handoff.md`
9. `operations.md` when deployment or support is in scope

## Loading Rule

Read `aidlc-docs/aidlc-state.md` first when resuming. Then load only the active stage playbook and exact source files needed for that stage.
