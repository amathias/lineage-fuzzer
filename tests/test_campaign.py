from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lineage_fuzzer.campaign.context import (
    DAILY_REVENUE_URN,
    RAW_ORDERS_URN,
    LiveDataHubContextReader,
    demo_context_snapshot,
    downstream_blast_radius,
)
from lineage_fuzzer.campaign.generation import (
    GeneratedSQLViolation,
    validate_generated_sql,
)
from lineage_fuzzer.campaign.runner import CampaignRunner
from lineage_fuzzer.config import Settings
from lineage_fuzzer.safety import SafetyViolation


def _settings(workspace: Path) -> Settings:
    fixture_root = workspace / "demo" / "fixtures" / "lineage-fuzzer"
    state_dir = workspace / ".lineage-fuzzer"
    state_dir.mkdir(exist_ok=True)
    return Settings(
        PROJECT_SLUG="lineage-fuzzer",
        APP_ENV="test",
        APP_STATE_DIR=state_dir,
        DEMO_FIXTURE_ROOT=fixture_root,
        LINEAGE_FUZZER_INJECTION_ENABLED=True,
        LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS=[
            str(fixture_root / "lineage_fuzzer.duckdb")
        ],
        LINEAGE_FUZZER_ALLOWED_ENVIRONMENTS=["DEV"],
        LINEAGE_FUZZER_ALLOWED_PLATFORMS=["duckdb"],
        DATAHUB_DOMAIN="Demo / Lineage Fuzzer",
        DATAHUB_PROJECT_TAG="project-lineage-fuzzer",
        DATAHUB_URN_PREFIX="fuzzer.",
    )


def _runner(workspace: Path) -> CampaignRunner:
    return CampaignRunner(
        _settings(workspace),
        demo_context_snapshot(),
        workspace_root=workspace,
        artifact_root=workspace / "examples" / "generated",
        evidence_root=workspace / "examples",
    )


def test_campaign_proves_one_to_three_coverage_and_exact_restoration(
    tmp_path: Path,
) -> None:
    runner = _runner(tmp_path)
    manifest = runner.plan()

    report = runner.run(approval_sha256=manifest.sha256, approved_by="test")

    assert report.status == "proved_and_restored"
    assert report.manifest.sha256 == manifest.sha256
    assert report.baseline.detected_faults == 1
    assert report.baseline.coverage_percent == 33.3
    assert report.improved.detected_faults == 3
    assert report.improved.coverage_percent == 100.0
    assert report.restoration_verified is True
    assert report.final_checksums == report.baseline_checksums
    assert all(
        run.blast_radius.exact_match and run.restoration_verified
        for run in (*report.baseline.fault_runs, *report.improved.fault_runs)
    )
    assert {
        row.fault_id: row.detected for row in report.baseline.matrix
    } == {
        "scale-order-amounts-100x": False,
        "stale-order-partitions-45d": False,
        "null-customer-density-10pct": True,
    }
    assert all(row.detected for row in report.improved.matrix)
    assert report.generated_artifact.clean_execution_passed is True
    assert (
        tmp_path
        / "examples"
        / "generated"
        / "lineage_fuzzer_generated_controls.sql"
    ).is_file()
    assert {
        "campaign-manifest.json",
        "baseline-coverage.json",
        "final-coverage.json",
        "campaign-report.json",
    } <= {path.name for path in (tmp_path / "examples").iterdir()}


def test_identical_campaign_replays_fault_rows_scores_and_digest(tmp_path: Path) -> None:
    first_runner = _runner(tmp_path)
    first = first_runner.run(approval_sha256=first_runner.plan().sha256)
    second_runner = _runner(tmp_path)
    second = second_runner.run(approval_sha256=second_runner.plan().sha256)

    assert first.replay_sha256 == second.replay_sha256
    assert first.manifest.sha256 == second.manifest.sha256
    assert [
        run.mutation.mutated_primary_keys for run in first.baseline.fault_runs
    ] == [
        run.mutation.mutated_primary_keys for run in second.baseline.fault_runs
    ]
    assert first.baseline.matrix == second.baseline.matrix
    assert first.improved.matrix == second.improved.matrix


def test_campaign_rejects_wrong_approval_before_fixture_mutation(tmp_path: Path) -> None:
    runner = _runner(tmp_path)

    with pytest.raises(SafetyViolation, match="not bound"):
        runner.run(approval_sha256="f" * 64)

    assert not runner.database_path.exists()


@pytest.mark.parametrize(
    "sql",
    (
        "UPDATE raw.orders SET amount_cents = 0",
        "SELECT * FROM raw.orders; DELETE FROM raw.orders",
        "PRAGMA database_list",
        "SELECT 1",
    ),
)
def test_generated_sql_policy_rejects_mutating_or_unscoped_sql(sql: str) -> None:
    with pytest.raises(GeneratedSQLViolation):
        validate_generated_sql(sql)


def test_demo_context_predicts_all_downstream_consumers() -> None:
    predicted = downstream_blast_radius(demo_context_snapshot(), RAW_ORDERS_URN)

    assert RAW_ORDERS_URN in predicted
    assert DAILY_REVENUE_URN in predicted
    assert len(predicted) == 5


class _FakeMCP:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        if name == "get_entities":
            return [{"urn": RAW_ORDERS_URN, "owners": ["urn:li:corpuser:test"]}]
        if name == "list_schema_fields":
            return {
                "urn": RAW_ORDERS_URN,
                "fields": [{"fieldPath": "amount_cents", "nativeDataType": "BIGINT"}],
            }
        if name == "get_lineage":
            return {
                "downstreams": {
                    "searchResults": [
                        {"entity": {"urn": DAILY_REVENUE_URN}, "degree": 2}
                    ]
                }
            }
        raise AssertionError(name)


class _FakeAssertions:
    async def assertions_for_dataset(self, dataset_urn: str) -> dict[str, Any]:
        return {"dataset": {"urn": dataset_urn, "assertions": {"assertions": []}}}


@pytest.mark.asyncio
async def test_live_context_reader_uses_official_mcp_context_tools(
    tmp_path: Path,
) -> None:
    mcp = _FakeMCP()
    context = await LiveDataHubContextReader(
        _settings(tmp_path),
        mcp,
        _FakeAssertions(),
    ).capture()

    assert context.source == "datahub-mcp-live"
    assert context.lineage[0].upstream_urn == RAW_ORDERS_URN
    assert context.lineage[0].downstream_urn == DAILY_REVENUE_URN
    assert mcp.calls == [
        ("get_entities", {"urns": [RAW_ORDERS_URN]}),
        (
            "list_schema_fields",
            {"urn": RAW_ORDERS_URN, "limit": 100, "offset": 0},
        ),
        (
            "get_lineage",
            {
                "urn": RAW_ORDERS_URN,
                "upstream": False,
                "max_hops": 3,
                "max_results": 100,
                "offset": 0,
            },
        ),
    ]
