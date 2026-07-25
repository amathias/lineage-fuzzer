from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from lineage_fuzzer.api import create_app
from lineage_fuzzer.campaign.context import save_live_context_snapshot
from lineage_fuzzer.config import Settings
from lineage_fuzzer.pipeline import CommerceFixture
from lineage_fuzzer.readiness import ReadinessCheck, ReadinessReport, ReadinessService
from tests.live_contract import (
    capture_pinned_context,
    prepare_bound_runtime,
)
from tests.live_contract import (
    make_settings as make_live_settings,
)


@dataclass
class FakeProbe:
    ready: bool = True
    missing_tools: tuple[str, ...] = ()


class FakeMCP:
    def __init__(self, entity: dict[str, Any], *, ready: bool = True) -> None:
        self.entity = entity
        self.ready = ready
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def probe(self) -> FakeProbe:
        return FakeProbe(
            ready=self.ready,
            missing_tools=() if self.ready else ("list_schema_fields",),
        )

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        return {"entities": [self.entity]}


class FakeGraphQL:
    def __init__(self) -> None:
        self.probe_count = 0

    async def __aenter__(self) -> FakeGraphQL:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def probe(self) -> dict[str, Any]:
        self.probe_count += 1
        return {"__typename": "Query"}


class StubReadiness:
    def __init__(self, report: ReadinessReport) -> None:
        self.report = report

    async def check(self) -> ReadinessReport:
        return self.report


@pytest.fixture(scope="module")
def seeded_workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    workspace = tmp_path_factory.mktemp("readiness")
    fixture_root = workspace / "demo" / "fixtures" / "lineage-fuzzer"
    state_dir = workspace / ".lineage-fuzzer"
    state_dir.mkdir()
    CommerceFixture(
        fixture_root / "lineage_fuzzer.duckdb",
        fixture_root=fixture_root,
    ).seed(seed=20260724)
    return workspace


def make_settings(workspace: Path, *, credential_available: bool = True) -> Settings:
    fixture_root = workspace / "demo" / "fixtures" / "lineage-fuzzer"
    return Settings(
        PROJECT_SLUG="lineage-fuzzer",
        APP_ENV="development",
        APP_STATE_DIR=workspace / ".lineage-fuzzer",
        DEMO_FIXTURE_ROOT=fixture_root,
        LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS=str(
            fixture_root / "lineage_fuzzer.duckdb"
        ),
        DATAHUB_GMS_URL="http://127.0.0.1:8080",
        DATAHUB_MCP_URL="http://127.0.0.1:8000/mcp",
        DATAHUB_TOKEN="unit-test-only-placeholder" if credential_available else None,
        DATAHUB_DOMAIN="Demo / Lineage Fuzzer",
        DATAHUB_PROJECT_TAG="project-lineage-fuzzer",
        DATAHUB_URN_PREFIX="fuzzer.",
    )


def catalog_entity(settings: Settings) -> dict[str, Any]:
    return {
        "urn": settings.readiness_dataset_urn,
        "domain": {"properties": {"name": settings.datahub_domain}},
        "tags": [
            {"tag": {"name": settings.datahub_project_tag}},
            {"tag": {"name": settings.required_sandbox_tag}},
        ],
        "properties": {
            "customProperties": [
                {
                    "key": settings.required_marker_key,
                    "value": settings.required_marker_value,
                }
            ]
        },
    }


@pytest.mark.asyncio
async def test_ready_only_after_local_remote_and_catalog_checks(
    seeded_workspace: Path,
) -> None:
    settings = make_settings(seeded_workspace)
    mcp = FakeMCP(catalog_entity(settings))
    graphql = FakeGraphQL()
    service = ReadinessService(
        settings,
        workspace_root=seeded_workspace,
        mcp_factory=lambda _: mcp,
        graphql_factory=lambda _: graphql,
    )

    report = await service.check()

    assert report.ready
    assert set(report.checks) == {
        "allocation",
        "state",
        "fixture",
        "gms",
        "mcp",
        "catalog_allocation",
        "campaign_context",
    }
    assert all(check.ready for check in report.checks.values())
    assert mcp.calls == [
        ("get_entities", {"urns": [settings.readiness_dataset_urn]})
    ]
    assert graphql.probe_count == 1


@pytest.mark.asyncio
async def test_missing_token_fails_without_attempting_remote_clients(
    seeded_workspace: Path,
) -> None:
    settings = make_settings(seeded_workspace, credential_available=False)

    def unexpected_mcp(_: Settings) -> FakeMCP:
        raise AssertionError("MCP must not be attempted without a credential")

    def unexpected_graphql(_: Settings) -> FakeGraphQL:
        raise AssertionError("GraphQL must not be attempted without a credential")

    report = await ReadinessService(
        settings,
        workspace_root=seeded_workspace,
        mcp_factory=unexpected_mcp,
        graphql_factory=unexpected_graphql,
    ).check()

    assert not report.ready
    assert report.checks["gms"].detail.startswith("DATAHUB_TOKEN is required")
    assert report.checks["mcp"].detail.startswith("DATAHUB_TOKEN is required")
    assert not report.checks["catalog_allocation"].ready


@pytest.mark.asyncio
async def test_catalog_entity_without_sandbox_marker_fails_closed(
    seeded_workspace: Path,
) -> None:
    settings = make_settings(seeded_workspace)
    entity = catalog_entity(settings)
    entity["properties"] = {"customProperties": []}
    report = await ReadinessService(
        settings,
        workspace_root=seeded_workspace,
        mcp_factory=lambda _: FakeMCP(entity),
        graphql_factory=lambda _: FakeGraphQL(),
    ).check()

    assert not report.ready
    assert not report.checks["catalog_allocation"].ready


@pytest.mark.asyncio
async def test_wrong_project_prefix_fails_before_network(
    seeded_workspace: Path,
) -> None:
    settings = make_settings(seeded_workspace).model_copy(
        update={"datahub_urn_prefix": "other."}
    )
    report = await ReadinessService(
        settings,
        workspace_root=seeded_workspace,
    ).check()

    assert not report.ready
    assert not report.checks["allocation"].ready
    assert not report.checks["fixture"].ready


@pytest.mark.asyncio
async def test_hackathon_readiness_requires_live_context_receipt(
    seeded_workspace: Path,
) -> None:
    settings = make_settings(seeded_workspace).model_copy(
        update={
            "environment": "hackathon",
            "candidate_sha": "a" * 40,
        }
    )

    report = await ReadinessService(
        settings,
        workspace_root=seeded_workspace,
        mcp_factory=lambda _: FakeMCP(catalog_entity(settings)),
        graphql_factory=lambda _: FakeGraphQL(),
    ).check()

    assert not report.ready
    assert not report.checks["campaign_context"].ready


@pytest.mark.asyncio
async def test_hackathon_readiness_accepts_current_bound_live_context(
    tmp_path: Path,
) -> None:
    settings = make_live_settings(tmp_path, environment="hackathon").model_copy(
        update={"datahub_token": "unit-test-only-placeholder"}
    )
    prepare_bound_runtime(tmp_path, settings)
    context = await capture_pinned_context(tmp_path, settings)
    context_path = save_live_context_snapshot(
        tmp_path / ".lineage-fuzzer" / "campaign-context.json",
        context,
    )
    settings = settings.model_copy(update={"campaign_context_file": context_path})

    report = await ReadinessService(
        settings,
        workspace_root=tmp_path,
        mcp_factory=lambda _: FakeMCP(catalog_entity(settings)),
        graphql_factory=lambda _: FakeGraphQL(),
    ).check()

    assert report.ready
    assert report.checks["campaign_context"].ready
    assert "6 datasets and 5 edges" in report.checks["campaign_context"].detail

def test_readiness_endpoint_returns_200_only_for_ready_report() -> None:

    ready_report = ReadinessReport(
        status="ready",
        checks={"fixture": ReadinessCheck(ready=True, detail="verified")},
    )
    not_ready_report = ReadinessReport(
        status="not_ready",
        checks={"fixture": ReadinessCheck(ready=False, detail="missing")},
    )

    ready_response = TestClient(
        create_app(readiness_service=StubReadiness(ready_report))
    ).get("/api/readiness")
    not_ready_response = TestClient(
        create_app(readiness_service=StubReadiness(not_ready_report))
    ).get("/api/readiness")

    assert ready_response.status_code == 200
    assert ready_response.json()["status"] == "ready"
    assert not_ready_response.status_code == 503
    assert not_ready_response.json()["status"] == "not_ready"
