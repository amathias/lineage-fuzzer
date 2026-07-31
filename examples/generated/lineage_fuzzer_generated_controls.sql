-- Generated from captured DataHub schema, measured gaps, and clean profile.
-- context_sha256=e7133a7bdf9c86fb6f4ab7acb4d18febb57fd66d622d3136daca814ea0581c86
-- manifest_sha256=c23afb443ca828c9d28cba90d96d988eb440a6ff109b6c59dcce7005a24c49a7
-- profile_sha256=6aedad8fef7c9fc1c974d7adb16f323f3826d74a3cd6eea56a3c82e8fc470c5d
-- Read-only DuckDB test artifact; zero violations means the control passes.
SELECT
    'orders_amount_cents_reasonable' AS control_id,
    count(*)::BIGINT AS violation_count
FROM raw.orders
WHERE "amount_cents" > 124365
UNION ALL
SELECT
    'orders_partition_not_stale' AS control_id,
    count(*)::BIGINT AS violation_count
FROM raw.orders
WHERE "source_partition" < DATE '2026-07-01'
ORDER BY control_id
