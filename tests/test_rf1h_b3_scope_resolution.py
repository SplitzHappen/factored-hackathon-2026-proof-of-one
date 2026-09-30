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



def test_b3_2_spanish_security_question_resolves_information_request() -> None:
    propositions = resolve_positive_propositions(
        "¿Qué alerta recibo por una transferencia que no autoricé?",
        "es",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.AUTHORIZATION_DENIAL
    )

    assert item.mode == PropositionMode.INFORMATION_REQUEST.value
    assert item.exclusion_provenance == (
        "M4:security_information_request",
    )


def test_b3_2_portuguese_security_question_resolves_information_request() -> None:
    propositions = resolve_positive_propositions(
        "Que alerta recebo por um Pix que eu não autorizei?",
        "pt",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.AUTHORIZATION_DENIAL
    )

    assert item.mode == PropositionMode.INFORMATION_REQUEST.value
    assert item.exclusion_provenance == (
        "M4:security_information_request",
    )


def test_b3_2_information_request_does_not_suppress_later_assertion() -> None:
    propositions = resolve_positive_propositions(
        "¿Qué alerta recibo por una transferencia que no autoricé? "
        "Este cargo no es mío.",
        "es",
    )

    authorization = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.AUTHORIZATION_DENIAL
    )
    ownership = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert authorization.mode == PropositionMode.INFORMATION_REQUEST.value
    assert ownership.mode == PropositionMode.ASSERTIVE.value
    assert ownership.exclusion_provenance == ()


def test_b3_2_descriptor_target_remains_nonpositive_in_b2() -> None:
    cases = (
        ("No reconozco el nombre del comercio.", "es"),
        ("Eu não reconheço o nome do comércio.", "pt"),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.ACTIVITY_NONRECOGNITION
            for proposition in propositions
        )


def test_b3_2_descriptor_clarification_does_not_suppress_later_assertion() -> None:
    propositions = resolve_positive_propositions(
        "No reconozco el nombre del comercio. Este cargo no es mío.",
        "es",
    )

    assert not any(
        proposition.family is PropositionFamily.ACTIVITY_NONRECOGNITION
        for proposition in propositions
    )
    ownership = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.OWNERSHIP_DENIAL
    )
    assert ownership.mode == PropositionMode.ASSERTIVE.value
