from __future__ import annotations

import httpx
import pytest

from lineage_fuzzer.datahub.graphql import DataHubGraphQLClient


@pytest.mark.asyncio
async def test_posts_to_exact_graphql_endpoint_without_trailing_slash() -> None:
    request_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        request_urls.append(str(request.url))
        return httpx.Response(200, json={"data": {"__typename": "Query"}})

    client = DataHubGraphQLClient(
        "http://datahub.test/api/graphql/",
        transport=httpx.MockTransport(handler),
    )
    await client.probe()
    await client.aclose()

    assert request_urls == ["http://datahub.test/api/graphql"]
