from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from lineage_fuzzer.campaign.context import (
    DAILY_REVENUE_URN,
    RAW_ORDERS_URN,
    context_sha256,
    downstream_blast_radius,
)
from lineage_fuzzer.domain.models import (
    CampaignManifest,
    DataHubContextSnapshot,
    FaultKind,
    FaultSpecification,
    TargetDescriptor,
)

DEFAULT_CAMPAIGN_SEED = 20260724


def build_campaign_manifest(
    context: DataHubContextSnapshot,
    *,
    database_path: str | Path,
    seed: int = DEFAULT_CAMPAIGN_SEED,
) -> CampaignManifest:
    graph_sha256 = context_sha256(context)
    target = TargetDescriptor(
        urn=RAW_ORDERS_URN,
        platform="duckdb",
        environment="DEV",
        database_path=Path(database_path),
        schema_name="raw",
        table_name="orders",
        tags=frozenset({"project-lineage-fuzzer", "lineage-fuzzer-sandbox"}),
        custom_properties={"sandbox": "true"},
    )
    predicted = downstream_blast_radius(context, target.urn)
    null_predicted = tuple(urn for urn in predicted if urn != DAILY_REVENUE_URN)
    campaign_id = uuid5(
        NAMESPACE_URL,
        f"lineage-fuzzer:{seed}:{graph_sha256}:{target.urn}",
    )
    faults = (
        FaultSpecification(
            fault_id="scale-order-amounts-100x",
            kind=FaultKind.NUMERIC_SCALE,
            target_urn=target.urn,
            parameters={
                "column": "amount_cents",
                "factor": 100,
                "row_count": 12,
            },
            expected_affected_urns=predicted,
            restore_action="restore_snapshot",
        ),
        FaultSpecification(
            fault_id="stale-order-partitions-45d",
            kind=FaultKind.STALE_PARTITION,
            target_urn=target.urn,
            parameters={
                "timestamp_column": "order_ts",
                "partition_column": "source_partition",
                "days": 45,
                "row_count": 12,
            },
            expected_affected_urns=predicted,
            restore_action="restore_snapshot",
        ),
        FaultSpecification(
            fault_id="null-customer-density-10pct",
            kind=FaultKind.NULL_DENSITY_SURGE,
            target_urn=target.urn,
            parameters={
                "column": "customer_id",
                "row_count": 12,
            },
            expected_affected_urns=null_predicted,
            expected_control_urns=(
                "urn:li:assertion:fuzzer.control.orders-customer-id-not-null",
            ),
            restore_action="restore_snapshot",
        ),
    )
    return CampaignManifest(
        campaign_id=campaign_id,
        seed=seed,
        graph_snapshot_sha256=graph_sha256,
        targets=(target,),
        faults=faults,
        created_at=datetime(2026, 7, 25, 12, 0, tzinfo=UTC),
    )
