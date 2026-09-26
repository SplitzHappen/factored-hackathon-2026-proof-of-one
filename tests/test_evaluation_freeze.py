from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from evaluation.freeze import (
    FreezeError,
    freeze_evaluation,
    verify_frozen_evaluation,
)
from evaluation.suite import SUITE_VERSION


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


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
        con.execute(
            """
            CREATE TABLE build_metadata (
                schema_version INTEGER NOT NULL,
                builder_version VARCHAR NOT NULL
            )
            """
        )
        con.execute("INSERT INTO build_metadata VALUES (1, 'fixture-builder')")

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


def _write_curated_manifest(path: Path, db_path: Path) -> None:
    payload = {
        "builder_version": "fixture-builder",
        "curated_schema_version": 1,
        "database_sha256": _sha256(db_path),
        "row_counts": {
            "customers": 360,
            "products": 360,
            "transactions": 720,
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_freeze_is_atomic_verifiable_and_non_overwritable(tmp_path: Path) -> None:
    db_path = tmp_path / "bank.duckdb"
    curated_manifest_path = tmp_path / "build_manifest.json"
    output_root = tmp_path / "evaluation"
    _build_fixture_database(db_path)
    _write_curated_manifest(curated_manifest_path, db_path)

    manifest = freeze_evaluation(
        database_path=db_path,
        curated_manifest_path=curated_manifest_path,
        output_root=output_root,
        repo_root=Path("."),
    )

    frozen_dir = output_root / "private" / "frozen" / SUITE_VERSION
    assert frozen_dir.is_dir()
    assert manifest.suite.case_count == 200
    assert manifest.suite.spanish_count == 150
    assert manifest.suite.portuguese_count == 50
    assert manifest.suite.multi_turn_count >= 50
    assert manifest.suite.high_risk_repeat_count == 85
    assert manifest.development_case_count == 100
    assert manifest.development_spanish_count == 75
    assert manifest.development_portuguese_count == 25
    assert manifest.heldout_development_customer_overlap == 0

    verified = verify_frozen_evaluation(
        frozen_dir=frozen_dir,
        database_path=db_path,
        curated_manifest_path=curated_manifest_path,
    )
    assert verified == manifest

    with pytest.raises(FreezeError, match="already exists"):
        freeze_evaluation(
            database_path=db_path,
            curated_manifest_path=curated_manifest_path,
            output_root=output_root,
            repo_root=Path("."),
        )


def test_verify_detects_frozen_artifact_tampering(tmp_path: Path) -> None:
    db_path = tmp_path / "bank.duckdb"
    curated_manifest_path = tmp_path / "build_manifest.json"
    output_root = tmp_path / "evaluation"
    _build_fixture_database(db_path)
    _write_curated_manifest(curated_manifest_path, db_path)

    freeze_evaluation(
        database_path=db_path,
        curated_manifest_path=curated_manifest_path,
        output_root=output_root,
        repo_root=Path("."),
    )
    frozen_dir = output_root / "private" / "frozen" / SUITE_VERSION
    heldout_path = frozen_dir / "heldout_cases.jsonl"
    heldout_path.write_text(
        heldout_path.read_text(encoding="utf-8") + "{}\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        verify_frozen_evaluation(
            frozen_dir=frozen_dir,
            database_path=db_path,
            curated_manifest_path=curated_manifest_path,
        )


def test_freeze_rejects_database_manifest_mismatch(tmp_path: Path) -> None:
    db_path = tmp_path / "bank.duckdb"
    curated_manifest_path = tmp_path / "build_manifest.json"
    _build_fixture_database(db_path)
    _write_curated_manifest(curated_manifest_path, db_path)

    payload = json.loads(curated_manifest_path.read_text(encoding="utf-8"))
    payload["database_sha256"] = "0" * 64
    curated_manifest_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(FreezeError, match="does not match"):
        freeze_evaluation(
            database_path=db_path,
            curated_manifest_path=curated_manifest_path,
            output_root=tmp_path / "evaluation",
            repo_root=Path("."),
        )
