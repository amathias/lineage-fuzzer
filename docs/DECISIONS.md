# Architectural Decisions

## ADR-001: Deterministic core with optional language-model assistance

- **Status:** Accepted
- **Date:** 2026-07-24

Campaign manifests, safety decisions, fault injection, detection attribution, scoring, and
restoration are deterministic application code. A language model may draft explanations or
candidate controls, but generated code must pass deterministic validation before execution.
A metadata-grounded template generator remains available when no model is configured.

This keeps campaigns replayable and prevents model output from bypassing safety controls.

## ADR-002: DuckDB is the only MVP fault target

- **Status:** Accepted
- **Date:** 2026-07-24

The MVP operates only on one explicitly allowlisted DuckDB fixture inside the repository. Fault
adapters do not accept arbitrary connection strings. DataHub represents the fixture's catalog
context, but the physical mutation target must independently match the local allowlist.

DuckDB keeps the demo fast and deterministic while making the safety boundary easy to inspect.

## ADR-003: DataHub MCP for context, supported API for assertion writeback

- **Status:** Accepted
- **Date:** 2026-07-24

The app uses the self-hosted DataHub MCP endpoint for entity, lineage, and schema context. It uses
DataHub's supported custom-assertion GraphQL operations to retrieve existing controls, register
generated controls, and report campaign results.

The application includes a live probe that fails if the required MCP tools are unavailable. Tests
may mock transport behavior, but demo evidence must come from a running open-source DataHub
instance.

## ADR-004: Approval is bound to immutable campaign content

- **Status:** Accepted
- **Date:** 2026-07-24

Approval records contain the SHA-256 digest of a canonical campaign manifest. Any change to seed,
targets, graph snapshot, or fault parameters invalidates approval. Both the campaign controller and
the fault adapter must invoke the safety gate.

## ADR-005: Restore between faults

- **Status:** Accepted
- **Date:** 2026-07-24

Each fault runs independently from the same clean snapshot. The fixture is restored and verified
between faults and again in a final cleanup path. This makes the fault-by-control matrix attributable
and prevents one mutation from influencing another fault's observation.

## ADR-006: Readiness is authenticated, non-mutating, and allocation-aware

- **Status:** Accepted
- **Date:** 2026-07-25

Process liveness remains separate from readiness. Readiness never creates probe files or writes to
DataHub. It verifies the pre-existing state directory, reads the DuckDB fixture and its sandbox
manifest read-only, probes authenticated GraphQL and MCP capabilities, and validates one allocated
catalog entity.

The endpoint returns not-ready unless the runtime slug, fixture root, exact database allowlist,
DataHub domain, project tag, sandbox tag, platform, environment, and `fuzzer.` URN prefix match the
coordinator contract. Missing credentials and missing catalog metadata are failures, not degraded
success.

The same allocation rules are enforced again by mutation authorization. This deliberately
duplicates critical checks across readiness and the mutation boundary so a healthy deployment
cannot make an out-of-scope target writable.

## ADR-007: DataHub fixture and proof writes are fixed, approved, and reversible

- **Status:** Accepted
- **Date:** 2026-07-25

DataHub catalog fixture creation uses the supported DataHub 1.6 OpenAPI v3 entity-aspect
interface. The writer is restricted to one fixed domain, two fixed tags, and
`urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.orders,DEV)`. Its canonical aspects
contain the assigned domain, project tag, sandbox tag, `sandbox=true`, and active status.

The live writeback proof uses DataHub's supported custom-assertion GraphQL operations and one
fixed assertion URN, `urn:li:assertion:fuzzer.catalog-proof.orders-nonempty`. Before mutation it
re-reads and validates the dataset's platform, environment, namespace, domain, tags, marker, and
active status. The proof upserts the assertion, makes it active, reports a deterministic result,
re-reads the result, and soft-deletes only that assertion in a `finally` restoration path.

Both catalog and assertion plans are immutable and require their exact canonical SHA-256 through
the CLI. Approval mismatch, foreign URNs, foreign runtime allocation, missing metadata, and
missing credentials fail before a write. The four proof phases are persisted atomically as
whitelisted, token-free JSON receipts under `APP_STATE_DIR/datahub-receipts/`; raw headers,
credentials, and server payloads are never written to evidence.
