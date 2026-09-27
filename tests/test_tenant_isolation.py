from __future__ import annotations

import sqlite3
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.bootstrap import build_app_context
from app.main import create_app
from app.runtime import RUNTIME_SCHEMA_VERSION, SessionIdentityMismatchError
from app.schemas import AuthenticatedSession, SessionRole, SupportedLanguage
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


def test_runtime_schema_bumped_for_explicit_ticket_tenant_binding() -> None:
    assert RUNTIME_SCHEMA_VERSION == 3


def test_authenticated_session_requires_explicit_tenant_and_role() -> None:
    with pytest.raises(ValidationError):
        AuthenticatedSession(
            session_id=uuid4(),
            demo_persona_id="lucia",
            customer_id="DEMO-CUST-ES-001",
            language=SupportedLanguage.ES,
        )


@pytest.mark.parametrize(
    ("new_tenant", "new_role"),
    [
        ("demo-rebound-tenant", SessionRole.CUSTOMER),
        ("demo-original-tenant", SessionRole.ANALYST),
    ],
)
def test_persisted_session_tenant_or_role_cannot_be_rebound(
    tmp_path,
    new_tenant: str,
    new_role: SessionRole,
) -> None:
    _, context = _client(tmp_path)
    session_id = uuid4()
    original = AuthenticatedSession(
        session_id=session_id,
        tenant_id="demo-original-tenant",
        role=SessionRole.CUSTOMER,
        demo_persona_id="lucia",
        customer_id="DEMO-CUST-ES-001",
        language=SupportedLanguage.ES,
    )
    context.store.save_authenticated_session(original)

    rebound = AuthenticatedSession(
        session_id=session_id,
        tenant_id=new_tenant,
        role=new_role,
        demo_persona_id=original.demo_persona_id,
        customer_id=original.customer_id,
        language=original.language,
    )

    with pytest.raises(SessionIdentityMismatchError):
        context.store.save_authenticated_session(rebound)

    assert context.store.get_authenticated_session(session_id) == original


def test_verified_ticket_listing_is_scoped_to_each_visitor_tenant(tmp_path) -> None:
    client, context = _client(tmp_path)
    first = _session(client, "lucia")
    second = _session(client, "rafael")

    first_ticket = client.post(
        "/api/customer/handoff",
        headers={"X-Demo-Session": first["session_id"]},
    )
    second_ticket = client.post(
        "/api/customer/handoff",
        headers={"X-Demo-Session": second["session_id"]},
    )

    assert first_ticket.status_code == 201
    assert second_ticket.status_code == 201
    first_ticket_id = UUID(first_ticket.json()["ticket_id"])
    second_ticket_id = UUID(second_ticket.json()["ticket_id"])

    assert context.store.list_verified_escalation_ticket_ids_for_tenant(
        first["tenant_id"]
    ) == [first_ticket_id]
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(
        second["tenant_id"]
    ) == [second_ticket_id]

    with sqlite3.connect(context.store.path) as connection:
        rows = connection.execute(
            """
            SELECT ticket_id, tenant_id
            FROM escalation_tickets
            ORDER BY ticket_id
            """
        ).fetchall()
    by_ticket = {ticket_id: tenant_id for ticket_id, tenant_id in rows}
    assert by_ticket[str(first_ticket_id)] == first["tenant_id"]
    assert by_ticket[str(second_ticket_id)] == second["tenant_id"]


def test_ticket_tenant_tampering_fails_closed_in_listing_and_resolution(tmp_path) -> None:
    client, context = _client(tmp_path)
    first = _session(client, "lucia")
    second = _session(client, "rafael")

    ticket = client.post(
        "/api/customer/handoff",
        headers={"X-Demo-Session": first["session_id"]},
    )
    assert ticket.status_code == 201
    ticket_id = UUID(ticket.json()["ticket_id"])

    with sqlite3.connect(context.store.path) as connection:
        connection.execute(
            "UPDATE escalation_tickets SET tenant_id = ? WHERE ticket_id = ?",
            (second["tenant_id"], str(ticket_id)),
        )
        connection.commit()

    assert context.store.resolve_verified_escalation_context(ticket_id) is None
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(
        first["tenant_id"]
    ) == []
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(
        second["tenant_id"]
    ) == []
