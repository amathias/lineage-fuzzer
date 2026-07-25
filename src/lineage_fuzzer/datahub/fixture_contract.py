from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lineage_fuzzer.domain.models import LineageEdge
from lineage_fuzzer.pipeline import BASELINE_CONTROLS
from lineage_fuzzer.pipeline.models import ControlDefinition

DATASET_PLATFORM_URN = "urn:li:dataPlatform:duckdb"
DOMAIN_URN = "urn:li:domain:lineage-fuzzer"
PROJECT_TAG_URN = "urn:li:tag:project-lineage-fuzzer"
SANDBOX_TAG_URN = "urn:li:tag:lineage-fuzzer-sandbox"
OWNER_URN = "urn:li:corpuser:lineage-fuzzer"

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

TABLE_SCHEMAS: dict[str, tuple[tuple[str, str, bool], ...]] = {
    "raw.customers": (
        ("customer_id", "INTEGER", False),
        ("customer_name", "VARCHAR", False),
        ("segment", "VARCHAR", False),
        ("country_code", "VARCHAR", False),
    ),
    "raw.orders": (
        ("order_id", "INTEGER", False),
        ("customer_id", "INTEGER", True),
        ("order_ts", "TIMESTAMP", False),
        ("amount_cents", "BIGINT", False),
        ("currency", "VARCHAR", False),
        ("source_partition", "DATE", False),
    ),
    "staging.orders_enriched": (
        ("order_id", "INTEGER", False),
        ("customer_id", "INTEGER", True),
        ("customer_name", "VARCHAR", True),
        ("segment", "VARCHAR", True),
        ("country_code", "VARCHAR", True),
        ("order_ts", "TIMESTAMP", False),
        ("order_date", "DATE", False),
        ("amount_cents", "BIGINT", False),
        ("currency", "VARCHAR", False),
        ("source_partition", "DATE", False),
    ),
    "marts.daily_revenue": (
        ("order_date", "DATE", False),
        ("currency", "VARCHAR", False),
        ("order_count", "BIGINT", False),
        ("revenue_cents", "BIGINT", True),
    ),
    "marts.customer_value": (
        ("customer_id", "INTEGER", True),
        ("customer_name", "VARCHAR", True),
        ("segment", "VARCHAR", True),
        ("country_code", "VARCHAR", True),
        ("order_count", "BIGINT", False),
        ("lifetime_value_cents", "BIGINT", True),
        ("last_order_ts", "TIMESTAMP", True),
    ),
    "reporting.executive_dashboard": (
        ("active_customers", "BIGINT", False),
        ("total_orders", "HUGEINT", True),
        ("total_revenue_cents", "HUGEINT", True),
        ("latest_order_ts", "TIMESTAMP", True),
    ),
}


@dataclass(frozen=True)
class BaselineAssertionSpec:
    urn: str
    entity_urn: str
    assertion_type: str
    description: str
    logic: str
    control: ControlDefinition


_CONTROL_BY_ID = {control.control_id: control for control in BASELINE_CONTROLS}

BASELINE_ASSERTIONS = (
    BaselineAssertionSpec(
        urn="urn:li:assertion:fuzzer.control.orders-customer-id-not-null",
        entity_urn=RAW_ORDERS_URN,
        assertion_type="orders_customer_id_not_null",
        description="Every raw order must identify its customer.",
        logic=_CONTROL_BY_ID["orders_customer_id_not_null"].violation_query,
        control=_CONTROL_BY_ID["orders_customer_id_not_null"],
    ),
    BaselineAssertionSpec(
        urn="urn:li:assertion:fuzzer.control.orders-order-id-unique",
        entity_urn=RAW_ORDERS_URN,
        assertion_type="orders_order_id_unique",
        description="Every raw order identifier must be unique.",
        logic=_CONTROL_BY_ID["orders_order_id_unique"].violation_query,
        control=_CONTROL_BY_ID["orders_order_id_unique"],
    ),
    BaselineAssertionSpec(
        urn="urn:li:assertion:fuzzer.control.daily-revenue-non-negative",
        entity_urn=DAILY_REVENUE_URN,
        assertion_type="daily_revenue_non_negative",
        description="Daily revenue must not fall below zero.",
        logic=_CONTROL_BY_ID["daily_revenue_non_negative"].violation_query,
        control=_CONTROL_BY_ID["daily_revenue_non_negative"],
    ),
)

BASELINE_ASSERTION_URNS = frozenset(spec.urn for spec in BASELINE_ASSERTIONS)
ALL_DATASET_URNS = tuple(TABLE_URNS.values())


def upstreams_for(dataset_urn: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            edge.upstream_urn
            for edge in DEMO_LINEAGE
            if edge.downstream_urn == dataset_urn
        )
    )


def downstreams_for(dataset_urn: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            edge.downstream_urn
            for edge in DEMO_LINEAGE
            if edge.upstream_urn == dataset_urn
        )
    )


def schema_metadata(table_name: str) -> dict[str, Any]:
    fields = TABLE_SCHEMAS[table_name]
    raw_schema = ", ".join(
        f"{name} {native_type}{'' if nullable else ' NOT NULL'}"
        for name, native_type, nullable in fields
    )
    return {
        "schemaName": table_name,
        "platform": DATASET_PLATFORM_URN,
        "version": 0,
        "hash": f"lineage-fuzzer:{table_name}:v1",
        "platformSchema": {
            "com.linkedin.schema.OtherSchema": {"rawSchema": raw_schema}
        },
        "fields": [
            {
                "fieldPath": name,
                "nativeDataType": native_type,
                "nullable": nullable,
                "description": f"Deterministic Lineage Fuzzer field {table_name}.{name}.",
                "type": {"type": {_schema_type(native_type): {}}},
            }
            for name, native_type, nullable in fields
        ],
    }


def expected_schema_fields(dataset_urn: str) -> tuple[str, ...]:
    table_name = next(name for name, urn in TABLE_URNS.items() if urn == dataset_urn)
    return tuple(field[0] for field in TABLE_SCHEMAS[table_name])


def assertion_payload(spec: BaselineAssertionSpec) -> dict[str, str]:
    return {
        "urn": spec.urn,
        "entityUrn": spec.entity_urn,
        "type": spec.assertion_type,
        "description": spec.description,
        "logic": spec.logic,
    }


def _schema_type(native_type: str) -> str:
    if native_type in {"INTEGER", "BIGINT", "HUGEINT"}:
        return "com.linkedin.schema.NumberType"
    if native_type == "TIMESTAMP":
        return "com.linkedin.schema.TimeType"
    if native_type == "DATE":
        return "com.linkedin.schema.DateType"
    return "com.linkedin.schema.StringType"
