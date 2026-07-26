from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from lineage_fuzzer.allocation import AllocationViolation, validate_dataset_urn
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.fixture_catalog import (
    catalog_state_path,
    fixture_contract_sha256,
    load_catalog_state,
    normalize_assertions,
)
from lineage_fuzzer.datahub.fixture_contract import (
    ALL_DATASET_URNS,
    BASELINE_ASSERTIONS,
    CUSTOMER_VALUE_URN,
    DAILY_REVENUE_URN,
    DASHBOARD_URN,
    DEMO_LINEAGE,
    DOMAIN_URN,
    OWNER_URN,
    PROJECT_TAG_URN,
    RAW_CUSTOMERS_URN,
    RAW_ORDERS_URN,
    SANDBOX_TAG_URN,
    STAGING_ORDERS_URN,
    TABLE_SCHEMAS,
    TABLE_URNS,
    assertion_payload,
    downstreams_for,
    expected_schema_fields,
)
from lineage_fuzzer.datahub.mcp import REQUIRED_CONTEXT_TOOLS
from lineage_fuzzer.datahub.receipts import canonical_json, sha256_json
from lineage_fuzzer.domain.models import (
    ContextProvenance,
    DataHubContextSnapshot,
)

__all__ = [
    "CUSTOMER_VALUE_URN",
    "DAILY_REVENUE_URN",
    "DASHBOARD_URN",
    "DEMO_LINEAGE",
    "RAW_CUSTOMERS_URN",
    "RAW_ORDERS_URN",
    "STAGING_ORDERS_URN",
    "TABLE_URNS",
    "ContextCaptureError",
    "LiveDataHubContextReader",
]
from lineage_fuzzer.pipeline import BASELINE_CONTROLS, CommerceFixture
from lineage_fuzzer.pipeline.models import ControlDefinition


class ContextCaptureError(RuntimeError):
    """Raised when DataHub context cannot support the fixed campaign."""


class MCPContextClient(Protocol):
    async def describe_tools(self) -> tuple[dict[str, Any], ...]: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


class AssertionContextClient(Protocol):
    async def assertions_for_dataset(self, dataset_urn: str) -> dict[str, Any]: ...


class LiveDataHubContextReader:
    """Capture exact, provenance-bound planning inputs through supported DataHub APIs."""

    def __init__(
        self,
        settings: Settings,
        mcp: MCPContextClient,
        graphql: AssertionContextClient,
        *,
        workspace_root: Path,
    ) -> None:
        self.settings = settings
        self.mcp = mcp
        self.graphql = graphql
        self.workspace_root = workspace_root.resolve()

    async def capture(self, target_urn: str = RAW_ORDERS_URN) -> DataHubContextSnapshot:
        if target_urn != RAW_ORDERS_URN:
            raise ContextCaptureError("campaign target differs from the exact fixture target")
        validate_dataset_urn(target_urn, self.settings)
        candidate_sha = self.settings.candidate_sha
        if candidate_sha is None:
            raise ContextCaptureError(
                "LINEAGE_FUZZER_CANDIDATE_SHA is required for live context capture"
            )
        catalog_state = _verified_catalog_state(self.settings, self.workspace_root)
        fixture_sha = fixture_binding_sha256(self.settings, self.workspace_root)

        tool_schemas = await self.mcp.describe_tools()
        tool_names = tuple(sorted(tool["name"] for tool in tool_schemas))
        missing_tools = sorted(REQUIRED_CONTEXT_TOOLS - set(tool_names))
        if missing_tools:
            raise ContextCaptureError(
                f"DataHub MCP is missing required context tools: {missing_tools}"
            )
        raw_digests: dict[str, str] = {
            "mcp.tool_schemas": sha256_json(tool_schemas),
        }

        entity_response = await self.mcp.call_tool(
            "get_entities",
            {"urns": list(ALL_DATASET_URNS)},
        )
        raw_digests["mcp.get_entities"] = sha256_json(entity_response)
        returned_entities = {
            urn: _find_entity(entity_response, urn) for urn in ALL_DATASET_URNS
        }
        if any(entity is None for entity in returned_entities.values()):
            raise ContextCaptureError("DataHub did not return all six allocated datasets")

        entities: list[dict[str, Any]] = []
        assertions: list[dict[str, str]] = []
        for table_name, urn in TABLE_URNS.items():
            entity = returned_entities[urn]
            assert entity is not None
            _validate_live_entity(entity, table_name, urn, self.settings)

            schema_response = await self.mcp.call_tool(
                "list_schema_fields",
                {"urn": urn, "limit": 100, "offset": 0},
            )
            raw_digests[f"mcp.schema:{urn}"] = sha256_json(schema_response)
            fields = _schema_field_paths(schema_response)
            expected_fields = expected_schema_fields(urn)
            if len(fields) != len(set(fields)) or set(fields) != set(expected_fields):
                raise ContextCaptureError(
                    f"DataHub schema is incomplete or contradictory for {urn}"
                )

            lineage_response = await self.mcp.call_tool(
                "get_lineage",
                {
                    "urn": urn,
                    "upstream": False,
                    "max_hops": 1,
                    "max_results": 100,
                    "offset": 0,
                },
            )
            raw_digests[f"mcp.lineage:{urn}"] = sha256_json(lineage_response)
            downstreams = _direct_lineage_urns(lineage_response, source_urn=urn)
            expected_downstreams = downstreams_for(urn)
            if downstreams != expected_downstreams:
                raise ContextCaptureError(
                    f"DataHub direct lineage is incomplete or contradictory for {urn}"
                )

            assertion_response = await self.graphql.assertions_for_dataset(urn)
            raw_digests[f"graphql.assertions:{urn}"] = sha256_json(assertion_response)
            dataset_assertions = normalize_assertions(assertion_response)
            expected = tuple(
                assertion_payload(spec)
                for spec in BASELINE_ASSERTIONS
                if spec.entity_urn == urn
            )
            if dataset_assertions != expected:
                raise ContextCaptureError(
                    f"DataHub baseline assertions are incomplete or contradictory for {urn}"
                )
            assertions.extend(dataset_assertions)
            entities.append(_normalized_entity(table_name, urn, expected_fields))

        context = DataHubContextSnapshot(
            source="datahub-mcp-live",
            entities=tuple(entities),
            lineage=DEMO_LINEAGE,
            assertions=tuple(assertions),
            provenance=ContextProvenance(
                candidate_sha=candidate_sha,
                catalog_plan_sha256=fixture_contract_sha256(self.settings),
                catalog_state_sha256=sha256_json(catalog_state),
                fixture_sha256=fixture_sha,
                tool_schema_sha256=sha256_json(tool_schemas),
                raw_response_sha256=dict(sorted(raw_digests.items())),
                tool_schemas=tool_schemas,
                mcp_tools=tool_names,
            ),
        )
        validate_live_context_snapshot(context)
        return context


def demo_context_snapshot() -> DataHubContextSnapshot:
    """Deterministic local topology for offline development and committed examples."""

    entities = tuple(
        _normalized_entity(
            table_name,
            urn,
            tuple(field[0] for field in TABLE_SCHEMAS[table_name]),
        )
        for table_name, urn in TABLE_URNS.items()
    )
    return DataHubContextSnapshot(
        captured_at=datetime(2026, 7, 25, 12, 0, tzinfo=UTC),
        source="local-fixture-topology",
        entities=entities,
        lineage=DEMO_LINEAGE,
        assertions=tuple(assertion_payload(spec) for spec in BASELINE_ASSERTIONS),
    )


def baseline_controls_from_context(
    context: DataHubContextSnapshot,
) -> tuple[ControlDefinition, ...]:
    if context.source == "local-fixture-topology":
        return BASELINE_CONTROLS
    if context.source != "datahub-mcp-live":
        raise ContextCaptureError("campaign context source is not recognized")
    validate_live_context_snapshot(context)
    observed = {
        assertion["urn"]: assertion for assertion in context.assertions
    }
    expected = {
        spec.urn: assertion_payload(spec) for spec in BASELINE_ASSERTIONS
    }
    if observed != expected:
        raise ContextCaptureError(
            "live campaign controls are not the exact DataHub assertion allocation"
        )
    return tuple(spec.control for spec in BASELINE_ASSERTIONS)


def context_sha256(context: DataHubContextSnapshot) -> str:
    payload = context.model_dump(mode="json", exclude={"captured_at"})
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def fixture_binding_sha256(settings: Settings, workspace_root: Path) -> str:
    root = settings.fixture_root
    if not root.is_absolute():
        root = workspace_root / root
    database = Path(settings.allowed_database_paths[0])
    if not database.is_absolute():
        database = workspace_root / database
    try:
        evidence = CommerceFixture(
            database.resolve(strict=False),
            fixture_root=root.resolve(strict=False),
        ).evidence()
    except Exception as exc:
        raise ContextCaptureError("allocated fixture is unavailable for context binding") from exc
    return sha256_json(
        {
            "seed": evidence.seed,
            "checksums": dict(sorted(evidence.checksum_map.items())),
        }
    )


def downstream_blast_radius(
    context: DataHubContextSnapshot,
    source_urn: str,
) -> tuple[str, ...]:
    adjacency: dict[str, set[str]] = {}
    for edge in context.lineage:
        adjacency.setdefault(edge.upstream_urn, set()).add(edge.downstream_urn)
    visited = {source_urn}
    frontier = [source_urn]
    while frontier:
        current = frontier.pop(0)
        for downstream in sorted(adjacency.get(current, ())):
            if downstream not in visited:
                visited.add(downstream)
                frontier.append(downstream)
    return tuple(sorted(visited))


def context_store_path(state_dir: Path) -> Path:
    return state_dir / "campaign-context.json"


def context_receipt_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.receipt.json")


def save_live_context_snapshot(
    path: Path,
    context: DataHubContextSnapshot,
) -> Path:
    """Persist a validated snapshot and a candidate/fixture-bound receipt."""

    validate_live_context_snapshot(context)
    resolved = path.resolve(strict=False)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(context.model_dump(mode="json"), indent=2, sort_keys=True)
    _atomic_text(resolved, f"{serialized}\n")
    provenance = context.provenance
    assert provenance is not None
    receipt = {
        "schema_version": 1,
        "source": context.source,
        "context_sha256": context_sha256(context),
        "candidate_sha": provenance.candidate_sha,
        "catalog_plan_sha256": provenance.catalog_plan_sha256,
        "catalog_state_sha256": provenance.catalog_state_sha256,
        "fixture_sha256": provenance.fixture_sha256,
    }
    _atomic_text(
        context_receipt_path(resolved),
        f"{json.dumps(receipt, indent=2, sort_keys=True)}\n",
    )
    return resolved


def load_live_context_snapshot(
    path: Path,
    *,
    settings: Settings | None = None,
    workspace_root: Path | None = None,
) -> DataHubContextSnapshot:
    """Load only a valid snapshot with a matching immutable capture receipt."""

    try:
        resolved = path.resolve(strict=True)
        context = DataHubContextSnapshot.model_validate_json(
            resolved.read_text(encoding="utf-8")
        )
        receipt = json.loads(
            context_receipt_path(resolved).read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise ContextCaptureError("saved DataHub context or receipt is invalid") from exc
    validate_live_context_snapshot(context)
    provenance = context.provenance
    assert provenance is not None
    expected_receipt = {
        "schema_version": 1,
        "source": context.source,
        "context_sha256": context_sha256(context),
        "candidate_sha": provenance.candidate_sha,
        "catalog_plan_sha256": provenance.catalog_plan_sha256,
        "catalog_state_sha256": provenance.catalog_state_sha256,
        "fixture_sha256": provenance.fixture_sha256,
    }
    if receipt != expected_receipt:
        raise ContextCaptureError("saved DataHub context receipt does not match its snapshot")

    if settings is not None:
        root = (workspace_root or Path.cwd()).resolve()
        if settings.candidate_sha is None:
            raise ContextCaptureError(
                "LINEAGE_FUZZER_CANDIDATE_SHA is required for saved live context"
            )
        if provenance.candidate_sha != settings.candidate_sha:
            raise ContextCaptureError("saved context belongs to a different product candidate")
        state = _verified_catalog_state(settings, root)
        if provenance.catalog_state_sha256 != sha256_json(state):
            raise ContextCaptureError("saved context belongs to a different catalog state")
        if provenance.catalog_plan_sha256 != fixture_contract_sha256(settings):
            raise ContextCaptureError("saved context belongs to a different catalog contract")
        if provenance.fixture_sha256 != fixture_binding_sha256(settings, root):
            raise ContextCaptureError("saved context belongs to a different fixture state")
    return context


def validate_live_context_snapshot(context: DataHubContextSnapshot) -> None:
    if context.source != "datahub-mcp-live":
        raise ContextCaptureError("context was not captured from live DataHub")
    if context.provenance is None:
        raise ContextCaptureError("live context is missing capture provenance")
    expected_entities = tuple(
        _normalized_entity(
            table_name,
            urn,
            tuple(field[0] for field in TABLE_SCHEMAS[table_name]),
        )
        for table_name, urn in TABLE_URNS.items()
    )
    if context.entities != expected_entities:
        raise ContextCaptureError("live context entity metadata is incomplete or forged")
    if context.lineage != DEMO_LINEAGE:
        raise ContextCaptureError("live context lineage is incomplete or forged")
    if context.assertions != tuple(
        assertion_payload(spec) for spec in BASELINE_ASSERTIONS
    ):
        raise ContextCaptureError("live context assertion metadata is incomplete or forged")
    if not REQUIRED_CONTEXT_TOOLS.issubset(context.provenance.mcp_tools):
        raise ContextCaptureError("live context provenance omits required MCP tools")
    if context.provenance.tool_schema_sha256 != sha256_json(
        context.provenance.tool_schemas
    ):
        raise ContextCaptureError("live context tool schema digest is invalid")
    if tuple(tool["name"] for tool in context.provenance.tool_schemas) != (
        context.provenance.mcp_tools
    ):
        raise ContextCaptureError("live context tool schemas contradict MCP tool names")
    expected_digest_keys = {
        "mcp.tool_schemas",
        "mcp.get_entities",
        *{f"mcp.schema:{urn}" for urn in ALL_DATASET_URNS},
        *{f"mcp.lineage:{urn}" for urn in ALL_DATASET_URNS},
        *{f"graphql.assertions:{urn}" for urn in ALL_DATASET_URNS},
    }
    if set(context.provenance.raw_response_sha256) != expected_digest_keys:
        raise ContextCaptureError("live context provenance omits raw response digests")
    if any(
        len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
        for value in context.provenance.raw_response_sha256.values()
    ):
        raise ContextCaptureError("live context contains an invalid response digest")


def _verified_catalog_state(settings: Settings, workspace_root: Path) -> dict[str, Any]:
    try:
        state = load_catalog_state(settings, workspace_root)
    except AllocationViolation as exc:
        raise ContextCaptureError(str(exc)) from exc
    expected_plan = fixture_contract_sha256(settings)
    if (
        state.get("status") != "seeded"
        or state.get("plan_sha256") != expected_plan
        or state.get("fixture_contract_sha256") != expected_plan
    ):
        raise ContextCaptureError("catalog state is not the current verified seed")
    if catalog_state_path(settings, workspace_root).resolve().parent != (
        settings.state_dir
        if settings.state_dir.is_absolute()
        else workspace_root / settings.state_dir
    ).resolve():
        raise ContextCaptureError("catalog state path differs from configured state root")
    return state


def _normalized_entity(
    table_name: str,
    urn: str,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "urn": urn,
        "name": f"fuzzer.{table_name}",
        "platform": "duckdb",
        "environment": "DEV",
        "owners": [OWNER_URN],
        "domain": DOMAIN_URN,
        "tags": ["lineage-fuzzer-sandbox", "project-lineage-fuzzer"],
        "customProperties": {"project_slug": "lineage-fuzzer", "sandbox": "true"},
        "schemaFields": list(fields),
    }


def _validate_live_entity(
    entity: dict[str, Any],
    table_name: str,
    urn: str,
    settings: Settings,
) -> None:
    validate_dataset_urn(urn, settings)
    serialized = canonical_json(entity).casefold()
    required = (
        urn.casefold(),
        f"fuzzer.{table_name}".casefold(),
        DOMAIN_URN.casefold(),
        settings.datahub_domain.casefold(),
        PROJECT_TAG_URN.casefold(),
        settings.datahub_project_tag.casefold(),
        SANDBOX_TAG_URN.casefold(),
        settings.required_sandbox_tag.casefold(),
        OWNER_URN.casefold(),
    )
    pairs = (
        ('"sandbox":"true"', '"key":"sandbox","value":"true"'),
        ('"project_slug":"lineage-fuzzer"', '"key":"project_slug","value":"lineage-fuzzer"'),
    )
    if any(not any(option in serialized for option in alternatives) for alternatives in pairs):
        raise ContextCaptureError(f"DataHub entity marker metadata is invalid for {urn}")
    if any(item not in serialized for item in required):
        raise ContextCaptureError(f"DataHub entity allocation metadata is invalid for {urn}")
    if '"removed":true' in serialized:
        raise ContextCaptureError(f"DataHub entity is soft-deleted: {urn}")


def _schema_field_paths(value: Any) -> tuple[str, ...]:
    fields: list[str] = []
    if isinstance(value, dict):
        field_path = value.get("fieldPath")
        if isinstance(field_path, str):
            fields.append(field_path)
        for child in value.values():
            fields.extend(_schema_field_paths(child))
    elif isinstance(value, list):
        for child in value:
            fields.extend(_schema_field_paths(child))
    return tuple(fields)


def _direct_lineage_urns(value: Any, *, source_urn: str) -> tuple[str, ...]:
    if not isinstance(value, dict) or set(value) != {"downstreams"}:
        raise ContextCaptureError("one-hop lineage response has an invalid result envelope")
    downstreams = value["downstreams"]
    required_fields = {
        "facets",
        "hasMore",
        "offset",
        "returned",
        "searchResults",
        "total",
    }
    if (
        not isinstance(downstreams, dict)
        or set(downstreams) != required_fields
        or not isinstance(downstreams["facets"], list)
        or not isinstance(downstreams["searchResults"], list)
        or downstreams["hasMore"] is not False
        or type(downstreams["offset"]) is not int
        or downstreams["offset"] != 0
        or type(downstreams["returned"]) is not int
        or downstreams["returned"] != len(downstreams["searchResults"])
        or type(downstreams["total"]) is not int
        or downstreams["total"] != downstreams["returned"]
    ):
        raise ContextCaptureError("one-hop lineage response has invalid pagination metadata")

    discovered: set[str] = set()
    for result in downstreams["searchResults"]:
        if not isinstance(result, dict) or not isinstance(result.get("entity"), dict):
            raise ContextCaptureError("one-hop lineage response has an invalid dataset result")
        entity = result["entity"]
        urn = entity.get("urn")
        entity_type = entity.get("type")
        if (
            not isinstance(urn, str)
            or not urn.startswith("urn:li:dataset:")
            or not isinstance(entity_type, str)
            or entity_type.casefold() != "dataset"
        ):
            raise ContextCaptureError("one-hop lineage response has an invalid dataset result")
        degree = result.get("degree")
        if (
            isinstance(degree, bool)
            or not isinstance(degree, (int, float))
            or degree != 1
        ):
            raise ContextCaptureError(
                "one-hop lineage response contains a non-direct result"
            )
        if urn == source_urn:
            raise ContextCaptureError(
                "one-hop lineage response contains its source as a downstream result"
            )
        if urn in discovered:
            raise ContextCaptureError(
                "one-hop lineage response contains a duplicate dataset result"
            )
        discovered.add(urn)

    return tuple(sorted(discovered))


def _find_entity(value: Any, urn: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("urn") == urn:
            return value
        for child in value.values():
            entity = _find_entity(child, urn)
            if entity is not None:
                return entity
    elif isinstance(value, list):
        for child in value:
            entity = _find_entity(child, urn)
            if entity is not None:
                return entity
    return None


def _atomic_text(path: Path, value: str) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    os.replace(temporary, path)
