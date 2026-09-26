from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_reports_deterministic_bootstrap() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "proof-of-one",
        "llm_connected": False,
    }
