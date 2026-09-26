from __future__ import annotations

from ml.calibration_contract import (
    CALIBRATION_CONTRACT_VERSION,
    LOGISTIC_CONVERGENCE_POLICY,
    SELECTED_GBDT_ID,
    best_non_gbdt_pr_auc,
    calibration_gate_contract_dict,
    calibration_gate_contract_sha256,
    selected_gbdt_config,
)


def test_c_c_contract_keeps_test_sealed() -> None:
    contract = calibration_gate_contract_dict()

    assert contract["version"] == CALIBRATION_CONTRACT_VERSION
    assert contract["information_boundary"] == {
        "refit_segments": ["train", "model_selection"],
        "calibration_fit_segment": "calibration_gate",
        "gate_evaluation_segment": "calibration_gate",
        "forbidden": ["test"],
    }
    assert contract["test_policy"]["test_may_be_loaded_in_c_c"] is False
    assert contract["test_policy"]["unseal_only_if_validation_gate_passes"] is True


def test_symmetric_refit_is_frozen() -> None:
    contract = calibration_gate_contract_dict()

    assert contract["refit"]["gbdt"]["information_set"] == [
        "train",
        "model_selection",
    ]
    assert contract["refit"]["regularized_logistic"]["information_set"] == [
        "train",
        "model_selection",
    ]
    assert contract["refit"]["prevalence_baseline"]["prevalence_source"] == [
        "train",
        "model_selection",
    ]


def test_selected_gbdt_is_exact_c_b_winner() -> None:
    config = selected_gbdt_config()

    assert SELECTED_GBDT_ID == "gbdt-small"
    assert config == {
        "id": "gbdt-small",
        "learning_rate": 0.08,
        "max_iter": 120,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 100,
        "l2_regularization": 1.0,
    }


def test_calibration_cannot_change_gate_ranking_semantics() -> None:
    calibration = calibration_gate_contract_dict()["calibration"]
    gate = calibration_gate_contract_dict()["gate"]

    assert calibration["method"] == "platt_sigmoid"
    assert calibration["fit_only_on"] == "calibration_gate"
    assert calibration["gate_ranking_uses_calibrated_probabilities"] is False
    assert calibration["gate_probability_diagnostics_are_gate_criteria"] is False
    assert gate["ranking_score"] == "uncalibrated_gbdt_score"


def test_logistic_warning_is_diagnostic_not_retuning_permission() -> None:
    policy = LOGISTIC_CONVERGENCE_POLICY

    assert policy["configuration_is_frozen"] is True
    assert policy["increase_max_iter_after_c_b"] is False
    assert policy["capture_convergence_warning"] is True
    assert policy["record_n_iter"] is True
    assert policy["warning_excludes_baseline"] is False
    assert policy["warning_triggers_retune"] is False


def test_best_non_gbdt_uses_strongest_comparator() -> None:
    name, value = best_non_gbdt_pr_auc(
        prevalence_pr_auc=0.0010,
        behavioral_heuristic_pr_auc=0.0012,
        regularized_logistic_pr_auc=0.0008,
    )

    assert name == "behavioral_heuristic"
    assert value == 0.0012


def test_calibration_contract_hash_is_stable() -> None:
    first = calibration_gate_contract_sha256()
    second = calibration_gate_contract_sha256()

    assert first == second
    assert len(first) == 64
    assert set(first) <= set("0123456789abcdef")
