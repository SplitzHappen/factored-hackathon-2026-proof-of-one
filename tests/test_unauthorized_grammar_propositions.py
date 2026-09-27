from __future__ import annotations

from app.unauthorized_grammar import (
    PropositionFamily,
    build_positive_propositions,
    dump_positive_propositions,
)


def _rules(text: str, language: str) -> set[str]:
    return {item.rule for item in build_positive_propositions(text, language)}


def _families(text: str, language: str) -> set[PropositionFamily]:
    return {item.family for item in build_positive_propositions(text, language)}


def test_p1_ownership_denial_is_structural_in_spanish_and_portuguese() -> None:
    es = build_positive_propositions("Este cargo no es mío.", "es")
    pt = build_positive_propositions("Este débito não é meu.", "pt")

    assert any(item.rule == "P1" for item in es)
    assert any(item.rule == "P1" for item in pt)
    assert all(item.family is PropositionFamily.OWNERSHIP_DENIAL for item in es + pt)


def test_p1b_alienation_predicates_do_not_require_phrase_level_templates() -> None:
    assert "P1b" in _rules("La transferencia resultó ajena.", "es")
    assert "P1b" in _rules("O Pix era de outra pessoa.", "pt")


def test_p2_performance_denial_handles_explicit_and_topic_default_activity() -> None:
    explicit = build_positive_propositions("La compra no la hice yo.", "es")
    topic_default = build_positive_propositions("No lo he hecho yo.", "es")

    explicit_p2 = next(item for item in explicit if item.rule == "P2")
    default_p2 = next(item for item in topic_default if item.rule == "P2")

    assert explicit_p2.activity_ref == "explicit_activity"
    assert explicit_p2.activity_token_span is not None
    assert default_p2.activity_ref == "topic_transaction"
    assert default_p2.activity_token_span is None


def test_p2_supports_negative_coordination_and_portuguese_emphasis() -> None:
    coordinated = _families("Ni yo ni otra persona hicimos la compra.", "es")
    emphatic = _families("Nunca que eu fiz esse Pix.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL in coordinated
    assert PropositionFamily.PERFORMANCE_DENIAL in emphatic


def test_self_dative_alone_cannot_satisfy_p2_performer_role() -> None:
    propositions = build_positive_propositions("No me hicieron ese cargo.", "es")

    assert PropositionFamily.PERFORMANCE_DENIAL not in {
        item.family for item in propositions
    }


def test_p3_origination_denial_requires_self_source_role() -> None:
    es = _families("La transferencia no salió de mí.", "es")
    pt = _families("O Pix não saiu de mim.", "pt")
    third_party = _families("La transferencia no salió de ella.", "es")

    assert PropositionFamily.ORIGINATION_DENIAL in es
    assert PropositionFamily.ORIGINATION_DENIAL in pt
    assert PropositionFamily.ORIGINATION_DENIAL not in third_party


def test_proposition_debug_dump_preserves_original_text_evidence() -> None:
    text = "Este débito não é meu."
    dump = dump_positive_propositions(text, "pt")

    assert dump
    assert dump[0]["rule"] == "P1"
    assert dump[0]["source"] in text
    assert dump[0]["mode"] == "unresolved"

def test_portuguese_no_contraction_does_not_create_p2_denial() -> None:
    propositions = build_positive_propositions("No meu cartão, eu fiz o Pix.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL not in {
        item.family for item in propositions
    }

def test_p4_direct_authorization_denial_in_both_languages() -> None:
    es = _families("Yo no autoricé esta transferencia.", "es")
    pt = _families("Eu não autorizei este Pix.", "pt")

    assert PropositionFamily.AUTHORIZATION_DENIAL in es
    assert PropositionFamily.AUTHORIZATION_DENIAL in pt


def test_p4_possessive_authorization_absence_is_customer_anchored() -> None:
    es = _rules("Esta transferencia llegó sin mi autorización.", "es")
    pt = _rules("Este Pix apareceu sem minha autorização.", "pt")

    assert "P4" in es
    assert "P4" in pt


def test_p4_unauthorized_participle_supports_gender_agreement() -> None:
    es = _families("Esta compra no fue autorizada.", "es")
    pt = _families("Esta compra não foi autorizada.", "pt")

    assert PropositionFamily.AUTHORIZATION_DENIAL in es
    assert PropositionFamily.AUTHORIZATION_DENIAL in pt


def test_r3_permission_denial_backlinks_to_immediately_prior_known_actor_use() -> None:
    es = build_positive_propositions(
        "Mi hermano usó mi tarjeta; yo no le di permiso.",
        "es",
    )
    pt = build_positive_propositions(
        "Minha irmã usou minha conta; eu não dei permissão.",
        "pt",
    )

    es_link = next(item for item in es if item.rule == "P4-R3-permission-backlink")
    pt_link = next(item for item in pt if item.rule == "P4-R3-permission-backlink")

    assert es_link.activity_ref == "linked_instrument_use"
    assert pt_link.activity_ref == "linked_instrument_use"


def test_r3_permission_backlink_can_reuse_prior_activity_referent() -> None:
    propositions = build_positive_propositions(
        "Mi hermana hizo esta compra; yo no le di permiso.",
        "es",
    )

    linked = next(
        item for item in propositions if item.rule == "P4-R3-permission-backlink"
    )
    assert linked.activity_ref == "linked_prior_activity"
    assert linked.activity_token_span is not None


def test_permission_backlink_does_not_jump_over_unrelated_clause() -> None:
    propositions = build_positive_propositions(
        "Mi hermano usó mi tarjeta; llamé al banco; yo no le di permiso.",
        "es",
    )

    assert not any(
        item.rule == "P4-R3-permission-backlink"
        for item in propositions
    )

def test_bare_permission_denial_without_activity_or_backlink_is_not_p4() -> None:
    es = build_positive_propositions("Yo no le di permiso.", "es")
    pt = build_positive_propositions("Eu não dei permissão.", "pt")

    assert PropositionFamily.AUTHORIZATION_DENIAL not in {
        item.family for item in es
    }
    assert PropositionFamily.AUTHORIZATION_DENIAL not in {
        item.family for item in pt
    }

def test_p5_unknown_actor_use_of_customer_instrument_is_positive() -> None:
    es = _families("Alguien usó mi tarjeta.", "es")
    pt = _families("Alguém usou minha conta.", "pt")

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt


def test_p5_known_actor_requires_permission_absence() -> None:
    es = _families("Mi hermano usó mi tarjeta.", "es")
    pt = _families("Minha irmã usou minha conta.", "pt")

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt


def test_p5_known_actor_with_explicit_permission_absence_is_positive() -> None:
    es = _families("Mi hermano usó mi tarjeta sin mi permiso.", "es")
    pt = _families("Minha irmã usou minha conta sem minha permissão.", "pt")

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt


def test_p5_known_actor_supports_permission_absence_constructions() -> None:
    es = _families("Mi hermano usó mi tarjeta sin avisarme.", "es")
    pt = _families("Minha irmã usou minha conta sem me avisar.", "pt")

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt


def test_p5_requires_customer_possession_of_instrument() -> None:
    es = _families("Alguien usó su tarjeta.", "es")
    pt = _families("Alguém usou o cartão dela.", "pt")

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt


def test_p5_does_not_turn_generic_third_party_performance_into_use() -> None:
    propositions = build_positive_propositions(
        "Alguien hizo una compra.",
        "es",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in {
        item.family for item in propositions
    }

def test_p5_bare_person_noun_does_not_bypass_known_actor_permission_rule() -> None:
    propositions = build_positive_propositions(
        "Mi hermano, una persona adulta, usó mi tarjeta.",
        "es",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in {
        item.family for item in propositions
    }


def test_p5_explicit_other_person_counts_as_unknown_actor() -> None:
    es = _families("Otra persona usó mi tarjeta.", "es")
    pt = _families("Outra pessoa usou minha conta.", "pt")

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt
