-- Generated deterministically from the raw.orders schema and campaign gaps.
-- Read-only DuckDB test artifact; zero violations means the control passes.
SELECT
    'orders_amount_cents_reasonable' AS control_id,
    count(*)::BIGINT AS violation_count
FROM raw.orders
WHERE amount_cents > 125000
UNION ALL
SELECT
    'orders_partition_not_stale' AS control_id,
    count(*)::BIGINT AS violation_count
FROM raw.orders
WHERE source_partition < DATE '2026-07-01'
ORDER BY control_id
