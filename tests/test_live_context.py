from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lineage_fuzzer.api import create_app
from lineage_fuzzer.campaign.context import (
    ContextCaptureError,
    demo_context_snapshot,
    load_live_context_snapshot,
    save_live_context_snapshot,
)
from lineage_fuzzer.config import Settings
from lineage_fuzzer.demo_cli import main


def live_context():
    return demo_context_snapshot().model_copy(update={"source": "datahub-mcp-live"})


def test_live_context_store_round_trips_typed_capture(tmp_path: Path) -> None:
    path = tmp_path / "campaign-context.json"
    context = live_context()

    saved = save_live_context_snapshot(path, context)
    loaded = load_live_context_snapshot(saved)

    assert loaded == context
    assert loaded.source == "datahub-mcp-live"
    assert not path.with_suffix(".json.tmp").exists()


def test_live_context_store_rejects_offline_topology(tmp_path: Path) -> None:
    with pytest.raises(ContextCaptureError, match="not captured from live DataHub"):
        save_live_context_snapshot(
            tmp_path / "campaign-context.json",
            demo_context_snapshot(),
        )

    with pytest.raises(ContextCaptureError, match="invalid"):
        load_live_context_snapshot(tmp_path / "missing.json")


def test_api_uses_explicit_saved_live_context(tmp_path: Path) -> None:
    context_path = save_live_context_snapshot(
        tmp_path / "campaign-context.json",
        live_context(),
    )
    settings = Settings(
        LINEAGE_FUZZER_CONTEXT_FILE=str(context_path),
        _env_file=None,
    )

    response = TestClient(create_app(settings=settings)).get("/api/demo/plan")

    assert response.status_code == 200
    assert response.json()["context_source"] == "datahub-mcp-live"


def test_live_capture_fails_closed_without_token(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("DATAHUB_TOKEN", raising=False)

    exit_code = main(["capture-live-context"])

    output = capsys.readouterr().out
    assert exit_code == 2
    assert '"status": "blocked"' in output
    assert "DATAHUB_TOKEN is required" in output
