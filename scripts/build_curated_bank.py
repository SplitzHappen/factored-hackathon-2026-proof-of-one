#!/usr/bin/env python3
"""Build the minimal trusted banking store used by Proof of One.

The organizer dataset is treated as read-only. This script reads only the
customers, products, and transactions tables, selects the approved fields, runs
integrity checks, and atomically creates a curated DuckDB artifact plus a build
manifest.

No raw rows are written back to the organizer data root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import duckdb


BUILDER_VERSION = "r3b-1"
CURATED_SCHEMA_VERSION = 1

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "customers": (
        "customer_id",
        "country",
        "detected_accent",
        "customer_status",
    ),
    "products": (
        "product_id",
        "customer_id",
        "product_type",
        "currency",
        "current_balance",
        "opening_date",
        "expiration_date",
        "product_status",
        "last_transaction_date",
    ),
    "transactions": (
        "transaction_id",
        "transaction_date",
        "product_id",
        "customer_id",
        "transaction_type",
        "transaction_category",
        "amount",
        "currency",
        "channel",
        "merchant_name",
        "merchant_category",
        "transaction_country",
        "transaction_city",
        "transaction_status",
        "is_fraud",
        "fraud_score",
    ),
}

CREATE_SELECTS: dict[str, tuple[str, ...]] = {
    "customers": (
        "CAST(NULLIF(TRIM(customer_id), '') AS VARCHAR) AS customer_id",
        "CAST(NULLIF(TRIM(country), '') AS VARCHAR) AS country",
        "CAST(NULLIF(TRIM(detected_accent), '') AS VARCHAR) AS detected_accent",
        "CAST(NULLIF(TRIM(customer_status), '') AS VARCHAR) AS customer_status",
    ),
    "products": (
        "CAST(NULLIF(TRIM(product_id), '') AS VARCHAR) AS product_id",
        "CAST(NULLIF(TRIM(customer_id), '') AS VARCHAR) AS customer_id",
        "CAST(NULLIF(TRIM(product_type), '') AS VARCHAR) AS product_type",
        "CAST(NULLIF(TRIM(currency), '') AS VARCHAR) AS currency",
        "CAST(NULLIF(TRIM(current_balance), '') AS DECIMAL(15,2)) AS current_balance",
        "CAST(NULLIF(TRIM(opening_date), '') AS DATE) AS opening_date",
        "CAST(NULLIF(TRIM(expiration_date), '') AS DATE) AS expiration_date",
        "CAST(NULLIF(TRIM(product_status), '') AS VARCHAR) AS product_status",
        "CAST(NULLIF(TRIM(last_transaction_date), '') AS TIMESTAMP) AS last_transaction_date",
    ),
    "transactions": (
        "CAST(NULLIF(TRIM(transaction_id), '') AS VARCHAR) AS transaction_id",
        "CAST(NULLIF(TRIM(transaction_date), '') AS TIMESTAMP) AS transaction_date",
        "CAST(NULLIF(TRIM(product_id), '') AS VARCHAR) AS product_id",
        "CAST(NULLIF(TRIM(customer_id), '') AS VARCHAR) AS customer_id",
        "CAST(NULLIF(TRIM(transaction_type), '') AS VARCHAR) AS transaction_type",
        "CAST(NULLIF(TRIM(transaction_category), '') AS VARCHAR) AS transaction_category",
        "CAST(NULLIF(TRIM(amount), '') AS DECIMAL(15,2)) AS amount",
        "CAST(NULLIF(TRIM(currency), '') AS VARCHAR) AS currency",
        "CAST(NULLIF(TRIM(channel), '') AS VARCHAR) AS channel",
        "CAST(NULLIF(TRIM(merchant_name), '') AS VARCHAR) AS merchant_name",
        "CAST(NULLIF(TRIM(merchant_category), '') AS VARCHAR) AS merchant_category",
        "CAST(NULLIF(TRIM(transaction_country), '') AS VARCHAR) AS transaction_country",
        "CAST(NULLIF(TRIM(transaction_city), '') AS VARCHAR) AS transaction_city",
        "CAST(NULLIF(TRIM(transaction_status), '') AS VARCHAR) AS transaction_status",
        "CAST(NULLIF(TRIM(is_fraud), '') AS BOOLEAN) AS is_fraud",
        "CAST(NULLIF(TRIM(fraud_score), '') AS DECIMAL(5,2)) AS fraud_score",
    ),
}

REQUIRED_NON_NULL: dict[str, tuple[str, ...]] = {
    "customers": ("customer_id", "country", "customer_status"),
    "products": (
        "product_id",
        "customer_id",
        "product_type",
        "currency",
        "current_balance",
        "opening_date",
        "product_status",
    ),
    "transactions": (
        "transaction_id",
        "transaction_date",
        "product_id",
        "customer_id",
        "transaction_type",
        "amount",
        "currency",
        "channel",
        "transaction_country",
        "transaction_status",
        "is_fraud",
    ),
}


@dataclass(frozen=True, slots=True)
class TableSource:
    name: str
    files: tuple[Path, ...]
    total_bytes: int
    inventory_sha256: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, help="Read-only organizer data root.")
    parser.add_argument(
        "--output",
        default="data/curated/bank.duckdb",
        help="Curated DuckDB output path.",
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
        help="Replace an existing curated artifact.",
    )
    return parser.parse_args()


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_fingerprint(data_root: Path, files: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        relative = path.relative_to(data_root).as_posix()
        digest.update(f"{relative}|{path.stat().st_size}\n".encode("utf-8"))
    return digest.hexdigest()


def discover_table_source(data_root: Path, table: str) -> TableSource:
    files: list[Path] = []

    direct = data_root / f"{table}.csv"
    if direct.is_file():
        files.append(direct)

    folder = data_root / table
    if folder.is_dir():
        files.extend(path for path in folder.rglob("*.csv") if path.is_file())

    files = sorted(set(files))
    if not files:
        raise FileNotFoundError(
            f"No CSV files found for required table '{table}' beneath {data_root}"
        )

    return TableSource(
        name=table,
        files=tuple(files),
        total_bytes=sum(path.stat().st_size for path in files),
        inventory_sha256=_inventory_fingerprint(data_root, files),
    )


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _read_csv_expression(files: tuple[Path, ...]) -> str:
    file_list = ", ".join(
        _sql_literal(path.resolve().as_posix()) for path in files
    )
    return (
        f"read_csv([{file_list}], "
        "header=true, all_varchar=true, union_by_name=true, strict_mode=true)"
    )


def _validate_source_columns(
    con: duckdb.DuckDBPyConnection,
    source: TableSource,
) -> None:
    read_expr = _read_csv_expression(source.files)
    rows = con.execute(f"DESCRIBE SELECT * FROM {read_expr}").fetchall()
    available = {str(row[0]) for row in rows}
    missing = sorted(set(TABLE_COLUMNS[source.name]) - available)
    if missing:
        raise ValueError(
            f"{source.name} is missing required columns: {', '.join(missing)}"
        )


def _create_curated_table(
    con: duckdb.DuckDBPyConnection,
    source: TableSource,
) -> None:
    read_expr = _read_csv_expression(source.files)
    select_sql = ",\n            ".join(CREATE_SELECTS[source.name])
    con.execute(
        f"""
        CREATE TABLE {source.name} AS
        SELECT
            {select_sql}
        FROM {read_expr}
        """
    )


def _scalar(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    value = con.execute(sql).fetchone()
    assert value is not None
    return int(value[0])


def _run_quality_checks(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    checks: dict[str, int] = {}

    for table, columns in REQUIRED_NON_NULL.items():
        predicate = " OR ".join(f"{column} IS NULL" for column in columns)
        checks[f"{table}_required_null_rows"] = _scalar(
            con, f"SELECT COUNT(*) FROM {table} WHERE {predicate}"
        )

    checks["customers_duplicate_pk_rows"] = _scalar(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT customer_id)
        FROM customers
        """,
    )
    checks["products_duplicate_pk_rows"] = _scalar(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT product_id)
        FROM products
        """,
    )
    checks["transactions_duplicate_pk_rows"] = _scalar(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT transaction_id)
        FROM transactions
        """,
    )
    checks["product_customer_orphans"] = _scalar(
        con,
        """
        SELECT COUNT(*)
        FROM products p
        LEFT JOIN customers c USING (customer_id)
        WHERE c.customer_id IS NULL
        """,
    )
    checks["transaction_customer_orphans"] = _scalar(
        con,
        """
        SELECT COUNT(*)
        FROM transactions t
        LEFT JOIN customers c USING (customer_id)
        WHERE c.customer_id IS NULL
        """,
    )
    checks["transaction_product_orphans"] = _scalar(
        con,
        """
        SELECT COUNT(*)
        FROM transactions t
        LEFT JOIN products p USING (product_id)
        WHERE p.product_id IS NULL
        """,
    )
    checks["transaction_product_customer_mismatches"] = _scalar(
        con,
        """
        SELECT COUNT(*)
        FROM transactions t
        JOIN products p USING (product_id)
        WHERE t.customer_id <> p.customer_id
        """,
    )

    failures = {name: count for name, count in checks.items() if count != 0}
    if failures:
        formatted = ", ".join(f"{name}={count}" for name, count in failures.items())
        raise ValueError(f"Curated-data integrity checks failed: {formatted}")

    return checks


def _create_indexes(con: duckdb.DuckDBPyConnection) -> None:
    statements = (
        "CREATE UNIQUE INDEX idx_customers_customer_id ON customers(customer_id)",
        "CREATE UNIQUE INDEX idx_products_product_id ON products(product_id)",
        "CREATE INDEX idx_products_customer_id ON products(customer_id)",
        "CREATE UNIQUE INDEX idx_transactions_transaction_id ON transactions(transaction_id)",
        "CREATE INDEX idx_transactions_customer_id ON transactions(customer_id)",
        "CREATE INDEX idx_transactions_product_id ON transactions(product_id)",
        "CREATE INDEX idx_transactions_customer_date ON transactions(customer_id, transaction_date)",
    )
    for statement in statements:
        con.execute(statement)


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def build_curated_database(
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
            f"Curated database already exists: {output}. Use --overwrite to replace it."
        )

    sources = {
        table: discover_table_source(data_root, table)
        for table in ("customers", "products", "transactions")
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

        for source in sources.values():
            _validate_source_columns(con, source)
            _create_curated_table(con, source)

        quality_checks = _run_quality_checks(con)
        _create_indexes(con)

        row_counts = {
            table: _scalar(con, f"SELECT COUNT(*) FROM {table}")
            for table in sources
        }

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
            [CURATED_SCHEMA_VERSION, BUILDER_VERSION],
        )
        con.execute("CHECKPOINT")
        con.close()
        con = None

        if output.exists():
            output.unlink()
        os.replace(temporary_db, output)

        manifest: dict[str, object] = {
            "builder_version": BUILDER_VERSION,
            "curated_schema_version": CURATED_SCHEMA_VERSION,
            "built_utc": datetime.now(timezone.utc).isoformat(),
            "source_root_name": data_root.name,
            "source_tables": {
                table: {
                    "file_count": len(source.files),
                    "total_bytes": source.total_bytes,
                    "inventory_sha256": source.inventory_sha256,
                }
                for table, source in sources.items()
            },
            "curated_columns": {
                table: list(columns) for table, columns in TABLE_COLUMNS.items()
            },
            "row_counts": row_counts,
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
    manifest = build_curated_database(
        data_root=Path(args.data_root),
        output=Path(args.output),
        manifest_path=Path(args.manifest),
        threads=args.threads,
        memory_limit=args.memory_limit,
        overwrite=args.overwrite,
    )

    print("R3B CURATED DATA BUILD COMPLETE")
    print(f"Customers:    {manifest['row_counts']['customers']:,}")
    print(f"Products:     {manifest['row_counts']['products']:,}")
    print(f"Transactions: {manifest['row_counts']['transactions']:,}")
    print(f"Database:     {Path(args.output).resolve()}")
    print(f"Manifest:     {Path(args.manifest).resolve()}")
    print(f"SHA-256:      {manifest['database_sha256']}")
    print(f"Build time:   {manifest['build_seconds']} seconds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
