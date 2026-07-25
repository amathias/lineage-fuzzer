# Judge Demo

Lineage Fuzzer runs one immutable seeded campaign against a disposable DuckDB fixture. It mutates
only `fuzzer.raw.orders`, restores the fixture between every fault, and requires a final six-table
checksum match before it can return `proved_and_restored`.

## Ninety-second story

1. Show the six DataHub datasets, five lineage edges, complete schemas, owner, domain, tags, and
   three baseline custom assertions captured from the live catalog.
2. Show the current candidate-bound context receipt and immutable campaign SHA-256.
3. Preview three seeded semantic faults: a 100x amount scale, a 45-day stale partition, and a 10%
   customer-key null surge.
4. Approve and run that exact digest.
5. Show that observed changed-table checksums exactly match the lineage-predicted blast radius.
6. Show baseline coverage at 1/3 using the controls derived from the captured DataHub assertions.
7. Open the generated read-only SQL artifact, then show improved coverage at 3/3.
8. Show the final restoration proof and immutable manifest/context evidence directory.

## Local development flow

Install and verify:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,datahub]"
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe scripts\scan_secrets.py
```

Seed the local fixture, print its explicitly local plan, and run the UI:

```powershell
.venv\Scripts\python.exe -m lineage_fuzzer.pipeline_cli seed
.venv\Scripts\python.exe -m lineage_fuzzer.demo_cli plan
$env:LINEAGE_FUZZER_INJECTION_ENABLED = "true"
.venv\Scripts\lineage-fuzzer.exe serve --host 127.0.0.1 --port 8104
```

Local mode is labeled `local-fixture-topology`; it is not live DataHub evidence.

## Immutable DataHub catalog approvals

Print the complete plans before any mutation:

```powershell
.venv\Scripts\lineage-fuzzer.exe show-datahub-plans
```

Current exact plan digests:

- complete six-dataset seed:
  `a4725dd0b241b5dc0dc4da4e9f220c7bca8b349731c3fa255864b4f21ac9f9df`
- exact dataset/baseline-assertion reset:
  `46f7a883f8583790b7bce44410cd8bad68c9acfd45700ae60e20bb2d5352b7d6`
- preserved, separate live-proof assertion plan:
  `75a4d4f9bedb54bfb847ee1e4ea83b33450c2cf6664cf6fe8c8aa16f7d53094e`

Seed is idempotent and restores `removed=false`. Reset invalidates current context evidence before
its first write, soft-deletes only the six exact dataset URNs and three exact baseline assertion
URNs, retains the Domain and Tags, and writes `started`, `failed`, or `completed` receipts. The
separate `fuzzer.catalog-proof.orders-nonempty` assertion is not part of the reset allowlist.

## Coordinator live sequence

Credentials remain out of band. Do not paste or print `DATAHUB_TOKEN`.

1. Promote the exact clean candidate and seed the mounted local DuckDB fixture.
2. Set `LINEAGE_FUZZER_CANDIDATE_SHA` to that exact 40-character commit.
3. Review `show-datahub-plans`, then run the seed command with the exact seed approval:

   ```powershell
   .venv\Scripts\lineage-fuzzer.exe seed-datahub-fixture `
     --approval-sha256 a4725dd0b241b5dc0dc4da4e9f220c7bca8b349731c3fa255864b4f21ac9f9df
   ```

4. Capture the complete live context:

   ```powershell
   .venv\Scripts\python.exe -m lineage_fuzzer.demo_cli `
     capture-live-context `
     --output .lineage-fuzzer\campaign-context.json
   ```

   Capture reads all six entities, all six schemas, direct one-hop lineage from every entity, and
   assertions for every dataset. It requires the exact five-edge graph and three assertion
   definitions. The typed snapshot preserves safe MCP tool schemas, tool/schema/lineage/assertion
   response digests, and candidate/catalog/fixture provenance.

5. Only after capture succeeds, restart the public app with:

   ```text
   APP_ENV=hackathon
   LINEAGE_FUZZER_CANDIDATE_SHA=<exact promoted commit>
   LINEAGE_FUZZER_CONTEXT_FILE=.lineage-fuzzer/campaign-context.json
   LINEAGE_FUZZER_INJECTION_ENABLED=true
   ```

   The container must mount only the allocated Lineage Fuzzer DuckDB fixture at the configured
   path. Injection remains disabled until this restart; no fallback to local context is allowed.

6. Verify `/api/readiness` is 200, `/api/demo/plan` reports
   `context_source=datahub-mcp-live`, review its new approval digest, and invoke the single-flight
   `/api/demo/run`.
7. If isolation/reset evidence is required, record the foreign baseline first, run the exact reset
   approval, confirm only allowlisted tombstones, reseed with the seed approval, recapture context,
   and recheck the foreign baseline byte-for-byte.
8. Roll back to the prior image/config if any gate fails. A reset or reseed always invalidates the
   previous live context, so public execution stays disabled until a fresh capture succeeds.

No expanded live seed/capture/campaign result is claimed by this project task.

## Evidence map

Each campaign writes under:

```text
<evidence-root>/m-<manifest-sha256[0:16]>-c-<context-sha256[0:16]>/
```

The directory contains:

| Path | Evidence |
|---|---|
| `campaign-manifest.json` | seed, exact target, three faults, and predicted URNs |
| `baseline-coverage.json` | DataHub-derived controls and baseline detection matrix |
| `generated/lineage_fuzzer_generated_controls.sql` | immutable runnable read-only SQL |
| `final-coverage.json` | baseline plus generated controls at full coverage |
| `campaign-report.json` | approval, mutation hashes, blast comparison, replay digest, restoration |

The full digests remain inside the manifest and report; the collision-resistant prefixes keep
Windows paths portable. Byte-identical replays reuse those files. A differing replay fails
closed instead of overwriting evidence.

## Preserved live-proof baseline

The earlier candidate `3f6adf08065852f4cd779b3565a979077dcab7be` completed the separate
authenticated assertion write/result/re-read/restore proof with readiness 200 and unchanged
foreign-project evidence. Its exact receipt and isolation hashes remain in
`COORDINATOR_HANDOFF.md`. The UI labels this as a separate proof baseline, not as the current
product candidate.

## Honest boundaries

- Only the exact allowlisted repository fixture is mutable; production databases are rejected.
- Offline fixtures and mocks are never presented as live context.
- The expanded catalog contract has comprehensive offline tests but awaits coordinator live
  promotion.
- Generated SQL cannot authorize mutation and must pass the deterministic read-only validator.
- No secret, raw authorization header, or token is written to Git, receipts, snapshots, or logs.
