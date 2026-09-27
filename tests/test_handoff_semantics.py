from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.customer_service import CustomerResolutionService
from app.main import create_app
from app.schemas import PolicyReason, SupportedLanguage
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
    response = client.post("/api/demo/sessions", json={"persona_id": persona_id})
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    ("persona_id", "message", "copy_phrase"),
    [
        (
            "lucia",
            "Transfiere 100 a mi otra cuenta.",
            "solicitar una revisión humana en este demo",
        ),
        (
            "rafael",
            "Transfira 100 para minha outra conta.",
            "solicitar uma revisão humana neste demo",
        ),
    ],
)
def test_abstain_exposes_actionable_opt_in_support_ticket(
    tmp_path,
    persona_id: str,
    message: str,
    copy_phrase: str,
) -> None:
    client, context = _client(tmp_path)
    session = _session(client, persona_id)

    turn = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": message},
    )

    assert turn.status_code == 200
    turn_body = turn.json()
    assert turn_body["route"] == "ABSTAIN"
    assert turn_body["handoff_available"] is True
    assert turn_body["escalation_ticket_id"] is None
    assert copy_phrase in turn_body["response_text"]

    handoff = client.post(
        "/api/customer/handoff",
        headers={"X-Demo-Session": session["session_id"]},
    )

    assert handoff.status_code == 201
    ticket = handoff.json()
    assert ticket["persisted"] is True
    assert ticket["verified"] is True
    assert ticket["session_id"] == session["session_id"]

    verified = context.store.resolve_verified_escalation_context(
        UUID(ticket["ticket_id"])
    )
    assert verified is not None
    assert verified.transaction_id is None
    assert verified.reason_code == "customer_requested_support"
    assert str(verified.session.session_id) == session["session_id"]


def test_missing_record_support_offer_is_actionable_without_disclosing_foreign_id(
    tmp_path,
) -> None:
    client, context = _client(tmp_path)
    session = _session(client, "lucia")

    turn = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame la transacción DEMO-PT-2001."},
    )

    assert turn.status_code == 200
    body = turn.json()
    assert body["route"] == "CLARIFY"
    assert body["handoff_available"] is True
    assert body["escalation_ticket_id"] is None
    assert "DEMO-PT-2001" not in body["response_text"]
    assert "solicita una revisión humana en este demo" in body["response_text"]

    handoff = client.post(
        "/api/customer/handoff",
        headers={"X-Demo-Session": session["session_id"]},
    )
    assert handoff.status_code == 201

    verified = context.store.resolve_verified_escalation_context(
        UUID(handoff.json()["ticket_id"])
    )
    assert verified is not None
    assert verified.transaction_id is None
    assert verified.reason_code == "customer_requested_support"


@pytest.mark.parametrize(
    ("persona_id", "message", "owned_id", "copy_phrase"),
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
def test_automatic_escalation_reports_persisted_ticket_not_available_handoff(
    tmp_path,
    persona_id: str,
    message: str,
    owned_id: str,
    copy_phrase: str,
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
    assert body["handoff_available"] is False
    assert body["escalation_ticket_id"] is not None
    assert copy_phrase in body["response_text"]

    verified = context.store.resolve_verified_escalation_context(
        UUID(body["escalation_ticket_id"])
    )
    assert verified is not None
    assert verified.transaction_id == owned_id
    assert verified.reason_code == "unauthorized_activity_reported"


def test_informational_unauthorized_wording_uses_soft_case_copy(tmp_path) -> None:
    client, _ = _client(tmp_path)
    session = _session(client, "lucia")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "¿Cómo reporto una compra que no reconozco?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ESCALATE"
    assert body["escalation_ticket_id"] is not None
    assert "Registré este caso para revisión humana en el demo." == body["response_text"]
    assert "indicaste" not in body["response_text"]


def test_escalation_summaries_are_reason_keyed() -> None:
    unauthorized = CustomerResolutionService._escalation_summary(
        SupportedLanguage.ES,
        PolicyReason.UNAUTHORIZED_ACTIVITY_REPORTED,
    )
    conflict = CustomerResolutionService._escalation_summary(
        SupportedLanguage.ES,
        PolicyReason.TRUSTED_DATA_CONFLICT,
    )
    excluded = CustomerResolutionService._escalation_summary(
        SupportedLanguage.ES,
        PolicyReason.EXCLUDED_RELATIONSHIP_REQUIRED,
    )

    assert len({unauthorized, conflict, excluded}) == 3
    assert "actividad no reconocida" in unauthorized
    assert "datos verificados" in conflict
    assert "fuera del alcance" in excluded
