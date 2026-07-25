# Superseded

This historical supplement has been merged into COORDINATOR_HANDOFF.md. Do not update this file.

# Coordinator Handoff Supplement: Lineage Fuzzer Phase 1

This supplement records the current verified Phase 1 state while the workspace editor is unable
to patch the pre-existing `COORDINATOR_HANDOFF.md`. The fixed allocation in that file remains
authoritative.

## Verified milestone

| Field | Current value |
|---|---|
| Status | `in progress` |
| Milestone | Deterministic disposable commerce pipeline and verified restoration |
| Verified artifact | Local workspace; no Git commit assigned |
| Build command | `python -m pip install -e ".[dev]"` then `python -m pip install -r requirements-fixture.txt` |
| Test command | `python -m pytest` |
| Seed command | `python -m lineage_fuzzer.pipeline_cli seed` |
| Reset command | `python -m lineage_fuzzer.pipeline_cli seed` |
| Baseline controls | `python -m lineage_fuzzer.pipeline_cli controls` |
| Snapshot command | `python -m lineage_fuzzer.pipeline_cli snapshot` |
| Restore command | `python -m lineage_fuzzer.pipeline_cli restore <manifest.json>` |
| Run command | `lineage-fuzzer serve --port 8104` |
| Health endpoint | `GET /api/health` |
| Readiness endpoint | Not yet connected |
| Disposable fixture | `demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb` |
| Snapshot state | `demo/fixtures/lineage-fuzzer/.snapshots/` |
| DataHub read/write | Clients implemented; live verification awaits shared DataHub |
| Verification | 25 tests pass; Ruff passes |

## Implemented proof

- A fixed seed creates 30 customers, 120 orders, 14 daily-revenue rows, 30 customer-value rows,
  and one executive-dashboard summary.
- Canonical SHA-256 evidence covers all six managed source and downstream tables.
- Baseline controls deliberately cover the planned null-density fault but not the planned semantic
  scale or stale-partition faults.
- Snapshots are restricted to the coordinator-owned fixture root.
- Restore compares every managed-table checksum with the pre-campaign snapshot.
- An exception inside a campaign still restores the exact original checksums.

## Current deployment notes

- DuckDB is installed in the local project virtual environment.
- `requirements-fixture.txt` temporarily carries the DuckDB declaration because the workspace
  patch helper currently fails when modifying existing files. Move the same requirement into
  `pyproject.toml` once that editor issue clears.
- The generated `.duckdb` file and snapshots are disposable and ignored by source control.
- There are no workers or externally reachable services in this milestone.

## Next project-owned milestone

Implement the three seeded semantic fault adapters, before/after evidence, and campaign execution
that always runs within the existing safety gate and restoration context.

