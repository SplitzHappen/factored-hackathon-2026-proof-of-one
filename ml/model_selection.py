from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import platform
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import duckdb
import numpy as np
from scipy import sparse
from sklearn import __version__ as sklearn_version
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from ml.evaluation_metrics import (
    behavioral_heuristic_scores,
    deterministic_tie_breaker,
    metric_contract_sha256,
    prevalence_scores,
    primary_budget,
    ranking_metrics,
)
from ml.full_data_contract import (
    MODEL_FEATURES,
    feature_contract_sha256,
)


MODEL_SELECTION_VERSION = "factored-r4b-c-model-selection-v1"
MODEL_SELECTION_SEED = 20260926
CATEGORICAL_MIN_FREQUENCY = 50

CATEGORICAL_FEATURES = tuple(
    feature.name for feature in MODEL_FEATURES if feature.kind == "categorical"
)
NUMERIC_FEATURES = tuple(
    feature.name for feature in MODEL_FEATURES if feature.kind != "categorical"
)

LOGISTIC_CONFIG = {
    "loss": "log_loss",
    "penalty": "l2",
    "alpha": 1e-4,
    "class_weight": "balanced",
    "max_iter": 40,
    "tol": 1e-4,
    "average": True,
    "random_state": MODEL_SELECTION_SEED,
}

GBDT_CANDIDATES: tuple[dict[str, Any], ...] = (
    {
        "id": "gbdt-small",
        "learning_rate": 0.08,
        "max_iter": 120,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 100,
        "l2_regularization": 1.0,
    },
    {
        "id": "gbdt-medium",
        "learning_rate": 0.06,
        "max_iter": 160,
        "max_leaf_nodes": 31,
        "min_samples_leaf": 100,
        "l2_regularization": 1.0,
    },
    {
        "id": "gbdt-regularized",
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 31,
        "min_samples_leaf": 200,
        "l2_regularization": 5.0,
    },
)


class ModelSelectionError(RuntimeError):
    """Raised when C-B cannot execute under its frozen information boundary."""


@dataclass(frozen=True, slots=True)
class SegmentArrays:
    transaction_ids: np.ndarray
    y: np.ndarray
    numeric: np.ndarray
    categorical: np.ndarray
    heuristic_inputs: Mapping[str, np.ndarray]


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
        raise ModelSelectionError(
            "Refusing model selection from a dirty Git working tree."
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
        raise ModelSelectionError("Could not resolve canonical Git commit.")
    return commit


def model_selection_contract_dict(
    candidate_configs: Sequence[Mapping[str, Any]] = GBDT_CANDIDATES,
) -> dict[str, Any]:
    return {
        "version": MODEL_SELECTION_VERSION,
        "seed": MODEL_SELECTION_SEED,
        "information_boundary": {
            "fit": ["train"],
            "select": ["model_selection"],
            "forbidden": ["calibration_gate", "test"],
        },
        "categorical_min_frequency": CATEGORICAL_MIN_FREQUENCY,
        "logistic_config": LOGISTIC_CONFIG,
        "gbdt_candidates": [dict(config) for config in candidate_configs],
        "gbdt_selection_rule": (
            "highest model-selection PR-AUC; exact ties retain earlier "
            "candidate order, which is ordered simplest-to-more-complex"
        ),
        "feature_contract_sha256": feature_contract_sha256(),
        "metric_contract_sha256": metric_contract_sha256(),
        "numeric_features": list(NUMERIC_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "gbdt_implementation": "sklearn.HistGradientBoostingClassifier",
        "logistic_implementation": "sklearn.SGDClassifier(loss=log_loss)",
    }


def model_selection_contract_sha256(
    candidate_configs: Sequence[Mapping[str, Any]] = GBDT_CANDIDATES,
) -> str:
    payload = json.dumps(
        model_selection_contract_dict(candidate_configs),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _verify_feature_artifact(
    feature_database_path: Path,
    feature_manifest_path: Path,
) -> dict[str, Any]:
    if not feature_database_path.is_file():
        raise FileNotFoundError(feature_database_path)
    if not feature_manifest_path.is_file():
        raise FileNotFoundError(feature_manifest_path)

    manifest = json.loads(feature_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("contract_sha256") != feature_contract_sha256():
        raise ModelSelectionError("Feature-contract SHA mismatch.")
    actual_sha = _sha256_file(feature_database_path)
    if manifest.get("artifact_database_sha256") != actual_sha:
        raise ModelSelectionError("Feature-artifact SHA mismatch.")
    if int(manifest.get("model_feature_count", -1)) != len(MODEL_FEATURES):
        raise ModelSelectionError("Feature-artifact model feature count mismatch.")
    return manifest


def _filled(values: np.ndarray, fill_value: Any) -> np.ndarray:
    if np.ma.isMaskedArray(values):
        return np.asarray(values.filled(fill_value))
    return np.asarray(values)


def _load_segment(
    con: duckdb.DuckDBPyConnection,
    segment: str,
) -> SegmentArrays:
    if segment not in {"train", "model_selection"}:
        raise ModelSelectionError(
            "C-B may load only train or model_selection segments."
        )

    select_columns = [
        "transaction_id",
        "is_fraud",
        *NUMERIC_FEATURES,
        *CATEGORICAL_FEATURES,
    ]
    query = (
        "SELECT "
        + ", ".join(f'"{column}"' for column in select_columns)
        + " FROM feature_rows WHERE segment = ? "
        + "ORDER BY transaction_date, transaction_id"
    )
    data = con.execute(query, [segment]).fetchnumpy()

    transaction_ids = _filled(data["transaction_id"], "").astype(str)
    y = _filled(data["is_fraud"], False).astype(np.int8)

    numeric_columns: list[np.ndarray] = []
    for name in NUMERIC_FEATURES:
        values = _filled(data[name], 0.0).astype(np.float32, copy=False)
        numeric_columns.append(values)
    numeric = np.column_stack(numeric_columns).astype(np.float32, copy=False)

    categorical_columns: list[np.ndarray] = []
    for name in CATEGORICAL_FEATURES:
        values = _filled(data[name], "__MISSING__").astype(object, copy=False)
        categorical_columns.append(values)
    categorical = np.column_stack(categorical_columns).astype(object, copy=False)

    heuristic_inputs = {
        "amount_to_prior_currency_mean_ratio": _filled(
            data["amount_to_prior_currency_mean_ratio"],
            np.nan,
        ).astype(np.float64, copy=False),
        "channel_novelty": _filled(
            data["channel_novelty"],
            False,
        ).astype(bool, copy=False),
        "merchant_category_novelty": _filled(
            data["merchant_category_novelty"],
            False,
        ).astype(bool, copy=False),
        "transaction_country_novelty": _filled(
            data["transaction_country_novelty"],
            False,
        ).astype(bool, copy=False),
        "prior_24h_tx_count": _filled(
            data["prior_24h_tx_count"],
            0,
        ).astype(np.int64, copy=False),
        "prior_30d_tx_count": _filled(
            data["prior_30d_tx_count"],
            0,
        ).astype(np.int64, copy=False),
    }
    return SegmentArrays(
        transaction_ids=transaction_ids,
        y=y,
        numeric=numeric,
        categorical=categorical,
        heuristic_inputs=heuristic_inputs,
    )


def _serialize_ranking(metrics) -> dict[str, Any]:
    payload = asdict(metrics)
    payload["primary_budget"] = asdict(primary_budget(metrics))
    return payload


def _selection_metrics(
    segment: SegmentArrays,
    scores: Iterable[float],
) -> dict[str, Any]:
    tie = deterministic_tie_breaker(segment.transaction_ids)
    return _serialize_ranking(
        ranking_metrics(segment.y, scores, tie_breaker=tie)
    )


def _fit_logistic(
    train: SegmentArrays,
    selection: SegmentArrays,
    *,
    config: Mapping[str, Any] = LOGISTIC_CONFIG,
) -> dict[str, Any]:
    scaler = StandardScaler()
    train_numeric = scaler.fit_transform(train.numeric).astype(np.float32, copy=False)
    selection_numeric = scaler.transform(selection.numeric).astype(np.float32, copy=False)

    encoder = OneHotEncoder(
        handle_unknown="ignore",
        min_frequency=CATEGORICAL_MIN_FREQUENCY,
        dtype=np.float32,
        sparse_output=True,
    )
    train_cat = encoder.fit_transform(train.categorical)
    selection_cat = encoder.transform(selection.categorical)

    x_train = sparse.hstack(
        [sparse.csr_matrix(train_numeric), train_cat],
        format="csr",
        dtype=np.float32,
    )
    x_selection = sparse.hstack(
        [sparse.csr_matrix(selection_numeric), selection_cat],
        format="csr",
        dtype=np.float32,
    )

    model = SGDClassifier(**dict(config))
    started = time.perf_counter()
    model.fit(x_train, train.y)
    fit_seconds = time.perf_counter() - started
    probabilities = model.predict_proba(x_selection)[:, 1]

    result = {
        "config": dict(config),
        "fit_seconds": fit_seconds,
        "encoded_feature_count": int(x_train.shape[1]),
        "selection": _selection_metrics(selection, probabilities),
    }

    del model, x_train, x_selection, train_numeric, selection_numeric
    del train_cat, selection_cat, encoder, scaler, probabilities
    gc.collect()
    return result


def _fit_gbdt_candidates(
    train: SegmentArrays,
    selection: SegmentArrays,
    *,
    candidate_configs: Sequence[Mapping[str, Any]] = GBDT_CANDIDATES,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ordinal = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=np.nan,
        encoded_missing_value=np.nan,
        min_frequency=CATEGORICAL_MIN_FREQUENCY,
        max_categories=255,
    )
    train_cat = ordinal.fit_transform(train.categorical).astype(np.float32, copy=False)
    selection_cat = ordinal.transform(selection.categorical).astype(
        np.float32,
        copy=False,
    )

    x_train = np.concatenate([train.numeric, train_cat], axis=1).astype(
        np.float32,
        copy=False,
    )
    x_selection = np.concatenate(
        [selection.numeric, selection_cat],
        axis=1,
    ).astype(np.float32, copy=False)

    categorical_mask = np.asarray(
        [False] * len(NUMERIC_FEATURES)
        + [True] * len(CATEGORICAL_FEATURES),
        dtype=bool,
    )

    results: list[dict[str, Any]] = []
    best_index = 0
    best_pr_auc = -math.inf

    for index, raw_config in enumerate(candidate_configs):
        config = dict(raw_config)
        candidate_id = str(config.pop("id"))
        model = HistGradientBoostingClassifier(
            **config,
            categorical_features=categorical_mask,
            class_weight="balanced",
            early_stopping=False,
            random_state=MODEL_SELECTION_SEED,
        )
        started = time.perf_counter()
        model.fit(x_train, train.y)
        fit_seconds = time.perf_counter() - started
        probabilities = model.predict_proba(x_selection)[:, 1]
        metrics = _selection_metrics(selection, probabilities)

        result = {
            "id": candidate_id,
            "config": dict(raw_config),
            "fit_seconds": fit_seconds,
            "selection": metrics,
        }
        results.append(result)
        pr_auc = float(metrics["pr_auc"])
        if pr_auc > best_pr_auc:
            best_pr_auc = pr_auc
            best_index = index

        del model, probabilities
        gc.collect()

    selected = results[best_index]
    del x_train, x_selection, train_cat, selection_cat, ordinal
    gc.collect()
    return results, selected


def _target_free_baselines(
    train: SegmentArrays,
    selection: SegmentArrays,
) -> dict[str, Any]:
    train_prevalence = float(train.y.mean())
    prevalence = prevalence_scores(train_prevalence, len(selection.y))
    heuristic = behavioral_heuristic_scores(**selection.heuristic_inputs)
    return {
        "training_prevalence": train_prevalence,
        "prevalence": _selection_metrics(selection, prevalence),
        "behavioral_heuristic": _selection_metrics(selection, heuristic),
    }


def run_model_selection(
    *,
    feature_database_path: Path,
    feature_manifest_path: Path,
    output_path: Path,
    repo_root: Path,
    candidate_configs: Sequence[Mapping[str, Any]] = GBDT_CANDIDATES,
    logistic_config: Mapping[str, Any] = LOGISTIC_CONFIG,
) -> dict[str, Any]:
    feature_database_path = feature_database_path.expanduser().resolve()
    feature_manifest_path = feature_manifest_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()

    if output_path.exists():
        raise ModelSelectionError(
            f"Model-selection output already exists: {output_path}. "
            "Do not overwrite observed selection results."
        )

    implementation_commit = _git_identity(repo_root)
    feature_manifest = _verify_feature_artifact(
        feature_database_path,
        feature_manifest_path,
    )

    con = duckdb.connect(
        str(feature_database_path),
        read_only=True,
        config={"enable_external_access": "false"},
    )
    try:
        train = _load_segment(con, "train")
        selection = _load_segment(con, "model_selection")
    finally:
        con.close()

    if len(train.y) != int(feature_manifest["split_plan"]["train_rows"]):
        raise ModelSelectionError("Training-row count disagrees with feature manifest.")
    if len(selection.y) != int(
        feature_manifest["split_plan"]["model_selection_rows"]
    ):
        raise ModelSelectionError(
            "Model-selection row count disagrees with feature manifest."
        )

    started = time.perf_counter()
    baselines = _target_free_baselines(train, selection)
    logistic = _fit_logistic(
        train,
        selection,
        config=logistic_config,
    )
    gbdt_candidates, selected_gbdt = _fit_gbdt_candidates(
        train,
        selection,
        candidate_configs=candidate_configs,
    )

    result = {
        "version": MODEL_SELECTION_VERSION,
        "implementation_commit": implementation_commit,
        "python_version": platform.python_version(),
        "duckdb_version": duckdb.__version__,
        "scikit_learn_version": sklearn_version,
        "feature_artifact_sha256": feature_manifest["artifact_database_sha256"],
        "feature_contract_sha256": feature_contract_sha256(),
        "metric_contract_sha256": metric_contract_sha256(),
        "model_selection_contract_sha256": model_selection_contract_sha256(
            candidate_configs
        ),
        "information_boundary": {
            "fit_segment": "train",
            "selection_segment": "model_selection",
            "calibration_gate_read": False,
            "test_read": False,
        },
        "train": {
            "rows": int(len(train.y)),
            "positive_rows": int(train.y.sum()),
            "prevalence": float(train.y.mean()),
        },
        "model_selection": {
            "rows": int(len(selection.y)),
            "positive_rows": int(selection.y.sum()),
            "prevalence": float(selection.y.mean()),
        },
        "baselines": baselines,
        "logistic": logistic,
        "gbdt_candidates": gbdt_candidates,
        "selected_gbdt": {
            "id": selected_gbdt["id"],
            "config": selected_gbdt["config"],
            "selection_pr_auc": selected_gbdt["selection"]["pr_auc"],
        },
        "total_seconds": time.perf_counter() - started,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, output_path)
    return result


def _safe_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": result["version"],
        "implementation_commit": result["implementation_commit"],
        "feature_artifact_sha256": result["feature_artifact_sha256"],
        "feature_contract_sha256": result["feature_contract_sha256"],
        "metric_contract_sha256": result["metric_contract_sha256"],
        "model_selection_contract_sha256": result[
            "model_selection_contract_sha256"
        ],
        "information_boundary": result["information_boundary"],
        "train": result["train"],
        "model_selection": result["model_selection"],
        "baselines": result["baselines"],
        "logistic": result["logistic"],
        "gbdt_candidates": result["gbdt_candidates"],
        "selected_gbdt": result["selected_gbdt"],
        "total_seconds": result["total_seconds"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--analytics",
        default="ml/private/r4b/analytics.duckdb",
    )
    parser.add_argument(
        "--analytics-manifest",
        default="ml/private/r4b/analytics_manifest.json",
    )
    parser.add_argument(
        "--output",
        default="ml/private/r4b/model_selection.json",
    )
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    result = run_model_selection(
        feature_database_path=Path(args.analytics),
        feature_manifest_path=Path(args.analytics_manifest),
        output_path=Path(args.output),
        repo_root=Path(args.repo_root),
    )
    print("R4B-C MODEL SELECTION COMPLETE")
    print(json.dumps(_safe_summary(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
