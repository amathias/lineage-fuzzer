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
| Status | `guarded catalog and live-proof workflow verified locally; coordinator promotion pending` |
| Milestone | Exact catalog fixture seed plus approved assertion write/re-read/restore receipts |
| Verified commit/artifact | `c8ca59a9438e703a81b7898b5690539340745731` |
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
| DataHub read | Guarded OpenAPI catalog verification plus existing GraphQL/MCP reads implemented; live receipts pending coordinator run |
| DataHub writeback | Fixed OpenAPI aspect seed/reset and fixed custom-assertion write/result/re-read/soft-delete restore implemented; no live receipt claimed |
| Blockers | Coordinator promotion, catalog seed on the shared host, readiness 200 confirmation, and guarded live proof receipt run |
| Evidence produced | 58 passing tests; Ruff clean; approval, foreign-namespace, missing-marker, sanitized-receipt, re-read, and restoration regressions |

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

Remaining live proof is **blocked, not simulated**:

- The allocated `fuzzer.` catalog entity and its required metadata are still absent.
- No live mutation, write, re-read, or restore receipt has been attempted.
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
- Rollback target is the previously deployed commit
  `2166ef2d464caf41708d33672ec3273ad5f4e02f`.

## Next project-owned milestone

1. Coordinator promotes the clean handoff candidate without changing the frozen allocation.
2. Run `show-datahub-plans` and confirm both printed digests match this handoff.
3. Run the approved catalog seed and confirm public `/api/readiness` changes from 503 to 200.
4. Run the approved proof reset, then the single proof command; archive `before`, `write`, `after`,
   and `restore` receipts outside Git.
5. Confirm the proof assertion is absent after restoration and report the exact live evidence
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
