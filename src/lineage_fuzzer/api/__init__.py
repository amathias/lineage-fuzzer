from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from lineage_fuzzer import __version__
from lineage_fuzzer.campaign.context import (
    ContextCaptureError,
    context_sha256,
    demo_context_snapshot,
    load_live_context_snapshot,
)
from lineage_fuzzer.campaign.models import CampaignExecutionReport
from lineage_fuzzer.campaign.runner import CampaignExecutionError, CampaignRunner
from lineage_fuzzer.config import Settings
from lineage_fuzzer.domain.models import CampaignManifest, DataHubContextSnapshot
from lineage_fuzzer.readiness import ReadinessReport, ReadinessService
from lineage_fuzzer.safety import SafetyViolation


class CampaignProvider(Protocol):
    context: DataHubContextSnapshot

    def plan(self) -> CampaignManifest: ...

    def run(
        self,
        *,
        approval_sha256: str,
        approved_by: str,
    ) -> CampaignExecutionReport: ...


class CampaignRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approved_by: str = Field(default="judge-demo", min_length=1, max_length=80)


class ReadinessProvider(Protocol):
    async def check(self) -> ReadinessReport: ...


def create_app(
    *,
    settings: Settings | None = None,
    readiness_service: ReadinessProvider | None = None,
    campaign_runner: CampaignProvider | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    docs_enabled = resolved_settings.environment.casefold() in {
        "development",
        "local",
        "test",
    }
    app = FastAPI(
        title="Lineage Fuzzer",
        version=__version__,
        description="Safe, deterministic semantic data fault campaigns powered by DataHub.",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.state.readiness_service = readiness_service or ReadinessService(
        resolved_settings,
        workspace_root=Path.cwd(),
    )
    app.state.campaign_error = None
    try:
        app.state.campaign_runner = campaign_runner or _default_campaign_runner(resolved_settings)
    except ContextCaptureError as exc:
        app.state.campaign_runner = None
        app.state.campaign_error = str(exc)
    app.state.settings = resolved_settings
    app.state.campaign_lock = asyncio.Lock()

    @app.get("/", response_class=HTMLResponse)
    async def judge_demo() -> HTMLResponse:
        demo_path = Path(__file__).resolve().parents[1] / "web" / "index.html"
        return HTMLResponse(demo_path.read_text(encoding="utf-8"))

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/readiness")
    async def readiness() -> JSONResponse:
        report = await app.state.readiness_service.check()
        return JSONResponse(
            status_code=200 if report.ready else 503,
            content=report.model_dump(mode="json"),
        )

    @app.get("/api/demo/plan")
    async def campaign_plan() -> dict[str, Any]:
        runner = app.state.campaign_runner
        if runner is None:
            raise HTTPException(status_code=503, detail=app.state.campaign_error)
        manifest = runner.plan()
        context = runner.context
        if resolved_settings.is_hackathon and context.source != "datahub-mcp-live":
            raise HTTPException(
                status_code=503,
                detail="hackathon mode requires current verified live DataHub context",
            )
        run_enabled = resolved_settings.injection_enabled and (
            not resolved_settings.is_hackathon or context.source == "datahub-mcp-live"
        )
        return {
            "manifest": manifest.model_dump(mode="json"),
            "run_enabled": run_enabled,
            "live_context_required": resolved_settings.is_hackathon,
            "candidate_sha": resolved_settings.candidate_sha,
            "graph": {
                "nodes": [
                    {
                        "urn": entity["urn"],
                        "name": entity["name"],
                        "schema_fields": entity["schemaFields"],
                    }
                    for entity in context.entities
                ],
                "edges": [
                    edge.model_dump(mode="json") for edge in context.lineage
                ],
            },
            "approval_sha256": manifest.sha256,
            "context_source": context.source,
            "context_sha256": context_sha256(context),
        }

    @app.post("/api/demo/run")
    async def campaign_run(request: CampaignRunRequest) -> dict[str, Any]:
        runner = app.state.campaign_runner
        if runner is None:
            raise HTTPException(status_code=503, detail=app.state.campaign_error)
        if resolved_settings.is_hackathon and runner.context.source != "datahub-mcp-live":
            raise HTTPException(
                status_code=503, detail="verified live context is required"
            )
        lock: asyncio.Lock = app.state.campaign_lock
        if lock.locked():
            raise HTTPException(
                status_code=409,
                detail="a campaign is already running against the disposable fixture",
            )
        await lock.acquire()
        try:
            try:
                report = await asyncio.to_thread(
                    runner.run,
                    approval_sha256=request.approval_sha256,
                    approved_by=request.approved_by,
                )
            except SafetyViolation as exc:
                raise HTTPException(status_code=403, detail=str(exc)) from exc
            except CampaignExecutionError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
        finally:
            lock.release()
        return report.model_dump(mode="json")

    return app


def _default_campaign_runner(settings: Settings) -> CampaignRunner:
    workspace_root = Path.cwd().resolve()
    context = demo_context_snapshot()
    if settings.campaign_context_file is not None:
        context_path = settings.campaign_context_file
        context_path = context_path if context_path.is_absolute() else workspace_root / context_path
        context = load_live_context_snapshot(
            context_path,
            settings=settings,
            workspace_root=workspace_root,
        )
    elif settings.is_hackathon:
        raise ContextCaptureError(
            "hackathon mode requires LINEAGE_FUZZER_CONTEXT_FILE and its receipt"
        )
    state_root = settings.state_dir
    state_root = state_root if state_root.is_absolute() else workspace_root / state_root
    return CampaignRunner(
        settings=settings,
        workspace_root=workspace_root,
        context=context,
        artifact_root=state_root / "generated",
        evidence_root=state_root / "campaign-evidence",
    )


app = create_app()

__all__ = ["app", "create_app"]
