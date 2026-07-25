from __future__ import annotations

from pathlib import Path

import pytest

from lineage_fuzzer.allocation import (
    AllocationViolation,
    validate_allocation_settings,
    validate_assertion_urn,
    validate_dataset_urn,
)
from lineage_fuzzer.config import Settings


def make_settings(workspace: Path) -> Settings:
    fixture_root = workspace / "demo" / "fixtures" / "lineage-fuzzer"
    return Settings(
        PROJECT_SLUG="lineage-fuzzer",
        APP_STATE_DIR=workspace / ".lineage-fuzzer",
        DEMO_FIXTURE_ROOT=fixture_root,
        LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS=str(
            fixture_root / "lineage_fuzzer.duckdb"
        ),
        DATAHUB_DOMAIN="Demo / Lineage Fuzzer",
        DATAHUB_PROJECT_TAG="project-lineage-fuzzer",
        DATAHUB_URN_PREFIX="fuzzer.",
    )


def test_accepts_exact_coordinator_allocation(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)

    database_path = validate_allocation_settings(settings, workspace_root=tmp_path)

    assert database_path == (
        tmp_path / "demo" / "fixtures" / "lineage-fuzzer" / "lineage_fuzzer.duckdb"
    ).resolve()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("DATAHUB_DOMAIN", "Demo / Other Project"),
        ("DATAHUB_PROJECT_TAG", "project-other"),
        ("DATAHUB_URN_PREFIX", "other."),
        ("PROJECT_SLUG", "other-project"),
    ],
)
def test_rejects_allocation_mismatch(tmp_path: Path, field: str, value: str) -> None:
    aliases = {
        "PROJECT_SLUG": "project_slug",
        "DATAHUB_DOMAIN": "datahub_domain",
        "DATAHUB_PROJECT_TAG": "datahub_project_tag",
        "DATAHUB_URN_PREFIX": "datahub_urn_prefix",
    }
    settings = make_settings(tmp_path).model_copy(update={aliases[field]: value})

    with pytest.raises(AllocationViolation, match="coordinator contract"):
        validate_allocation_settings(settings, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "urn",
    [
        "urn:li:dataset:(urn:li:dataPlatform:snowflake,fuzzer.raw.orders,DEV)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,other.raw.orders,DEV)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.orders,PROD)",
        "urn:li:chart:fuzzer.raw.orders",
    ],
)
def test_rejects_dataset_outside_platform_prefix_or_environment(
    tmp_path: Path,
    urn: str,
) -> None:
    with pytest.raises(AllocationViolation):
        validate_dataset_urn(urn, make_settings(tmp_path))


def test_assertion_urn_must_use_project_prefix(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)

    validate_assertion_urn("urn:li:assertion:fuzzer.live-proof", settings)

    with pytest.raises(AllocationViolation, match="allocated URN prefix"):
        validate_assertion_urn("urn:li:assertion:other.live-proof", settings)
