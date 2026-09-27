from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import AppContext, build_app_context
from app.customer_service import CustomerResolutionService
from app.interpretation import InterpretationProviderError, InterpretationService
from app.main import create_app
from app.settings import Settings


class FailingProvider:
    def extract(self, request, *, system_prompt, response_schema):
        del request, system_prompt, response_schema
        raise InterpretationProviderError("provider unavailable")


class InvalidOutputProvider:
    def extract(self, request, *, system_prompt, response_schema):
        del request, system_prompt, response_schema
        return "{not-json"


def _client(tmp_path, provider=None) -> tuple[TestClient, AppContext]:
    base = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    interpreter = InterpretationService(
        bank=base.bank,
        store=base.store,
        provider=provider or FailingProvider(),
        max_attempts=1,
    )
    service = CustomerResolutionService(
        bank=base.bank,
        store=base.store,
        interpreter=interpreter,
        synthetic_data=True,
    )
    context = AppContext(
        bank=base.bank,
        store=base.store,
        customer_service=service,
        personas=base.personas,
        data_mode=base.data_mode,
    )
    return TestClient(create_app(context)), context


def _session(client: TestClient, persona_id: str = "lucia") -> dict:
    response = client.post("/api/demo/sessions", json={"persona_id": persona_id})
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    ("persona_id", "message", "provider", "copy_phrase"),
    [
        (
            "lucia",
            "Muéstrame mis pagos recientes.",
            FailingProvider(),
            "No pude interpretar",
        ),
        (
            "rafael",
            "Mostre meus pagamentos recentes.",
            FailingProvider(),
            "Não consegui interpretar",
        ),
        (
            "lucia",
            "Muéstrame mis pagos recientes.",
            InvalidOutputProvider(),
            "No pude interpretar",
        ),
        (
            "rafael",
            "Mostre meus pagamentos recentes.",
            InvalidOutputProvider(),
            "Não consegui interpretar",
        ),
    ],
)
def test_safe_fallback_creates_nonmandatory_interpretation_handoff(
    tmp_path,
    persona_id: str,
    message: str,
    provider,
    copy_phrase: str,
) -> None:
    client, context = _client(tmp_path, provider=provider)
    session = _session(client, persona_id)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": message},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ESCALATE"
    assert body["reason_codes"] == ["interpretation_unavailable"]
    assert body["transactions"] == []
    assert body["clarification_transaction_ids"] == []
    assert body["escalation_ticket_id"] is not None
    assert body["handoff_available"] is False
    assert copy_phrase in body["response_text"]

    verified = context.store.resolve_verified_escalation_context(
        UUID(body["escalation_ticket_id"])
    )
    assert verified is not None
    assert verified.transaction_id is None
    assert verified.reason_code == "interpretation_unavailable"


@pytest.mark.parametrize(
    ("persona_id", "message"),
    [
        ("lucia", "No hice ese pago, alguien usó mi tarjeta."),
        ("rafael", "Eu não fiz esse pagamento, alguém usou meu cartão."),
    ],
)
def test_provider_failure_does_not_lower_explicit_unauthorized_assertion(
    tmp_path,
    persona_id: str,
    message: str,
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
    assert body["escalation_ticket_id"] is not None
    assert "interpretation_unavailable" not in body["reason_codes"]

    verified = context.store.resolve_verified_escalation_context(
        UUID(body["escalation_ticket_id"])
    )
    assert verified is not None
    assert verified.reason_code == "unauthorized_activity_reported"
    assert verified.transaction_id is None
