from app.unauthorized_grammar import (
    PropositionFamily,
    PropositionMode,
    build_positive_propositions,
    resolve_positive_propositions,
)


def _mode_for_family(message: str, language: str, family: PropositionFamily) -> str:
    propositions = resolve_positive_propositions(message, language)
    return next(
        proposition.mode
        for proposition in propositions
        if proposition.family is family
    )


def test_b3_1_positive_builder_remains_unresolved() -> None:
    propositions = build_positive_propositions(
        "No hice la transferencia.",
        "es",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )
    assert item.mode == "unresolved"
    assert item.exclusion_provenance == ()


def test_b3_1_plain_positive_resolves_assertive() -> None:
    assert (
        _mode_for_family(
            "No hice la transferencia.",
            "es",
            PropositionFamily.PERFORMANCE_DENIAL,
        )
        == PropositionMode.ASSERTIVE.value
    )


def test_b3_1_conditional_scope_stops_at_comma() -> None:
    propositions = resolve_positive_propositions(
        "Si no hice la transferencia, este cargo no es mío.",
        "es",
    )

    performance = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )
    ownership = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert performance.mode == PropositionMode.HYPOTHETICAL.value
    assert performance.exclusion_provenance
    assert ownership.mode == PropositionMode.ASSERTIVE.value
    assert ownership.exclusion_provenance == ()


def test_b3_1_uncertainty_scope_does_not_cross_contrast() -> None:
    propositions = resolve_positive_propositions(
        "Quizás no hice la transferencia, pero este cargo no es mío.",
        "es",
    )

    performance = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )
    ownership = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert performance.mode == PropositionMode.UNCERTAIN.value
    assert performance.exclusion_provenance
    assert ownership.mode == PropositionMode.ASSERTIVE.value


def test_b3_1_spanish_explicit_question_marks_questioned_proposition() -> None:
    assert (
        _mode_for_family(
            "¿No hice la transferencia?",
            "es",
            PropositionFamily.PERFORMANCE_DENIAL,
        )
        == PropositionMode.QUESTIONED.value
    )


def test_b3_1_portuguese_question_boundary_marks_questioned_proposition() -> None:
    assert (
        _mode_for_family(
            "Eu não fiz o Pix?",
            "pt",
            PropositionFamily.PERFORMANCE_DENIAL,
        )
        == PropositionMode.QUESTIONED.value
    )


def test_b3_1_conditional_precedes_question_mode_on_same_proposition() -> None:
    propositions = resolve_positive_propositions(
        "¿Si no hice la transferencia?",
        "es",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )

    assert item.mode == PropositionMode.HYPOTHETICAL.value
    assert any(
        provenance.startswith("M2:conditional:")
        for provenance in item.exclusion_provenance
    )
