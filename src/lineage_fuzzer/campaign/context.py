from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from lineage_fuzzer.allocation import validate_dataset_urn
from lineage_fuzzer.config import Settings
from lineage_fuzzer.domain.models import DataHubContextSnapshot, LineageEdge

RAW_CUSTOMERS_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.customers,DEV)"
)
RAW_ORDERS_URN = "urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.orders,DEV)"
STAGING_ORDERS_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.staging.orders_enriched,DEV)"
)
DAILY_REVENUE_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.marts.daily_revenue,DEV)"
)
CUSTOMER_VALUE_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.marts.customer_value,DEV)"
)
DASHBOARD_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,"
    "fuzzer.reporting.executive_dashboard,DEV)"
)

TABLE_URNS = {
    "raw.customers": RAW_CUSTOMERS_URN,
    "raw.orders": RAW_ORDERS_URN,
    "staging.orders_enriched": STAGING_ORDERS_URN,
    "marts.daily_revenue": DAILY_REVENUE_URN,
    "marts.customer_value": CUSTOMER_VALUE_URN,
    "reporting.executive_dashboard": DASHBOARD_URN,
}

DEMO_LINEAGE = (
    LineageEdge(upstream_urn=RAW_CUSTOMERS_URN, downstream_urn=STAGING_ORDERS_URN),
    LineageEdge(upstream_urn=RAW_ORDERS_URN, downstream_urn=STAGING_ORDERS_URN),
    LineageEdge(upstream_urn=STAGING_ORDERS_URN, downstream_urn=DAILY_REVENUE_URN),
    LineageEdge(upstream_urn=STAGING_ORDERS_URN, downstream_urn=CUSTOMER_VALUE_URN),
    LineageEdge(upstream_urn=CUSTOMER_VALUE_URN, downstream_urn=DASHBOARD_URN),
)


class ContextCaptureError(RuntimeError):
    """Raised when DataHub context cannot support the fixed campaign."""


class MCPContextClient(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


class AssertionContextClient(Protocol):
    async def assertions_for_dataset(self, dataset_urn: str) -> dict[str, Any]: ...


class LiveDataHubContextReader:
    """Capture the immutable planning inputs through official DataHub MCP tools."""

    def __init__(
        self,
        settings: Settings,
        mcp: MCPContextClient,
        graphql: AssertionContextClient,
    ) -> None:
        self.settings = settings
        self.mcp = mcp
        self.graphql = graphql

    async def capture(self, target_urn: str = RAW_ORDERS_URN) -> DataHubContextSnapshot:
        validate_dataset_urn(target_urn, self.settings)
        entity = await self.mcp.call_tool("get_entities", {"urns": [target_urn]})
        schema = await self.mcp.call_tool(
            "list_schema_fields",
            {"urn": target_urn, "limit": 100, "offset": 0},
        )
        lineage = await self.mcp.call_tool(
            "get_lineage",
            {
                "urn": target_urn,
                "upstream": False,
                "max_hops": 3,
                "max_results": 100,
                "offset": 0,
            },
        )
        assertions = await self.graphql.assertions_for_dataset(target_urn)

        downstream_urns = tuple(sorted(_lineage_entity_urns(lineage) - {target_urn}))
        if not downstream_urns:
            raise ContextCaptureError(
                "DataHub returned no downstream lineage for the allocated campaign target"
            )
        for urn in downstream_urns:
            validate_dataset_urn(urn, self.settings)

        entities = _entity_dicts(entity)
        entities += ({"urn": target_urn, "schema": schema},)
        edges = tuple(
            LineageEdge(upstream_urn=target_urn, downstream_urn=urn)
            for urn in downstream_urns
        )
        return DataHubContextSnapshot(
            source="datahub-mcp-live",
            entities=entities,
            lineage=edges,
            assertions=(assertions,),
        )


def demo_context_snapshot() -> DataHubContextSnapshot:
    """Deterministic local topology for offline development and committed examples."""

    columns = {
        RAW_ORDERS_URN: (
            "order_id",
            "customer_id",
            "order_ts",
            "amount_cents",
            "currency",
            "source_partition",
        ),
        STAGING_ORDERS_URN: (
            "order_id",
            "customer_id",
            "customer_name",
            "segment",
            "country_code",
            "order_ts",
            "order_date",
            "amount_cents",
            "currency",
            "source_partition",
        ),
        DAILY_REVENUE_URN: (
            "order_date",
            "currency",
            "order_count",
            "revenue_cents",
        ),
        CUSTOMER_VALUE_URN: (
            "customer_id",
            "customer_name",
            "segment",
            "country_code",
            "order_count",
            "lifetime_value_cents",
            "last_order_ts",
        ),
        DASHBOARD_URN: (
            "active_customers",
            "total_orders",
            "total_revenue_cents",
            "latest_order_ts",
        ),
    }
    entities = tuple(
        {
            "urn": urn,
            "name": urn.split(",")[1],
            "platform": "duckdb",
            "environment": "DEV",
            "owners": ["urn:li:corpuser:lineage-fuzzer"],
            "tags": ["project-lineage-fuzzer", "lineage-fuzzer-sandbox"],
            "customProperties": {"sandbox": "true"},
            "schemaFields": list(columns.get(urn, ())),
        }
        for urn in TABLE_URNS.values()
    )
    assertions = (
        {
            "urn": "urn:li:assertion:fuzzer.control.orders-customer-id-not-null",
            "entityUrn": RAW_ORDERS_URN,
            "type": "not_null",
            "field": "customer_id",
        },
        {
            "urn": "urn:li:assertion:fuzzer.control.orders-order-id-unique",
            "entityUrn": RAW_ORDERS_URN,
            "type": "unique",
            "field": "order_id",
        },
        {
            "urn": "urn:li:assertion:fuzzer.control.daily-revenue-non-negative",
            "entityUrn": DAILY_REVENUE_URN,
            "type": "non_negative",
            "field": "revenue_cents",
        },
    )
    return DataHubContextSnapshot(
        captured_at=datetime(2026, 7, 25, 12, 0, tzinfo=UTC),
        source="local-fixture-topology",
        entities=entities,
        lineage=DEMO_LINEAGE,
        assertions=assertions,
    )


def context_sha256(context: DataHubContextSnapshot) -> str:
    payload = context.model_dump(mode="json", exclude={"captured_at"})
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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

def save_live_context_snapshot(
    path: Path,
    context: DataHubContextSnapshot,
) -> Path:
    """Persist only context actually captured through DataHub MCP."""

    if context.source != "datahub-mcp-live":
        raise ContextCaptureError("refusing to persist context not captured from live DataHub")
    resolved = path.resolve(strict=False)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        context.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )
    temporary = resolved.with_suffix(f"{resolved.suffix}.tmp")
    temporary.write_text(f"{serialized}\n", encoding="utf-8", newline="\n")
    temporary.replace(resolved)
    return resolved


def load_live_context_snapshot(path: Path) -> DataHubContextSnapshot:
    """Load a saved live snapshot without silently substituting fixture topology."""

    try:
        resolved = path.resolve(strict=True)
        context = DataHubContextSnapshot.model_validate_json(
            resolved.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise ContextCaptureError("saved DataHub context is invalid") from exc
    if context.source != "datahub-mcp-live":
        raise ContextCaptureError("saved context is not marked as live DataHub context")
    if not context.lineage:
        raise ContextCaptureError("saved DataHub context contains no lineage")
    return context


def _lineage_entity_urns(value: Any) -> set[str]:
    urns: set[str] = set()
    if isinstance(value, dict):
        entity = value.get("entity")
        if isinstance(entity, dict) and isinstance(entity.get("urn"), str):
            urns.add(entity["urn"])
        for child in value.values():
            urns.update(_lineage_entity_urns(child))
    elif isinstance(value, list):
        for child in value:
            urns.update(_lineage_entity_urns(child))
    return urns


def _entity_dicts(value: Any) -> tuple[dict[str, Any], ...]:
    if isinstance(value, dict):
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, dict))
    raise ContextCaptureError("DataHub get_entities returned an unsupported payload")
