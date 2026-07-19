# Code Graph Mapper

Code Graph Mapper creates a compact, freshness-checked metadata cache at `.tailtrail/code-graph-cache.json`.

Use it for heavy Sonar, vulnerability, dependency, QA, review, handoff, or broad implementation work where repeated source discovery would waste tokens.

## Commands

```bash
python3 scripts/tailtrail.py graph map --changed src/service/Foo.java
python3 scripts/tailtrail.py graph status --changed src/service/Foo.java
python3 scripts/tailtrail.py graph refresh --changed src/service/Foo.java
```

The direct script is:

```bash
python3 scripts/code-graph-mapper.py map --root . --changed src/service/Foo.java
python3 scripts/code-graph-mapper.py status --root . --changed src/service/Foo.java
python3 scripts/code-graph-mapper.py refresh --root . --changed src/service/Foo.java
```

## What It Stores

- file hashes for target files, likely tests, likely callers, watched manifests, and optional scanner evidence
- language profiles for Python, Java, .NET/C#, SQL, and Terraform
- metadata-only symbols, references, call-chain hints, type-hierarchy hints, endpoint hints, DB table hints, config usage hints, and workspace overlays
- suggested read order
- confidence and freshness reasons

## What It Does Not Store

- source snippets
- secrets
- raw prompts
- full assistant responses
- raw scanner logs
- vector embeddings
- graph database state

## Advanced Enterprise Metadata

The mapper now adds a first advanced metadata layer while staying local and dependency-free:

- **Monorepo partitions**: groups files by nearby module/service markers such as build files, project files, and top-level folders so agents can avoid unrelated modules.
- **Service dependency hints**: detects obvious HTTP URLs, service/base-url config keys, endpoint/host config values, and .NET project references.
- **Endpoint-to-service-to-table flows**: connects detected endpoint hints to same-file service calls, external service hints, DB table hints, and config keys.
- **Owner/test/release mapping**: connects changed files to CODEOWNERS entries, likely tests, and release/deployment path hints such as workflow, pipeline, deployment, Helm, Kubernetes, and Terraform files.

These fields help the agent choose what to read first. They are not a complete semantic graph, not validation evidence, and not proof that a release path or owner is exhaustive.

## Navigator Rules

- Skip for tiny typo, comment, docs-only, or conceptual tasks.
- Check cache status for heavy Sonar, vulnerability, dependency, QA, review, release, or handoff prompts.
- If fresh, use the suggested read order before broad source reading.
- Use partitions to stay inside the relevant service/module before widening scope.
- Use owner/test/release mapping to prepare focused validation and handoff notes.
- If stale, refresh before relying on the graph.
- If missing, recommend `graph map` when changed files or scanner-reported files are known.
- Never treat graph freshness as proof that Sonar, vulnerability, CI, or tests are fixed.
- Always read exact current source files before editing.

## Language Coverage

- Python: modules, imports, classes, functions, route decorators, pytest proximity, and Python `ast` symbols when parsable.
- Java: packages, classes, interfaces, enums, methods, Spring/JAX-RS-style route annotations, JPA table annotations, Maven/Gradle manifests.
- .NET/C#: namespaces, classes, interfaces, records, methods, ASP.NET route attributes, EF `DbSet` hints, `.sln`, and `.csproj` files.
- SQL: tables, routines, migrations, and query references.
- Terraform: resources, data sources, modules, variables, outputs, providers, and references.

## AST Lite, AST V1, And Semantic V2 Maps

Code Graph Mapper creates a reusable cache. AST maps are a read-only, on-demand companion for selected files when the agent needs more structure before editing.

```bash
python3 scripts/tailtrail.py graph ast --changed src/service/Foo.java --depth lite
python3 scripts/tailtrail.py graph ast --changed src/service/Foo.java --depth v1
python3 scripts/tailtrail.py graph ast --changed src/service/Foo.java --depth v1 --format json
python3 scripts/tailtrail.py graph ast --changed src/service/Foo.java --depth v2
python3 scripts/tailtrail.py graph ast --changed src/service/Foo.java --depth v2 --format json
```

Use AST Lite when a file-level graph is too broad and you only need selected-file symbols. Use AST V1 when you also need reference hints, call hints, hierarchy hints, endpoints, DB/config hints, likely tests, and changed-symbol impact. Use Semantic V2 when you need richer local orientation: symbol index, import/module edges, reference edges, endpoint-to-handler links, data-flow-lite hints, test coverage hints, and readiness checks for optional language-server, SCIP, Roslyn, or tree-sitter providers.

AST maps:

- do not write `.tailtrail/code-graph-cache.json`
- do not store source snippets
- do not run tests, scanners, builds, network calls, model calls, or background services
- do not start language servers, run Roslyn, ingest SCIP, call tree-sitter, install parser-package dependencies, use vector DB, graph DB, or MCP adapters
- are metadata only; exact current source and validation evidence still win

## Scanner Graph Overlay

Scanner Graph Overlay is the bridge between local scanner evidence and graph impact.

```bash
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed src/service/Foo.java
python3 scripts/tailtrail.py graph overlay --vulnerability audit.log --changed package.json
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --vulnerability audit.log --format json
```

Use it after CI/Sonar Intelligence or Security And Vulnerability Intelligence has identified scanner evidence, but before remediation. It reads local report files and local metadata, then groups findings by impacted file. It adds scopes, likely tests, related files, nearby manifests, AST V1 hints, suggested read order, and follow-up commands.

The overlay does not write the graph cache. Use `graph refresh --changed ...` when the reusable cache itself should be updated. The overlay also does not run Sonar, vulnerability scanners, builds, tests, network calls, or fixes.

For structured vulnerability reports, the overlay supports SARIF, Trivy JSON, and Grype JSON. It normalizes report paths against the target project root, redacts common secret-like evidence text, caps scanner report reads with `--max-bytes`, filters generic related-file tokens, and treats Trivy package-manifest findings as dependency vulnerabilities.

Deferred deeper mapper work:

- full semantic AST engine
- language-server, SCIP, or Roslyn provider
- tree-sitter or other parser-package provider
- cross-repo service graph across multiple checked-out repos or approved provider indexes
- graph DB or vector DB
- background indexing service
- provider-specific scanner report parsers for Sonar JSON, dependency-check XML, CycloneDX, SPDX, and additional schemas; SARIF, Trivy JSON, and Grype JSON are already supported for vulnerability summary and scanner overlay inputs
- deeper data-flow beyond local endpoint-to-service-to-table hints

## Safe Use

Use the mapper as an index of where to look first. Do not use it as a correctness proof, a replacement for source inspection, or evidence that validation passed.
