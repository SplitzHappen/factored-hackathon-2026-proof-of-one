from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import subprocess
import time
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import duckdb
import numpy as np
from scipy import sparse
from sklearn import __version__ as sklearn_version
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from ml.calibration_contract import (
    C_B_IMPLEMENTATION_COMMIT,
    C_B_RESULT_SHA256,
    CALIBRATION_CONTRACT_VERSION,
    LOGISTIC_CONVERGENCE_POLICY,
    PLATT_CALIBRATION_CONFIG,
    SELECTED_GBDT_ID,
    calibration_gate_contract_sha256,
    selected_gbdt_config,
)
from ml.evaluation_metrics import (
    behavioral_heuristic_scores,
    deterministic_tie_breaker,
    metric_contract_sha256,
    poisson_bootstrap_pr_auc_interval,
    prevalence_scores,
    primary_budget,
    probability_metrics,
    ranking_metrics,
    validation_gate_decision,
)
from ml.full_data_contract import MODEL_FEATURES, feature_contract_sha256
from ml.model_selection import (
    CATEGORICAL_MIN_FREQUENCY,
    LOGISTIC_CONFIG,
    MODEL_SELECTION_SEED,
)


CALIBRATION_GATE_VERSION = "factored-r4b-c-calibration-gate-run-v1"

CATEGORICAL_FEATURES = tuple(
    feature.name for feature in MODEL_FEATURES if feature.kind == "categorical"
)
NUMERIC_FEATURES = tuple(
    feature.name for feature in MODEL_FEATURES if feature.kind != "categorical"
)

ALLOWED_REFIT_SEGMENTS = ("train", "model_selection")
ALLOWED_GATE_SEGMENT = "calibration_gate"


class CalibrationGateError(RuntimeError):
    """Raised when C-C2 cannot execute under the frozen information boundary."""


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
        raise CalibrationGateError(
            "Refusing calibration-gate execution from a dirty Git working tree."
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
        raise CalibrationGateError("Could not resolve canonical Git commit.")
    return commit


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
        raise CalibrationGateError("Feature-contract SHA mismatch.")
    actual_sha = _sha256_file(feature_database_path)
    if manifest.get("artifact_database_sha256") != actual_sha:
        raise CalibrationGateError("Feature-artifact SHA mismatch.")
    if int(manifest.get("model_feature_count", -1)) != len(MODEL_FEATURES):
        raise CalibrationGateError("Feature-artifact model feature count mismatch.")
    return manifest


def _verify_c_b_result(
    path: Path,
    *,
    expected_sha256: str = C_B_RESULT_SHA256,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_sha = _sha256_file(path)
    if actual_sha != expected_sha256:
        raise CalibrationGateError(
            "Model-selection result SHA mismatch; refusing to continue from "
            "a noncanonical C-B result."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("implementation_commit") != C_B_IMPLEMENTATION_COMMIT:
        raise CalibrationGateError("C-B implementation commit mismatch.")
    selected = payload.get("selected_gbdt")
    if not isinstance(selected, dict) or selected.get("id") != SELECTED_GBDT_ID:
        raise CalibrationGateError("C-B selected GBDT does not match C-C contract.")
    if selected.get("config") != selected_gbdt_config():
        raise CalibrationGateError("C-B selected GBDT configuration mismatch.")
    return payload


def _filled(values: np.ndarray, fill_value: Any) -> np.ndarray:
    if np.ma.isMaskedArray(values):
        return np.asarray(values.filled(fill_value))
    return np.asarray(values)


def _load_segments(
    con: duckdb.DuckDBPyConnection,
    segments: Sequence[str],
    *,
    include_evaluation_fields: bool,
) -> SegmentArrays:
    requested = tuple(segments)
    allowed = {"train", "model_selection", "calibration_gate"}
    if not requested or any(segment not in allowed for segment in requested):
        raise CalibrationGateError(
            "C-C2 may load only train, model_selection, or calibration_gate; "
            "test is forbidden."
        )
    if "calibration_gate" in requested and len(requested) != 1:
        raise CalibrationGateError(
            "Calibration-gate rows must be loaded separately from refit rows."
        )
    if set(requested) == {"train", "model_selection"} and len(requested) != 2:
        raise CalibrationGateError("Refit segment set is invalid.")

    placeholders = ", ".join("?" for _ in requested)
    select_columns = [
        *([ "transaction_id" ] if include_evaluation_fields else []),
        "is_fraud",
        *NUMERIC_FEATURES,
        *CATEGORICAL_FEATURES,
    ]
    query = (
        "SELECT "
        + ", ".join(f'"{column}"' for column in select_columns)
        + f" FROM feature_rows WHERE segment IN ({placeholders}) "
        + "ORDER BY transaction_date, transaction_id"
    )
    data = con.execute(query, list(requested)).fetchnumpy()

    transaction_ids = (
        _filled(data["transaction_id"], "").astype(str)
        if include_evaluation_fields
        else np.empty(0, dtype=str)
    )
    y = _filled(data["is_fraud"], False).astype(np.int8)

    numeric = np.column_stack(
        [
            _filled(data[name], 0.0).astype(np.float32, copy=False)
            for name in NUMERIC_FEATURES
        ]
    ).astype(np.float32, copy=False)
    categorical = np.column_stack(
        [
            _filled(data[name], "__MISSING__").astype(object, copy=False)
            for name in CATEGORICAL_FEATURES
        ]
    ).astype(object, copy=False)

    heuristic_inputs = (
        {
            "amount_to_prior_currency_mean_ratio": _filled(
                data["amount_to_prior_currency_mean_ratio"], np.nan
            ).astype(np.float64, copy=False),
            "channel_novelty": _filled(
                data["channel_novelty"], False
            ).astype(bool, copy=False),
            "merchant_category_novelty": _filled(
                data["merchant_category_novelty"], False
            ).astype(bool, copy=False),
            "transaction_country_novelty": _filled(
                data["transaction_country_novelty"], False
            ).astype(bool, copy=False),
            "prior_24h_tx_count": _filled(
                data["prior_24h_tx_count"], 0
            ).astype(np.int64, copy=False),
            "prior_30d_tx_count": _filled(
                data["prior_30d_tx_count"], 0
            ).astype(np.int64, copy=False),
        }
        if include_evaluation_fields
        else {}
    )
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


def _ranking_payload(
    segment: SegmentArrays,
    scores: Iterable[float],
) -> tuple[Any, dict[str, Any]]:
    tie = deterministic_tie_breaker(segment.transaction_ids)
    metrics = ranking_metrics(segment.y, scores, tie_breaker=tie)
    return metrics, _serialize_ranking(metrics)


def _fit_logistic_refit(
    refit: SegmentArrays,
    gate: SegmentArrays,
) -> tuple[np.ndarray, dict[str, Any]]:
    scaler = StandardScaler()
    refit_numeric = scaler.fit_transform(refit.numeric).astype(np.float32, copy=False)
    gate_numeric = scaler.transform(gate.numeric).astype(np.float32, copy=False)

    encoder = OneHotEncoder(
        handle_unknown="ignore",
        min_frequency=CATEGORICAL_MIN_FREQUENCY,
        dtype=np.float32,
        sparse_output=True,
    )
    refit_cat = encoder.fit_transform(refit.categorical)
    gate_cat = encoder.transform(gate.categorical)

    x_refit = sparse.hstack(
        [sparse.csr_matrix(refit_numeric), refit_cat],
        format="csr",
        dtype=np.float32,
    )
    x_gate = sparse.hstack(
        [sparse.csr_matrix(gate_numeric), gate_cat],
        format="csr",
        dtype=np.float32,
    )

    model = SGDClassifier(**dict(LOGISTIC_CONFIG))
    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(x_refit, refit.y)
    fit_seconds = time.perf_counter() - started
    probabilities = model.predict_proba(x_gate)[:, 1].astype(np.float64, copy=False)
    convergence_messages = [
        str(item.message)
        for item in caught
        if issubclass(item.category, ConvergenceWarning)
    ]

    diagnostics = {
        "config": dict(LOGISTIC_CONFIG),
        "fit_seconds": fit_seconds,
        "encoded_feature_count": int(x_refit.shape[1]),
        "convergence_warning": bool(convergence_messages),
        "convergence_warning_messages": convergence_messages,
        "n_iter": [int(value) for value in np.atleast_1d(model.n_iter_)],
        "convergence_policy": dict(LOGISTIC_CONVERGENCE_POLICY),
    }

    del model, x_refit, x_gate, refit_numeric, gate_numeric
    del refit_cat, gate_cat, encoder, scaler
    gc.collect()
    return probabilities, diagnostics


def _fit_selected_gbdt_refit(
    refit: SegmentArrays,
    gate: SegmentArrays,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    ordinal = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=np.nan,
        encoded_missing_value=np.nan,
        min_frequency=CATEGORICAL_MIN_FREQUENCY,
        max_categories=255,
    )
    refit_cat = ordinal.fit_transform(refit.categorical).astype(np.float32, copy=False)
    gate_cat = ordinal.transform(gate.categorical).astype(np.float32, copy=False)

    x_refit = np.concatenate([refit.numeric, refit_cat], axis=1).astype(
        np.float32, copy=False
    )
    x_gate = np.concatenate([gate.numeric, gate_cat], axis=1).astype(
        np.float32, copy=False
    )

    categorical_mask = np.asarray(
        [False] * len(NUMERIC_FEATURES)
        + [True] * len(CATEGORICAL_FEATURES),
        dtype=bool,
    )
    config = selected_gbdt_config()
    estimator_config = dict(config)
    estimator_config.pop("id")
    model = HistGradientBoostingClassifier(
        **estimator_config,
        categorical_features=categorical_mask,
        class_weight="balanced",
        early_stopping=False,
        random_state=MODEL_SELECTION_SEED,
    )
    started = time.perf_counter()
    model.fit(x_refit, refit.y)
    fit_seconds = time.perf_counter() - started

    raw_scores = model.decision_function(x_gate).astype(np.float64, copy=False)
    raw_probabilities = model.predict_proba(x_gate)[:, 1].astype(
        np.float64, copy=False
    )
    diagnostics = {
        "id": SELECTED_GBDT_ID,
        "config": config,
        "fit_seconds": fit_seconds,
        "encoded_feature_count": int(x_refit.shape[1]),
    }

    del model, x_refit, x_gate, refit_cat, gate_cat, ordinal
    gc.collect()
    return raw_scores, raw_probabilities, diagnostics


def _fit_platt(
    raw_scores: np.ndarray,
    y: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    cfg = dict(PLATT_CALIBRATION_CONFIG)
    model = LogisticRegression(
        C=float(cfg["C"]),
        solver=str(cfg["solver"]),
        max_iter=int(cfg["max_iter"]),
        tol=float(cfg["tol"]),
        random_state=MODEL_SELECTION_SEED,
    )
    x = raw_scores.reshape(-1, 1)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(x, y)
    probabilities = model.predict_proba(x)[:, 1].astype(np.float64, copy=False)
    convergence_messages = [
        str(item.message)
        for item in caught
        if issubclass(item.category, ConvergenceWarning)
    ]
    diagnostics = {
        "config": cfg,
        "convergence_warning": bool(convergence_messages),
        "convergence_warning_messages": convergence_messages,
        "n_iter": [int(value) for value in np.atleast_1d(model.n_iter_)],
        "coefficient": float(model.coef_[0, 0]),
        "intercept": float(model.intercept_[0]),
    }
    del model, x
    gc.collect()
    return probabilities, diagnostics


def run_calibration_gate(
    *,
    feature_database_path: Path,
    feature_manifest_path: Path,
    model_selection_result_path: Path,
    output_path: Path,
    repo_root: Path,
    expected_c_b_sha256: str = C_B_RESULT_SHA256,
    bootstrap_iterations: int | None = None,
) -> dict[str, Any]:
    feature_database_path = feature_database_path.expanduser().resolve()
    feature_manifest_path = feature_manifest_path.expanduser().resolve()
    model_selection_result_path = model_selection_result_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()

    if output_path.exists():
        raise CalibrationGateError(
            f"Calibration-gate output already exists: {output_path}. "
            "Do not overwrite an observed gate result."
        )

    implementation_commit = _git_identity(repo_root)
    feature_manifest = _verify_feature_artifact(
        feature_database_path,
        feature_manifest_path,
    )
    c_b_result = _verify_c_b_result(
        model_selection_result_path,
        expected_sha256=expected_c_b_sha256,
    )

    con = duckdb.connect(
        str(feature_database_path),
        read_only=True,
        config={"enable_external_access": "false"},
    )
    try:
        refit = _load_segments(
            con,
            ALLOWED_REFIT_SEGMENTS,
            include_evaluation_fields=False,
        )
        gate = _load_segments(
            con,
            (ALLOWED_GATE_SEGMENT,),
            include_evaluation_fields=True,
        )
    finally:
        con.close()

    split = feature_manifest["split_plan"]
    expected_refit = int(split["train_rows"]) + int(split["model_selection_rows"])
    if len(refit.y) != expected_refit:
        raise CalibrationGateError("Refit row count disagrees with feature manifest.")
    if len(gate.y) != int(split["calibration_gate_rows"]):
        raise CalibrationGateError("Gate row count disagrees with feature manifest.")
    if int(refit.y.sum()) == 0 or int(gate.y.sum()) == 0:
        raise CalibrationGateError("Refit and gate segments must contain positive labels.")

    started = time.perf_counter()
    refit_prevalence = float(refit.y.mean())
    prevalence_scores_gate = prevalence_scores(refit_prevalence, len(gate.y))
    heuristic_scores_gate = behavioral_heuristic_scores(**gate.heuristic_inputs)

    prevalence_metrics, prevalence_payload = _ranking_payload(
        gate, prevalence_scores_gate
    )
    heuristic_metrics, heuristic_payload = _ranking_payload(
        gate, heuristic_scores_gate
    )

    logistic_scores, logistic_diagnostics = _fit_logistic_refit(refit, gate)
    logistic_metrics, logistic_payload = _ranking_payload(gate, logistic_scores)

    gbdt_raw_scores, gbdt_raw_probabilities, gbdt_diagnostics = (
        _fit_selected_gbdt_refit(refit, gate)
    )
    gbdt_metrics, gbdt_payload = _ranking_payload(gate, gbdt_raw_scores)

    interval_kwargs = (
        {}
        if bootstrap_iterations is None
        else {"iterations": int(bootstrap_iterations)}
    )
    gbdt_interval = poisson_bootstrap_pr_auc_interval(
        gate.y,
        gbdt_raw_scores,
        **interval_kwargs,
    )
    gate_decision = validation_gate_decision(
        gbdt_metrics=gbdt_metrics,
        gbdt_pr_auc_interval=gbdt_interval,
        non_gbdt_baseline_pr_aucs={
            "prevalence": prevalence_metrics.pr_auc,
            "behavioral_heuristic": heuristic_metrics.pr_auc,
            "regularized_logistic": logistic_metrics.pr_auc,
        },
    )

    calibrated_probabilities, calibration_diagnostics = _fit_platt(
        gbdt_raw_scores,
        gate.y,
    )
    raw_brier = probability_metrics(gate.y, gbdt_raw_probabilities)
    calibrated_brier = probability_metrics(gate.y, calibrated_probabilities)

    non_gbdt_points = {
        "prevalence": float(prevalence_metrics.pr_auc),
        "behavioral_heuristic": float(heuristic_metrics.pr_auc),
        "regularized_logistic": float(logistic_metrics.pr_auc),
    }
    best_non_gbdt_name = max(non_gbdt_points, key=non_gbdt_points.__getitem__)

    result = {
        "version": CALIBRATION_GATE_VERSION,
        "implementation_commit": implementation_commit,
        "python_version": platform.python_version(),
        "duckdb_version": duckdb.__version__,
        "scikit_learn_version": sklearn_version,
        "feature_artifact_sha256": feature_manifest["artifact_database_sha256"],
        "feature_manifest_sha256": _sha256_file(feature_manifest_path),
        "feature_contract_sha256": feature_contract_sha256(),
        "metric_contract_sha256": metric_contract_sha256(),
        "calibration_contract_version": CALIBRATION_CONTRACT_VERSION,
        "calibration_contract_sha256": calibration_gate_contract_sha256(),
        "c_b_result_sha256": _sha256_file(model_selection_result_path),
        "c_b_implementation_commit": c_b_result["implementation_commit"],
        "information_boundary": {
            "refit_segments": list(ALLOWED_REFIT_SEGMENTS),
            "gate_segment": ALLOWED_GATE_SEGMENT,
            "test_read": False,
        },
        "refit": {
            "rows": int(len(refit.y)),
            "positive_rows": int(refit.y.sum()),
            "prevalence": refit_prevalence,
        },
        "calibration_gate": {
            "rows": int(len(gate.y)),
            "positive_rows": int(gate.y.sum()),
            "prevalence": float(gate.y.mean()),
        },
        "baselines": {
            "prevalence": prevalence_payload,
            "behavioral_heuristic": heuristic_payload,
            "regularized_logistic": {
                **logistic_diagnostics,
                "gate": logistic_payload,
            },
            "best_non_gbdt": {
                "name": best_non_gbdt_name,
                "pr_auc": non_gbdt_points[best_non_gbdt_name],
            },
        },
        "selected_gbdt": {
            **gbdt_diagnostics,
            "gate": gbdt_payload,
            "pr_auc_bootstrap_95": asdict(gbdt_interval),
        },
        "calibration": {
            **calibration_diagnostics,
            "raw_probability_brier": raw_brier.brier_score,
            "platt_probability_brier_in_sample": calibrated_brier.brier_score,
            "diagnostic_scope": (
                "calibrator fit and Brier diagnostic use the same calibration_gate "
                "segment; not independent gate evidence"
            ),
        },
        "gate_decision": asdict(gate_decision),
        "test_authorized": bool(gate_decision.passed),
        "total_seconds": time.perf_counter() - started,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, output_path)

    del refit, gate, logistic_scores, gbdt_raw_scores
    del gbdt_raw_probabilities, calibrated_probabilities
    gc.collect()
    return result


def _safe_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": result["version"],
        "implementation_commit": result["implementation_commit"],
        "feature_artifact_sha256": result["feature_artifact_sha256"],
        "feature_manifest_sha256": result["feature_manifest_sha256"],
        "feature_contract_sha256": result["feature_contract_sha256"],
        "metric_contract_sha256": result["metric_contract_sha256"],
        "calibration_contract_sha256": result["calibration_contract_sha256"],
        "c_b_result_sha256": result["c_b_result_sha256"],
        "information_boundary": result["information_boundary"],
        "refit": result["refit"],
        "calibration_gate": result["calibration_gate"],
        "baselines": result["baselines"],
        "selected_gbdt": result["selected_gbdt"],
        "calibration": result["calibration"],
        "gate_decision": result["gate_decision"],
        "test_authorized": result["test_authorized"],
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
        "--model-selection-result",
        default="ml/private/r4b/model_selection.json",
    )
    parser.add_argument(
        "--output",
        default="ml/private/r4b/calibration_gate.json",
    )
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    result = run_calibration_gate(
        feature_database_path=Path(args.analytics),
        feature_manifest_path=Path(args.analytics_manifest),
        model_selection_result_path=Path(args.model_selection_result),
        output_path=Path(args.output),
        repo_root=Path(args.repo_root),
    )
    print("R4B-C CALIBRATION / USEFULNESS GATE COMPLETE")
    print(json.dumps(_safe_summary(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
