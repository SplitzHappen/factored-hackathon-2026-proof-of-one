from __future__ import annotations

import inspect
import sqlite3
from pathlib import Path
from uuid import uuid4

import duckdb
import pytest

from app.bank import BankRepository
from app.behavioral_evidence import compute_behavioral_evidence
from app.evidence_service import (
    BehavioralEvidenceService,
    EvidenceAccessError,
    EvidenceAccessPath,
)
from app.runtime import OperationalStore
from app.schemas import (
    AuthenticatedSession,
    EscalationRequest,
    SupportedLanguage,
    SessionRole,
)


def _make_bank(path: Path) -> None:
    con = duckdb.connect(str(path))
    try:
        con.execute(
            """
            CREATE TABLE build_metadata (
                schema_version INTEGER NOT NULL,
                builder_version VARCHAR NOT NULL
            )
            """
        )
        con.execute("INSERT INTO build_metadata VALUES (1, 'test')")
        con.execute(
            """
            CREATE TABLE customers (
                customer_id VARCHAR,
                country VARCHAR,
                detected_accent VARCHAR,
                customer_status VARCHAR
            )
            """
        )
        con.execute(
            """
            INSERT INTO customers VALUES
            ('C001', 'Colombia', 'colombian', 'Active'),
            ('C002', 'Argentina', 'argentine', 'Active')
            """
        )
        con.execute(
            """
            CREATE TABLE products (
                product_id VARCHAR,
                customer_id VARCHAR,
                product_type VARCHAR,
                currency VARCHAR,
                current_balance DECIMAL(15,2),
                opening_date DATE,
                expiration_date DATE,
                product_status VARCHAR,
                last_transaction_date TIMESTAMP
            )
            """
        )
        con.execute(
            """
            INSERT INTO products VALUES
            ('P001', 'C001', 'Savings Account', 'COP', 250000.00,
             DATE '2025-01-01', NULL, 'Active', TIMESTAMP '2026-06-18 10:00:00'),
            ('P002', 'C002', 'Checking Account', 'ARS', 80000.00,
             DATE '2025-02-01', NULL, 'Active', TIMESTAMP '2026-06-17 11:00:00')
            """
        )
        con.execute(
            """
            CREATE TABLE transactions (
                transaction_id VARCHAR,
                transaction_date TIMESTAMP,
                product_id VARCHAR,
                customer_id VARCHAR,
                transaction_type VARCHAR,
                transaction_category VARCHAR,
                amount DECIMAL(15,2),
                currency VARCHAR,
                channel VARCHAR,
                merchant_name VARCHAR,
                merchant_category VARCHAR,
                transaction_country VARCHAR,
                transaction_city VARCHAR,
                transaction_status VARCHAR,
                is_fraud BOOLEAN,
                fraud_score DECIMAL(5,2)
            )
            """
        )
        con.execute(
            """
            INSERT INTO transactions VALUES
            ('T001', TIMESTAMP '2026-06-01 10:00:00', 'P001', 'C001',
             'Payment', 'Retail', 100.00, 'COP', 'App',
             'Merchant A', 'Grocery', 'Colombia', 'Bogota',
             'Approved', false, 1.00),
            ('T002', TIMESTAMP '2026-06-10 10:00:00', 'P001', 'C001',
             'Payment', 'Retail', 100.00, 'COP', 'App',
             'Merchant B', 'Grocery', 'Colombia', 'Bogota',
             'Approved', false, 2.00),
            ('T003', TIMESTAMP '2026-06-15 10:00:00', 'P001', 'C001',
             'Payment', 'Travel', 100.00, 'COP', 'Web',
             'Merchant C', 'Travel', 'Colombia', 'Bogota',
             'Approved', false, 3.00),
            ('T004', TIMESTAMP '2026-06-16 10:00:00', 'P001', 'C001',
             'Payment', 'Retail', 100.00, 'COP', 'App',
             'Merchant D', 'Grocery', 'Colombia', 'Bogota',
             'Approved', false, 4.00),
            ('T005', TIMESTAMP '2026-06-17 08:00:00', 'P001', 'C001',
             'Payment', 'Retail', 100.00, 'COP', 'App',
             'Merchant E', 'Grocery', 'Colombia', 'Bogota',
             'Approved', false, 5.00),
            ('T006', TIMESTAMP '2026-06-17 10:00:00', 'P001', 'C001',
             'Payment', 'Electronics', 400.00, 'COP', 'Mobile',
             'Merchant F', 'Electronics', 'Mexico', 'Mexico City',
             'Approved', true, 99.00),
            ('T007', TIMESTAMP '2026-06-17 10:00:00', 'P001', 'C001',
             'Payment', 'Electronics', 100.00, 'COP', 'Mobile',
             'Merchant G', 'Electronics', 'Mexico', 'Mexico City',
             'Approved', false, 0.00),
            ('T008', TIMESTAMP '2026-06-18 10:00:00', 'P001', 'C001',
             'Payment', 'Electronics', 1000.00, 'COP', 'Mobile',
             'Merchant H', 'Electronics', 'Mexico', 'Mexico City',
             'Approved', true, 100.00),
            ('T900', TIMESTAMP '2026-06-17 11:00:00', 'P002', 'C002',
             'Payment', 'Retail', 12500.00, 'ARS', 'App',
             'Merchant Z', 'Services', 'Argentina', 'Buenos Aires',
             'Approved', true, 92.00)
            """
        )
    finally:
        con.close()


def _session(customer_id: str = "C001") -> AuthenticatedSession:
    return AuthenticatedSession(
        session_id=uuid4(),
        tenant_id=f"test-tenant-{customer_id}",
        role=SessionRole.CUSTOMER,
        demo_persona_id=f"persona-{customer_id}",
        customer_id=customer_id,
        language=SupportedLanguage.ES,
    )


@pytest.fixture()
def service(tmp_path: Path) -> tuple[
    BehavioralEvidenceService,
    BankRepository,
    OperationalStore,
    Path,
]:
    bank_path = tmp_path / "bank.duckdb"
    _make_bank(bank_path)
    runtime = OperationalStore(tmp_path / "runtime.sqlite")
    runtime.initialize()
    bank = BankRepository(bank_path)
    return BehavioralEvidenceService(bank, runtime), bank, runtime, bank_path


def test_customer_path_requires_exact_persisted_session_and_owned_transaction(
    service,
) -> None:
    evidence_service, _, runtime, _ = service
    session = _session()
    runtime.save_authenticated_session(session)

    result = evidence_service.for_customer_session(session, "T006")
    assert result is not None
    assert result.access_path is EvidenceAccessPath.CUSTOMER_SESSION
    assert result.ticket_id is None
    assert result.transaction_id == "T006"
    assert result.evidence.behavioral_unusualness_0_100 == 100.0

    assert evidence_service.for_customer_session(session, "T900") is None

    forged = session.model_copy(update={"customer_id": "C002"})
    with pytest.raises(EvidenceAccessError, match="does not match"):
        evidence_service.for_customer_session(forged, "T900")

    with pytest.raises(EvidenceAccessError, match="persisted"):
        evidence_service.for_customer_session(_session(), "T006")


def test_history_is_strictly_earlier_and_same_timestamp_peers_never_count(
    service,
) -> None:
    _, bank, _, _ = service

    facts = bank.get_behavioral_evidence_input("C001", "T006")

    assert facts is not None
    assert facts.prior_tx_count_lifetime == 5
    assert facts.product_tenure_days == 532.0
    assert facts.prior_24h_tx_count == 2
    assert facts.prior_30d_tx_count == 5
    assert facts.amount_to_prior_currency_mean_ratio == pytest.approx(4.0)
    assert facts.channel_novelty is True
    assert facts.merchant_category_novelty is True
    assert facts.transaction_country_novelty is True


def test_service_uses_the_exact_frozen_behavioral_semantics(service) -> None:
    evidence_service, bank, runtime, _ = service
    session = _session()
    runtime.save_authenticated_session(session)

    facts = bank.get_behavioral_evidence_input("C001", "T006")
    result = evidence_service.for_customer_session(session, "T006")

    assert facts is not None
    assert result is not None
    assert result.evidence == compute_behavioral_evidence(facts)
    assert result.evidence.predictive is False
    assert result.evidence.fraud_probability is False
    assert result.evidence.fraud_adjudication is False
    assert result.evidence.routing_authority is False
    assert result.evidence.queue_priority_authority is False


def test_target_labels_and_reference_scores_cannot_change_runtime_evidence(
    service,
) -> None:
    evidence_service, _, runtime, bank_path = service
    session = _session()
    runtime.save_authenticated_session(session)

    before = evidence_service.for_customer_session(session, "T006")
    assert before is not None

    con = duckdb.connect(str(bank_path))
    try:
        con.execute(
            """
            UPDATE transactions
            SET is_fraud = NOT is_fraud,
                fraud_score = 42.00
            """
        )
    finally:
        con.close()

    after = evidence_service.for_customer_session(session, "T006")

    assert after is not None
    assert after == before

    source = (
        inspect.getsource(BankRepository.get_behavioral_evidence_input)
        + inspect.getsource(BehavioralEvidenceService)
    ).lower()
    assert "is_fraud" not in source
    assert "fraud_score" not in source


def test_verified_ticket_path_resolves_chain_and_reverifies_banking_ownership(
    service,
) -> None:
    evidence_service, _, runtime, _ = service
    session = _session()
    runtime.save_authenticated_session(session)

    good_ticket = runtime.create_escalation_ticket(
        session,
        EscalationRequest(
            session_id=session.session_id,
            transaction_id="T006",
            reason_code="suspected_unauthorized_activity",
            summary="Customer does not recognize this transaction.",
        ),
    )
    good = evidence_service.for_verified_escalation_ticket(
        good_ticket.ticket_id
    )

    assert good is not None
    assert good.access_path is EvidenceAccessPath.VERIFIED_ESCALATION_TICKET
    assert good.ticket_id == good_ticket.ticket_id
    assert good.transaction_id == "T006"

    cross_customer_ticket = runtime.create_escalation_ticket(
        session,
        EscalationRequest(
            session_id=session.session_id,
            transaction_id="T900",
            reason_code="manual_support_required",
            summary="Deliberately mismatched test ticket.",
        ),
    )
    assert (
        evidence_service.for_verified_escalation_ticket(
            cross_customer_ticket.ticket_id
        )
        is None
    )


def test_ticket_without_verified_transaction_context_returns_no_evidence(
    service,
) -> None:
    evidence_service, _, runtime, _ = service
    session = _session()
    runtime.save_authenticated_session(session)

    no_transaction = runtime.create_escalation_ticket(
        session,
        EscalationRequest(
            session_id=session.session_id,
            reason_code="manual_support_required",
            summary="No specific transaction was established.",
        ),
    )
    assert (
        evidence_service.for_verified_escalation_ticket(
            no_transaction.ticket_id
        )
        is None
    )

    unverified_id = uuid4()
    with sqlite3.connect(runtime.path) as connection:
        connection.execute(
            """
            INSERT INTO escalation_tickets(
                ticket_id, session_id, tenant_id, transaction_id, reason_code, summary,
                created_at, verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), NULL)
            """,
            (
                str(unverified_id),
                str(session.session_id),
                session.tenant_id,
                "T006",
                "manual_support_required",
                "Unverified test record.",
            ),
        )

    assert (
        evidence_service.for_verified_escalation_ticket(unverified_id)
        is None
    )
