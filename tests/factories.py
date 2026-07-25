from __future__ import annotations

from pathlib import Path

from lineage_fuzzer.domain.models import (
    ApprovalReceipt,
    CampaignManifest,
    FaultKind,
    FaultSpecification,
    TargetDescriptor,
)

DATASET_URN = "urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.orders,DEV)"


def make_target(
    database_path: Path | str = "demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb",
) -> TargetDescriptor:
    return TargetDescriptor(
        urn=DATASET_URN,
        platform="duckdb",
        environment="DEV",
        database_path=database_path,
        schema_name="raw",
        table_name="orders",
        tags=frozenset({"project-lineage-fuzzer", "lineage-fuzzer-sandbox"}),
        custom_properties={"sandbox": "true"},
    )


def make_manifest(target: TargetDescriptor | None = None) -> CampaignManifest:
    selected_target = target or make_target()
    return CampaignManifest(
        campaign_id="019bdd2a-c340-7eb1-8e09-8d0eaef3129b",
        seed=20260724,
        graph_snapshot_sha256="a" * 64,
        targets=(selected_target,),
        faults=(
            FaultSpecification(
                fault_id="scale-orders",
                kind=FaultKind.NUMERIC_SCALE,
                target_urn=selected_target.urn,
                parameters={"column": "amount", "factor": 100},
                restore_action="restore_snapshot",
            ),
        ),
        created_at="2026-07-24T12:00:00Z",
    )


def make_approval(manifest: CampaignManifest) -> ApprovalReceipt:
    return ApprovalReceipt.for_manifest(manifest, approved_by="test-user")
