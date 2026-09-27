from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.schemas import (
    AuthenticatedSession,
    ConversationState,
    EscalationRecord,
    EscalationRequest,
    SessionRole,
    SupportedLanguage,
    TransactionQuery,
)

RUNTIME_SCHEMA_VERSION = 4
RUNTIME_TABLES = {
    "runtime_metadata",
    "sessions",
    "conversation_state",
    "escalation_tickets",
    "rate_limit_events",
}

DEFAULT_SESSION_TTL_SECONDS = 4 * 60 * 60
DEFAULT_TENANT_RETENTION_SECONDS = 24 * 60 * 60
DEFAULT_SESSION_REQUEST_LIMIT = 60
DEFAULT_SESSION_REQUEST_WINDOW_SECONDS = 60
DEFAULT_SESSION_CREATION_LIMIT = 10
DEFAULT_SESSION_CREATION_WINDOW_SECONDS = 60 * 60
DEFAULT_TICKET_LIMIT_PER_SESSION = 5


class RuntimeStoreError(RuntimeError):
    """Base error for fail-closed operational-store failures."""


class RuntimeSchemaVersionError(RuntimeStoreError):
    """Raised when an existing runtime database has an unexpected schema version."""


class RuntimeDataModeMismatchError(RuntimeStoreError):
    """Raised when operational state is reused across banking data modes."""


class SessionIdentityMismatchError(RuntimeStoreError):
    """Raised when a caller tries to reuse a session ID with different identity."""


class SessionNotFoundError(RuntimeStoreError):
    """Raised when operational state refers to a session that was not persisted."""


class PersistenceVerificationError(RuntimeStoreError):
    """Raised when a durable write cannot be read back and verified exactly."""


class RateLimitExceededError(RuntimeStoreError):
    """Raised when a persistent demo abuse limit is exceeded."""


class TicketLimitExceededError(RuntimeStoreError):
    """Raised when one session reaches its bounded distinct-ticket limit."""


class RuntimeReadinessError(RuntimeStoreError):
    """Raised when the runtime store cannot satisfy deployment-readiness checks."""


@dataclass(frozen=True, slots=True)
class _TicketSnapshot:
    ticket_id: UUID
    session_id: UUID
    tenant_id: str
    transaction_id: str | None
    reason_code: str
    summary: str
    idempotency_key: str
    created_at: datetime
    verified_at: datetime | None


@dataclass(frozen=True, slots=True)
class VerifiedEscalationContext:
    """Internal verified ticket chain for analyst-side application services."""

    ticket_id: UUID
    session: AuthenticatedSession
    transaction_id: str | None
    reason_code: str
    summary: str

class OperationalStore:
    """Separate writable SQLite state; never stores authoritative banking records."""

    def __init__(
        self,
        path: Path,
        *,
        busy_timeout_seconds: float = 5.0,
        session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        tenant_retention_seconds: int = DEFAULT_TENANT_RETENTION_SECONDS,
        session_request_limit: int = DEFAULT_SESSION_REQUEST_LIMIT,
        session_request_window_seconds: int = DEFAULT_SESSION_REQUEST_WINDOW_SECONDS,
        session_creation_limit: int = DEFAULT_SESSION_CREATION_LIMIT,
        session_creation_window_seconds: int = DEFAULT_SESSION_CREATION_WINDOW_SECONDS,
        ticket_limit_per_session: int = DEFAULT_TICKET_LIMIT_PER_SESSION,
    ) -> None:
        numeric_values = {
            "busy_timeout_seconds": busy_timeout_seconds,
            "session_ttl_seconds": session_ttl_seconds,
            "tenant_retention_seconds": tenant_retention_seconds,
            "session_request_limit": session_request_limit,
            "session_request_window_seconds": session_request_window_seconds,
            "session_creation_limit": session_creation_limit,
            "session_creation_window_seconds": session_creation_window_seconds,
            "ticket_limit_per_session": ticket_limit_per_session,
        }
        if any(value <= 0 for value in numeric_values.values()):
            raise ValueError("Operational-store lifecycle and limit values must be positive")
        if tenant_retention_seconds < session_ttl_seconds:
            raise ValueError("tenant retention must be at least as long as session TTL")
        self.path = path
        self.busy_timeout_seconds = busy_timeout_seconds
        self.session_ttl_seconds = int(session_ttl_seconds)
        self.tenant_retention_seconds = int(tenant_retention_seconds)
        self.session_request_limit = int(session_request_limit)
        self.session_request_window_seconds = int(session_request_window_seconds)
        self.session_creation_limit = int(session_creation_limit)
        self.session_creation_window_seconds = int(session_creation_window_seconds)
        self.ticket_limit_per_session = int(ticket_limit_per_session)

    def initialize(self, *, data_mode: str | None = None) -> None:
        if data_mode not in {None, "synthetic", "curated"}:
            raise ValueError("data_mode must be 'synthetic', 'curated', or None")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            preexisting_tables = self._runtime_tables(connection)
            self._preflight_existing_runtime(
                connection,
                preexisting_tables,
                data_mode=data_mode,
            )
            journal_row = connection.execute("PRAGMA journal_mode=WAL").fetchone()
            journal_mode = "" if journal_row is None else str(journal_row[0]).casefold()
            if journal_mode != "wal":
                raise RuntimeReadinessError(
                    f"Runtime SQLite must use WAL mode; found {journal_mode or 'unknown'}"
                )
            # Serialize schema inspection/creation so simultaneous startup attempts
            # cannot both conclude that metadata is absent and race to initialize it.
            connection.execute("BEGIN IMMEDIATE")
            existing_tables = self._runtime_tables(connection)
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

                if data_mode is not None:
                    mode_row = connection.execute(
                        "SELECT value FROM runtime_metadata WHERE key = 'data_mode'"
                    ).fetchone()
                    if mode_row is None:
                        populated_rows = sum(
                            int(
                                connection.execute(
                                    f"SELECT COUNT(*) FROM {table}"
                                ).fetchone()[0]
                            )
                            for table in (
                                "sessions",
                                "conversation_state",
                                "escalation_tickets",
                                "rate_limit_events",
                            )
                            if table in existing_tables
                        )
                        if populated_rows:
                            raise RuntimeDataModeMismatchError(
                                "Existing runtime state has no data-mode binding; "
                                "refusing to infer one after operational rows exist."
                            )
                        connection.execute(
                            "INSERT INTO runtime_metadata(key, value) "
                            "VALUES ('data_mode', ?)",
                            (data_mode,),
                        )
                    elif mode_row["value"] != data_mode:
                        raise RuntimeDataModeMismatchError(
                            "Runtime data mode does not match the banking artifact: "
                            f"runtime={mode_row['value']!r}, artifact={data_mode!r}."
                        )

            ddl_statements = (
                """
                CREATE TABLE IF NOT EXISTS runtime_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """,
                """
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
                    updated_at TEXT NOT NULL,
                    revoked_at TEXT
                )
                """,
                """
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
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS escalation_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL
                        REFERENCES sessions(session_id) ON DELETE RESTRICT,
                    tenant_id TEXT NOT NULL
                        CHECK(length(tenant_id) BETWEEN 1 AND 128),
                    transaction_id TEXT
                        CHECK(transaction_id IS NULL OR length(transaction_id) BETWEEN 1 AND 128),
                    reason_code TEXT NOT NULL
                        CHECK(length(reason_code) BETWEEN 1 AND 80),
                    summary TEXT NOT NULL
                        CHECK(length(summary) BETWEEN 1 AND 500),
                    idempotency_key TEXT NOT NULL UNIQUE
                        CHECK(length(idempotency_key) = 64),
                    created_at TEXT NOT NULL,
                    verified_at TEXT
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS rate_limit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope TEXT NOT NULL CHECK(length(scope) BETWEEN 1 AND 40),
                    subject TEXT NOT NULL CHECK(length(subject) BETWEEN 1 AND 128),
                    created_at TEXT NOT NULL
                )
                """,
            )
            for statement in ddl_statements:
                connection.execute(statement)
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_escalation_tickets_tenant_verified
                ON escalation_tickets(tenant_id, verified_at, created_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rate_limit_events_scope_subject_time
                ON rate_limit_events(scope, subject, created_at)
                """
            )
            if not existing_tables:
                connection.execute(
                    "INSERT INTO runtime_metadata(key, value) VALUES ('schema_version', ?)",
                    (str(RUNTIME_SCHEMA_VERSION),),
                )
                if data_mode is not None:
                    connection.execute(
                        "INSERT INTO runtime_metadata(key, value) VALUES ('data_mode', ?)",
                        (data_mode,),
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
                SELECT session_id, tenant_id, role, demo_persona_id, customer_id, language,
                       created_at, revoked_at
                FROM sessions
                WHERE session_id = ?
                """,
                (str(session_id),),
            ).fetchone()
        return self._active_session_from_row(row)

    def authenticate_session_request(
        self,
        session_id: UUID,
    ) -> AuthenticatedSession | None:
        """Authenticate one active session and persist its request-rate event atomically."""

        now = self._utc_now()
        cutoff = now - timedelta(seconds=self.session_request_window_seconds)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT session_id, tenant_id, role, demo_persona_id, customer_id, language,
                       created_at, revoked_at
                FROM sessions
                WHERE session_id = ?
                """,
                (str(session_id),),
            ).fetchone()
            session = self._active_session_from_row(row, now=now)
            if session is None:
                return None
            connection.execute(
                """
                DELETE FROM rate_limit_events
                WHERE scope = 'session_request' AND subject = ? AND created_at < ?
                """,
                (str(session_id), cutoff.isoformat()),
            )
            count = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM rate_limit_events
                    WHERE scope = 'session_request' AND subject = ?
                    """,
                    (str(session_id),),
                ).fetchone()[0]
            )
            if count >= self.session_request_limit:
                raise RateLimitExceededError(
                    "Rate limit exceeded for session_request"
                )
            connection.execute(
                """
                INSERT INTO rate_limit_events(scope, subject, created_at)
                VALUES ('session_request', ?, ?)
                """,
                (str(session_id), now.isoformat()),
            )
        return session

    def _active_session_from_row(
        self,
        row: sqlite3.Row | None,
        *,
        now: datetime | None = None,
    ) -> AuthenticatedSession | None:
        if row is None or row["revoked_at"] is not None:
            return None
        created_at = datetime.fromisoformat(row["created_at"])
        reference_time = self._utc_now() if now is None else now
        if reference_time >= created_at + timedelta(seconds=self.session_ttl_seconds):
            return None
        return self._session_from_row(row)

    def revoke_session(self, session_id: UUID) -> bool:
        """Revoke an active customer session without deleting retained support state."""

        now = self._utc_now().isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE sessions
                SET revoked_at = ?, updated_at = ?
                WHERE session_id = ? AND revoked_at IS NULL
                """,
                (now, now, str(session_id)),
            )
        return cursor.rowcount == 1

    def enforce_session_creation_rate(self, subject: str) -> None:
        self._enforce_rate_limit(
            scope="session_create",
            subject=subject,
            limit=self.session_creation_limit,
            window_seconds=self.session_creation_window_seconds,
        )

    def cleanup_expired_state(self) -> None:
        """Delete retained visitor state after the bounded tenant-retention window."""

        cutoff = self._utc_now() - timedelta(seconds=self.tenant_retention_seconds)
        cutoff_text = cutoff.isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                DELETE FROM escalation_tickets
                WHERE session_id IN (
                    SELECT session_id FROM sessions WHERE created_at < ?
                )
                """,
                (cutoff_text,),
            )
            connection.execute(
                "DELETE FROM sessions WHERE created_at < ?",
                (cutoff_text,),
            )
            connection.execute(
                "DELETE FROM rate_limit_events WHERE created_at < ?",
                (cutoff_text,),
            )

    def _enforce_rate_limit(
        self,
        *,
        scope: str,
        subject: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        if not scope or len(scope) > 40:
            raise ValueError("rate-limit scope must be between 1 and 40 characters")
        if not subject or len(subject) > 128:
            raise ValueError("rate-limit subject must be between 1 and 128 characters")
        now = self._utc_now()
        cutoff = now - timedelta(seconds=window_seconds)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                DELETE FROM rate_limit_events
                WHERE scope = ? AND subject = ? AND created_at < ?
                """,
                (scope, subject, cutoff.isoformat()),
            )
            count = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM rate_limit_events
                    WHERE scope = ? AND subject = ?
                    """,
                    (scope, subject),
                ).fetchone()[0]
            )
            if count >= limit:
                raise RateLimitExceededError(
                    f"Rate limit exceeded for {scope}"
                )
            connection.execute(
                """
                INSERT INTO rate_limit_events(scope, subject, created_at)
                VALUES (?, ?, ?)
                """,
                (scope, subject, now.isoformat()),
            )

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> AuthenticatedSession:
        return AuthenticatedSession(
            session_id=UUID(row["session_id"]),
            tenant_id=row["tenant_id"],
            role=SessionRole(row["role"]),
            demo_persona_id=row["demo_persona_id"],
            customer_id=row["customer_id"],
            language=SupportedLanguage(row["language"]),
        )

    def _get_persisted_session_identity(
        self,
        session_id: UUID,
    ) -> AuthenticatedSession | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, tenant_id, role, demo_persona_id, customer_id, language
                FROM sessions
                WHERE session_id = ?
                """,
                (str(session_id),),
            ).fetchone()
        return None if row is None else self._session_from_row(row)

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
        """Persist one retry-safe verified ticket for one session/reason/transaction."""

        if request.session_id != session.session_id:
            raise SessionIdentityMismatchError(
                "Escalation request must belong to the authenticated session"
            )
        self._verify_persisted_session(session)

        idempotency_key = self._ticket_idempotency_key(session, request)
        created_new = False
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT ticket_id
                FROM escalation_tickets
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                ticket_id = UUID(existing["ticket_id"])
            else:
                ticket_count = int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM escalation_tickets
                        WHERE session_id = ?
                        """,
                        (str(session.session_id),),
                    ).fetchone()[0]
                )
                if ticket_count >= self.ticket_limit_per_session:
                    raise TicketLimitExceededError(
                        "Support ticket limit reached for this session"
                    )
                ticket_id = uuid4()
                now = self._utc_now()
                connection.execute(
                    """
                    INSERT INTO escalation_tickets(
                        ticket_id, session_id, tenant_id, transaction_id, reason_code, summary,
                        idempotency_key, created_at, verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        str(ticket_id),
                        str(session.session_id),
                        session.tenant_id,
                        request.transaction_id,
                        request.reason_code,
                        request.summary,
                        idempotency_key,
                        now.isoformat(),
                    ),
                )
                created_new = True

        persisted = self._read_ticket_snapshot(ticket_id)
        if persisted is None:
            raise PersistenceVerificationError(
                "Escalation ticket persistence could not be verified"
            )
        if (
            persisted.session_id != session.session_id
            or persisted.tenant_id != session.tenant_id
            or persisted.transaction_id != request.transaction_id
            or persisted.reason_code != request.reason_code
            or persisted.idempotency_key != idempotency_key
        ):
            raise PersistenceVerificationError(
                "Escalation ticket identity changed during persistence verification"
            )
        if created_new and persisted.summary != request.summary:
            raise PersistenceVerificationError(
                "Escalation ticket summary changed during persistence verification"
            )

        if persisted.verified_at is None:
            verified_at = self._utc_now()
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE escalation_tickets
                    SET verified_at = ?
                    WHERE ticket_id = ? AND verified_at IS NULL
                    """,
                    (verified_at.isoformat(), str(ticket_id)),
                )
                if cursor.rowcount not in {0, 1}:
                    raise PersistenceVerificationError(
                        "Escalation ticket verification status could not be persisted"
                    )

        final = self._read_ticket_snapshot(ticket_id)
        if final is None or final.verified_at is None:
            raise PersistenceVerificationError(
                "Escalation ticket verification status could not be read back"
            )
        if (
            final.session_id != session.session_id
            or final.tenant_id != session.tenant_id
            or final.transaction_id != request.transaction_id
            or final.reason_code != request.reason_code
            or final.idempotency_key != idempotency_key
        ):
            raise PersistenceVerificationError(
                "Escalation ticket changed during verification"
            )

        return EscalationRecord(
            ticket_id=final.ticket_id,
            session_id=final.session_id,
            created_at=final.created_at,
            persisted=True,
            verified=True,
        )

    @staticmethod
    def _ticket_idempotency_key(
        session: AuthenticatedSession,
        request: EscalationRequest,
    ) -> str:
        raw = "|".join(
            (
                str(session.session_id),
                request.transaction_id or "",
                request.reason_code,
            )
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def list_verified_escalation_ticket_ids_for_tenant(
        self,
        tenant_id: str,
    ) -> list[UUID]:
        """Return only verified tickets belonging to one server-issued tenant."""

        if not 1 <= len(tenant_id) <= 128:
            raise ValueError("tenant_id must be between 1 and 128 characters")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT t.ticket_id
                FROM escalation_tickets AS t
                JOIN sessions AS s
                  ON s.session_id = t.session_id
                 AND s.tenant_id = t.tenant_id
                WHERE t.tenant_id = ? AND t.verified_at IS NOT NULL
                ORDER BY t.created_at, t.ticket_id
                """,
                (tenant_id,),
            ).fetchall()
        return [UUID(row["ticket_id"]) for row in rows]

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
        if snapshot is None or snapshot.verified_at is None:
            return None

        session = self._get_persisted_session_identity(snapshot.session_id)
        if session is None or snapshot.tenant_id != session.tenant_id:
            return None

        return VerifiedEscalationContext(
            ticket_id=snapshot.ticket_id,
            session=session,
            transaction_id=snapshot.transaction_id,
            reason_code=snapshot.reason_code,
            summary=snapshot.summary,
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
                SELECT ticket_id, session_id, tenant_id, transaction_id, reason_code, summary,
                       idempotency_key, created_at, verified_at
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
            tenant_id=row["tenant_id"],
            transaction_id=row["transaction_id"],
            reason_code=row["reason_code"],
            summary=row["summary"],
            idempotency_key=row["idempotency_key"],
            created_at=datetime.fromisoformat(row["created_at"]),
            verified_at=(
                datetime.fromisoformat(row["verified_at"])
                if row["verified_at"] is not None
                else None
            ),
        )

    @staticmethod
    def _runtime_tables(connection: sqlite3.Connection) -> set[str]:
        return {
            row["name"]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            )
        }

    def _preflight_existing_runtime(
        self,
        connection: sqlite3.Connection,
        existing_tables: set[str],
        *,
        data_mode: str | None,
    ) -> None:
        """Reject incompatible existing runtime state before changing journal mode."""

        if not existing_tables:
            return
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
        if data_mode is None:
            return
        mode_row = connection.execute(
            "SELECT value FROM runtime_metadata WHERE key = 'data_mode'"
        ).fetchone()
        if mode_row is not None and mode_row["value"] != data_mode:
            raise RuntimeDataModeMismatchError(
                "Runtime data mode does not match the banking artifact: "
                f"runtime={mode_row['value']!r}, artifact={data_mode!r}."
            )
        if mode_row is None:
            populated_rows = sum(
                int(
                    connection.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()[0]
                )
                for table in (
                    "sessions",
                    "conversation_state",
                    "escalation_tickets",
                    "rate_limit_events",
                )
                if table in existing_tables
            )
            if populated_rows:
                raise RuntimeDataModeMismatchError(
                    "Existing runtime state has no data-mode binding; "
                    "refusing to infer one after operational rows exist."
                )

    def check_ready(self, *, expected_data_mode: str) -> None:
        """Verify schema/mode binding, WAL, and runtime-store writability."""

        with self._connect() as connection:
            journal_row = connection.execute("PRAGMA journal_mode").fetchone()
            journal_mode = "" if journal_row is None else str(journal_row[0]).casefold()
            if journal_mode != "wal":
                raise RuntimeReadinessError(
                    f"Runtime SQLite is not in WAL mode: {journal_mode or 'unknown'}"
                )
            schema_row = connection.execute(
                "SELECT value FROM runtime_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if schema_row is None or schema_row["value"] != str(RUNTIME_SCHEMA_VERSION):
                raise RuntimeReadinessError("Runtime schema version is not ready")
            mode_row = connection.execute(
                "SELECT value FROM runtime_metadata WHERE key = 'data_mode'"
            ).fetchone()
            if mode_row is None or mode_row["value"] != expected_data_mode:
                raise RuntimeReadinessError("Runtime data-mode binding is not ready")
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE runtime_metadata
                SET value = value
                WHERE key = 'schema_version'
                """
            )
            if cursor.rowcount != 1:
                raise RuntimeReadinessError("Runtime store is not writable")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self.path,
            timeout=self.busy_timeout_seconds,
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                f"PRAGMA busy_timeout = {int(self.busy_timeout_seconds * 1000)}"
            )
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)
