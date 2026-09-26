from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import RouteDecision, SupportedLanguage
from evaluation.contracts import (
    CaseCategory,
    CaseProvenance,
    CountryGroup,
    EvaluationLocator,
    EvaluationStep,
    HeldoutAnswerKey,
    HeldoutCase,
    LanguageProvenance,
    RequiredFact,
    SafetyAssertion,
    StepExpectation,
)
from evaluation.suite import (
    CATEGORY_LANGUAGE_QUOTAS,
    HIGH_RISK_CATEGORIES,
    LANGUAGE_QUOTAS,
    SUITE_VERSION,
    SuiteValidationError,
    build_manifest,
    validate_suite,
)


def make_case(
    *,
    case_id: str = "HO-ES-001",
    category: CaseCategory = CaseCategory.NORMAL_SUPPORTED,
    language: SupportedLanguage = SupportedLanguage.ES,
    provenance: CaseProvenance = CaseProvenance.ORGANIZER_DERIVED,
    language_provenance: LanguageProvenance = LanguageProvenance.ORGANIZER_SPANISH,
    steps: int = 1,
) -> HeldoutCase:
    return HeldoutCase(
        case_id=case_id,
        category=category,
        language=language,
        provenance=provenance,
        language_provenance=language_provenance,
        country_group=CountryGroup.COLOMBIA,
        high_risk_repeat=category in HIGH_RISK_CATEGORIES,
        locator=EvaluationLocator(
            customer_id="customer-local-only",
            transaction_ids=["txn-local-only"],
        ),
        steps=[
            EvaluationStep(user_utterance=f"Utterance {index}")
            for index in range(steps)
        ],
    )


def make_key(case: HeldoutCase) -> HeldoutAnswerKey:
    return HeldoutAnswerKey(
        case_id=case.case_id,
        expectations=[
            StepExpectation(
                expected_route=RouteDecision.ANSWER,
                required_facts=[
                    RequiredFact(field="amount", value=Decimal("42.00"))
                ],
                safety_assertions=[SafetyAssertion.NO_CRITICAL_FACT_INVENTION],
            )
            for _ in case.steps
        ],
    )


def test_category_language_plan_sums_to_frozen_totals() -> None:
    assert sum(CATEGORY_LANGUAGE_QUOTAS.values()) == 200
    for language, expected in LANGUAGE_QUOTAS.items():
        assert (
            sum(
                count
                for (category, planned_language), count in CATEGORY_LANGUAGE_QUOTAS.items()
                if planned_language is language
            )
            == expected
        )


def test_portuguese_case_must_be_team_generated() -> None:
    case = make_case(
        case_id="HO-PT-001",
        language=SupportedLanguage.PT,
        provenance=CaseProvenance.ORGANIZER_DERIVED,
        language_provenance=LanguageProvenance.TEAM_GENERATED_PORTUGUESE,
    )
    key = make_key(case)

    with pytest.raises(SuiteValidationError, match="Portuguese cases must be team_generated"):
        validate_suite([case], [key])


def test_answer_key_step_count_must_match_case() -> None:
    case = make_case(steps=2)
    key = HeldoutAnswerKey(
        case_id=case.case_id,
        expectations=[
            StepExpectation(expected_route=RouteDecision.CLARIFY)
        ],
    )

    with pytest.raises(SuiteValidationError, match="steps but"):
        validate_suite([case], [key])


def test_case_contract_rejects_unknown_answer_key_fields() -> None:
    with pytest.raises(ValidationError):
        StepExpectation(
            expected_route=RouteDecision.ANSWER,
            expected_customer_id="forbidden-runtime-answer-key-field",
        )


def test_manifest_is_deterministic_for_identical_ordered_inputs() -> None:
    cases: list[HeldoutCase] = []
    keys: list[HeldoutAnswerKey] = []
    counters = {
        SupportedLanguage.ES: 0,
        SupportedLanguage.PT: 0,
    }

    for (category, language), count in CATEGORY_LANGUAGE_QUOTAS.items():
        for index in range(count):
            counters[language] += 1
            case_id = f"HO-{language.value.upper()}-{counters[language]:03d}"
            provenance = (
                CaseProvenance.TEAM_GENERATED
                if language is SupportedLanguage.PT
                else CaseProvenance.ORGANIZER_DERIVED
            )
            language_provenance = (
                LanguageProvenance.TEAM_GENERATED_PORTUGUESE
                if language is SupportedLanguage.PT
                else LanguageProvenance.ORGANIZER_SPANISH
            )
            step_count = 2 if len(cases) < 50 else 1
            case = make_case(
                case_id=case_id,
                category=category,
                language=language,
                provenance=provenance,
                language_provenance=language_provenance,
                steps=step_count,
            )
            cases.append(case)
            keys.append(make_key(case))

    first = build_manifest(cases, keys)
    second = build_manifest(cases, keys)

    assert first.suite_version == SUITE_VERSION
    assert first == second
    assert first.case_count == 200
    assert first.spanish_count == 150
    assert first.portuguese_count == 50
    assert first.multi_turn_count >= 50
    assert first.high_risk_repeat_count == 85
