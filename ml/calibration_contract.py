from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from ml.evaluation_metrics import (
    METRIC_CONTRACT_VERSION,
    metric_contract_sha256,
)
from ml.full_data_contract import feature_contract_sha256
from ml.model_selection import (
    GBDT_CANDIDATES,
    LOGISTIC_CONFIG,
    MODEL_SELECTION_VERSION,
    model_selection_contract_sha256,
)


CALIBRATION_CONTRACT_VERSION = "factored-r4b-c-calibration-gate-v1"
SELECTED_GBDT_ID = "gbdt-small"

PLATT_CALIBRATION_CONFIG: dict[str, Any] = {
    "method": "platt_sigmoid",
    "input": "gbdt_decision_function",
    "implementation": "sklearn.linear_model.LogisticRegression",
    "solver": "lbfgs",
    "C": 1_000_000.0,
    "max_iter": 1000,
    "tol": 1e-8,
}

LOGISTIC_CONVERGENCE_POLICY: dict[str, Any] = {
    "configuration_is_frozen": True,
    "increase_max_iter_after_c_b": False,
    "capture_convergence_warning": True,
    "record_n_iter": True,
    "warning_excludes_baseline": False,
    "warning_triggers_retune": False,
}


class CalibrationContractError(RuntimeError):
    """Raised when the frozen C-C calibration contract cannot be resolved."""


def selected_gbdt_config() -> dict[str, Any]:
    matches = [
        dict(config)
        for config in GBDT_CANDIDATES
        if config.get("id") == SELECTED_GBDT_ID
    ]
    if len(matches) != 1:
        raise CalibrationContractError(
            f"Expected exactly one selected GBDT config for {SELECTED_GBDT_ID!r}."
        )
    return matches[0]


def calibration_gate_contract_dict() -> dict[str, Any]:
    return {
        "version": CALIBRATION_CONTRACT_VERSION,
        "upstream": {
            "model_selection_version": MODEL_SELECTION_VERSION,
            "metric_contract_version": METRIC_CONTRACT_VERSION,
            "feature_contract_sha256": feature_contract_sha256(),
            "metric_contract_sha256": metric_contract_sha256(),
            "model_selection_contract_sha256": model_selection_contract_sha256(),
        },
        "information_boundary": {
            "refit_segments": ["train", "model_selection"],
            "calibration_fit_segment": "calibration_gate",
            "gate_evaluation_segment": "calibration_gate",
            "forbidden": ["test"],
        },
        "refit": {
            "gbdt": {
                "selected_id": SELECTED_GBDT_ID,
                "config": selected_gbdt_config(),
                "information_set": ["train", "model_selection"],
            },
            "regularized_logistic": {
                "config": dict(LOGISTIC_CONFIG),
                "information_set": ["train", "model_selection"],
                "convergence_policy": dict(LOGISTIC_CONVERGENCE_POLICY),
            },
            "prevalence_baseline": {
                "prevalence_source": ["train", "model_selection"],
            },
            "behavioral_heuristic": {
                "target_free": True,
                "formula_source": "factored-r4b-c-metrics-v1",
            },
        },
        "calibration": {
            **dict(PLATT_CALIBRATION_CONFIG),
            "fit_only_on": "calibration_gate",
            "applied_to_test_only_if_gate_passes": True,
            "gate_ranking_uses_calibrated_probabilities": False,
            "gate_probability_diagnostics_are_in_sample": True,
            "gate_probability_diagnostics_are_gate_criteria": False,
        },
        "gate": {
            "ranking_score": "uncalibrated_gbdt_score",
            "gbdt_pr_auc_ci": "poisson-bootstrap-score-grouped-2000",
            "best_non_gbdt_baselines": [
                "prevalence",
                "behavioral_heuristic",
                "regularized_logistic",
            ],
            "criteria_source": "factored-r4b-c-metrics-v1",
            "all_checks_required": True,
        },
        "test_policy": {
            "test_may_be_loaded_in_c_c": False,
            "unseal_only_if_validation_gate_passes": True,
        },
    }


def calibration_gate_contract_sha256() -> str:
    payload = json.dumps(
        calibration_gate_contract_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def best_non_gbdt_pr_auc(
    *,
    prevalence_pr_auc: float,
    behavioral_heuristic_pr_auc: float,
    regularized_logistic_pr_auc: float,
) -> tuple[str, float]:
    values: Mapping[str, float] = {
        "prevalence": float(prevalence_pr_auc),
        "behavioral_heuristic": float(behavioral_heuristic_pr_auc),
        "regularized_logistic": float(regularized_logistic_pr_auc),
    }
    name = max(values, key=values.__getitem__)
    return name, values[name]
