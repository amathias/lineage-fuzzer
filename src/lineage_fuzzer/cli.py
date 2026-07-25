from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence

import uvicorn

from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.graphql import DataHubGraphQLClient
from lineage_fuzzer.datahub.mcp import DataHubMCPClient


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
    return parser


async def _probe_datahub(settings: Settings) -> int:
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


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        uvicorn.run("lineage_fuzzer.api:app", host=args.host, port=args.port, reload=False)
        return 0
    if args.command == "probe-datahub":
        return asyncio.run(_probe_datahub(Settings()))
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
