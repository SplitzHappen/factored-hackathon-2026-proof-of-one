from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import duckdb

from app.bank import BankRepository
from app.interpretation import InterpretationService
from app.runtime import OperationalStore
from app.schemas import (
    AuthenticatedSession,
    InterpretationFallbackReason,
    InterpretationStatus,
    PolicyIntent,
    SessionRole,
    SupportedLanguage,
    TransactionReferenceStatus,
)

REFERENCE_DATE = date(2026, 6, 4)


class FakeProvider:
    def __init__(self, *outputs: str) -> None:
        self.outputs = list(outputs)
        self.calls = 0

    def extract(self, request, *, system_prompt, response_schema):
        del request, system_prompt, response_schema
        self.calls += 1
        if not self.outputs:
            raise AssertionError("unexpected provider call")
        return self.outputs.pop(0)


def _make_bank(path: Path) -> None:
    con = duckdb.connect(str(path))
    try:
        con.execute("""
            CREATE TABLE build_metadata (
                schema_version INTEGER NOT NULL,
                builder_version VARCHAR NOT NULL
            )
        """)
        con.execute("INSERT INTO build_metadata VALUES (1, 'test')")
        con.execute("""
            CREATE TABLE customers (
                customer_id VARCHAR,
                country VARCHAR,
                detected_accent VARCHAR,
                customer_status VARCHAR
            )
        """)
        con.execute(
            "INSERT INTO customers VALUES ('C001', 'Colombia', 'colombian', 'Active')"
        )
        con.execute("""
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
        """)
        con.execute("""
            INSERT INTO products VALUES
            ('P001', 'C001', 'Checking Account', 'COP', 1000.00,
             DATE '2025-01-01', NULL, 'Active', TIMESTAMP '2026-06-04 10:00:00')
        """)
        con.execute("""
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
        """)
        con.execute("""
            INSERT INTO transactions VALUES
            ('T100', TIMESTAMP '2026-06-01 10:00:00', 'P001', 'C001',
             'Payment', 'Retail', 100.00, 'COP', 'App',
             'Merchant A', 'Grocery', 'Colombia', 'Bogota',
             'Approved', false, 1.00),
            ('T101', TIMESTAMP '2026-06-04 10:00:00', 'P001', 'C001',
             'Payment', 'Retail', 100.00, 'COP', 'Web',
             'Merchant B', 'Retail', 'Colombia', 'Bogota',
             'Pending', false, 2.00)
        """)
    finally:
        con.close()


def _session() -> AuthenticatedSession:
    return AuthenticatedSession(
        session_id=uuid4(),
        tenant_id="test-tenant-c001",
        role=SessionRole.CUSTOMER,
        demo_persona_id="persona-c001",
        customer_id="C001",
        language=SupportedLanguage.ES,
    )


def _service(tmp_path: Path, provider: FakeProvider) -> tuple[InterpretationService, AuthenticatedSession]:
    bank_path = tmp_path / "bank.duckdb"
    _make_bank(bank_path)
    bank = BankRepository(bank_path)
    store = OperationalStore(tmp_path / "runtime.sqlite")
    store.initialize()
    session = _session()
    store.save_authenticated_session(session)
    return (
        InterpretationService(
            bank=bank,
            store=store,
            provider=provider,
            max_attempts=2,
        ),
        session,
    )


def test_amount_only_lookup_fallback_preserves_ambiguity_after_invalid_provider_output(tmp_path: Path) -> None:
    provider = FakeProvider("{not-json", "{not-json")
    service, session = _service(tmp_path, provider)

    result = service.interpret(
        session=session,
        message="Quiero consultar una transacci?n por 100 COP.",
        reference_date=REFERENCE_DATE,
    )

    assert provider.calls == 2
    assert result.status is InterpretationStatus.VERIFIED
    assert result.intent is PolicyIntent.TRANSACTION_LOOKUP
    assert result.language is SupportedLanguage.ES
    assert result.transaction_query is not None
    assert result.transaction_query.amount == Decimal("100")
    assert result.transaction_reference_status is TransactionReferenceStatus.AMBIGUOUS
    assert set(result.candidate_transaction_ids) == {"T100", "T101"}
    assert result.fallback_reason is None
    assert result.requires_human_fallback is False


def test_amount_lookup_fallback_does_not_relabel_non_lookup_money_request(tmp_path: Path) -> None:
    provider = FakeProvider("{not-json", "{not-json")
    service, session = _service(tmp_path, provider)

    result = service.interpret(
        session=session,
        message="Quiero hacer una transferencia de 100 COP a otra cuenta.",
        reference_date=REFERENCE_DATE,
    )

    assert provider.calls == 2
    assert result.status is InterpretationStatus.SAFE_FALLBACK
    assert result.intent is PolicyIntent.UNKNOWN
    assert result.transaction_query is None
    assert result.candidate_transaction_ids == []
    assert result.fallback_reason is InterpretationFallbackReason.INVALID_STRUCTURED_OUTPUT
    assert result.requires_human_fallback is True
