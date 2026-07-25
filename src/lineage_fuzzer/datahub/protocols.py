from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class WritebackReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation: str
    entity_urn: str
    response: dict[str, Any]


class ContextReader(Protocol):
    async def list_tools(self) -> tuple[str, ...]: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


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
    ) -> WritebackReceipt: ...

    async def report_assertion_result(
        self,
        *,
        assertion_urn: str,
        result_type: str,
        properties: dict[str, str],
        timestamp_millis: int | None = None,
    ) -> WritebackReceipt: ...
