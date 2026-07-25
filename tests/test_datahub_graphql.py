from __future__ import annotations

import json

import httpx
import pytest

from lineage_fuzzer.datahub.graphql import DataHubGraphQLClient, DataHubGraphQLError


@pytest.mark.asyncio
async def test_upserts_custom_assertion_with_schema_grounded_logic() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "data": {
                    "upsertCustomAssertion": {"urn": "urn:li:assertion:lineage-fuzzer-freshness"}
                }
            },
        )

    client = DataHubGraphQLClient(
        "http://datahub.test/api/graphql",
        token="secret",
        transport=httpx.MockTransport(handler),
    )
    receipt = await client.upsert_custom_assertion(
        assertion_urn="urn:li:assertion:lineage-fuzzer-freshness",
        entity_urn="urn:li:dataset:orders",
        assertion_type="Lineage Fuzzer Generated Control",
        description="Newest partition must be current",
        logic="SELECT 1 WHERE max_order_date < current_date",
        field_path="order_date",
    )
    await client.aclose()

    variables = captured["variables"]
    assert variables["input"]["fieldPath"] == "order_date"
    assert variables["input"]["platform"] == {"name": "Lineage Fuzzer"}
    assert receipt.entity_urn == "urn:li:assertion:lineage-fuzzer-freshness"


@pytest.mark.asyncio
async def test_reports_sorted_campaign_evidence_properties() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"data": {"reportAssertionResult": True}})

    client = DataHubGraphQLClient(
        "http://datahub.test/api/graphql",
        transport=httpx.MockTransport(handler),
    )
    await client.report_assertion_result(
        assertion_urn="urn:li:assertion:test",
        result_type="SUCCESS",
        properties={"seed": "42", "campaign_id": "campaign-1"},
        timestamp_millis=123,
    )
    await client.aclose()

    properties = captured["variables"]["result"]["properties"]
    assert properties == [
        {"key": "campaign_id", "value": "campaign-1"},
        {"key": "seed", "value": "42"},
    ]


@pytest.mark.asyncio
async def test_surfaces_graphql_errors() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "Edit Assertions denied"}]})

    client = DataHubGraphQLClient(
        "http://datahub.test/api/graphql",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(DataHubGraphQLError, match="Edit Assertions denied"):
        await client.probe()
    await client.aclose()
