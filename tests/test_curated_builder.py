from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from scripts.build_curated_bank import build_curated_database


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _source_fixture(root: Path, *, mismatch: bool = False) -> None:
    _write_csv(
        root / "customers.csv",
        [
            "customer_id",
            "country",
            "detected_accent",
            "customer_status",
            "first_name",
            "email",
            "document_number",
        ],
        [
            {
                "customer_id": "C001",
                "country": "Colombia",
                "detected_accent": "colombian",
                "customer_status": "Active",
                "first_name": "Example",
                "email": "not-curated@example.test",
                "document_number": "NOT-CURATED",
            },
            {
                "customer_id": "C002",
                "country": "Argentina",
                "detected_accent": "argentine",
                "customer_status": "Active",
                "first_name": "Example2",
                "email": "also-not-curated@example.test",
                "document_number": "NOT-CURATED-2",
            },
        ],
    )
    _write_csv(
        root / "products.csv",
        [
            "product_id",
            "customer_id",
            "product_type",
            "product_number",
            "currency",
            "current_balance",
            "opening_date",
            "expiration_date",
            "product_status",
            "last_transaction_date",
        ],
        [
            {
                "product_id": "P001",
                "customer_id": "C001",
                "product_type": "Savings Account",
                "product_number": "NOT-CURATED-ACCOUNT",
                "currency": "COP",
                "current_balance": "250000.00",
                "opening_date": "2025-01-01",
                "expiration_date": "",
                "product_status": "Active",
                "last_transaction_date": "2026-06-17 10:00:00",
            }
        ],
    )
    _write_csv(
        root / "transactions.csv",
        [
            "transaction_id",
            "transaction_date",
            "product_id",
            "customer_id",
            "transaction_type",
            "transaction_category",
            "amount",
            "currency",
            "channel",
            "branch_id",
            "merchant_name",
            "merchant_category",
            "transaction_country",
            "transaction_city",
            "transaction_status",
            "response_code",
            "is_fraud",
            "fraud_score",
            "latitude",
            "longitude",
        ],
        [
            {
                "transaction_id": "T001",
                "transaction_date": "2026-06-17 10:00:00",
                "product_id": "P001",
                "customer_id": "C002" if mismatch else "C001",
                "transaction_type": "Payment",
                "transaction_category": "Services",
                "amount": "12500.00",
                "currency": "COP",
                "channel": "App",
                "branch_id": "",
                "merchant_name": "Demo Merchant",
                "merchant_category": "Services",
                "transaction_country": "Colombia",
                "transaction_city": "Bogota",
                "transaction_status": "Approved",
                "response_code": "00",
                "is_fraud": "false",
                "fraud_score": "3.50",
                "latitude": "4.0",
                "longitude": "-74.0",
            }
        ],
    )


def test_builder_creates_minimized_verified_artifact(tmp_path: Path) -> None:
    raw = tmp_path / "organizer-data"
    raw.mkdir()
    _source_fixture(raw)

    output = tmp_path / "curated" / "bank.duckdb"
    manifest_path = tmp_path / "curated" / "build_manifest.json"

    manifest = build_curated_database(
        data_root=raw,
        output=output,
        manifest_path=manifest_path,
        threads=1,
        memory_limit="1GB",
    )

    assert output.exists()
    assert manifest["row_counts"] == {
        "customers": 2,
        "products": 1,
        "transactions": 1,
    }
    assert all(value == 0 for value in manifest["quality_checks"].values())

    expected_sha = hashlib.sha256(output.read_bytes()).hexdigest()
    persisted_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert persisted_manifest["database_sha256"] == expected_sha

    con = duckdb.connect(str(output), read_only=True)
    try:
        customer_columns = {
            row[1] for row in con.execute("PRAGMA table_info('customers')").fetchall()
        }
        product_columns = {
            row[1] for row in con.execute("PRAGMA table_info('products')").fetchall()
        }
        transaction_columns = {
            row[1]
            for row in con.execute("PRAGMA table_info('transactions')").fetchall()
        }

        assert "email" not in customer_columns
        assert "first_name" not in customer_columns
        assert "document_number" not in customer_columns
        assert "product_number" not in product_columns
        assert "latitude" not in transaction_columns
        assert "longitude" not in transaction_columns
        assert "branch_id" not in transaction_columns
        assert "response_code" not in transaction_columns
    finally:
        con.close()


def test_builder_rejects_transaction_product_customer_mismatch(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "organizer-data"
    raw.mkdir()
    _source_fixture(raw, mismatch=True)

    with pytest.raises(
        ValueError,
        match="transaction_product_customer_mismatches=1",
    ):
        build_curated_database(
            data_root=raw,
            output=tmp_path / "curated" / "bank.duckdb",
            manifest_path=tmp_path / "curated" / "build_manifest.json",
            threads=1,
            memory_limit="1GB",
        )


def test_builder_refuses_to_write_inside_raw_data_root(tmp_path: Path) -> None:
    raw = tmp_path / "organizer-data"
    raw.mkdir()
    _source_fixture(raw)

    with pytest.raises(ValueError, match="inside the organizer data root"):
        build_curated_database(
            data_root=raw,
            output=raw / "bank.duckdb",
            manifest_path=tmp_path / "build_manifest.json",
            threads=1,
            memory_limit="1GB",
        )
