from __future__ import annotations

import csv
import json
from pathlib import Path

import duckdb
import pytest

from app.artifact_identity import identify_bank_artifact_mode
from scripts.build_full_challenge_data import (
    FULL_CURATED_BUILDER_VERSION,
    FULL_TABLE_COLUMNS,
    build_full_challenge_database,
)


def _write_csv(path: Path, fieldnames: tuple[str, ...], row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerow(row)


def _row(table: str) -> dict[str, str]:
    row = {column: f"{table}-{column}" for column in FULL_TABLE_COLUMNS[table]}

    if table == "customers":
        row.update(
            {
                "customer_id": "C001",
                "country": "Colombia",
                "detected_accent": "colombian",
                "customer_status": "Active",
                "email": "customer@example.test",
            }
        )
    elif table == "products":
        row.update(
            {
                "product_id": "P001",
                "customer_id": "C001",
                "product_type": "Checking Account",
                "currency": "COP",
                "current_balance": "1000.00",
                "opening_date": "2025-01-01",
                "expiration_date": "",
                "product_status": "Active",
                "last_transaction_date": "2026-09-25 10:00:00",
            }
        )
    elif table == "transactions":
        row.update(
            {
                "transaction_id": "T001",
                "transaction_date": "2026-09-25 10:00:00",
                "product_id": "P001",
                "customer_id": "C001",
                "transaction_type": "Payment",
                "transaction_category": "Retail",
                "amount": "125.00",
                "currency": "COP",
                "channel": "App",
                "merchant_name": "Merchant",
                "merchant_category": "Retail",
                "transaction_country": "Colombia",
                "transaction_city": "Bogota",
                "transaction_status": "Approved",
                "is_fraud": "false",
                "fraud_score": "1.00",
            }
        )
    elif "customer_id" in row:
        row["customer_id"] = "C001"

    if table == "call_center_interactions":
        row["interaction_id"] = "I001"
        row["agent_id"] = "A001"
    elif table == "call_transcripts":
        row.update(
            {
                "transcript_id": "TR001",
                "interaction_id": "I001",
                "agent_id": "A001",
                "full_text": "Customer asks about payment status.",
                "customer_text": "¿Cuál es el estado de mi pago?",
                "agent_text": "Voy a revisarlo.",
            }
        )
    elif table == "complaints":
        row.update(
            {
                "complaint_id": "CP001",
                "origin_interaction_id": "I001",
                "assigned_agent_id": "A001",
            }
        )
    elif table == "satisfaction_surveys":
        row.update(
            {
                "survey_id": "S001",
                "interaction_id": "I001",
                "agent_id": "A001",
            }
        )
    elif table == "service_agents":
        row["agent_id"] = "A001"
    elif table == "branches":
        row["branch_id"] = "B001"
    elif table == "marketing_campaigns":
        row["campaign_id"] = "M001"
    elif table == "campaign_sends":
        row.update({"send_id": "SEND001", "campaign_id": "M001"})
    elif table == "digital_events":
        row.update({"event_id": "E001", "session_id": "SESSION001"})
    elif table == "daily_exchange_rates":
        row.update(
            {
                "date": "2026-09-25",
                "source_currency": "USD",
                "target_currency": "COP",
            }
        )

    return row


def _full_source_fixture(root: Path) -> None:
    for table, columns in FULL_TABLE_COLUMNS.items():
        if table in {
            "call_center_interactions",
            "call_transcripts",
            "campaign_sends",
            "complaints",
            "digital_events",
            "satisfaction_surveys",
            "transactions",
        }:
            path = root / table / "part-0001.csv"
        else:
            path = root / f"{table}.csv"
        _write_csv(path, columns, _row(table))


def test_full_builder_preserves_all_source_tables_and_runtime_core(tmp_path: Path) -> None:
    raw = tmp_path / "organizer-data"
    raw.mkdir()
    _full_source_fixture(raw)

    output = tmp_path / "curated" / "bank.duckdb"
    manifest_path = tmp_path / "curated" / "build_manifest.json"

    manifest = build_full_challenge_database(
        data_root=raw,
        output=output,
        manifest_path=manifest_path,
        threads=1,
        memory_limit="1GB",
    )

    assert manifest["builder_version"] == FULL_CURATED_BUILDER_VERSION
    assert manifest["source_table_count"] == len(FULL_TABLE_COLUMNS)
    assert set(manifest["source_tables"]) == set(FULL_TABLE_COLUMNS)
    assert all(
        info["row_count"] == 1
        for info in manifest["source_tables"].values()
    )
    assert manifest["canonical_row_counts"] == {
        "customers": 1,
        "products": 1,
        "transactions": 1,
    }
    assert all(value == 0 for value in manifest["quality_checks"].values())
    assert identify_bank_artifact_mode(output) == "curated"

    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert persisted["database_sha256"] == manifest["database_sha256"]

    con = duckdb.connect(str(output), read_only=True)
    try:
        transcript = con.execute(
            """
            SELECT customer_text
            FROM call_transcripts
            WHERE customer_id = 'C001'
            """
        ).fetchone()
        assert transcript == ("¿Cuál es el estado de mi pago?",)

        raw_customer_columns = {
            row[1]
            for row in con.execute(
                "PRAGMA table_info('challenge_customers')"
            ).fetchall()
        }
        canonical_customer_columns = {
            row[1]
            for row in con.execute("PRAGMA table_info('customers')").fetchall()
        }
        assert "email" in raw_customer_columns
        assert "document_number" in raw_customer_columns
        assert "email" not in canonical_customer_columns
        assert "document_number" not in canonical_customer_columns
    finally:
        con.close()


def test_full_builder_requires_every_challenge_table(tmp_path: Path) -> None:
    raw = tmp_path / "organizer-data"
    raw.mkdir()
    _full_source_fixture(raw)
    (raw / "call_transcripts" / "part-0001.csv").unlink()

    with pytest.raises(FileNotFoundError, match="call_transcripts"):
        build_full_challenge_database(
            data_root=raw,
            output=tmp_path / "curated" / "bank.duckdb",
            manifest_path=tmp_path / "curated" / "build_manifest.json",
            threads=1,
            memory_limit="1GB",
        )
