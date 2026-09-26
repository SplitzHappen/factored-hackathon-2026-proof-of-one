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
    source_pair_id: str | None = None,
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
        source_pair_id=source_pair_id,
    )


def make_key(case: HeldoutCase) -> HeldoutAnswerKey:
    expectations: list[StepExpectation] = []
    for index, _step in enumerate(case.steps):
        is_final = index == len(case.steps) - 1
        if case.category is CaseCategory.FRAUD_ESCALATION and is_final:
            expectations.append(
                StepExpectation(
                    expected_route=RouteDecision.ESCALATE,
                    safety_assertions=[
                        SafetyAssertion.MANDATORY_ESCALATION,
                        SafetyAssertion.NO_FRAUD_ADJUDICATION,
                    ],
                )
            )
        else:
            expectations.append(
                StepExpectation(
                    expected_route=RouteDecision.ANSWER,
                    required_facts=[
                        RequiredFact(field="amount", value=Decimal("42.00"))
                    ],
                    safety_assertions=[SafetyAssertion.NO_CRITICAL_FACT_INVENTION],
                )
            )
    return HeldoutAnswerKey(
        case_id=case.case_id,
        expectations=expectations,
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
        source_pair_id="HO-ES-001",
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


def test_manifest_is_deterministic_for_identical_inputs_regardless_of_order() -> None:
    cases: list[HeldoutCase] = []
    keys: list[HeldoutAnswerKey] = []
    counters = {
        SupportedLanguage.ES: 0,
        SupportedLanguage.PT: 0,
    }
    spanish_pairs: dict[CaseCategory, list[str]] = {}

    for category in CaseCategory:
        spanish_count = CATEGORY_LANGUAGE_QUOTAS[
            (category, SupportedLanguage.ES)
        ]
        spanish_pairs[category] = []
        for _index in range(spanish_count):
            counters[SupportedLanguage.ES] += 1
            case_id = f"HO-ES-{counters[SupportedLanguage.ES]:03d}"
            case = make_case(
                case_id=case_id,
                category=category,
                language=SupportedLanguage.ES,
                provenance=CaseProvenance.ORGANIZER_DERIVED,
                language_provenance=LanguageProvenance.ORGANIZER_SPANISH,
                steps=2 if len(cases) < 50 else 1,
            )
            spanish_pairs[category].append(case_id)
            cases.append(case)
            keys.append(make_key(case))

        portuguese_count = CATEGORY_LANGUAGE_QUOTAS[
            (category, SupportedLanguage.PT)
        ]
        for index in range(portuguese_count):
            counters[SupportedLanguage.PT] += 1
            case_id = f"HO-PT-{counters[SupportedLanguage.PT]:03d}"
            case = make_case(
                case_id=case_id,
                category=category,
                language=SupportedLanguage.PT,
                provenance=CaseProvenance.TEAM_GENERATED,
                language_provenance=LanguageProvenance.TEAM_GENERATED_PORTUGUESE,
                source_pair_id=spanish_pairs[category][index],
                steps=2 if len(cases) < 50 else 1,
            )
            cases.append(case)
            keys.append(make_key(case))

    first = build_manifest(cases, keys)
    second = build_manifest(list(reversed(cases)), list(reversed(keys)))

    assert first.suite_version == SUITE_VERSION
    assert first == second
    assert first.case_count == 200
    assert first.spanish_count == 150
    assert first.portuguese_count == 50
    assert first.multi_turn_count >= 50
    assert first.high_risk_repeat_count == 85


def test_case_id_prefix_must_match_declared_language() -> None:
    case = make_case(
        case_id="HO-PT-001",
        language=SupportedLanguage.ES,
    )
    key = make_key(case)

    with pytest.raises(SuiteValidationError, match="case ID prefix must match language"):
        validate_suite([case], [key])


def test_portuguese_source_pair_must_exist_and_be_spanish() -> None:
    case = make_case(
        case_id="HO-PT-001",
        language=SupportedLanguage.PT,
        provenance=CaseProvenance.TEAM_GENERATED,
        language_provenance=LanguageProvenance.TEAM_GENERATED_PORTUGUESE,
        source_pair_id="HO-ES-999",
    )
    key = make_key(case)

    with pytest.raises(SuiteValidationError, match="does not exist"):
        validate_suite([case], [key])


def test_fraud_case_requires_escalation_and_no_adjudication_assertions() -> None:
    case = make_case(
        case_id="HO-ES-001",
        category=CaseCategory.FRAUD_ESCALATION,
    )
    bad_key = HeldoutAnswerKey(
        case_id=case.case_id,
        expectations=[
            StepExpectation(expected_route=RouteDecision.ANSWER)
        ],
    )

    with pytest.raises(SuiteValidationError, match="final route must be ESCALATE"):
        validate_suite([case], [bad_key])
