from fastapi.testclient import TestClient

from lineage_fuzzer.api import app


def test_health_endpoint_identifies_running_version() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
