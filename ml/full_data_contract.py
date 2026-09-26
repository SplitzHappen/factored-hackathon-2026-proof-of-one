from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

import duckdb


CONTRACT_VERSION = "factored-r4b-reduced-contract-v1"

TRAIN_FRACTION = 0.70
MODEL_SELECTION_FRACTION = 0.075
CALIBRATION_GATE_FRACTION = 0.075
TEST_FRACTION = 0.15


class Segment(StrEnum):
    TRAIN = "train"
    MODEL_SELECTION = "model_selection"
    CALIBRATION_GATE = "calibration_gate"
    TEST = "test"


@dataclass(frozen=True, slots=True)
class OfficialSplitPlan:
    total_rows: int
    train_rows: int
    model_selection_rows: int
    calibration_gate_rows: int
    test_rows: int
    train_cutoff: str
    model_selection_cutoff: str
    calibration_gate_cutoff: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    name: str
    kind: str
    source: str
    as_of_rule: str
    nullable: bool = False


INTRINSIC_FEATURES = (
    FeatureDefinition(
        "log_amount",
        "numeric",
        "transactions.amount",
        "current transaction fact; log1p(nonnegative amount)",
    ),
    FeatureDefinition(
        "hour_of_day",
        "numeric",
        "transactions.transaction_date",
        "current transaction timestamp",
    ),
    FeatureDefinition(
        "day_of_week",
        "numeric",
        "transactions.transaction_date",
        "current transaction timestamp",
    ),
    FeatureDefinition(
        "product_tenure_days",
        "numeric",
        "products.opening_date",
        "opening_date used only to derive tenure at current transaction time",
    ),
    FeatureDefinition(
        "currency",
        "categorical",
        "transactions.currency",
        "explicit current transaction fact",
    ),
    FeatureDefinition(
        "transaction_type",
        "categorical",
        "transactions.transaction_type",
        "current transaction fact",
    ),
    FeatureDefinition(
        "transaction_category",
        "categorical",
        "transactions.transaction_category",
        "current transaction fact",
        nullable=True,
    ),
    FeatureDefinition(
        "channel",
        "categorical",
        "transactions.channel",
        "current transaction fact",
    ),
    FeatureDefinition(
        "merchant_category",
        "categorical",
        "transactions.merchant_category",
        "current transaction fact",
        nullable=True,
    ),
    FeatureDefinition(
        "product_type",
        "categorical",
        "products.product_type",
        "current linked-product fact",
    ),
)

REDUCED_HISTORY_FEATURES = (
    FeatureDefinition(
        "prior_tx_count_lifetime",
        "numeric",
        "transactions",
        "same customer; transaction_date strictly earlier than current timestamp",
    ),
    FeatureDefinition(
        "has_prior_transaction",
        "boolean",
        "transactions",
        "1 iff at least one same-customer transaction is strictly earlier",
    ),
    FeatureDefinition(
        "seconds_since_previous_tx",
        "numeric",
        "transactions.transaction_date",
        "current timestamp minus latest strictly earlier same-customer timestamp",
        nullable=True,
    ),
    FeatureDefinition(
        "prior_24h_tx_count",
        "numeric",
        "transactions",
        "same customer; [t-24h, t) only",
    ),
    FeatureDefinition(
        "prior_24h_amount_sum",
        "numeric",
        "transactions.amount",
        "same customer; [t-24h, t) only",
    ),
    FeatureDefinition(
        "prior_30d_tx_count",
        "numeric",
        "transactions",
        "same customer; [t-30d, t) only",
    ),
    FeatureDefinition(
        "prior_30d_amount_sum",
        "numeric",
        "transactions.amount",
        "same customer; [t-30d, t) only",
    ),
    FeatureDefinition(
        "prior_currency_mean_amount_lifetime",
        "numeric",
        "transactions.amount + currency",
        "same customer and explicit currency; strictly earlier timestamps only",
        nullable=True,
    ),
    FeatureDefinition(
        "has_prior_currency_amount_history",
        "boolean",
        "transactions.amount + currency",
        "1 iff prior_currency_mean_amount_lifetime is defined",
    ),
    FeatureDefinition(
        "amount_to_prior_currency_mean_ratio",
        "numeric",
        "derived",
        "current amount / prior currency mean; null when prior mean unavailable or zero",
        nullable=True,
    ),
    FeatureDefinition(
        "prior_channel_count_lifetime",
        "numeric",
        "transactions.channel",
        "same customer and channel; strictly earlier timestamps only",
    ),
    FeatureDefinition(
        "channel_novelty",
        "boolean",
        "transactions.channel",
        "1 iff no strictly earlier same-customer transaction used this channel",
    ),
    FeatureDefinition(
        "prior_merchant_category_count_lifetime",
        "numeric",
        "transactions.merchant_category",
        "same customer and nonmissing merchant category; strictly earlier timestamps only",
    ),
    FeatureDefinition(
        "merchant_category_novelty",
        "boolean",
        "transactions.merchant_category",
        "1 iff nonmissing current category has no strictly earlier same-customer occurrence",
    ),
    FeatureDefinition(
        "prior_transaction_country_count_lifetime",
        "numeric",
        "transactions.transaction_country",
        "same customer and transaction country; strictly earlier timestamps only",
    ),
    FeatureDefinition(
        "transaction_country_novelty",
        "boolean",
        "transactions.transaction_country",
        "1 iff no strictly earlier same-customer transaction used this transaction country",
    ),
)

MODEL_FEATURES = INTRINSIC_FEATURES + REDUCED_HISTORY_FEATURES
MODEL_FEATURE_NAMES = tuple(feature.name for feature in MODEL_FEATURES)

ROW_KEY_COLUMNS = (
    "transaction_id",
    "customer_id",
    "product_id",
    "transaction_date",
    "segment",
)
TARGET_COLUMN = "is_fraud"
REFERENCE_ONLY_COLUMNS = ("fraud_score",)

EXPLICITLY_EXCLUDED_PREDICTORS = (
    "is_fraud_except_target",
    "fraud_score",
    "transaction_status",
    "customer_status",
    "product_status",
    "products.last_transaction_date",
    "expiration_date",
    "current_balance",
    "products.last_updated",
    "customer_country",
    "detected_accent",
    "customer_id",
    "product_id",
    "transaction_id",
    "raw_merchant_name",
    "transaction_city",
    "prior_fraud_count",
    "days_since_fraud",
    "target_encoding",
    "fraud_rate_encoding",
    "future_transactions",
    "future_labels",
    "10m_history_window",
    "1h_history_window",
    "7d_history_window",
    "90d_history_window",
)


class SplitContractError(RuntimeError):
    """Raised when official chronological segments cannot be derived safely."""


def _timestamp_groups(
    con: duckdb.DuckDBPyConnection,
) -> list[tuple[datetime, int]]:
    return con.execute(
        """
        SELECT transaction_date, COUNT(*)::BIGINT AS n
        FROM transactions
        GROUP BY transaction_date
        ORDER BY transaction_date
        """
    ).fetchall()


def _cutoff_for_global_fraction(
    groups: list[tuple[datetime, int]],
    fraction: float,
) -> tuple[datetime, int]:
    if not groups:
        raise SplitContractError("No transaction timestamp groups are available.")
    total = sum(count for _, count in groups)
    target = math.ceil(total * fraction)
    cumulative = 0
    for timestamp, count in groups:
        cumulative += count
        if cumulative >= target:
            return timestamp, cumulative
    return groups[-1][0], total


def derive_official_split_plan(
    con: duckdb.DuckDBPyConnection,
) -> OfficialSplitPlan:
    groups = _timestamp_groups(con)
    total = sum(count for _, count in groups)

    train_cutoff, train_end = _cutoff_for_global_fraction(groups, TRAIN_FRACTION)
    selection_cutoff, selection_end = _cutoff_for_global_fraction(
        groups,
        TRAIN_FRACTION + MODEL_SELECTION_FRACTION,
    )
    gate_cutoff, gate_end = _cutoff_for_global_fraction(
        groups,
        TRAIN_FRACTION + MODEL_SELECTION_FRACTION + CALIBRATION_GATE_FRACTION,
    )

    if not (train_cutoff < selection_cutoff < gate_cutoff):
        raise SplitContractError(
            "Timestamp groups are too coarse to create four strictly ordered segments."
        )

    plan = OfficialSplitPlan(
        total_rows=total,
        train_rows=train_end,
        model_selection_rows=selection_end - train_end,
        calibration_gate_rows=gate_end - selection_end,
        test_rows=total - gate_end,
        train_cutoff=train_cutoff.isoformat(),
        model_selection_cutoff=selection_cutoff.isoformat(),
        calibration_gate_cutoff=gate_cutoff.isoformat(),
    )
    if sum(
        (
            plan.train_rows,
            plan.model_selection_rows,
            plan.calibration_gate_rows,
            plan.test_rows,
        )
    ) != total:
        raise SplitContractError("Official segment counts do not sum to total rows.")
    if min(
        plan.train_rows,
        plan.model_selection_rows,
        plan.calibration_gate_rows,
        plan.test_rows,
    ) <= 0:
        raise SplitContractError("Every official segment must contain rows.")
    return plan


def segment_case_sql() -> str:
    """Return the canonical SQL CASE expression for segment assignment."""

    return """
    CASE
        WHEN transaction_date <= CAST(? AS TIMESTAMP) THEN 'train'
        WHEN transaction_date <= CAST(? AS TIMESTAMP) THEN 'model_selection'
        WHEN transaction_date <= CAST(? AS TIMESTAMP) THEN 'calibration_gate'
        ELSE 'test'
    END
    """.strip()


def feature_contract_dict() -> dict[str, object]:
    return {
        "contract_version": CONTRACT_VERSION,
        "split_fractions": {
            "train": TRAIN_FRACTION,
            "model_selection": MODEL_SELECTION_FRACTION,
            "calibration_gate": CALIBRATION_GATE_FRACTION,
            "test": TEST_FRACTION,
        },
        "model_features": [asdict(feature) for feature in MODEL_FEATURES],
        "row_key_columns": list(ROW_KEY_COLUMNS),
        "target_column": TARGET_COLUMN,
        "reference_only_columns": list(REFERENCE_ONLY_COLUMNS),
        "explicitly_excluded_predictors": list(EXPLICITLY_EXCLUDED_PREDICTORS),
        "same_timestamp_rule": (
            "Historical features use transaction_date strictly earlier than the "
            "current timestamp; same-timestamp peers never count as history."
        ),
        "first_history_rule": (
            "Rows with no prior history are retained with explicit history-depth/"
            "missing indicators and nullable historical values where appropriate."
        ),
        "breadth": "reduced",
    }



def feature_contract_sha256() -> str:
    payload = json.dumps(
        feature_contract_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
