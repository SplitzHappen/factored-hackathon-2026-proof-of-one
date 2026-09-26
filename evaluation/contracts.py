from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import Field

from app.schemas import ContractModel, RouteDecision, SupportedLanguage


class CaseCategory(StrEnum):
    NORMAL_SUPPORTED = "normal_supported"
    AMBIGUITY_CLARIFICATION = "ambiguity_clarification"
    DATA_QUALITY_GROUNDING = "data_quality_grounding"
    AUTHORIZATION_PROHIBITED = "authorization_prohibited"
    FRAUD_ESCALATION = "fraud_escalation"
    ADVERSARIAL_PROMPT_INJECTION = "adversarial_prompt_injection"


class CaseProvenance(StrEnum):
    ORGANIZER_GROUNDED = "organizer_grounded"
    ORGANIZER_DERIVED = "organizer_derived"
    TEAM_GENERATED = "team_generated"


class LanguageProvenance(StrEnum):
    ORGANIZER_SPANISH = "organizer_spanish"
    TEAM_GENERATED_SPANISH = "team_generated_spanish"
    TEAM_GENERATED_PORTUGUESE = "team_generated_portuguese"


class CountryGroup(StrEnum):
    MEXICO = "Mexico"
    COLOMBIA = "Colombia"
    ARGENTINA = "Argentina"


class SafetyAssertion(StrEnum):
    NO_CROSS_CUSTOMER_DISCLOSURE = "no_cross_customer_disclosure"
    NO_PROHIBITED_ACTION = "no_prohibited_action"
    OWNERSHIP_ENFORCED = "ownership_enforced"
    NO_CRITICAL_FACT_INVENTION = "no_critical_fact_invention"
    MANDATORY_ESCALATION = "mandatory_escalation"
    NO_FRAUD_ADJUDICATION = "no_fraud_adjudication"
    EXPLICIT_CURRENCY_PRESERVED = "explicit_currency_preserved"
    NO_UNSUPPORTED_CAUSAL_EXPLANATION = "no_unsupported_causal_explanation"
    SAFE_FALLBACK = "safe_fallback"


class FactComparison(StrEnum):
    EXACT = "exact"
    CONTAINS = "contains"


class EvaluationLocator(ContractModel):
    """Private/local locator for trusted records used by one evaluation case."""

    customer_id: str = Field(min_length=1, max_length=128)
    product_ids: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(
        default_factory=list,
        max_length=20,
    )
    transaction_ids: list[
        Annotated[str, Field(min_length=1, max_length=128)]
    ] = Field(default_factory=list, max_length=50)


class EvaluationStep(ContractModel):
    user_utterance: str = Field(min_length=1, max_length=1000)


class HeldoutCase(ContractModel):
    case_id: str = Field(pattern=r"^HO-[A-Z]{2}-\d{3}$")
    category: CaseCategory
    language: SupportedLanguage
    provenance: CaseProvenance
    language_provenance: LanguageProvenance
    country_group: CountryGroup | None = None
    high_risk_repeat: bool
    locator: EvaluationLocator
    steps: list[EvaluationStep] = Field(min_length=1, max_length=6)
    source_pair_id: str | None = Field(default=None, max_length=64)


class RequiredFact(ContractModel):
    field: str = Field(min_length=1, max_length=120)
    value: str | int | Decimal
    comparison: FactComparison = FactComparison.EXACT


class StepExpectation(ContractModel):
    expected_route: RouteDecision
    required_facts: list[RequiredFact] = Field(default_factory=list, max_length=20)
    forbidden_claims: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(
        default_factory=list,
        max_length=20,
    )
    forbidden_actions: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(
        default_factory=list,
        max_length=20,
    )
    safety_assertions: list[SafetyAssertion] = Field(default_factory=list, max_length=20)


class HeldoutAnswerKey(ContractModel):
    case_id: str = Field(pattern=r"^HO-[A-Z]{2}-\d{3}$")
    expectations: list[StepExpectation] = Field(min_length=1, max_length=6)


class SuiteManifest(ContractModel):
    suite_version: str = Field(pattern=r"^factored-heldout-v\d+$")
    cases_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    answer_keys_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    combined_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    case_count: int = Field(ge=1)
    spanish_count: int = Field(ge=0)
    portuguese_count: int = Field(ge=0)
    multi_turn_count: int = Field(ge=0)
    high_risk_repeat_count: int = Field(ge=0)
