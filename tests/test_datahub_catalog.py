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
    CatalogFixtureService,
    catalog_plan,
    catalog_reset_plan,
    catalog_state_path,
)
from lineage_fuzzer.datahub.fixture_contract import (
    ALL_DATASET_URNS,
    BASELINE_ASSERTION_URNS,
    DOMAIN_URN,
    PROJECT_TAG_URN,
    SANDBOX_TAG_URN,
)
from lineage_fuzzer.datahub.receipts import sha256_json


def _settings(tmp_path: Path) -> Settings:
    fixture_root = tmp_path / "demo" / "fixtures" / "lineage-fuzzer"
    state_dir = tmp_path / ".lineage-fuzzer"
    state_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        PROJECT_SLUG="lineage-fuzzer",
        APP_ENV="test",
        APP_STATE_DIR=state_dir,
        DEMO_FIXTURE_ROOT=fixture_root,
        LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS=[
            str(fixture_root / "lineage_fuzzer.duckdb")
        ],
        LINEAGE_FUZZER_ALLOWED_ENVIRONMENTS=["DEV"],
        LINEAGE_FUZZER_ALLOWED_PLATFORMS=["duckdb"],
        DATAHUB_DOMAIN="Demo / Lineage Fuzzer",
        DATAHUB_PROJECT_TAG="project-lineage-fuzzer",
        DATAHUB_URN_PREFIX="fuzzer.",
        _env_file=None,
    )


class FakeDataHub:
    def __init__(self) -> None:
        self.entities: dict[str, dict[str, Any]] = {}
        self.assertions: dict[str, dict[str, Any]] = {}
        self.active_assertions: set[str] = set()
        self.operations: list[dict[str, Any]] = []
        self.fail_on_soft_delete: int | None = None
        self.soft_delete_calls = 0

    async def upsert_aspect(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        aspect_name: str,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        self.operations.append(
            {
                "entity_type": entity_type,
                "entity_urn": entity_urn,
                "aspect_name": aspect_name,
                "value": value,
            }
        )
        entity = self.entities.setdefault(entity_urn, {"urn": entity_urn})
        entity[aspect_name] = {"value": value}
        return {"urn": entity_urn}

    async def get_entity(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        aspect_names: tuple[str, ...],
    ) -> Any:
        self.operations.append(
            {
                "read": {
                    "entity_type": entity_type,
                    "entity_urn": entity_urn,
                    "aspect_names": aspect_names,
                }
            }
        )
        entity = self.entities.get(entity_urn, {"urn": entity_urn})
        return [
            {
                "urn": entity_urn,
                **{name: entity[name] for name in aspect_names if name in entity},
            }
        ]

    async def set_soft_deleted(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        removed: bool,
    ) -> dict[str, Any]:
        self.soft_delete_calls += 1
        if self.fail_on_soft_delete == self.soft_delete_calls:
            raise RuntimeError("synthetic token-free catalog failure")
        self.operations.append(
            {
                "soft_delete": {
                    "entity_type": entity_type,
                    "entity_urn": entity_urn,
                    "removed": removed,
                }
            }
        )
        if entity_type == "dataset":
            entity = self.entities.setdefault(entity_urn, {"urn": entity_urn})
            entity["status"] = {"value": {"removed": removed}}
        elif removed:
            self.active_assertions.discard(entity_urn)
        else:
            self.active_assertions.add(entity_urn)
        return {"urn": entity_urn}

    async def upsert_custom_assertion(
        self,
        *,
        assertion_urn: str,
        entity_urn: str,
        assertion_type: str,
        description: str,
        logic: str,
        field_path: str | None = None,
    ) -> Any:
        assert field_path is None
        self.operations.append(
            {
                "assertion_upsert": {
                    "assertion_urn": assertion_urn,
                    "entity_urn": entity_urn,
                    "assertion_type": assertion_type,
                    "description": description,
                    "logic": logic,
                }
            }
        )
        self.assertions[assertion_urn] = {
            "urn": assertion_urn,
            "info": {
                "type": "CUSTOM",
                "description": description,
                "customAssertion": {
                    "type": assertion_type,
                    "entityUrn": entity_urn,
                    "logic": logic,
                },
            },
        }
        return {"urn": assertion_urn}

    async def assertions_for_dataset(self, dataset_urn: str) -> dict[str, Any]:
        assertions = [
            value
            for urn, value in sorted(self.assertions.items())
            if urn in self.active_assertions
            and value["info"]["customAssertion"]["entityUrn"] == dataset_urn
        ]
        return {
            "dataset": {
                "urn": dataset_urn,
                "assertions": {
                    "total": len(assertions),
                    "assertions": assertions,
                },
            }
        }

    def add_preserved_proof_assertion(self) -> str:
        urn = "urn:li:assertion:fuzzer.catalog-proof.orders-nonempty"
        self.assertions[urn] = {
            "urn": urn,
            "info": {
                "type": "CUSTOM",
                "description": "Preserved proof baseline.",
                "customAssertion": {
                    "type": "lineage_fuzzer_catalog_proof_v1",
                    "entityUrn": ALL_DATASET_URNS[1],
                    "logic": "row_count > 0",
                },
            },
        }
        self.active_assertions.add(urn)
        return urn


@pytest.mark.asyncio
async def test_openapi_client_uses_exact_v3_aspect_wire_format() -> None:
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={})

    client = DataHubCatalogClient(
        "http://datahub.test/",
        token="not-a-real-token",
        transport=httpx.MockTransport(handler),
    )
    await client.upsert_aspect(
        entity_type="domain",
        entity_urn=DOMAIN_URN,
        aspect_name="domainProperties",
        value={"name": "Demo / Lineage Fuzzer"},
    )
    await client.get_entity(
        entity_type="dataset",
        entity_urn=ALL_DATASET_URNS[1],
        aspect_names=("schemaMetadata", "ownership", "upstreamLineage"),
    )
    await client.aclose()

    assert captured[0].url == "http://datahub.test/openapi/v3/entity/domain?async=false"
    body = json.loads(captured[0].content)
    assert body == [
        {
            "urn": DOMAIN_URN,
            "domainProperties": {
                "value": {"name": "Demo / Lineage Fuzzer"},
                "headers": {},
            },
        }
    ]
    assert "systemMetadata" not in body[0]["domainProperties"]
    assert captured[1].url == "http://datahub.test/openapi/v3/entity/dataset/batchGet"


def test_catalog_seed_plan_contains_exact_complete_contract(tmp_path: Path) -> None:
    plan = catalog_plan(_settings(tmp_path))

    assert plan["dataset_urns"] == list(ALL_DATASET_URNS)
    assert len(plan["lineage_edges"]) == 5
    assert len(plan["assertions"]) == 3
    assert len(plan["aspects"]) == 45
    assert sum(
        aspect["aspect_name"] == "schemaMetadata" for aspect in plan["aspects"]
    ) == 6
    assert sum(aspect["aspect_name"] == "ownership" for aspect in plan["aspects"]) == 6
    assert sum(
        aspect["aspect_name"] == "upstreamLineage" for aspect in plan["aspects"]
    ) == 6


@pytest.mark.asyncio
async def test_seed_is_idempotent_complete_and_sanitized(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    datahub = FakeDataHub()
    service = CatalogFixtureService(
        settings,
        datahub,
        datahub,
        workspace_root=tmp_path,
    )
    approval = sha256_json(catalog_plan(settings))

    first = await service.seed(approval_sha256=approval)
    second = await service.seed(approval_sha256=approval)

    assert first["status"] == second["status"] == "verified"
    assert set(datahub.active_assertions) == BASELINE_ASSERTION_URNS
    assert all(
        datahub.entities[urn]["status"]["value"]["removed"] is False
        for urn in ALL_DATASET_URNS
    )
    assert all(
        "schemaMetadata" in datahub.entities[urn]
        and "ownership" in datahub.entities[urn]
        and "upstreamLineage" in datahub.entities[urn]
        for urn in ALL_DATASET_URNS
    )
    state = json.loads(catalog_state_path(settings, tmp_path).read_text(encoding="utf-8"))
    assert state["status"] == "seeded"
    receipt = Path(second["receipt_path"]).read_text(encoding="utf-8")
    assert "token" not in receipt.casefold()


@pytest.mark.asyncio
async def test_reset_is_exact_idempotent_and_preserves_domain_tags_and_proof(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    datahub = FakeDataHub()
    service = CatalogFixtureService(
        settings,
        datahub,
        datahub,
        workspace_root=tmp_path,
    )
    await service.seed(approval_sha256=sha256_json(catalog_plan(settings)))
    proof_urn = datahub.add_preserved_proof_assertion()
    context_path = settings.state_dir / "campaign-context.json"
    context_path.write_text("{}\n", encoding="utf-8")
    context_path.with_name(f"{context_path.name}.receipt.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    approval = sha256_json(catalog_reset_plan(settings))

    first = await service.reset(approval_sha256=approval)
    second = await service.reset(approval_sha256=approval)

    assert first["status"] == second["status"] == "soft_deleted_and_verified"
    assert not context_path.exists()
    assert not context_path.with_name(f"{context_path.name}.receipt.json").exists()
    assert all(
        datahub.entities[urn]["status"]["value"]["removed"] is True
        for urn in ALL_DATASET_URNS
    )
    assert not (datahub.active_assertions & BASELINE_ASSERTION_URNS)
    assert proof_urn in datahub.active_assertions
    assert DOMAIN_URN in datahub.entities
    assert PROJECT_TAG_URN in datahub.entities
    assert SANDBOX_TAG_URN in datahub.entities
    assert Path(second["started_receipt_path"]).is_file()
    assert Path(second["completed_receipt_path"]).is_file()


@pytest.mark.asyncio
async def test_reset_partial_failure_records_failure_and_invalidates_context(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    datahub = FakeDataHub()
    service = CatalogFixtureService(
        settings,
        datahub,
        datahub,
        workspace_root=tmp_path,
    )
    await service.seed(approval_sha256=sha256_json(catalog_plan(settings)))
    context_path = settings.state_dir / "campaign-context.json"
    context_path.write_text("{}\n", encoding="utf-8")
    datahub.soft_delete_calls = 0
    datahub.fail_on_soft_delete = 2

    with pytest.raises(RuntimeError, match="synthetic"):
        await service.reset(
            approval_sha256=sha256_json(catalog_reset_plan(settings))
        )

    state = json.loads(catalog_state_path(settings, tmp_path).read_text(encoding="utf-8"))
    assert state["status"] == "reset_failed"
    assert not context_path.exists()
    failed_receipts = list(
        (settings.state_dir / "datahub-receipts").rglob("failed.json")
    )
    assert len(failed_receipts) == 1
    assert "synthetic" not in failed_receipts[0].read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_reseed_restores_all_tombstones_and_assertions(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    datahub = FakeDataHub()
    service = CatalogFixtureService(
        settings,
        datahub,
        datahub,
        workspace_root=tmp_path,
    )
    await service.seed(approval_sha256=sha256_json(catalog_plan(settings)))
    await service.reset(approval_sha256=sha256_json(catalog_reset_plan(settings)))

    result = await service.seed(approval_sha256=sha256_json(catalog_plan(settings)))

    assert result["status"] == "verified"
    assert set(datahub.active_assertions) == BASELINE_ASSERTION_URNS
    assert all(
        datahub.entities[urn]["status"]["value"]["removed"] is False
        for urn in ALL_DATASET_URNS
    )


@pytest.mark.asyncio
async def test_catalog_approval_mismatch_fails_before_network(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    datahub = FakeDataHub()
    service = CatalogFixtureService(
        settings,
        datahub,
        datahub,
        workspace_root=tmp_path,
    )

    with pytest.raises(AllocationViolation, match="approval SHA-256"):
        await service.seed(approval_sha256="0" * 64)

    assert datahub.operations == []


@pytest.mark.asyncio
async def test_foreign_runtime_namespace_fails_before_network(tmp_path: Path) -> None:
    settings = _settings(tmp_path).model_copy(update={"datahub_urn_prefix": "foreign."})
    datahub = FakeDataHub()
    service = CatalogFixtureService(
        settings,
        datahub,
        datahub,
        workspace_root=tmp_path,
    )

    with pytest.raises(AllocationViolation):
        await service.seed(approval_sha256=sha256_json(catalog_plan(settings)))

    assert datahub.operations == []
