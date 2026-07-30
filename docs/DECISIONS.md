# Architectural Decisions

## ADR-001: Deterministic core with optional language-model assistance

- **Status:** Accepted
- **Date:** 2026-07-24

Campaign manifests, safety decisions, fault injection, detection attribution, scoring, and
restoration are deterministic application code. The MVP emits two predesigned controls and does
not use a language model. Future model-drafted controls would still have to pass the same
deterministic validation before execution.

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
one separately approved proof assertion, report a fixed result, reread it, and remove it.

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

## ADR-008: Semantic campaign evidence is checksum-based and fault-isolated

- **Status:** Accepted
- **Date:** 2026-07-25

The vertical slice implements exactly three materially different adapters: numeric scale,
partition staleness, and null-density surge. Seed plus fault ID deterministically selects primary
keys, and evidence records selected keys plus before/after value hashes rather than raw row data.

Each fault starts from the same fixture snapshot. The app materializes all managed downstream
tables, compares their canonical checksums with the clean state, and requires the observed changed
URNs to equal the fault-specific predicted URNs. A mismatch fails the campaign before evidence can
claim success. Restoration is checksum-verified after every fault and again in an unconditional
final cleanup path.

This makes detection attribution and blast-radius comparison reproducible while preventing
cross-fault contamination.

## ADR-009: Emitted controls use a strict read-only SQL policy

- **Status:** Accepted
- **Date:** 2026-07-25

The MVP builder deterministically emits one DuckDB SQL artifact containing two predesigned controls
for the measured amount-range and partition-freshness gaps. Before execution, the validator
requires a single read-only statement, only the approved `raw.orders` relation, and the expected
control IDs. Mutation, attachment, file access, installation, pragma, and multi-statement forms are
denied.

The artifact must execute cleanly before the improved campaign. It then runs after each fault
alongside the typed application controls, and the campaign is successful only when coverage moves
from the designed 1/3 baseline to 3/3.

Offline development uses an explicit `local-fixture-topology` context. A separate authenticated
capture command reads entity, schema, downstream lineage, and assertions through DataHub MCP and
GraphQL, persists only a typed snapshot marked `datahub-mcp-live`, and binds its digest into a new
manifest approval. The API refuses to load a context file without that live marker and lineage.
This prevents offline fixture topology from being presented as newly captured live metadata.

## ADR-010: One exact catalog contract drives seed, capture, controls, and reset

- **Status:** Accepted
- **Date:** 2026-07-25

The live campaign allocation is six fixed `fuzzer.*` DuckDB/DEV dataset URNs, five fixed lineage
edges, six complete schemas, one owner, one domain, two tags, `sandbox=true`, active status, and
three fixed custom assertion URNs. One typed contract generates the OpenAPI aspect writes,
GraphQL assertion writes, immutable seed plan, reset allowlist, live-capture validation, local
topology, UI graph, and baseline control mapping.

Seed and reset have different approval SHA-256 values. Seed idempotently restores every dataset
and baseline assertion to active state. Reset invalidates the current live-context snapshot and
receipt before its first write, soft-deletes only the six dataset URNs and three baseline
assertions, retains Domain and Tags, and records started/failed/completed receipts. The separate
live-proof assertion remains outside that reset contract.

Live capture reads all six entities in one MCP call, reads each schema, reads direct one-hop
lineage from each dataset, and queries assertions for every dataset. It fails on a missing field,
edge, owner, domain, tag, marker, active status, assertion, or expected URN. It preserves safe raw
response digests and MCP tool schemas in the typed provenance. Executable baseline controls in
live mode are derived only from the exact captured assertion URN/type/entity/logic mapping.

This eliminates the earlier failure mode where changing a local snapshot's source label could
make it appear live.

## ADR-011: Public campaigns require current bound context and immutable run evidence

- **Status:** Accepted
- **Date:** 2026-07-25

In `APP_ENV=hackathon`, readiness and campaign construction require
`LINEAGE_FUZZER_CANDIDATE_SHA`, a complete `datahub-mcp-live` snapshot, and its adjacent receipt.
The receipt binds the context digest to the exact candidate commit, verified catalog seed state,
catalog plan digest, and local fixture seed/checksums. Any reset, reseed, candidate change, catalog
state change, or fixture drift invalidates the context. The app does not silently substitute local
topology, and the judge page keeps its run control disabled until the live gate and the explicit
injection flag both pass.

Campaign JSON evidence and a copy of the emitted SQL artifact are stored under a directory
named with both the manifest and context SHA-256 values. Replays may reuse only byte-identical
files; a differing byte raises an error rather than overwriting evidence. Approval time is bound
to the deterministic manifest time so a true replay remains byte-identical.

The release verifier operates on `git archive`, builds and reinstalls the wheel in a fresh virtual
environment, imports the pinned DataHub clients, runs tests/Ruff/secret scan, seeds and checks the
fixture, and exercises the judge UI. This verifies distributable source rather than accidental
working-tree state.
