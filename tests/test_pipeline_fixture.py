from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from lineage_fuzzer.pipeline import (
    DEFAULT_SEED,
    CommerceFixture,
    FixtureBoundaryError,
)


def make_fixture(tmp_path: Path, name: str = "lineage_fuzzer.duckdb") -> CommerceFixture:
    fixture_root = tmp_path / "demo" / "fixtures" / "lineage-fuzzer"
    return CommerceFixture(fixture_root / name, fixture_root=fixture_root)


def test_seed_builds_expected_pipeline_and_clean_controls(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)

    evidence = fixture.seed()

    assert evidence.seed == DEFAULT_SEED
    assert fixture.table_counts() == {
        "raw.customers": 30,
        "raw.orders": 120,
        "staging.orders_enriched": 120,
        "marts.daily_revenue": 14,
        "marts.customer_value": 30,
        "reporting.executive_dashboard": 1,
    }
    results = fixture.run_controls()
    assert all(result.passed for result in results)
    assert {result.control_id for result in results} == {
        "orders_customer_id_not_null",
        "orders_order_id_unique",
        "daily_revenue_non_negative",
    }


def test_same_seed_has_identical_managed_table_checksums(tmp_path: Path) -> None:
    first = make_fixture(tmp_path, "first.duckdb")
    second = make_fixture(tmp_path, "second.duckdb")

    first_checksums = first.seed(seed=17).checksum_map
    second_checksums = second.seed(seed=17).checksum_map

    assert first_checksums == second_checksums


def test_different_seed_changes_source_and_downstream_checksums(tmp_path: Path) -> None:
    first = make_fixture(tmp_path, "first.duckdb")
    second = make_fixture(tmp_path, "second.duckdb")

    first_checksums = first.seed(seed=17).checksum_map
    second_checksums = second.seed(seed=18).checksum_map

    assert first_checksums["raw.customers"] == second_checksums["raw.customers"]
    assert first_checksums["raw.orders"] != second_checksums["raw.orders"]
    assert (
        first_checksums["reporting.executive_dashboard"]
        != second_checksums["reporting.executive_dashboard"]
    )


def test_snapshot_restore_returns_every_managed_table_to_exact_state(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    baseline = fixture.seed(seed=42)
    snapshot = fixture.snapshot()

    with duckdb.connect(str(fixture.database_path)) as connection:
        connection.execute(
            "UPDATE raw.orders SET amount_cents = amount_cents * 100 WHERE order_id <= 10"
        )
    fixture.rebuild_transformations()
    assert fixture.evidence().checksum_map != baseline.checksum_map

    restored = fixture.restore(snapshot)

    assert restored.checksum_map == baseline.checksum_map
    assert restored.checksum_map == snapshot.checksum_map


def test_restored_campaign_restores_after_exception(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    baseline = fixture.seed(seed=42)

    with pytest.raises(RuntimeError, match="campaign failed"), fixture.restored_campaign():
        with duckdb.connect(str(fixture.database_path)) as connection:
            connection.execute("UPDATE raw.orders SET customer_id = NULL WHERE order_id <= 12")
        fixture.rebuild_transformations()
        results = {result.control_id: result for result in fixture.run_controls()}
        assert results["orders_customer_id_not_null"].violation_count == 12
        raise RuntimeError("campaign failed")

    assert fixture.evidence().checksum_map == baseline.checksum_map


def test_fixture_rejects_database_outside_allocated_root(tmp_path: Path) -> None:
    fixture_root = tmp_path / "demo" / "fixtures" / "lineage-fuzzer"

    with pytest.raises(FixtureBoundaryError, match="must remain inside"):
        CommerceFixture(tmp_path / "other-project.duckdb", fixture_root=fixture_root)
