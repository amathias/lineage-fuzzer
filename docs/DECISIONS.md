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

