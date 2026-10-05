from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.main import create_app
from app.runtime import OperationalStore, RateLimitExceededError, TicketLimitExceededError
from app.schemas import EscalationRequest
from app.settings import Settings


def _context(tmp_path):
    return build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )


def _client(tmp_path, *, raise_server_exceptions: bool = True):
    context = _context(tmp_path)
    client = TestClient(
        create_app(context),
        raise_server_exceptions=raise_server_exceptions,
    )
    return client, context


def _session(client: TestClient, persona_id: str = "lucia") -> dict:
    response = client.post("/api/demo/sessions", json={"persona_id": persona_id})
    assert response.status_code == 201
    return response.json()


def _clock(monkeypatch, store, now: datetime) -> list[datetime]:
    current = [now]
    monkeypatch.setattr(store, "_utc_now", lambda: current[0])
    return current


def test_session_expires_after_four_hours_but_ticket_context_is_retained(
    tmp_path,
    monkeypatch,
) -> None:
    client, context = _client(tmp_path)
    current = _clock(
        monkeypatch,
        context.store,
        datetime(2026, 9, 27, 0, 0, tzinfo=timezone.utc),
    )
    session = _session(client)

    handoff = client.post(
        "/api/customer/handoff",
        headers={"X-Demo-Session": session["session_id"]},
    )
    assert handoff.status_code == 201
    ticket_id = UUID(handoff.json()["ticket_id"])

    current[0] += timedelta(hours=4, seconds=1)

    turn = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame mis últimos movimientos."},
    )
    assert turn.status_code == 401
    assert context.store.resolve_verified_escalation_context(ticket_id) is not None


def test_customer_can_revoke_own_demo_session(tmp_path) -> None:
    client, _ = _client(tmp_path)
    session = _session(client)

    revoked = client.delete(
        "/api/demo/session",
        headers={"X-Demo-Session": session["session_id"]},
    )
    assert revoked.status_code == 204

    turn = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame mis últimos movimientos."},
    )
    assert turn.status_code == 401


def test_unknown_persona_does_not_consume_session_creation_quota(tmp_path) -> None:
    client, context = _client(tmp_path)
    context.store.session_creation_limit = 1

    unknown = client.post(
        "/api/demo/sessions",
        json={"persona_id": "does-not-exist"},
    )
    assert unknown.status_code == 404

    created = client.post(
        "/api/demo/sessions",
        json={"persona_id": "lucia"},
    )
    assert created.status_code == 201

    limited = client.post(
        "/api/demo/sessions",
        json={"persona_id": "rafael"},
    )
    assert limited.status_code == 429


def test_challenge_session_creation_quota_is_separate_and_higher(tmp_path) -> None:
    store = OperationalStore(
        tmp_path / "runtime.sqlite",
        session_creation_limit=1,
        challenge_session_creation_limit=3,
    )
    store.initialize()

    store.enforce_session_creation_rate("peer-a")
    with pytest.raises(RateLimitExceededError):
        store.enforce_session_creation_rate("peer-a")

    for _ in range(3):
        store.enforce_challenge_session_creation_rate("peer-a")
    with pytest.raises(RateLimitExceededError):
        store.enforce_challenge_session_creation_rate("peer-a")


def test_rate_limit_state_survives_store_reopen(tmp_path) -> None:
    _, context = _client(tmp_path)
    context.store.session_creation_limit = 1
    context.store.enforce_session_creation_rate("peer-a")

    reopened = OperationalStore(
        context.store.path,
        session_creation_limit=1,
    )
    reopened.initialize(data_mode="synthetic")

    with pytest.raises(RateLimitExceededError):
        reopened.enforce_session_creation_rate("peer-a")


def test_session_creation_rate_limit_returns_429(tmp_path) -> None:
    client, context = _client(tmp_path)
    context.store.session_creation_limit = 2

    assert client.post("/api/demo/sessions", json={"persona_id": "lucia"}).status_code == 201
    assert client.post("/api/demo/sessions", json={"persona_id": "rafael"}).status_code == 201
    limited = client.post("/api/demo/sessions", json={"persona_id": "lucia"})

    assert limited.status_code == 429
    assert limited.json()["detail"] == "Demo session creation limit reached"


def test_per_session_request_rate_limit_returns_429(tmp_path) -> None:
    client, context = _client(tmp_path)
    context.store.session_request_limit = 2
    session = _session(client)

    for _ in range(2):
        response = client.post(
            "/api/customer/turn",
            headers={"X-Demo-Session": session["session_id"]},
            json={"message": "Muéstrame mis últimos movimientos."},
        )
        assert response.status_code == 200

    limited = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame mis últimos movimientos."},
    )
    assert limited.status_code == 429
    assert limited.json()["detail"] == "Demo session request limit reached"


def test_identical_automatic_escalation_reuses_verified_ticket(tmp_path) -> None:
    client, context = _client(tmp_path)
    session = _session(client)
    request = {
        "message": "No reconozco la transacción DEMO-ES-1001; yo no la hice."
    }

    first = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json=request,
    )
    second = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json=request,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["escalation_ticket_id"] == second.json()["escalation_ticket_id"]

    with sqlite3.connect(context.store.path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM escalation_tickets WHERE session_id = ?",
            (session["session_id"],),
        ).fetchone()[0]
    assert count == 1


def test_retry_after_state_failure_does_not_duplicate_verified_ticket(
    tmp_path,
    monkeypatch,
) -> None:
    client, context = _client(tmp_path, raise_server_exceptions=False)
    session = _session(client)
    original_save = context.store.save_conversation_state

    def fail_state_save(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("simulated state failure")

    monkeypatch.setattr(context.store, "save_conversation_state", fail_state_save)
    request = {
        "message": "No reconozco la transacción DEMO-ES-1001; yo no la hice."
    }
    failed = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json=request,
    )
    assert failed.status_code == 500

    monkeypatch.setattr(context.store, "save_conversation_state", original_save)
    retried = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json=request,
    )

    assert retried.status_code == 200
    assert retried.json()["escalation_ticket_id"] is not None
    with sqlite3.connect(context.store.path) as connection:
        rows = connection.execute(
            """
            SELECT ticket_id, verified_at
            FROM escalation_tickets
            WHERE session_id = ?
            """,
            (session["session_id"],),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][1] is not None
    assert retried.json()["escalation_ticket_id"] == rows[0][0]


def test_distinct_ticket_cap_fails_closed_and_maps_to_429(tmp_path) -> None:
    client, context = _client(tmp_path)
    context.store.ticket_limit_per_session = 1
    session = _session(client)

    support = client.post(
        "/api/customer/handoff",
        headers={"X-Demo-Session": session["session_id"]},
    )
    assert support.status_code == 201

    limited = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={
            "message": "No reconozco la transacción DEMO-ES-1001; yo no la hice."
        },
    )
    assert limited.status_code == 429
    assert limited.json()["detail"] == "Demo support ticket limit reached"


def test_direct_distinct_ticket_cap_raises_before_extra_insert(tmp_path) -> None:
    client, context = _client(tmp_path)
    context.store.ticket_limit_per_session = 2
    issued = _session(client)
    session = context.store.get_authenticated_session(UUID(issued["session_id"]))
    assert session is not None

    for reason in ("reason-one", "reason-two"):
        record = context.store.create_escalation_ticket(
            session,
            EscalationRequest(
                session_id=session.session_id,
                reason_code=reason,
                summary=f"Summary for {reason}",
            ),
        )
        assert record.verified is True

    with pytest.raises(TicketLimitExceededError):
        context.store.create_escalation_ticket(
            session,
            EscalationRequest(
                session_id=session.session_id,
                reason_code="reason-three",
                summary="Third distinct ticket",
            ),
        )

    with sqlite3.connect(context.store.path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM escalation_tickets WHERE session_id = ?",
            (str(session.session_id),),
        ).fetchone()[0]
    assert count == 2


def test_cleanup_removes_tenant_state_after_24_hours(tmp_path, monkeypatch) -> None:
    client, context = _client(tmp_path)
    current = _clock(
        monkeypatch,
        context.store,
        datetime(2026, 9, 27, 0, 0, tzinfo=timezone.utc),
    )
    session = _session(client)
    ticket = client.post(
        "/api/customer/handoff",
        headers={"X-Demo-Session": session["session_id"]},
    )
    assert ticket.status_code == 201

    current[0] += timedelta(hours=24, seconds=1)
    context.store.cleanup_expired_state()

    with sqlite3.connect(context.store.path) as connection:
        sessions = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        tickets = connection.execute(
            "SELECT COUNT(*) FROM escalation_tickets"
        ).fetchone()[0]
        rate_events = connection.execute(
            "SELECT COUNT(*) FROM rate_limit_events"
        ).fetchone()[0]

    assert sessions == 0
    assert tickets == 0
    assert rate_events == 0
