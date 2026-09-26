from __future__ import annotations

from datetime import datetime, timedelta

import duckdb

from ml.full_data_contract import (
    CONTRACT_VERSION,
    EXPLICITLY_EXCLUDED_PREDICTORS,
    MODEL_FEATURE_NAMES,
    REFERENCE_ONLY_COLUMNS,
    TARGET_COLUMN,
    derive_official_split_plan,
    feature_contract_dict,
    segment_case_sql,
)


def _fixture() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE transactions (
            transaction_id VARCHAR,
            transaction_date TIMESTAMP
        )
        """
    )
    start = datetime(2025, 1, 1)
    rows = []
    # 100 timestamp groups x 10 transactions each.
    for group in range(100):
        timestamp = start + timedelta(hours=group)
        for item in range(10):
            rows.append((f"T-{group:03d}-{item:02d}", timestamp))
    con.executemany("INSERT INTO transactions VALUES (?, ?)", rows)
    return con


def test_official_split_plan_keeps_whole_timestamp_groups() -> None:
    con = _fixture()
    try:
        plan = derive_official_split_plan(con)
        counts = con.execute(
            f"""
            SELECT segment, COUNT(*)
            FROM (
                SELECT
                    {segment_case_sql()} AS segment
                FROM transactions
            )
            GROUP BY segment
            ORDER BY segment
            """,
            [
                plan.train_cutoff,
                plan.model_selection_cutoff,
                plan.calibration_gate_cutoff,
            ],
        ).fetchall()

        mixed = con.execute(
            f"""
            SELECT transaction_date, COUNT(DISTINCT segment)
            FROM (
                SELECT
                    transaction_date,
                    {segment_case_sql()} AS segment
                FROM transactions
            )
            GROUP BY transaction_date
            HAVING COUNT(DISTINCT segment) > 1
            """,
            [
                plan.train_cutoff,
                plan.model_selection_cutoff,
                plan.calibration_gate_cutoff,
            ],
        ).fetchall()
    finally:
        con.close()

    assert plan.total_rows == 1000
    assert plan.train_rows == 700
    assert plan.model_selection_rows == 80
    assert plan.calibration_gate_rows == 70
    assert plan.test_rows == 150
    assert sum(count for _, count in counts) == 1000
    assert mixed == []


def test_reduced_feature_contract_is_exact_and_leakage_safe() -> None:
    contract = feature_contract_dict()

    assert contract["contract_version"] == CONTRACT_VERSION
    assert contract["breadth"] == "reduced"
    assert contract["target_column"] == TARGET_COLUMN
    assert REFERENCE_ONLY_COLUMNS == ("fraud_score",)
    assert len(MODEL_FEATURE_NAMES) == len(set(MODEL_FEATURE_NAMES))

    expected_history = {
        "prior_tx_count_lifetime",
        "has_prior_transaction",
        "seconds_since_previous_tx",
        "prior_24h_tx_count",
        "prior_24h_amount_sum",
        "prior_30d_tx_count",
        "prior_30d_amount_sum",
        "prior_currency_mean_amount_lifetime",
        "has_prior_currency_amount_history",
        "amount_to_prior_currency_mean_ratio",
        "prior_channel_count_lifetime",
        "channel_novelty",
        "prior_merchant_category_count_lifetime",
        "merchant_category_novelty",
        "prior_transaction_country_count_lifetime",
        "transaction_country_novelty",
    }
    assert expected_history.issubset(MODEL_FEATURE_NAMES)

    forbidden_names = {
        "fraud_score",
        "transaction_status",
        "customer_id",
        "product_id",
        "transaction_id",
        "raw_merchant_name",
        "transaction_city",
    }
    assert not (forbidden_names & set(MODEL_FEATURE_NAMES))
    assert forbidden_names.issubset(set(EXPLICITLY_EXCLUDED_PREDICTORS))


def test_contract_retains_first_history_rows_and_forbids_same_timestamp_history() -> None:
    contract = feature_contract_dict()

    assert "strictly earlier" in contract["same_timestamp_rule"]
    assert "same-timestamp peers never count as history" in contract["same_timestamp_rule"]
    assert "Rows with no prior history are retained" in contract["first_history_rule"]


def test_split_fractions_are_frozen() -> None:
    fractions = feature_contract_dict()["split_fractions"]

    assert fractions == {
        "train": 0.70,
        "model_selection": 0.075,
        "calibration_gate": 0.075,
        "test": 0.15,
    }
    assert sum(fractions.values()) == 1.0
