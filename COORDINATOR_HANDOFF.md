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
| Status | `Local three-fault judge campaign complete; prior live DataHub proof preserved` |
| Milestone | Deterministic fault/coverage/generation/restoration vertical slice plus judge UI |
| Verified commit/artifact | This clean candidate carries local replay `5e7c9171bcfc0f24d3165711b5690f74a6ad3eb69e73b54187d0bb26cc1fa9f4`; deployed live-proof candidate remains `3f6adf08065852f4cd779b3565a979077dcab7be` |
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
| Campaign plan | `python -m lineage_fuzzer.demo_cli plan` (non-mutating; prints manifest and context-bound approval SHA-256) |
| Campaign run | `python -m lineage_fuzzer.demo_cli --artifact-root examples/generated --evidence-root examples run --approval-sha256 b952f3635f1025b5ff7e1a64c3747c4cb4d88d3bde930f13373ebdcff8bd27cd` |
| Live context capture | `python -m lineage_fuzzer.demo_cli capture-live-context --output <APP_STATE_DIR>/campaign-context.json` (read-only; requires runtime token) |
| Snapshot command | `python -m lineage_fuzzer.pipeline_cli snapshot` |
| Restore command | `python -m lineage_fuzzer.pipeline_cli restore <manifest.json>` |
| Run command | `lineage-fuzzer serve --host 127.0.0.1 --port 8104` |
| Health endpoint | `GET /api/health` verified locally |
| Readiness endpoint | `GET /api/readiness`; returns 200 only when all local and authenticated DataHub checks pass |
| Disposable fixture | `demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb` |
| Snapshot state | `demo/fixtures/lineage-fuzzer/.snapshots/` |
| Long-running workers | None |
| DataHub read | Public readiness 200 before/after proof; exact fixed assertion association and result re-read verified live |
| DataHub writeback | Fixed assertion write/result succeeded live; all four proof receipts verified; assertion restored absent |
| Blockers | None for the local judge campaign or completed live integration gate; fresh live campaign-context capture was not attempted from this no-AWS project chat |
| Evidence produced | 83 passing tests; Ruff clean; local 1/3 to 3/3 report and generated SQL; preserved five live receipt hashes, exact after/restore payloads, and byte-identical 253-row foreign baseline |

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
LINEAGE_FUZZER_CONTEXT_FILE=<optional-saved-live-context-path>
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

## Deterministic semantic campaign status

The new project-owned vertical slice is complete locally:

- Seed `20260724`, context digest
  `12b6bd917e6a1d28614f7d696ff39c26231e80659ea79c66481103cbeca31330`, and
  UUIDv5 campaign identity produce immutable plan SHA-256
  `b952f3635f1025b5ff7e1a64c3747c4cb4d88d3bde930f13373ebdcff8bd27cd`.
- `numeric_scale` deterministically multiplies 12 approved `amount_cents` values by 100.
- `stale_partition` deterministically shifts 12 latest-customer partitions back 45 days.
- `null_density_surge` deterministically nulls 12 approved `customer_id` values.
- Each adapter independently invokes the complete safety gate. Controller authorization occurs
  before fixture creation or seeding.
- Every fault starts from the same snapshot. Row IDs and before/after value SHA-256 values are
  retained; raw mutated values are not.
- Fault-specific predicted DataHub URNs are compared with changed canonical table checksums. All
  baseline and improved runs produced exact predicted/observed matches with no missed or unexpected
  URNs.
- Existing controls detect only the null-density fault: 1/3 or 33.3% baseline coverage.
- The deterministic generator emits
  `examples/generated/lineage_fuzzer_generated_controls.sql`, validates it as a single read-only
  query against only `raw.orders`, executes it cleanly, and adds amount-range plus
  partition-freshness controls.
- The identical campaign then reaches 3/3 or 100.0% coverage.
- Restoration is verified after every fault and at final cleanup across all six managed table
  checksums. The report status is `proved_and_restored`.
- The committed local report replay SHA-256 is
  `5e7c9171bcfc0f24d3165711b5690f74a6ad3eb69e73b54187d0bb26cc1fa9f4`.
- The browser-facing `GET /` demo, `GET /api/demo/plan`, and approved
  `POST /api/demo/run` flow passed locally: page 200, three faults, baseline 1/3, improved 3/3,
  and restoration true.

Offline examples truthfully use `context_source=local-fixture-topology`. The new
`capture-live-context` command provides the production seam: it requires an injected token,
probes `get_entities`, `get_lineage`, and `list_schema_fields`, reads the allocated entity/schema/
three-hop downstream lineage through MCP, reads assertions through authenticated GraphQL, rejects
foreign URNs, and atomically stores a typed snapshot marked `datahub-mcp-live`. The API and CLI can
load that file with `LINEAGE_FUZZER_CONTEXT_FILE` or `--context-file`; any other source marker or
lineageless file fails closed. A captured context creates a distinct manifest digest and therefore
requires a fresh explicit approval.

This chat did not access AWS, did not deploy, did not request a token, and did not rerun or alter
the completed live assertion proof. Coordinator live evidence recorded below remains authoritative
and unchanged.

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

Coordinator promotion of exact candidate `b683e6afc44367e9a88c57ce11d57f486acf3294`
established:

- The exact approved proof reset succeeds idempotently; the fixed assertion is soft-deleted.
- The seeded catalog allocation and public readiness remain 200.
- The first exact proof attempt upserted and activated only the fixed assertion, but DataHub
  rejected `reportAssertionResult` because its index did not yet expose the new assertion/entity
  association. The unconditional `finally` restore succeeded.
- A strict retry after indexing reported the fixed result, but the immediate assertion reread did
  not yet expose that result. It failed closed with `ProofVerificationError`, and the unconditional
  restore succeeded again.
- No successful four-receipt proof set was claimed. The fixed assertion remains soft-deleted and
  the foreign-project baseline remains preserved.

Commit `09e3271ff800e40667b9dd5152b2b771901ba973` adds two exact visibility
gates using the immutable retry schedule `0, 0.25, 0.5, 1, 2, 3` seconds and one strict 15-second
overall deadline around association polling, result reporting, and result polling. The first gate
requires the exact assertion URN, dataset URN, custom type, and logic before result reporting. The
second requires the exact fixed timestamp, result type, and properties before `after.json` can be
written. Absent or older indexed state retries; contradictory state fails immediately with a
static token-free error. Restoration remains outside the deadline and executes unconditionally.
Delayed fake visibility at both boundaries, overall-deadline cancellation, result-attempt
exhaustion, sanitized failure receipts, and restoration are covered by the 64-test suite.

Coordinator promotion and live verification of exact candidate
`3f6adf08065852f4cd779b3565a979077dcab7be` completed the gate:

- Promotion and deterministic local seed succeeded.
- Public health and readiness were 200 before and after the proof.
- Both immutable approval digests matched this handoff exactly.
- The exact proof reset succeeded idempotently.
- One exact proof command returned `status=proved_and_restored` and all four proof paths.
- The verified `after` payload contained exactly the fixed assertion URN, dataset URN, custom type,
  logic, timestamp `1784937600000`, result `SUCCESS`, and the three approved properties.
- The verified restore payload contained `assertions=[]` and
  `status=soft_deleted_and_absent_from_dataset`.
- A fresh foreign-project baseline contained 253 Lifeboat, Forget, License, and Traffic aspect rows
  with SHA-256
  `703dbdb1d1df856ba1e5fd7fd3d57f4e939a83847978f9bc8f91d6c16863481f`.
  The foreign-after snapshot retained 253 rows with the identical hash, and byte-for-byte `cmp`
  passed.
- Coordinator evidence is preserved outside Git at
  `/var/lib/datahub-hackathon/coordinator-evidence/fuzzer-proof-live-002`.
- The credential remains coordinator-managed; this project chat did not request or access it.

Verified receipt SHA-256 values:

| Receipt | SHA-256 |
|---|---|
| Catalog | `6d317ce1b95758f2390231434c6c683f0fd2ece45e588955f657f3b03d4bac93` |
| Before | `76490b831c6dfc2ca605c8d2d680934ece2b313af6999399c889171571ff8aff` |
| Write | `2a05b4011b53bf0719a3dbd4c2c142316bea409853a5675f96e3d5d2f737b1fa` |
| After | `37fca6a4a706ade2a9899f6640f8f543dd43e596a526baed2b3b409128e15a88` |
| Restore | `b27bf7aab97a7dfc2d61dd7d179a2ece326936dfa97350bcba1434a689416ef1` |

The live catalog/assertion write, re-read, restore, readiness, and foreign-isolation gate is
complete. No further compatibility fix is required for this milestone.

### Verified coordinator runbook

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
2. Upserts and activates the fixed custom assertion.
3. Polls the dataset assertion index on the fixed schedule until the exact approved association,
   type, and logic are visible; only then reports the fixed successful result (`write.json`).
4. Polls again until the exact approved timestamp, result type, and properties are visible; only
   then records `after.json`.
5. Soft-deletes only the fixed assertion in `finally`, outside the polling deadline, re-reads its
   absence, and records `restore.json`.

Both polls share one 15-second overall deadline. Exhausting an attempt schedule or the deadline
fails closed with a static token-free error. If association visibility fails, result reporting is
never attempted. If result visibility fails after reporting, `after.json` is not written. The
restore path runs in both cases.

Receipts are atomic, whitelisted, and contain no request headers, raw token, or unbounded server
payload. Expected durable paths are:

```text
/var/lib/datahub-hackathon/lineage-fuzzer/datahub-receipts/catalog-540ba6977764a316/catalog.json
/var/lib/datahub-hackathon/lineage-fuzzer/datahub-receipts/assertion-75a4d4f9bedb54bf/before.json
/var/lib/datahub-hackathon/lineage-fuzzer/datahub-receipts/assertion-75a4d4f9bedb54bf/write.json
/var/lib/datahub-hackathon/lineage-fuzzer/datahub-receipts/assertion-75a4d4f9bedb54bf/after.json
/var/lib/datahub-hackathon/lineage-fuzzer/datahub-receipts/assertion-75a4d4f9bedb54bf/restore.json
```

The verified live proof returned `status=proved_and_restored` with all four proof paths, and public
`/api/readiness` remained 200. Evidence copies and isolation snapshots are preserved at
`/var/lib/datahub-hackathon/coordinator-evidence/fuzzer-proof-live-002`; do not add them to Git.
Future reruns must satisfy the same exact payload, restoration, readiness, and isolation checks
before any new success claim.

## Resource and deployment notes

- DuckDB and snapshots are disposable and ignored by source control.
- DuckDB is now declared directly in `pyproject.toml`; `requirements-fixture.txt` remains only as
  a backward-compatible setup aid.
- DataHub receipts add five small JSON files beneath the existing persistent state allocation.
- Catalog/proof commands are bounded foreground jobs; they add no workers or recurring load.
- Assertion visibility polling uses at most six reads per boundary and one strict 15-second
  deadline for both boundaries plus result reporting.
- A campaign performs six isolated fault runs (three baseline and three improved), restoring before
  and after each; the localhost end-to-end request completed in approximately 22 seconds.
- Local campaign evidence is five small JSON/SQL files under `examples/`; the disposable DuckDB and
  snapshots remain ignored.
- Live campaign-context capture is one bounded read-only foreground job and adds one JSON snapshot.
- `POST /api/demo/run` is single-flight per application process; concurrent fixture campaigns
  receive 409 rather than sharing mutable DuckDB state.
- There are no workers, migrations, new ports, public services, or infrastructure changes.
- Readiness performs bounded read-only DuckDB, GraphQL, and MCP queries per request.
- A local Windows smoke run reached `/api/health` in 7.265 seconds and reported a 3.9 MiB working
  set and 0.016 CPU seconds; treat this as indicative only and remeasure on the deployment host.
- The application remains one process on internal port 8104 with a 512 MiB deployment ceiling.
- The currently deployed, seeded, readiness-200, live-proof-verified commit is
  `3f6adf08065852f4cd779b3565a979077dcab7be`.

## Next project-owned milestone

1. On a coordinator-controlled host, capture the allocated live DataHub context with the new
   read-only command, print its distinct plan digest, and run the same guarded local fixture
   campaign against that saved context.
2. Preserve the new live-context snapshot digest and campaign report only after exact
   predicted/observed, 1/3 to 3/3, and restoration checks pass.
3. Preserve the completed assertion receipts and foreign-isolation snapshot as immutable
   coordinator evidence; do not rerun the proof unless new integration behavior needs verification.
4. Keep the fixed assertion soft-deleted outside an explicitly approved proof run.

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
