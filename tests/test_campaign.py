from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from lineage_fuzzer.campaign.context import (
    DAILY_REVENUE_URN,
    RAW_ORDERS_URN,
    ContextCaptureError,
    demo_context_snapshot,
    downstream_blast_radius,
)
from lineage_fuzzer.campaign.generation import (
    GeneratedSQLViolation,
    validate_generated_sql,
)
from lineage_fuzzer.campaign.runner import (
    CampaignExecutionError,
    CampaignRunner,
)
from lineage_fuzzer.config import Settings
from lineage_fuzzer.safety import SafetyViolation
from tests.live_contract import (
    capture_pinned_context,
    make_settings,
    prepare_bound_runtime,
)


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
    run_directories = [
        path
        for path in (tmp_path / "examples").iterdir()
        if path.is_dir() and path.name != "generated"
    ]
    assert len(run_directories) == 1
    assert {
        "campaign-manifest.json",
        "baseline-coverage.json",
        "final-coverage.json",
        "campaign-report.json",
        "generated",
    } == {path.name for path in run_directories[0].iterdir()}


    assert (
        run_directories[0] / "generated" / "lineage_fuzzer_generated_controls.sql"
    ).is_file()


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


def test_campaign_evidence_refuses_nonidentical_overwrite(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    runner.run(approval_sha256=runner.plan().sha256)
    run_directory = next(
        path
        for path in (tmp_path / "examples").iterdir()
        if path.is_dir() and path.name != "generated"
    )
    report_path = run_directory / "campaign-report.json"
    report_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(CampaignExecutionError, match="non-identical immutable"):
        runner.run(approval_sha256=runner.plan().sha256)


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


def test_live_context_derives_baseline_controls_from_captured_assertions(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    prepare_bound_runtime(tmp_path, settings)
    context = asyncio.run(capture_pinned_context(tmp_path, settings))

    runner = CampaignRunner(
        settings,
        context,
        workspace_root=tmp_path,
        artifact_root=tmp_path / "generated",
        evidence_root=tmp_path / "evidence",
    )

    assert tuple(control.control_id for control in runner.baseline_controls) == (
        "orders_customer_id_not_null",
        "orders_order_id_unique",
        "daily_revenue_non_negative",
    )


def test_live_context_rejects_contradictory_baseline_control_mapping(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    prepare_bound_runtime(tmp_path, settings)
    context = asyncio.run(capture_pinned_context(tmp_path, settings))
    forged_assertions = list(context.assertions)
    forged_assertions[0] = {
        **forged_assertions[0],
        "logic": "SELECT 0",
    }
    forged = context.model_copy(update={"assertions": tuple(forged_assertions)})

    with pytest.raises(ContextCaptureError, match="assertion metadata"):
        CampaignRunner(
            settings,
            forged,
            workspace_root=tmp_path,
            artifact_root=tmp_path / "generated",
            evidence_root=tmp_path / "evidence",
        )
