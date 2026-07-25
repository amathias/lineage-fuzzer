from __future__ import annotations

from fastapi import FastAPI

from lineage_fuzzer import __version__


def create_app() -> FastAPI:
    app = FastAPI(
        title="Lineage Fuzzer",
        version=__version__,
        description="Safe, deterministic semantic data fault campaigns powered by DataHub.",
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
