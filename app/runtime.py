from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.schemas import (
    AuthenticatedSession,
    ConversationState,
    EscalationRecord,
    EscalationRequest,
    SupportedLanguage,
    TransactionQuery,
)

RUNTIME_SCHEMA_VERSION = 2
RUNTIME_TABLES = {
    "runtime_metadata",
    "sessions",
    "conversation_state",
    "escalation_tickets",
}


class RuntimeStoreError(RuntimeError):
    """Base error for fail-closed operational-store failures."""


class RuntimeSchemaVersionError(RuntimeStoreError):
    """Raised when an existing runtime database has an unexpected schema version."""


class SessionIdentityMismatchError(RuntimeStoreError):
    """Raised when a caller tries to reuse a session ID with different identity."""


class SessionNotFoundError(RuntimeStoreError):
    """Raised when operational state refers to a session that was not persisted."""


class PersistenceVerificationError(RuntimeStoreError):
    """Raised when a durable write cannot be read back and verified exactly."""


@dataclass(frozen=True, slots=True)
class _TicketSnapshot:
    ticket_id: UUID
    session_id: UUID
    transaction_id: str | None
    reason_code: str
    summary: str
    created_at: datetime
    verified_at: datetime | None


@dataclass(frozen=True, slots=True)
class VerifiedEscalationContext:
    """Internal verified ticket chain for analyst-side application services."""

    ticket_id: UUID
    session: AuthenticatedSession
    transaction_id: str

class OperationalStore:
    """Separate writable SQLite state; never stores authoritative banking records."""

    def __init__(self, path: Path, *, busy_timeout_seconds: float = 5.0) -> None:
        if busy_timeout_seconds <= 0:
            raise ValueError("busy_timeout_seconds must be positive")
        self.path = path
        self.busy_timeout_seconds = busy_timeout_seconds

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            existing_tables = {
                row["name"]
                for row in connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    """
                )
            }
            if existing_tables:
                unexpected_tables = existing_tables - RUNTIME_TABLES
                if unexpected_tables:
                    raise RuntimeSchemaVersionError(
                        "Runtime database contains unexpected tables: "
                        + ", ".join(sorted(unexpected_tables))
                    )
                if "runtime_metadata" not in existing_tables:
                    raise RuntimeSchemaVersionError(
                        "Existing runtime database is missing schema metadata"
                    )
                row = connection.execute(
                    "SELECT value FROM runtime_metadata WHERE key = 'schema_version'"
                ).fetchone()
                if row is None or row["value"] != str(RUNTIME_SCHEMA_VERSION):
                    version = None if row is None else row["value"]
                    raise RuntimeSchemaVersionError(
                        f"Unsupported runtime schema version: {version}"
                    )

            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runtime_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL
                        CHECK(length(tenant_id) BETWEEN 1 AND 128),
                    role TEXT NOT NULL CHECK(role IN ('customer', 'analyst')),
                    demo_persona_id TEXT NOT NULL
                        CHECK(length(demo_persona_id) BETWEEN 1 AND 128),
                    customer_id TEXT NOT NULL
                        CHECK(length(customer_id) BETWEEN 1 AND 128),
                    language TEXT NOT NULL CHECK(language IN ('es', 'pt')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversation_state (
                    session_id TEXT PRIMARY KEY
                        REFERENCES sessions(session_id) ON DELETE CASCADE,
                    language TEXT NOT NULL CHECK(language IN ('es', 'pt')),
                    previous_intent TEXT
                        CHECK(previous_intent IS NULL OR length(previous_intent) <= 120),
                    pending_query_json TEXT
                        CHECK(pending_query_json IS NULL OR length(pending_query_json) <= 2048),
                    candidate_transaction_ids_json TEXT NOT NULL
                        CHECK(length(candidate_transaction_ids_json) <= 8192),
                    clarification_required INTEGER NOT NULL
                        CHECK(clarification_required IN (0, 1)),
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS escalation_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL
                        REFERENCES sessions(session_id) ON DELETE RESTRICT,
                    transaction_id TEXT
                        CHECK(transaction_id IS NULL OR length(transaction_id) BETWEEN 1 AND 128),
                    reason_code TEXT NOT NULL
                        CHECK(length(reason_code) BETWEEN 1 AND 80),
                    summary TEXT NOT NULL
                        CHECK(length(summary) BETWEEN 1 AND 500),
                    created_at TEXT NOT NULL,
                    verified_at TEXT
                );
                """
            )
            if not existing_tables:
                connection.execute(
                    "INSERT INTO runtime_metadata(key, value) VALUES ('schema_version', ?)",
                    (str(RUNTIME_SCHEMA_VERSION),),
                )

    def save_authenticated_session(self, session: AuthenticatedSession) -> None:
        """Persist the server-controlled session once; identity is immutable thereafter."""

        now = self._utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT tenant_id, role, demo_persona_id, customer_id, language
                FROM sessions
                WHERE session_id = ?
                """,
                (str(session.session_id),),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO sessions(
                        session_id, tenant_id, role, demo_persona_id, customer_id,
                        language, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(session.session_id),
                        session.tenant_id,
                        session.role.value,
                        session.demo_persona_id,
                        session.customer_id,
                        session.language.value,
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
                return

            if (
                existing["tenant_id"] != session.tenant_id
                or existing["role"] != session.role.value
                or existing["demo_persona_id"] != session.demo_persona_id
                or existing["customer_id"] != session.customer_id
                or existing["language"] != session.language.value
            ):
                raise SessionIdentityMismatchError(
                    "Existing session identity cannot be changed"
                )

    def get_authenticated_session(self, session_id: UUID) -> AuthenticatedSession | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, tenant_id, role, demo_persona_id, customer_id, language
                FROM sessions
                WHERE session_id = ?
                """,
                (str(session_id),),
            ).fetchone()
        if row is None:
            return None
        from app.schemas import SessionRole

        return AuthenticatedSession(
            session_id=UUID(row["session_id"]),
            tenant_id=row["tenant_id"],
            role=SessionRole(row["role"]),
            demo_persona_id=row["demo_persona_id"],
            customer_id=row["customer_id"],
            language=SupportedLanguage(row["language"]),
        )

    def save_conversation_state(
        self,
        session: AuthenticatedSession,
        state: ConversationState,
    ) -> None:
        """Persist bounded multi-turn state without any authority to change identity."""

        if state.session_id != session.session_id:
            raise SessionIdentityMismatchError(
                "Conversation state must belong to the authenticated session"
            )
        self._verify_persisted_session(session)

        pending_query_json = (
            state.pending_query.model_dump_json() if state.pending_query is not None else None
        )
        candidate_ids_json = json.dumps(
            state.candidate_transaction_ids,
            ensure_ascii=True,
            separators=(",", ":"),
        )
        now = self._utc_now().isoformat()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversation_state(
                    session_id, language, previous_intent, pending_query_json,
                    candidate_transaction_ids_json, clarification_required, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    language = excluded.language,
                    previous_intent = excluded.previous_intent,
                    pending_query_json = excluded.pending_query_json,
                    candidate_transaction_ids_json = excluded.candidate_transaction_ids_json,
                    clarification_required = excluded.clarification_required,
                    updated_at = excluded.updated_at
                """,
                (
                    str(state.session_id),
                    state.language.value,
                    state.previous_intent,
                    pending_query_json,
                    candidate_ids_json,
                    int(state.clarification_required),
                    now,
                ),
            )

    def get_conversation_state(
        self,
        session: AuthenticatedSession,
    ) -> ConversationState | None:
        self._verify_persisted_session(session)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, language, previous_intent, pending_query_json,
                       candidate_transaction_ids_json, clarification_required
                FROM conversation_state
                WHERE session_id = ?
                """,
                (str(session.session_id),),
            ).fetchone()
        if row is None:
            return None

        pending_query = (
            TransactionQuery.model_validate_json(row["pending_query_json"])
            if row["pending_query_json"] is not None
            else None
        )
        candidate_ids = json.loads(row["candidate_transaction_ids_json"])
        return ConversationState(
            session_id=UUID(row["session_id"]),
            language=SupportedLanguage(row["language"]),
            previous_intent=row["previous_intent"],
            pending_query=pending_query,
            candidate_transaction_ids=candidate_ids,
            clarification_required=bool(row["clarification_required"]),
        )

    def create_escalation_ticket(
        self,
        session: AuthenticatedSession,
        request: EscalationRequest,
    ) -> EscalationRecord:
        """Persist, re-read, and verify a handoff before reporting success."""

        if request.session_id != session.session_id:
            raise SessionIdentityMismatchError(
                "Escalation request must belong to the authenticated session"
            )
        self._verify_persisted_session(session)

        expected = _TicketSnapshot(
            ticket_id=uuid4(),
            session_id=session.session_id,
            transaction_id=request.transaction_id,
            reason_code=request.reason_code,
            summary=request.summary,
            created_at=self._utc_now(),
            verified_at=None,
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO escalation_tickets(
                    ticket_id, session_id, transaction_id, reason_code, summary,
                    created_at, verified_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    str(expected.ticket_id),
                    str(expected.session_id),
                    expected.transaction_id,
                    expected.reason_code,
                    expected.summary,
                    expected.created_at.isoformat(),
                ),
            )

        persisted = self._read_ticket_snapshot(expected.ticket_id)
        if persisted != expected:
            raise PersistenceVerificationError(
                "Escalation ticket persistence could not be verified"
            )

        verified_at = self._utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE escalation_tickets
                SET verified_at = ?
                WHERE ticket_id = ? AND verified_at IS NULL
                """,
                (verified_at.isoformat(), str(expected.ticket_id)),
            )
            if cursor.rowcount != 1:
                raise PersistenceVerificationError(
                    "Escalation ticket verification status could not be persisted"
                )

        final = self._read_ticket_snapshot(expected.ticket_id)
        if final is None or final.verified_at != verified_at:
            raise PersistenceVerificationError(
                "Escalation ticket verification status could not be read back"
            )
        if (
            final.ticket_id != expected.ticket_id
            or final.session_id != expected.session_id
            or final.transaction_id != expected.transaction_id
            or final.reason_code != expected.reason_code
            or final.summary != expected.summary
            or final.created_at != expected.created_at
        ):
            raise PersistenceVerificationError(
                "Escalation ticket changed during persistence verification"
            )

        return EscalationRecord(
            ticket_id=final.ticket_id,
            session_id=final.session_id,
            created_at=final.created_at,
            persisted=True,
            verified=True,
        )

    def get_escalation_record(self, ticket_id: UUID) -> EscalationRecord | None:
        snapshot = self._read_ticket_snapshot(ticket_id)
        if snapshot is None:
            return None
        return EscalationRecord(
            ticket_id=snapshot.ticket_id,
            session_id=snapshot.session_id,
            created_at=snapshot.created_at,
            persisted=True,
            verified=snapshot.verified_at is not None,
        )

    def resolve_verified_escalation_context(
        self,
        ticket_id: UUID,
    ) -> VerifiedEscalationContext | None:
        """Resolve only a verified ticket through its persisted customer session.

        This deliberately accepts a ticket ID only. It does not provide arbitrary
        customer or transaction lookup and is intended for the later analyst role
        boundary, which remains separate from this storage layer.
        """

        snapshot = self._read_ticket_snapshot(ticket_id)
        if (
            snapshot is None
            or snapshot.verified_at is None
            or snapshot.transaction_id is None
        ):
            return None

        session = self.get_authenticated_session(snapshot.session_id)
        if session is None:
            return None

        return VerifiedEscalationContext(
            ticket_id=snapshot.ticket_id,
            session=session,
            transaction_id=snapshot.transaction_id,
        )

    def _verify_persisted_session(self, session: AuthenticatedSession) -> None:
        persisted = self.get_authenticated_session(session.session_id)
        if persisted is None:
            raise SessionNotFoundError("Authenticated session is not persisted")
        if persisted != session:
            raise SessionIdentityMismatchError(
                "Authenticated session does not match persisted server identity"
            )

    def _read_ticket_snapshot(self, ticket_id: UUID) -> _TicketSnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT ticket_id, session_id, transaction_id, reason_code, summary,
                       created_at, verified_at
                FROM escalation_tickets
                WHERE ticket_id = ?
                """,
                (str(ticket_id),),
            ).fetchone()
        if row is None:
            return None
        return _TicketSnapshot(
            ticket_id=UUID(row["ticket_id"]),
            session_id=UUID(row["session_id"]),
            transaction_id=row["transaction_id"],
            reason_code=row["reason_code"],
            summary=row["summary"],
            created_at=datetime.fromisoformat(row["created_at"]),
            verified_at=(
                datetime.fromisoformat(row["verified_at"])
                if row["verified_at"] is not None
                else None
            ),
        )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self.path,
            timeout=self.busy_timeout_seconds,
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)
