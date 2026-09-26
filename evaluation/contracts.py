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



class DevelopmentCase(ContractModel):
    case_id: str = Field(pattern=r"^DEV-[A-Z]{2}-\d{3}$")
    category: CaseCategory
    language: SupportedLanguage
    provenance: CaseProvenance
    language_provenance: LanguageProvenance
    country_group: CountryGroup | None = None
    locator: EvaluationLocator
    steps: list[EvaluationStep] = Field(min_length=1, max_length=6)
    source_pair_id: str | None = Field(default=None, max_length=64)


class DevelopmentAnswerKey(ContractModel):
    case_id: str = Field(pattern=r"^DEV-[A-Z]{2}-\d{3}$")
    expectations: list[StepExpectation] = Field(min_length=1, max_length=6)



class EvaluationSystem(StrEnum):
    DETERMINISTIC_BASELINE = "deterministic_baseline"
    SIMPLE_MODEL_BASELINE = "simple_model_baseline"
    PROPOSED = "proposed"


class ObservedFact(ContractModel):
    field: str = Field(min_length=1, max_length=120)
    value: str | int | Decimal


class StepObservation(ContractModel):
    route: RouteDecision
    observed_facts: list[ObservedFact] = Field(default_factory=list, max_length=50)
    claim_codes: list[
        Annotated[str, Field(min_length=1, max_length=120)]
    ] = Field(default_factory=list, max_length=50)
    action_codes: list[
        Annotated[str, Field(min_length=1, max_length=120)]
    ] = Field(default_factory=list, max_length=50)
    safety_violations: list[SafetyAssertion] = Field(default_factory=list, max_length=20)
    factual_claim_count: int = Field(default=0, ge=0)
    grounded_factual_claim_count: int = Field(default=0, ge=0)
    critical_fact_error: bool = False
    retrieval_correct: bool = True
    tool_correct: bool = True
    ownership_enforced: bool = True


class CaseExecution(ContractModel):
    suite_version: str = Field(pattern=r"^factored-heldout-v\d+$")
    system: EvaluationSystem
    system_version: str = Field(min_length=1, max_length=160)
    case_id: str = Field(pattern=r"^HO-[A-Z]{2}-\d{3}$")
    run_index: int = Field(ge=1, le=3)
    observations: list[StepObservation] = Field(min_length=1, max_length=6)
    latency_ms: int = Field(ge=0)
    estimated_cost_usd: Decimal = Field(ge=0)
    cold_start: bool = False
    model_provider: str | None = Field(default=None, max_length=120)
    model_name: str | None = Field(default=None, max_length=160)
    model_config_id: str | None = Field(default=None, max_length=160)
    prompt_version: str | None = Field(default=None, max_length=160)
    deployment_version: str | None = Field(default=None, max_length=160)


class StepScore(ContractModel):
    route_correct: bool
    required_facts_correct: bool
    forbidden_claims_clear: bool
    forbidden_actions_clear: bool
    safety_assertions_clear: bool
    correct: bool
    safe: bool


class CaseScore(ContractModel):
    system: EvaluationSystem
    case_id: str = Field(pattern=r"^HO-[A-Z]{2}-\d{3}$")
    run_index: int = Field(ge=1, le=3)
    correct: bool
    safe: bool
    automated_resolution: bool
    expected_final_route: RouteDecision
    observed_final_route: RouteDecision
    step_scores: list[StepScore] = Field(min_length=1, max_length=6)
    factual_claim_count: int = Field(ge=0)
    grounded_factual_claim_count: int = Field(ge=0)
    critical_fact_errors: int = Field(ge=0)
    retrieval_correct: bool
    tool_correct: bool
    ownership_enforced: bool
    latency_ms: int = Field(ge=0)
    estimated_cost_usd: Decimal = Field(ge=0)


class AggregateMetrics(ContractModel):
    suite_version: str = Field(pattern=r"^factored-heldout-v\d+$")
    system: EvaluationSystem
    system_version: str
    semantic_case_count: int = Field(ge=0)
    overall_correct_rate: float = Field(ge=0, le=1)
    safe_automated_resolution_rate: float | None = Field(default=None, ge=0, le=1)
    clarification_abstention_correct_rate: float | None = Field(default=None, ge=0, le=1)
    escalation_correct_rate: float | None = Field(default=None, ge=0, le=1)
    mandatory_fraud_escalation_rate: float | None = Field(default=None, ge=0, le=1)
    groundedness_rate: float | None = Field(default=None, ge=0, le=1)
    critical_fact_accuracy: float | None = Field(default=None, ge=0, le=1)
    retrieval_tool_correctness_rate: float = Field(ge=0, le=1)
    ownership_enforcement_rate: float = Field(ge=0, le=1)
    spanish_correct_rate: float | None = Field(default=None, ge=0, le=1)
    portuguese_correct_rate: float | None = Field(default=None, ge=0, le=1)
    language_gap_percentage_points: float | None = Field(default=None, ge=0)
    automation_rate: float = Field(ge=0, le=1)
    escalation_rate: float = Field(ge=0, le=1)
    latency_p50_ms: float | None = Field(default=None, ge=0)
    latency_p95_ms: float | None = Field(default=None, ge=0)
    average_cost_usd: Decimal | None = Field(default=None, ge=0)
    p95_cost_usd: Decimal | None = Field(default=None, ge=0)
    cost_per_safe_automated_resolution_usd: Decimal | None = Field(
        default=None,
        ge=0,
    )
    high_risk_execution_count: int = Field(ge=0)
    high_risk_unsafe_outcomes: int = Field(ge=0)
    zero_failure_one_sided_upper_95: float | None = Field(default=None, ge=0, le=1)
    country_correct_rates: dict[str, float] = Field(default_factory=dict)


class PairedDifference(ContractModel):
    metric_name: str = Field(min_length=1, max_length=120)
    baseline_system: EvaluationSystem
    proposed_system: EvaluationSystem
    paired_case_count: int = Field(ge=1)
    point_difference: float
    ci95_low: float
    ci95_high: float
    bootstrap_iterations: int = Field(ge=100)
