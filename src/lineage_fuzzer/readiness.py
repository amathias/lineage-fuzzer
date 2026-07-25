from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from lineage_fuzzer.allocation import (
    AllocationViolation,
    validate_allocation_settings,
    validate_dataset_urn,
)
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.graphql import DataHubGraphQLClient
from lineage_fuzzer.datahub.mcp import DataHubMCPClient
from lineage_fuzzer.pipeline import CommerceFixture


class ReadinessCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    ready: bool
    detail: str


class ReadinessReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    checks: dict[str, ReadinessCheck]

    @property
    def ready(self) -> bool:
        return self.status == "ready"


class MCPReadinessClient(Protocol):
    async def probe(self) -> Any: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


class GraphQLReadinessClient(Protocol):
    async def __aenter__(self) -> GraphQLReadinessClient: ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    async def probe(self) -> dict[str, Any]: ...


MCPFactory = Callable[[Settings], MCPReadinessClient]
GraphQLFactory = Callable[[Settings], GraphQLReadinessClient]


class ReadinessService:
    """Non-mutating verification of local state and the allocated DataHub context."""

    def __init__(
        self,
        settings: Settings,
        *,
        workspace_root: Path | None = None,
        mcp_factory: MCPFactory | None = None,
        graphql_factory: GraphQLFactory | None = None,
    ) -> None:
        self.settings = settings
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self._mcp_factory = mcp_factory or _create_mcp_client
        self._graphql_factory = graphql_factory or _create_graphql_client

    async def check(self) -> ReadinessReport:
        checks: dict[str, ReadinessCheck] = {}
        database_path = self._check_allocation(checks)
        self._check_state(checks)
        self._check_fixture(checks, database_path)

        if database_path is None:
            checks["gms"] = ReadinessCheck(
                ready=False,
                detail="not evaluated because allocation validation failed",
            )
            checks["mcp"] = ReadinessCheck(
                ready=False,
                detail="not evaluated because allocation validation failed",
            )
            checks["catalog_allocation"] = ReadinessCheck(
                ready=False,
                detail="not evaluated because allocation validation failed",
            )
            return _report(checks)

        if not self.settings.datahub_token:
            missing_token = ReadinessCheck(
                ready=False,
                detail="DATAHUB_TOKEN is required for authenticated verification",
            )
            checks["gms"] = missing_token
            checks["mcp"] = missing_token
            checks["catalog_allocation"] = ReadinessCheck(
                ready=False,
                detail="not evaluated because authenticated DataHub access is unavailable",
            )
            return _report(checks)

        await self._check_datahub(checks)
        return _report(checks)

    def _check_allocation(self, checks: dict[str, ReadinessCheck]) -> Path | None:
        try:
            database_path = validate_allocation_settings(
                self.settings,
                workspace_root=self.workspace_root,
            )
        except AllocationViolation as error:
            checks["allocation"] = ReadinessCheck(ready=False, detail=str(error))
            return None
        checks["allocation"] = ReadinessCheck(
            ready=True,
            detail="runtime domain, tags, prefix, platform, environment, and paths match",
        )
        return database_path

    def _check_state(self, checks: dict[str, ReadinessCheck]) -> None:
        state_dir = _resolve(self.settings.state_dir, self.workspace_root)
        if not state_dir.is_dir():
            checks["state"] = ReadinessCheck(
                ready=False,
                detail="configured state directory does not exist",
            )
            return
        if not os.access(state_dir, os.R_OK | os.W_OK):
            checks["state"] = ReadinessCheck(
                ready=False,
                detail="configured state directory is not readable and writable",
            )
            return
        checks["state"] = ReadinessCheck(
            ready=True,
            detail="configured state directory exists with required access",
        )

    def _check_fixture(
        self,
        checks: dict[str, ReadinessCheck],
        database_path: Path | None,
    ) -> None:
        if database_path is None:
            checks["fixture"] = ReadinessCheck(
                ready=False,
                detail="not evaluated because allocation validation failed",
            )
            return
        if not database_path.is_file():
            checks["fixture"] = ReadinessCheck(
                ready=False,
                detail="allocated fixture database does not exist",
            )
            return
        try:
            fixture = CommerceFixture(
                database_path,
                fixture_root=_resolve(self.settings.fixture_root, self.workspace_root),
            )
            evidence = fixture.evidence()
            import duckdb

            with duckdb.connect(str(database_path), read_only=True) as connection:
                manifest = connection.execute(
                    """
                    SELECT seed, sandbox_marker, project_slug
                    FROM fixture_meta.seed_manifest
                    """
                ).fetchone()
            if manifest is None:
                raise RuntimeError("fixture seed manifest is missing")
            _, sandbox_marker, project_slug = manifest
            if sandbox_marker is not True or project_slug != self.settings.project_slug:
                raise RuntimeError("fixture sandbox marker or project slug is invalid")
        except Exception:
            checks["fixture"] = ReadinessCheck(
                ready=False,
                detail="fixture could not be verified read-only",
            )
            return
        checks["fixture"] = ReadinessCheck(
            ready=True,
            detail=f"seed {evidence.seed} and {len(evidence.tables)} checksums verified read-only",
        )

    async def _check_datahub(self, checks: dict[str, ReadinessCheck]) -> None:
        try:
            async with self._graphql_factory(self.settings) as graphql:
                await graphql.probe()
        except Exception:
            checks["gms"] = ReadinessCheck(
                ready=False,
                detail="authenticated GraphQL probe failed",
            )
        else:
            checks["gms"] = ReadinessCheck(
                ready=True,
                detail="authenticated GraphQL probe succeeded",
            )

        try:
            mcp = self._mcp_factory(self.settings)
            probe = await mcp.probe()
        except Exception:
            checks["mcp"] = ReadinessCheck(
                ready=False,
                detail="authenticated MCP capability probe failed",
            )
            checks["catalog_allocation"] = ReadinessCheck(
                ready=False,
                detail="not evaluated because MCP is unavailable",
            )
            return

        if not probe.ready:
            checks["mcp"] = ReadinessCheck(
                ready=False,
                detail=f"required MCP tools missing: {', '.join(probe.missing_tools)}",
            )
            checks["catalog_allocation"] = ReadinessCheck(
                ready=False,
                detail="not evaluated because required MCP tools are missing",
            )
            return
        checks["mcp"] = ReadinessCheck(
            ready=True,
            detail="required non-mutating MCP context tools are available",
        )

        try:
            payload = await mcp.call_tool(
                "get_entities",
                {"urns": [self.settings.readiness_dataset_urn]},
            )
            entity = _find_entity(payload, self.settings.readiness_dataset_urn)
            if entity is None:
                raise AllocationViolation("allocated readiness entity was not returned")
            _validate_catalog_entity(entity, self.settings)
        except Exception:
            checks["catalog_allocation"] = ReadinessCheck(
                ready=False,
                detail="catalog entity failed namespace, domain, tag, or sandbox verification",
            )
            return
        checks["catalog_allocation"] = ReadinessCheck(
            ready=True,
            detail="catalog entity matches namespace, domain, project tag, and sandbox marker",
        )


def _create_mcp_client(settings: Settings) -> DataHubMCPClient:
    return DataHubMCPClient(
        settings.datahub_mcp_url,
        token=settings.datahub_token,
        timeout_seconds=settings.datahub_mcp_timeout_seconds,
    )


def _create_graphql_client(settings: Settings) -> DataHubGraphQLClient:
    endpoint = f"{settings.datahub_gms_url.rstrip('/')}/api/graphql"
    return DataHubGraphQLClient(
        endpoint,
        token=settings.datahub_token,
        timeout_seconds=settings.datahub_mcp_timeout_seconds,
    )


def _report(checks: dict[str, ReadinessCheck]) -> ReadinessReport:
    ready = all(check.ready for check in checks.values())
    return ReadinessReport(status="ready" if ready else "not_ready", checks=checks)


def _resolve(path: Path, workspace_root: Path) -> Path:
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve(strict=False)


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


def _validate_catalog_entity(entity: dict[str, Any], settings: Settings) -> None:
    urn = entity.get("urn")
    if not isinstance(urn, str):
        raise AllocationViolation("catalog entity has no URN")
    validate_dataset_urn(urn, settings)

    serialized = json.dumps(entity, sort_keys=True).casefold()
    required_strings = (
        settings.datahub_domain.casefold(),
        settings.datahub_project_tag.casefold(),
        settings.required_sandbox_tag.casefold(),
    )
    if any(value not in serialized for value in required_strings):
        raise AllocationViolation("catalog entity is missing domain or required tags")
    if not _has_marker(
        entity,
        key=settings.required_marker_key,
        expected_value=settings.required_marker_value,
    ):
        raise AllocationViolation("catalog entity is missing its sandbox marker")


def _has_marker(node: Any, *, key: str, expected_value: str) -> bool:
    if isinstance(node, dict):
        direct = node.get(key)
        if str(direct).casefold() == expected_value.casefold():
            return True
        if (
            str(node.get("key", "")).casefold() == key.casefold()
            and str(node.get("value", "")).casefold() == expected_value.casefold()
        ):
            return True
        return any(
            _has_marker(child, key=key, expected_value=expected_value)
            for child in node.values()
        )
    if isinstance(node, list):
        return any(
            _has_marker(child, key=key, expected_value=expected_value) for child in node
        )
    return False
