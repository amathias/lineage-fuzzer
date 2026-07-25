from __future__ import annotations

import argparse
import asyncio
import json
import socket
import sys
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlparse

import uvicorn

from lineage_fuzzer.allocation import AllocationViolation, validate_allocation_settings
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.catalog import DataHubCatalogClient, DataHubCatalogError
from lineage_fuzzer.datahub.fixture_catalog import (
    CatalogFixtureService,
    catalog_plan,
)
from lineage_fuzzer.datahub.graphql import DataHubGraphQLClient
from lineage_fuzzer.datahub.mcp import DataHubMCPClient
from lineage_fuzzer.datahub.proof import (
    DEFAULT_PROOF_PLAN,
    DataHubAssertionProofService,
    ProofApprovalViolation,
    ProofVerificationError,
)
from lineage_fuzzer.datahub.receipts import ReceiptPathViolation, sha256_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lineage-fuzzer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the campaign API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    subparsers.add_parser(
        "probe-datahub",
        help="Verify MCP context tools and GraphQL connectivity against real DataHub",
    )



    subparsers.add_parser(
        "show-datahub-plans",
        help="Print immutable catalog and assertion plans with approval SHA-256 values",
    )
    for command, help_text in (
        (
            "seed-datahub-fixture",
            "Seed and verify only the exact allocated DataHub catalog fixture",
        ),
        (
            "reset-datahub-fixture",
            "Deterministically replay the exact allocated catalog fixture aspects",
        ),
        (
            "run-datahub-proof",
            "Write, report, re-read, and restore the fixed sandbox assertion",
        ),
        (
            "reset-datahub-proof",
            "Soft-delete only the fixed sandbox proof assertion",
        ),
    ):
        operation = subparsers.add_parser(command, help=help_text)
        operation.add_argument(
            "--approval-sha256",
            required=True,
            help="Exact SHA-256 printed by show-datahub-plans",
        )
    return parser


async def _assert_datahub_port_reachable(settings: Settings) -> None:
    parsed = urlparse(settings.datahub_gms_url)
    host = parsed.hostname
    if not host:
        raise ConnectionError(f"invalid DATAHUB_GMS_URL: {settings.datahub_gms_url}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    def connect() -> None:
        with socket.create_connection(
            (host, port),
            timeout=settings.datahub_mcp_timeout_seconds,
        ):
            return

    try:
        await asyncio.to_thread(connect)
    except OSError as error:
        raise ConnectionError(f"DataHub is not reachable at {host}:{port}") from error


async def _probe_datahub(settings: Settings) -> int:
    await _assert_datahub_port_reachable(settings)
    mcp_client = DataHubMCPClient(
        settings.datahub_mcp_url,
        token=settings.datahub_token,
        timeout_seconds=settings.datahub_mcp_timeout_seconds,
    )
    mcp_probe = await mcp_client.probe()
    graphql_endpoint = f"{settings.datahub_gms_url.rstrip('/')}/api/graphql"
    async with DataHubGraphQLClient(
        graphql_endpoint,
        token=settings.datahub_token,
        timeout_seconds=settings.datahub_mcp_timeout_seconds,
    ) as graphql:
        graphql_response = await graphql.probe()

    output = {
        "mcp": {
            "endpoint": mcp_probe.endpoint,
            "available_tools": mcp_probe.available_tools,
            "required_tools": mcp_probe.required_tools,
            "missing_tools": mcp_probe.missing_tools,
            "ready": mcp_probe.ready,
        },
        "graphql": {
            "endpoint": graphql_endpoint,
            "response": graphql_response,
            "ready": True,
        },
    }
    print(json.dumps(output, indent=2))
    return 0 if mcp_probe.ready else 1


def _require_datahub_token(settings: Settings) -> None:
    if not settings.datahub_token:
        raise ConnectionError(
            "DATAHUB_TOKEN is required and must be supplied only through the environment"
        )


def _show_datahub_plans(settings: Settings) -> int:
    validate_allocation_settings(settings, workspace_root=Path.cwd())
    fixture_plan = catalog_plan(settings)
    output = {
        "catalog_fixture": {
            "approval_sha256": sha256_json(fixture_plan),
            "plan": fixture_plan,
        },
        "assertion_proof": {
            "approval_sha256": DEFAULT_PROOF_PLAN.sha256,
            "plan": DEFAULT_PROOF_PLAN.model_dump(mode="json"),
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


async def _catalog_fixture(
    settings: Settings,
    *,
    approval_sha256: str,
    reset: bool,
) -> int:
    _require_datahub_token(settings)
    async with DataHubCatalogClient(
        settings.datahub_gms_url,
        token=settings.datahub_token,
        timeout_seconds=settings.datahub_mcp_timeout_seconds,
    ) as catalog:
        service = CatalogFixtureService(
            settings,
            catalog,
            workspace_root=Path.cwd(),
        )
        result = (
            await service.reset(approval_sha256=approval_sha256)
            if reset
            else await service.seed(approval_sha256=approval_sha256)
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


async def _datahub_proof(
    settings: Settings,
    *,
    approval_sha256: str,
    reset: bool,
) -> int:
    _require_datahub_token(settings)
    graphql_endpoint = f"{settings.datahub_gms_url.rstrip('/')}/api/graphql"
    async with (
        DataHubCatalogClient(
            settings.datahub_gms_url,
            token=settings.datahub_token,
            timeout_seconds=settings.datahub_mcp_timeout_seconds,
        ) as catalog,
        DataHubGraphQLClient(
            graphql_endpoint,
            token=settings.datahub_token,
            timeout_seconds=settings.datahub_mcp_timeout_seconds,
        ) as graphql,
    ):
        service = DataHubAssertionProofService(
            settings,
            graphql,
            catalog,
            workspace_root=Path.cwd(),
        )
        result = (
            await service.reset(approval_sha256=approval_sha256)
            if reset
            else await service.run(approval_sha256=approval_sha256)
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _run_guarded(operation: object) -> int:
    try:
        return asyncio.run(operation)
    except (
        AllocationViolation,
        ConnectionError,
        DataHubCatalogError,
        ProofApprovalViolation,
        ProofVerificationError,
        ReceiptPathViolation,
    ) as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": type(error).__name__,
                    "error": "DataHub operation failed closed; inspect token-free service logs",
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        uvicorn.run("lineage_fuzzer.api:app", host=args.host, port=args.port, reload=False)
        return 0
    if args.command == "probe-datahub":
        try:
            return asyncio.run(_probe_datahub(Settings()))
        except ConnectionError as error:
            print(
                json.dumps(
                    {
                        "ready": False,
                        "error": str(error),
                        "action": "Install/start Docker and run the pinned DataHub quickstart.",
                    },
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2
    if args.command == "show-datahub-plans":
        try:
            return _show_datahub_plans(Settings())
        except AllocationViolation as error:
            print(
                json.dumps({"ok": False, "error": str(error)}, indent=2),
                file=sys.stderr,
            )
            return 2
    if args.command in {"seed-datahub-fixture", "reset-datahub-fixture"}:
        return _run_guarded(
            _catalog_fixture(
                Settings(),
                approval_sha256=args.approval_sha256,
                reset=args.command == "reset-datahub-fixture",
            )
        )
    if args.command in {"run-datahub-proof", "reset-datahub-proof"}:
        return _run_guarded(
            _datahub_proof(
                Settings(),
                approval_sha256=args.approval_sha256,
                reset=args.command == "reset-datahub-proof",
            )
        )
    raise AssertionError(f"unhandled command: {args.command}")
