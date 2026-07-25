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
| Status | `deployment compatibility fix verified; coordinator promotion pending` |
| Milestone | Exact DataHub GraphQL endpoint and native CSV environment parsing |
| Verified commit/artifact | `08b0ac06a68c836fff781464c645192478cd99a2` |
| Build command | `python -m pip install -e ".[dev]"` |
| Test command | `python -m pytest` |
| Seed command | `python -m lineage_fuzzer.pipeline_cli seed` |
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
| DataHub read | Exact GMS endpoint fix verified locally; authenticated live recheck and catalog receipt pending coordinator run |
| DataHub writeback | GraphQL client implemented; no live write/re-read/restore receipt claimed |
| Blockers | Coordinator promotion, absent catalog allocation, and guarded shared-host read/write/re-read/restore receipt run |
| Evidence produced | 45 passing tests; Ruff clean; exact URL and real CSV environment regressions; prior live health 200/readiness 503 finding |

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

## Resource and deployment notes

- DuckDB and snapshots are disposable and ignored by source control.
- DuckDB is now declared directly in `pyproject.toml`; `requirements-fixture.txt` remains only as
  a backward-compatible setup aid.
- There are no workers, migrations, new ports, public services, or infrastructure changes.
- Readiness performs bounded read-only DuckDB, GraphQL, and MCP queries per request.
- A local Windows smoke run reached `/api/health` in 7.265 seconds and reported a 3.9 MiB working
  set and 0.016 CPU seconds; treat this as indicative only and remeasure on the deployment host.
- The application remains one process on internal port 8104 with a 512 MiB deployment ceiling.
- Rollback target is the previously deployed commit
  `2166ef2d464caf41708d33672ec3273ad5f4e02f`.

## Next project-owned milestone

1. Coordinator promotes the new clean candidate without the JSON-list workaround.
2. Coordinator verifies authenticated GMS and MCP readiness on the shared host.
3. Seed the missing namespaced catalog entity with domain, project tag, sandbox tag, and marker.
4. Preserve the sanitized read receipt, then perform the specifically approved sandbox-only
   write/re-read/restore sequence and preserve all four receipts.
5. Implement the three seeded semantic fault adapters and campaign execution after the live
   integration gate is verified.

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
