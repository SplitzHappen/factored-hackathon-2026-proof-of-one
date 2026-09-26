from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from app.behavioral_evidence import (
    BehavioralEvidenceInput,
    DeviationBand,
    EvidenceComponent,
    MIN_AVAILABLE_COMPONENTS_FOR_COMPOSITE,
    MIN_PRIOR_TRANSACTIONS_FOR_COMPOSITE,
    REQUIRED_DISCLAIMER,
    behavioral_evidence_contract_dict,
    behavioral_evidence_contract_sha256,
    compute_behavioral_evidence,
)


def _facts(**overrides):
    payload = {
        "prior_tx_count_lifetime": 20,
        "product_tenure_days": 365.0,
        "has_prior_currency_amount_history": True,
        "amount_to_prior_currency_mean_ratio": 1.0,
        "channel_novelty": False,
        "merchant_category_present": True,
        "merchant_category_novelty": False,
        "transaction_country_novelty": False,
        "prior_24h_tx_count": 1,
        "prior_30d_tx_count": 10,
    }
    payload.update(overrides)
    return BehavioralEvidenceInput(**payload)


def _component(result, component: EvidenceComponent):
    return next(item for item in result.components if item.component == component)


def test_cold_start_suppresses_composite_instead_of_calling_everything_unusual() -> None:
    facts = BehavioralEvidenceInput(
        prior_tx_count_lifetime=0,
        product_tenure_days=1.0,
        has_prior_currency_amount_history=False,
        amount_to_prior_currency_mean_ratio=None,
        channel_novelty=True,
        merchant_category_present=True,
        merchant_category_novelty=False,
        transaction_country_novelty=True,
        prior_24h_tx_count=0,
        prior_30d_tx_count=0,
    )

    result = compute_behavioral_evidence(facts)

    assert result.composite_available is False
    assert result.behavioral_unusualness_0_100 is None
    assert result.deviation_band is None
    assert result.available_component_count == 0
    assert "at least 5 prior transactions" in result.not_available_reason
    assert all(component.available is False for component in result.components)


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        (1.0, 0.0),
        (2.0, 0.5),
        (0.5, 0.5),
        (4.0, 1.0),
        (0.25, 1.0),
        (8.0, 1.0),
    ],
)
def test_amount_surprise_is_symmetric_and_saturating(
    ratio: float,
    expected: float,
) -> None:
    result = compute_behavioral_evidence(
        _facts(amount_to_prior_currency_mean_ratio=ratio)
    )
    amount = _component(result, EvidenceComponent.AMOUNT_SURPRISE)

    assert amount.available is True
    assert amount.score_0_1 == pytest.approx(expected)


def test_novelty_components_are_descriptive_binary_evidence() -> None:
    result = compute_behavioral_evidence(
        _facts(
            channel_novelty=True,
            merchant_category_novelty=True,
            transaction_country_novelty=True,
        )
    )

    for component in (
        EvidenceComponent.CHANNEL_NOVELTY,
        EvidenceComponent.MERCHANT_CATEGORY_NOVELTY,
        EvidenceComponent.TRANSACTION_COUNTRY_NOVELTY,
    ):
        item = _component(result, component)
        assert item.available is True
        assert item.score_0_1 == 1.0
        assert item.label == "high observed deviation"

    assert result.predictive is False
    assert result.fraud_probability is False
    assert result.fraud_adjudication is False
    assert result.routing_authority is False
    assert result.queue_priority_authority is False
    assert result.disclaimer == REQUIRED_DISCLAIMER


def test_missing_merchant_category_is_unavailable_not_novel() -> None:
    result = compute_behavioral_evidence(
        _facts(
            merchant_category_present=False,
            merchant_category_novelty=False,
        )
    )

    merchant = _component(
        result,
        EvidenceComponent.MERCHANT_CATEGORY_NOVELTY,
    )
    assert merchant.available is False
    assert merchant.score_0_1 is None
    assert merchant.label == "merchant category unavailable"


def test_24h_velocity_uses_customer_recent_rate_and_only_scores_elevation() -> None:
    low = compute_behavioral_evidence(
        _facts(prior_24h_tx_count=0, prior_30d_tx_count=10)
    )
    elevated = compute_behavioral_evidence(
        _facts(prior_24h_tx_count=2, prior_30d_tx_count=10)
    )

    low_item = _component(low, EvidenceComponent.VELOCITY_24H)
    high_item = _component(elevated, EvidenceComponent.VELOCITY_24H)

    assert low_item.score_0_1 == 0.0
    assert high_item.score_0_1 is not None
    assert high_item.score_0_1 > 0.0


def test_24h_velocity_is_unavailable_without_minimum_recent_baseline() -> None:
    result = compute_behavioral_evidence(
        _facts(prior_24h_tx_count=1, prior_30d_tx_count=4)
    )

    velocity = _component(result, EvidenceComponent.VELOCITY_24H)
    assert velocity.available is False
    assert velocity.score_0_1 is None
    assert velocity.label == "insufficient 30-day history"


def test_30d_velocity_requires_long_run_history() -> None:
    short = compute_behavioral_evidence(
        _facts(product_tenure_days=30.0)
    )
    long = compute_behavioral_evidence(
        _facts(
            product_tenure_days=365.0,
            prior_tx_count_lifetime=20,
            prior_30d_tx_count=10,
            prior_24h_tx_count=1,
        )
    )

    short_item = _component(short, EvidenceComponent.VELOCITY_30D)
    long_item = _component(long, EvidenceComponent.VELOCITY_30D)

    assert short_item.available is False
    assert long_item.available is True
    assert long_item.score_0_1 is not None
    assert long_item.score_0_1 > 0.0


def test_composite_is_unweighted_mean_only_when_history_and_coverage_are_sufficient() -> None:
    result = compute_behavioral_evidence(
        _facts(
            amount_to_prior_currency_mean_ratio=4.0,
            channel_novelty=True,
            merchant_category_novelty=False,
            transaction_country_novelty=True,
            prior_24h_tx_count=2,
            prior_30d_tx_count=10,
        )
    )

    scores = [
        item.score_0_1
        for item in result.components
        if item.available and item.score_0_1 is not None
    ]
    expected = round(100.0 * sum(scores) / len(scores), 1)

    assert result.prior_transaction_count >= MIN_PRIOR_TRANSACTIONS_FOR_COMPOSITE
    assert len(scores) >= MIN_AVAILABLE_COMPONENTS_FOR_COMPOSITE
    assert result.composite_available is True
    assert result.behavioral_unusualness_0_100 == expected
    assert isinstance(result.deviation_band, DeviationBand)


def test_contract_boundary_rejects_target_and_reference_score_fields() -> None:
    payload = _facts().model_dump()
    payload["is_fraud"] = True

    with pytest.raises(ValidationError):
        BehavioralEvidenceInput(**payload)

    payload = _facts().model_dump()
    payload["fraud_score"] = 99.0

    with pytest.raises(ValidationError):
        BehavioralEvidenceInput(**payload)


def test_history_count_invariants_fail_closed() -> None:
    with pytest.raises(ValidationError, match="prior_24h_tx_count"):
        _facts(
            prior_tx_count_lifetime=5,
            prior_30d_tx_count=4,
            prior_24h_tx_count=5,
        )

    with pytest.raises(ValidationError, match="lifetime"):
        _facts(
            prior_tx_count_lifetime=5,
            prior_30d_tx_count=6,
            prior_24h_tx_count=1,
        )


def test_behavioral_contract_is_target_free_and_not_a_risk_contract() -> None:
    contract = behavioral_evidence_contract_dict()
    serialized = str(contract).lower()

    assert contract["semantics"]["target_free"] is True
    assert contract["semantics"]["learned_weights"] is False
    assert contract["semantics"]["fraud_probability"] is False
    assert contract["semantics"]["fraud_risk_score"] is False
    assert contract["semantics"]["routing_authority"] is False
    assert contract["semantics"]["mandatory_escalation_authority"] is False
    assert contract["semantics"]["queue_priority_authority"] is False
    assert contract["offline_transparency_evaluation"]["segment"] == "calibration_gate"
    assert contract["offline_transparency_evaluation"]["test_segment_remains_sealed"] is True
    assert "organizer fraud score" not in serialized


def test_behavioral_contract_hash_is_stable() -> None:
    first = behavioral_evidence_contract_sha256()
    second = behavioral_evidence_contract_sha256()

    assert first == second
    assert len(first) == 64
    assert set(first) <= set("0123456789abcdef")
