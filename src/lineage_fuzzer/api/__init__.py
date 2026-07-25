from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from lineage_fuzzer import __version__
from lineage_fuzzer.campaign.context import (
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
    app = FastAPI(
        title="Lineage Fuzzer",
        version=__version__,
        description="Safe, deterministic semantic data fault campaigns powered by DataHub.",
    )
    app.state.readiness_service = readiness_service or ReadinessService(resolved_settings)
    app.state.campaign_runner = campaign_runner or _default_campaign_runner(resolved_settings)
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
        manifest = app.state.campaign_runner.plan()
        context = app.state.campaign_runner.context
        return {
            "manifest": manifest.model_dump(mode="json"),
            "approval_sha256": manifest.sha256,
            "context_source": context.source,
            "context_sha256": context_sha256(context),
        }

    @app.post("/api/demo/run")
    async def campaign_run(request: CampaignRunRequest) -> dict[str, Any]:
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
                    app.state.campaign_runner.run,
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
        context = load_live_context_snapshot(context_path)
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
