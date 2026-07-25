# Coordinator Handoff: Lineage Fuzzer

## Relationship to the portfolio coordinator

This project chat owns Lineage Fuzzer's product, code, tests, demo, evidence, and submission. The
portfolio coordinator at `../COORDINATOR_PLAN.md` owns the shared DataHub and AWS deployment
contracts.

Before changing a port, public route, shared environment variable, DataHub namespace, deployment
topology, or global reset behavior, submit the proposed change to the coordinator. Do not edit the
live EC2 host from this project chat.

## Fixed project allocation

| Setting | Value |
|---|---|
| Project slug | `lineage-fuzzer` |
| Internal port | `8104` |
| DataHub domain | `Demo / Lineage Fuzzer` |
| Required DataHub tag | `project-lineage-fuzzer` |
| Entity prefix | `fuzzer.` |
| Fixture root | `demo/fixtures/lineage-fuzzer` |
| State root | `/var/lib/datahub-hackathon/lineage-fuzzer` |

## Project-chat obligations

- Build only Lineage Fuzzer business behavior.
- Keep campaigns, mutations, evidence, generated controls, and reset inside this allocation.
- Fail closed if a mutation or reset target falls outside the `fuzzer.` namespace.
- Preserve exact-path fixture allowlisting and manifest-bound approval.
- Implement `GET /api/health` and `GET /api/readiness`.
- Keep the project independently runnable without the other four submissions.
- Update the milestone handoff below whenever deployment-facing behavior changes.

## Milestone handoff

| Field | Current value |
|---|---|
| Status | `DataHub 1.6 assertion reread schema fix verified; coordinator promotion pending` |
| Milestone | Approved assertion reset/write/re-read/restore receipts against seeded live catalog |
| Verified commit/artifact | `6df411dd542a846431a1aaa0d5c4a9f0f32ea5f1` |
| Build command | `python -m pip install -e ".[dev]"` |
| Test command | `python -m pytest` |
| Seed command | `python -m lineage_fuzzer.pipeline_cli seed` |
| DataHub plan command | `lineage-fuzzer show-datahub-plans` (non-mutating; prints both approval SHA-256 values) |
| DataHub catalog seed | `lineage-fuzzer seed-datahub-fixture --approval-sha256 540ba6977764a3165af20bd2c2fad5870e8be74546478095086f27a0e778de38` |
| DataHub catalog reset | `lineage-fuzzer reset-datahub-fixture --approval-sha256 540ba6977764a3165af20bd2c2fad5870e8be74546478095086f27a0e778de38` |
| DataHub proof run | `lineage-fuzzer run-datahub-proof --approval-sha256 75a4d4f9bedb54bfb847ee1e4ea83b33450c2cf6664cf6fe8c8aa16f7d53094e` |
| DataHub proof reset | `lineage-fuzzer reset-datahub-proof --approval-sha256 75a4d4f9bedb54bfb847ee1e4ea83b33450c2cf6664cf6fe8c8aa16f7d53094e` |
| Reset command | `python -m lineage_fuzzer.pipeline_cli seed` (deterministic destructive reset is implemented as a fresh scoped reseed) |
| Baseline controls | `python -m lineage_fuzzer.pipeline_cli controls` |
| Snapshot command | `python -m lineage_fuzzer.pipeline_cli snapshot` |
| Restore command | `python -m lineage_fuzzer.pipeline_cli restore <manifest.json>` |
| Run command | `lineage-fuzzer serve --host 127.0.0.1 --port 8104` |
| Health endpoint | `GET /api/health` verified locally |
| Readiness endpoint | `GET /api/readiness`; returns 200 only when all local and authenticated DataHub checks pass |
| Disposable fixture | `demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb` |
| Snapshot state | `demo/fixtures/lineage-fuzzer/.snapshots/` |
| Long-running workers | None |
| DataHub read | Live catalog seed receipt verified and public readiness 200; corrected assertion reread pending promotion |
| DataHub writeback | Live catalog write verified; fixed proof assertion soft-delete executed, but successful proof receipts remain pending |
| Blockers | Assertion-schema candidate promotion, idempotent reset reread, then guarded live proof receipt run |
| Evidence produced | 61 passing tests; Ruff clean; exact DataHub 1.6 assertion query and already-soft-deleted reset idempotency regressions |

## Required environment variables

The application consumes `APP_ENV` and `APP_STATE_DIR` directly and retains the original
`LINEAGE_FUZZER_ENVIRONMENT` and `LINEAGE_FUZZER_STATE_DIR` names as compatibility aliases.
Secret values are injected only at runtime and must never be written to repository files.
The three `LINEAGE_FUZZER_ALLOWED_*` variables accept ordinary comma-separated values; JSON-array
serialization is neither required nor preferred.

```text
PROJECT_SLUG=lineage-fuzzer
APP_ENV=<environment>
APP_HOST=<bind-address>
APP_PORT=8104
APP_PUBLIC_URL=<coordinator-assigned-url>
APP_STATE_DIR=/var/lib/datahub-hackathon/lineage-fuzzer
DATAHUB_GMS_URL=http://127.0.0.1:8080
DATAHUB_MCP_URL=http://127.0.0.1:8000/mcp
DATAHUB_TOKEN=<secret-injected-at-runtime>
DATAHUB_DOMAIN=Demo / Lineage Fuzzer
DATAHUB_PROJECT_TAG=project-lineage-fuzzer
DATAHUB_URN_PREFIX=fuzzer.
LINEAGE_FUZZER_READINESS_DATASET_URN=urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.orders,DEV)
DEMO_FIXTURE_ROOT=demo/fixtures/lineage-fuzzer
```

## Implemented proof

- A fixed seed creates 30 customers, 120 orders, 14 daily-revenue rows, 30 customer-value rows,
  and one executive-dashboard summary.
- Canonical SHA-256 evidence covers all six managed source and downstream tables.
- Baseline controls deliberately cover the planned null-density fault but not the planned semantic
  scale or stale-partition faults.
- Snapshots are restricted to the coordinator-owned fixture root.
- Restore compares every managed-table checksum with the pre-campaign snapshot.
- An exception inside a campaign still restores the exact original checksums.
- Mutation authorization now also requires the exact `project-lineage-fuzzer` tag and validates
  platform, environment, entity identity, and the `fuzzer.` dataset-name prefix.

## Readiness contract and live-proof status

`GET /api/readiness` is non-mutating and checks:

1. Exact coordinator slug, domain, project tag, sandbox tag, URN prefix, fixture root, and database
   allowlist.
2. Existing readable/writable state directory without creating a probe file.
3. Existing DuckDB fixture, seed manifest, `sandbox_marker=true`, project slug, and six canonical
   table checksums using read-only connections.
4. Authenticated GMS GraphQL connectivity.
5. MCP availability of `get_entities`, `get_lineage`, and `list_schema_fields`.
6. The configured readiness entity's `fuzzer.` URN, domain, project tag, sandbox tag, and
   `sandbox=true` custom property.

Coordinator promotion of candidate `2166ef2d464caf41708d33672ec3273ad5f4e02f` established:

- The image built and deterministic seed succeeded.
- `/api/health` returned 200 and `/api/readiness` truthfully returned 503.
- Deployment temporarily JSON-serialized the three allowed-list variables.
- GMS failed because `post("")` appended `/` to `/api/graphql`; DataHub Core 1.6.0 returned 404.
- The same authenticated endpoint without the trailing slash returned 200.

Commit `08b0ac06a68c836fff781464c645192478cd99a2` addresses both deployment findings:

- GraphQL requests post to the normalized exact absolute endpoint.
- CSV list fields use pydantic-settings `NoDecode` before the existing splitter.
- URL and real environment-source regressions pass within the 45-test suite.

Coordinator promotion of exact candidate `497a5ec59c9c119372cf003fb7905b1535e51939`
established:

- Pre-seed `/api/health` returned 200 and `/api/readiness` truthfully returned 503.
- Both non-mutating approval SHA-256 values exactly matched this handoff.
- The coordinator completed an encrypted pre-proof snapshot and hashed 225 foreign
  Lifeboat/Forget aspect rows.
- The exact approved catalog seed failed closed on its first Domain request with HTTP 500.
- DataHub Core 1.6.0 reported `ModelConversionException: Failed to deserialize DataMap: null`
  while parsing `systemMetadata` in `/openapi/v3/entity/domain`.
- No catalog receipt or assertion live proof was claimed; foreign projects remained untouched and
  Fuzzer readiness remained 503.

Commit `75c7b1c3918e5f207ae8dafa8f7529c879d6b8b1` omits the optional
`systemMetadata` member instead of serializing JSON null. Exact serialized-payload regressions
cover Domain, Tag, dataset properties, global tags, domains, and status. The two approval digests
are unchanged because the immutable catalog and assertion plans did not change.

Coordinator promotion of exact candidate `52047ce3bf1ead25097632803088b75660414c78`
established:

- The exact approved catalog seed succeeded and its durable catalog receipt was verified.
- Public `/api/readiness` changed to 200; the Fuzzer catalog allocation remains seeded.
- The exact approved `reset-datahub-proof` soft-deleted only
  `urn:li:assertion:fuzzer.catalog-proof.orders-nonempty`.
- Reset then failed closed during its GraphQL reread because `AssertionInfo.customType` and
  `CustomAssertionInfo.fieldPath` are undefined in DataHub Core 1.6.0.
- Guarded live introspection reported `AssertionInfo` fields
  `[type,datasetAssertion,description,externalUrl,freshnessAssertion,volumeAssertion,sqlAssertion,fieldAssertion,schemaAssertion,customAssertion,source,lastUpdated]`
  and `CustomAssertionInfo` fields `[type,entityUrn,field,logic]`.
- No successful assertion proof receipts were claimed. The foreign baseline remained preserved,
  and the fixed Fuzzer assertion is currently soft-deleted.

Commit `6df411dd542a846431a1aaa0d5c4a9f0f32ea5f1` selects only the required live-supported
fields: `AssertionInfo.type`, `description`, and `customAssertion`, with
`CustomAssertionInfo.type`, `entityUrn`, and `logic`. It omits unsupported `customType` and
`fieldPath` and does not request the unnecessary `field`. The parser reads custom type and logic
from `customAssertion`. An exact query regression locks this selection, and reset tests prove two
consecutive calls succeed when the fixed assertion is already soft-deleted.

Remaining live proof is **blocked, not simulated**:

- The allocated `fuzzer.` catalog entity is seeded, its catalog receipt is verified, and readiness is 200.
- The fixed proof assertion is currently soft-deleted after the scoped partial reset.
- No successful assertion before/write/after/restore receipt set exists yet.
- The credential remains coordinator-managed; this project chat did not request or access it.

### Guarded coordinator runbook

Run these commands from the deployed application container/shell, where the coordinator already
injects `DATAHUB_TOKEN`, `DATAHUB_GMS_URL`, `DATAHUB_MCP_URL`, `APP_STATE_DIR`, and the frozen
allocation variables. Do not echo or pass the token on the command line.

```powershell
lineage-fuzzer show-datahub-plans
lineage-fuzzer seed-datahub-fixture --approval-sha256 540ba6977764a3165af20bd2c2fad5870e8be74546478095086f27a0e778de38
lineage-fuzzer reset-datahub-fixture --approval-sha256 540ba6977764a3165af20bd2c2fad5870e8be74546478095086f27a0e778de38
lineage-fuzzer reset-datahub-proof --approval-sha256 75a4d4f9bedb54bfb847ee1e4ea83b33450c2cf6664cf6fe8c8aa16f7d53094e
lineage-fuzzer run-datahub-proof --approval-sha256 75a4d4f9bedb54bfb847ee1e4ea83b33450c2cf6664cf6fe8c8aa16f7d53094e
```

The catalog seed and reset are identical deterministic replays. They are restricted to:

- `urn:li:domain:lineage-fuzzer`
- `urn:li:tag:project-lineage-fuzzer`
- `urn:li:tag:lineage-fuzzer-sandbox`
- `urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.orders,DEV)`

The assertion command is restricted to
`urn:li:assertion:fuzzer.catalog-proof.orders-nonempty`. Before any assertion mutation it re-reads
the allocated dataset over OpenAPI and requires the exact `duckdb` platform, `DEV` environment,
`fuzzer.` name, domain URN, both tag URNs, active status, and `sandbox=true`. It then:

1. Captures the dataset's attached assertions (`before.json`).
2. Upserts the fixed custom assertion, activates it, and reports the fixed successful result
   (`write.json`).
3. Re-reads and verifies the assertion, entity, result, properties, and timestamp (`after.json`).
4. Soft-deletes only the fixed assertion in `finally`, re-reads its absence, and records
   `restore.json`.

Receipts are atomic, whitelisted, and contain no request headers, raw token, or unbounded server
payload. Expected durable paths are:

```text
/var/lib/datahub-hackathon/lineage-fuzzer/datahub-receipts/catalog-540ba6977764a316/catalog.json
/var/lib/datahub-hackathon/lineage-fuzzer/datahub-receipts/assertion-75a4d4f9bedb54bf/before.json
/var/lib/datahub-hackathon/lineage-fuzzer/datahub-receipts/assertion-75a4d4f9bedb54bf/write.json
/var/lib/datahub-hackathon/lineage-fuzzer/datahub-receipts/assertion-75a4d4f9bedb54bf/after.json
/var/lib/datahub-hackathon/lineage-fuzzer/datahub-receipts/assertion-75a4d4f9bedb54bf/restore.json
```

After the catalog seed, verify public `/api/readiness` is 200. A successful proof command must
return `status=proved_and_restored` and all four paths. Preserve copies as coordinator evidence;
do not add them to Git.

## Resource and deployment notes

- DuckDB and snapshots are disposable and ignored by source control.
- DuckDB is now declared directly in `pyproject.toml`; `requirements-fixture.txt` remains only as
  a backward-compatible setup aid.
- DataHub receipts add five small JSON files beneath the existing persistent state allocation.
- Catalog/proof commands are bounded foreground jobs; they add no workers or recurring load.
- There are no workers, migrations, new ports, public services, or infrastructure changes.
- Readiness performs bounded read-only DuckDB, GraphQL, and MCP queries per request.
- A local Windows smoke run reached `/api/health` in 7.265 seconds and reported a 3.9 MiB working
  set and 0.016 CPU seconds; treat this as indicative only and remeasure on the deployment host.
- The application remains one process on internal port 8104 with a 512 MiB deployment ceiling.
- Rollback target is the currently deployed seeded/readiness-200 commit
  `52047ce3bf1ead25097632803088b75660414c78`.

## Next project-owned milestone

1. Coordinator promotes the assertion-schema candidate without changing the seeded catalog.
2. Confirm public readiness remains 200 and both approval digests still match this handoff.
3. Rerun the approved reset against the already-soft-deleted fixed assertion and verify its
   restore receipt.
4. Run the single approved proof command; archive `before`, `write`, `after`, and `restore`
   receipts outside Git.
5. Confirm the proof assertion remains absent after restoration and report the exact live evidence
   paths and outcomes back to this project chat.
6. Only after that live integration gate passes, continue the three semantic fault adapters and
   campaign execution milestone.

## Required deployment handoff format

When requesting deployment, replace all placeholder values and include:

1. Exact commit or immutable artifact identifier.
2. Required environment variables without secret values.
3. Build, test, seed, reset, run, and rollback commands.
4. Health/readiness results.
5. DataHub entities, reads, writes, and receipts.
6. Filesystem volumes and disposable paths.
7. Expected CPU, memory, startup time, and job duration.
8. Known limitations and demo concurrency behavior.
