from __future__ import annotations

import hashlib
import json
import math
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from app.schemas import ContractModel
from ml.null_result_contract import (
    ALLOWED_BEHAVIORAL_COMPONENTS,
    NULL_RESULT_CONTRACT_VERSION,
    null_result_contract_sha256,
)


BEHAVIORAL_EVIDENCE_VERSION = "factored-behavioral-evidence-v1"

MIN_PRIOR_TRANSACTIONS_FOR_COMPOSITE = 5
MIN_AVAILABLE_COMPONENTS_FOR_COMPOSITE = 4
MIN_PRODUCT_TENURE_DAYS_FOR_30D_VELOCITY = 60.0
MIN_PRIOR_30D_TRANSACTIONS_FOR_24H_BASELINE = 5

REQUIRED_DISCLAIMER = (
    "Descriptive behavioral evidence only; not a fraud probability "
    "or fraud determination."
)


class EvidenceComponent(StrEnum):
    AMOUNT_SURPRISE = "amount_surprise"
    CHANNEL_NOVELTY = "channel_novelty"
    MERCHANT_CATEGORY_NOVELTY = "merchant_category_novelty"
    TRANSACTION_COUNTRY_NOVELTY = "transaction_country_novelty"
    VELOCITY_24H = "velocity_24h"
    VELOCITY_30D = "velocity_30d"


class DeviationBand(StrEnum):
    LOW = "low_observed_deviation"
    MODERATE = "moderate_observed_deviation"
    ELEVATED = "elevated_observed_deviation"
    HIGH = "high_observed_deviation"


class BehavioralEvidenceInput(ContractModel):
    prior_tx_count_lifetime: int = Field(ge=0)
    product_tenure_days: float = Field(ge=0)

    has_prior_currency_amount_history: bool
    amount_to_prior_currency_mean_ratio: float | None = Field(default=None, gt=0)

    channel_novelty: bool

    merchant_category_present: bool
    merchant_category_novelty: bool

    transaction_country_novelty: bool

    prior_24h_tx_count: int = Field(ge=0)
    prior_30d_tx_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_history_consistency(self) -> "BehavioralEvidenceInput":
        if self.prior_24h_tx_count > self.prior_30d_tx_count:
            raise ValueError("prior_24h_tx_count cannot exceed prior_30d_tx_count")
        if self.prior_30d_tx_count > self.prior_tx_count_lifetime:
            raise ValueError("prior_30d_tx_count cannot exceed lifetime count")
        if self.has_prior_currency_amount_history:
            if self.amount_to_prior_currency_mean_ratio is None:
                raise ValueError(
                    "amount ratio is required when prior currency history exists"
                )
        elif self.amount_to_prior_currency_mean_ratio is not None:
            raise ValueError(
                "amount ratio must be absent without prior currency history"
            )
        if not self.merchant_category_present and self.merchant_category_novelty:
            raise ValueError(
                "merchant-category novelty cannot be true when category is absent"
            )
        if self.prior_tx_count_lifetime == 0:
            if self.prior_24h_tx_count != 0 or self.prior_30d_tx_count != 0:
                raise ValueError("zero lifetime history requires zero window counts")
            if self.has_prior_currency_amount_history:
                raise ValueError(
                    "zero lifetime history cannot have prior currency history"
                )
        return self


class ComponentEvidence(ContractModel):
    component: EvidenceComponent
    available: bool
    score_0_1: float | None = Field(default=None, ge=0.0, le=1.0)
    label: str = Field(min_length=1, max_length=120)
    context: str = Field(min_length=1, max_length=240)


class BehavioralEvidenceResult(ContractModel):
    version: str
    composite_available: bool
    behavioral_unusualness_0_100: float | None = Field(
        default=None, ge=0.0, le=100.0
    )
    deviation_band: DeviationBand | None = None
    available_component_count: int = Field(ge=0, le=6)
    prior_transaction_count: int = Field(ge=0)
    not_available_reason: str | None = Field(default=None, max_length=240)
    components: list[ComponentEvidence] = Field(min_length=6, max_length=6)

    disclaimer: str
    predictive: bool
    fraud_probability: bool
    fraud_adjudication: bool
    routing_authority: bool
    queue_priority_authority: bool


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _amount_surprise(ratio: float) -> float:
    """Symmetric deviation from prior same-currency mean.

    A 4x or 0.25x amount reaches the configured maximum. This is a
    descriptive transformation, not a learned fraud association.
    """

    return _clamp_01(abs(math.log2(ratio)) / 2.0)


def _elevated_rate_score(rate_ratio: float, *, saturation_ratio: float) -> float:
    """Score only elevated activity relative to the customer's own baseline."""

    if rate_ratio <= 1.0:
        return 0.0
    return _clamp_01(
        math.log2(rate_ratio) / math.log2(saturation_ratio)
    )


def _component_label(score: float) -> str:
    if score < 0.25:
        return "low observed deviation"
    if score < 0.50:
        return "moderate observed deviation"
    if score < 0.75:
        return "elevated observed deviation"
    return "high observed deviation"


def _composite_band(score_0_100: float) -> DeviationBand:
    if score_0_100 < 25.0:
        return DeviationBand.LOW
    if score_0_100 < 50.0:
        return DeviationBand.MODERATE
    if score_0_100 < 75.0:
        return DeviationBand.ELEVATED
    return DeviationBand.HIGH


def _unavailable(
    component: EvidenceComponent,
    *,
    label: str,
    context: str,
) -> ComponentEvidence:
    return ComponentEvidence(
        component=component,
        available=False,
        score_0_1=None,
        label=label,
        context=context,
    )


def _available(
    component: EvidenceComponent,
    *,
    score: float,
    context: str,
) -> ComponentEvidence:
    score = _clamp_01(score)
    return ComponentEvidence(
        component=component,
        available=True,
        score_0_1=score,
        label=_component_label(score),
        context=context,
    )


def compute_behavioral_evidence(
    facts: BehavioralEvidenceInput,
) -> BehavioralEvidenceResult:
    components: list[ComponentEvidence] = []

    if facts.has_prior_currency_amount_history:
        assert facts.amount_to_prior_currency_mean_ratio is not None
        amount_score = _amount_surprise(
            facts.amount_to_prior_currency_mean_ratio
        )
        components.append(
            _available(
                EvidenceComponent.AMOUNT_SURPRISE,
                score=amount_score,
                context=(
                    "Current amount is "
                    f"{facts.amount_to_prior_currency_mean_ratio:.2f}x "
                    "the prior same-currency mean."
                ),
            )
        )
    else:
        components.append(
            _unavailable(
                EvidenceComponent.AMOUNT_SURPRISE,
                label="insufficient same-currency history",
                context="No prior same-currency amount baseline is available.",
            )
        )

    if facts.prior_tx_count_lifetime > 0:
        components.append(
            _available(
                EvidenceComponent.CHANNEL_NOVELTY,
                score=1.0 if facts.channel_novelty else 0.0,
                context=(
                    "First observed channel in prior history."
                    if facts.channel_novelty
                    else "Channel was observed previously."
                ),
            )
        )
    else:
        components.append(
            _unavailable(
                EvidenceComponent.CHANNEL_NOVELTY,
                label="insufficient history",
                context="No prior transaction exists for channel comparison.",
            )
        )

    if not facts.merchant_category_present:
        components.append(
            _unavailable(
                EvidenceComponent.MERCHANT_CATEGORY_NOVELTY,
                label="merchant category unavailable",
                context="Current transaction has no merchant category.",
            )
        )
    elif facts.prior_tx_count_lifetime > 0:
        components.append(
            _available(
                EvidenceComponent.MERCHANT_CATEGORY_NOVELTY,
                score=1.0 if facts.merchant_category_novelty else 0.0,
                context=(
                    "First observed merchant category in prior history."
                    if facts.merchant_category_novelty
                    else "Merchant category was observed previously."
                ),
            )
        )
    else:
        components.append(
            _unavailable(
                EvidenceComponent.MERCHANT_CATEGORY_NOVELTY,
                label="insufficient history",
                context=(
                    "No prior transaction exists for merchant-category comparison."
                ),
            )
        )

    if facts.prior_tx_count_lifetime > 0:
        components.append(
            _available(
                EvidenceComponent.TRANSACTION_COUNTRY_NOVELTY,
                score=1.0 if facts.transaction_country_novelty else 0.0,
                context=(
                    "First observed transaction country in prior history."
                    if facts.transaction_country_novelty
                    else "Transaction country was observed previously."
                ),
            )
        )
    else:
        components.append(
            _unavailable(
                EvidenceComponent.TRANSACTION_COUNTRY_NOVELTY,
                label="insufficient history",
                context="No prior transaction exists for country comparison.",
            )
        )

    if (
        facts.prior_30d_tx_count
        >= MIN_PRIOR_30D_TRANSACTIONS_FOR_24H_BASELINE
    ):
        expected_24h = facts.prior_30d_tx_count / 30.0
        ratio_24h = facts.prior_24h_tx_count / expected_24h
        components.append(
            _available(
                EvidenceComponent.VELOCITY_24H,
                score=_elevated_rate_score(
                    ratio_24h,
                    saturation_ratio=8.0,
                ),
                context=(
                    f"{facts.prior_24h_tx_count} prior transactions in 24h "
                    f"versus a 30d average of {expected_24h:.2f} per day."
                ),
            )
        )
    else:
        components.append(
            _unavailable(
                EvidenceComponent.VELOCITY_24H,
                label="insufficient 30-day history",
                context=(
                    "At least 5 prior transactions in the 30-day window are "
                    "required for the 24-hour velocity baseline."
                ),
            )
        )

    if (
        facts.prior_tx_count_lifetime
        >= MIN_PRIOR_TRANSACTIONS_FOR_COMPOSITE
        and facts.product_tenure_days
        >= MIN_PRODUCT_TENURE_DAYS_FOR_30D_VELOCITY
    ):
        lifetime_daily_rate = (
            facts.prior_tx_count_lifetime / facts.product_tenure_days
        )
        expected_30d = max(lifetime_daily_rate * 30.0, 1e-12)
        ratio_30d = facts.prior_30d_tx_count / expected_30d
        components.append(
            _available(
                EvidenceComponent.VELOCITY_30D,
                score=_elevated_rate_score(
                    ratio_30d,
                    saturation_ratio=4.0,
                ),
                context=(
                    f"{facts.prior_30d_tx_count} prior transactions in 30d "
                    f"versus a tenure-adjusted expectation of "
                    f"{expected_30d:.2f}."
                ),
            )
        )
    else:
        components.append(
            _unavailable(
                EvidenceComponent.VELOCITY_30D,
                label="insufficient long-run history",
                context=(
                    "At least 5 prior transactions and 60 days of product tenure "
                    "are required for the 30-day velocity baseline."
                ),
            )
        )

    available_scores = [
        component.score_0_1
        for component in components
        if component.available and component.score_0_1 is not None
    ]

    enough_history = (
        facts.prior_tx_count_lifetime
        >= MIN_PRIOR_TRANSACTIONS_FOR_COMPOSITE
    )
    enough_components = (
        len(available_scores)
        >= MIN_AVAILABLE_COMPONENTS_FOR_COMPOSITE
    )

    if enough_history and enough_components:
        composite = round(
            100.0 * sum(available_scores) / len(available_scores),
            1,
        )
        band = _composite_band(composite)
        reason = None
        composite_available = True
    else:
        composite = None
        band = None
        composite_available = False
        if not enough_history:
            reason = (
                "Insufficient behavioral history: at least 5 prior "
                "transactions are required for a composite."
            )
        else:
            reason = (
                "Insufficient component coverage: at least 4 behavioral "
                "components are required for a composite."
            )

    return BehavioralEvidenceResult(
        version=BEHAVIORAL_EVIDENCE_VERSION,
        composite_available=composite_available,
        behavioral_unusualness_0_100=composite,
        deviation_band=band,
        available_component_count=len(available_scores),
        prior_transaction_count=facts.prior_tx_count_lifetime,
        not_available_reason=reason,
        components=components,
        disclaimer=REQUIRED_DISCLAIMER,
        predictive=False,
        fraud_probability=False,
        fraud_adjudication=False,
        routing_authority=False,
        queue_priority_authority=False,
    )


def behavioral_evidence_contract_dict() -> dict[str, Any]:
    return {
        "version": BEHAVIORAL_EVIDENCE_VERSION,
        "upstream": {
            "null_result_contract_version": NULL_RESULT_CONTRACT_VERSION,
            "null_result_contract_sha256": null_result_contract_sha256(),
        },
        "components": list(ALLOWED_BEHAVIORAL_COMPONENTS),
        "composite": {
            "name": "Behavioral Unusualness",
            "range": [0, 100],
            "aggregation": "unweighted_mean_of_available_component_scores",
            "minimum_prior_transactions": MIN_PRIOR_TRANSACTIONS_FOR_COMPOSITE,
            "minimum_available_components": MIN_AVAILABLE_COMPONENTS_FOR_COMPOSITE,
            "no_composite_when_history_is_insufficient": True,
        },
        "component_semantics": {
            "amount_surprise": {
                "source": "amount_to_prior_currency_mean_ratio",
                "transformation": "min(abs(log2(ratio))/2, 1)",
                "saturation": "4x or 0.25x prior same-currency mean",
            },
            "channel_novelty": {
                "source": "channel_novelty",
                "transformation": "binary first-observed indicator",
            },
            "merchant_category_novelty": {
                "source": "merchant_category_novelty",
                "transformation": "binary first-observed indicator",
                "missing_category": "component unavailable",
            },
            "transaction_country_novelty": {
                "source": "transaction_country_novelty",
                "transformation": "binary first-observed indicator",
            },
            "velocity_24h": {
                "source": "prior_24h_tx_count vs prior_30d_tx_count/30",
                "minimum_prior_30d_transactions": (
                    MIN_PRIOR_30D_TRANSACTIONS_FOR_24H_BASELINE
                ),
                "transformation": (
                    "0 at <=1x baseline; log2 ratio scaled to 1 at 8x"
                ),
            },
            "velocity_30d": {
                "source": (
                    "prior_30d_tx_count vs lifetime count / product tenure * 30"
                ),
                "minimum_product_tenure_days": (
                    MIN_PRODUCT_TENURE_DAYS_FOR_30D_VELOCITY
                ),
                "minimum_prior_transactions": (
                    MIN_PRIOR_TRANSACTIONS_FOR_COMPOSITE
                ),
                "transformation": (
                    "0 at <=1x baseline; log2 ratio scaled to 1 at 4x"
                ),
            },
        },
        "semantics": {
            "target_free": True,
            "learned_weights": False,
            "fraud_probability": False,
            "fraud_risk_score": False,
            "fraud_adjudication": False,
            "routing_authority": False,
            "mandatory_escalation_authority": False,
            "queue_priority_authority": False,
            "required_disclaimer": REQUIRED_DISCLAIMER,
        },
        "offline_transparency_evaluation": {
            "permitted_target": "is_fraud",
            "purpose": (
                "association reporting only after formula freeze; "
                "never weight fitting or threshold tuning"
            ),
            "segment": "calibration_gate",
            "test_segment_remains_sealed": True,
        },
    }


def behavioral_evidence_contract_sha256() -> str:
    payload = json.dumps(
        behavioral_evidence_contract_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
