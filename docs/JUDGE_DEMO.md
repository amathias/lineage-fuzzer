# Judge Demo and Recording Runbook

Target duration: **2 minutes 45 seconds**. Hard stop: **2 minutes 55 seconds**.

The recording uses only the public Lineage Fuzzer application and public repository:

- [Live judge application](https://fuzzer.datahub-hackathon.aaronmathias.com)
- [Public source repository](https://github.com/amathias/lineage-fuzzer)
- [Emitted runnable SQL](https://github.com/amathias/lineage-fuzzer/blob/main/examples/generated/lineage_fuzzer_generated_controls.sql)

## Claims the recording must keep separate

- The page's campaign context is captured from live open-source DataHub through DataHub MCP plus
  supported GraphQL reads.
- The three fault mutations run only against the disposable Lineage Fuzzer DuckDB fixture. They
  do not mutate DataHub datasets or a production warehouse.
- A complete expanded campaign returned `proved_and_restored`; current public-environment
  verification also established fresh live capture, readiness 200, and an enabled live plan.
- The “Separate live-proof baseline” card refers to an earlier, separately restored DataHub
  custom-assertion write/result/re-read proof. Do not describe it as the current campaign's
  writeback.

One sentence that captures the boundary cleanly:

> DataHub supplies the live graph, schemas, ownership, and baseline assertions; the faults run
> only in a disposable DuckDB fixture; and a separate approval-bound assertion transaction proves
> supported DataHub writeback and restoration.

## Before recording

### Public-state check

- [ ] Open the [live judge application](https://fuzzer.datahub-hackathon.aaronmathias.com).
- [ ] Confirm the toolbar says **Current live DataHub context verified**.
- [ ] Confirm the footer says `Context source: datahub-mcp-live`.
- [ ] Confirm **Approve + run campaign** is enabled.
- [ ] Confirm the graph and all three fault cards render.
- [ ] Do not record if the page reports local context, readiness failure, disabled injection, a
      different candidate, or a campaign error.

### Browser and capture setup

- [ ] Use a 1920x1080 or larger capture and browser zoom that keeps the graph, fault cards, and
      result matrix legible.
- [ ] Pre-open the live application in the first tab and the
      [emitted SQL file](https://github.com/amathias/lineage-fuzzer/blob/main/examples/generated/lineage_fuzzer_generated_controls.sql)
      in the second.
- [ ] Hide bookmarks containing private links, close terminals and cloud consoles, disable
      notifications, and use a clean browser profile.
- [ ] Keep the browser address bar visible when introducing the live app and repository.
- [ ] Do not open DataHub credentials, API headers, internal endpoints, logs, receipts, evidence
      directories, or cloud consoles.
- [ ] Do not use copyrighted music or third-party footage.

### Rehearsal

- [ ] Read the narration aloud once and keep it below 2:45.
- [ ] Click the campaign button only once. The public endpoint is single-flight and rejects a
      concurrent run.
- [ ] Confirm a rehearsal ends with baseline 33.3%, improved 100%, three `EXACT` blast results,
      and **RESTORATION VERIFIED — all six table checksums match baseline**.
- [ ] Refresh before the final take so the result reveal happens on camera.

## Exact recording sequence

### 0:00-0:16 — Problem and product

**Screen:** Live app hero, with the public URL visible.

**Narration:**

> Passing pipelines can still ship silent failures: a 100x unit change, stale data, or broken join
> keys. Lineage Fuzzer uses DataHub to break an isolated copy safely and prove whether today's
> controls catch those failures.

### 0:16-0:42 — Prove live DataHub context

**Screen:** Point to **Current live DataHub context verified**, the approval digest, the six-node
graph, and the footer values `datahub-mcp-live` and the current candidate.

**Narration:**

> This plan is bound to live open-source DataHub context captured through the DataHub MCP Server:
> six datasets, complete schemas, five lineage edges, ownership, sandbox metadata, and three
> existing assertions. Incomplete, stale, foreign, or local-only context disables the run.

### 0:42-1:00 — Preview the campaign and safety boundary

**Screen:** Point to the three fault cards: 100x unit scale, 45-day stale partition, and 10%
customer-key null surge. Keep the graph visible.

**Narration:**

> One fixed seed creates three semantic faults against only the allowlisted DuckDB fixture.
> DataHub lineage predicts which downstream tables should change, and the manifest digest is the
> approval. Every fault restores before the next begins.

### 1:00-1:08 — Approve once

**Screen:** Click **Approve + run campaign** once. Show the button change to
**Running + restoring...**.

**Narration:**

> I am approving this exact digest. Injection is default-deny, path- and namespace-bound, and
> single-flight.

### 1:08-1:38 — Explain the work while it runs

**Screen:** Stay on the live application while the campaign executes.

**Narration:**

> For each fault, Lineage Fuzzer snapshots the fixture, mutates deterministic rows, rebuilds the
> downstream tables, compares observed checksums with the lineage prediction, runs the controls
> captured from DataHub, and restores in a finally path. It then selects two predesigned read-only
> SQL controls for the measured gaps and repeats the identical campaign.

If the result appears early, pause on the complete matrix rather than rushing ahead.

### 1:38-2:11 — Show measured improvement and restoration

**Screen:** The page scrolls to the result panel. Point, in order, to:

1. **Baseline coverage: 33.3% — 1 of 3 faults detected**
2. **Improved coverage: 100.0% — 3 of 3 faults detected**
3. The three matrix rows, each with an improved detection and `EXACT`
4. The emitted SQL artifact path
5. **RESTORATION VERIFIED — all six table checksums match baseline**

**Narration:**

> The cataloged controls catch only the null surge: one out of three. The emitted controls catch
> the scale and staleness gaps, so the same seed reaches three out of three. Every observed blast
> radius exactly matches the DataHub prediction, and all six table checksums return to baseline.

### 2:11-2:31 — Show the runnable artifact

**Screen:** Switch to the pre-opened public GitHub SQL file. Point to the two control IDs, the
read-only `SELECT`, and the approved `raw.orders` table.

**Narration:**

> This is the emitted artifact judges can inspect and run: two predesigned read-only SQL controls
> validated on clean data and executed against the two missed faults. The repository also includes
> the manifest and before-and-after coverage examples.

### 2:31-2:44 — Close on restored proof

**Screen:** Return to the app, keep the restoration line visible, then scroll to the separate
live-proof card if timing allows.

**Narration:**

> The campaign evidence is immutable, the fixture is restored, and a separate approval-bound
> custom-assertion transaction proves DataHub writeback, re-read, isolation, and restoration.
> Lineage Fuzzer breaks data safely before bad data breaks production.

Stop the recording by 2:55 even if there is unused narration.

## If the live run does not complete

- If the button is disabled, stop. Do not present local fixture mode as live evidence.
- If the app reports a stale context or readiness error, stop and ask the coordinator to restore
  the verified public state. Do not run catalog reset or seed operations during recording.
- If the app reports that a campaign is already running, wait for that single flight to finish,
  refresh, verify the live labels again, and start a new take.
- If any campaign row shows `DIFF`, coverage is not 33.3% to 100%, or restoration is not verified,
  stop the take. Preserve the failure for diagnosis; do not edit around it or substitute static
  output.
- If the run takes longer than the recording budget, capture a new continuous take after the
  service is healthy. Do not speed up the result footage or imply that a cached file was a fresh
  execution.

## Final video check

- [ ] Total duration is below 3:00; target is 2:45.
- [ ] The application visibly functions on camera.
- [ ] The public application and repository URLs are readable.
- [ ] `datahub-mcp-live`, three faults, 33.3% to 100% coverage, three `EXACT` results, emitted SQL,
      and restoration are legible.
- [ ] The narration distinguishes live DataHub context, isolated DuckDB mutations, and the
      separate restored DataHub writeback proof.
- [ ] No secret, private URL, receipt path, cloud console, terminal history, notification, or
      unrelated project is visible.
- [ ] Captions are corrected for DataHub, MCP, DuckDB, Lineage Fuzzer, and `proved_and_restored`.
- [ ] The upload is public on YouTube, Vimeo, or Youku and plays without authentication.
- [ ] The Devpost entry uses the final copy in `SUBMISSION.md`.

## Repository evidence shown or linked

| Evidence | Public path |
|---|---|
| Seeded campaign | [`examples/campaign-manifest.json`](../examples/campaign-manifest.json) |
| Baseline 1/3 | [`examples/baseline-coverage.json`](../examples/baseline-coverage.json) |
| Emitted SQL | [`examples/generated/lineage_fuzzer_generated_controls.sql`](../examples/generated/lineage_fuzzer_generated_controls.sql) |
| Improved 3/3 | [`examples/final-coverage.json`](../examples/final-coverage.json) |
| Full restored report | [`examples/campaign-report.json`](../examples/campaign-report.json) |

These repository examples are deterministic local evidence and are labeled
`local-fixture-topology`. The public page's current campaign plan is separately bound to
`datahub-mcp-live`; do not blur the two.
