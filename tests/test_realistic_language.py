from __future__ import annotations

from app.schemas import SupportedLanguage
from evaluation.realistic_language import (
    CANONICAL_REALISTIC_LANGUAGE_SHA256,
    assert_realistic_language_v1_evidence_use,
    load_realistic_language_suite,
)


def test_realistic_language_freeze_identity_and_counts() -> None:
    cases, manifest = load_realistic_language_suite()

    assert manifest.suite_version == "factored-realistic-language-v1"
    assert manifest.cases_sha256 == CANONICAL_REALISTIC_LANGUAGE_SHA256
    assert manifest.case_count == 32
    assert manifest.spanish_count == 16
    assert manifest.portuguese_count == 16
    assert manifest.paired_count == 16
    assert len(cases) == 32
    assert len({case.case_id for case in cases}) == 32
    assert len({case.source_pair_id for case in cases}) == 16


def test_realistic_language_freeze_is_public_synthetic_only() -> None:
    cases, manifest = load_realistic_language_suite()

    assert manifest.organizer_data_used is False
    assert manifest.portuguese_native_reviewed is False
    assert all(case.organizer_data_used is False for case in cases)
    assert all(case.native_language_reviewed is False for case in cases)
    assert all("C00" not in case.message for case in cases)
    assert all("P00" not in case.message for case in cases)
    assert all("MISSING-" not in case.message for case in cases)


def test_realistic_language_freeze_is_distinct_from_legacy_template_surfaces() -> None:
    _, manifest = load_realistic_language_suite()

    assert manifest.max_legacy_surface_similarity == 0.657143
    assert manifest.max_legacy_surface_similarity < 0.70


def test_realistic_language_pairs_cover_both_languages() -> None:
    cases, _ = load_realistic_language_suite()

    by_pair: dict[str, set[SupportedLanguage]] = {}
    for case in cases:
        by_pair.setdefault(case.source_pair_id, set()).add(case.language)

    assert set(by_pair) == {f"PAIR-{index:03d}" for index in range(1, 17)}
    assert all(
        languages == {SupportedLanguage.ES, SupportedLanguage.PT}
        for languages in by_pair.values()
    )


def test_realistic_language_freeze_contains_positive_unauthorized_cases_in_both_languages() -> None:
    cases, _ = load_realistic_language_suite()

    positives = [case for case in cases if case.unauthorized_activity_asserted]

    assert len(positives) == 6
    assert {case.language for case in positives} == {
        SupportedLanguage.ES,
        SupportedLanguage.PT,
    }
    assert sum(case.language is SupportedLanguage.ES for case in positives) == 3
    assert sum(case.language is SupportedLanguage.PT for case in positives) == 3


def test_realistic_language_v1_allows_selection_and_stress_only() -> None:
    assert_realistic_language_v1_evidence_use("provider_selection")
    assert_realistic_language_v1_evidence_use("language_stress")


def test_realistic_language_v1_rejects_baseline_uplift_evidence() -> None:
    import pytest

    with pytest.raises(ValueError, match="uplift claims require"):
        assert_realistic_language_v1_evidence_use("baseline_uplift")

    with pytest.raises(ValueError, match="selection/development evidence only"):
        assert_realistic_language_v1_evidence_use("deterministic_baseline_evidence")
