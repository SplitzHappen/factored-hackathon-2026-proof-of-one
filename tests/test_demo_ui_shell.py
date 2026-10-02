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


def _compact(text: str) -> str:
    return "".join(text.split())


def test_signal_box_shell_is_available_at_demo_and_root(tmp_path) -> None:
    client = _client(tmp_path)

    demo_response = client.get("/demo")
    root_response = client.get("/")

    assert demo_response.status_code == 200
    assert root_response.status_code == 200
    assert demo_response.headers["content-type"].startswith("text/html")
    assert root_response.headers["content-type"].startswith("text/html")

    html = demo_response.text
    assert "Proof of One — Signal Box Demo" in html
    assert "Proof of One" in html
    assert "Interlocking · 8 fixed checks" in html
    assert "Scenario presets" in html
    assert "Local prototype · synthetic" in html
    assert "No live LLM · Not fraud detection" in html
    assert (
        "Synthetic data · local API · no live LLM · not fraud detection · "
        "not production/pilot-ready"
    ) in html


def test_signal_box_shell_references_only_final_public_demo_api_paths(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text

    for path in (
        "/api/demo/personas",
        "/api/demo/sessions",
        "/api/customer/turn",
        "/api/customer/handoff",
        "/api/demo/session",
    ):
        assert path in html

    assert "/ready" not in html
    assert "_render_demo_shell_html" not in html


def test_signal_box_shell_contains_final_claim_safe_route_copy(tmp_path) -> None:
    client = _client(tmp_path)

    html = client.get("/demo").text

    assert "Customer-reported unauthorized activity?" in html
    assert "Message may report unauthorized activity?" in html
    assert "Record-backed answer" in html
    assert "Needs exact reference" in html
    assert "Unsupported / unsafe" in html
    assert "Human review" in html
    assert "Support ticket" in html
    assert "Not fraud detection" in html
    assert "fraud determination" not in html.casefold()
    assert "production ready" not in html.casefold()
    assert "pilot ready" not in html.casefold()


def test_signal_box_shell_contains_audited_state_and_handoff_ui_logic(tmp_path) -> None:
    client = _client(tmp_path)

    html = client.get("/demo").text
    compact_html = _compact(html)

    for state in ("WAITING", "CLEAR", "ON", "N/A"):
        assert state in html

    assert "▶ Route set" in html
    assert "UNSUPPORTED INTENT" in html
    assert "customer_requested_support_handoff" in html
    assert "persisted ${escapeHtml(response.persisted)}" in html
    assert "read-back verified ${escapeHtml(response.verified)}" in html
    assert "synthetic ${escapeHtml(response.synthetic_data)}" in html
    assert "els.message.value='';" in compact_html


def test_signal_box_shell_contains_exact_final_judge_presets(tmp_path) -> None:
    client = _client(tmp_path)

    html = client.get("/demo").text

    expected_presets = (
        (
            "lucia",
            "¿Cuál es el estado de la transacción DEMO-ES-1001?",
            "ANSWER · Known transaction",
        ),
        (
            "lucia",
            "Quiero consultar una transacción por 54000 COP.",
            "CLARIFY · Two matches",
        ),
        (
            "lucia",
            "No reconozco la transacción DEMO-ES-1001. Yo no autoricé ese pago.",
            "ESCALATE · Unauthorized report",
        ),
        (
            "lucia",
            "Quiero hacer una transferencia de 10000 COP a otra cuenta.",
            "ABSTAIN · Out-of-scope request",
        ),
        (
            "rafael",
            "Qual é o estado da transação DEMO-PT-2001?",
            "PT · Rafael path",
        ),
    )

    for persona_id, message, label in expected_presets:
        assert f'data-persona="{persona_id}"' in html
        assert f'data-message="{message}"' in html
        assert label in html


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
        (
            "lucia",
            "¿Cuál es el estado de la transacción DEMO-ES-1001?",
            "ANSWER",
        ),
        (
            "lucia",
            "Quiero consultar una transacción por 54000 COP.",
            "CLARIFY",
        ),
        (
            "lucia",
            "No reconozco la transacción DEMO-ES-1001. Yo no autoricé ese pago.",
            "ESCALATE",
        ),
        (
            "lucia",
            "Quiero hacer una transferencia de 10000 COP a otra cuenta.",
            "ABSTAIN",
        ),
        (
            "rafael",
            "Qual é o estado da transação DEMO-PT-2001?",
            "ANSWER",
        ),
    ],
)
def test_final_judge_preset_messages_match_expected_routes(
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
        assert body["transactions"][0]["transaction_id"] == "DEMO-PT-2001"


def test_final_clarify_preset_returns_expected_candidates(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Quiero consultar una transacción por 54000 COP."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "CLARIFY"
    assert body["reason_codes"] == ["ambiguous_transaction_match"]
    assert body["clarification_transaction_ids"] == [
        "DEMO-ES-1003",
        "DEMO-ES-1004",
    ]


def test_final_escalate_preset_creates_human_review_ticket_without_fraud_claim(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={
            "message": (
                "No reconozco la transacción DEMO-ES-1001. "
                "Yo no autoricé ese pago."
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ESCALATE"
    assert body["reason_codes"] == ["unauthorized_activity_reported"]
    assert body["escalation_ticket_id"]
    assert body["handoff_available"] is False
    assert "fraud" not in body["response_text"].casefold()


def test_final_abstain_preset_stays_outside_supported_workflow(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Quiero hacer una transferencia de 10000 COP a otra cuenta."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ABSTAIN"
    assert body["reason_codes"] == ["prohibited_banking_action"]
    assert body["escalation_ticket_id"] is None
    assert body["handoff_available"] is True


def test_demo_shell_clarify_follow_up_resolves_to_answer(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Quiero la transacción DEMO-ES-1003."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ANSWER"
    assert body["transactions"]
    assert body["transactions"][0]["transaction_id"] == "DEMO-ES-1003"


def test_demo_shell_missing_id_clarify_is_not_ambiguity(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Quiero la transacción DEMO-ES-9999."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "CLARIFY"
    assert "ambiguous_transaction_match" not in body["reason_codes"]
    assert body["clarification_transaction_ids"] == []


def test_demo_shell_handoff_api_returns_persisted_readback_verified_ticket(tmp_path) -> None:
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
