# Coordinator Handoff: Lineage Fuzzer

## 2026-07-29 shadow-module cleanup — deployed and verified

- Removed the four unreachable module files shadowed by the canonical `api`, `cli`, `config`, and
  `datahub.mcp` packages.
- Import-resolution checks still select the package implementations used by the application.
- Verification: 123 tests passed, Ruff passed, secret scanning passed, and whitespace checks
  passed.
- The change removes 281 divergent dead lines and does not alter runtime behavior, dependencies,
  ports, DataHub namespace, or deployment topology.
- Exact commit `5ca3c010d57d542bc66f78b6dad67d9ee2bec350` passed GitHub Actions and was
  promoted by the coordinator.
- The candidate-bound live-context receipt correctly failed closed after promotion. The
  coordinator backed up the prior files and ran the documented read-only recapture: six entities,
  five lineage edges, and three assertion payloads produced context SHA-256
  `3382b372f4ec39c412cd35bc5f04bf1aabeced1aee12a3c36d3f454b69bc10f3`.
  Root, health, and readiness then returned 200; the judge plan is enabled with approval SHA-256
  `d48de523069341cdf5ca58f4672272aa005722ceef15c629c7bc06cbdad862f1`.

## 2026-07-29 public-demo boundary closeout

| Field | Verified value |
|---|---|
| Exact deployed product | `afb62abcbb5ec5a141f23f42a8755d75ec2c549d` |
| Public endpoint | `https://fuzzer.datahub-hackathon.aaronmathias.com` |
| Public acceptance | Root, health, and strong readiness returned 200 |
| Browser acceptance | One prominent `PUBLIC DEMO` notice rendered above the workflow and identified the disposable DuckDB fixture, `fuzzer.*` topology, single-flight restoration contract, and source/API/self-hosting link |
| Hosted API documentation | `/docs`, `/redoc`, and `/openapi.json` returned 404 in hackathon mode; local/development/test documentation remains enabled |
| Verification | 123 tests passed, Ruff passed, GitHub Actions passed, and exact `main` matched `origin/main` before promotion |
| Current live context | Read-only recapture verified 6 entities, 5 lineage edges, and 3 assertion payloads; context SHA-256 `3ea7094e773a6c2d6370660d0c0a8a55eb058c0fa39ab3b8af8b94cbff1b930f` |
| Current judge plan | `context_source=datahub-mcp-live`, `run_enabled=true`, approval SHA-256 `9764eea55cde76eb9a9b31510bebda95030a32d57795c3cbac0cf8fee56c092d` |

Because a live context receipt is intentionally bound to the exact deployed candidate, the UI-only
commit correctly invalidated the earlier receipt. The coordinator retained timestamped local
backups, reran only the documented read-only context capture, restarted the service, and verified
the exact new candidate in the browser. No DataHub catalog seed, write, or reset occurred.

## Current handoff

| Field | Value |
|---|---|
| Status | `Submission assets finalized; deployed product candidate unchanged` |
| Product candidate | `92db02471a6bdb517be2db934a146b71509fe442` |
| Branch | `main` |
| Canonical origin | `git@github-datahub-lineage-fuzzer:amathias/lineage-fuzzer.git` |
| Milestone | Complete product, restored live evidence, judge-ready Devpost copy, and under-three-minute recording runbook |
| Local tests | `122 passed` |
| Lint | `python -m ruff check src tests scripts` passed |
| Secret scan | `secret_scan=clean tracked_files=81` |
| Archive verification | Exact `git archive` of the product candidate passed isolated install, wheel build/reinstall/import, 122 tests, Ruff, fixture/controls commands, and judge UI smoke |
| Local campaign | `status=proved_and_restored`, baseline `1/3 (33.3%)`, improved `3/3 (100.0%)`, restoration true |
| Live status | Deployed `92db024` completed zero-write reset recovery, then the unchanged approved seed and live capture succeeded after the coordinator restored the shared OpenSearch backend. Readiness and plan are 200, context source is `datahub-mcp-live`, run is enabled, and injection is true. |
| AWS/deployment activity | None from this project task |

This project chat owns Lineage Fuzzer product code and evidence contracts. The portfolio coordinator
owns shared DataHub, AWS, deployment, credentials, public routing, and cross-project isolation. Do
not edit the live host from this project chat, and do not place a token in a command, log, prompt,
receipt, screenshot, fixture, or Git.

## Final submission assets

The final public submission package is documentation-only and does not change or redeploy product
candidate `92db02471a6bdb517be2db934a146b71509fe442`.

| Asset | Exact value |
|---|---|
| Public application | `https://fuzzer.datahub-hackathon.aaronmathias.com` |
| Public repository | `https://github.com/amathias/lineage-fuzzer` |
| Public demo video | `https://youtu.be/eAmFwXIyRi4` (2:28, published English captions) |
| Devpost copy | `SUBMISSION.md` |
| Recording runbook | `docs/JUDGE_DEMO.md` |
| Recording target | `2:45`; hard stop `2:55` |

The submission copy covers category fit, architecture, use case, setup/adoption, challenges,
accomplishments, DataHub MCP plus supported API integration, and the exact live-evidence boundary.
The runbook gives a timestamped public-app/public-repository sequence and requires the recording
to stop rather than substitute local or cached evidence if live context, exact blast matching,
coverage improvement, or restoration is unavailable. `README.md` now links both final assets and
the exact public URLs.

Proportional documentation checks passed: Markdown structure and balanced fences, local link
targets, the exact public URL allowlist, placeholder scan, public-safety pattern scan, tracked-file
secret scan, docs-only diff scope, and `git diff --check`. Product tests, dependencies, runtime
configuration, campaign evidence, and SQL controls were not changed or rerun for this
documentation-only milestone.

## Fixed allocation

| Setting | Exact value |
|---|---|
| Project slug | `lineage-fuzzer` |
| Internal port | `8104` |
| DataHub domain | `Demo / Lineage Fuzzer` |
| Domain URN | `urn:li:domain:lineage-fuzzer` |
| Project tag | `project-lineage-fuzzer` |
| Sandbox tag | `lineage-fuzzer-sandbox` |
| Dataset prefix | `fuzzer.` |
| Dataset platform/environment | `duckdb` / `DEV` |
| Owner | `urn:li:corpuser:lineage-fuzzer` |
| Fixture root | `demo/fixtures/lineage-fuzzer` |
| Default fixture | `demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb` |
| Deployment state root | `/var/lib/datahub-hackathon/lineage-fuzzer` |

Every mutating path fails closed on environment, platform, path, marker, tag, allocation, and URN
prefix. DataHub catalog reset is an exact allowlist, not a search delete or global cleanup.

## Exact live catalog contract

The immutable seed plan creates or restores these six active datasets:

1. `urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.customers,DEV)`
2. `urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.orders,DEV)`
3. `urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.staging.orders_enriched,DEV)`
4. `urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.marts.daily_revenue,DEV)`
5. `urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.marts.customer_value,DEV)`
6. `urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.reporting.executive_dashboard,DEV)`

Each dataset must have its complete expected `schemaMetadata`, `datasetProperties` containing
`project_slug=lineage-fuzzer` and `sandbox=true`, exact Domain, both exact Tags, exact owner, and
`removed=false`.

The exact five lineage edges are:

1. `fuzzer.raw.customers -> fuzzer.staging.orders_enriched`
2. `fuzzer.raw.orders -> fuzzer.staging.orders_enriched`
3. `fuzzer.staging.orders_enriched -> fuzzer.marts.daily_revenue`
4. `fuzzer.staging.orders_enriched -> fuzzer.marts.customer_value`
5. `fuzzer.marts.customer_value -> fuzzer.reporting.executive_dashboard`

The exact active baseline assertions are:

| Assertion URN | Dataset | Control type |
|---|---|---|
| `urn:li:assertion:fuzzer.control.orders-customer-id-not-null` | `fuzzer.raw.orders` | `orders_customer_id_not_null` |
| `urn:li:assertion:fuzzer.control.orders-order-id-unique` | `fuzzer.raw.orders` | `orders_order_id_unique` |
| `urn:li:assertion:fuzzer.control.daily-revenue-non-negative` | `fuzzer.marts.daily_revenue` | `daily_revenue_non_negative` |

The separate proof assertion
`urn:li:assertion:fuzzer.catalog-proof.orders-nonempty` is not part of this baseline assertion
allowlist and is preserved by the expanded catalog reset.

## Immutable approvals

Run the non-mutating plan command first:

```powershell
lineage-fuzzer show-datahub-plans
```

The exact current digests are:

| Plan | SHA-256 |
|---|---|
| Complete catalog seed | `a4725dd0b241b5dc0dc4da4e9f220c7bca8b349731c3fa255864b4f21ac9f9df` |
| Exact catalog reset | `46f7a883f8583790b7bce44410cd8bad68c9acfd45700ae60e20bb2d5352b7d6` |
| Preserved assertion proof | `75a4d4f9bedb54bfb847ee1e4ea83b33450c2cf6664cf6fe8c8aa16f7d53094e` |

Commands:

```powershell
lineage-fuzzer seed-datahub-fixture `
  --approval-sha256 a4725dd0b241b5dc0dc4da4e9f220c7bca8b349731c3fa255864b4f21ac9f9df

lineage-fuzzer reset-datahub-fixture `
  --approval-sha256 46f7a883f8583790b7bce44410cd8bad68c9acfd45700ae60e20bb2d5352b7d6
```

Seed is idempotent, restores every dataset to `removed=false`, activates the three baseline
assertions, and verifies the complete catalog before writing seeded state. Reset first invalidates
the current campaign context and receipt and records `started`. It reads the direct status aspect
for only the three exact baseline assertions and six exact datasets, skips writes for tombstones
already present, writes only missing exact tombstones, then positively re-reads all nine status
aspects before recording `completed`. It does not query assertions through soft-deleted datasets.
A read, write, or postcondition failure writes a sanitized `failed` receipt. Repeated reset is
idempotent. Domain, Tags, proof assertion, and foreign namespaces are retained.

## Required deployment environment

The coordinator supplies values without exposing the credential:

```text
PROJECT_SLUG=lineage-fuzzer
APP_ENV=hackathon
APP_HOST=<coordinator bind address>
APP_PORT=8104
APP_PUBLIC_URL=<coordinator assigned URL>
APP_STATE_DIR=/var/lib/datahub-hackathon/lineage-fuzzer
DATAHUB_GMS_URL=http://127.0.0.1:8080
DATAHUB_MCP_URL=http://127.0.0.1:8000/mcp
DATAHUB_TOKEN=<runtime secret>
DATAHUB_DOMAIN=Demo / Lineage Fuzzer
DATAHUB_PROJECT_TAG=project-lineage-fuzzer
DATAHUB_URN_PREFIX=fuzzer.
DEMO_FIXTURE_ROOT=demo/fixtures/lineage-fuzzer
LINEAGE_FUZZER_READINESS_DATASET_URN=urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.orders,DEV)
LINEAGE_FUZZER_CANDIDATE_SHA=92db02471a6bdb517be2db934a146b71509fe442
LINEAGE_FUZZER_CONTEXT_FILE=/var/lib/datahub-hackathon/lineage-fuzzer/campaign-context.json
LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS=demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb
LINEAGE_FUZZER_ALLOWED_ENVIRONMENTS=DEV
LINEAGE_FUZZER_ALLOWED_PLATFORMS=duckdb
LINEAGE_FUZZER_REQUIRED_SANDBOX_TAG=lineage-fuzzer-sandbox
LINEAGE_FUZZER_REQUIRED_MARKER_KEY=sandbox
LINEAGE_FUZZER_REQUIRED_MARKER_VALUE=true
LINEAGE_FUZZER_INJECTION_ENABLED=false
```

Pinning is deliberate: `mcp==1.28.1` and optional DataHub client
`acryl-datahub==1.6.0.15`.

## Coordinator promotion and live run order

Do not silently fall back to local context. A saved file is accepted only with its matching
receipt, promoted 40-character candidate SHA, seeded catalog-state digest, catalog-plan digest,
current fixture checksums, exact MCP tool schemas, and complete DataHub observations.

The coordinator has completed the reset/reseed/capture recovery described below. This remains the
normal clean promotion/run order for a future deployment or replay.

1. Promote exact candidate `92db02471a6bdb517be2db934a146b71509fe442`. Keep
   `LINEAGE_FUZZER_INJECTION_ENABLED=false` and do not expose the public run yet.
2. Install/build, then seed the mounted disposable DuckDB fixture:

   ```powershell
   python -m lineage_fuzzer.pipeline_cli seed
   ```

3. Set `LINEAGE_FUZZER_CANDIDATE_SHA` to the exact promoted commit. Run
   `lineage-fuzzer show-datahub-plans` and compare all three digests above.
4. Run the exact approved complete catalog seed. It must return verified seeded state for all six
   entities, five edges, complete schemas/metadata, and three baseline assertions.
5. Capture live context read-only:

   ```powershell
   python -m lineage_fuzzer.demo_cli capture-live-context `
     --output /var/lib/datahub-hackathon/lineage-fuzzer/campaign-context.json
   ```

   Capture reads safe MCP tool schemas, all six entities, each full schema, direct lineage from
   every entity, and GraphQL assertions for every dataset. It rejects incomplete lineage,
   missing/contradictory assertions, forged source labels, foreign URNs, wrong metadata, stale
   catalog state, candidate mismatch, and fixture drift. It writes the snapshot and adjacent
   `campaign-context.json.receipt.json`.

6. Restart the app only after capture succeeds, with the context path above and
   `LINEAGE_FUZZER_INJECTION_ENABLED=true`. The container must mount only the allocated disposable
   Lineage Fuzzer DuckDB at the exactly allowlisted path.
7. Verify:

   - `GET /api/health` is 200.
   - `GET /api/readiness` is 200 and reports current candidate-bound live context.
   - `GET /api/demo/plan` reports `context_source=datahub-mcp-live`, six nodes, five edges,
     `run_enabled=true`, and a new context-bound approval SHA-256.
   - The judge page displays the live source before enabling Run.

8. Review and approve the exact digest returned by the live plan, then invoke the single-flight
   judge run. A successful result must show three reproducible fault adapters, exact
   predicted-versus-observed URNs, baseline `1/3`, generated runnable read-only SQL, improved
   `3/3`, immutable evidence, and `status=proved_and_restored`.
9. Preserve campaign evidence under its manifest/context-digest directory. Byte-identical replay
   may reuse evidence; differing bytes must fail rather than overwrite it.
10. If reset/isolation evidence is required:

    - Capture and hash the foreign-project baseline first.
    - Run the exact reset approval.
    - Confirm readiness/run becomes unavailable because context was invalidated.
    - Verify only the six datasets and three baseline assertions were tombstoned.
    - Rerun the exact seed, recapture context, restart with the new receipt, and recheck readiness.
    - Compare the foreign baseline byte-for-byte and by row count/hash.

11. If any gate fails, immediately disable injection and the public run. While this candidate is
    still available, use only its approval-bound reset if the expanded allocation must be removed.
    Never search-delete or globally reset DataHub. Roll the app image/config back to the prior
    coordinator-approved version and preserve all failed receipts for diagnosis.

The complete expanded seed, live context capture, and judge campaign are coordinator-reported
successful. Exact zero-write reset recovery and the subsequent unchanged seed/capture restore are
also complete on deployed `92db02471a6bdb517be2db934a146b71509fe442`.

## Coordinator live capture finding and correction

Coordinator promotion of exact candidate
`2fe34e4366e2c25db502ceffba7a8e24bc0dc58a` established:

- The exact approval-bound six-dataset seed succeeded and verified the complete catalog contract.
- Strict context capture then failed closed on `fuzzer.raw.customers`.
- The pinned MCP response was complete and returned correct field metadata in alphabetical order:
  `country_code`, `customer_id`, `customer_name`, `segment`.
- The contract declaration order is `customer_id`, `customer_name`, `segment`, `country_code`.
- Schema field order is non-semantic. Candidate `2fe34e4` incorrectly required tuple order equality.
- No live context receipt, public judge campaign, reset, or new isolation result was claimed.

Candidate `99c0924677971ed1cf0c47ea2c1bd76fc4be8b98` makes only the project-owned
compatibility correction:

- Captured field paths are compared as an exact order-insensitive set.
- Duplicate observations fail closed before set comparison can hide them.
- Missing and extra paths continue to fail closed.
- Accepted paths are canonicalized to contract declaration order before snapshotting, so MCP
  response ordering cannot change the typed context digest.
- Entity metadata, lineage, assertions, candidate SHA, catalog state/plan, fixture checksums, raw
  response digests, context receipt, sandbox, namespace, and mutation gates are unchanged.
- Regression fixtures use the exact observed alphabetical `raw.customers` response and separately
  reject duplicate, missing, and extra paths.

Coordinator promotion of exact candidate
`99c0924677971ed1cf0c47ea2c1bd76fc4be8b98` established:

- The idempotent exact seed again verified all 6 datasets, 5 edges, and 3 baseline assertions.
- Schema validation passed with the real MCP response order.
- Capture then failed closed with
  `one-hop lineage response contains a non-direct result`.
- The sanitized MCP evidence SHA-256 is
  `c7f11beba2618dc83401dad3703f472dfb9454a8ea118f5ce6e90ee0a07aceb9`.
- All five expected downstream dataset results were present with numeric `degree=1`.
- The same response also embedded the source dataset's owner, platform, domain, and tag entities
  without degrees.
- The recursive extractor treated any nested dictionary containing `entity.urn` as a lineage
  result and therefore rejected unrelated governance metadata.
- No live context receipt, public judge campaign, reset, or new isolation result was claimed.

Candidate `3633f2113779469f938c07cffd1510851e344570` makes only the lineage-result
extraction correction:

- Only entries in the pinned MCP `searchResults` list are considered lineage results.
- Every accepted entry must contain a dataset entity at the exact result location and a numeric
  `degree=1`.
- Missing or non-direct degrees, malformed/wrong entity types, source-as-downstream results,
  duplicate dataset results, and foreign or unexpected dataset URNs fail closed.
- Owner, platform, domain, tag, and other unrelated entity metadata outside result entries is
  ignored rather than reclassified as lineage.
- Accepted downstream URNs are sorted before exact comparison with the expected direct set.
- Entity, schema, assertion, candidate SHA, catalog state/plan, fixture checksum, raw-response
  digest, context receipt, sandbox, namespace, and mutation gates are unchanged.
- Regression fixtures reproduce the exact mixed response for `raw.customers`, `raw.orders`,
  `staging.orders_enriched`, and `marts.customer_value`, while retaining incomplete, foreign,
  missing-degree, non-direct, duplicate, and contradictory-type failures.

Coordinator promotion of exact candidate
`3633f2113779469f938c07cffd1510851e344570` established:

- The strict parser failed closed with
  `one-hop lineage response has an invalid result envelope`.
- The real pinned `upstream=false` response does not place `searchResults` at top level.
- Its exact direction shape is
  `{"downstreams":{"facets":[...],"hasMore":false,"offset":0,"returned":N,"searchResults":[...],"total":N}}`.
- Nonempty results contain the expected dataset entity at `downstreams.searchResults[*].entity`
  with numeric `degree=1`. At this point the local contract assumed empty downstreams returned
  the same envelope with zero counts and an empty list; the fourth live finding below corrects
  that assumption.
- Governance aggregation facets contain unrelated nested entity URNs but remain outside
  `downstreams.searchResults`.
- Candidate `3633f21` correctly stopped recursive discovery but incorrectly assumed the synthetic
  top-level `searchResults` test envelope.
- No live context receipt, public judge campaign, reset, or new isolation result was claimed.

Candidate `3a25d79aa1d9b81ebc48ad3a3b567ce6e4119a0a` makes only the exact direction
envelope correction:

- The only accepted top-level shape is one unambiguous `downstreams` object for the existing
  `upstream=false` request.
- The direction object must contain exactly `facets`, `hasMore`, `offset`, `returned`,
  `searchResults`, and `total`.
- `facets` and `searchResults` must be lists; `offset` must be integer zero; `hasMore` must be
  false; `returned` must equal the result-list length; and `total` must equal `returned`.
- Pagination, inconsistent counters, top-level `searchResults`, upstream-only, dual-direction,
  missing-field, and extra-field envelopes fail closed.
- Only `downstreams.searchResults` entries are parsed. Governance facets are retained in the raw
  response digest but never traversed for lineage.
- Numeric direct degree, dataset type/location, source exclusion, uniqueness, foreign/unexpected
  rejection, completeness, and canonical sorting remain enforced.
- Exact regressions cover nested nonempty downstreams plus malformed, ambiguous,
  wrong-direction, paginated, incomplete, foreign, non-direct, duplicate, and contradictory
  results. No unproven top-level compatibility is retained.
- Entity, schema, assertion, candidate SHA, catalog state/plan, fixture checksum, raw-response
  digest, context receipt, sandbox, namespace, and mutation gates are unchanged.

Coordinator promotion of exact candidate
`3a25d79aa1d9b81ebc48ad3a3b567ce6e4119a0a` established:

- Strict capture reached lineage pagination validation after the approved catalog again verified.
- The real pinned MCP exposes two exact downstream direction variants.
- Nonempty directions contain exactly `facets`, `hasMore`, `offset`, `returned`,
  `searchResults`, and `total`. The observed counts are `1/1` or `2/2`, `hasMore=false`, and
  `offset=0`.
- Empty directions for `fuzzer.marts.daily_revenue` and
  `fuzzer.reporting.executive_dashboard` contain exactly `facets` and integer `total=0`.
  Their `facets` value is a one-element list; all four paging/result keys are omitted.
- Candidate `3a25d79` incorrectly required the full six-key direction for empty results and
  therefore failed closed on this truthful pinned response.
- No live context receipt, public judge campaign, reset, or new isolation result was claimed.

Candidate `472d4d850c9b6e34529eddb0507a4e015987d33f` makes only the exact zero-result
compatibility correction:

- An empty direction is accepted only when its key set is exactly `{"facets","total"}`,
  `facets` is a list, `total` has exact integer type, and `total == 0`.
- A short-form nonzero total, any extra field, any partial/mixed paging shape, and a synthetic
  full six-field empty direction fail closed.
- The full direction remains required for nonempty results and must contain a positive exact
  `returned` count, an equally sized `searchResults` list, matching integer `total`,
  `hasMore=false`, and integer `offset=0`.
- Numeric direct degree, dataset type/location, source exclusion, uniqueness, exact expected
  downstream comparison, foreign rejection, and canonical sorting are unchanged.
- Entity, schema, assertion, candidate SHA, catalog state/plan, fixture checksum, raw-response
  digest, context receipt, sandbox, namespace, and mutation gates are unchanged.
- Pinned regressions reproduce the exact one-facet short empty envelope and reject short-form
  nonzero, extra-key, mixed, and full-empty variants.

## Coordinator live reset finding and correction

After the coordinator-reported successful live campaign on exact deployed product
`472d4d850c9b6e34529eddb0507a4e015987d33f`:

- The exact reset approval was
  `46f7a883f8583790b7bce44410cd8bad68c9acfd45700ae60e20bb2d5352b7d6`.
- Reset wrote sanitized `started` and `failed` receipts. The failed receipt recorded only
  `error_type=DataHubGraphQLError`.
- Context and its receipt were correctly invalidated before mutation; public readiness is
  truthfully 503.
- Read-only inspection of current `status` aspects in `metadata_aspect_v2` confirmed
  `removed=true` for exactly all nine allowlisted fixtures: the three
  `urn:li:assertion:fuzzer.control.*` assertions and all six allocated DuckDB `fuzzer.*`
  datasets.
- This proves all nine reset mutations completed. Candidate `472d4d8` then called
  `assertions_for_dataset` for already-tombstoned datasets during `_verify_reset`; the resulting
  GraphQL error prevented an honest completed receipt.
- Sibling portfolio state remained byte-identical with SHA-256
  `873849f2a097ad5a799275d578339392ed64bc17b3315eac7bfdf746e4af8a53`.
- No successful reset completion receipt is claimed from that attempt.

Candidate `92db02471a6bdb517be2db934a146b71509fe442` makes only the reset verification
and recovery correction:

- Reset preflights direct OpenAPI `status` aspects for the exact three assertion and six dataset
  URNs. Read errors propagate and fail closed.
- Tombstones already observed as `removed=true` are reused without another mutation. Only missing
  exact tombstones are written.
- A separate strict postcondition read positively verifies `removed=true` for all nine exact URNs
  before catalog state becomes `reset` and a completed receipt is written.
- Assertion verification no longer traverses GraphQL through deleted datasets. GraphQL errors are
  neither caught nor interpreted as success.
- The completed receipt separately lists already-present assertion/dataset tombstones and
  assertion/dataset tombstones written by that invocation.
- Context invalidation, immutable approval, exact namespace, retained Domain/Tags/proof assertion,
  sanitized failed receipts, and foreign-project isolation guards are unchanged.
- Regressions reproduce a `DataHubGraphQLError` only after all datasets are tombstoned, prove a
  zero-write idempotent recovery, and fail closed when an assertion tombstone is not visible.

### Completed zero-write reset recovery and restored live state

The coordinator promoted exact `92db02471a6bdb517be2db934a146b71509fe442` and ran the same
approval-bound reset against the nine already-tombstoned entities:

- Reset exited 0 with `status=soft_deleted_and_verified`.
- All three assertion URNs were listed in `assertion_urns_already_tombstoned`.
- All six dataset URNs were listed in `dataset_urns_already_tombstoned`.
- Both `assertion_tombstones_written` and `dataset_tombstones_written` were empty.
- A completed receipt was written. Its coordinator-reported payload SHA-256 prefix is
  `155a7111...`.
- Readiness remained 503 and injection remained false, as required while context was invalidated.

The coordinator then followed the documented restore with the unchanged exact seed approval
`a4725dd0b241b5dc0dc4da4e9f220c7bca8b349731c3fa255864b4f21ac9f9df`:

- Both the initial seed and one evidence-preserving idempotent retry reactivated all nine exact
  statuses to `removed=false`, then failed closed with `DataHubGraphQLError`.
- Catalog state remained `seed_failed`; readiness remained 503; injection remained false; no
  context capture was attempted.
- The repeated failures were not a Lineage Fuzzer defect. Shared `datahub-opensearch-1` had exited
  at 17:15:28 with exit 127 after `OutOfMemoryError: unable to create native thread` and a fatal
  refresh-thread failure; its restart policy was `no`.
- The same missing shared search backend caused contemporaneous `Root cause: search` failures in
  sibling projects. No project product change was warranted.

After the coordinator restored and hardened OpenSearch, the unchanged deployed `92db024` path
succeeded:

- The unchanged approved seed exited 0 with `status=verified`.
- Live context capture exited 0 with 6 entities, 5 edges, and 3 assertion payloads.
- The coordinator-reported context SHA-256 prefix is `68e5b038...`.
- The sibling query remained byte-identical; its coordinator-reported SHA-256 prefix is
  `4bc98104...`.
- Injection was restored to true.
- `GET /api/readiness` returned 200.
- `GET /api/demo/plan` returned 200 with `context_source=datahub-mcp-live` and
  `run_enabled=true`.
- The coordinator-reported live plan approval SHA-256 prefix is `1a9f004f...`.

The direct seed-verification experiment created while OpenSearch was unavailable was discarded and
never pushed. Product candidate `92db02471a6bdb517be2db934a146b71509fe442` remains authoritative.

## Readiness and judge UI contract

In `APP_ENV=hackathon`, readiness and the public plan require:

1. Exact allocation and existing writable state directory.
2. Current deterministic DuckDB fixture and six read-only checksums.
3. Authenticated GMS and required MCP capabilities.
4. Allocated readiness dataset metadata.
5. A complete `datahub-mcp-live` context plus matching receipt bound to the running candidate,
   seeded catalog state/plan, and current fixture.

Missing or stale live evidence returns 503 and disables the public run. Injection separately
remains default-deny. `POST /api/demo/run` is single-flight per process and returns 409 for a
concurrent campaign.

The graph and executable baseline control set come from the verified live snapshot. In live mode,
the runner derives only the three exact allowlisted controls from the captured DataHub assertions;
it rejects missing, extra, foreign, or contradictory definitions. Local development remains
explicitly labeled `local-fixture-topology`.

## Local deterministic evidence

This product candidate completed an offline, explicitly local campaign:

| Evidence | Value |
|---|---|
| Context source | `local-fixture-topology` |
| Local context digest | `5fb670d83bcf5f6be59023c85f5b74fe59fd5eeaf30f2c47a8d84b625b953dde` |
| Approval/manifest SHA-256 | `e5e5443c89c8b74cadf4b2a62dd7e7a5cec5315c072b97efee25049cb2d18fd0` |
| Replay SHA-256 | `be8aca5f64be2cab422bfff73c6ccb79271275abd93526b9720d13116fa169cd` |
| Generated SQL SHA-256 | `a5d3f3dd8ae5ae05f21f870dff9d57d639fa6fa9a7d82d4b5a23848fb559fd52` |
| Baseline/improved | `1/3 (33.3%)` to `3/3 (100.0%)` |
| Final status | `proved_and_restored`; all six fixture table checksums restored |

Evidence is stored under:

```text
<evidence-root>/m-<manifest-sha256[0:16]>-c-<context-sha256[0:16]>/
```

It includes `campaign-manifest.json`, `baseline-coverage.json`, immutable generated SQL,
`final-coverage.json`, and `campaign-report.json`. This evidence is intentionally ignored and was
not added to Git.

## Exact local verification

Working-tree checks:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests scripts
.venv\Scripts\python.exe scripts\scan_secrets.py
git diff --check
```

Results: 122 tests passed; Ruff passed; `secret_scan=clean tracked_files=81`; diff check passed.
The test suite covers exact seed payloads, pinned SDK deserialization, idempotent reset/reseed,
partial reset failure receipts, tombstones, foreign namespaces, full pinned MCP/GraphQL response
shapes, forged/incomplete snapshots, DataHub-derived controls, immutable evidence, public
live-only gates, single-flight execution, generated SQL validation, and restoration.

Exact-archive command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify_archive.ps1 `
  -Commit 92db02471a6bdb517be2db934a146b71509fe442
```

Result:

```text
verified_archive commit=92db02471a6bdb517be2db934a146b71509fe442
wheel=lineage_fuzzer-0.1.0-py3-none-any.whl
```

The verifier extracted `git archive` into a disposable directory, scanned all 81 archived files,
created a fresh environment, installed `.[dev,datahub]`, built and force-reinstalled the wheel,
imported `datahub`, `lineage_fuzzer`, and `mcp`, reran all 122 tests and Ruff, seeded the fixture,
ran baseline controls, and exercised the judge root/plan through `TestClient`.

## Preserved live assertion proof

The previous live proof is authoritative, unchanged, and separate from this new product
candidate. Exact deployed proof candidate:
`3f6adf08065852f4cd779b3565a979077dcab7be`.

- Promotion and deterministic local seed succeeded.
- Public health/readiness were 200 before and after proof.
- Exact proof reset was idempotent.
- The command returned `status=proved_and_restored`.
- The after payload contained the exact fixed assertion/dataset/custom type/logic, timestamp
  `1784937600000`, `SUCCESS`, and three approved properties.
- Restore contained `assertions=[]` and
  `status=soft_deleted_and_absent_from_dataset`.
- A 253-row foreign baseline had SHA-256
  `703dbdb1d1df856ba1e5fd7fd3d57f4e939a83847978f9bc8f91d6c16863481f`;
  foreign-after retained 253 rows, the identical hash, and byte-for-byte `cmp`.
- Evidence remains outside Git at
  `/var/lib/datahub-hackathon/coordinator-evidence/fuzzer-proof-live-002`.

Receipt SHA-256:

| Receipt | SHA-256 |
|---|---|
| Catalog | `6d317ce1b95758f2390231434c6c683f0fd2ece45e588955f657f3b03d4bac93` |
| Before | `76490b831c6dfc2ca605c8d2d680934ece2b313af6999399c889171571ff8aff` |
| Write | `2a05b4011b53bf0719a3dbd4c2c142316bea409853a5675f96e3d5d2f737b1fa` |
| After | `37fca6a4a706ade2a9899f6640f8f543dd43e596a526baed2b3b409128e15a88` |
| Restore | `b27bf7aab97a7dfc2d61dd7d179a2ece326936dfa97350bcba1434a689416ef1` |

The earlier live assertion write/re-read/restore/isolation gate is complete, and no further live
proof compatibility fix is pending. Do not rerun it unless a future integration change requires a
new explicit proof.

## Resource notes and limitations

- One application process, internal port 8104, no workers, migrations, recurring jobs, or new
  infrastructure.
- `mcp==1.28.1` and `acryl-datahub==1.6.0.15` increase image dependency size but add no idle
  service.
- Catalog seed/reset and context capture are bounded foreground commands.
- Readiness performs bounded read-only DuckDB, GraphQL, MCP, allocation, and context-binding
  checks.
- One campaign performs six isolated fault runs and restores before/after each. Local execution is
  campaign-heavy and should remain single-flight.
- DuckDB, snapshots, context receipts, catalog receipts, and campaign evidence belong only under
  the allocated state/fixture roots and remain outside Git.
- The expanded catalog seed, schema compatibility, both lineage-envelope variants, live capture,
  judge campaign, exact zero-write reset recovery, completed reset receipt, unchanged reseed,
  recapture, and sibling isolation are coordinator-observed on the authoritative product.
- Shared DataHub search availability is an infrastructure prerequisite for GraphQL assertion
  discovery, MCP entity search, and lineage PIT queries. A shared search outage must not be
  misclassified as a project-owned verification defect.
