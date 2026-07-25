import asyncio
from typing import Any

from fastapi.testclient import TestClient

from lineage_fuzzer.api import create_app
from lineage_fuzzer.campaign.context import demo_context_snapshot
from lineage_fuzzer.campaign.planner import build_campaign_manifest
from lineage_fuzzer.config import Settings


class FakeReport:
    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return {
            "status": "proved_and_restored",
            "restoration_verified": True,
            "replay_sha256": "a" * 64,
        }


class FakeCampaignRunner:
    def __init__(self) -> None:
        self.context = demo_context_snapshot()
        self.manifest = build_campaign_manifest(
            self.context,
            database_path="demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb",
        )

    def plan(self):
        return self.manifest

    def run(self, *, approval_sha256: str, approved_by: str):
        assert approval_sha256 == self.manifest.sha256
        assert approved_by == "api-test"
        return FakeReport()


def test_judge_page_and_plan_expose_the_fixed_campaign() -> None:
    runner = FakeCampaignRunner()
    client = TestClient(create_app(campaign_runner=runner))

    page = client.get("/")
    plan = client.get("/api/demo/plan")

    assert page.status_code == 200
    assert "Lineage Fuzzer" in page.text
    assert plan.status_code == 200
    payload = plan.json()
    assert payload["approval_sha256"] == runner.manifest.sha256
    assert "Separate live-proof baseline" in page.text
    assert "Verified candidate" not in page.text
    assert "button.disabled = !plan.run_enabled" in page.text
    assert "renderGraph(plan.graph)" in page.text
    assert payload["context_source"] == "local-fixture-topology"
    assert len(payload["manifest"]["faults"]) == 3
    assert len(payload["graph"]["nodes"]) == 6
    assert len(payload["graph"]["edges"]) == 5
    assert payload["run_enabled"] is False


def test_judge_run_passes_the_exact_approved_digest() -> None:
    runner = FakeCampaignRunner()
    response = TestClient(create_app(campaign_runner=runner)).post(
        "/api/demo/run",
        json={
            "approval_sha256": runner.manifest.sha256,
            "approved_by": "api-test",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "proved_and_restored"
    assert response.json()["restoration_verified"] is True
def test_judge_run_rejects_a_second_concurrent_campaign() -> None:
    runner = FakeCampaignRunner()
    app = create_app(campaign_runner=runner)
    asyncio.run(app.state.campaign_lock.acquire())
    try:
        response = TestClient(app).post(
            "/api/demo/run",
            json={
                "approval_sha256": runner.manifest.sha256,
                "approved_by": "api-test",
            },
        )
    finally:
        app.state.campaign_lock.release()

    assert response.status_code == 409
    assert "already running" in response.json()["detail"]




def test_judge_run_fails_closed_when_injection_is_disabled() -> None:
    app = create_app(settings=Settings(_env_file=None))
    manifest = app.state.campaign_runner.plan()
    response = TestClient(app).post(
        "/api/demo/run",
        json={"approval_sha256": manifest.sha256},
    )

    assert response.status_code == 403
    assert "injection is disabled" in response.json()["detail"].lower()
