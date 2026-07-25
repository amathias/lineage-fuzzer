from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from lineage_fuzzer.allocation import AllocationViolation
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.catalog import DataHubCatalogClient
from lineage_fuzzer.datahub.fixture_catalog import (
    DATASET_URN,
    DOMAIN_URN,
    PROJECT_TAG_URN,
    SANDBOX_TAG_URN,
    CatalogFixtureService,
    catalog_plan,
)
from lineage_fuzzer.datahub.receipts import sha256_json


def _settings(workspace: Path) -> Settings:
    fixture_root = workspace / "demo" / "fixtures" / "lineage-fuzzer"
    state_dir = workspace / ".lineage-fuzzer"
    state_dir.mkdir()
    return Settings(
        PROJECT_SLUG="lineage-fuzzer",
        APP_STATE_DIR=state_dir,
        DEMO_FIXTURE_ROOT=fixture_root,
        LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS=str(
            fixture_root / "lineage_fuzzer.duckdb"
        ),
        DATAHUB_DOMAIN="Demo / Lineage Fuzzer",
        DATAHUB_PROJECT_TAG="project-lineage-fuzzer",
        DATAHUB_URN_PREFIX="fuzzer.",
    )


class FakeCatalog:
    def __init__(self) -> None:
        self.operations: list[dict[str, Any]] = []

    async def upsert_aspect(self, **operation: Any) -> dict[str, Any]:
        self.operations.append(operation)
        return {"ok": True}

    async def get_entity(self, **request: Any) -> Any:
        self.operations.append({"read": request})
        return [
            {
                "urn": DATASET_URN,
                "datasetProperties": {
                    "value": {
                        "customProperties": {
                            "sandbox": "true",
                            "project_slug": "lineage-fuzzer",
                        }
                    }
                },
                "globalTags": {
                    "value": {
                        "tags": [
                            {"tag": PROJECT_TAG_URN},
                            {"tag": SANDBOX_TAG_URN},
                        ]
                    }
                },
                "domains": {"value": {"domains": [DOMAIN_URN]}},
                "status": {"value": {"removed": False}},
            }
        ]


@pytest.mark.asyncio
async def test_openapi_client_uses_v3_aspect_wire_format() -> None:
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=[{"urn": DATASET_URN}])

    client = DataHubCatalogClient(
        "http://datahub.test/",
        token="not-a-real-token",
        transport=httpx.MockTransport(handler),
    )
    await client.upsert_aspect(
        entity_type="dataset",
        entity_urn=DATASET_URN,
        aspect_name="status",
        value={"removed": False},
    )
    await client.get_entity(
        entity_type="dataset",
        entity_urn=DATASET_URN,
        aspect_names=("status",),
    )
    await client.aclose()

    assert captured[0].url == "http://datahub.test/openapi/v3/entity/dataset?async=false"
    assert json.loads(captured[0].content) == [
        {
            "urn": DATASET_URN,
            "status": {
                "value": {"removed": False},
                "systemMetadata": None,
                "headers": {},
            },
        }
    ]
    assert captured[1].url == "http://datahub.test/openapi/v3/entity/dataset/batchGet"
    assert json.loads(captured[1].content) == [{"urn": DATASET_URN, "status": {}}]


@pytest.mark.asyncio
async def test_seeds_only_fixed_catalog_entities_and_writes_sanitized_receipt(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    catalog = FakeCatalog()
    service = CatalogFixtureService(settings, catalog, workspace_root=tmp_path)

    approval = sha256_json(catalog_plan(settings))
    result = await service.seed(approval_sha256=approval)

    writes = [operation for operation in catalog.operations if "entity_type" in operation]
    assert len(writes) == 7
    assert {operation["entity_urn"] for operation in writes} == {
        DATASET_URN,
        DOMAIN_URN,
        PROJECT_TAG_URN,
        SANDBOX_TAG_URN,
    }
    dataset_properties = next(
        operation["value"]
        for operation in writes
        if operation["aspect_name"] == "datasetProperties"
    )
    assert dataset_properties["customProperties"]["sandbox"] == "true"
    receipt = Path(result["receipt_path"]).read_text(encoding="utf-8")
    assert '"status": "verified"' in receipt
    assert "token" not in receipt.casefold()


@pytest.mark.asyncio
async def test_catalog_seed_rejects_foreign_namespace_before_network(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    catalog = FakeCatalog()
    service = CatalogFixtureService(settings, catalog, workspace_root=tmp_path)

    with pytest.raises(AllocationViolation):
        await service.seed(
            approval_sha256=sha256_json(catalog_plan(settings)),
            dataset_urn=(
                "urn:li:dataset:(urn:li:dataPlatform:duckdb,other.raw.orders,DEV)"
            )
        )

    assert catalog.operations == []


@pytest.mark.asyncio
async def test_catalog_reset_replays_canonical_aspects(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    catalog = FakeCatalog()
    service = CatalogFixtureService(settings, catalog, workspace_root=tmp_path)

    approval = sha256_json(catalog_plan(settings))
    first = await service.reset(approval_sha256=approval)
    second = await service.reset(approval_sha256=approval)

    assert first["status"] == second["status"] == "verified"
    writes = [operation for operation in catalog.operations if "entity_type" in operation]
    assert len(writes) == 14


@pytest.mark.asyncio
async def test_catalog_seed_requires_manifest_approval_before_network(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    catalog = FakeCatalog()
    service = CatalogFixtureService(settings, catalog, workspace_root=tmp_path)

    with pytest.raises(AllocationViolation, match="approval SHA-256"):
        await service.seed(approval_sha256="wrong")

    assert catalog.operations == []
