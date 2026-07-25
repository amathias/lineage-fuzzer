from __future__ import annotations

from typing import Any

import httpx


class DataHubCatalogError(RuntimeError):
    """Raised when a supported DataHub OpenAPI entity operation fails."""


class DataHubCatalogClient:
    """Small async adapter for DataHub 1.6 OpenAPI v3 entity aspects."""

    def __init__(
        self,
        gms_url: str,
        *,
        token: str | None = None,
        timeout_seconds: float = 15,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._base_url = gms_url.rstrip("/")
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=timeout_seconds,
            transport=transport,
        )

    async def __aenter__(self) -> DataHubCatalogClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def upsert_aspect(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        aspect_name: str,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self._base_url}/openapi/v3/entity/{entity_type}?async=false"
        payload = [
            {
                "urn": entity_urn,
                aspect_name: {
                    "value": value,
                    "headers": {},
                },
            }
        ]
        return await self._request("POST", url, json=payload)

    async def get_entity(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        aspect_names: tuple[str, ...],
    ) -> Any:
        url = f"{self._base_url}/openapi/v3/entity/{entity_type}/batchGet"
        request: dict[str, Any] = {"urn": entity_urn}
        request.update({aspect_name: {} for aspect_name in aspect_names})
        return await self._request("POST", url, json=[request])

    async def set_soft_deleted(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        removed: bool,
    ) -> dict[str, Any]:
        return await self.upsert_aspect(
            entity_type=entity_type,
            entity_urn=entity_urn,
            aspect_name="status",
            value={"removed": removed},
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: Any,
    ) -> Any:
        response = await self._client.request(method, url, json=json)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise DataHubCatalogError(
                f"DataHub OpenAPI request failed with HTTP {response.status_code}"
            ) from error
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as error:
            raise DataHubCatalogError(
                "DataHub OpenAPI response was not valid JSON"
            ) from error
