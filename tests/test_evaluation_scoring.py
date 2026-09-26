from __future__ import annotations

from decimal import Decimal

import pytest

from app.schemas import RouteDecision, SupportedLanguage
from evaluation.contracts import (
    CaseCategory,
    CaseExecution,
    CaseProvenance,
    CountryGroup,
    EvaluationLocator,
    EvaluationStep,
    EvaluationSystem,
    HeldoutAnswerKey,
    HeldoutCase,
    LanguageProvenance,
    ObservedFact,
    RequiredFact,
    SafetyAssertion,
    StepExpectation,
    StepObservation,
)
from evaluation.scoring import (
    ExecutionValidationError,
    aggregate_metrics,
    paired_bootstrap_boolean_difference,
    score_execution,
    score_system,
    validate_execution_set,
)
from evaluation.suite import CATEGORY_LANGUAGE_QUOTAS, HIGH_RISK_CATEGORIES, SUITE_VERSION


CRITICAL_FIELDS = {"amount", "currency", "status"}


def _suite() -> tuple[list[HeldoutCase], list[HeldoutAnswerKey]]:
    cases: list[HeldoutCase] = []
    keys: list[HeldoutAnswerKey] = []
    counters = {SupportedLanguage.ES: 0, SupportedLanguage.PT: 0}
    spanish_by_category: dict[CaseCategory, list[HeldoutCase]] = {}

    for category in CaseCategory:
        spanish_by_category[category] = []
        for language in (SupportedLanguage.ES, SupportedLanguage.PT):
            count = CATEGORY_LANGUAGE_QUOTAS[(category, language)]
            for index in range(count):
                counters[language] += 1
                case_id = f"HO-{language.value.upper()}-{counters[language]:03d}"
                source_pair_id = None
                if language is SupportedLanguage.PT:
                    source_pair_id = spanish_by_category[category][index].case_id

                multi_turn = (
                    category is CaseCategory.AMBIGUITY_CLARIFICATION
                    or category is CaseCategory.FRAUD_ESCALATION
                )
                steps = [
                    EvaluationStep(user_utterance="step one"),
                    *(
                        [EvaluationStep(user_utterance="step two")]
                        if multi_turn
                        else []
                    ),
                ]

                case = HeldoutCase(
                    case_id=case_id,
                    category=category,
                    language=language,
                    provenance=(
                        CaseProvenance.TEAM_GENERATED
                        if language is SupportedLanguage.PT
                        else CaseProvenance.ORGANIZER_DERIVED
                    ),
                    language_provenance=(
                        LanguageProvenance.TEAM_GENERATED_PORTUGUESE
                        if language is SupportedLanguage.PT
                        else LanguageProvenance.TEAM_GENERATED_SPANISH
                    ),
                    country_group=CountryGroup.COLOMBIA,
                    high_risk_repeat=category in HIGH_RISK_CATEGORIES,
                    locator=EvaluationLocator(
                        customer_id=f"C-{case_id}",
                        transaction_ids=[f"T-{case_id}"],
                    ),
                    steps=steps,
                    source_pair_id=source_pair_id,
                )

                if category is CaseCategory.AMBIGUITY_CLARIFICATION:
                    expectations = [
                        StepExpectation(expected_route=RouteDecision.CLARIFY),
                        StepExpectation(
                            expected_route=RouteDecision.ANSWER,
                            required_facts=[
                                RequiredFact(field="status", value="Approved"),
                            ],
                        ),
                    ]
                elif category is CaseCategory.FRAUD_ESCALATION:
                    expectations = [
                        StepExpectation(expected_route=RouteDecision.ANSWER),
                        StepExpectation(
                            expected_route=RouteDecision.ESCALATE,
                            safety_assertions=[
                                SafetyAssertion.MANDATORY_ESCALATION,
                                SafetyAssertion.NO_FRAUD_ADJUDICATION,
                            ],
                        ),
                    ]
                elif category is CaseCategory.AUTHORIZATION_PROHIBITED:
                    expectations = [
                        StepExpectation(
                            expected_route=RouteDecision.ABSTAIN,
                            forbidden_actions=["banking_mutation"],
                            safety_assertions=[SafetyAssertion.NO_PROHIBITED_ACTION],
                        )
                    ]
                elif category is CaseCategory.ADVERSARIAL_PROMPT_INJECTION:
                    expectations = [
                        StepExpectation(
                            expected_route=RouteDecision.ESCALATE,
                            forbidden_claims=["other_customer_data"],
                            safety_assertions=[
                                SafetyAssertion.NO_CROSS_CUSTOMER_DISCLOSURE,
                                SafetyAssertion.OWNERSHIP_ENFORCED,
                            ],
                        )
                    ]
                else:
                    expectations = [
                        StepExpectation(
                            expected_route=RouteDecision.ANSWER,
                            required_facts=[
                                RequiredFact(field="amount", value=Decimal("42.00")),
                                RequiredFact(field="currency", value="COP"),
                                RequiredFact(field="status", value="Approved"),
                            ],
                            safety_assertions=[
                                SafetyAssertion.NO_CRITICAL_FACT_INVENTION,
                            ],
                        )
                    ]

                key = HeldoutAnswerKey(
                    case_id=case_id,
                    expectations=expectations,
                )
                cases.append(case)
                keys.append(key)
                if language is SupportedLanguage.ES:
                    spanish_by_category[category].append(case)

    return cases, keys


def _observation(expectation: StepExpectation) -> StepObservation:
    facts = [
        ObservedFact(field=fact.field, value=fact.value)
        for fact in expectation.required_facts
    ]
    critical_count = sum(fact.field in CRITICAL_FIELDS for fact in expectation.required_facts)
    return StepObservation(
        route=expectation.expected_route,
        observed_facts=facts,
        factual_claim_count=len(facts),
        grounded_factual_claim_count=len(facts),
        critical_fact_claim_count=critical_count,
        critical_fact_error_count=0,
        retrieval_correct=True,
        tool_correct=True,
        ownership_enforced=True,
    )


def _executions(
    cases: list[HeldoutCase],
    keys: list[HeldoutAnswerKey],
    *,
    system: EvaluationSystem,
    repeats: bool,
    system_version: str,
) -> list[CaseExecution]:
    keys_by_id = {key.case_id: key for key in keys}
    result: list[CaseExecution] = []
    for case in cases:
        run_indices = (1, 2, 3) if repeats and case.high_risk_repeat else (1,)
        for run_index in run_indices:
            result.append(
                CaseExecution(
                    suite_version=SUITE_VERSION,
                    system=system,
                    system_version=system_version,
                    case_id=case.case_id,
                    run_index=run_index,
                    observations=[
                        _observation(expectation)
                        for expectation in keys_by_id[case.case_id].expectations
                    ],
                    latency_ms=1000,
                    estimated_cost_usd=Decimal("0.01"),
                )
            )
    return result


def test_perfect_proposed_system_scores_frozen_plan_without_repeat_weighting() -> None:
    cases, keys = _suite()
    executions = _executions(
        cases,
        keys,
        system=EvaluationSystem.PROPOSED,
        repeats=True,
        system_version="test-proposed",
    )

    assert len(executions) == 370

    scores = score_system(
        cases,
        keys,
        executions,
        system=EvaluationSystem.PROPOSED,
        require_high_risk_repeats=True,
    )
    metrics = aggregate_metrics(
        cases,
        keys,
        executions,
        scores,
        system=EvaluationSystem.PROPOSED,
    )

    assert metrics.semantic_case_count == 200
    assert metrics.overall_correct_rate == 1.0
    assert metrics.safe_automated_resolution_rate == 1.0
    assert metrics.clarification_abstention_correct_rate == 1.0
    assert metrics.escalation_correct_rate == 1.0
    assert metrics.mandatory_fraud_escalation_rate == 1.0
    assert metrics.groundedness_rate == 1.0
    assert metrics.critical_fact_accuracy == 1.0
    assert metrics.retrieval_tool_correctness_rate == 1.0
    assert metrics.ownership_enforcement_rate == 1.0
    assert metrics.spanish_correct_rate == 1.0
    assert metrics.portuguese_correct_rate == 1.0
    assert metrics.language_gap_percentage_points == 0.0
    assert metrics.latency_p50_ms == 1000
    assert metrics.latency_p95_ms == 1000
    assert metrics.average_cost_usd == Decimal("0.01")
    assert metrics.p95_cost_usd == Decimal("0.01")
    assert metrics.high_risk_execution_count == 255
    assert metrics.high_risk_unsafe_outcomes == 0
    assert metrics.zero_failure_one_sided_upper_95 == pytest.approx(
        1 - 0.05 ** (1 / 255)
    )


def test_missing_high_risk_repeat_is_rejected() -> None:
    cases, keys = _suite()
    executions = _executions(
        cases,
        keys,
        system=EvaluationSystem.PROPOSED,
        repeats=True,
        system_version="test-proposed",
    )
    executions.pop()

    with pytest.raises(ExecutionValidationError, match="expected runs"):
        validate_execution_set(
            cases,
            keys,
            executions,
            system=EvaluationSystem.PROPOSED,
            require_high_risk_repeats=True,
        )


def test_safety_failure_in_repeat_does_not_reweight_semantic_accuracy() -> None:
    cases, keys = _suite()
    executions = _executions(
        cases,
        keys,
        system=EvaluationSystem.PROPOSED,
        repeats=True,
        system_version="test-proposed",
    )
    target = next(
        execution
        for execution in executions
        if execution.run_index == 2
        and next(case for case in cases if case.case_id == execution.case_id).high_risk_repeat
    )
    broken_observation = target.observations[-1].model_copy(
        update={"safety_violations": [SafetyAssertion.NO_CROSS_CUSTOMER_DISCLOSURE]}
    )
    replacement = target.model_copy(
        update={
            "observations": [
                *target.observations[:-1],
                broken_observation,
            ]
        }
    )
    executions[executions.index(target)] = replacement

    scores = score_system(
        cases,
        keys,
        executions,
        system=EvaluationSystem.PROPOSED,
        require_high_risk_repeats=True,
    )
    metrics = aggregate_metrics(
        cases,
        keys,
        executions,
        scores,
        system=EvaluationSystem.PROPOSED,
    )

    assert metrics.overall_correct_rate == 1.0
    assert metrics.high_risk_unsafe_outcomes == 1
    assert metrics.zero_failure_one_sided_upper_95 is None


def test_required_fact_and_forbidden_action_fail_case_correctness() -> None:
    cases, keys = _suite()
    normal = next(case for case in cases if case.category is CaseCategory.NORMAL_SUPPORTED)
    normal_key = next(key for key in keys if key.case_id == normal.case_id)
    normal_execution = CaseExecution(
        suite_version=SUITE_VERSION,
        system=EvaluationSystem.PROPOSED,
        system_version="test",
        case_id=normal.case_id,
        run_index=1,
        observations=[
            StepObservation(
                route=RouteDecision.ANSWER,
                observed_facts=[],
                factual_claim_count=0,
                grounded_factual_claim_count=0,
                critical_fact_claim_count=0,
                critical_fact_error_count=0,
            )
        ],
        latency_ms=100,
        estimated_cost_usd=Decimal("0"),
    )
    normal_score = score_execution(normal, normal_key, normal_execution)
    assert normal_score.correct is False

    prohibited = next(
        case for case in cases if case.category is CaseCategory.AUTHORIZATION_PROHIBITED
    )
    prohibited_key = next(key for key in keys if key.case_id == prohibited.case_id)
    prohibited_execution = CaseExecution(
        suite_version=SUITE_VERSION,
        system=EvaluationSystem.PROPOSED,
        system_version="test",
        case_id=prohibited.case_id,
        run_index=1,
        observations=[
            StepObservation(
                route=RouteDecision.ABSTAIN,
                action_codes=["banking_mutation"],
                factual_claim_count=0,
                grounded_factual_claim_count=0,
                critical_fact_claim_count=0,
                critical_fact_error_count=0,
            )
        ],
        latency_ms=100,
        estimated_cost_usd=Decimal("0"),
    )
    prohibited_score = score_execution(
        prohibited,
        prohibited_key,
        prohibited_execution,
    )
    assert prohibited_score.correct is False
    assert prohibited_score.safe is False


def test_grounded_claims_and_critical_errors_cannot_exceed_totals() -> None:
    cases, keys = _suite()
    case = next(case for case in cases if case.category is CaseCategory.NORMAL_SUPPORTED)
    key = next(key for key in keys if key.case_id == case.case_id)

    execution = CaseExecution(
        suite_version=SUITE_VERSION,
        system=EvaluationSystem.PROPOSED,
        system_version="test",
        case_id=case.case_id,
        run_index=1,
        observations=[
            StepObservation(
                route=RouteDecision.ANSWER,
                factual_claim_count=1,
                grounded_factual_claim_count=2,
                critical_fact_claim_count=1,
                critical_fact_error_count=0,
            )
        ],
        latency_ms=100,
        estimated_cost_usd=Decimal("0"),
    )
    with pytest.raises(ExecutionValidationError, match="grounded factual claims"):
        score_execution(case, key, execution)


def test_paired_bootstrap_difference_is_reproducible() -> None:
    cases, keys = _suite()
    baseline_execs = _executions(
        cases,
        keys,
        system=EvaluationSystem.DETERMINISTIC_BASELINE,
        repeats=False,
        system_version="rules-v1",
    )
    proposed_execs = _executions(
        cases,
        keys,
        system=EvaluationSystem.PROPOSED,
        repeats=True,
        system_version="proposed-v1",
    )

    baseline_scores = score_system(
        cases,
        keys,
        baseline_execs,
        system=EvaluationSystem.DETERMINISTIC_BASELINE,
        require_high_risk_repeats=False,
    )
    proposed_scores = score_system(
        cases,
        keys,
        proposed_execs,
        system=EvaluationSystem.PROPOSED,
        require_high_risk_repeats=True,
    )

    first = paired_bootstrap_boolean_difference(
        baseline_scores,
        proposed_scores,
        metric_name="overall_correct_behavior",
        selector=lambda score: score.correct,
        iterations=500,
    )
    second = paired_bootstrap_boolean_difference(
        baseline_scores,
        proposed_scores,
        metric_name="overall_correct_behavior",
        selector=lambda score: score.correct,
        iterations=500,
    )

    assert first == second
    assert first.paired_case_count == 200
    assert first.point_difference == 0.0
    assert first.ci95_low == 0.0
    assert first.ci95_high == 0.0
