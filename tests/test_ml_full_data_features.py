from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import duckdb
import pytest

from ml.build_full_features import (
    FeatureArtifactError,
    build_feature_artifact,
    verify_feature_artifact,
)
from ml.full_data_contract import MODEL_FEATURE_NAMES, feature_contract_sha256


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _init_git_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Fixture"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def _build_curated_fixture(
    path: Path,
    *,
    flip_labels: bool = False,
    fraud_score_value: float = 50.0,
) -> dict[str, int]:
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
        con.execute("INSERT INTO build_metadata VALUES (1, 'fixture-builder')")

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
        total_transactions = 0

        for customer_index in range(40):
            customer_id = f"C{customer_index:03d}"
            product_id = f"P{customer_index:03d}"
            country, currency = countries[customer_index % len(countries)]
            con.execute(
                "INSERT INTO customers VALUES (?, ?, NULL, 'Active')",
                [customer_id, country],
            )
            con.execute(
                """
                INSERT INTO products VALUES (
                    ?, ?, 'Checking', ?, 1000.00, DATE '2024-01-01',
                    NULL, 'Active', NULL
                )
                """,
                [product_id, customer_id, currency],
            )

            for tx_index in range(5):
                day_offset = customer_index * 2 + tx_index
                timestamp_expr = (
                    "TIMESTAMP '2025-01-01 00:00:00' + (? * INTERVAL '1 day')"
                )
                transaction_id = f"T-{customer_index:03d}-{tx_index}"
                is_fraud = ((customer_index + tx_index) % 17 == 0)
                if flip_labels:
                    is_fraud = not is_fraud
                con.execute(
                    f"""
                    INSERT INTO transactions VALUES (
                        ?, {timestamp_expr}, ?, ?, 'Purchase', 'Retail',
                        ?, ?, ?, 'Fixture Merchant', ?, ?, 'Fixture City',
                        'Approved', ?, ?
                    )
                    """,
                    [
                        transaction_id,
                        day_offset,
                        product_id,
                        customer_id,
                        10.0 + customer_index + tx_index,
                        currency,
                        "App" if tx_index % 2 == 0 else "Web",
                        "Food" if tx_index % 3 else "Services",
                        country,
                        is_fraud,
                        fraud_score_value,
                    ],
                )
                total_transactions += 1

        # Replace C000 history with explicit edge cases and same-timestamp peers.
        con.execute("DELETE FROM transactions WHERE customer_id = 'C000'")
        explicit = [
            ("T-000-A", "2025-01-01 00:00:00", 10.0, "App", "Food"),
            ("T-000-B", "2025-01-01 00:00:00", 20.0, "App", "Food"),
            ("T-000-C", "2025-01-02 00:00:00", 30.0, "Web", "Food"),
            ("T-000-D", "2025-02-05 00:00:00", 40.0, "App", None),
            ("T-000-E", "2025-02-06 00:00:00", 50.0, "App", "Food"),
        ]
        total_transactions -= 5
        for index, (txid, timestamp, amount, channel, merchant_category) in enumerate(explicit):
            is_fraud = index == 4
            if flip_labels:
                is_fraud = not is_fraud
            con.execute(
                """
                INSERT INTO transactions VALUES (
                    ?, CAST(? AS TIMESTAMP), 'P000', 'C000',
                    'Purchase', 'Retail', ?, 'COP', ?,
                    'Fixture Merchant', ?, 'Colombia', 'Fixture City',
                    'Approved', ?, ?
                )
                """,
                [
                    txid,
                    timestamp,
                    amount,
                    channel,
                    merchant_category,
                    is_fraud,
                    fraud_score_value,
                ],
            )
            total_transactions += 1

        return {
            "customers": 40,
            "products": 40,
            "transactions": total_transactions,
        }
    finally:
        con.close()


def _write_manifest(path: Path, db_path: Path, counts: dict[str, int]) -> None:
    payload = {
        "builder_version": "fixture-builder",
        "curated_schema_version": 1,
        "database_sha256": _sha256(db_path),
        "row_counts": counts,
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _build(
    tmp_path: Path,
    name: str,
    *,
    flip_labels: bool = False,
    fraud_score_value: float = 50.0,
):
    db = tmp_path / f"{name}.duckdb"
    curated_manifest = tmp_path / f"{name}_curated.json"
    counts = _build_curated_fixture(
        db,
        flip_labels=flip_labels,
        fraud_score_value=fraud_score_value,
    )
    _write_manifest(curated_manifest, db, counts)
    repo_root = tmp_path / "repo"
    if not repo_root.exists():
        repo_root = _init_git_repo(tmp_path)

    feature_db = tmp_path / f"{name}_analytics.duckdb"
    feature_manifest = tmp_path / f"{name}_analytics.json"
    source_sha_before = _sha256(db)
    manifest = build_feature_artifact(
        database_path=db,
        curated_manifest_path=curated_manifest,
        output_database_path=feature_db,
        output_manifest_path=feature_manifest,
        repo_root=repo_root,
    )
    assert _sha256(db) == source_sha_before
    return db, curated_manifest, feature_db, feature_manifest, manifest


def test_builder_preserves_strict_history_and_same_timestamp_peer_exclusion(
    tmp_path: Path,
) -> None:
    _, curated_manifest, feature_db, feature_manifest, manifest = _build(
        tmp_path,
        "base",
    )

    assert manifest["contract_sha256"] == feature_contract_sha256()
    assert manifest["source_transaction_rows"] == 200
    assert manifest["model_feature_count"] == len(MODEL_FEATURE_NAMES)

    con = duckdb.connect(str(feature_db), read_only=True)
    try:
        rows = {
            row[0]: row[1:]
            for row in con.execute(
                """
                SELECT
                    transaction_id,
                    prior_tx_count_lifetime,
                    has_prior_transaction,
                    seconds_since_previous_tx,
                    prior_24h_tx_count,
                    prior_24h_amount_sum,
                    prior_30d_tx_count,
                    prior_30d_amount_sum,
                    prior_channel_count_lifetime,
                    channel_novelty,
                    prior_merchant_category_count_lifetime,
                    merchant_category_novelty
                FROM feature_rows
                WHERE customer_id = 'C000'
                ORDER BY transaction_date, transaction_id
                """
            ).fetchall()
        }
    finally:
        con.close()

    assert rows["T-000-A"][0] == 0
    assert rows["T-000-B"][0] == 0
    assert rows["T-000-A"][1] is False
    assert rows["T-000-B"][1] is False
    assert rows["T-000-A"][2] is None
    assert rows["T-000-B"][2] is None

    # Jan 2 sees both Jan 1 peers, but neither Jan 1 peer saw the other.
    assert rows["T-000-C"][0] == 2
    assert rows["T-000-C"][2] == 86400.0
    assert rows["T-000-C"][3] == 2
    assert rows["T-000-C"][4] == 30.0
    assert rows["T-000-C"][8] == 0
    assert rows["T-000-C"][9] is True

    # Feb 5 is outside both the 24h and 30d window of the prior Jan 2 event.
    assert rows["T-000-D"][0] == 3
    assert rows["T-000-D"][3] == 0
    assert rows["T-000-D"][4] == 0.0
    assert rows["T-000-D"][5] == 0
    assert rows["T-000-D"][6] == 0.0
    assert rows["T-000-D"][10] == 0
    assert rows["T-000-D"][11] is False

    verified = verify_feature_artifact(
        database_path=tmp_path / "base.duckdb",
        curated_manifest_path=curated_manifest,
        feature_database_path=feature_db,
        feature_manifest_path=feature_manifest,
    )
    assert verified == manifest


def test_model_features_do_not_depend_on_target_or_reference_score(tmp_path: Path) -> None:
    _, _, first_db, _, _ = _build(
        tmp_path,
        "first",
        flip_labels=False,
        fraud_score_value=10.0,
    )
    _, _, second_db, _, _ = _build(
        tmp_path,
        "second",
        flip_labels=True,
        fraud_score_value=90.0,
    )

    first = duckdb.connect(str(first_db), read_only=True)
    second = duckdb.connect(str(second_db), read_only=True)
    try:
        quoted_features = ", ".join(f'"{name}"' for name in MODEL_FEATURE_NAMES)
        first_rows = first.execute(
            f"""
            SELECT transaction_id, {quoted_features}
            FROM feature_rows
            ORDER BY transaction_id
            """
        ).fetchall()
        second_rows = second.execute(
            f"""
            SELECT transaction_id, {quoted_features}
            FROM feature_rows
            ORDER BY transaction_id
            """
        ).fetchall()
        assert first_rows == second_rows

        first_targets = first.execute(
            """
            SELECT transaction_id, is_fraud, fraud_score_reference
            FROM feature_rows
            ORDER BY transaction_id
            """
        ).fetchall()
        second_targets = second.execute(
            """
            SELECT transaction_id, is_fraud, fraud_score_reference
            FROM feature_rows
            ORDER BY transaction_id
            """
        ).fetchall()
        assert first_targets != second_targets
    finally:
        first.close()
        second.close()


def test_builder_refuses_overwrite_and_verifier_detects_tamper(tmp_path: Path) -> None:
    db, curated_manifest, feature_db, feature_manifest, _ = _build(
        tmp_path,
        "base",
    )

    with pytest.raises(FeatureArtifactError, match="already exists"):
        build_feature_artifact(
            database_path=db,
            curated_manifest_path=curated_manifest,
            output_database_path=feature_db,
            output_manifest_path=feature_manifest,
            repo_root=tmp_path / "repo",
        )

    con = duckdb.connect(str(feature_db))
    try:
        con.execute(
            """
            UPDATE feature_rows
            SET prior_tx_count_lifetime = prior_tx_count_lifetime + 1
            WHERE transaction_id = (
                SELECT transaction_id FROM feature_rows LIMIT 1
            )
            """
        )
    finally:
        con.close()

    with pytest.raises(FeatureArtifactError, match="database SHA-256 mismatch"):
        verify_feature_artifact(
            database_path=db,
            curated_manifest_path=curated_manifest,
            feature_database_path=feature_db,
            feature_manifest_path=feature_manifest,
        )
