import pytest

from app.unauthorized_grammar import (
    PredicateFamily,
    PropositionFamily,
    PropositionMode,
    analyze_foundation,
    resolve_positive_propositions,
)


def _family_items(
    message: str,
    language: str,
    family: PropositionFamily,
):
    return tuple(
        proposition
        for proposition in resolve_positive_propositions(message, language)
        if proposition.family is family
    )


def _mode(
    message: str,
    language: str,
    family: PropositionFamily,
) -> str:
    items = _family_items(message, language, family)
    assert items
    return items[0].mode


def _assert_assertive_family(
    message: str,
    language: str,
    family: PropositionFamily,
) -> None:
    items = _family_items(message, language, family)
    assert items
    assert any(item.mode == PropositionMode.ASSERTIVE.value for item in items)


@pytest.mark.parametrize(
    ("message", "language", "family", "person", "number", "tense"),
    [
        (
            "Nosotros no autorizamos estas transferencias.",
            "es",
            PredicateFamily.AUTHORIZE,
            1,
            "plural",
            None,
        ),
        (
            "Nós não fizemos estas compras.",
            "pt",
            PredicateFamily.PERFORM,
            1,
            "plural",
            "preterite",
        ),
        (
            "Eu não tinha feito esta compra.",
            "pt",
            PredicateFamily.PERFORM,
            1,
            "singular",
            "pluperfect",
        ),
        (
            "La transferencia no vino de mí.",
            "es",
            PredicateFamily.ORIGINATE,
            3,
            "singular",
            "preterite",
        ),
    ],
)
def test_b4_predicate_family_morphology(
    message: str,
    language: str,
    family: PredicateFamily,
    person: int,
    number: str,
    tense: str | None,
) -> None:
    analysis = analyze_foundation(message, language)
    matches = [
        predicate
        for predicate in analysis.predicates
        if predicate.form.family is family
        and predicate.form.person == person
        and predicate.form.number == number
    ]

    assert matches
    if tense is not None:
        assert any(
            predicate.form.tense_aspect == tense
            for predicate in matches
        )


@pytest.mark.parametrize(
    ("message", "language", "family"),
    [
        (
            "Estas transferencias no son mías.",
            "es",
            PropositionFamily.OWNERSHIP_DENIAL,
        ),
        (
            "Estas compras não são minhas.",
            "pt",
            PropositionFamily.OWNERSHIP_DENIAL,
        ),
        (
            "Sin mi permiso, mi prima usó mi tarjeta.",
            "es",
            PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE,
        ),
        (
            "Sem minha permissão, meu primo usou meu cartão.",
            "pt",
            PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE,
        ),
        (
            "Estas compras fraudulentas aparecieron hoy.",
            "es",
            PropositionFamily.FRAUD_CHARACTERIZATION,
        ),
        (
            "Estas compras fraudulentas apareceram hoje.",
            "pt",
            PropositionFamily.FRAUD_CHARACTERIZATION,
        ),
        (
            "Esta operación no la reconozco.",
            "es",
            PropositionFamily.ACTIVITY_NONRECOGNITION,
        ),
        (
            "Esta transação, não a reconheço.",
            "pt",
            PropositionFamily.ACTIVITY_NONRECOGNITION,
        ),
        (
            "Me clonaron la tarjeta.",
            "es",
            PropositionFamily.COMPROMISE_LINKED_ACTIVITY,
        ),
        (
            "Minha conta foi clonada.",
            "pt",
            PropositionFamily.COMPROMISE_LINKED_ACTIVITY,
        ),
    ],
)
def test_b4_structural_positive_examples_remain_assertive(
    message: str,
    language: str,
    family: PropositionFamily,
) -> None:
    _assert_assertive_family(message, language, family)


def test_b4_hypothetical_scope_is_proposition_local() -> None:
    propositions = resolve_positive_propositions(
        "Si no autoricé esta compra, este débito no es mío.",
        "es",
    )
    authorization = next(
        item
        for item in propositions
        if item.family is PropositionFamily.AUTHORIZATION_DENIAL
    )
    ownership = next(
        item
        for item in propositions
        if item.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert authorization.mode == PropositionMode.HYPOTHETICAL.value
    assert ownership.mode == PropositionMode.ASSERTIVE.value


def test_b4_uncertainty_scope_stops_before_independent_assertion() -> None:
    propositions = resolve_positive_propositions(
        "Quizás no reconozco esta transferencia, "
        "pero este cargo no es mío.",
        "es",
    )
    recognition = next(
        item
        for item in propositions
        if item.family is PropositionFamily.ACTIVITY_NONRECOGNITION
    )
    ownership = next(
        item
        for item in propositions
        if item.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert recognition.mode == PropositionMode.UNCERTAIN.value
    assert ownership.mode == PropositionMode.ASSERTIVE.value


def test_b4_security_information_request_is_nonassertive() -> None:
    assert (
        _mode(
            "¿Qué protección recibo por una compra que no autoricé?",
            "es",
            PropositionFamily.AUTHORIZATION_DENIAL,
        )
        == PropositionMode.INFORMATION_REQUEST.value
    )


def test_b4_authorized_third_party_scope_is_nonassertive() -> None:
    assert (
        _mode(
            "Autoricé a mi hermana a hacer esta transferencia fraudulenta.",
            "es",
            PropositionFamily.FRAUD_CHARACTERIZATION,
        )
        == PropositionMode.AUTHORIZED_THIRD_PARTY.value
    )


def test_b4_reported_prior_belief_is_nonassertive() -> None:
    assert (
        _mode(
            "Creí que no autoricé esta compra.",
            "es",
            PropositionFamily.AUTHORIZATION_DENIAL,
        )
        == PropositionMode.REPORTED_PRIOR_BELIEF.value
    )


def test_b4_explicit_same_referent_correction_retracts() -> None:
    assert (
        _mode(
            "No autoricé esta compra, pero sí autoricé esta compra.",
            "es",
            PropositionFamily.AUTHORIZATION_DENIAL,
        )
        == PropositionMode.RETRACTED.value
    )


def test_b4_mixed_security_question_preserves_separate_assertion() -> None:
    propositions = resolve_positive_propositions(
        "¿Qué protección recibo por una compra que no autoricé? "
        "Esta transferencia no es mía.",
        "es",
    )
    authorization = next(
        item
        for item in propositions
        if item.family is PropositionFamily.AUTHORIZATION_DENIAL
    )
    ownership = next(
        item
        for item in propositions
        if item.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert authorization.mode == PropositionMode.INFORMATION_REQUEST.value
    assert ownership.mode == PropositionMode.ASSERTIVE.value


def test_b4_mixed_descriptor_clarification_preserves_separate_assertion() -> None:
    propositions = resolve_positive_propositions(
        "No reconozco el comercio de esta compra. "
        "Esta transferencia no es mía.",
        "es",
    )

    assert not any(
        item.family is PropositionFamily.ACTIVITY_NONRECOGNITION
        for item in propositions
    )
    ownership = next(
        item
        for item in propositions
        if item.family is PropositionFamily.OWNERSHIP_DENIAL
    )
    assert ownership.mode == PropositionMode.ASSERTIVE.value


def test_b4_mixed_retraction_preserves_new_unauthorized_assertion() -> None:
    propositions = resolve_positive_propositions(
        "No autoricé esta compra, pero sí autoricé esta compra, "
        "y esta transferencia no es mía.",
        "es",
    )
    authorization = next(
        item
        for item in propositions
        if item.family is PropositionFamily.AUTHORIZATION_DENIAL
    )
    ownership = next(
        item
        for item in propositions
        if item.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert authorization.mode == PropositionMode.RETRACTED.value
    assert ownership.mode == PropositionMode.ASSERTIVE.value


def test_b4_mixed_authorized_activity_preserves_other_unauthorized_assertion() -> None:
    propositions = resolve_positive_propositions(
        "Autoricé a mi hermana a hacer esta transferencia fraudulenta, "
        "pero esta otra compra no es mía.",
        "es",
    )
    fraud = next(
        item
        for item in propositions
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    ownership = next(
        item
        for item in propositions
        if item.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert fraud.mode == PropositionMode.AUTHORIZED_THIRD_PARTY.value
    assert ownership.mode == PropositionMode.ASSERTIVE.value


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("No hice esta compra.", PropositionMode.ASSERTIVE.value),
        ("Quizás no hice esta compra.", PropositionMode.UNCERTAIN.value),
        ("¿No hice esta compra?", PropositionMode.QUESTIONED.value),
        (
            "Pensé que no hice esta compra.",
            PropositionMode.REPORTED_PRIOR_BELIEF.value,
        ),
    ],
)
def test_b4_contrastive_mode_minimal_pairs(
    message: str,
    expected: str,
) -> None:
    assert (
        _mode(
            message,
            "es",
            PropositionFamily.PERFORMANCE_DENIAL,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("base", "variant", "language", "family"),
    [
        (
            "No autoricé esta transferencia.",
            "No autoricé DEMO-ES-4321.",
            "es",
            PropositionFamily.AUTHORIZATION_DENIAL,
        ),
        (
            "Eu não fiz esta compra.",
            "Eu realmente não fiz esta compra hoje.",
            "pt",
            PropositionFamily.PERFORMANCE_DENIAL,
        ),
        (
            "Yo no autoricé esta compra.",
            "Yo no autoricé esta compra de mi cuenta.",
            "es",
            PropositionFamily.AUTHORIZATION_DENIAL,
        ),
        (
            "Esta compra no es mía.",
            "Estas compras no son mías.",
            "es",
            PropositionFamily.OWNERSHIP_DENIAL,
        ),
        (
            "Esta operación no la hice yo.",
            "Yo no hice esta operación.",
            "es",
            PropositionFamily.PERFORMANCE_DENIAL,
        ),
    ],
)
def test_b4_positive_metamorphic_invariance(
    base: str,
    variant: str,
    language: str,
    family: PropositionFamily,
) -> None:
    assert _mode(base, language, family) == PropositionMode.ASSERTIVE.value
    assert _mode(variant, language, family) == PropositionMode.ASSERTIVE.value
