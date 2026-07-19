# TailTrail Demo Policy

This policy is active for the Build Week demo project.

## Local Commands

Focused validation:

```bash
python3 -m unittest discover -s tests
```

## Dependency Policy

Do not add dependencies for this demo. Use Python standard library only.

## Validation

For changes to claim validation, run:

```bash
python3 -m unittest discover -s tests
```

## Code Intelligence Policy

Provider-backed Semantic V3 ingestion is disabled by default.

provider_backed_semantic_ingestion: disabled
require_provider_ingestion_approval: true
allowed_provider_outputs:
- tailtrail-meta/providers/

Semantic V3 may ingest approved local JSON provider outputs only when the command includes `--approved`.

