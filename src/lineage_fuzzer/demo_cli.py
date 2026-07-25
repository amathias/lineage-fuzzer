from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from lineage_fuzzer.campaign.context import (
    ContextCaptureError,
    LiveDataHubContextReader,
    context_sha256,
    demo_context_snapshot,
    load_live_context_snapshot,
    save_live_context_snapshot,
)
from lineage_fuzzer.campaign.generation import GeneratedSQLViolation
from lineage_fuzzer.campaign.runner import CampaignExecutionError, CampaignRunner
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.graphql import DataHubGraphQLClient
from lineage_fuzzer.datahub.mcp import DataHubMCPClient
from lineage_fuzzer.pipeline.faults import FaultAdapterError
from lineage_fuzzer.safety import SafetyViolation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lineage_fuzzer.demo_cli",
        description="Plan or run the deterministic Lineage Fuzzer judge campaign.",
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    subcommands = parser.add_subparsers(dest="command", required=True)
    parser.add_argument("--context-file", type=Path)
    subcommands.add_parser("plan", help="Print the immutable campaign and approval digest.")
    run = subcommands.add_parser("run", help="Run, measure, and restore the campaign.")
    capture = subcommands.add_parser(
        "capture-live-context",
        help="Read and persist allocated lineage, schema, entity, and assertion context.",
    )
    capture.add_argument("--output", type=Path)
    run.add_argument("--approval-sha256", required=True)
    run.add_argument("--approved-by", default="judge-demo")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings()
        if args.command == "capture-live-context":
            payload = asyncio.run(_capture_live_context(settings, args))
            runner = None
        elif args.command == "plan":
            runner = _runner(settings, args)
            manifest = runner.plan()
            payload = {
                "approval_sha256": manifest.sha256,
                "context_source": runner.context.source,
                "context_sha256": context_sha256(runner.context),
                "manifest": manifest.model_dump(mode="json"),
            }
        else:
            runner = _runner(settings, args)
            payload = runner.run(
                approval_sha256=args.approval_sha256,
                approved_by=args.approved_by,
            ).model_dump(mode="json")
    except (
        CampaignExecutionError,
        ContextCaptureError,
        FaultAdapterError,
        GeneratedSQLViolation,
        SafetyViolation,
        ValidationError,
    ) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


async def _capture_live_context(
    settings: Settings,
    args: argparse.Namespace,
) -> dict[str, object]:
    if not settings.datahub_token:
        raise ContextCaptureError(
            "DATAHUB_TOKEN is required for authenticated live context capture"
        )
    workspace_root = args.workspace_root.resolve()
    state_root = _resolve(settings.state_dir, workspace_root)
    output_path = (
        _resolve(args.output, workspace_root)
        if args.output
        else state_root / "campaign-context.json"
    )
    mcp = DataHubMCPClient(
        settings.datahub_mcp_url,
        token=settings.datahub_token,
        timeout_seconds=settings.datahub_mcp_timeout_seconds,
    )
    try:
        probe = await mcp.probe()
        if not probe.ready:
            raise ContextCaptureError(
                f"DataHub MCP is missing required tools: {probe.missing_tools}"
            )
        graphql_endpoint = f"{settings.datahub_gms_url.rstrip('/')}/api/graphql"
        async with DataHubGraphQLClient(
            graphql_endpoint,
            token=settings.datahub_token,
            timeout_seconds=settings.datahub_mcp_timeout_seconds,
        ) as graphql:
            context = await LiveDataHubContextReader(settings, mcp, graphql).capture()
    except ContextCaptureError:
        raise
    except Exception as exc:
        raise ContextCaptureError("live DataHub context capture failed closed") from exc
    saved = save_live_context_snapshot(output_path, context)
    return {
        "status": "captured",
        "path": str(saved),
        "source": context.source,
        "context_sha256": context_sha256(context),
        "entities": len(context.entities),
        "lineage_edges": len(context.lineage),
        "assertion_payloads": len(context.assertions),
    }


def _runner(settings: Settings, args: argparse.Namespace) -> CampaignRunner:
    workspace_root = args.workspace_root.resolve()
    state_root = _resolve(settings.state_dir, workspace_root)
    artifact_root = (
        _resolve(args.artifact_root, workspace_root)
        if args.artifact_root
        else state_root / "generated"
    )
    configured_context = args.context_file or settings.campaign_context_file
    context = (
        load_live_context_snapshot(_resolve(configured_context, workspace_root))
        if configured_context is not None
        else demo_context_snapshot()
    )
    evidence_root = (
        _resolve(args.evidence_root, workspace_root)
        if args.evidence_root
        else state_root / "campaign-evidence"
    )
    return CampaignRunner(
        settings,
        context,
        workspace_root=workspace_root,
        artifact_root=artifact_root,
        evidence_root=evidence_root,
    )


def _resolve(path: Path, workspace_root: Path) -> Path:
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve(strict=False)


if __name__ == "__main__":
    raise SystemExit(main())
