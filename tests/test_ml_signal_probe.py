from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb

from ml.signal_probe import (
    FULL_FEATURE_MIN_POSITIVES,
    PROBE_VERSION,
    derive_splits,
    run_probe,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _build_fixture(path: Path, *, late_labels_flipped: bool = False) -> None:
    con = duckdb.connect(str(path))
    try:
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
        channels = ["App", "Web", "POS"]
        categories = ["Retail", "Travel", "Food"]
        total_rows = 3000
        for index in range(total_rows):
            customer_number = index // 5
            tx_index = index % 5
            customer_id = f"C{customer_number:04d}"
            product_id = f"P{customer_number:04d}"
            country, currency = countries[customer_number % len(countries)]
            if tx_index == 0:
                con.execute(
                    """
                    INSERT INTO products VALUES (
                        ?, ?, 'Checking', ?, 1000.00, DATE '2025-01-01',
                        NULL, 'Active', NULL
                    )
                    """,
                    [product_id, customer_id, currency],
                )

            day_offset = index // 24
            hour = index % 24
            # Training-region fraud signal: larger amount + channel pattern.
            fraud = (
                index % 7 == 0
                or (channels[index % 3] == "Web" and index % 11 == 0)
            )
            if index >= 2100 and late_labels_flipped:
                fraud = not fraud

            amount = 1000 + (index % 100) * 25 if fraud else 10 + (index % 50)
            fraud_score = Decimal("90.00") if fraud else Decimal("10.00")
            con.execute(
                """
                INSERT INTO transactions VALUES (
                    ?,
                    TIMESTAMP '2023-01-01 00:00:00'
                        + (? * INTERVAL '1 day')
                        + (? * INTERVAL '1 hour'),
                    ?, ?, 'Purchase', 'Card Purchase', ?, ?, ?,
                    'Fixture Merchant', ?, ?, 'Fixture City', 'Approved', ?, ?
                )
                """,
                [
                    f"T{index:05d}",
                    day_offset,
                    hour,
                    product_id,
                    customer_id,
                    amount,
                    currency,
                    channels[index % len(channels)],
                    categories[index % len(categories)],
                    country,
                    fraud,
                    fraud_score,
                ],
            )
    finally:
        con.close()


def _write_manifest(path: Path, db_path: Path) -> None:
    payload = {
        "builder_version": "fixture",
        "curated_schema_version": 1,
        "database_sha256": _sha256(db_path),
        "row_counts": {
            "customers": 600,
            "products": 600,
            "transactions": 3000,
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_split_keeps_timestamp_groups_inside_training_region(tmp_path: Path) -> None:
    db_path = tmp_path / "bank.duckdb"
    _build_fixture(db_path)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        split = derive_splits(con)
        at_cutoff = con.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE transaction_date = CAST(? AS TIMESTAMP)
            """,
            [split.training_cutoff],
        ).fetchone()[0]
        before_cutoff = con.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE transaction_date < CAST(? AS TIMESTAMP)
            """,
            [split.training_cutoff],
        ).fetchone()[0]
    finally:
        con.close()

    assert split.total_rows == 3000
    assert split.training_rows == before_cutoff + at_cutoff
    assert split.training_rows >= 2100
    assert split.internal_train_rows < split.training_rows


def test_probe_is_training_only_and_ignores_late_labels(tmp_path: Path) -> None:
    first_db = tmp_path / "first.duckdb"
    second_db = tmp_path / "second.duckdb"
    first_manifest = tmp_path / "first_manifest.json"
    second_manifest = tmp_path / "second_manifest.json"

    _build_fixture(first_db, late_labels_flipped=False)
    _build_fixture(second_db, late_labels_flipped=True)
    _write_manifest(first_manifest, first_db)
    _write_manifest(second_manifest, second_db)

    first = run_probe(
        database_path=first_db,
        curated_manifest_path=first_manifest,
        output_path=tmp_path / "first_probe.json",
    )
    second = run_probe(
        database_path=second_db,
        curated_manifest_path=second_manifest,
        output_path=tmp_path / "second_probe.json",
    )

    assert first["probe_version"] == PROBE_VERSION
    assert first["split"] == second["split"]
    assert first["training_profile"] == second["training_profile"]
    assert first["profiles"] == second["profiles"]
    assert first["quick_intrinsic_gbdt"] == second["quick_intrinsic_gbdt"]


def test_probe_never_uses_fraud_score_value_as_predictor(tmp_path: Path) -> None:
    db_path = tmp_path / "bank.duckdb"
    manifest_path = tmp_path / "manifest.json"
    _build_fixture(db_path)
    _write_manifest(manifest_path, db_path)

    first = run_probe(
        database_path=db_path,
        curated_manifest_path=manifest_path,
        output_path=tmp_path / "first.json",
    )

    con = duckdb.connect(str(db_path))
    try:
        con.execute("UPDATE transactions SET fraud_score = 42.42")
    finally:
        con.close()
    _write_manifest(manifest_path, db_path)

    second = run_probe(
        database_path=db_path,
        curated_manifest_path=manifest_path,
        output_path=tmp_path / "second.json",
    )

    # Coverage/missingness is unchanged, and fraud_score values never enter predictors.
    assert first["training_profile"] == second["training_profile"]
    assert first["profiles"] == second["profiles"]
    assert first["quick_intrinsic_gbdt"] == second["quick_intrinsic_gbdt"]
    assert "fraud_score" in second["predictor_contract"]["explicitly_not_used"]


def test_probe_reports_pre_registered_breadth_rule(tmp_path: Path) -> None:
    db_path = tmp_path / "bank.duckdb"
    manifest_path = tmp_path / "manifest.json"
    _build_fixture(db_path)
    _write_manifest(manifest_path, db_path)

    result = run_probe(
        database_path=db_path,
        curated_manifest_path=manifest_path,
        output_path=tmp_path / "probe.json",
    )
    model = result["quick_intrinsic_gbdt"]

    assert model["holdout_positive_rows"] > 0
    assert model["pr_auc"] >= model["holdout_prevalence"]
    assert model["breadth_decision"] in {"full", "reduced"}
    assert (
        model["breadth_rule"]["minimum_holdout_positive_rows"]
        == FULL_FEATURE_MIN_POSITIVES
    )
    assert result["predictor_contract"]["target_only"] == "is_fraud"
