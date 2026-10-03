#!/usr/bin/env python3
"""Build a full, read-only Factored challenge-data DuckDB artifact.

The organizer dataset remains read-only. This builder preserves every source
column from all provided challenge tables in server-side DuckDB tables while
also materializing the existing minimized canonical banking tables used by the
Proof of One runtime.

The LLM is not granted database access by this artifact. Runtime access remains
through backend repositories and policy controls.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from scripts.build_curated_bank import (
    CREATE_SELECTS,
    CURATED_SCHEMA_VERSION,
    _read_csv_expression,
    _run_quality_checks,
    _sha256_file,
    _sql_literal,
    _write_json_atomic,
    discover_table_source,
)


FULL_CURATED_BUILDER_VERSION = "r3b-full-1"

FULL_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "branches": (
        "branch_id", "branch_code", "branch_name", "branch_type", "address",
        "city", "state", "country", "postal_code", "geographic_zone", "phone",
        "email", "opening_time", "closing_time", "has_atms", "atm_count",
        "has_teller_windows", "teller_window_count", "latitude", "longitude",
        "branch_opening_date", "branch_status",
    ),
    "call_center_interactions": (
        "interaction_id", "interaction_date", "process_date", "customer_id",
        "agent_id", "interaction_type", "channel", "contact_reason",
        "reason_category", "duration_seconds", "wait_time_seconds", "was_resolved",
        "requires_followup", "detected_sentiment", "sentiment_score",
        "customer_detected_accent", "agent_used_accent", "was_escalated",
        "mentioned_products", "has_transcript", "has_recording",
    ),
    "call_transcripts": (
        "transcript_id", "interaction_id", "process_date", "customer_id",
        "agent_id", "full_text", "customer_text", "agent_text",
        "detected_language", "detected_accent", "accent_confidence",
        "detected_keywords", "mentioned_entities", "detected_intents",
        "main_topics", "transcription_model", "audio_quality", "duration_seconds",
    ),
    "campaign_sends": (
        "send_id", "send_date", "process_date", "campaign_id", "customer_id",
        "send_channel", "template_used", "subject", "send_status", "was_delivered",
        "was_opened", "open_date", "was_clicked", "click_date", "click_count",
        "had_conversion", "conversion_date", "conversion_value", "open_device",
        "open_country", "failure_reason", "send_cost",
    ),
    "complaints": (
        "complaint_id", "creation_date", "process_date", "customer_id",
        "case_type", "category", "subcategory", "reception_channel",
        "affected_product_id", "related_branch_id", "origin_interaction_id",
        "description", "claimed_amount", "currency", "priority", "status",
        "assigned_agent_id", "assignment_date", "first_response_date",
        "resolution_date", "closing_date", "sla_breached", "resolution_days",
        "resolution", "compensation_granted", "resolution_satisfaction",
        "is_repeat_complainer",
    ),
    "customers": (
        "customer_id", "document_number", "document_type", "first_name",
        "last_name", "date_of_birth", "gender", "email", "mobile_phone",
        "landline_phone", "address", "city", "state", "country", "postal_code",
        "detected_accent", "segment", "credit_score", "estimated_monthly_income",
        "occupation", "marital_status", "education_level", "registration_date",
        "registration_branch_id", "customer_status", "last_updated",
        "accepts_marketing",
    ),
    "daily_exchange_rates": (
        "date", "source_currency", "target_currency", "exchange_rate",
        "buy_rate", "sell_rate", "source",
    ),
    "digital_events": (
        "event_id", "event_date", "process_date", "customer_id", "session_id",
        "event_type", "event_category", "channel", "platform", "browser",
        "app_version", "page_url", "page_title", "action", "element_id",
        "product_id", "event_value", "duration_seconds", "ip_address",
        "ip_country", "ip_city", "is_mobile", "referrer", "utm_source",
        "utm_medium", "utm_campaign",
    ),
    "marketing_campaigns": (
        "campaign_id", "campaign_name", "description", "campaign_type",
        "campaign_objective", "promoted_product", "target_segment",
        "target_country", "start_date", "end_date", "budget", "campaign_status",
        "expected_conversion_rate",
    ),
    "products": (
        "product_id", "customer_id", "product_type", "product_number", "currency",
        "current_balance", "credit_limit", "interest_rate", "opening_date",
        "expiration_date", "opening_branch_id", "product_status",
        "opening_channel", "has_linked_app", "days_past_due",
        "last_transaction_date", "last_updated",
    ),
    "satisfaction_surveys": (
        "survey_id", "survey_date", "process_date", "interaction_id",
        "customer_id", "agent_id", "survey_type", "send_channel", "main_score",
        "nps_category", "question_1_text", "question_1_response",
        "question_2_text", "question_2_response", "question_3_text",
        "question_3_response", "open_comments", "comment_sentiment",
        "response_time_hours", "campaign_response_rate",
    ),
    "service_agents": (
        "agent_id", "employee_code", "first_name", "last_name", "email", "phone",
        "native_accent", "country_of_origin", "assigned_branch_id", "agent_type",
        "experience_level", "languages", "specialty", "hire_date", "avg_csat",
        "total_monthly_interactions", "agent_status", "work_shift",
    ),
    "transactions": (
        "transaction_id", "transaction_date", "process_date", "product_id",
        "customer_id", "transaction_type", "transaction_category", "amount",
        "currency", "amount_usd", "channel", "branch_id", "merchant_name",
        "merchant_category", "transaction_country", "transaction_city",
        "transaction_status", "response_code", "is_fraud", "fraud_score",
        "latitude", "longitude",
    ),
}

SOURCE_TABLES = tuple(FULL_TABLE_COLUMNS)
CORE_TABLES = ("customers", "products", "transactions")
RAW_CORE_TABLES = {
    "customers": "challenge_customers",
    "products": "challenge_products",
    "transactions": "challenge_transactions",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, help="Read-only organizer data root.")
    parser.add_argument(
        "--output",
        default="data/curated/bank.duckdb",
        help="Full challenge DuckDB output path.",
    )
    parser.add_argument(
        "--manifest",
        default="data/curated/build_manifest.json",
        help="Build-manifest output path.",
    )
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--memory-limit", default="8GB")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing full challenge artifact.",
    )
    return parser.parse_args()


def _source_columns(
    con: duckdb.DuckDBPyConnection,
    source,
) -> tuple[str, ...]:
    rows = con.execute(
        f"DESCRIBE SELECT * FROM {_read_csv_expression(source.files)}"
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _validate_source_columns(
    con: duckdb.DuckDBPyConnection,
    source,
) -> tuple[str, ...]:
    columns = _source_columns(con, source)
    available = set(columns)
    missing = sorted(set(FULL_TABLE_COLUMNS[source.name]) - available)
    if missing:
        raise ValueError(
            f"{source.name} is missing required columns: {', '.join(missing)}"
        )
    return columns


def _create_preserved_table(
    con: duckdb.DuckDBPyConnection,
    *,
    source,
    table_name: str,
) -> None:
    con.execute(
        f"""
        CREATE TABLE {table_name} AS
        SELECT *
        FROM {_read_csv_expression(source.files)}
        """
    )


def _create_canonical_core_tables(con: duckdb.DuckDBPyConnection) -> None:
    for table in CORE_TABLES:
        source_table = RAW_CORE_TABLES[table]
        select_sql = ",\n            ".join(CREATE_SELECTS[table])
        con.execute(
            f"""
            CREATE TABLE {table} AS
            SELECT
                {select_sql}
            FROM {source_table}
            """
        )


def _create_indexes(con: duckdb.DuckDBPyConnection) -> None:
    statements = (
        "CREATE UNIQUE INDEX idx_customers_customer_id ON customers(customer_id)",
        "CREATE UNIQUE INDEX idx_products_product_id ON products(product_id)",
        "CREATE INDEX idx_products_customer_id ON products(customer_id)",
        "CREATE UNIQUE INDEX idx_transactions_transaction_id ON transactions(transaction_id)",
        "CREATE INDEX idx_transactions_customer_id ON transactions(customer_id)",
        "CREATE INDEX idx_transactions_product_id ON transactions(product_id)",
        "CREATE INDEX idx_transactions_customer_date ON transactions(customer_id, transaction_date)",
        "CREATE INDEX idx_cc_interactions_customer ON call_center_interactions(customer_id)",
        "CREATE INDEX idx_cc_interactions_interaction ON call_center_interactions(interaction_id)",
        "CREATE INDEX idx_transcripts_customer ON call_transcripts(customer_id)",
        "CREATE INDEX idx_transcripts_interaction ON call_transcripts(interaction_id)",
        "CREATE INDEX idx_complaints_customer ON complaints(customer_id)",
        "CREATE INDEX idx_complaints_interaction ON complaints(origin_interaction_id)",
        "CREATE INDEX idx_campaign_sends_customer ON campaign_sends(customer_id)",
        "CREATE INDEX idx_surveys_customer ON satisfaction_surveys(customer_id)",
        "CREATE INDEX idx_surveys_interaction ON satisfaction_surveys(interaction_id)",
        "CREATE INDEX idx_digital_events_customer ON digital_events(customer_id)",
        "CREATE INDEX idx_digital_events_session ON digital_events(session_id)",
        "CREATE UNIQUE INDEX idx_branches_branch ON branches(branch_id)",
        "CREATE UNIQUE INDEX idx_campaigns_campaign ON marketing_campaigns(campaign_id)",
        "CREATE UNIQUE INDEX idx_agents_agent ON service_agents(agent_id)",
        "CREATE INDEX idx_fx_pair_date ON daily_exchange_rates(source_currency, target_currency, date)",
    )
    for statement in statements:
        con.execute(statement)


def _count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    row = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    assert row is not None
    return int(row[0])


def build_full_challenge_database(
    *,
    data_root: Path,
    output: Path,
    manifest_path: Path,
    threads: int = 4,
    memory_limit: str = "8GB",
    overwrite: bool = False,
) -> dict[str, object]:
    started = time.perf_counter()
    data_root = data_root.expanduser().resolve()
    output = output.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()

    if not data_root.is_dir():
        raise FileNotFoundError(f"Organizer data root does not exist: {data_root}")
    if output.is_relative_to(data_root) or manifest_path.is_relative_to(data_root):
        raise ValueError(
            "Refusing to write curated outputs inside the organizer data root."
        )
    if threads < 1:
        raise ValueError("threads must be at least 1")
    if output.exists() and not overwrite:
        raise FileExistsError(
            f"Full challenge database already exists: {output}. "
            "Use --overwrite to replace it."
        )

    sources = {
        table: discover_table_source(data_root, table)
        for table in SOURCE_TABLES
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_db = output.with_name(output.name + ".building")
    for stale in (temporary_db, Path(str(temporary_db) + ".wal")):
        if stale.exists():
            stale.unlink()

    con: duckdb.DuckDBPyConnection | None = None
    try:
        con = duckdb.connect(str(temporary_db))
        con.execute(f"SET threads = {threads}")
        con.execute(f"SET memory_limit = {_sql_literal(memory_limit)}")
        con.execute("SET preserve_insertion_order = false")

        source_columns: dict[str, tuple[str, ...]] = {}
        for table, source in sources.items():
            source_columns[table] = _validate_source_columns(con, source)
            target_table = RAW_CORE_TABLES.get(table, table)
            _create_preserved_table(
                con,
                source=source,
                table_name=target_table,
            )

        _create_canonical_core_tables(con)
        quality_checks = _run_quality_checks(con)

        source_row_counts = {
            table: _count(con, RAW_CORE_TABLES.get(table, table))
            for table in SOURCE_TABLES
        }
        canonical_row_counts = {
            table: _count(con, table)
            for table in CORE_TABLES
        }
        for table in CORE_TABLES:
            if source_row_counts[table] != canonical_row_counts[table]:
                raise ValueError(
                    f"Full challenge row preservation failed for {table}: "
                    f"source={source_row_counts[table]}, "
                    f"canonical={canonical_row_counts[table]}"
                )

        _create_indexes(con)

        con.execute(
            """
            CREATE TABLE build_metadata (
                schema_version INTEGER NOT NULL,
                builder_version VARCHAR NOT NULL
            )
            """
        )
        con.execute(
            "INSERT INTO build_metadata VALUES (?, ?)",
            [CURATED_SCHEMA_VERSION, FULL_CURATED_BUILDER_VERSION],
        )
        con.execute("CHECKPOINT")
        con.close()
        con = None

        if output.exists():
            output.unlink()
        os.replace(temporary_db, output)

        manifest: dict[str, object] = {
            "builder_version": FULL_CURATED_BUILDER_VERSION,
            "curated_schema_version": CURATED_SCHEMA_VERSION,
            "built_utc": datetime.now(timezone.utc).isoformat(),
            "source_root_name": data_root.name,
            "source_table_count": len(SOURCE_TABLES),
            "source_total_files": sum(len(source.files) for source in sources.values()),
            "source_total_bytes": sum(source.total_bytes for source in sources.values()),
            "source_tables": {
                table: {
                    "file_count": len(source.files),
                    "total_bytes": source.total_bytes,
                    "inventory_sha256": source.inventory_sha256,
                    "columns": list(source_columns[table]),
                    "row_count": source_row_counts[table],
                    "preserved_table": RAW_CORE_TABLES.get(table, table),
                }
                for table, source in sources.items()
            },
            "canonical_row_counts": canonical_row_counts,
            "quality_checks": quality_checks,
            "database_size_bytes": output.stat().st_size,
            "database_sha256": _sha256_file(output),
            "build_seconds": round(time.perf_counter() - started, 3),
        }
        _write_json_atomic(manifest_path, manifest)
        return manifest
    except Exception:
        if con is not None:
            con.close()
        for stale in (temporary_db, Path(str(temporary_db) + ".wal")):
            if stale.exists():
                stale.unlink()
        raise


def main() -> int:
    args = parse_args()
    manifest = build_full_challenge_database(
        data_root=Path(args.data_root),
        output=Path(args.output),
        manifest_path=Path(args.manifest),
        threads=args.threads,
        memory_limit=args.memory_limit,
        overwrite=args.overwrite,
    )

    print("FULL CHALLENGE DATA BUILD COMPLETE")
    print(f"Source tables: {manifest['source_table_count']}")
    print(f"Source files:  {manifest['source_total_files']:,}")
    print(f"Source bytes:  {manifest['source_total_bytes']:,}")
    print(f"Customers:     {manifest['canonical_row_counts']['customers']:,}")
    print(f"Products:      {manifest['canonical_row_counts']['products']:,}")
    print(f"Transactions:  {manifest['canonical_row_counts']['transactions']:,}")
    print(f"Database:      {Path(args.output).resolve()}")
    print(f"Manifest:      {Path(args.manifest).resolve()}")
    print(f"SHA-256:       {manifest['database_sha256']}")
    print(f"Build time:    {manifest['build_seconds']} seconds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
