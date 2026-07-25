from __future__ import annotations

import hashlib
import json
import random
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

import duckdb

from lineage_fuzzer.campaign.models import MutationEvidence
from lineage_fuzzer.domain.models import (
    ApprovalReceipt,
    CampaignManifest,
    FaultKind,
    FaultSpecification,
    TargetDescriptor,
)
from lineage_fuzzer.pipeline.fixture import CommerceFixture
from lineage_fuzzer.safety import SafetyGate


class FaultAdapterError(RuntimeError):
    """Raised when a fault request differs from its bounded deterministic contract."""


class FaultAdapter(ABC):
    kind: FaultKind

    def __init__(self, safety_gate: SafetyGate) -> None:
        self.safety_gate = safety_gate

    def apply(
        self,
        *,
        fixture: CommerceFixture,
        target: TargetDescriptor,
        specification: FaultSpecification,
        manifest: CampaignManifest,
        approval: ApprovalReceipt,
    ) -> MutationEvidence:
        if specification.kind is not self.kind:
            raise FaultAdapterError("fault specification was routed to the wrong adapter")
        safety = self.safety_gate.authorize(
            target=target,
            manifest=manifest,
            approval=approval,
        )
        if target.schema_name != "raw" or target.table_name != "orders":
            raise FaultAdapterError("fault adapter target is not the fixed raw.orders table")
        if fixture.database_path != safety.resolved_database_path:
            raise FaultAdapterError("fixture path differs from the safety-authorized target")
        return self._apply(
            fixture=fixture,
            specification=specification,
            manifest=manifest,
        )

    @abstractmethod
    def _apply(
        self,
        *,
        fixture: CommerceFixture,
        specification: FaultSpecification,
        manifest: CampaignManifest,
    ) -> MutationEvidence:
        raise NotImplementedError


class NumericScaleFaultAdapter(FaultAdapter):
    kind = FaultKind.NUMERIC_SCALE

    def _apply(
        self,
        *,
        fixture: CommerceFixture,
        specification: FaultSpecification,
        manifest: CampaignManifest,
    ) -> MutationEvidence:
        _require_exact_parameter(specification, "column", "amount_cents")
        factor = _integer_parameter(specification, "factor", minimum=2, maximum=1000)
        row_count = _integer_parameter(specification, "row_count", minimum=1, maximum=60)
        with duckdb.connect(str(fixture.database_path)) as connection:
            available = [
                int(row[0])
                for row in connection.execute(
                    "SELECT order_id FROM raw.orders ORDER BY order_id"
                ).fetchall()
            ]
            selected = _sample_ids(
                available,
                count=row_count,
                seed=_fault_seed(manifest.seed, specification.fault_id),
            )
            before = _fetch_rows(
                connection,
                "SELECT order_id, amount_cents FROM raw.orders",
                selected,
            )
            connection.execute(
                f"UPDATE raw.orders SET amount_cents = amount_cents * ? "
                f"WHERE order_id IN ({_placeholders(selected)})",
                [factor, *selected],
            )
            after = _fetch_rows(
                connection,
                "SELECT order_id, amount_cents FROM raw.orders",
                selected,
            )
        fixture.rebuild_transformations()
        return _mutation_evidence(specification, selected, before, after)


class StalePartitionFaultAdapter(FaultAdapter):
    kind = FaultKind.STALE_PARTITION

    def _apply(
        self,
        *,
        fixture: CommerceFixture,
        specification: FaultSpecification,
        manifest: CampaignManifest,
    ) -> MutationEvidence:
        _require_exact_parameter(specification, "timestamp_column", "order_ts")
        _require_exact_parameter(
            specification,
            "partition_column",
            "source_partition",
        )
        days = _integer_parameter(specification, "days", minimum=1, maximum=365)
        row_count = _integer_parameter(specification, "row_count", minimum=1, maximum=30)
        with duckdb.connect(str(fixture.database_path)) as connection:
            candidates = [
                int(row[0])
                for row in connection.execute(
                    """
                    SELECT order_id
                    FROM raw.orders
                    QUALIFY row_number() OVER (
                        PARTITION BY customer_id
                        ORDER BY order_ts DESC, order_id DESC
                    ) = 1
                    ORDER BY order_ts DESC, order_id DESC
                    """
                ).fetchall()
            ]
            selected = _sample_with_required_first(
                candidates,
                count=row_count,
                seed=_fault_seed(manifest.seed, specification.fault_id),
            )
            before = _fetch_rows(
                connection,
                "SELECT order_id, order_ts, source_partition FROM raw.orders",
                selected,
            )
            connection.execute(
                f"""
                UPDATE raw.orders
                SET
                    order_ts = order_ts - INTERVAL {days} DAY,
                    source_partition = source_partition - {days}
                WHERE order_id IN ({_placeholders(selected)})
                """,
                selected,
            )
            after = _fetch_rows(
                connection,
                "SELECT order_id, order_ts, source_partition FROM raw.orders",
                selected,
            )
        fixture.rebuild_transformations()
        return _mutation_evidence(specification, selected, before, after)


class NullDensityFaultAdapter(FaultAdapter):
    kind = FaultKind.NULL_DENSITY_SURGE

    def _apply(
        self,
        *,
        fixture: CommerceFixture,
        specification: FaultSpecification,
        manifest: CampaignManifest,
    ) -> MutationEvidence:
        _require_exact_parameter(specification, "column", "customer_id")
        row_count = _integer_parameter(specification, "row_count", minimum=1, maximum=60)
        with duckdb.connect(str(fixture.database_path)) as connection:
            available = [
                int(row[0])
                for row in connection.execute(
                    """
                    SELECT order_id
                    FROM raw.orders
                    WHERE customer_id IS NOT NULL
                    ORDER BY order_id
                    """
                ).fetchall()
            ]
            selected = _sample_ids(
                available,
                count=row_count,
                seed=_fault_seed(manifest.seed, specification.fault_id),
            )
            before = _fetch_rows(
                connection,
                "SELECT order_id, customer_id FROM raw.orders",
                selected,
            )
            connection.execute(
                f"UPDATE raw.orders SET customer_id = NULL "
                f"WHERE order_id IN ({_placeholders(selected)})",
                selected,
            )
            after = _fetch_rows(
                connection,
                "SELECT order_id, customer_id FROM raw.orders",
                selected,
            )
        fixture.rebuild_transformations()
        return _mutation_evidence(specification, selected, before, after)


def default_fault_adapters(safety_gate: SafetyGate) -> dict[FaultKind, FaultAdapter]:
    return {
        FaultKind.NUMERIC_SCALE: NumericScaleFaultAdapter(safety_gate),
        FaultKind.STALE_PARTITION: StalePartitionFaultAdapter(safety_gate),
        FaultKind.NULL_DENSITY_SURGE: NullDensityFaultAdapter(safety_gate),
    }


def _integer_parameter(
    specification: FaultSpecification,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = specification.parameters.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise FaultAdapterError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise FaultAdapterError(f"{name} is outside the fault adapter bounds")
    return value


def _require_exact_parameter(
    specification: FaultSpecification,
    name: str,
    expected: str,
) -> None:
    if specification.parameters.get(name) != expected:
        raise FaultAdapterError(f"{name} differs from the fixed adapter contract")


def _fault_seed(campaign_seed: int, fault_id: str) -> int:
    digest = hashlib.sha256(f"{campaign_seed}:{fault_id}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def _sample_ids(available: Sequence[int], *, count: int, seed: int) -> tuple[int, ...]:
    if count > len(available):
        raise FaultAdapterError("fault row_count exceeds available fixture rows")
    return tuple(sorted(random.Random(seed).sample(list(available), count)))


def _sample_with_required_first(
    available: Sequence[int],
    *,
    count: int,
    seed: int,
) -> tuple[int, ...]:
    if not available:
        raise FaultAdapterError("stale-partition fault found no candidate rows")
    if count > len(available):
        raise FaultAdapterError("fault row_count exceeds available fixture rows")
    required = available[0]
    remainder = random.Random(seed).sample(list(available[1:]), count - 1)
    return tuple(sorted((required, *remainder)))


def _fetch_rows(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    selected: tuple[int, ...],
) -> list[tuple[Any, ...]]:
    rows = connection.execute(
        f"{query} WHERE order_id IN ({_placeholders(selected)}) ORDER BY order_id",
        selected,
    ).fetchall()
    return [tuple(_canonical(value) for value in row) for row in rows]


def _placeholders(values: Sequence[object]) -> str:
    return ", ".join("?" for _ in values)


def _mutation_evidence(
    specification: FaultSpecification,
    selected: tuple[int, ...],
    before: list[tuple[Any, ...]],
    after: list[tuple[Any, ...]],
) -> MutationEvidence:
    before_sha = _rows_sha256(before)
    after_sha = _rows_sha256(after)
    if before_sha == after_sha:
        raise FaultAdapterError("fault mutation did not change the selected rows")
    return MutationEvidence(
        fault_id=specification.fault_id,
        kind=specification.kind,
        mutated_primary_keys=selected,
        before_values_sha256=before_sha,
        after_values_sha256=after_sha,
    )


def _rows_sha256(rows: list[tuple[Any, ...]]) -> str:
    serialized = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)
