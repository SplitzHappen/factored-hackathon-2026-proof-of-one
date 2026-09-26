from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import duckdb

from ml.full_data_contract import (
    CONTRACT_VERSION,
    MODEL_FEATURES,
    MODEL_FEATURE_NAMES,
    OfficialSplitPlan,
    derive_official_split_plan,
    feature_contract_sha256,
)


ARTIFACT_VERSION = "factored-r4b-feature-artifact-v1"


class FeatureArtifactError(RuntimeError):
    """Raised when the full-data feature artifact cannot be built or verified safely."""


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _git_identity(repo_root: Path) -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise FeatureArtifactError(
            "Refusing to build the feature artifact from a dirty Git working tree."
        )

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        raise FeatureArtifactError("Could not resolve canonical Git commit.")
    return commit


def _load_curated_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "builder_version",
        "curated_schema_version",
        "database_sha256",
        "row_counts",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise FeatureArtifactError(
            "Curated manifest is missing required fields: " + ", ".join(missing)
        )
    if not isinstance(payload["row_counts"], dict):
        raise FeatureArtifactError("Curated manifest row_counts is invalid.")
    return payload


def _attach_read_only(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    alias: str,
) -> None:
    escaped = str(path).replace("'", "''")
    con.execute(f"ATTACH '{escaped}' AS {alias} (READ_ONLY)")


def _validate_curated_source(
    database_path: Path,
    curated_manifest_path: Path,
) -> tuple[dict[str, Any], str, str]:
    manifest = _load_curated_manifest(curated_manifest_path)
    database_sha = _sha256_file(database_path)
    manifest_sha = _sha256_file(curated_manifest_path)

    if database_sha != str(manifest["database_sha256"]):
        raise FeatureArtifactError(
            "Curated database SHA-256 does not match the curated manifest."
        )

    con = duckdb.connect(
        str(database_path),
        read_only=True,
        config={"enable_external_access": "false"},
    )
    try:
        metadata = con.execute(
            "SELECT schema_version, builder_version FROM build_metadata LIMIT 1"
        ).fetchone()
        if metadata is None:
            raise FeatureArtifactError("Curated database is missing build_metadata.")
        if int(metadata[0]) != int(manifest["curated_schema_version"]):
            raise FeatureArtifactError(
                "Curated schema version disagrees with the curated manifest."
            )
        if str(metadata[1]) != str(manifest["builder_version"]):
            raise FeatureArtifactError(
                "Curated builder version disagrees with the curated manifest."
            )

        for table in ("customers", "products", "transactions"):
            actual = int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            expected = int(manifest["row_counts"][table])
            if actual != expected:
                raise FeatureArtifactError(
                    f"Curated {table} row count disagrees with the curated manifest."
                )
    finally:
        con.close()

    return manifest, database_sha, manifest_sha


def _feature_sql(plan: OfficialSplitPlan) -> tuple[str, list[str]]:
    sql = """
    CREATE TABLE feature_rows AS
    WITH base AS (
        SELECT
            t.transaction_id,
            t.customer_id,
            t.product_id,
            t.transaction_date,
            CASE
                WHEN t.transaction_date <= CAST(? AS TIMESTAMP) THEN 'train'
                WHEN t.transaction_date <= CAST(? AS TIMESTAMP) THEN 'model_selection'
                WHEN t.transaction_date <= CAST(? AS TIMESTAMP) THEN 'calibration_gate'
                ELSE 'test'
            END AS segment,
            c.country AS customer_country_eval,
            CAST(t.fraud_score AS DOUBLE) AS fraud_score_reference,
            t.is_fraud,

            LN(1 + GREATEST(CAST(t.amount AS DOUBLE), 0.0)) AS log_amount,
            EXTRACT('hour' FROM t.transaction_date)::DOUBLE AS hour_of_day,
            EXTRACT('dow' FROM t.transaction_date)::DOUBLE AS day_of_week,
            GREATEST(
                DATE_DIFF(
                    'day',
                    p.opening_date,
                    CAST(t.transaction_date AS DATE)
                ),
                0
            )::DOUBLE AS product_tenure_days,
            t.currency,
            t.transaction_type,
            t.transaction_category,
            t.channel,
            t.merchant_category,
            p.product_type,
            CAST(t.amount AS DOUBLE) AS _amount,
            t.transaction_country
        FROM bank.transactions t
        JOIN bank.products p
          ON p.product_id = t.product_id
         AND p.customer_id = t.customer_id
        JOIN bank.customers c
          ON c.customer_id = t.customer_id
    ),
    history AS (
        SELECT
            *,
            (COUNT(*) OVER w_lifetime)::BIGINT AS prior_tx_count_lifetime,
            MAX(transaction_date) OVER w_lifetime AS _previous_transaction_date,

            (COUNT(*) OVER w_24h)::BIGINT AS prior_24h_tx_count,
            COALESCE(SUM(_amount) OVER w_24h, 0.0)::DOUBLE
                AS prior_24h_amount_sum,

            (COUNT(*) OVER w_30d)::BIGINT AS prior_30d_tx_count,
            COALESCE(SUM(_amount) OVER w_30d, 0.0)::DOUBLE
                AS prior_30d_amount_sum,

            (AVG(_amount) OVER w_currency)::DOUBLE
                AS prior_currency_mean_amount_lifetime,

            (COUNT(*) OVER w_channel)::BIGINT
                AS prior_channel_count_lifetime,

            CASE
                WHEN merchant_category IS NULL THEN 0
                ELSE COUNT(*) OVER w_merchant_category
            END::BIGINT AS prior_merchant_category_count_lifetime,

            (COUNT(*) OVER w_transaction_country)::BIGINT
                AS prior_transaction_country_count_lifetime
        FROM base
        WINDOW
            w_lifetime AS (
                PARTITION BY customer_id
                ORDER BY transaction_date
                RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                EXCLUDE GROUP
            ),
            w_24h AS (
                PARTITION BY customer_id
                ORDER BY transaction_date
                RANGE BETWEEN INTERVAL 24 HOURS PRECEDING AND CURRENT ROW
                EXCLUDE GROUP
            ),
            w_30d AS (
                PARTITION BY customer_id
                ORDER BY transaction_date
                RANGE BETWEEN INTERVAL 30 DAYS PRECEDING AND CURRENT ROW
                EXCLUDE GROUP
            ),
            w_currency AS (
                PARTITION BY customer_id, currency
                ORDER BY transaction_date
                RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                EXCLUDE GROUP
            ),
            w_channel AS (
                PARTITION BY customer_id, channel
                ORDER BY transaction_date
                RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                EXCLUDE GROUP
            ),
            w_merchant_category AS (
                PARTITION BY customer_id, merchant_category
                ORDER BY transaction_date
                RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                EXCLUDE GROUP
            ),
            w_transaction_country AS (
                PARTITION BY customer_id, transaction_country
                ORDER BY transaction_date
                RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                EXCLUDE GROUP
            )
    )
    SELECT
        transaction_id,
        customer_id,
        product_id,
        transaction_date,
        segment,
        customer_country_eval,
        fraud_score_reference,
        is_fraud,

        log_amount,
        hour_of_day,
        day_of_week,
        product_tenure_days,
        currency,
        transaction_type,
        transaction_category,
        channel,
        merchant_category,
        product_type,

        prior_tx_count_lifetime,
        (prior_tx_count_lifetime > 0) AS has_prior_transaction,
        CASE
            WHEN _previous_transaction_date IS NULL THEN NULL
            ELSE DATE_DIFF(
                'second',
                _previous_transaction_date,
                transaction_date
            )::DOUBLE
        END AS seconds_since_previous_tx,

        prior_24h_tx_count,
        prior_24h_amount_sum,
        prior_30d_tx_count,
        prior_30d_amount_sum,

        prior_currency_mean_amount_lifetime,
        (prior_currency_mean_amount_lifetime IS NOT NULL)
            AS has_prior_currency_amount_history,
        CASE
            WHEN prior_currency_mean_amount_lifetime IS NULL
                 OR prior_currency_mean_amount_lifetime = 0
            THEN NULL
            ELSE _amount / prior_currency_mean_amount_lifetime
        END::DOUBLE AS amount_to_prior_currency_mean_ratio,

        prior_channel_count_lifetime,
        (prior_channel_count_lifetime = 0) AS channel_novelty,

        prior_merchant_category_count_lifetime,
        CASE
            WHEN merchant_category IS NULL THEN FALSE
            ELSE prior_merchant_category_count_lifetime = 0
        END AS merchant_category_novelty,

        prior_transaction_country_count_lifetime,
        (prior_transaction_country_count_lifetime = 0)
            AS transaction_country_novelty
    FROM history
    """
    return sql, [
        plan.train_cutoff,
        plan.model_selection_cutoff,
        plan.calibration_gate_cutoff,
    ]


def _create_metadata(
    con: duckdb.DuckDBPyConnection,
    *,
    implementation_commit: str,
    source_database_sha256: str,
    source_manifest_sha256: str,
    plan: OfficialSplitPlan,
) -> None:
    con.execute(
        """
        CREATE TABLE artifact_metadata (
            artifact_version VARCHAR NOT NULL,
            contract_version VARCHAR NOT NULL,
            contract_sha256 VARCHAR NOT NULL,
            implementation_commit VARCHAR NOT NULL,
            source_database_sha256 VARCHAR NOT NULL,
            source_manifest_sha256 VARCHAR NOT NULL,
            total_rows BIGINT NOT NULL,
            train_rows BIGINT NOT NULL,
            model_selection_rows BIGINT NOT NULL,
            calibration_gate_rows BIGINT NOT NULL,
            test_rows BIGINT NOT NULL,
            train_cutoff TIMESTAMP NOT NULL,
            model_selection_cutoff TIMESTAMP NOT NULL,
            calibration_gate_cutoff TIMESTAMP NOT NULL
        )
        """
    )
    con.execute(
        """
        INSERT INTO artifact_metadata VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            CAST(? AS TIMESTAMP),
            CAST(? AS TIMESTAMP),
            CAST(? AS TIMESTAMP)
        )
        """,
        [
            ARTIFACT_VERSION,
            CONTRACT_VERSION,
            feature_contract_sha256(),
            implementation_commit,
            source_database_sha256,
            source_manifest_sha256,
            plan.total_rows,
            plan.train_rows,
            plan.model_selection_rows,
            plan.calibration_gate_rows,
            plan.test_rows,
            plan.train_cutoff,
            plan.model_selection_cutoff,
            plan.calibration_gate_cutoff,
        ],
    )


def _verify_schema(con: duckdb.DuckDBPyConnection) -> None:
    columns = {
        row[1]: row
        for row in con.execute("PRAGMA table_info('feature_rows')").fetchall()
    }

    required = {
        "transaction_id",
        "customer_id",
        "product_id",
        "transaction_date",
        "segment",
        "customer_country_eval",
        "fraud_score_reference",
        "is_fraud",
        *MODEL_FEATURE_NAMES,
    }
    missing = sorted(required - set(columns))
    if missing:
        raise FeatureArtifactError(
            "Feature artifact is missing required columns: " + ", ".join(missing)
        )

    forbidden_predictor_like = {
        "transaction_status",
        "customer_status",
        "product_status",
        "current_balance",
        "detected_accent",
        "merchant_name",
        "transaction_city",
    }
    unexpected = sorted(forbidden_predictor_like & set(columns))
    if unexpected:
        raise FeatureArtifactError(
            "Forbidden fields leaked into feature artifact: " + ", ".join(unexpected)
        )


def _verify_artifact_in_connection(
    con: duckdb.DuckDBPyConnection,
    plan: OfficialSplitPlan,
) -> None:
    _verify_schema(con)

    row_count, unique_ids = con.execute(
        """
        SELECT COUNT(*)::BIGINT, COUNT(DISTINCT transaction_id)::BIGINT
        FROM feature_rows
        """
    ).fetchone()
    if int(row_count) != plan.total_rows:
        raise FeatureArtifactError(
            f"Feature row count {row_count} does not match {plan.total_rows}."
        )
    if int(unique_ids) != plan.total_rows:
        raise FeatureArtifactError("Feature transaction IDs are not unique.")

    actual_segments = dict(
        con.execute(
            """
            SELECT segment, COUNT(*)::BIGINT
            FROM feature_rows
            GROUP BY segment
            """
        ).fetchall()
    )
    expected_segments = {
        "train": plan.train_rows,
        "model_selection": plan.model_selection_rows,
        "calibration_gate": plan.calibration_gate_rows,
        "test": plan.test_rows,
    }
    if actual_segments != expected_segments:
        raise FeatureArtifactError(
            f"Segment counts do not match split plan: {actual_segments!r}"
        )

    nullable = {
        feature.name
        for feature in MODEL_FEATURES
        if feature.nullable
    }
    nonnullable = [
        feature.name
        for feature in MODEL_FEATURES
        if feature.name not in nullable
    ]
    for feature in nonnullable:
        missing_count = int(
            con.execute(
                f'SELECT COUNT(*) FROM feature_rows WHERE "{feature}" IS NULL'
            ).fetchone()[0]
        )
        if missing_count:
            raise FeatureArtifactError(
                f"Non-nullable feature {feature} has {missing_count} null rows."
            )

    negative_counts = int(
        con.execute(
            """
            SELECT COUNT(*)
            FROM feature_rows
            WHERE prior_tx_count_lifetime < 0
               OR prior_24h_tx_count < 0
               OR prior_30d_tx_count < 0
               OR prior_channel_count_lifetime < 0
               OR prior_merchant_category_count_lifetime < 0
               OR prior_transaction_country_count_lifetime < 0
            """
        ).fetchone()[0]
    )
    if negative_counts:
        raise FeatureArtifactError("Historical count features contain negatives.")

    inconsistent_flags = int(
        con.execute(
            """
            SELECT COUNT(*)
            FROM feature_rows
            WHERE has_prior_transaction != (prior_tx_count_lifetime > 0)
               OR has_prior_currency_amount_history
                  != (prior_currency_mean_amount_lifetime IS NOT NULL)
               OR channel_novelty != (prior_channel_count_lifetime = 0)
               OR transaction_country_novelty
                  != (prior_transaction_country_count_lifetime = 0)
               OR (
                    merchant_category IS NULL
                    AND merchant_category_novelty != FALSE
               )
               OR (
                    merchant_category IS NOT NULL
                    AND merchant_category_novelty
                        != (prior_merchant_category_count_lifetime = 0)
               )
            """
        ).fetchone()[0]
    )
    if inconsistent_flags:
        raise FeatureArtifactError("Historical indicator invariants failed.")

    # Every customer's earliest timestamp group must have no prior history.
    earliest_history_failures = int(
        con.execute(
            """
            WITH earliest AS (
                SELECT customer_id, MIN(transaction_date) AS first_ts
                FROM feature_rows
                GROUP BY customer_id
            )
            SELECT COUNT(*)
            FROM feature_rows f
            JOIN earliest e USING (customer_id)
            WHERE f.transaction_date = e.first_ts
              AND (
                    f.prior_tx_count_lifetime != 0
                    OR f.has_prior_transaction
                    OR f.seconds_since_previous_tx IS NOT NULL
                    OR f.prior_24h_tx_count != 0
                    OR f.prior_30d_tx_count != 0
              )
            """
        ).fetchone()[0]
    )
    if earliest_history_failures:
        raise FeatureArtifactError(
            "Earliest timestamp rows incorrectly contain prior history."
        )


def _independent_history_sample_check(
    con: duckdb.DuckDBPyConnection,
    *,
    sample_size: int = 64,
) -> None:
    """Recompute reduced history for a deterministic sample from the source bank."""

    mismatches = int(
        con.execute(
            """
            WITH sample AS (
                SELECT
                    transaction_id,
                    customer_id,
                    transaction_date,
                    currency,
                    channel,
                    merchant_category,
                    prior_tx_count_lifetime,
                    seconds_since_previous_tx,
                    prior_24h_tx_count,
                    prior_24h_amount_sum,
                    prior_30d_tx_count,
                    prior_30d_amount_sum,
                    prior_currency_mean_amount_lifetime,
                    prior_channel_count_lifetime,
                    prior_merchant_category_count_lifetime,
                    prior_transaction_country_count_lifetime,
                    transaction_country_novelty
                FROM feature_rows
                ORDER BY HASH(transaction_id || 'r4b-b-verify-v1')
                LIMIT ?
            ),
            expected AS (
                SELECT
                    s.transaction_id,
                    COUNT(t.transaction_id)::BIGINT AS prior_tx_count_lifetime,
                    DATE_DIFF(
                        'second',
                        MAX(t.transaction_date),
                        s.transaction_date
                    )::DOUBLE AS seconds_since_previous_tx,
                    COUNT(t.transaction_id)
                        FILTER (
                            WHERE t.transaction_date
                                  >= s.transaction_date - INTERVAL 24 HOURS
                        )::BIGINT AS prior_24h_tx_count,
                    COALESCE(
                        SUM(CAST(t.amount AS DOUBLE))
                            FILTER (
                                WHERE t.transaction_date
                                      >= s.transaction_date - INTERVAL 24 HOURS
                            ),
                        0.0
                    )::DOUBLE AS prior_24h_amount_sum,
                    COUNT(t.transaction_id)
                        FILTER (
                            WHERE t.transaction_date
                                  >= s.transaction_date - INTERVAL 30 DAYS
                        )::BIGINT AS prior_30d_tx_count,
                    COALESCE(
                        SUM(CAST(t.amount AS DOUBLE))
                            FILTER (
                                WHERE t.transaction_date
                                      >= s.transaction_date - INTERVAL 30 DAYS
                            ),
                        0.0
                    )::DOUBLE AS prior_30d_amount_sum,
                    AVG(CAST(t.amount AS DOUBLE))
                        FILTER (WHERE t.currency = s.currency)::DOUBLE
                        AS prior_currency_mean_amount_lifetime,
                    COUNT(t.transaction_id)
                        FILTER (WHERE t.channel = s.channel)::BIGINT
                        AS prior_channel_count_lifetime,
                    COUNT(t.transaction_id)
                        FILTER (
                            WHERE s.merchant_category IS NOT NULL
                              AND t.merchant_category = s.merchant_category
                        )::BIGINT AS prior_merchant_category_count_lifetime,
                    COUNT(t.transaction_id)
                        FILTER (
                            WHERE t.transaction_country = current_tx.transaction_country
                        )::BIGINT AS prior_transaction_country_count_lifetime
                FROM sample s
                JOIN bank.transactions current_tx
                  ON current_tx.transaction_id = s.transaction_id
                LEFT JOIN bank.transactions t
                  ON t.customer_id = s.customer_id
                 AND t.transaction_date < s.transaction_date
                GROUP BY
                    s.transaction_id,
                    s.transaction_date,
                    s.currency,
                    s.channel,
                    s.merchant_category,
                    current_tx.transaction_country
            )
            SELECT COUNT(*)
            FROM sample s
            JOIN expected e USING (transaction_id)
            WHERE s.prior_tx_count_lifetime != e.prior_tx_count_lifetime
               OR s.seconds_since_previous_tx
                    IS DISTINCT FROM e.seconds_since_previous_tx
               OR s.prior_24h_tx_count != e.prior_24h_tx_count
               OR ABS(s.prior_24h_amount_sum - e.prior_24h_amount_sum) > 1e-8
               OR s.prior_30d_tx_count != e.prior_30d_tx_count
               OR ABS(s.prior_30d_amount_sum - e.prior_30d_amount_sum) > 1e-8
               OR (
                    s.prior_currency_mean_amount_lifetime
                    IS DISTINCT FROM e.prior_currency_mean_amount_lifetime
                    AND NOT (
                        s.prior_currency_mean_amount_lifetime IS NOT NULL
                        AND e.prior_currency_mean_amount_lifetime IS NOT NULL
                        AND ABS(
                            s.prior_currency_mean_amount_lifetime
                            - e.prior_currency_mean_amount_lifetime
                        ) <= 1e-8
                    )
               )
               OR s.prior_channel_count_lifetime
                    != e.prior_channel_count_lifetime
               OR s.prior_merchant_category_count_lifetime
                    != e.prior_merchant_category_count_lifetime
               OR s.prior_transaction_country_count_lifetime
                    != e.prior_transaction_country_count_lifetime
            """,
            [sample_size],
        ).fetchone()[0]
    )
    if mismatches:
        raise FeatureArtifactError(
            f"Independent history verification found {mismatches} mismatched rows."
        )


def build_feature_artifact(
    *,
    database_path: Path,
    curated_manifest_path: Path,
    output_database_path: Path,
    output_manifest_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    database_path = database_path.expanduser().resolve()
    curated_manifest_path = curated_manifest_path.expanduser().resolve()
    output_database_path = output_database_path.expanduser().resolve()
    output_manifest_path = output_manifest_path.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()

    if not database_path.is_file():
        raise FileNotFoundError(database_path)
    if not curated_manifest_path.is_file():
        raise FileNotFoundError(curated_manifest_path)
    if output_database_path.exists() or output_manifest_path.exists():
        raise FeatureArtifactError(
            "Feature artifact output already exists; refusing to overwrite."
        )

    implementation_commit = _git_identity(repo_root)
    curated_manifest, source_db_sha, source_manifest_sha = _validate_curated_source(
        database_path,
        curated_manifest_path,
    )

    source_con = duckdb.connect(
        str(database_path),
        read_only=True,
        config={"enable_external_access": "false"},
    )
    try:
        plan = derive_official_split_plan(source_con)
    finally:
        source_con.close()

    expected_rows = int(curated_manifest["row_counts"]["transactions"])
    if plan.total_rows != expected_rows:
        raise FeatureArtifactError(
            "Official split plan total does not match curated transaction count."
        )

    output_database_path.parent.mkdir(parents=True, exist_ok=True)
    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    staging_db = output_database_path.with_suffix(
        output_database_path.suffix + ".building"
    )
    staging_manifest = output_manifest_path.with_suffix(
        output_manifest_path.suffix + ".tmp"
    )
    if staging_db.exists():
        staging_db.unlink()
    if staging_manifest.exists():
        staging_manifest.unlink()

    started = time.perf_counter()
    try:
        con = duckdb.connect(str(staging_db))
        try:
            _attach_read_only(con, database_path, "bank")
            con.execute("PRAGMA threads=4")
            sql, params = _feature_sql(plan)
            con.execute(sql, params)
            _create_metadata(
                con,
                implementation_commit=implementation_commit,
                source_database_sha256=source_db_sha,
                source_manifest_sha256=source_manifest_sha,
                plan=plan,
            )
            _verify_artifact_in_connection(con, plan)
            _independent_history_sample_check(con)
            con.execute("CHECKPOINT")
        finally:
            con.close()

        database_sha = _sha256_file(staging_db)
        build_seconds = time.perf_counter() - started
        manifest = {
            "artifact_version": ARTIFACT_VERSION,
            "contract_version": CONTRACT_VERSION,
            "contract_sha256": feature_contract_sha256(),
            "implementation_commit": implementation_commit,
            "source_database_sha256": source_db_sha,
            "source_manifest_sha256": source_manifest_sha,
            "source_transaction_rows": expected_rows,
            "split_plan": asdict(plan),
            "model_feature_names": list(MODEL_FEATURE_NAMES),
            "model_feature_count": len(MODEL_FEATURE_NAMES),
            "artifact_database_sha256": database_sha,
            "build_seconds": build_seconds,
        }
        staging_manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        os.replace(staging_db, output_database_path)
        os.replace(staging_manifest, output_manifest_path)

        verify_feature_artifact(
            database_path=database_path,
            curated_manifest_path=curated_manifest_path,
            feature_database_path=output_database_path,
            feature_manifest_path=output_manifest_path,
        )
        return manifest
    except Exception:
        for path in (
            staging_db,
            staging_manifest,
            output_database_path,
            output_manifest_path,
        ):
            if path.exists():
                path.unlink()
        wal = Path(str(staging_db) + ".wal")
        if wal.exists():
            wal.unlink()
        raise


def verify_feature_artifact(
    *,
    database_path: Path,
    curated_manifest_path: Path,
    feature_database_path: Path,
    feature_manifest_path: Path,
) -> dict[str, Any]:
    database_path = database_path.expanduser().resolve()
    curated_manifest_path = curated_manifest_path.expanduser().resolve()
    feature_database_path = feature_database_path.expanduser().resolve()
    feature_manifest_path = feature_manifest_path.expanduser().resolve()

    if not feature_database_path.is_file():
        raise FileNotFoundError(feature_database_path)
    if not feature_manifest_path.is_file():
        raise FileNotFoundError(feature_manifest_path)

    manifest = json.loads(feature_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("artifact_version") != ARTIFACT_VERSION:
        raise FeatureArtifactError("Unsupported feature artifact version.")
    if manifest.get("contract_version") != CONTRACT_VERSION:
        raise FeatureArtifactError("Feature artifact contract version mismatch.")
    if manifest.get("contract_sha256") != feature_contract_sha256():
        raise FeatureArtifactError("Feature artifact contract SHA-256 mismatch.")

    _, source_db_sha, source_manifest_sha = _validate_curated_source(
        database_path,
        curated_manifest_path,
    )
    if manifest.get("source_database_sha256") != source_db_sha:
        raise FeatureArtifactError("Feature artifact source database mismatch.")
    if manifest.get("source_manifest_sha256") != source_manifest_sha:
        raise FeatureArtifactError("Feature artifact source manifest mismatch.")

    actual_artifact_sha = _sha256_file(feature_database_path)
    if manifest.get("artifact_database_sha256") != actual_artifact_sha:
        raise FeatureArtifactError("Feature artifact database SHA-256 mismatch.")

    source_con = duckdb.connect(
        str(database_path),
        read_only=True,
        config={"enable_external_access": "false"},
    )
    try:
        expected_plan = derive_official_split_plan(source_con)
    finally:
        source_con.close()

    if manifest.get("split_plan") != asdict(expected_plan):
        raise FeatureArtifactError("Feature artifact split plan mismatch.")

    con = duckdb.connect(str(feature_database_path), read_only=True)
    try:
        _attach_read_only(con, database_path, "bank")
        _verify_artifact_in_connection(con, expected_plan)
        _independent_history_sample_check(con)
    finally:
        con.close()

    return manifest


def _safe_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_version": manifest["artifact_version"],
        "contract_version": manifest["contract_version"],
        "contract_sha256": manifest["contract_sha256"],
        "implementation_commit": manifest["implementation_commit"],
        "source_database_sha256": manifest["source_database_sha256"],
        "source_manifest_sha256": manifest["source_manifest_sha256"],
        "source_transaction_rows": manifest["source_transaction_rows"],
        "split_plan": manifest["split_plan"],
        "model_feature_count": manifest["model_feature_count"],
        "artifact_database_sha256": manifest["artifact_database_sha256"],
        "build_seconds": manifest["build_seconds"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/curated/bank.duckdb")
    parser.add_argument(
        "--curated-manifest",
        default="data/curated/build_manifest.json",
    )
    parser.add_argument(
        "--output-database",
        default="ml/private/r4b/analytics.duckdb",
    )
    parser.add_argument(
        "--output-manifest",
        default="ml/private/r4b/analytics_manifest.json",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing feature artifact instead of building it.",
    )
    args = parser.parse_args()

    if args.verify:
        manifest = verify_feature_artifact(
            database_path=Path(args.database),
            curated_manifest_path=Path(args.curated_manifest),
            feature_database_path=Path(args.output_database),
            feature_manifest_path=Path(args.output_manifest),
        )
        print("R4B FULL-DATA FEATURE ARTIFACT VERIFIED")
    else:
        manifest = build_feature_artifact(
            database_path=Path(args.database),
            curated_manifest_path=Path(args.curated_manifest),
            output_database_path=Path(args.output_database),
            output_manifest_path=Path(args.output_manifest),
            repo_root=Path(args.repo_root),
        )
        print("R4B FULL-DATA FEATURE ARTIFACT COMPLETE")

    print(json.dumps(_safe_summary(manifest), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
