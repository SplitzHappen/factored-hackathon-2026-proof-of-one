from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.main import create_app
from app.settings import Settings


def _client(tmp_path):
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(context))


def _session(client: TestClient, persona_id: str) -> dict:
    response = client.post("/api/demo/sessions", json={"persona_id": persona_id})
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    ("persona_id", "message", "expected_balance", "currency"),
    [
        ("lucia", "¿Cuál es el saldo de mi cuenta?", "3250000.00", "COP"),
        ("rafael", "Qual é o saldo da minha conta?", "8450.00", "BRL"),
    ],
)
def test_account_product_info_answers_only_with_verified_product_facts(
    tmp_path,
    persona_id: str,
    message: str,
    expected_balance: str,
    currency: str,
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
    assert body["route"] == "ANSWER"
    assert body["intent"] == "account_product_info"
    assert body["transactions"] == []
    assert len(body["products"]) == 1
    product = body["products"][0]
    assert Decimal(str(product["current_balance"])) == Decimal(expected_balance)
    assert product["currency"] == currency
    assert product["product_status"] == "Active"
    assert expected_balance in body["response_text"]
    assert currency in body["response_text"]


@pytest.mark.parametrize(
    ("persona_id", "message", "expected_ids", "excluded_id"),
    [
        (
            "lucia",
            "Muéstrame mi historial de pagos recientes.",
            ["DEMO-ES-1001", "DEMO-ES-1003", "DEMO-ES-1004"],
            "DEMO-ES-1002",
        ),
        (
            "rafael",
            "Mostre meu histórico de pagamentos recentes.",
            ["DEMO-PT-2001", "DEMO-PT-2003", "DEMO-PT-2004"],
            "DEMO-PT-2002",
        ),
    ],
)
def test_payment_history_is_payment_filtered_over_owned_records(
    tmp_path,
    persona_id: str,
    message: str,
    expected_ids: list[str],
    excluded_id: str,
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
    assert body["route"] == "ANSWER"
    assert body["intent"] == "payment_history"
    assert body["products"] == []
    assert [item["transaction_id"] for item in body["transactions"]] == expected_ids
    assert excluded_id not in response.text
    assert all(
        item["transaction_type"].casefold() == "payment"
        for item in body["transactions"]
    )


@pytest.mark.parametrize(
    ("persona_id", "message", "forbidden_phrase"),
    [
        (
            "lucia",
            "¿Por qué falló la transacción DEMO-ES-1001?",
            "ese rechazo",
        ),
        (
            "lucia",
            "¿Por qué falló la transacción DEMO-ES-9999?",
            "ese rechazo",
        ),
        (
            "rafael",
            "Por que falhou a transação DEMO-PT-2001?",
            "essa recusa",
        ),
        (
            "rafael",
            "Por que falhou a transação DEMO-PT-9999?",
            "essa recusa",
        ),
    ],
)
def test_payment_history_explicit_transfer_reference_does_not_masquerade_as_payment(
    tmp_path,
) -> None:
    client = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame el historial de pagos de DEMO-ES-1002."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ANSWER"
    assert body["intent"] == "payment_history"
    assert body["transactions"] == []
    assert "DEMO-ES-1002" not in body["response_text"]
    assert "No encontré pagos recientes verificables" in body["response_text"]


def test_decline_cause_abstention_does_not_presuppose_rejection(
    tmp_path,
    persona_id: str,
    message: str,
    forbidden_phrase: str,
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
    assert body["route"] == "ABSTAIN"
    assert body["intent"] == "decline_cause"
    assert body["reason_codes"] == ["unsupported_causal_explanation"]
    assert body["products"] == []
    assert body["transactions"] == []
    assert forbidden_phrase not in body["response_text"].casefold()
    assert "resultado" in body["response_text"].casefold()
