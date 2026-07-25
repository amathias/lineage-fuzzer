from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from lineage_fuzzer import __version__
from lineage_fuzzer.config import Settings
from lineage_fuzzer.readiness import ReadinessReport, ReadinessService


class ReadinessProvider(Protocol):
    async def check(self) -> ReadinessReport: ...


def create_app(
    *,
    settings: Settings | None = None,
    readiness_service: ReadinessProvider | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Lineage Fuzzer",
        version=__version__,
        description="Safe, deterministic semantic data fault campaigns powered by DataHub.",
    )
    app.state.readiness_service = readiness_service or ReadinessService(settings or Settings())

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

    return app


app = create_app()

__all__ = ["app", "create_app"]
