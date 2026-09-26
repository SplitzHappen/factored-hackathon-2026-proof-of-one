from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


METRIC_CONTRACT_VERSION = "factored-r4b-c-metrics-v1"
REVIEW_BUDGETS = (0.001, 0.005, 0.01)
PRIMARY_REVIEW_BUDGET = 0.005
POISSON_BOOTSTRAP_ITERATIONS = 2000
POISSON_BOOTSTRAP_SEED = 20260926

VALIDATION_MIN_TOP_005_RECALL = 0.05
VALIDATION_MIN_TOP_005_PRECISION_LIFT = 10.0

TEST_MIN_GATE_PR_AUC_RATIO = 0.50
TEST_MIN_TOP_005_RECALL = 0.025
TEST_MIN_TOP_005_PRECISION_LIFT = 5.0


@dataclass(frozen=True, slots=True)
class ReviewBudgetMetrics:
    budget_fraction: float
    review_rows: int
    fraud_caught: int
    false_positives: int
    recall: float
    precision: float
    precision_lift: float | None
    false_positives_per_detected_fraud: float | None


@dataclass(frozen=True, slots=True)
class RankingMetrics:
    rows: int
    positive_rows: int
    prevalence: float
    pr_auc: float
    roc_auc: float | None
    budgets: tuple[ReviewBudgetMetrics, ...]


@dataclass(frozen=True, slots=True)
class ProbabilityMetrics:
    brier_score: float


@dataclass(frozen=True, slots=True)
class BootstrapInterval:
    point_estimate: float
    lower_95: float
    upper_95: float
    iterations: int
    method: str
    seed: int


@dataclass(frozen=True, slots=True)
class GateDecision:
    passed: bool
    checks: Mapping[str, bool]
    values: Mapping[str, float]


def _as_binary(y_true: Iterable[int | bool]) -> np.ndarray:
    y = np.asarray(list(y_true), dtype=np.int8)
    if y.ndim != 1:
        raise ValueError("y_true must be one-dimensional")
    if len(y) == 0:
        raise ValueError("y_true must be nonempty")
    unique = set(np.unique(y).tolist())
    if not unique.issubset({0, 1}):
        raise ValueError("y_true must contain only 0/1 values")
    return y


def _as_scores(scores: Iterable[float], n: int) -> np.ndarray:
    values = np.asarray(list(scores), dtype=np.float64)
    if values.ndim != 1 or len(values) != n:
        raise ValueError("scores must be one-dimensional and match y_true")
    if not np.all(np.isfinite(values)):
        raise ValueError("scores must be finite")
    return values


def deterministic_tie_breaker(transaction_ids: Iterable[str]) -> np.ndarray:
    """Stable target-blind tie breaker derived only from opaque row identity."""

    values: list[int] = []
    for transaction_id in transaction_ids:
        digest = hashlib.blake2b(
            (str(transaction_id) + "|proof-of-one-eval-tie-v1").encode("utf-8"),
            digest_size=8,
        ).digest()
        values.append(int.from_bytes(digest, "big", signed=False))
    return np.asarray(values, dtype=np.uint64)


def prevalence_scores(train_prevalence: float, rows: int) -> np.ndarray:
    if not (0.0 <= train_prevalence <= 1.0):
        raise ValueError("train_prevalence must be in [0, 1]")
    if rows <= 0:
        raise ValueError("rows must be positive")
    return np.full(rows, train_prevalence, dtype=np.float64)


def behavioral_heuristic_scores(
    *,
    amount_to_prior_currency_mean_ratio: Iterable[float | None],
    channel_novelty: Iterable[bool],
    merchant_category_novelty: Iterable[bool],
    transaction_country_novelty: Iterable[bool],
    prior_24h_tx_count: Iterable[int],
    prior_30d_tx_count: Iterable[int],
) -> np.ndarray:
    """Frozen target-free behavioral heuristic in [0, 1].

    Weights sum to 1.0:
      0.35 amount surprise
      0.15 channel novelty
      0.10 merchant-category novelty
      0.15 transaction-country novelty
      0.15 24h velocity
      0.10 30d velocity
    """

    ratio_raw = np.asarray(
        [np.nan if value is None else float(value) for value in amount_to_prior_currency_mean_ratio],
        dtype=np.float64,
    )
    channel = np.asarray(list(channel_novelty), dtype=np.float64)
    merchant = np.asarray(list(merchant_category_novelty), dtype=np.float64)
    country = np.asarray(list(transaction_country_novelty), dtype=np.float64)
    count_24h = np.asarray(list(prior_24h_tx_count), dtype=np.float64)
    count_30d = np.asarray(list(prior_30d_tx_count), dtype=np.float64)

    n = len(ratio_raw)
    arrays = (channel, merchant, country, count_24h, count_30d)
    if n == 0 or any(len(values) != n for values in arrays):
        raise ValueError("all heuristic inputs must be nonempty and equal length")
    if np.any(count_24h < 0) or np.any(count_30d < 0):
        raise ValueError("velocity counts cannot be negative")

    # Only unusually large amounts increase the baseline score. A 2x prior mean
    # gives 1/3 of the amount component, 4x gives 2/3, and >=8x saturates it.
    amount_component = np.zeros(n, dtype=np.float64)
    valid_ratio = np.isfinite(ratio_raw) & (ratio_raw > 1.0)
    amount_component[valid_ratio] = np.clip(
        np.log2(ratio_raw[valid_ratio]) / 3.0,
        0.0,
        1.0,
    )

    # Velocity terms saturate at 5 prior transactions in 24h and 20 in 30d.
    velocity_24h = np.clip(np.log1p(count_24h) / math.log(6.0), 0.0, 1.0)
    velocity_30d = np.clip(np.log1p(count_30d) / math.log(21.0), 0.0, 1.0)

    score = (
        0.35 * amount_component
        + 0.15 * channel
        + 0.10 * merchant
        + 0.15 * country
        + 0.15 * velocity_24h
        + 0.10 * velocity_30d
    )
    return np.clip(score, 0.0, 1.0)


def _review_budget_metrics(
    y: np.ndarray,
    scores: np.ndarray,
    tie_breaker: np.ndarray,
    budget_fraction: float,
) -> ReviewBudgetMetrics:
    if not (0.0 < budget_fraction <= 1.0):
        raise ValueError("budget_fraction must be in (0, 1]")
    if len(tie_breaker) != len(y):
        raise ValueError("tie_breaker must match y_true length")

    review_rows = max(1, math.ceil(len(y) * budget_fraction))
    order = np.lexsort((tie_breaker, -scores))
    reviewed = y[order[:review_rows]]
    fraud_caught = int(reviewed.sum())
    positives = int(y.sum())
    false_positives = int(review_rows - fraud_caught)

    recall = fraud_caught / positives if positives else 0.0
    precision = fraud_caught / review_rows
    prevalence = positives / len(y)
    precision_lift = precision / prevalence if prevalence else None
    false_positive_burden = (
        false_positives / fraud_caught if fraud_caught else None
    )

    return ReviewBudgetMetrics(
        budget_fraction=budget_fraction,
        review_rows=review_rows,
        fraud_caught=fraud_caught,
        false_positives=false_positives,
        recall=recall,
        precision=precision,
        precision_lift=precision_lift,
        false_positives_per_detected_fraud=false_positive_burden,
    )


def ranking_metrics(
    y_true: Iterable[int | bool],
    scores: Iterable[float],
    *,
    tie_breaker: Iterable[int] | np.ndarray,
    budgets: tuple[float, ...] = REVIEW_BUDGETS,
) -> RankingMetrics:
    y = _as_binary(y_true)
    s = _as_scores(scores, len(y))
    tie = np.asarray(list(tie_breaker), dtype=np.uint64)
    if len(tie) != len(y):
        raise ValueError("tie_breaker must match y_true length")

    positives = int(y.sum())
    prevalence = positives / len(y)
    pr_auc = float(average_precision_score(y, s))
    roc_auc = (
        float(roc_auc_score(y, s))
        if 0 < positives < len(y)
        else None
    )
    return RankingMetrics(
        rows=len(y),
        positive_rows=positives,
        prevalence=prevalence,
        pr_auc=pr_auc,
        roc_auc=roc_auc,
        budgets=tuple(
            _review_budget_metrics(y, s, tie, budget)
            for budget in budgets
        ),
    )


def probability_metrics(
    y_true: Iterable[int | bool],
    probabilities: Iterable[float],
) -> ProbabilityMetrics:
    y = _as_binary(y_true)
    p = _as_scores(probabilities, len(y))
    if np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("probabilities must be in [0, 1]")
    return ProbabilityMetrics(brier_score=float(brier_score_loss(y, p)))


def primary_budget(metrics: RankingMetrics) -> ReviewBudgetMetrics:
    for budget in metrics.budgets:
        if math.isclose(
            budget.budget_fraction,
            PRIMARY_REVIEW_BUDGET,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            return budget
    raise ValueError("primary 0.5% review budget is missing")


def poisson_bootstrap_pr_auc_interval(
    y_true: Iterable[int | bool],
    scores: Iterable[float],
    *,
    iterations: int = POISSON_BOOTSTRAP_ITERATIONS,
    seed: int = POISSON_BOOTSTRAP_SEED,
) -> BootstrapInterval:
    """Poisson bootstrap PR-AUC CI with exact score-tie grouping.

    For each unique score threshold, positive and negative bootstrap
    multiplicities are sampled as independent Poisson counts with rates equal to
    their empirical counts. This is the standard Poisson-bootstrap analogue of
    row resampling and avoids repeatedly sorting hundreds of thousands of rows.
    """

    y = _as_binary(y_true)
    s = _as_scores(scores, len(y))
    if iterations < 100:
        raise ValueError("iterations must be at least 100")
    positives = int(y.sum())
    if positives == 0:
        raise ValueError("PR-AUC bootstrap requires at least one positive row")

    order = np.argsort(-s, kind="stable")
    sorted_scores = s[order]
    sorted_y = y[order]

    group_starts = np.r_[0, 1 + np.flatnonzero(sorted_scores[1:] != sorted_scores[:-1])]
    group_ends = np.r_[group_starts[1:], len(sorted_scores)]
    pos_counts = np.add.reduceat(sorted_y.astype(np.int64), group_starts)
    group_sizes = group_ends - group_starts
    neg_counts = group_sizes - pos_counts

    rng = np.random.default_rng(seed)
    bootstrap_values = np.empty(iterations, dtype=np.float64)

    for index in range(iterations):
        pos_w = rng.poisson(pos_counts)
        neg_w = rng.poisson(neg_counts)
        total_pos = int(pos_w.sum())
        if total_pos == 0:
            bootstrap_values[index] = np.nan
            continue

        cumulative_pos = np.cumsum(pos_w, dtype=np.float64)
        cumulative_all = np.cumsum(pos_w + neg_w, dtype=np.float64)
        precision = np.divide(
            cumulative_pos,
            cumulative_all,
            out=np.zeros_like(cumulative_pos),
            where=cumulative_all > 0,
        )
        bootstrap_values[index] = float(
            np.sum((pos_w / total_pos) * precision)
        )

    valid = bootstrap_values[np.isfinite(bootstrap_values)]
    if len(valid) < max(100, int(iterations * 0.95)):
        raise RuntimeError("too many degenerate bootstrap replicates")

    lower, upper = np.quantile(valid, [0.025, 0.975])
    return BootstrapInterval(
        point_estimate=float(average_precision_score(y, s)),
        lower_95=float(lower),
        upper_95=float(upper),
        iterations=iterations,
        method="poisson-bootstrap-score-grouped",
        seed=seed,
    )


def validation_gate_decision(
    *,
    gbdt_metrics: RankingMetrics,
    gbdt_pr_auc_interval: BootstrapInterval,
    non_gbdt_baseline_pr_aucs: Mapping[str, float],
) -> GateDecision:
    if not non_gbdt_baseline_pr_aucs:
        raise ValueError("at least one non-GBDT baseline is required")
    best_baseline = max(float(value) for value in non_gbdt_baseline_pr_aucs.values())
    budget = primary_budget(gbdt_metrics)
    lift = budget.precision_lift or 0.0

    checks = {
        "pr_auc_lower_bound_exceeds_best_non_gbdt": (
            gbdt_pr_auc_interval.lower_95 > best_baseline
        ),
        "top_0_5_recall_at_least_5_percent": (
            budget.recall >= VALIDATION_MIN_TOP_005_RECALL
        ),
        "top_0_5_precision_lift_at_least_10x": (
            lift >= VALIDATION_MIN_TOP_005_PRECISION_LIFT
        ),
    }
    return GateDecision(
        passed=all(checks.values()),
        checks=checks,
        values={
            "gbdt_pr_auc": gbdt_metrics.pr_auc,
            "gbdt_pr_auc_lower_95": gbdt_pr_auc_interval.lower_95,
            "best_non_gbdt_pr_auc": best_baseline,
            "top_0_5_recall": budget.recall,
            "top_0_5_precision_lift": lift,
            "segment_prevalence": gbdt_metrics.prevalence,
        },
    )


def test_survival_decision(
    *,
    test_gbdt_metrics: RankingMetrics,
    gate_gbdt_pr_auc: float,
    test_non_gbdt_baseline_pr_aucs: Mapping[str, float],
) -> GateDecision:
    if not test_non_gbdt_baseline_pr_aucs:
        raise ValueError("at least one test non-GBDT baseline is required")
    best_baseline = max(float(value) for value in test_non_gbdt_baseline_pr_aucs.values())
    budget = primary_budget(test_gbdt_metrics)
    lift = budget.precision_lift or 0.0

    checks = {
        "test_pr_auc_exceeds_best_non_gbdt": (
            test_gbdt_metrics.pr_auc > best_baseline
        ),
        "test_pr_auc_at_least_half_gate_pr_auc": (
            test_gbdt_metrics.pr_auc >= TEST_MIN_GATE_PR_AUC_RATIO * gate_gbdt_pr_auc
        ),
        "top_0_5_recall_at_least_2_5_percent": (
            budget.recall >= TEST_MIN_TOP_005_RECALL
        ),
        "top_0_5_precision_lift_at_least_5x": (
            lift >= TEST_MIN_TOP_005_PRECISION_LIFT
        ),
    }
    return GateDecision(
        passed=all(checks.values()),
        checks=checks,
        values={
            "test_gbdt_pr_auc": test_gbdt_metrics.pr_auc,
            "gate_gbdt_pr_auc": gate_gbdt_pr_auc,
            "best_test_non_gbdt_pr_auc": best_baseline,
            "top_0_5_recall": budget.recall,
            "top_0_5_precision_lift": lift,
            "test_prevalence": test_gbdt_metrics.prevalence,
        },
    )


def metric_contract_dict() -> dict[str, object]:
    return {
        "contract_version": METRIC_CONTRACT_VERSION,
        "review_budgets": list(REVIEW_BUDGETS),
        "primary_review_budget": PRIMARY_REVIEW_BUDGET,
        "poisson_bootstrap_iterations": POISSON_BOOTSTRAP_ITERATIONS,
        "poisson_bootstrap_seed": POISSON_BOOTSTRAP_SEED,
        "behavioral_heuristic": {
            "amount_surprise_weight": 0.35,
            "channel_novelty_weight": 0.15,
            "merchant_category_novelty_weight": 0.10,
            "transaction_country_novelty_weight": 0.15,
            "prior_24h_velocity_weight": 0.15,
            "prior_30d_velocity_weight": 0.10,
            "amount_surprise_saturates_at_ratio": 8.0,
            "prior_24h_velocity_saturates_at_count": 5,
            "prior_30d_velocity_saturates_at_count": 20,
        },
        "validation_gate": {
            "gbdt_pr_auc_lower_95_gt_best_non_gbdt_point": True,
            "top_0_5_recall_min": VALIDATION_MIN_TOP_005_RECALL,
            "top_0_5_precision_lift_min": VALIDATION_MIN_TOP_005_PRECISION_LIFT,
        },
        "test_survival": {
            "pr_auc_gt_best_non_gbdt_point": True,
            "pr_auc_min_fraction_of_gate": TEST_MIN_GATE_PR_AUC_RATIO,
            "top_0_5_recall_min": TEST_MIN_TOP_005_RECALL,
            "top_0_5_precision_lift_min": TEST_MIN_TOP_005_PRECISION_LIFT,
        },
        "tie_breaker": "blake2b-64(transaction_id|proof-of-one-eval-tie-v1)",
        "accuracy_is_headline_metric": False,
    }


def metric_contract_sha256() -> str:
    payload = json.dumps(
        metric_contract_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
