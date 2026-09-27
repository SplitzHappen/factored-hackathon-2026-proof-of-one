from __future__ import annotations

from uuid import uuid4

import duckdb
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.demo_data import DEMO_TENANT_ID, build_synthetic_demo_bank
from app.main import create_app
from app.schemas import (
    AuthenticatedSession,
    SessionRole,
    SupportedLanguage,
)
from app.settings import Settings


def _client(tmp_path):
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(context)), context


def _session(client: TestClient, persona_id: str, language: str | None = None) -> dict:
    payload = {"persona_id": persona_id}
    if language is not None:
        payload["language"] = language
    response = client.post("/api/demo/sessions", json=payload)
    assert response.status_code == 201
    return response.json()


def test_demo_personas_are_public_synthetic_and_do_not_expose_customer_ids(tmp_path) -> None:
    client, _ = _client(tmp_path)

    response = client.get("/api/demo/personas")

    assert response.status_code == 200
    body = response.json()
    assert {item["persona_id"] for item in body} == {"lucia", "rafael"}
    assert all(item["synthetic_data"] is True for item in body)
    assert all("customer_id" not in item for item in body)


def test_session_identity_tenant_and_role_are_server_issued(tmp_path) -> None:
    client, context = _client(tmp_path)

    response = client.post(
        "/api/demo/sessions",
        json={"persona_id": "lucia", "language": "es"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["tenant_id"] == DEMO_TENANT_ID
    assert body["role"] == "customer"
    assert body["persona_id"] == "lucia"
    assert "customer_id" not in body

    persisted = context.store.get_authenticated_session(
        __import__("uuid").UUID(body["session_id"])
    )
    assert persisted is not None
    assert persisted.customer_id == "DEMO-CUST-ES-001"
    assert persisted.tenant_id == DEMO_TENANT_ID
    assert persisted.role is SessionRole.CUSTOMER


def test_verified_spanish_transaction_status_flows_end_to_end(tmp_path) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={
            "message": "¿Cuál es el estado de la transacción DEMO-ES-1001?"
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ANSWER"
    assert body["intent"] == "transaction_status"
    assert body["synthetic_data"] is True
    assert [tx["transaction_id"] for tx in body["transactions"]] == [
        "DEMO-ES-1001"
    ]
    assert body["transactions"][0]["status"] == "Approved"
    assert "aprobada" in body["response_text"]
    assert body["escalation_ticket_id"] is None
    assert "DEMO-PT-" not in response.text


def test_verified_portuguese_transaction_status_uses_pt_template(tmp_path) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, "rafael")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Qual é o status da transação DEMO-PT-2002?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ANSWER"
    assert body["transactions"][0]["transaction_id"] == "DEMO-PT-2002"
    assert body["transactions"][0]["status"] == "Pending"
    assert "A transação" in body["response_text"]
    assert "pendente" in body["response_text"]


def test_other_customer_transaction_is_not_disclosed_or_fraud_escalated(tmp_path) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame la transacción DEMO-PT-2001."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "CLARIFY"
    assert body["transactions"] == []
    assert body["escalation_ticket_id"] is None
    assert body["handoff_available"] is True
    assert "DEMO-PT-2001" not in body["response_text"]


def test_unauthorized_assertion_creates_verified_handoff(tmp_path) -> None:
    client, context = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={
            "message": (
                "No reconozco la transacción DEMO-ES-1001; yo no la hice."
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ESCALATE"
    assert body["transactions"] == []
    assert body["handoff_available"] is False
    assert body["escalation_ticket_id"] is not None

    record = context.store.get_escalation_record(
        __import__("uuid").UUID(body["escalation_ticket_id"])
    )
    assert record is not None
    assert record.persisted is True
    assert record.verified is True


def test_prohibited_money_movement_abstains_with_human_handoff(tmp_path) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Transfiere 100 a mi otra cuenta."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ABSTAIN"
    assert body["reason_codes"] == ["prohibited_banking_action"]
    assert body["handoff_available"] is True
    assert body["escalation_ticket_id"] is None


def test_recent_history_returns_only_authenticated_customer_transactions(tmp_path) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame mis últimos movimientos."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ANSWER"
    assert len(body["transactions"]) == 3
    assert all(tx["transaction_id"].startswith("DEMO-ES-") for tx in body["transactions"])


def test_unknown_and_malformed_sessions_are_rejected(tmp_path) -> None:
    client, _ = _client(tmp_path)

    malformed = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": "not-a-uuid"},
        json={"message": "hola"},
    )
    unknown = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": str(uuid4())},
        json={"message": "hola"},
    )

    assert malformed.status_code == 401
    assert unknown.status_code == 401


def test_customer_endpoint_rejects_server_persisted_analyst_role(tmp_path) -> None:
    client, context = _client(tmp_path)
    analyst = AuthenticatedSession(
        session_id=uuid4(),
        tenant_id=DEMO_TENANT_ID,
        role=SessionRole.ANALYST,
        demo_persona_id="lucia",
        customer_id="DEMO-CUST-ES-001",
        language=SupportedLanguage.ES,
    )
    context.store.save_authenticated_session(analyst)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": str(analyst.session_id)},
        json={"message": "Muéstrame mis últimos movimientos."},
    )

    assert response.status_code == 403


def test_customer_endpoint_rejects_wrong_tenant_even_with_valid_session(tmp_path) -> None:
    client, context = _client(tmp_path)
    foreign = AuthenticatedSession(
        session_id=uuid4(),
        tenant_id="other-demo-tenant",
        role=SessionRole.CUSTOMER,
        demo_persona_id="lucia",
        customer_id="DEMO-CUST-ES-001",
        language=SupportedLanguage.ES,
    )
    context.store.save_authenticated_session(foreign)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": str(foreign.session_id)},
        json={"message": "Muéstrame mis últimos movimientos."},
    )

    assert response.status_code == 403


def test_curated_mode_disables_public_demo_issuance(tmp_path) -> None:
    bank_path = tmp_path / "curated-compatible.duckdb"
    connection = duckdb.connect(str(bank_path))
    try:
        connection.execute(
            """
            CREATE TABLE build_metadata (
                schema_version INTEGER NOT NULL,
                builder_version VARCHAR NOT NULL
            )
            """
        )
        connection.execute("INSERT INTO build_metadata VALUES (1, 'r3b-1')")
    finally:
        connection.close()

    context = build_app_context(
        Settings(
            bank_db_path=bank_path,
            runtime_db_path=tmp_path / "curated-runtime.sqlite",
            data_mode="curated",
        )
    )
    client = TestClient(create_app(context))

    assert client.get("/api/demo/personas").status_code == 404
    assert client.post(
        "/api/demo/sessions",
        json={"persona_id": "lucia"},
    ).status_code == 404
