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
| Status | `code verified; live DataHub proof pending coordinator run` |
| Milestone | Truthful readiness and fail-closed allocation enforcement |
| Verified commit/artifact | `d4dd9f2084a4c9a773c1ec35e36565ce881ea5a0` |
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
| DataHub read | MCP client and checks implemented; live receipt pending coordinator promotion and guarded shared-host run |
| DataHub writeback | GraphQL client implemented; no live write/re-read/restore receipt claimed |
| Blockers | Coordinator promotion and guarded shared-host read/write/re-read/restore receipt run |
| Evidence produced | 42 passing tests; Ruff clean; local readiness 503 proves missing state/token honestly; fixture checksum and exception-safe restoration evidence |

## Required environment variables

The application consumes `APP_ENV` and `APP_STATE_DIR` directly and retains the original
`LINEAGE_FUZZER_ENVIRONMENT` and `LINEAGE_FUZZER_STATE_DIR` names as compatibility aliases.
Secret values are injected only at runtime and must never be written to repository files.

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

Local verification without runtime state or a service credential returns HTTP 503. It reports the
successful allocation and fixture checks while identifying state, GMS, MCP, and catalog checks as
not ready. Allocation failure short-circuits all network access.

The live DataHub proof is **blocked, not simulated**:

- `DATAHUB_TOKEN` was absent during this milestone. Its presence was checked without requesting,
  printing, persisting, or logging a value.
- No mock result is presented as live evidence.
- No before/write/after/restore receipts exist yet.
- The public deployment is still commit `a7d2d51e1f9cd3213d5f822e08c22d3d9c477e33`;
  `/api/readiness` remains 404 there until the coordinator promotes the verified artifact.
- The coordinator owns promotion and guarded shared-host verification. This project chat did not
  open tunnels, access EC2, or deploy.

After this local milestone, the coordinator confirmed that a dedicated service credential is
stored in AWS and loaded into the live services. This project chat did not request, receive, print,
or access that credential. Live receipts remain pending the coordinator-owned guarded host run.

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
  `a7d2d51e1f9cd3213d5f822e08c22d3d9c477e33`.

## Next project-owned milestone

1. After the coordinator's credential follow-up, open separate local tunnels with
   `..\infra\scripts\open_tunnel.ps1 -Service gms` and `-Service mcp`.
2. Run authenticated readiness and preserve the sanitized read receipt.
3. Perform the specifically approved sandbox-only write/re-read/restore sequence and preserve all
   four sanitized receipts.
4. Implement the three seeded semantic fault adapters and campaign execution after the live
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
