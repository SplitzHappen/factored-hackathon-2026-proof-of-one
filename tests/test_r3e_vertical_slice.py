from __future__ import annotations

from uuid import UUID

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
    return TestClient(create_app(context)), context


def _session(client: TestClient, persona_id: str) -> dict:
    response = client.post(
        "/api/demo/sessions",
        json={"persona_id": persona_id},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    ("persona_id", "message", "expected_id", "localized_status"),
    [
        (
            "lucia",
            "¿Cuál es el estado de la transacción DEMO-ES-1001?",
            "DEMO-ES-1001",
            "aprobada",
        ),
        (
            "rafael",
            "Qual é o status da transação DEMO-PT-2002?",
            "DEMO-PT-2002",
            "pendente",
        ),
    ],
)
def test_r3e_normal_verified_answer_is_bilingual(
    tmp_path,
    persona_id: str,
    message: str,
    expected_id: str,
    localized_status: str,
) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, persona_id)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": message},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ANSWER"
    assert [tx["transaction_id"] for tx in body["transactions"]] == [expected_id]
    assert body["clarification_transaction_ids"] == []
    assert body["handoff_available"] is False
    assert localized_status in body["response_text"]


@pytest.mark.parametrize(
    (
        "persona_id",
        "first_message",
        "expected_candidates",
        "followup_message",
        "selected_id",
    ),
    [
        (
            "lucia",
            "Busca las transacciones de 54000.",
            ["DEMO-ES-1003", "DEMO-ES-1004"],
            "Quiero la transacción DEMO-ES-1004.",
            "DEMO-ES-1004",
        ),
        (
            "rafael",
            "Mostre as transações de 142,75.",
            ["DEMO-PT-2003", "DEMO-PT-2004"],
            "Quero a transação DEMO-PT-2003.",
            "DEMO-PT-2003",
        ),
    ],
)
def test_r3e_followup_explicit_id_is_fresh_reverified_lookup(
    tmp_path,
    persona_id: str,
    first_message: str,
    expected_candidates: list[str],
    followup_message: str,
    selected_id: str,
) -> None:
    client, context = _client(tmp_path)
    session = _session(client, persona_id)
    session_id = UUID(session["session_id"])

    first = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": first_message},
    )

    assert first.status_code == 200
    first_body = first.json()
    assert first_body["route"] == "CLARIFY"
    assert first_body["transactions"] == []
    assert first_body["clarification_transaction_ids"] == expected_candidates
    assert all(candidate in first_body["response_text"] for candidate in expected_candidates)
    assert first_body["escalation_ticket_id"] is None

    persisted_session = context.store.get_authenticated_session(session_id)
    assert persisted_session is not None
    first_state = context.store.get_conversation_state(persisted_session)
    assert first_state is not None
    assert first_state.clarification_required is True
    assert first_state.candidate_transaction_ids == expected_candidates

    second = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": followup_message},
    )

    assert second.status_code == 200
    second_body = second.json()
    assert second_body["route"] == "ANSWER"
    assert [tx["transaction_id"] for tx in second_body["transactions"]] == [selected_id]
    assert second_body["clarification_transaction_ids"] == []
    assert second_body["escalation_ticket_id"] is None

    second_state = context.store.get_conversation_state(persisted_session)
    assert second_state is not None
    assert second_state.clarification_required is False
    assert second_state.candidate_transaction_ids == [selected_id]


def test_followup_explicit_owned_id_need_not_be_in_prior_candidate_set(
    tmp_path,
) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, "lucia")

    first = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Busca las transacciones de 54000."},
    )
    assert first.status_code == 200
    assert first.json()["clarification_transaction_ids"] == [
        "DEMO-ES-1003",
        "DEMO-ES-1004",
    ]

    second = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Quiero la transacción DEMO-ES-1001."},
    )

    assert second.status_code == 200
    body = second.json()
    assert body["route"] == "ANSWER"
    assert [tx["transaction_id"] for tx in body["transactions"]] == [
        "DEMO-ES-1001"
    ]


def test_ordinal_followup_is_not_claimed_as_candidate_bound_selection(tmp_path) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, "lucia")

    first = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Busca las transacciones de 54000."},
    )
    assert first.status_code == 200
    assert first.json()["route"] == "CLARIFY"

    second = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "La segunda."},
    )

    assert second.status_code == 200
    body = second.json()
    assert body["route"] == "ABSTAIN"
    assert body["intent"] == "unknown"
    assert body["transactions"] == []


@pytest.mark.parametrize(
    ("persona_id", "message", "expected_phrase"),
    [
        (
            "lucia",
            "Transfiere 100 a mi otra cuenta.",
            "No puedo ejecutar",
        ),
        (
            "rafael",
            "Transfira 100 para minha outra conta.",
            "Não posso executar",
        ),
    ],
)
def test_r3e_safe_handoff_for_prohibited_action_is_bilingual(
    tmp_path,
    persona_id: str,
    message: str,
    expected_phrase: str,
) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, persona_id)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": message},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ABSTAIN"
    assert body["reason_codes"] == ["prohibited_banking_action"]
    assert body["transactions"] == []
    assert body["clarification_transaction_ids"] == []
    assert body["handoff_available"] is True
    assert body["escalation_ticket_id"] is None
    assert expected_phrase in body["response_text"]


@pytest.mark.parametrize(
    ("persona_id", "message", "owned_id", "expected_phrase"),
    [
        (
            "lucia",
            "No reconozco la transacción DEMO-ES-1001; yo no la hice.",
            "DEMO-ES-1001",
            "revisión humana en el demo",
        ),
        (
            "rafael",
            "Não reconheço a transação DEMO-PT-2001; eu não fiz isso.",
            "DEMO-PT-2001",
            "revisão humana no demo",
        ),
    ],
)
def test_r3e_verified_unauthorized_escalation_is_bilingual(
    tmp_path,
    persona_id: str,
    message: str,
    owned_id: str,
    expected_phrase: str,
) -> None:
    client, context = _client(tmp_path)
    session = _session(client, persona_id)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": message},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ESCALATE"
    assert body["reason_codes"] == ["unauthorized_activity_reported"]
    assert body["transactions"] == []
    assert body["clarification_transaction_ids"] == []
    assert body["handoff_available"] is False
    assert body["escalation_ticket_id"] is not None
    assert expected_phrase in body["response_text"]

    verified = context.store.resolve_verified_escalation_context(
        UUID(body["escalation_ticket_id"])
    )
    assert verified is not None
    assert verified.transaction_id == owned_id
    assert str(verified.session.session_id) == session["session_id"]


@pytest.mark.parametrize(
    ("persona_id", "message", "foreign_id"),
    [
        (
            "lucia",
            "Muéstrame la transacción DEMO-PT-2001.",
            "DEMO-PT-2001",
        ),
        (
            "rafael",
            "Mostre a transação DEMO-ES-1001.",
            "DEMO-ES-1001",
        ),
    ],
)
def test_r3e_unowned_reference_never_exposes_clarification_candidates(
    tmp_path,
    persona_id: str,
    message: str,
    foreign_id: str,
) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, persona_id)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": message},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "CLARIFY"
    assert body["transactions"] == []
    assert body["clarification_transaction_ids"] == []
    assert body["escalation_ticket_id"] is None
    assert foreign_id not in body["response_text"]


@pytest.mark.parametrize(
    ("persona_id", "message", "expected_phrase"),
    [
        (
            "lucia",
            "¿Cuál es el estado de esa transacción?",
            "Necesito más detalles",
        ),
        (
            "rafael",
            "Qual é o status dessa transação?",
            "Preciso de mais detalhes",
        ),
    ],
)
def test_r3e_missing_reference_clarifies_without_empty_candidate_prompt(
    tmp_path,
    persona_id: str,
    message: str,
    expected_phrase: str,
) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, persona_id)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": message},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "CLARIFY"
    assert body["reason_codes"] == ["required_parameters_missing"]
    assert body["transactions"] == []
    assert body["clarification_transaction_ids"] == []
    assert body["escalation_ticket_id"] is None
    assert expected_phrase in body["response_text"]
