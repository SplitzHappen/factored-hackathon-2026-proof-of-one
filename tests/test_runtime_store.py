from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.runtime import (
    OperationalStore,
    PersistenceVerificationError,
    RuntimeSchemaVersionError,
    SessionIdentityMismatchError,
    SessionNotFoundError,
)
from app.schemas import (
    AuthenticatedSession,
    ConversationState,
    EscalationRequest,
    SupportedLanguage,
    SessionRole,
    TransactionQuery,
)


def make_session(*, customer_id: str = "customer-demo-001") -> AuthenticatedSession:
    return AuthenticatedSession(
        session_id=uuid4(),
        tenant_id=f"test-tenant-{customer_id}",
        role=SessionRole.CUSTOMER,
        demo_persona_id="persona-demo-001",
        customer_id=customer_id,
        language=SupportedLanguage.ES,
    )


def test_runtime_schema_v3_is_refused_instead_of_partially_migrated(tmp_path) -> None:
    path = tmp_path / "runtime.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE runtime_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO runtime_metadata(key, value) VALUES ('schema_version', '3')"
        )
        connection.commit()

    store = OperationalStore(path)
    with pytest.raises(RuntimeSchemaVersionError, match="Unsupported runtime schema version: 3"):
        store.initialize(data_mode="synthetic")

    with sqlite3.connect(path) as connection:
        version = connection.execute(
            "SELECT value FROM runtime_metadata WHERE key = 'schema_version'"
        ).fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert version == "3"
    assert "sessions" not in tables
    assert "escalation_tickets" not in tables


def test_session_identity_is_persisted_and_cannot_be_rebound(tmp_path) -> None:
    store = OperationalStore(tmp_path / "runtime.sqlite")
    store.initialize()
    session = make_session()

    store.save_authenticated_session(session)
    assert store.get_authenticated_session(session.session_id) == session

    rebound = session.model_copy(update={"customer_id": "customer-demo-999"})
    with pytest.raises(SessionIdentityMismatchError):
        store.save_authenticated_session(rebound)

    assert store.get_authenticated_session(session.session_id) == session


def test_conversation_state_round_trips_without_customer_identity(tmp_path) -> None:
    store = OperationalStore(tmp_path / "runtime.sqlite")
    store.initialize()
    session = make_session()
    store.save_authenticated_session(session)

    state = ConversationState(
        session_id=session.session_id,
        language=SupportedLanguage.PT,
        previous_intent="transaction_lookup",
        pending_query=TransactionQuery(
            date_from=date(2026, 9, 1),
            amount=Decimal("42.50"),
            transaction_type="Purchase",
            limit=5,
        ),
        candidate_transaction_ids=["txn-demo-001", "txn-demo-002"],
        clarification_required=True,
    )

    store.save_conversation_state(session, state)
    assert store.get_conversation_state(session) == state

    with sqlite3.connect(store.path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(conversation_state)")
        }
    assert "customer_id" not in columns
    assert "transcript" not in columns
    assert "message" not in columns


def test_conversation_state_cannot_cross_session_boundary(tmp_path) -> None:
    store = OperationalStore(tmp_path / "runtime.sqlite")
    store.initialize()
    session = make_session()
    other_session = make_session(customer_id="customer-demo-002")
    store.save_authenticated_session(session)
    store.save_authenticated_session(other_session)

    state = ConversationState(
        session_id=other_session.session_id,
        language=SupportedLanguage.ES,
    )
    with pytest.raises(SessionIdentityMismatchError):
        store.save_conversation_state(session, state)


def test_conversation_state_requires_persisted_session(tmp_path) -> None:
    store = OperationalStore(tmp_path / "runtime.sqlite")
    store.initialize()
    session = make_session()
    state = ConversationState(
        session_id=session.session_id,
        language=SupportedLanguage.ES,
    )

    with pytest.raises(SessionNotFoundError):
        store.save_conversation_state(session, state)


def test_conversation_candidate_ids_are_bounded() -> None:
    session = make_session()
    with pytest.raises(ValidationError):
        ConversationState(
            session_id=session.session_id,
            language=SupportedLanguage.ES,
            candidate_transaction_ids=["x" * 129],
        )


def test_escalation_reports_success_only_after_verified_readback(tmp_path) -> None:
    store = OperationalStore(tmp_path / "runtime.sqlite")
    store.initialize()
    session = make_session()
    store.save_authenticated_session(session)
    request = EscalationRequest(
        session_id=session.session_id,
        transaction_id="txn-demo-001",
        reason_code="suspected_unauthorized_activity",
        summary="Customer does not recognize the referenced purchase.",
    )

    result = store.create_escalation_ticket(session, request)

    assert result.persisted is True
    assert result.verified is True
    assert store.get_escalation_record(result.ticket_id) == result

    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            """
            SELECT transaction_id, reason_code, summary, verified_at
            FROM escalation_tickets
            WHERE ticket_id = ?
            """,
            (str(result.ticket_id),),
        ).fetchone()
    assert row is not None
    assert row[:3] == (
        request.transaction_id,
        request.reason_code,
        request.summary,
    )
    assert row[3] is not None


def test_escalation_verification_failure_never_returns_success(
    tmp_path,
    monkeypatch,
) -> None:
    store = OperationalStore(tmp_path / "runtime.sqlite")
    store.initialize()
    session = make_session()
    store.save_authenticated_session(session)
    request = EscalationRequest(
        session_id=session.session_id,
        reason_code="manual_support_required",
        summary="Verified records are insufficient for a safe automated answer.",
    )

    monkeypatch.setattr(store, "_read_ticket_snapshot", lambda ticket_id: None)

    with pytest.raises(PersistenceVerificationError):
        store.create_escalation_ticket(session, request)

    with sqlite3.connect(store.path) as connection:
        persisted, verified = connection.execute(
            """
            SELECT COUNT(*), COUNT(verified_at)
            FROM escalation_tickets
            """
        ).fetchone()
    assert persisted == 1
    assert verified == 0


def test_runtime_sqlite_contains_only_operational_tables(tmp_path) -> None:
    store = OperationalStore(tmp_path / "runtime.sqlite")
    store.initialize()

    with sqlite3.connect(store.path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            )
        }

    assert tables == {
        "runtime_metadata",
        "sessions",
        "conversation_state",
        "escalation_tickets",
        "rate_limit_events",
    }
    assert not {"customers", "products", "transactions"} & tables


def test_existing_unversioned_sqlite_is_rejected_without_adding_runtime_tables(
    tmp_path,
) -> None:
    path = tmp_path / "runtime.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE unexpected_table(value TEXT)")

    store = OperationalStore(path)

    with pytest.raises(RuntimeSchemaVersionError):
        store.initialize()

    with sqlite3.connect(path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            )
        }
    assert tables == {"unexpected_table"}


def test_versioned_runtime_sqlite_rejects_unexpected_tables(tmp_path) -> None:
    path = tmp_path / "runtime.sqlite"
    store = OperationalStore(path)
    store.initialize()
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE customers(customer_id TEXT)")

    with pytest.raises(RuntimeSchemaVersionError):
        store.initialize()
