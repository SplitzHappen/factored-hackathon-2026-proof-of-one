from __future__ import annotations

import pytest
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


def _session(client: TestClient, persona_id: str, language: str | None = None) -> dict:
    payload = {"persona_id": persona_id}
    if language is not None:
        payload["language"] = language
    response = client.post("/api/demo/sessions", json=payload)
    assert response.status_code == 201
    return response.json()


def test_demo_shell_is_available_at_demo_and_root(tmp_path) -> None:
    client = _client(tmp_path)

    demo_response = client.get("/demo")
    root_response = client.get("/")

    assert demo_response.status_code == 200
    assert root_response.status_code == 200
    assert demo_response.headers["content-type"].startswith("text/html")
    assert root_response.headers["content-type"].startswith("text/html")
    assert "Proof of One" in demo_response.text
    assert "Local Synthetic Demo" in demo_response.text
    assert "local synthetic demo" in demo_response.text
    assert "verified synthetic account records" in demo_response.text
    assert "no language model connected" in demo_response.text


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
    assert 'data-persona="rafael"' in html
    assert "Busca las transacciones de 54.000 COP." in html
    assert "No live agent is connected in this demo" in html
    assert "justify-content:flex-start" in html
    assert "gap:16px" in html
    assert "state.session&&els.persona.value!==state.session.persona_id" in html
    assert "The selected persona differs from the active session" in html
    assert "state.session?.synthetic_data===true" in html
    assert "reason_codes: ['customer_requested_support_handoff']" not in html
    assert "_render_demo_shell_html" not in html


def test_demo_shell_routes_are_hidden_from_openapi_schema(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/demo" not in paths
    assert "/" not in paths
    assert "/api/customer/turn" in paths


@pytest.mark.parametrize(
    ("persona_id", "message", "expected_route"),
    [
        ("lucia", "Muéstrame mis últimos movimientos.", "ANSWER"),
        ("lucia", "Busca las transacciones de 54.000 COP.", "CLARIFY"),
        (
            "lucia",
            "No reconozco este pago y no autoricé esta actividad en mi cuenta.",
            "ESCALATE",
        ),
        ("rafael", "Quero ver meus pagamentos recentes.", "ANSWER"),
    ],
)
def test_demo_shell_preset_messages_match_expected_routes(
    tmp_path,
    persona_id: str,
    message: str,
    expected_route: str,
) -> None:
    client = _client(tmp_path)
    session = _session(client, persona_id)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": message},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["synthetic_data"] is True
    assert body["session_id"] == session["session_id"]
    assert body["route"] == expected_route
    if persona_id == "rafael":
        assert body["transactions"]
        assert body["transactions"][0]["transaction_id"].startswith("DEMO-PT-")


def test_demo_shell_clarify_preset_returns_expected_candidates(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Busca las transacciones de 54.000 COP."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "CLARIFY"
    assert body["clarification_transaction_ids"] == [
        "DEMO-ES-1003",
        "DEMO-ES-1004",
    ]


def test_demo_shell_handoff_api_returns_persisted_verified_ticket(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/handoff",
        headers={"X-Demo-Session": session["session_id"]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["session_id"] == session["session_id"]
    assert body["persisted"] is True
    assert body["verified"] is True
    assert body["ticket_id"]
