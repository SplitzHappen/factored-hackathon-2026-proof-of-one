from __future__ import annotations

from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.main import create_app
from app.settings import Settings


def _client(tmp_path) -> TestClient:
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(context))


def test_demo_shell_is_available_at_demo_and_root(tmp_path) -> None:
    client = _client(tmp_path)

    demo_response = client.get("/demo")
    root_response = client.get("/")

    assert demo_response.status_code == 200
    assert root_response.status_code == 200
    assert demo_response.headers["content-type"].startswith("text/html")
    assert root_response.headers["content-type"].startswith("text/html")
    assert "Proof of One" in demo_response.text
    assert "Judge Demo Shell" in demo_response.text
    assert "local synthetic demo" in demo_response.text
    assert "live-provider readiness" in demo_response.text


def test_demo_shell_references_only_existing_public_demo_api_paths(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "/ready" in html
    assert "/api/demo/personas" in html
    assert "/api/demo/sessions" in html
    assert "/api/customer/turn" in html
    assert "/api/customer/handoff" in html
    assert "/api/demo/session" in html
    assert "customer_id" not in html


def test_demo_shell_routes_are_hidden_from_openapi_schema(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/demo" not in paths
    assert "/" not in paths
    assert "/api/customer/turn" in paths


def test_demo_shell_preserves_existing_api_flow(tmp_path) -> None:
    client = _client(tmp_path)

    session_response = client.post(
        "/api/demo/sessions",
        json={"persona_id": "lucia"},
    )
    assert session_response.status_code == 201
    session = session_response.json()

    turn_response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame mis últimos movimientos."},
    )

    assert turn_response.status_code == 200
    body = turn_response.json()
    assert body["synthetic_data"] is True
    assert body["session_id"] == session["session_id"]
    assert body["route"] in {"ANSWER", "CLARIFY", "ABSTAIN", "ESCALATE"}
