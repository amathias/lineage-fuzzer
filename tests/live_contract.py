from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lineage_fuzzer.campaign.context import LiveDataHubContextReader
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.fixture_catalog import (
    catalog_state_path,
    fixture_contract_sha256,
)
from lineage_fuzzer.datahub.fixture_contract import (
    ALL_DATASET_URNS,
    BASELINE_ASSERTIONS,
    DOMAIN_URN,
    OWNER_URN,
    PROJECT_TAG_URN,
    SANDBOX_TAG_URN,
    TABLE_SCHEMAS,
    TABLE_URNS,
    assertion_payload,
    downstreams_for,
)
from lineage_fuzzer.datahub.mcp import REQUIRED_CONTEXT_TOOLS
from lineage_fuzzer.pipeline import CommerceFixture

CANDIDATE_SHA = "a" * 40


def make_settings(
    workspace: Path,
    *,
    environment: str = "test",
    injection_enabled: bool = True,
) -> Settings:
    fixture_root = workspace / "demo" / "fixtures" / "lineage-fuzzer"
    state_dir = workspace / ".lineage-fuzzer"
    state_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        PROJECT_SLUG="lineage-fuzzer",
        APP_ENV=environment,
        APP_STATE_DIR=state_dir,
        DEMO_FIXTURE_ROOT=fixture_root,
        LINEAGE_FUZZER_INJECTION_ENABLED=injection_enabled,
        LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS=[
            str(fixture_root / "lineage_fuzzer.duckdb")
        ],
        LINEAGE_FUZZER_ALLOWED_ENVIRONMENTS=["DEV"],
        LINEAGE_FUZZER_ALLOWED_PLATFORMS=["duckdb"],
        LINEAGE_FUZZER_CANDIDATE_SHA=CANDIDATE_SHA,
        DATAHUB_DOMAIN="Demo / Lineage Fuzzer",
        DATAHUB_PROJECT_TAG="project-lineage-fuzzer",
        DATAHUB_URN_PREFIX="fuzzer.",
        _env_file=None,
    )


def prepare_bound_runtime(workspace: Path, settings: Settings) -> None:
    fixture_root = Path(settings.fixture_root)
    CommerceFixture(
        fixture_root / "lineage_fuzzer.duckdb",
        fixture_root=fixture_root,
    ).seed()
    plan_sha = fixture_contract_sha256(settings)
    catalog_state_path(settings, workspace).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_slug": "lineage-fuzzer",
                "status": "seeded",
                "plan_sha256": plan_sha,
                "fixture_contract_sha256": plan_sha,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def entity_payload(table_name: str, urn: str) -> dict[str, Any]:
    return {
        "urn": urn,
        "type": "DATASET",
        "name": f"fuzzer.{table_name}",
        "platform": {"urn": "urn:li:dataPlatform:duckdb", "name": "duckdb"},
        "environment": "DEV",
        "domain": {"urn": DOMAIN_URN, "name": "Demo / Lineage Fuzzer"},
        "tags": [
            {"urn": PROJECT_TAG_URN, "name": "project-lineage-fuzzer"},
            {"urn": SANDBOX_TAG_URN, "name": "lineage-fuzzer-sandbox"},
        ],
        "owners": [{"urn": OWNER_URN, "type": "DATAOWNER"}],
        "properties": {
            "customProperties": {
                "project_slug": "lineage-fuzzer",
                "sandbox": "true",
            }
        },
        "status": {"removed": False},
    }


def assertion_graphql_payload(dataset_urn: str) -> dict[str, Any]:
    assertions = [
        {
            "urn": spec.urn,
            "info": {
                "type": "CUSTOM",
                "description": spec.description,
                "customAssertion": {
                    "type": spec.assertion_type,
                    "entityUrn": spec.entity_urn,
                    "logic": spec.logic,
                },
            },
            "runEvents": {"runEvents": []},
        }
        for spec in BASELINE_ASSERTIONS
        if spec.entity_urn == dataset_urn
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


class PinnedMCP:
    def __init__(
        self,
        *,
        incomplete_lineage: bool = False,
        missing_schema_field: bool = False,
        duplicate_schema_field: bool = False,
        extra_schema_field: bool = False,
        missing_marker: bool = False,
        foreign_lineage: bool = False,
        missing_lineage_degree: bool = False,
        non_direct_lineage: bool = False,
        duplicate_lineage: bool = False,
        invalid_lineage_type: bool = False,
    ) -> None:
        self.incomplete_lineage = incomplete_lineage
        self.missing_schema_field = missing_schema_field
        self.duplicate_schema_field = duplicate_schema_field
        self.extra_schema_field = extra_schema_field
        self.missing_marker = missing_marker
        self.foreign_lineage = foreign_lineage
        self.missing_lineage_degree = missing_lineage_degree
        self.non_direct_lineage = non_direct_lineage
        self.duplicate_lineage = duplicate_lineage
        self.invalid_lineage_type = invalid_lineage_type
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def describe_tools(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "name": name,
                "inputSchema": {"type": "object", "additionalProperties": False},
                "outputSchema": {"type": "object"},
            }
            for name in sorted(REQUIRED_CONTEXT_TOOLS)
        )

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        if name == "get_entities":
            entities = [
                entity_payload(table_name, urn)
                for table_name, urn in TABLE_URNS.items()
            ]
            if self.missing_marker:
                entities[1]["properties"]["customProperties"].pop("sandbox")
            return {"entities": entities}
        urn = arguments["urn"]
        table_name = next(name for name, value in TABLE_URNS.items() if value == urn)
        if name == "list_schema_fields":
            fields = [
                {
                    "fieldPath": field_name,
                    "nativeDataType": native_type,
                    "nullable": nullable,
                }
                for field_name, native_type, nullable in TABLE_SCHEMAS[table_name]
            ]
            if urn == TABLE_URNS["raw.customers"]:
                fields.sort(key=lambda field: field["fieldPath"])
            if self.missing_schema_field and urn == TABLE_URNS["raw.orders"]:
                fields = fields[:-1]
            if self.duplicate_schema_field and urn == TABLE_URNS["raw.customers"]:
                fields.append(dict(fields[0]))
            if self.extra_schema_field and urn == TABLE_URNS["raw.customers"]:
                fields.append(
                    {
                        "fieldPath": "unexpected_field",
                        "nativeDataType": "VARCHAR",
                        "nullable": True,
                    }
                )
            return {
                "urn": urn,
                "total": len(fields),
                "fields": fields,
            }
        if name == "get_lineage":
            downstreams = list(downstreams_for(urn))
            if self.incomplete_lineage and urn == TABLE_URNS["raw.orders"]:
                downstreams = []
            if self.foreign_lineage and urn == TABLE_URNS["raw.orders"]:
                downstreams.append(
                    "urn:li:dataset:(urn:li:dataPlatform:duckdb,foreign.orders,DEV)"
                )
            results = [
                {
                    "entity": {"urn": downstream, "type": "DATASET"},
                    "degree": 1,
                }
                for downstream in downstreams
            ]
            if results and urn == TABLE_URNS["raw.orders"]:
                if self.missing_lineage_degree:
                    results[0].pop("degree")
                if self.non_direct_lineage:
                    results[0]["degree"] = 2
                if self.duplicate_lineage:
                    results.append(
                        {
                            "entity": dict(results[0]["entity"]),
                            "degree": results[0].get("degree", 1),
                        }
                    )
                if self.invalid_lineage_type:
                    results[0]["entity"]["type"] = "CHART"
            response = {
                "searchResults": results,
                "count": len(downstreams),
            }
            if urn in {
                TABLE_URNS["raw.customers"],
                TABLE_URNS["raw.orders"],
                TABLE_URNS["staging.orders_enriched"],
                TABLE_URNS["marts.customer_value"],
            }:
                response["source"] = {
                    "entity": {
                        "urn": urn,
                        "type": "DATASET",
                        "owner": {
                            "entity": {"urn": OWNER_URN, "type": "CORP_USER"}
                        },
                        "platform": {
                            "entity": {
                                "urn": "urn:li:dataPlatform:duckdb",
                                "type": "DATA_PLATFORM",
                            }
                        },
                        "domain": {
                            "entity": {"urn": DOMAIN_URN, "type": "DOMAIN"}
                        },
                        "tags": [
                            {"entity": {"urn": PROJECT_TAG_URN, "type": "TAG"}},
                            {"entity": {"urn": SANDBOX_TAG_URN, "type": "TAG"}},
                        ],
                    }
                }
            return response
        raise AssertionError(name)


class PinnedAssertions:
    def __init__(self, *, missing_assertion: bool = False) -> None:
        self.missing_assertion = missing_assertion
        self.calls: list[str] = []

    async def assertions_for_dataset(self, dataset_urn: str) -> dict[str, Any]:
        self.calls.append(dataset_urn)
        payload = assertion_graphql_payload(dataset_urn)
        if self.missing_assertion and dataset_urn == TABLE_URNS["raw.orders"]:
            payload["dataset"]["assertions"]["assertions"] = []
            payload["dataset"]["assertions"]["total"] = 0
        return payload


async def capture_pinned_context(
    workspace: Path,
    settings: Settings,
    *,
    mcp: PinnedMCP | None = None,
    assertions: PinnedAssertions | None = None,
):
    return await LiveDataHubContextReader(
        settings,
        mcp or PinnedMCP(),
        assertions or PinnedAssertions(),
        workspace_root=workspace,
    ).capture()


def expected_assertions() -> tuple[dict[str, str], ...]:
    return tuple(assertion_payload(spec) for spec in BASELINE_ASSERTIONS)


def expected_urns() -> tuple[str, ...]:
    return ALL_DATASET_URNS
