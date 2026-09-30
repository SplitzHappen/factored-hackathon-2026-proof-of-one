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

def test_b3_3_spanish_authorized_third_party_scope_is_nonassertive() -> None:
    propositions = resolve_positive_propositions(
        "Autoricé a mi hijo a hacer esta compra fraudulenta.",
        "es",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert item.mode == PropositionMode.AUTHORIZED_THIRD_PARTY.value
    assert item.exclusion_provenance == (
        "M6:authorized_third_party:authorize",
    )


def test_b3_3_portuguese_authorized_third_party_scope_is_nonassertive() -> None:
    propositions = resolve_positive_propositions(
        "Autorizei meu filho a fazer esta compra fraudulenta.",
        "pt",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert item.mode == PropositionMode.AUTHORIZED_THIRD_PARTY.value
    assert item.exclusion_provenance == (
        "M6:authorized_third_party:authorize",
    )


def test_b3_3_authorization_scope_does_not_suppress_later_assertion() -> None:
    propositions = resolve_positive_propositions(
        "Autoricé a mi hijo a hacer esta compra fraudulenta, "
        "pero este cargo no es mío.",
        "es",
    )
    fraud = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    ownership = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert fraud.mode == PropositionMode.AUTHORIZED_THIRD_PARTY.value
    assert ownership.mode == PropositionMode.ASSERTIVE.value
    assert ownership.exclusion_provenance == ()


def test_b3_3_exceeded_authorization_stays_assertive() -> None:
    cases = (
        ("Mi hermano gastó más de lo que autoricé.", "es"),
        ("Meu irmão gastou mais do que eu autorizei.", "pt"),
    )

    for message, language in cases:
        propositions = resolve_positive_propositions(message, language)
        item = next(
            proposition
            for proposition in propositions
            if proposition.rule == "P5-exceeded-authorization-amount"
        )
        assert item.mode == PropositionMode.ASSERTIVE.value
        assert item.exclusion_provenance == ()


def test_b3_3_limited_grant_does_not_suppress_out_of_scope_purchase() -> None:
    cases = (
        (
            "Le di la tarjeta a mi hijo para la gasolina "
            "y compró otras cosas sin permiso.",
            "es",
        ),
        (
            "Dei o cartão ao meu irmão para gasolina "
            "e ele comprou outras coisas sem permissão.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = resolve_positive_propositions(message, language)
        item = next(
            proposition
            for proposition in propositions
            if proposition.rule == "P5-exceeded-authorization-purpose"
        )
        assert item.mode == PropositionMode.ASSERTIVE.value
        assert item.exclusion_provenance == ()


def test_b3_3_questioned_authorization_is_not_an_affirmative_grant() -> None:
    propositions = resolve_positive_propositions(
        "¿Autoricé a mi hijo a hacer esta compra fraudulenta?",
        "es",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert item.mode == PropositionMode.QUESTIONED.value
    assert item.exclusion_provenance == ("M8:explicit_question",)



def test_b3_3_recovery_does_not_change_b2_spanish_target_typing() -> None:
    propositions = build_positive_propositions(
        "Autoricé a mi hijo a hacer esta compra fraudulenta.",
        "es",
    )
    assert not any(
        proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
        for proposition in propositions
    )


def test_b3_3_recovery_requires_bounded_authorization_or_question_scope() -> None:
    propositions = resolve_positive_propositions(
        "Vi a mi hijo hacer esta compra fraudulenta.",
        "es",
    )
    assert not any(
        proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
        for proposition in propositions
    )


def test_b3_4_spanish_same_activity_performance_correction_retracts() -> None:
    propositions = resolve_positive_propositions(
        "No hice esta transferencia, pero sí la hice.",
        "es",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )

    assert item.mode == PropositionMode.RETRACTED.value
    assert item.retraction_provenance == ("M7:retraction:perform:pero",)


def test_b3_4_portuguese_same_activity_authorization_correction_retracts() -> None:
    propositions = resolve_positive_propositions(
        "Eu não autorizei esta compra, mas autorizei esta compra sim.",
        "pt",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.AUTHORIZATION_DENIAL
    )

    assert item.mode == PropositionMode.RETRACTED.value
    assert item.retraction_provenance == ("M7:retraction:authorize:mas",)


def test_b3_4_portuguese_ownership_correction_retracts() -> None:
    propositions = resolve_positive_propositions(
        "Esta transferência não é minha, mas é minha sim.",
        "pt",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert item.mode == PropositionMode.RETRACTED.value
    assert item.retraction_provenance == ("M7:retraction:own:mas",)


def test_b3_4_different_activity_referent_is_not_retracted() -> None:
    propositions = resolve_positive_propositions(
        "No hice esta transferencia, pero sí hice otra transferencia.",
        "es",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )

    assert item.mode == PropositionMode.ASSERTIVE.value
    assert item.retraction_provenance == ()


def test_b3_4_same_txid_correction_retracts() -> None:
    propositions = resolve_positive_propositions(
        "No hice DEMO-ES-0001, pero sí hice DEMO-ES-0001.",
        "es",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )

    assert item.mode == PropositionMode.RETRACTED.value


def test_b3_4_different_txid_correction_does_not_retract() -> None:
    propositions = resolve_positive_propositions(
        "No hice DEMO-ES-0001, pero sí hice DEMO-ES-0002.",
        "es",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )

    assert item.mode == PropositionMode.ASSERTIVE.value
    assert item.retraction_provenance == ()


def test_b3_4_retracted_first_assertion_does_not_suppress_new_assertion() -> None:
    propositions = resolve_positive_propositions(
        "No hice esta transferencia, pero sí la hice, "
        "y esta otra compra no es mía.",
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

    assert performance.mode == PropositionMode.RETRACTED.value
    assert ownership.mode == PropositionMode.ASSERTIVE.value
    assert ownership.retraction_provenance == ()


def test_b3_4_spanish_reported_prior_belief_is_nonassertive() -> None:
    propositions = resolve_positive_propositions(
        "Pensé que no hice esta transferencia.",
        "es",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )

    assert item.mode == PropositionMode.REPORTED_PRIOR_BELIEF.value
    assert item.exclusion_provenance == (
        "R7:reported_prior_belief:pense_que",
    )


def test_b3_4_portuguese_reported_prior_belief_is_nonassertive() -> None:
    propositions = resolve_positive_propositions(
        "Achei que eu não fiz esta transferência.",
        "pt",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )

    assert item.mode == PropositionMode.REPORTED_PRIOR_BELIEF.value
    assert item.exclusion_provenance == (
        "R7:reported_prior_belief:achei_que",
    )


def test_b3_4_reported_prior_belief_does_not_suppress_later_assertion() -> None:
    propositions = resolve_positive_propositions(
        "Pensé que no hice esta transferencia, "
        "pero esta otra compra no es mía.",
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

    assert performance.mode == PropositionMode.REPORTED_PRIOR_BELIEF.value
    assert ownership.mode == PropositionMode.ASSERTIVE.value


def test_b3_4_portuguese_ia_dizer_frame_is_reported_prior_belief() -> None:
    propositions = resolve_positive_propositions(
        "Ia dizer que eu não fiz esta transferência.",
        "pt",
    )
    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.PERFORMANCE_DENIAL
    )

    assert item.mode == PropositionMode.REPORTED_PRIOR_BELIEF.value
