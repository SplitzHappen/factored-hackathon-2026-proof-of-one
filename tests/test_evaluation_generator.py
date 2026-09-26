from __future__ import annotations

from pathlib import Path

import duckdb

from evaluation.contracts import (
    DevelopmentCase,
    HeldoutAnswerKey,
    HeldoutCase,
)
from evaluation.generate import generate
from evaluation.suite import load_jsonl, validate_suite


def _build_fixture_database(path: Path) -> None:
    con = duckdb.connect(str(path))
    try:
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

        countries = [("Colombia", "COP"), ("Mexico", "MXN"), ("Argentina", "ARS")]
        for index in range(1, 361):
            country, currency = countries[(index - 1) % len(countries)]
            customer_id = f"C{index:04d}"
            product_id = f"P{index:04d}"
            con.execute(
                "INSERT INTO customers VALUES (?, ?, ?, ?)",
                [customer_id, country, None, "Active"],
            )
            con.execute(
                """
                INSERT INTO products VALUES (
                    ?, ?, 'Checking', ?, 1000.00, DATE '2025-01-01',
                    NULL, 'Active', TIMESTAMP '2026-09-25 12:00:00'
                )
                """,
                [product_id, customer_id, currency],
            )
            for tx_index in range(2):
                transaction_id = f"T{index:04d}-{tx_index}"
                day = (index % 20) + 1
                status = "Declined" if tx_index == 0 and index % 4 == 0 else "Approved"
                con.execute(
                    """
                    INSERT INTO transactions VALUES (
                        ?, make_timestamp(2026, 9, ?, 12, ?, 0),
                        ?, ?, 'Purchase', 'Card Purchase', ?, ?, 'App',
                        'Fixture Merchant', 'Retail', ?, 'Fixture City', ?, FALSE, NULL
                    )
                    """,
                    [
                        transaction_id,
                        day,
                        tx_index,
                        product_id,
                        customer_id,
                        index * 10 + tx_index,
                        currency,
                        country,
                        status,
                    ],
                )
    finally:
        con.close()


def test_generator_creates_full_disjoint_reproducible_pools(tmp_path: Path) -> None:
    db_path = tmp_path / "bank.duckdb"
    _build_fixture_database(db_path)

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    first_summary = generate(database_path=db_path, output_dir=first_dir)
    second_summary = generate(database_path=db_path, output_dir=second_dir)

    assert first_summary == second_summary
    assert first_summary["heldout_cases"] == 200
    assert first_summary["development_cases"] == 100
    assert first_summary["customer_overlap"] == 0

    first_private = first_dir / "private"
    second_private = second_dir / "private"

    for filename in (
        "heldout_cases.jsonl",
        "heldout_answer_keys.jsonl",
        "development_cases.jsonl",
        "development_answer_keys.jsonl",
    ):
        assert (first_private / filename).read_bytes() == (
            second_private / filename
        ).read_bytes()

    heldout_cases = load_jsonl(
        first_private / "heldout_cases.jsonl",
        HeldoutCase,
    )
    heldout_keys = _load_models(
        first_private / "heldout_answer_keys.jsonl",
        HeldoutAnswerKey,
    )
    development_cases = _load_models(
        first_private / "development_cases.jsonl",
        DevelopmentCase,
    )

    validate_suite(heldout_cases, heldout_keys)

    heldout_primary_customers = {
        case.locator.customer_id
        for case in heldout_cases
        if case.language.value == "es"
    }
    development_primary_customers = {
        case.locator.customer_id
        for case in development_cases
        if case.language.value == "es"
    }
    assert heldout_primary_customers.isdisjoint(development_primary_customers)

    heldout_ids = {case.case_id for case in heldout_cases}
    for case in heldout_cases:
        if case.language.value == "pt":
            assert case.source_pair_id in heldout_ids

    normal_spanish = [
        case
        for case in heldout_cases
        if case.language.value == "es"
        and case.category.value == "normal_supported"
    ]
    # The fixture's "-1" transaction is always later than "-0".
    assert all(
        case.locator.transaction_ids[0].endswith("-1")
        for case in normal_spanish
    )

    serialized = (first_private / "heldout_cases.jsonl").read_text(encoding="utf-8")
    assert "is_fraud" not in serialized
    assert "fraud_score" not in serialized


def test_different_seed_changes_selected_cases(tmp_path: Path) -> None:
    db_path = tmp_path / "bank.duckdb"
    _build_fixture_database(db_path)

    first_dir = tmp_path / "seed-a"
    second_dir = tmp_path / "seed-b"

    generate(database_path=db_path, output_dir=first_dir, seed="seed-a")
    generate(database_path=db_path, output_dir=second_dir, seed="seed-b")

    assert (
        (first_dir / "private" / "heldout_cases.jsonl").read_bytes()
        != (second_dir / "private" / "heldout_cases.jsonl").read_bytes()
    )
