from __future__ import annotations

import time
from typing import Any

import httpx

from lineage_fuzzer.datahub.protocols import WritebackReceipt


class DataHubGraphQLError(RuntimeError):
    pass


class DataHubGraphQLClient:
    """Supported DataHub GraphQL operations for assertion context and writeback."""

    def __init__(
        self,
        endpoint: str,
        *,
        token: str | None = None,
        timeout_seconds: float = 15,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._endpoint = endpoint.rstrip("/")
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=timeout_seconds,
            transport=transport,
        )

    async def __aenter__(self) -> DataHubGraphQLClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def probe(self) -> dict[str, Any]:
        return await self._execute("query LineageFuzzerProbe { __typename }")

    async def upsert_custom_assertion(
        self,
        *,
        assertion_urn: str,
        entity_urn: str,
        assertion_type: str,
        description: str,
        logic: str,
        field_path: str | None = None,
    ) -> WritebackReceipt:
        mutation = """
        mutation UpsertLineageFuzzerAssertion(
          $urn: String!,
          $input: UpsertCustomAssertionInput!
        ) {
          upsertCustomAssertion(urn: $urn, input: $input) {
            urn
          }
        }
        """
        input_value: dict[str, Any] = {
            "entityUrn": entity_urn,
            "type": assertion_type,
            "description": description,
            "platform": {"name": "Lineage Fuzzer"},
            "logic": logic,
        }
        if field_path:
            input_value["fieldPath"] = field_path

        response = await self._execute(
            mutation,
            variables={"urn": assertion_urn, "input": input_value},
        )
        returned_urn = response["upsertCustomAssertion"]["urn"]
        return WritebackReceipt(
            operation="upsert_custom_assertion",
            entity_urn=returned_urn,
            response=response,
        )

    async def report_assertion_result(
        self,
        *,
        assertion_urn: str,
        result_type: str,
        properties: dict[str, str],
        timestamp_millis: int | None = None,
    ) -> WritebackReceipt:
        mutation = """
        mutation ReportLineageFuzzerAssertionResult(
          $urn: String!,
          $result: AssertionResultInput!
        ) {
          reportAssertionResult(urn: $urn, result: $result)
        }
        """
        result = {
            "timestampMillis": timestamp_millis or int(time.time() * 1000),
            "type": result_type,
            "properties": [
                {"key": key, "value": value} for key, value in sorted(properties.items())
            ],
        }
        response = await self._execute(
            mutation,
            variables={"urn": assertion_urn, "result": result},
        )
        return WritebackReceipt(
            operation="report_assertion_result",
            entity_urn=assertion_urn,
            response=response,
        )

    async def assertions_for_dataset(self, dataset_urn: str) -> dict[str, Any]:
        query = """
        query LineageFuzzerDatasetAssertions($urn: String!) {
          dataset(urn: $urn) {
            assertions(start: 0, count: 1000) {
              total
              assertions {
                urn
                info {
                  type
                  description
                  customAssertion {
                    type
                    entityUrn
                    logic
                  }
                }
                runEvents(status: COMPLETE, limit: 1) {
                  runEvents {
                    timestampMillis
                    result {
                      type
                      nativeResults {
                        key
                        value
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        return await self._execute(query, variables={"urn": dataset_urn})

    async def _execute(
        self,
        query: str,
        *,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.post(
            self._endpoint,
            json={"query": query, "variables": variables or {}},
        )
        response.raise_for_status()
        payload = response.json()
        if errors := payload.get("errors"):
            messages = "; ".join(error.get("message", str(error)) for error in errors)
            raise DataHubGraphQLError(messages)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise DataHubGraphQLError(
                "DataHub GraphQL response did not contain an object data field"
            )
        return data
