from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Protocol

from lineage_fuzzer.allocation import (
    DATAHUB_DOMAIN,
    DATAHUB_PROJECT_TAG,
    PROJECT_SLUG,
    SANDBOX_TAG,
    AllocationViolation,
    validate_allocation_settings,
    validate_assertion_urn,
    validate_dataset_urn,
)
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.fixture_contract import (
    ALL_DATASET_URNS,
    BASELINE_ASSERTION_URNS,
    BASELINE_ASSERTIONS,
    DEMO_LINEAGE,
    DOMAIN_URN,
    OWNER_URN,
    PROJECT_TAG_URN,
    RAW_ORDERS_URN,
    SANDBOX_TAG_URN,
    TABLE_URNS,
    assertion_payload,
    schema_metadata,
    upstreams_for,
)
from lineage_fuzzer.datahub.receipts import ReceiptStore, sha256_json

DATASET_URN = RAW_ORDERS_URN
CATALOG_STATE_FILENAME = "catalog-state.json"
CONTEXT_FILENAME = "campaign-context.json"


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

    async def set_soft_deleted(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        removed: bool,
    ) -> dict[str, Any]: ...


class AssertionWriter(Protocol):
    async def upsert_custom_assertion(
        self,
        *,
        assertion_urn: str,
        entity_urn: str,
        assertion_type: str,
        description: str,
        logic: str,
        field_path: str | None = None,
    ) -> Any: ...

    async def assertions_for_dataset(self, dataset_urn: str) -> dict[str, Any]: ...


class CatalogFixtureService:
    """Seed and reset only the immutable six-dataset Lineage Fuzzer allocation."""

    def __init__(
        self,
        settings: Settings,
        client: CatalogWriter,
        assertions: AssertionWriter,
        *,
        workspace_root: Path,
    ) -> None:
        self.settings = settings
        self.client = client
        self.assertions = assertions
        self.workspace_root = workspace_root.resolve()

    async def seed(self, *, approval_sha256: str) -> dict[str, Any]:
        plan = catalog_plan(self.settings)
        plan_sha = sha256_json(plan)
        self._guard(approval_sha256, plan_sha)
        self._invalidate_context()
        _write_catalog_state(
            self.settings,
            self.workspace_root,
            status="seeding",
            plan_sha256=plan_sha,
        )
        try:
            for operation in _canonical_operations(self.settings):
                await self.client.upsert_aspect(**operation)
            for spec in BASELINE_ASSERTIONS:
                await self.assertions.upsert_custom_assertion(
                    assertion_urn=spec.urn,
                    entity_urn=spec.entity_urn,
                    assertion_type=spec.assertion_type,
                    description=spec.description,
                    logic=spec.logic,
                )
                await self.client.set_soft_deleted(
                    entity_type="assertion",
                    entity_urn=spec.urn,
                    removed=False,
                )
            await self._verify_seeded()
        except Exception:
            _write_catalog_state(
                self.settings,
                self.workspace_root,
                status="seed_failed",
                plan_sha256=plan_sha,
            )
            raise

        state = _write_catalog_state(
            self.settings,
            self.workspace_root,
            status="seeded",
            plan_sha256=plan_sha,
        )
        receipt = {
            "operation": plan["operation"],
            "status": "verified",
            "plan_sha256": plan_sha,
            "catalog_state_sha256": sha256_json(state),
            "dataset_urns": list(ALL_DATASET_URNS),
            "lineage_edges": [edge.model_dump(mode="json") for edge in DEMO_LINEAGE],
            "assertion_urns": sorted(BASELINE_ASSERTION_URNS),
            "required_metadata": {
                "domain": DATAHUB_DOMAIN,
                "project_tag": DATAHUB_PROJECT_TAG,
                "sandbox_tag": SANDBOX_TAG,
                "owner": OWNER_URN,
                "sandbox": "true",
            },
        }
        store = ReceiptStore(
            self.settings.state_dir,
            workspace_root=self.workspace_root,
            run_id=f"catalog-seed-{plan_sha[:16]}",
        )
        path = store.write("catalog", plan_sha256=plan_sha, payload=receipt)
        return {**receipt, "receipt_path": str(path)}

    async def reset(self, *, approval_sha256: str) -> dict[str, Any]:
        plan = catalog_reset_plan(self.settings)
        plan_sha = sha256_json(plan)
        self._guard(approval_sha256, plan_sha)
        self._invalidate_context()
        _write_catalog_state(
            self.settings,
            self.workspace_root,
            status="resetting",
            plan_sha256=plan_sha,
        )
        store = ReceiptStore(
            self.settings.state_dir,
            workspace_root=self.workspace_root,
            run_id=f"catalog-reset-{plan_sha[:16]}",
        )
        started = {
            "status": "started",
            "dataset_urns": list(ALL_DATASET_URNS),
            "assertion_urns": sorted(BASELINE_ASSERTION_URNS),
        }
        started_path = store.write("started", plan_sha256=plan_sha, payload=started)
        existing_assertion_tombstones: set[str] = set()
        existing_dataset_tombstones: set[str] = set()
        written_assertion_tombstones: set[str] = set()
        written_dataset_tombstones: set[str] = set()
        try:
            (
                existing_assertion_tombstones,
                existing_dataset_tombstones,
            ) = await self._observed_reset_tombstones()
            for assertion_urn in sorted(BASELINE_ASSERTION_URNS):
                if assertion_urn in existing_assertion_tombstones:
                    continue
                await self.client.set_soft_deleted(
                    entity_type="assertion",
                    entity_urn=assertion_urn,
                    removed=True,
                )
                written_assertion_tombstones.add(assertion_urn)
            for dataset_urn in ALL_DATASET_URNS:
                if dataset_urn in existing_dataset_tombstones:
                    continue
                await self.client.set_soft_deleted(
                    entity_type="dataset",
                    entity_urn=dataset_urn,
                    removed=True,
                )
                written_dataset_tombstones.add(dataset_urn)
            await self._verify_reset()
        except Exception as exc:
            failed = {
                **started,
                "status": "failed",
                "error_type": type(exc).__name__,
            }
            failed_path = store.write("failed", plan_sha256=plan_sha, payload=failed)
            _write_catalog_state(
                self.settings,
                self.workspace_root,
                status="reset_failed",
                plan_sha256=plan_sha,
            )
            exc.sanitized_receipt_path = str(failed_path)
            raise

        state = _write_catalog_state(
            self.settings,
            self.workspace_root,
            status="reset",
            plan_sha256=plan_sha,
        )
        completed = {
            **started,
            "status": "soft_deleted_and_verified",
            "catalog_state_sha256": sha256_json(state),
            "retained_urns": [DOMAIN_URN, PROJECT_TAG_URN, SANDBOX_TAG_URN],
            "assertion_urns_already_tombstoned": sorted(
                existing_assertion_tombstones
            ),
            "dataset_urns_already_tombstoned": sorted(existing_dataset_tombstones),
            "assertion_tombstones_written": sorted(written_assertion_tombstones),
            "dataset_tombstones_written": sorted(written_dataset_tombstones),
        }
        completed_path = store.write(
            "completed",
            plan_sha256=plan_sha,
            payload=completed,
        )
        return {
            **completed,
            "started_receipt_path": str(started_path),
            "completed_receipt_path": str(completed_path),
        }

    async def _verify_seeded(self) -> None:
        for table_name, dataset_urn in TABLE_URNS.items():
            observed = await self.client.get_entity(
                entity_type="dataset",
                entity_urn=dataset_urn,
                aspect_names=(
                    "datasetProperties",
                    "globalTags",
                    "domains",
                    "ownership",
                    "schemaMetadata",
                    "upstreamLineage",
                    "status",
                ),
            )
            validate_observed_dataset(
                observed,
                self.settings,
                dataset_urn,
                table_name=table_name,
                removed=False,
            )
        await self._wait_for_assertions(
            {
                spec.urn: assertion_payload(spec) for spec in BASELINE_ASSERTIONS
            }
        )

    async def _verify_reset(self) -> None:
        for assertion_urn in sorted(BASELINE_ASSERTION_URNS):
            observed = await self.client.get_entity(
                entity_type="assertion",
                entity_urn=assertion_urn,
                aspect_names=("status",),
            )
            validate_observed_assertion_tombstone(observed, assertion_urn)
        for table_name, dataset_urn in TABLE_URNS.items():
            observed = await self.client.get_entity(
                entity_type="dataset",
                entity_urn=dataset_urn,
                aspect_names=("status",),
            )
            validate_observed_dataset(
                observed,
                self.settings,
                dataset_urn,
                table_name=table_name,
                removed=True,
                status_only=True,
            )

    async def _observed_reset_tombstones(self) -> tuple[set[str], set[str]]:
        assertions: set[str] = set()
        datasets: set[str] = set()
        for assertion_urn in sorted(BASELINE_ASSERTION_URNS):
            observed = await self.client.get_entity(
                entity_type="assertion",
                entity_urn=assertion_urn,
                aspect_names=("status",),
            )
            if _has_tombstone(observed, assertion_urn):
                assertions.add(assertion_urn)
        for dataset_urn in ALL_DATASET_URNS:
            observed = await self.client.get_entity(
                entity_type="dataset",
                entity_urn=dataset_urn,
                aspect_names=("status",),
            )
            if _has_tombstone(observed, dataset_urn):
                datasets.add(dataset_urn)
        return assertions, datasets

    async def _all_assertions(self) -> dict[str, dict[str, str]]:
        observed: dict[str, dict[str, str]] = {}
        for dataset_urn in ALL_DATASET_URNS:

            payload = await self.assertions.assertions_for_dataset(dataset_urn)
            for assertion in normalize_assertions(payload):
                urn = assertion["urn"]
                if urn in BASELINE_ASSERTION_URNS:
                    observed[urn] = assertion
                elif urn.startswith("urn:li:assertion:fuzzer.control."):
                    raise AllocationViolation(
                        "unexpected assertion exists inside the baseline control namespace"
                    )
        return observed

    async def _wait_for_assertions(
        self,
        expected: dict[str, dict[str, str]],
    ) -> None:
        delays = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)
        for delay in delays:
            if delay:
                await asyncio.sleep(delay)
            if await self._all_assertions() == expected:
                return
        if expected:
            raise AllocationViolation(
                "DataHub did not return the exact active baseline assertion allocation"
            )
        raise AllocationViolation("baseline assertions remain attached after reset")

    def _guard(self, approval_sha256: str, expected_sha256: str) -> None:
        validate_allocation_settings(self.settings, workspace_root=self.workspace_root)
        for dataset_urn in ALL_DATASET_URNS:
            validate_dataset_urn(dataset_urn, self.settings)
        for assertion_urn in BASELINE_ASSERTION_URNS:
            validate_assertion_urn(assertion_urn, self.settings)
        if self.settings.readiness_dataset_urn != DATASET_URN:
            raise AllocationViolation("readiness target differs from the campaign target")
        if self.settings.required_marker_key != "sandbox":
            raise AllocationViolation("sandbox marker key differs from coordinator contract")
        if self.settings.required_marker_value.casefold() != "true":
            raise AllocationViolation("sandbox marker value differs from coordinator contract")
        if approval_sha256 != expected_sha256:
            raise AllocationViolation(
                "approval SHA-256 does not match the immutable catalog operation plan"
            )

    def _invalidate_context(self) -> None:
        state_root = _state_root(self.settings, self.workspace_root)
        paths = {
            state_root / CONTEXT_FILENAME,
            state_root / f"{CONTEXT_FILENAME}.receipt.json",
        }
        if self.settings.campaign_context_file is not None:
            configured = self.settings.campaign_context_file
            if not configured.is_absolute():
                configured = self.workspace_root / configured
            configured = configured.resolve(strict=False)
            paths.add(configured)
            paths.add(configured.with_name(f"{configured.name}.receipt.json"))
        for path in paths:
            resolved = path.resolve(strict=False)
            if not resolved.is_relative_to(state_root):
                raise AllocationViolation("context evidence path escapes the state root")
            if resolved.is_file():
                resolved.unlink()


def catalog_plan(settings: Settings) -> dict[str, Any]:
    return {
        "operation": "seed_datahub_fixture_v2",
        "dataset_urns": list(ALL_DATASET_URNS),
        "domain_urn": DOMAIN_URN,
        "tag_urns": [PROJECT_TAG_URN, SANDBOX_TAG_URN],
        "owner_urn": OWNER_URN,
        "lineage_edges": [edge.model_dump(mode="json") for edge in DEMO_LINEAGE],
        "assertions": [assertion_payload(spec) for spec in BASELINE_ASSERTIONS],
        "aspects": _canonical_operations(settings),
    }


def catalog_reset_plan(settings: Settings) -> dict[str, Any]:
    _ = settings
    return {
        "operation": "reset_datahub_fixture_v2",
        "soft_delete_dataset_urns": list(ALL_DATASET_URNS),
        "soft_delete_assertion_urns": sorted(BASELINE_ASSERTION_URNS),
        "retained_urns": [DOMAIN_URN, PROJECT_TAG_URN, SANDBOX_TAG_URN],
        "invalidate_context_files": [
            CONTEXT_FILENAME,
            f"{CONTEXT_FILENAME}.receipt.json",
        ],
    }


def fixture_contract_sha256(settings: Settings) -> str:
    return sha256_json(catalog_plan(settings))


def catalog_state_path(settings: Settings, workspace_root: Path) -> Path:
    return _state_root(settings, workspace_root) / CATALOG_STATE_FILENAME


def load_catalog_state(settings: Settings, workspace_root: Path) -> dict[str, Any]:
    path = catalog_state_path(settings, workspace_root)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AllocationViolation("catalog state receipt is missing or invalid") from exc
    if not isinstance(value, dict):
        raise AllocationViolation("catalog state receipt is not an object")
    return value


def normalize_assertions(value: Any) -> tuple[dict[str, str], ...]:
    results: list[dict[str, str]] = []
    for node in _assertion_nodes(value):
        urn = node.get("urn")
        info = node.get("info")
        custom = info.get("customAssertion") if isinstance(info, dict) else None
        if not isinstance(urn, str) or not isinstance(custom, dict):
            continue
        assertion_type = custom.get("type")
        entity_urn = custom.get("entityUrn")
        logic = custom.get("logic")
        description = info.get("description") if isinstance(info, dict) else None
        if not all(
            isinstance(item, str)
            for item in (assertion_type, entity_urn, logic, description)
        ):
            raise AllocationViolation("baseline assertion metadata is incomplete")
        results.append(
            {
                "urn": urn,
                "entityUrn": entity_urn,
                "type": assertion_type,
                "description": description,
                "logic": logic,
            }
        )
    return tuple(sorted(results, key=lambda item: item["urn"]))


def validate_observed_dataset(
    observed: Any,
    settings: Settings,
    dataset_urn: str,
    *,
    table_name: str | None = None,
    removed: bool = False,
    status_only: bool = False,
) -> None:
    entity = _find_entity(observed, dataset_urn)
    if entity is None:
        raise AllocationViolation("DataHub did not return an allocated dataset")
    status = _aspect_value(entity, "status")
    if not isinstance(status, dict) or status.get("removed") is not removed:
        raise AllocationViolation("DataHub dataset active/tombstone status differs")
    if status_only:
        return

    if table_name is None:
        serialized = json.dumps(entity, sort_keys=True).casefold()
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
        if removed:
            raise AllocationViolation("proof target must be active")
        return

    properties = _aspect_value(entity, "datasetProperties")
    tags = _aspect_value(entity, "globalTags")
    domains = _aspect_value(entity, "domains")
    ownership = _aspect_value(entity, "ownership")
    schema = _aspect_value(entity, "schemaMetadata")
    lineage = _aspect_value(entity, "upstreamLineage")
    if not all(
        isinstance(value, dict)
        for value in (properties, tags, domains, ownership, schema, lineage)
    ):
        raise AllocationViolation("DataHub dataset is missing a required seeded aspect")
    expected_properties = {
        settings.required_marker_key: settings.required_marker_value,
        "project_slug": PROJECT_SLUG,
    }
    if (
        properties.get("name") != f"fuzzer.{table_name}"
        or properties.get("customProperties") != expected_properties
    ):
        raise AllocationViolation("DataHub dataset properties differ from the fixture contract")
    if {tag.get("tag") for tag in tags.get("tags", [])} != {
        PROJECT_TAG_URN,
        SANDBOX_TAG_URN,
    }:
        raise AllocationViolation("DataHub dataset tags differ from the fixture contract")
    if domains.get("domains") != [DOMAIN_URN]:
        raise AllocationViolation("DataHub dataset domain differs from the fixture contract")
    owners = {
        (owner.get("owner"), owner.get("type"))
        for owner in ownership.get("owners", [])
        if isinstance(owner, dict)
    }
    if owners != {(OWNER_URN, "DATAOWNER")}:
        raise AllocationViolation("DataHub dataset owner differs from the fixture contract")
    expected_schema = schema_metadata(table_name)
    if schema != expected_schema:
        raise AllocationViolation("DataHub dataset schema differs from the fixture contract")
    upstreams = {
        item.get("dataset")
        for item in lineage.get("upstreams", [])
        if isinstance(item, dict) and item.get("type") == "TRANSFORMED"
    }
    if upstreams != set(upstreams_for(dataset_urn)):
        raise AllocationViolation("DataHub upstream lineage differs from the fixture contract")


def validate_observed_assertion_tombstone(
    observed: Any,
    assertion_urn: str,
) -> None:
    entity = _find_entity(observed, assertion_urn)
    if entity is None:
        raise AllocationViolation("DataHub did not return an allocated assertion")
    status = _aspect_value(entity, "status")
    if not isinstance(status, dict) or status.get("removed") is not True:
        raise AllocationViolation("DataHub assertion tombstone status differs")


def _has_tombstone(observed: Any, entity_urn: str) -> bool:
    entity = _find_entity(observed, entity_urn)
    if entity is None:
        return False
    status = _aspect_value(entity, "status")
    return isinstance(status, dict) and status.get("removed") is True


def _canonical_operations(settings: Settings) -> list[dict[str, Any]]:
    description = "Disposable Lineage Fuzzer hackathon fixture."
    operations: list[dict[str, Any]] = [
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
    ]
    for table_name, dataset_urn in TABLE_URNS.items():
        operations.extend(
            [
                {
                    "entity_type": "dataset",
                    "entity_urn": dataset_urn,
                    "aspect_name": "datasetProperties",
                    "value": {
                        "customProperties": {
                            settings.required_marker_key: settings.required_marker_value,
                            "project_slug": PROJECT_SLUG,
                        },
                        "name": f"fuzzer.{table_name}",
                        "description": description,
                        "tags": [],
                    },
                },
                {
                    "entity_type": "dataset",
                    "entity_urn": dataset_urn,
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
                    "entity_urn": dataset_urn,
                    "aspect_name": "domains",
                    "value": {"domains": [DOMAIN_URN]},
                },
                {
                    "entity_type": "dataset",
                    "entity_urn": dataset_urn,
                    "aspect_name": "ownership",
                    "value": {
                        "owners": [{"owner": OWNER_URN, "type": "DATAOWNER"}],
                        "lastModified": {"time": 0, "actor": OWNER_URN},
                    },
                },
                {
                    "entity_type": "dataset",
                    "entity_urn": dataset_urn,
                    "aspect_name": "schemaMetadata",
                    "value": schema_metadata(table_name),
                },
                {
                    "entity_type": "dataset",
                    "entity_urn": dataset_urn,
                    "aspect_name": "upstreamLineage",
                    "value": {
                        "upstreams": [
                            {"dataset": upstream_urn, "type": "TRANSFORMED"}
                            for upstream_urn in upstreams_for(dataset_urn)
                        ]
                    },
                },
                {
                    "entity_type": "dataset",
                    "entity_urn": dataset_urn,
                    "aspect_name": "status",
                    "value": {"removed": False},
                },
            ]
        )
    return operations


def _write_catalog_state(
    settings: Settings,
    workspace_root: Path,
    *,
    status: str,
    plan_sha256: str,
) -> dict[str, Any]:
    path = catalog_state_path(settings, workspace_root)
    if not path.parent.is_dir():
        raise AllocationViolation("configured state directory does not exist")
    value = {
        "schema_version": 1,
        "project_slug": PROJECT_SLUG,
        "status": status,
        "plan_sha256": plan_sha256,
        "fixture_contract_sha256": fixture_contract_sha256(settings),
    }
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        f"{json.dumps(value, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)
    return value


def _state_root(settings: Settings, workspace_root: Path) -> Path:
    root = settings.state_dir
    if not root.is_absolute():
        root = workspace_root / root
    root = root.resolve(strict=False)
    if root == Path(root.anchor):
        raise AllocationViolation("state directory cannot be a filesystem root")
    return root


def _find_entity(value: Any, urn: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("urn") == urn:
            return value
        for child in value.values():
            result = _find_entity(child, urn)
            if result is not None:
                return result
    elif isinstance(value, list):
        for child in value:
            result = _find_entity(child, urn)
            if result is not None:
                return result
    return None


def _aspect_value(entity: dict[str, Any], name: str) -> Any:
    aspect = entity.get(name)
    if isinstance(aspect, dict) and "value" in aspect:
        return aspect["value"]
    return aspect


def _assertion_nodes(value: Any) -> tuple[dict[str, Any], ...]:
    if isinstance(value, dict):
        if isinstance(value.get("urn"), str) and isinstance(value.get("info"), dict):
            return (value,)
        nodes: list[dict[str, Any]] = []
        for child in value.values():
            nodes.extend(_assertion_nodes(child))
        return tuple(nodes)
    if isinstance(value, list):
        nodes = []
        for child in value:
            nodes.extend(_assertion_nodes(child))
        return tuple(nodes)
    return ()
