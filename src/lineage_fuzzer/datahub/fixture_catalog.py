from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from lineage_fuzzer.allocation import (
    DATAHUB_DOMAIN,
    DATAHUB_PROJECT_TAG,
    PROJECT_SLUG,
    SANDBOX_TAG,
    AllocationViolation,
    validate_allocation_settings,
    validate_dataset_urn,
)
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.receipts import ReceiptStore, sha256_json

DATASET_URN = "urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.orders,DEV)"
DOMAIN_URN = "urn:li:domain:lineage-fuzzer"
PROJECT_TAG_URN = "urn:li:tag:project-lineage-fuzzer"
SANDBOX_TAG_URN = "urn:li:tag:lineage-fuzzer-sandbox"


class CatalogWriter(Protocol):
    async def upsert_aspect(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        aspect_name: str,
        value: dict[str, Any],
    ) -> dict[str, Any]: ...

    async def get_entity(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        aspect_names: tuple[str, ...],
    ) -> Any: ...


class CatalogFixtureService:
    """Seeds only the immutable Lineage Fuzzer DataHub catalog allocation."""

    def __init__(
        self,
        settings: Settings,
        client: CatalogWriter,
        *,
        workspace_root: Path,
    ) -> None:
        self.settings = settings
        self.client = client
        self.workspace_root = workspace_root.resolve()

    async def seed(
        self,
        *,
        approval_sha256: str,
        dataset_urn: str = DATASET_URN,
    ) -> dict[str, Any]:
        self._guard(dataset_urn, approval_sha256)
        operations = _canonical_operations(self.settings)
        for operation in operations:
            await self.client.upsert_aspect(**operation)

        observed = await self.client.get_entity(
            entity_type="dataset",
            entity_urn=dataset_urn,
            aspect_names=("datasetProperties", "globalTags", "domains", "status"),
        )
        validate_observed_dataset(observed, self.settings, dataset_urn)

        plan = catalog_plan(self.settings)
        plan_sha = sha256_json(plan)
        receipt = {
            **plan,
            "status": "verified",
            "required_metadata": {
                "domain": DATAHUB_DOMAIN,
                "project_tag": DATAHUB_PROJECT_TAG,
                "sandbox_tag": SANDBOX_TAG,
                "sandbox": "true",
            },
        }
        store = ReceiptStore(
            self.settings.state_dir,
            workspace_root=self.workspace_root,
            run_id=f"catalog-{plan_sha[:16]}",
        )
        path = store.write("catalog", plan_sha256=plan_sha, payload=receipt)
        return {**receipt, "receipt_path": str(path)}

    async def reset(
        self,
        *,
        approval_sha256: str,
        dataset_urn: str = DATASET_URN,
    ) -> dict[str, Any]:
        return await self.seed(
            approval_sha256=approval_sha256,
            dataset_urn=dataset_urn,
        )

    def _guard(self, dataset_urn: str, approval_sha256: str) -> None:
        validate_allocation_settings(self.settings, workspace_root=self.workspace_root)
        validate_dataset_urn(dataset_urn, self.settings)
        if dataset_urn != DATASET_URN or dataset_urn != self.settings.readiness_dataset_urn:
            raise AllocationViolation(
                "catalog mutation target is not the exact allocated readiness dataset"
            )
        if self.settings.required_marker_key != "sandbox":
            raise AllocationViolation("sandbox marker key differs from coordinator contract")
        if self.settings.required_marker_value.casefold() != "true":
            raise AllocationViolation("sandbox marker value differs from coordinator contract")
        if approval_sha256 != sha256_json(catalog_plan(self.settings)):
            raise AllocationViolation(
                "approval SHA-256 does not match the immutable catalog fixture plan"
            )


def catalog_plan(settings: Settings) -> dict[str, Any]:
    operations = _canonical_operations(settings)
    return {
        "operation": "seed_datahub_fixture",
        "dataset_urn": DATASET_URN,
        "domain_urn": DOMAIN_URN,
        "tag_urns": [PROJECT_TAG_URN, SANDBOX_TAG_URN],
        "aspects": [
            {
                "entity_type": operation["entity_type"],
                "entity_urn": operation["entity_urn"],
                "aspect_name": operation["aspect_name"],
                "value": operation["value"],
            }
            for operation in operations
        ],
    }


def _canonical_operations(settings: Settings) -> list[dict[str, Any]]:
    description = "Disposable Lineage Fuzzer hackathon fixture."
    return [
        {
            "entity_type": "domain",
            "entity_urn": DOMAIN_URN,
            "aspect_name": "domainProperties",
            "value": {
                "customProperties": {"project_slug": PROJECT_SLUG},
                "name": DATAHUB_DOMAIN,
                "description": description,
            },
        },
        {
            "entity_type": "tag",
            "entity_urn": PROJECT_TAG_URN,
            "aspect_name": "tagProperties",
            "value": {
                "name": DATAHUB_PROJECT_TAG,
                "description": "Lineage Fuzzer project allocation.",
            },
        },
        {
            "entity_type": "tag",
            "entity_urn": SANDBOX_TAG_URN,
            "aspect_name": "tagProperties",
            "value": {
                "name": SANDBOX_TAG,
                "description": "Explicitly disposable Lineage Fuzzer sandbox.",
            },
        },
        {
            "entity_type": "dataset",
            "entity_urn": DATASET_URN,
            "aspect_name": "datasetProperties",
            "value": {
                "customProperties": {
                    settings.required_marker_key: settings.required_marker_value,
                    "project_slug": PROJECT_SLUG,
                },
                "name": "fuzzer.raw.orders",
                "description": description,
                "tags": [],
            },
        },
        {
            "entity_type": "dataset",
            "entity_urn": DATASET_URN,
            "aspect_name": "globalTags",
            "value": {
                "tags": [
                    {"tag": PROJECT_TAG_URN},
                    {"tag": SANDBOX_TAG_URN},
                ]
            },
        },
        {
            "entity_type": "dataset",
            "entity_urn": DATASET_URN,
            "aspect_name": "domains",
            "value": {"domains": [DOMAIN_URN]},
        },
        {
            "entity_type": "dataset",
            "entity_urn": DATASET_URN,
            "aspect_name": "status",
            "value": {"removed": False},
        },
    ]


def validate_observed_dataset(
    observed: Any,
    settings: Settings,
    dataset_urn: str,
) -> None:
    serialized = json.dumps(observed, sort_keys=True).casefold()
    required = (
        dataset_urn.casefold(),
        DOMAIN_URN.casefold(),
        PROJECT_TAG_URN.casefold(),
        SANDBOX_TAG_URN.casefold(),
        settings.required_marker_key.casefold(),
        settings.required_marker_value.casefold(),
    )
    if any(item not in serialized for item in required):
        raise AllocationViolation(
            "DataHub did not return the exact required dataset aspects after seed"
        )
    if '"removed": true' in serialized:
        raise AllocationViolation("seeded DataHub fixture remains soft-deleted")
