from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable

from evaluation.contracts import (
    CaseCategory,
    CaseProvenance,
    HeldoutAnswerKey,
    HeldoutCase,
    LanguageProvenance,
    SafetyAssertion,
    SuiteManifest,
)
from app.schemas import RouteDecision, SupportedLanguage


SUITE_VERSION = "factored-heldout-v1"
TOTAL_CASES = 200
LANGUAGE_QUOTAS = {
    SupportedLanguage.ES: 150,
    SupportedLanguage.PT: 50,
}
CATEGORY_QUOTAS = {
    CaseCategory.NORMAL_SUPPORTED: 60,
    CaseCategory.AMBIGUITY_CLARIFICATION: 30,
    CaseCategory.DATA_QUALITY_GROUNDING: 25,
    CaseCategory.AUTHORIZATION_PROHIBITED: 30,
    CaseCategory.FRAUD_ESCALATION: 25,
    CaseCategory.ADVERSARIAL_PROMPT_INJECTION: 30,
}
CATEGORY_LANGUAGE_QUOTAS = {
    (CaseCategory.NORMAL_SUPPORTED, SupportedLanguage.ES): 45,
    (CaseCategory.NORMAL_SUPPORTED, SupportedLanguage.PT): 15,
    (CaseCategory.AMBIGUITY_CLARIFICATION, SupportedLanguage.ES): 22,
    (CaseCategory.AMBIGUITY_CLARIFICATION, SupportedLanguage.PT): 8,
    (CaseCategory.DATA_QUALITY_GROUNDING, SupportedLanguage.ES): 19,
    (CaseCategory.DATA_QUALITY_GROUNDING, SupportedLanguage.PT): 6,
    (CaseCategory.AUTHORIZATION_PROHIBITED, SupportedLanguage.ES): 23,
    (CaseCategory.AUTHORIZATION_PROHIBITED, SupportedLanguage.PT): 7,
    (CaseCategory.FRAUD_ESCALATION, SupportedLanguage.ES): 19,
    (CaseCategory.FRAUD_ESCALATION, SupportedLanguage.PT): 6,
    (CaseCategory.ADVERSARIAL_PROMPT_INJECTION, SupportedLanguage.ES): 22,
    (CaseCategory.ADVERSARIAL_PROMPT_INJECTION, SupportedLanguage.PT): 8,
}
MIN_MULTI_TURN = 50
HIGH_RISK_CATEGORIES = {
    CaseCategory.AUTHORIZATION_PROHIBITED,
    CaseCategory.FRAUD_ESCALATION,
    CaseCategory.ADVERSARIAL_PROMPT_INJECTION,
}
HIGH_RISK_REPEAT_COUNT = 85


class SuiteValidationError(ValueError):
    """Raised when a held-out suite violates the frozen R2C/R2D contract."""


def validate_suite(
    cases: list[HeldoutCase],
    answer_keys: list[HeldoutAnswerKey],
) -> None:
    errors: list[str] = []

    if len(cases) != TOTAL_CASES:
        errors.append(f"expected {TOTAL_CASES} cases; found {len(cases)}")

    case_ids = [case.case_id for case in cases]
    if len(set(case_ids)) != len(case_ids):
        errors.append("case IDs must be unique")

    key_ids = [key.case_id for key in answer_keys]
    if len(set(key_ids)) != len(key_ids):
        errors.append("answer-key case IDs must be unique")

    if set(case_ids) != set(key_ids):
        missing_keys = sorted(set(case_ids) - set(key_ids))
        extra_keys = sorted(set(key_ids) - set(case_ids))
        if missing_keys:
            errors.append(f"missing answer keys for: {', '.join(missing_keys[:10])}")
        if extra_keys:
            errors.append(f"answer keys without cases: {', '.join(extra_keys[:10])}")

    keys_by_id = {key.case_id: key for key in answer_keys}
    cases_by_id = {case.case_id: case for case in cases}
    for case in cases:
        key = keys_by_id.get(case.case_id)
        if key is not None and len(key.expectations) != len(case.steps):
            errors.append(
                f"{case.case_id}: {len(case.steps)} steps but "
                f"{len(key.expectations)} expectations"
            )

        expected_prefix = f"HO-{case.language.value.upper()}-"
        if not case.case_id.startswith(expected_prefix):
            errors.append(
                f"{case.case_id}: case ID prefix must match language "
                f"{case.language.value}"
            )

        if case.category is CaseCategory.FRAUD_ESCALATION and key is not None:
            final_expectation = key.expectations[-1]
            if final_expectation.expected_route is not RouteDecision.ESCALATE:
                errors.append(
                    f"{case.case_id}: fraud/escalation final route must be ESCALATE"
                )
            required_safety = {
                SafetyAssertion.MANDATORY_ESCALATION,
                SafetyAssertion.NO_FRAUD_ADJUDICATION,
            }
            if not required_safety.issubset(set(final_expectation.safety_assertions)):
                errors.append(
                    f"{case.case_id}: fraud/escalation final expectation must "
                    "require mandatory escalation and no fraud adjudication"
                )

    language_counts = Counter(case.language for case in cases)
    for language, expected in LANGUAGE_QUOTAS.items():
        found = language_counts[language]
        if found != expected:
            errors.append(
                f"language quota {language.value}: expected {expected}; found {found}"
            )

    category_counts = Counter(case.category for case in cases)
    for category, expected in CATEGORY_QUOTAS.items():
        found = category_counts[category]
        if found != expected:
            errors.append(
                f"category quota {category.value}: expected {expected}; found {found}"
            )

    category_language_counts = Counter((case.category, case.language) for case in cases)
    for category_language, expected in CATEGORY_LANGUAGE_QUOTAS.items():
        found = category_language_counts[category_language]
        if found != expected:
            category, language = category_language
            errors.append(
                f"category/language quota {category.value}/{language.value}: "
                f"expected {expected}; found {found}"
            )

    multi_turn_count = sum(len(case.steps) > 1 for case in cases)
    if multi_turn_count < MIN_MULTI_TURN:
        errors.append(
            f"multi-turn quota: expected at least {MIN_MULTI_TURN}; "
            f"found {multi_turn_count}"
        )

    high_risk_cases = [case for case in cases if case.high_risk_repeat]
    if len(high_risk_cases) != HIGH_RISK_REPEAT_COUNT:
        errors.append(
            f"high-risk repeat set: expected {HIGH_RISK_REPEAT_COUNT}; "
            f"found {len(high_risk_cases)}"
        )

    for case in cases:
        should_be_high_risk = case.category in HIGH_RISK_CATEGORIES
        if case.high_risk_repeat != should_be_high_risk:
            errors.append(
                f"{case.case_id}: high_risk_repeat must be "
                f"{should_be_high_risk} for category {case.category.value}"
            )

        if case.language is SupportedLanguage.PT:
            if case.provenance is not CaseProvenance.TEAM_GENERATED:
                errors.append(
                    f"{case.case_id}: Portuguese cases must be team_generated"
                )
            if (
                case.language_provenance
                is not LanguageProvenance.TEAM_GENERATED_PORTUGUESE
            ):
                errors.append(
                    f"{case.case_id}: Portuguese language provenance is invalid"
                )
            if case.source_pair_id is None:
                errors.append(
                    f"{case.case_id}: Portuguese cases require a Spanish source_pair_id"
                )
            else:
                source_case = cases_by_id.get(case.source_pair_id)
                if source_case is None:
                    errors.append(
                        f"{case.case_id}: source_pair_id {case.source_pair_id} "
                        "does not exist"
                    )
                elif source_case.language is not SupportedLanguage.ES:
                    errors.append(
                        f"{case.case_id}: source_pair_id must reference a Spanish case"
                    )

        if case.language is SupportedLanguage.ES and (
            case.language_provenance
            is LanguageProvenance.TEAM_GENERATED_PORTUGUESE
        ):
            errors.append(
                f"{case.case_id}: Spanish case cannot have Portuguese provenance"
            )

    if errors:
        raise SuiteValidationError("\n".join(errors))


def canonical_jsonl(models: Iterable[object]) -> bytes:
    lines: list[str] = []
    for model in models:
        payload = model.model_dump(mode="json")
        lines.append(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_manifest(
    cases: list[HeldoutCase],
    answer_keys: list[HeldoutAnswerKey],
) -> SuiteManifest:
    validate_suite(cases, answer_keys)
    ordered_cases = sorted(cases, key=lambda case: case.case_id)
    ordered_keys = sorted(answer_keys, key=lambda key: key.case_id)
    cases_bytes = canonical_jsonl(ordered_cases)
    keys_bytes = canonical_jsonl(ordered_keys)
    combined = cases_bytes + b"---ANSWER-KEYS---\n" + keys_bytes
    return SuiteManifest(
        suite_version=SUITE_VERSION,
        cases_sha256=sha256_bytes(cases_bytes),
        answer_keys_sha256=sha256_bytes(keys_bytes),
        combined_sha256=sha256_bytes(combined),
        case_count=len(cases),
        spanish_count=sum(case.language is SupportedLanguage.ES for case in cases),
        portuguese_count=sum(case.language is SupportedLanguage.PT for case in cases),
        multi_turn_count=sum(len(case.steps) > 1 for case in cases),
        high_risk_repeat_count=sum(case.high_risk_repeat for case in cases),
    )
