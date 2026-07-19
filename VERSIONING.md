# Versioning

TailTrail uses semantic versioning for public releases.

## Version Source Of Truth

Before a public tag, these must agree:

- `.codex-plugin/plugin.json` -> `version`
- `CHANGELOG.md`
- Git tag in the form `vMAJOR.MINOR.PATCH`

## Version Rules

- Patch: documentation updates, small script fixes, validation updates, or non-breaking hardening.
- Minor: new compatible commands, docs, templates, report sections, or parser support.
- Major: breaking command behavior, install layout, file contract, output schema, or default privacy behavior.

## Release Tag Rules

- Use tags like `v0.6.0`.
- Do not move a published tag.
- Release notes should include:
  - added
  - changed
  - fixed
  - security/privacy
  - migration notes
  - validation commands
  - known limitations

## Public Claim Rule

Do not describe exact token savings, quality improvement, risk reduction, or productivity impact unless the release notes point to measured local evidence. Estimates must be labeled as estimates.
