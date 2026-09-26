from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from app.bank import BankRepository, IncompatibleBankDatabaseError
from app.schemas import TransactionQuery


def _make_bank(path: Path, *, schema_version: int = 1) -> None:
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
        con.execute(
            "INSERT INTO build_metadata VALUES (?, 'test')",
            [schema_version],
        )
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
             DATE '2025-01-01', NULL, 'Active', TIMESTAMP '2026-06-17 10:00:00'),
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
            ('T001', TIMESTAMP '2026-06-17 10:00:00', 'P001', 'C001',
             'Payment', 'Services', 12500.00, 'COP', 'App',
             'Merchant A', 'Services', 'Colombia', 'Bogota',
             'Approved', false, 3.50),
            ('T002', TIMESTAMP '2026-06-16 09:00:00', 'P001', 'C001',
             'Transfer', NULL, 50000.00, 'COP', 'Web',
             NULL, NULL, 'Colombia', 'Bogota',
             'Pending', false, NULL),
            ('T900', TIMESTAMP '2026-06-17 11:00:00', 'P002', 'C002',
             'Payment', 'Services', 12500.00, 'ARS', 'App',
             'Merchant B', 'Services', 'Argentina', 'Buenos Aires',
             'Approved', true, 92.00)
            """
        )
    finally:
        con.close()


@pytest.fixture()
def bank(tmp_path: Path) -> BankRepository:
    path = tmp_path / "bank.duckdb"
    _make_bank(path)
    return BankRepository(path)


def test_customer_summary_is_scoped(bank: BankRepository) -> None:
    own = bank.get_customer_summary("C001")
    missing = bank.get_customer_summary("C999")

    assert own is not None
    assert own.customer_status == "Active"
    assert "country" not in own.model_dump()
    assert "detected_accent" not in own.model_dump()
    assert missing is None


def test_product_listing_never_returns_other_customer(bank: BankRepository) -> None:
    products = bank.list_customer_products("C001")

    assert [product.product_id for product in products] == ["P001"]


def test_recent_transactions_never_return_other_customer(
    bank: BankRepository,
) -> None:
    transactions = bank.list_recent_transactions("C001", limit=50)

    assert [transaction.transaction_id for transaction in transactions] == [
        "T001",
        "T002",
    ]
    assert "T900" not in {transaction.transaction_id for transaction in transactions}


def test_transaction_search_keeps_customer_filter_server_side(
    bank: BankRepository,
) -> None:
    query = TransactionQuery(
        date_from=date(2026, 6, 17),
        date_to=date(2026, 6, 17),
        amount=Decimal("12500.00"),
        transaction_type="Payment",
        status="Approved",
        limit=10,
    )

    transactions = bank.find_transactions("C001", query)

    assert [transaction.transaction_id for transaction in transactions] == ["T001"]
    assert transactions[0].currency == "COP"


def test_direct_other_customer_transaction_id_is_not_accessible(
    bank: BankRepository,
) -> None:
    assert bank.get_transaction("C001", "T900") is None


def test_owner_can_retrieve_own_transaction(bank: BankRepository) -> None:
    transaction = bank.get_transaction("C002", "T900")

    assert transaction is not None
    assert transaction.transaction_id == "T900"
    assert transaction.is_fraud is True


def test_query_limit_is_bounded(bank: BankRepository) -> None:
    with pytest.raises(ValueError, match="between 1 and 50"):
        bank.list_recent_transactions("C001", limit=51)


def test_repository_fails_closed_on_wrong_curated_schema(tmp_path: Path) -> None:
    path = tmp_path / "bank.duckdb"
    _make_bank(path, schema_version=999)

    with pytest.raises(IncompatibleBankDatabaseError):
        BankRepository(path)
