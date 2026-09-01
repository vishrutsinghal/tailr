# Installation Experience And Release Qualification Design

The implementation composes the existing package-owned installer rather than
adding a second lifecycle.

1. `tailtrail setup` resolves an explicit host or a single unambiguous local
   candidate, selects install versus update from ownership manifests, then
   reuses verify/doctor and the adapter contract.
2. `tailtrail upgrade` accepts only a local TailTrail wheel plus exact digest.
   It safely extracts and verifies package-owned integrity, preflights all
   selected project plans, requires `--approved`, performs an offline/no-deps
   transactional project updates, then performs the offline/no-deps pip
   upgrade. Project transactions roll back in reverse order if pip fails.
3. `InstallResult` retains full in-process detail. Text and new setup JSON
   summarize counts and plan identity by default. Existing 0.6 lifecycle JSON
   remains full; `--compact` opts into summaries and `--verbose` expands setup.
4. Extended runtime files live under
   `.tailtrail/install/payload/common/<version>/`; each host has a small Python
   launcher that reads its ownership manifest and executes that immutable
   version. Per-host manifests may reference the same common paths. The engine
   preserves a common path whenever another installed host references it.
5. `release-channel-v1.json` identifies only the trusted repository/channel.
   Tagged CI performs the existing exact platform gate and identity
   attestation, checks tag/version agreement, then publishes the same canonical
   bytes with checksums, SBOM, and evidence.
6. `tailtrail qualify` prepares all host bundles or reports four independent
   gates. It invokes GitHub attestation verification for the canonical wheel,
   hosted platform aggregate, and post-publication observation receipt. Only
   all-green genuine evidence produces `supported: true`.
7. Adapter v3 adds closed reload objects because reload behavior does not
   change runtime receipt semantics; old v3 receipts remain valid for their
   original instruction digest and naturally become stale when that digest
   changes.

Failure posture: ambiguous setup, digest mismatch, corrupt/unsafe wheel,
project conflict, missing approval, package-manager failure, missing receipts,
stale runtime evidence, incomplete platform coverage, and absent publication
proof all fail without a success/support claim.
