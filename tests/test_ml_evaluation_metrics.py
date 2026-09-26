from __future__ import annotations

import math

import numpy as np
import pytest
from sklearn.metrics import average_precision_score

from ml.evaluation_metrics import (
    METRIC_CONTRACT_VERSION,
    PRIMARY_REVIEW_BUDGET,
    behavioral_heuristic_scores,
    deterministic_tie_breaker,
    metric_contract_dict,
    metric_contract_sha256,
    poisson_bootstrap_pr_auc_interval,
    prevalence_scores,
    primary_budget,
    probability_metrics,
    ranking_metrics,
    test_survival_decision,
    validation_gate_decision,
)


def test_behavioral_heuristic_is_frozen_bounded_and_target_free() -> None:
    scores = behavioral_heuristic_scores(
        amount_to_prior_currency_mean_ratio=[None, 1.0, 2.0, 8.0, 16.0],
        channel_novelty=[False, False, True, True, True],
        merchant_category_novelty=[False, True, False, True, True],
        transaction_country_novelty=[False, False, False, True, True],
        prior_24h_tx_count=[0, 1, 2, 5, 100],
        prior_30d_tx_count=[0, 2, 5, 20, 100],
    )

    assert len(scores) == 5
    assert np.all(scores >= 0.0)
    assert np.all(scores <= 1.0)
    assert scores[0] == 0.0
    assert scores[-1] == pytest.approx(1.0)
    assert np.all(np.diff(scores) >= 0.0)


def test_prevalence_baseline_is_constant_training_prevalence() -> None:
    scores = prevalence_scores(0.001, 4)
    assert scores.tolist() == [0.001] * 4


def test_review_budget_uses_exact_target_blind_tie_breaker() -> None:
    y = [1, 0, 1, 0, 0, 0, 0, 0, 0, 0]
    scores = [0.5] * 10
    transaction_ids = [f"T{i}" for i in range(10)]
    tie = deterministic_tie_breaker(transaction_ids)

    metrics = ranking_metrics(
        y,
        scores,
        tie_breaker=tie,
        budgets=(0.2,),
    )

    order = np.lexsort((tie, -np.asarray(scores)))
    expected_caught = int(np.asarray(y)[order[:2]].sum())
    budget = metrics.budgets[0]
    assert budget.review_rows == 2
    assert budget.fraud_caught == expected_caught


def test_ranking_metrics_match_sklearn_pr_auc_and_budget_math() -> None:
    y = [1, 0, 1, 0, 0, 1, 0, 0]
    scores = [0.9, 0.8, 0.7, 0.3, 0.2, 0.6, 0.1, 0.05]
    tie = np.arange(len(y), dtype=np.uint64)

    metrics = ranking_metrics(
        y,
        scores,
        tie_breaker=tie,
        budgets=(0.5,),
    )

    assert metrics.pr_auc == pytest.approx(average_precision_score(y, scores))
    assert metrics.positive_rows == 3
    assert metrics.prevalence == pytest.approx(3 / 8)
    budget = metrics.budgets[0]
    assert budget.review_rows == 4
    assert budget.fraud_caught == 3
    assert budget.recall == 1.0
    assert budget.precision == pytest.approx(0.75)
    assert budget.precision_lift == pytest.approx(2.0)
    assert budget.false_positives_per_detected_fraud == pytest.approx(1 / 3)


def test_probability_metric_requires_probability_range() -> None:
    metric = probability_metrics([1, 0], [0.8, 0.2])
    assert metric.brier_score == pytest.approx(0.04)

    with pytest.raises(ValueError, match="probabilities"):
        probability_metrics([1, 0], [1.2, -0.1])


def test_poisson_bootstrap_is_reproducible_and_contains_point_for_strong_signal() -> None:
    y = np.array([1] * 20 + [0] * 180, dtype=np.int8)
    scores = np.r_[np.linspace(1.0, 0.8, 20), np.linspace(0.7, 0.0, 180)]

    first = poisson_bootstrap_pr_auc_interval(
        y,
        scores,
        iterations=200,
        seed=123,
    )
    second = poisson_bootstrap_pr_auc_interval(
        y,
        scores,
        iterations=200,
        seed=123,
    )

    assert first == second
    assert first.lower_95 <= first.point_estimate <= first.upper_95
    assert first.point_estimate == pytest.approx(1.0)
    assert first.method == "poisson-bootstrap-score-grouped"


def test_bootstrap_tie_group_point_matches_sklearn() -> None:
    y = [1, 0, 1, 0, 0, 1]
    scores = [0.8, 0.8, 0.4, 0.4, 0.1, 0.1]

    interval = poisson_bootstrap_pr_auc_interval(
        y,
        scores,
        iterations=200,
        seed=9,
    )

    assert interval.point_estimate == pytest.approx(
        average_precision_score(y, scores)
    )


def _gate_metrics(*, recall: float, lift: float, pr_auc: float):
    rows = 1000
    prevalence = 0.01
    positives = 10
    review_rows = math.ceil(rows * PRIMARY_REVIEW_BUDGET)
    from ml.evaluation_metrics import RankingMetrics, ReviewBudgetMetrics

    budget = ReviewBudgetMetrics(
        budget_fraction=PRIMARY_REVIEW_BUDGET,
        review_rows=review_rows,
        fraud_caught=max(1, round(recall * positives)),
        false_positives=max(0, review_rows - max(1, round(recall * positives))),
        recall=recall,
        precision=prevalence * lift,
        precision_lift=lift,
        false_positives_per_detected_fraud=1.0,
    )
    return RankingMetrics(
        rows=rows,
        positive_rows=positives,
        prevalence=prevalence,
        pr_auc=pr_auc,
        roc_auc=0.8,
        budgets=(budget,),
    )


def test_validation_gate_requires_all_three_frozen_conditions() -> None:
    from ml.evaluation_metrics import BootstrapInterval

    metrics = _gate_metrics(recall=0.06, lift=12.0, pr_auc=0.20)
    interval = BootstrapInterval(
        point_estimate=0.20,
        lower_95=0.15,
        upper_95=0.25,
        iterations=2000,
        method="poisson-bootstrap-score-grouped",
        seed=20260926,
    )
    passed = validation_gate_decision(
        gbdt_metrics=metrics,
        gbdt_pr_auc_interval=interval,
        non_gbdt_baseline_pr_aucs={
            "prevalence": 0.01,
            "heuristic": 0.05,
            "logistic": 0.10,
        },
    )
    assert passed.passed is True

    failed = validation_gate_decision(
        gbdt_metrics=_gate_metrics(recall=0.049, lift=12.0, pr_auc=0.20),
        gbdt_pr_auc_interval=interval,
        non_gbdt_baseline_pr_aucs={"logistic": 0.10},
    )
    assert failed.passed is False
    assert (
        failed.checks["top_0_5_recall_at_least_5_percent"]
        is False
    )


def test_test_survival_requires_all_frozen_conditions() -> None:
    good = test_survival_decision(
        test_gbdt_metrics=_gate_metrics(recall=0.03, lift=6.0, pr_auc=0.12),
        gate_gbdt_pr_auc=0.20,
        test_non_gbdt_baseline_pr_aucs={"logistic": 0.08},
    )
    assert good.passed is True

    bad = test_survival_decision(
        test_gbdt_metrics=_gate_metrics(recall=0.03, lift=6.0, pr_auc=0.09),
        gate_gbdt_pr_auc=0.20,
        test_non_gbdt_baseline_pr_aucs={"logistic": 0.08},
    )
    assert bad.passed is False
    assert bad.checks["test_pr_auc_at_least_half_gate_pr_auc"] is False


def test_metric_contract_is_hashed_and_matches_audited_thresholds() -> None:
    contract = metric_contract_dict()
    assert contract["contract_version"] == METRIC_CONTRACT_VERSION
    assert contract["validation_gate"]["top_0_5_recall_min"] == 0.05
    assert contract["validation_gate"]["top_0_5_precision_lift_min"] == 10.0
    assert contract["test_survival"]["pr_auc_min_fraction_of_gate"] == 0.50
    assert contract["test_survival"]["top_0_5_recall_min"] == 0.025
    assert contract["test_survival"]["top_0_5_precision_lift_min"] == 5.0

    first = metric_contract_sha256()
    second = metric_contract_sha256()
    assert first == second
    assert len(first) == 64
    assert set(first) <= set("0123456789abcdef")
