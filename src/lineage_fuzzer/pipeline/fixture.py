from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import duckdb

from lineage_fuzzer.pipeline.models import (
    ControlDefinition,
    ControlResult,
    FixtureEvidence,
    FixtureSnapshot,
    TableChecksum,
)

DEFAULT_FIXTURE_PATH = Path("demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb")
DEFAULT_SEED = 20260724

MANAGED_TABLES = (
    "raw.customers",
    "raw.orders",
    "staging.orders_enriched",
    "marts.daily_revenue",
    "marts.customer_value",
    "reporting.executive_dashboard",
)

BASELINE_CONTROLS = (
    ControlDefinition(
        control_id="orders_customer_id_not_null",
        description="Every raw order must identify its customer.",
        target_table="raw.orders",
        violation_query="SELECT count(*) FROM raw.orders WHERE customer_id IS NULL",
        detects_faults=("null_density_surge",),
    ),
    ControlDefinition(
        control_id="orders_order_id_unique",
        description="Every raw order identifier must be unique.",
        target_table="raw.orders",
        violation_query=(
            "SELECT count(*) FROM ("
            "SELECT order_id FROM raw.orders GROUP BY order_id HAVING count(*) > 1"
            ") AS duplicate_order_ids"
        ),
    ),
    ControlDefinition(
        control_id="daily_revenue_non_negative",
        description="Daily revenue must not fall below zero.",
        target_table="marts.daily_revenue",
        violation_query="SELECT count(*) FROM marts.daily_revenue WHERE revenue_cents < 0",
    ),
)


class FixtureBoundaryError(RuntimeError):
    """Raised when a fixture operation would leave the allocated project root."""


class FixtureRestoreError(RuntimeError):
    """Raised when a snapshot cannot reproduce its original checksums."""


class CommerceFixture:
    """Deterministic, disposable commerce fixture used by Lineage Fuzzer campaigns."""

    def __init__(
        self,
        database_path: str | Path = DEFAULT_FIXTURE_PATH,
        *,
        fixture_root: str | Path | None = None,
    ) -> None:
        root = Path(fixture_root) if fixture_root else DEFAULT_FIXTURE_PATH.parent
        self.fixture_root = root.resolve(strict=False)
        self.database_path = Path(database_path).resolve(strict=False)
        self._assert_within_root(self.database_path)

    def seed(self, *, seed: int = DEFAULT_SEED) -> FixtureEvidence:
        """Create clean source data and all downstream tables as one atomic replacement."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.database_path.with_suffix(".building.duckdb")
        self._assert_within_root(temporary_path)
        if temporary_path.exists():
            temporary_path.unlink()

        customers, orders = _generate_source_rows(seed)
        connection = duckdb.connect(str(temporary_path))
        try:
            connection.execute("CREATE SCHEMA raw")
            connection.execute("CREATE SCHEMA staging")
            connection.execute("CREATE SCHEMA marts")
            connection.execute("CREATE SCHEMA reporting")
            connection.execute("CREATE SCHEMA fixture_meta")

            connection.execute(
                """
                CREATE TABLE raw.customers (
                    customer_id INTEGER PRIMARY KEY,
                    customer_name VARCHAR NOT NULL,
                    segment VARCHAR NOT NULL,
                    country_code VARCHAR NOT NULL
                )
                """
            )
            connection.executemany(
                "INSERT INTO raw.customers VALUES (?, ?, ?, ?)",
                customers,
            )

            connection.execute(
                """
                CREATE TABLE raw.orders (
                    order_id INTEGER PRIMARY KEY,
                    customer_id INTEGER,
                    order_ts TIMESTAMP NOT NULL,
                    amount_cents BIGINT NOT NULL,
                    currency VARCHAR NOT NULL,
                    source_partition DATE NOT NULL
                )
                """
            )
            connection.executemany(
                "INSERT INTO raw.orders VALUES (?, ?, ?, ?, ?, ?)",
                orders,
            )
            connection.execute(
                """
                CREATE TABLE fixture_meta.seed_manifest (
                    seed BIGINT NOT NULL,
                    seeded_at TIMESTAMP NOT NULL,
                    sandbox_marker BOOLEAN NOT NULL,
                    project_slug VARCHAR NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT INTO fixture_meta.seed_manifest VALUES (?, ?, TRUE, ?)",
                [seed, datetime(2026, 7, 24, 12, 0, tzinfo=UTC), "lineage-fuzzer"],
            )
            self._build_transformations(connection)
            connection.execute("CHECKPOINT")
        finally:
            connection.close()

        os.replace(temporary_path, self.database_path)
        return self.evidence(seed=seed)

    def rebuild_transformations(self) -> None:
        with self._connect() as connection:
            self._build_transformations(connection)

    def evidence(self, *, seed: int | None = None) -> FixtureEvidence:
        self._require_database()
        actual_seed = seed if seed is not None else self._read_seed()
        return FixtureEvidence(
            seed=actual_seed,
            database_path=self.database_path,
            created_at=datetime.now(UTC),
            tables=self.table_checksums(),
        )

    def table_checksums(self) -> tuple[TableChecksum, ...]:
        self._require_database()
        with self._connect(read_only=True) as connection:
            return tuple(
                self._checksum_table(connection, table_name) for table_name in MANAGED_TABLES
            )

    def snapshot(self, *, snapshot_root: str | Path | None = None) -> FixtureSnapshot:
        self._require_database()
        checksums = self.table_checksums()
        seed = self._read_seed()
        snapshot_id = _snapshot_id(seed=seed, checksums=checksums)
        root = (
            Path(snapshot_root).resolve(strict=False)
            if snapshot_root
            else (self.fixture_root / ".snapshots").resolve(strict=False)
        )
        self._assert_within_root(root)
        root.mkdir(parents=True, exist_ok=True)
        backup_path = (root / f"{snapshot_id}.duckdb").resolve(strict=False)
        self._assert_within_root(backup_path)
        shutil.copy2(self.database_path, backup_path)
        return FixtureSnapshot(
            snapshot_id=snapshot_id,
            database_path=self.database_path,
            backup_path=backup_path,
            seed=seed,
            created_at=datetime.now(UTC),
            checksums=checksums,
        )

    def restore(self, snapshot: FixtureSnapshot) -> FixtureEvidence:
        database_path = snapshot.database_path.resolve(strict=False)
        backup_path = snapshot.backup_path.resolve(strict=False)
        self._assert_within_root(database_path)
        self._assert_within_root(backup_path)
        if database_path != self.database_path:
            raise FixtureBoundaryError("snapshot belongs to a different fixture database")
        if not backup_path.is_file():
            raise FixtureRestoreError(f"snapshot backup does not exist: {backup_path}")

        temporary_path = self.database_path.with_suffix(".restoring.duckdb")
        self._assert_within_root(temporary_path)
        shutil.copy2(backup_path, temporary_path)
        os.replace(temporary_path, self.database_path)
        evidence = self.evidence(seed=snapshot.seed)
        if evidence.checksum_map != snapshot.checksum_map:
            raise FixtureRestoreError("restored fixture checksums do not match the snapshot")
        return evidence

    @contextmanager
    def restored_campaign(self) -> Iterator[FixtureSnapshot]:
        """Restore the exact pre-campaign state, even if campaign execution raises."""
        snapshot = self.snapshot()
        try:
            yield snapshot
        finally:
            self.restore(snapshot)

    def run_controls(
        self,
        controls: tuple[ControlDefinition, ...] = BASELINE_CONTROLS,
    ) -> tuple[ControlResult, ...]:
        self._require_database()
        results: list[ControlResult] = []
        with self._connect(read_only=True) as connection:
            for control in controls:
                violation_count = int(connection.execute(control.violation_query).fetchone()[0])
                results.append(
                    ControlResult(
                        control_id=control.control_id,
                        target_table=control.target_table,
                        passed=violation_count == 0,
                        violation_count=violation_count,
                        detects_faults=control.detects_faults,
                    )
                )
        return tuple(results)

    def table_counts(self) -> dict[str, int]:
        self._require_database()
        with self._connect(read_only=True) as connection:
            return {
                table_name: int(
                    connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
                )
                for table_name in MANAGED_TABLES
            }

    def _build_transformations(self, connection: duckdb.DuckDBPyConnection) -> None:
        for table_name in reversed(MANAGED_TABLES[2:]):
            connection.execute(f"DROP TABLE IF EXISTS {table_name}")

        connection.execute(
            """
            CREATE TABLE staging.orders_enriched AS
            SELECT
                o.order_id,
                o.customer_id,
                c.customer_name,
                c.segment,
                c.country_code,
                o.order_ts,
                CAST(o.order_ts AS DATE) AS order_date,
                o.amount_cents,
                o.currency,
                o.source_partition
            FROM raw.orders AS o
            LEFT JOIN raw.customers AS c USING (customer_id)
            """
        )
        connection.execute(
            """
            CREATE TABLE marts.daily_revenue AS
            SELECT
                order_date,
                currency,
                count(*) AS order_count,
                sum(amount_cents)::BIGINT AS revenue_cents
            FROM staging.orders_enriched
            GROUP BY order_date, currency
            """
        )
        connection.execute(
            """
            CREATE TABLE marts.customer_value AS
            SELECT
                customer_id,
                customer_name,
                segment,
                country_code,
                count(*) AS order_count,
                sum(amount_cents)::BIGINT AS lifetime_value_cents,
                max(order_ts) AS last_order_ts
            FROM staging.orders_enriched
            GROUP BY customer_id, customer_name, segment, country_code
            """
        )
        connection.execute(
            """
            CREATE TABLE reporting.executive_dashboard AS
            SELECT
                count(*) AS active_customers,
                sum(order_count)::BIGINT AS total_orders,
                sum(lifetime_value_cents)::BIGINT AS total_revenue_cents,
                max(last_order_ts) AS latest_order_ts
            FROM marts.customer_value
            """
        )

    def _checksum_table(
        self,
        connection: duckdb.DuckDBPyConnection,
        table_name: str,
    ) -> TableChecksum:
        columns = [
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        ]
        order_clause = ", ".join(f'"{column}" NULLS FIRST' for column in columns)
        rows = connection.execute(f"SELECT * FROM {table_name} ORDER BY {order_clause}").fetchall()
        payload = {
            "table": table_name,
            "columns": columns,
            "rows": [[_canonical_value(value) for value in row] for row in rows],
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return TableChecksum(
            table_name=table_name,
            row_count=len(rows),
            sha256=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        )

    def _read_seed(self) -> int:
        with self._connect(read_only=True) as connection:
            row = connection.execute("SELECT seed FROM fixture_meta.seed_manifest").fetchone()
        if row is None:
            raise FixtureRestoreError("fixture seed manifest is missing")
        return int(row[0])

    def _connect(self, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.database_path), read_only=read_only)

    def _require_database(self) -> None:
        if not self.database_path.is_file():
            raise FileNotFoundError(f"fixture database does not exist: {self.database_path}")

    def _assert_within_root(self, path: Path) -> None:
        resolved = path.resolve(strict=False)
        if resolved != self.fixture_root and self.fixture_root not in resolved.parents:
            raise FixtureBoundaryError(
                f"fixture path must remain inside {self.fixture_root}: {resolved}"
            )


def _generate_source_rows(
    seed: int,
) -> tuple[list[tuple[int, str, str, str]], list[tuple[int, int, datetime, int, str, date]]]:
    rng = random.Random(seed)
    segments = ("enterprise", "mid_market", "small_business")
    countries = ("US", "CA", "GB", "DE")
    customers = [
        (
            customer_id,
            f"Customer {customer_id:03d}",
            segments[(customer_id - 1) % len(segments)],
            countries[(customer_id - 1) % len(countries)],
        )
        for customer_id in range(1, 31)
    ]

    start = datetime(2026, 7, 1, 8, 0)
    orders: list[tuple[int, int, datetime, int, str, date]] = []
    for order_id in range(1, 121):
        customer_id = rng.randint(1, len(customers))
        order_ts = start + timedelta(
            days=rng.randint(0, 13),
            hours=rng.randint(0, 11),
            minutes=rng.randint(0, 59),
        )
        amount_cents = rng.randint(1_500, 125_000)
        orders.append(
            (
                order_id,
                customer_id,
                order_ts,
                amount_cents,
                "USD",
                order_ts.date(),
            )
        )
    return customers, orders


def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return format(value, ".17g")
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _snapshot_id(*, seed: int, checksums: tuple[TableChecksum, ...]) -> str:
    payload = {
        "seed": seed,
        "tables": [checksum.model_dump(mode="json") for checksum in checksums],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
