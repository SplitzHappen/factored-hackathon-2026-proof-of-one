from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn import __version__ as sklearn_version
from sklearn.preprocessing import OrdinalEncoder


PROBE_VERSION = "factored-r4a-signal-probe-v1"
SAMPLE_MODULUS = 4
SAMPLE_REMAINDER = 0
INTERNAL_TRAIN_FRACTION = 0.80
FULL_FEATURE_MIN_POSITIVES = 100
FULL_FEATURE_MIN_PR_AUC_LIFT = 3.0
FULL_FEATURE_MIN_TOP_005_RECALL = 0.03

CATEGORICAL_FEATURES = [
    "currency",
    "transaction_type",
    "transaction_category",
    "channel",
    "merchant_category",
    "product_type",
]
NUMERIC_FEATURES = [
    "log_amount",
    "hour_of_day",
    "day_of_week",
    "product_tenure_days",
]


class SignalProbeError(RuntimeError):
    """Raised when the training-only signal probe cannot run safely."""


@dataclass(frozen=True)
class SplitIdentity:
    total_rows: int
    training_rows: int
    training_cutoff: str
    internal_train_rows: int
    internal_holdout_rows: int
    internal_cutoff: str



def _git_identity(repo_root: Path) -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise SignalProbeError(
            "Refusing to run the signal probe from a dirty Git working tree."
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
        raise SignalProbeError("Could not resolve canonical Git commit.")
    return commit


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _timestamp_groups(
    con: duckdb.DuckDBPyConnection,
    *,
    maximum_timestamp: str | None = None,
) -> list[tuple[datetime, int]]:
    where = "WHERE transaction_date <= CAST(? AS TIMESTAMP)" if maximum_timestamp else ""
    params = [maximum_timestamp] if maximum_timestamp else []
    return con.execute(
        f"""
        SELECT transaction_date, COUNT(*)::BIGINT AS n
        FROM transactions
        {where}
        GROUP BY transaction_date
        ORDER BY transaction_date
        """,
        params,
    ).fetchall()


def _cutoff_for_fraction(
    groups: list[tuple[datetime, int]],
    fraction: float,
) -> tuple[datetime, int]:
    if not groups:
        raise SignalProbeError("No timestamp groups are available.")
    total = sum(count for _, count in groups)
    target = math.ceil(total * fraction)
    cumulative = 0
    for timestamp, count in groups:
        cumulative += count
        if cumulative >= target:
            return timestamp, cumulative
    return groups[-1][0], total


def derive_splits(con: duckdb.DuckDBPyConnection) -> SplitIdentity:
    all_groups = _timestamp_groups(con)
    total_rows = sum(count for _, count in all_groups)
    training_cutoff, training_rows = _cutoff_for_fraction(all_groups, 0.70)

    training_groups = [
        (timestamp, count)
        for timestamp, count in all_groups
        if timestamp <= training_cutoff
    ]
    internal_cutoff, internal_train_rows = _cutoff_for_fraction(
        training_groups,
        INTERNAL_TRAIN_FRACTION,
    )
    return SplitIdentity(
        total_rows=total_rows,
        training_rows=training_rows,
        training_cutoff=training_cutoff.isoformat(),
        internal_train_rows=internal_train_rows,
        internal_holdout_rows=training_rows - internal_train_rows,
        internal_cutoff=internal_cutoff.isoformat(),
    )


def _training_profile(
    con: duckdb.DuckDBPyConnection,
    split: SplitIdentity,
) -> dict[str, Any]:
    cutoff = split.training_cutoff
    prevalence = con.execute(
        """
        SELECT
            COUNT(*)::BIGINT,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::BIGINT,
            AVG(CASE WHEN is_fraud THEN 1.0 ELSE 0.0 END)
        FROM transactions
        WHERE transaction_date <= CAST(? AS TIMESTAMP)
        """,
        [cutoff],
    ).fetchone()

    organizer_score = con.execute(
        """
        SELECT
            COUNT(*)::BIGINT,
            COUNT(fraud_score)::BIGINT,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::BIGINT,
            SUM(CASE WHEN fraud_score IS NOT NULL AND is_fraud THEN 1 ELSE 0 END)::BIGINT,
            SUM(CASE WHEN fraud_score IS NULL AND is_fraud THEN 1 ELSE 0 END)::BIGINT
        FROM transactions
        WHERE transaction_date <= CAST(? AS TIMESTAMP)
        """,
        [cutoff],
    ).fetchone()

    return {
        "rows": int(prevalence[0]),
        "positive_rows": int(prevalence[1]),
        "prevalence": float(prevalence[2]),
        "organizer_fraud_score_coverage": float(organizer_score[1] / organizer_score[0]),
        "fraud_prevalence_score_present": (
            float(organizer_score[3] / organizer_score[1])
            if organizer_score[1]
            else None
        ),
        "fraud_prevalence_score_missing": (
            float(organizer_score[4] / (organizer_score[0] - organizer_score[1]))
            if organizer_score[0] != organizer_score[1]
            else None
        ),
    }


def _group_profile(
    con: duckdb.DuckDBPyConnection,
    split: SplitIdentity,
    expression: str,
    alias: str,
    *,
    top_n: int = 20,
) -> list[dict[str, Any]]:
    rows = con.execute(
        f"""
        SELECT
            CAST({expression} AS VARCHAR) AS value,
            COUNT(*)::BIGINT AS rows,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::BIGINT AS fraud_rows,
            AVG(CASE WHEN is_fraud THEN 1.0 ELSE 0.0 END) AS fraud_rate
        FROM transactions
        WHERE transaction_date <= CAST(? AS TIMESTAMP)
        GROUP BY 1
        ORDER BY rows DESC, value
        LIMIT ?
        """,
        [split.training_cutoff, top_n],
    ).fetchall()
    return [
        {
            alias: row[0],
            "rows": int(row[1]),
            "fraud_rows": int(row[2]),
            "fraud_rate": float(row[3]),
        }
        for row in rows
    ]


def _amount_deciles(
    con: duckdb.DuckDBPyConnection,
    split: SplitIdentity,
) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        WITH training AS (
            SELECT amount, is_fraud
            FROM transactions
            WHERE transaction_date <= CAST(? AS TIMESTAMP)
        ),
        bucketed AS (
            SELECT
                NTILE(10) OVER (ORDER BY amount) AS amount_decile,
                amount,
                is_fraud
            FROM training
        )
        SELECT
            amount_decile,
            COUNT(*)::BIGINT,
            MIN(amount),
            MAX(amount),
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::BIGINT,
            AVG(CASE WHEN is_fraud THEN 1.0 ELSE 0.0 END)
        FROM bucketed
        GROUP BY amount_decile
        ORDER BY amount_decile
        """,
        [split.training_cutoff],
    ).fetchall()
    return [
        {
            "amount_decile": int(row[0]),
            "rows": int(row[1]),
            "min_amount": float(row[2]),
            "max_amount": float(row[3]),
            "fraud_rows": int(row[4]),
            "fraud_rate": float(row[5]),
        }
        for row in rows
    ]


def _novelty_profile(
    con: duckdb.DuckDBPyConnection,
    split: SplitIdentity,
    column: str,
) -> list[dict[str, Any]]:
    allowed = {"channel", "merchant_category", "transaction_country"}
    if column not in allowed:
        raise ValueError(f"Unsupported novelty column: {column}")
    rows = con.execute(
        f"""
        WITH training AS (
            SELECT
                customer_id,
                transaction_date,
                {column} AS feature_value,
                is_fraud,
                MIN(transaction_date) OVER (
                    PARTITION BY customer_id, {column}
                ) AS first_seen_at
            FROM transactions
            WHERE transaction_date <= CAST(? AS TIMESTAMP)
        )
        SELECT
            CASE
                WHEN feature_value IS NULL THEN 'missing'
                WHEN transaction_date = first_seen_at THEN 'first_observed'
                ELSE 'familiar'
            END AS novelty,
            COUNT(*)::BIGINT,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::BIGINT,
            AVG(CASE WHEN is_fraud THEN 1.0 ELSE 0.0 END)
        FROM training
        GROUP BY 1
        ORDER BY 1
        """,
        [split.training_cutoff],
    ).fetchall()
    return [
        {
            "novelty": row[0],
            "rows": int(row[1]),
            "fraud_rows": int(row[2]),
            "fraud_rate": float(row[3]),
        }
        for row in rows
    ]


def _model_rows(
    con: duckdb.DuckDBPyConnection,
    split: SplitIdentity,
    *,
    internal_train: bool,
) -> dict[str, np.ndarray]:
    comparator = "<=" if internal_train else ">"
    upper = split.internal_cutoff if internal_train else split.training_cutoff
    lower_clause = "" if internal_train else "AND t.transaction_date <= CAST(? AS TIMESTAMP)"
    params: list[Any]
    if internal_train:
        params = [split.internal_cutoff, SAMPLE_MODULUS, SAMPLE_REMAINDER]
    else:
        params = [
            split.internal_cutoff,
            split.training_cutoff,
            SAMPLE_MODULUS,
            SAMPLE_REMAINDER,
        ]

    query = f"""
        SELECT
            LN(1 + GREATEST(t.amount, 0)) AS log_amount,
            EXTRACT('hour' FROM t.transaction_date)::DOUBLE AS hour_of_day,
            EXTRACT('dow' FROM t.transaction_date)::DOUBLE AS day_of_week,
            GREATEST(
                DATE_DIFF('day', p.opening_date, CAST(t.transaction_date AS DATE)),
                0
            )::DOUBLE AS product_tenure_days,
            COALESCE(t.currency, '__MISSING__') AS currency,
            COALESCE(t.transaction_type, '__MISSING__') AS transaction_type,
            COALESCE(t.transaction_category, '__MISSING__') AS transaction_category,
            COALESCE(t.channel, '__MISSING__') AS channel,
            COALESCE(t.merchant_category, '__MISSING__') AS merchant_category,
            COALESCE(p.product_type, '__MISSING__') AS product_type,
            CASE WHEN t.is_fraud THEN 1 ELSE 0 END::INTEGER AS target
        FROM transactions t
        JOIN products p
          ON p.product_id = t.product_id
         AND p.customer_id = t.customer_id
        WHERE t.transaction_date {comparator} CAST(? AS TIMESTAMP)
          {lower_clause}
          AND MOD(HASH(t.transaction_id || 'proof-of-one-r4a-v1'), ?) = ?
        ORDER BY t.transaction_date, t.transaction_id
    """
    return con.execute(query, params).fetchnumpy()


def _feature_blocks(
    rows: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    numeric = np.column_stack(
        [
            np.asarray(rows[name], dtype=np.float64)
            for name in NUMERIC_FEATURES
        ]
    )
    categorical = np.column_stack(
        [
            np.asarray(rows[name], dtype=object)
            for name in CATEGORICAL_FEATURES
        ]
    )
    target = np.asarray(rows["target"], dtype=np.int8)
    return numeric, categorical, target


def _fit_quick_gbdt(
    train_rows: dict[str, np.ndarray],
    holdout_rows: dict[str, np.ndarray],
) -> dict[str, Any]:
    numeric_train, categorical_train, y_train = _feature_blocks(train_rows)
    numeric_holdout, categorical_holdout, y_holdout = _feature_blocks(holdout_rows)

    if y_train.sum() == 0 or y_holdout.sum() == 0:
        raise SignalProbeError("Probe sample contains no positive fraud labels.")

    encoder = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=np.nan,
        encoded_missing_value=np.nan,
        max_categories=255,
        min_frequency=20,
    )
    encoded_train = encoder.fit_transform(categorical_train)
    encoded_holdout = encoder.transform(categorical_holdout)
    x_train = np.concatenate([numeric_train, encoded_train], axis=1)
    x_holdout = np.concatenate([numeric_holdout, encoded_holdout], axis=1)

    categorical_mask = (
        [False] * len(NUMERIC_FEATURES)
        + [True] * len(CATEGORICAL_FEATURES)
    )
    model = HistGradientBoostingClassifier(
        learning_rate=0.08,
        max_iter=120,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        categorical_features=categorical_mask,
        class_weight="balanced",
        random_state=20260926,
    )
    model.fit(x_train, y_train)
    scores = model.predict_proba(x_holdout)[:, 1]

    prevalence = float(y_holdout.mean())
    pr_auc = float(average_precision_score(y_holdout, scores))
    roc_auc = float(roc_auc_score(y_holdout, scores))

    order = np.argsort(-scores, kind="stable")
    review_n = max(1, math.ceil(len(scores) * 0.005))
    reviewed = y_holdout[order[:review_n]]
    total_positive = int(y_holdout.sum())
    caught = int(reviewed.sum())
    recall = caught / total_positive if total_positive else 0.0
    precision = caught / review_n
    pr_auc_lift = pr_auc / prevalence if prevalence else None
    precision_lift = precision / prevalence if prevalence else None

    full_breadth = (
        total_positive >= FULL_FEATURE_MIN_POSITIVES
        and pr_auc_lift is not None
        and pr_auc_lift >= FULL_FEATURE_MIN_PR_AUC_LIFT
        and recall >= FULL_FEATURE_MIN_TOP_005_RECALL
    )

    return {
        "sample_modulus": SAMPLE_MODULUS,
        "sample_remainder": SAMPLE_REMAINDER,
        "train_rows": int(len(y_train)),
        "train_positive_rows": int(y_train.sum()),
        "holdout_rows": int(len(y_holdout)),
        "holdout_positive_rows": total_positive,
        "holdout_prevalence": prevalence,
        "pr_auc": pr_auc,
        "pr_auc_lift_over_prevalence": pr_auc_lift,
        "roc_auc": roc_auc,
        "top_0_5_percent_review_rows": review_n,
        "top_0_5_percent_fraud_caught": caught,
        "top_0_5_percent_recall": recall,
        "top_0_5_percent_precision": precision,
        "top_0_5_percent_precision_lift": precision_lift,
        "breadth_decision": "full" if full_breadth else "reduced",
        "breadth_rule": {
            "minimum_holdout_positive_rows": FULL_FEATURE_MIN_POSITIVES,
            "minimum_pr_auc_lift_over_prevalence": FULL_FEATURE_MIN_PR_AUC_LIFT,
            "minimum_top_0_5_percent_recall": FULL_FEATURE_MIN_TOP_005_RECALL,
        },
    }


def run_probe(
    *,
    database_path: Path,
    curated_manifest_path: Path,
    output_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    database_path = database_path.expanduser().resolve()
    curated_manifest_path = curated_manifest_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()

    if output_path.exists():
        raise SignalProbeError(
            f"Signal-probe result already exists: {output_path}. "
            "Do not overwrite a completed probe after observing its result."
        )

    implementation_commit = _git_identity(repo_root)

    if not database_path.is_file():
        raise FileNotFoundError(database_path)
    if not curated_manifest_path.is_file():
        raise FileNotFoundError(curated_manifest_path)

    manifest = json.loads(curated_manifest_path.read_text(encoding="utf-8"))
    database_sha = _sha256_file(database_path)
    if database_sha != manifest.get("database_sha256"):
        raise SignalProbeError("Curated database SHA-256 does not match its manifest.")

    con = duckdb.connect(
        str(database_path),
        read_only=True,
        config={"enable_external_access": "false"},
    )
    try:
        split = derive_splits(con)
        training = _training_profile(con, split)
        profiles = {
            "channel": _group_profile(con, split, "channel", "channel"),
            "transaction_type": _group_profile(
                con, split, "transaction_type", "transaction_type"
            ),
            "transaction_category": _group_profile(
                con, split, "transaction_category", "transaction_category"
            ),
            "merchant_category": _group_profile(
                con, split, "merchant_category", "merchant_category"
            ),
            "hour_of_day": _group_profile(
                con,
                split,
                "EXTRACT('hour' FROM transaction_date)",
                "hour_of_day",
                top_n=24,
            ),
            "day_of_week": _group_profile(
                con,
                split,
                "EXTRACT('dow' FROM transaction_date)",
                "day_of_week",
                top_n=7,
            ),
            "amount_deciles": _amount_deciles(con, split),
            "channel_novelty": _novelty_profile(con, split, "channel"),
            "merchant_category_novelty": _novelty_profile(
                con, split, "merchant_category"
            ),
            "transaction_country_novelty": _novelty_profile(
                con, split, "transaction_country"
            ),
        }
        train_rows = _model_rows(con, split, internal_train=True)
        holdout_rows = _model_rows(con, split, internal_train=False)
    finally:
        con.close()

    model_probe = _fit_quick_gbdt(train_rows, holdout_rows)

    result = {
        "probe_version": PROBE_VERSION,
        "implementation_commit": implementation_commit,
        "python_version": platform.python_version(),
        "duckdb_version": duckdb.__version__,
        "scikit_learn_version": sklearn_version,
        "curated_database_sha256": database_sha,
        "curated_manifest_sha256": _sha256_file(curated_manifest_path),
        "split": asdict(split),
        "training_profile": training,
        "profiles": profiles,
        "quick_intrinsic_gbdt": model_probe,
        "predictor_contract": {
            "numeric": NUMERIC_FEATURES,
            "categorical": CATEGORICAL_FEATURES,
            "target_only": "is_fraud",
            "explicitly_not_used": [
                "fraud_score",
                "transaction_status",
                "customer_country",
                "detected_accent",
                "customer_id",
                "product_id",
                "transaction_id",
                "current_balance",
                "last_updated",
                "last_transaction_date",
                "target_derived_history",
                "future_transactions",
                "future_labels",
            ],
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, output_path)
    return result


def _safe_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe_version": result["probe_version"],
        "implementation_commit": result["implementation_commit"],
        "python_version": result["python_version"],
        "duckdb_version": result["duckdb_version"],
        "scikit_learn_version": result["scikit_learn_version"],
        "curated_database_sha256": result["curated_database_sha256"],
        "curated_manifest_sha256": result["curated_manifest_sha256"],
        "split": result["split"],
        "training_profile": result["training_profile"],
        "quick_intrinsic_gbdt": result["quick_intrinsic_gbdt"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/curated/bank.duckdb")
    parser.add_argument(
        "--curated-manifest",
        default="data/curated/build_manifest.json",
    )
    parser.add_argument(
        "--output",
        default="ml/private/r4a_signal_probe.json",
    )
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    result = run_probe(
        database_path=Path(args.database),
        curated_manifest_path=Path(args.curated_manifest),
        output_path=Path(args.output),
        repo_root=Path(args.repo_root),
    )
    print("R4A TRAINING-ONLY SIGNAL PROBE COMPLETE")
    print(json.dumps(_safe_summary(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
