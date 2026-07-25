from __future__ import annotations

import json
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

REQUIRED_CONTEXT_TOOLS = frozenset(
    {
        "get_entities",
        "get_lineage",
        "list_schema_fields",
    }
)


@dataclass(frozen=True)
class DataHubMCPProbe:
    endpoint: str
    available_tools: tuple[str, ...]
    required_tools: tuple[str, ...]

    @property
    def missing_tools(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.required_tools) - set(self.available_tools)))

    @property
    def ready(self) -> bool:
        return not self.missing_tools


class DataHubMCPClient:
    """Direct MCP adapter for context reads from self-hosted DataHub."""

    def __init__(
        self,
        endpoint: str,
        *,
        token: str | None = None,
        timeout_seconds: float = 15,
    ) -> None:
        self.endpoint = endpoint
        self._token = token
        self._timeout_seconds = timeout_seconds

    async def list_tools(self) -> tuple[str, ...]:
        async with self._session() as session:
            response = await session.list_tools()
            return tuple(sorted(tool.name for tool in response.tools))

    async def probe(self) -> DataHubMCPProbe:
        tools = await self.list_tools()
        return DataHubMCPProbe(
            endpoint=self.endpoint,
            available_tools=tools,
            required_tools=tuple(sorted(REQUIRED_CONTEXT_TOOLS)),
        )

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        async with self._session() as session:
            response = await session.call_tool(name, arguments)
            if response.isError:
                details = self._decode_content(response.content)
                raise RuntimeError(f"DataHub MCP tool {name!r} failed: {details}")
            return self._decode_content(response.content)

    def _session(self) -> _McpSessionContext:
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        return _McpSessionContext(
            endpoint=self.endpoint,
            headers=headers,
            timeout_seconds=self._timeout_seconds,
        )

    @staticmethod
    def _decode_content(content: list[Any]) -> Any:
        values: list[Any] = []
        for block in content:
            text = getattr(block, "text", None)
            if text is None:
                values.append(block.model_dump(mode="json"))
                continue
            try:
                values.append(json.loads(text))
            except json.JSONDecodeError:
                values.append(text)
        if len(values) == 1:
            return values[0]
        return values


class _McpSessionContext:
    def __init__(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> None:
        self._endpoint = endpoint
        self._headers = headers
        self._timeout_seconds = timeout_seconds
        self._stack: AsyncExitStack | None = None

    async def __aenter__(self) -> ClientSession:
        self._stack = AsyncExitStack()
        http_client = await self._stack.enter_async_context(
            httpx.AsyncClient(
                headers=self._headers,
                timeout=self._timeout_seconds,
            )
        )
        read_stream, write_stream, _ = await self._stack.enter_async_context(
            streamable_http_client(
                self._endpoint,
                http_client=http_client,
            )
        )
        session = await self._stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()
        return session

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._stack is not None:
            await self._stack.aclose()
