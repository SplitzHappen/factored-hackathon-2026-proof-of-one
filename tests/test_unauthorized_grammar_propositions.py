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

def test_p6_attributive_fraud_characterization_is_customer_anchored() -> None:
    es = _families("Este cargo fraudulento apareció hoy.", "es")
    pt = _families("Esta cobrança fraudulenta apareceu hoje.", "pt")

    assert PropositionFamily.FRAUD_CHARACTERIZATION in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION in pt


def test_p6_attributive_requires_gender_number_agreement() -> None:
    es = _families("Esta transferencia fraudulento apareció hoy.", "es")
    pt = _families("Estas cobranças fraudulento apareceram hoje.", "pt")

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in pt


def test_p6_copular_fraud_characterization_supports_noun_markers() -> None:
    es = _families("Esta transferencia es un fraude.", "es")
    pt = _families("Este Pix é um golpe.", "pt")

    assert PropositionFamily.FRAUD_CHARACTERIZATION in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION in pt


def test_p6_copular_link_can_cross_bounded_contextual_modifiers() -> None:
    es = _families("Esta transferencia de ayer realmente es un fraude.", "es")
    pt = _families("Este Pix de ontem realmente é um golpe.", "pt")

    assert PropositionFamily.FRAUD_CHARACTERIZATION in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION in pt


def test_p6_non_activity_fraud_heads_do_not_create_transaction_proposition() -> None:
    es = _families("Este correo es un fraude.", "es")
    pt = _families("Este site é um golpe.", "pt")

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in pt


def test_p6_bare_generic_activity_is_not_customer_anchored() -> None:
    es = _families("Cargo fraudulento es una categoría.", "es")
    pt = _families("Cobrança fraudulenta é uma categoria.", "pt")

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in pt


def test_p6_explicit_third_person_possession_blocks_customer_anchor() -> None:
    es = _families("Su compra fue un fraude.", "es")
    pt = _families("Sua compra foi um golpe.", "pt")

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in pt


def test_p6_transaction_id_can_anchor_copular_characterization() -> None:
    es = _families("DEMO-ES-1001 es un fraude.", "es")
    pt = _families("DEMO-PT-2001 é um golpe.", "pt")

    assert PropositionFamily.FRAUD_CHARACTERIZATION in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION in pt

def test_p6_copular_predication_does_not_jump_to_later_non_activity_head() -> None:
    es = _families(
        "Esta transferencia es legítima pero este correo es un fraude.",
        "es",
    )
    pt = _families(
        "Este Pix é legítimo mas este site é um golpe.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in pt

def test_p7_nonrecognition_targets_activity_in_both_languages() -> None:
    es = _families("No reconozco este cargo.", "es")
    pt = _families("Não reconheço este Pix.", "pt")

    assert PropositionFamily.ACTIVITY_NONRECOGNITION in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION in pt


def test_p7_descriptor_target_remains_informational() -> None:
    es = _families("No reconozco el comercio.", "es")
    pt = _families("Não reconheço o nome do estabelecimento.", "pt")

    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in pt


def test_p7_descriptor_head_beats_embedded_activity_reference() -> None:
    es = _families("No reconozco el comercio de esta compra.", "es")
    pt = _families("Não reconheço o estabelecimento desta compra.", "pt")

    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in pt


def test_p7_preposed_activity_can_be_targeted_by_clitic() -> None:
    es = _families("Esta compra no la reconozco.", "es")
    pt = _families("Este Pix, não o reconheço.", "pt")

    assert PropositionFamily.ACTIVITY_NONRECOGNITION in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION in pt


def test_p7_r3_activity_anaphora_links_nearest_prior_activity() -> None:
    propositions = build_positive_propositions(
        "Este cargo apareció ayer; no lo reconozco.",
        "es",
    )

    linked = next(
        item
        for item in propositions
        if item.family is PropositionFamily.ACTIVITY_NONRECOGNITION
    )
    assert linked.rule == "P7-R3-activity-anaphora"
    assert linked.activity_ref == "linked_prior_activity"
    assert linked.activity_token_span is not None


def test_p7_r3_activity_anaphora_can_link_prior_transaction_id() -> None:
    propositions = build_positive_propositions(
        "DEMO-ES-1001; no lo reconozco.",
        "es",
    )

    linked = next(
        item
        for item in propositions
        if item.family is PropositionFamily.ACTIVITY_NONRECOGNITION
    )
    assert linked.rule == "P7-R3-activity-anaphora"
    assert linked.activity_ref == "linked_prior_txid"


def test_p7_argumentless_first_person_nonrecognition_uses_topic_default() -> None:
    es = build_positive_propositions("No reconozco.", "es")
    pt = build_positive_propositions("Não reconheço.", "pt")

    es_item = next(
        item for item in es
        if item.family is PropositionFamily.ACTIVITY_NONRECOGNITION
    )
    pt_item = next(
        item for item in pt
        if item.family is PropositionFamily.ACTIVITY_NONRECOGNITION
    )

    assert es_item.activity_ref == "topic_transaction"
    assert pt_item.activity_ref == "topic_transaction"


def test_p7_generic_activity_category_is_not_specific_transaction_target() -> None:
    es = _families("No reconozco cargos internacionales.", "es")
    pt = _families("Não reconheço cobranças internacionais.", "pt")

    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in pt

def test_p7_d2_does_not_link_generic_prior_activity_category() -> None:
    propositions = build_positive_propositions(
        "Transferencias internacionales son una categoría; no lo reconozco.",
        "es",
    )

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.ACTIVITY_NONRECOGNITION
    )
    assert item.activity_ref == "topic_transaction"
    assert item.activity_token_span is None

def test_p8_explicit_customer_possession_is_positive_without_activity() -> None:
    es = build_positive_propositions("Clonaron mi tarjeta.", "es")
    pt = build_positive_propositions("Hackearam minha conta.", "pt")

    es_item = next(
        item
        for item in es
        if item.family is PropositionFamily.COMPROMISE_LINKED_ACTIVITY
    )
    pt_item = next(
        item
        for item in pt
        if item.family is PropositionFamily.COMPROMISE_LINKED_ACTIVITY
    )

    assert es_item.activity_ref == "customer_instrument_compromise"
    assert pt_item.activity_ref == "customer_instrument_compromise"


def test_p8_dative_experiencer_can_anchor_customer_instrument() -> None:
    es = _families("Me robaron la tarjeta.", "es")
    pt = _families("Me roubaram o cartão.", "pt")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in pt


def test_p8_passive_participle_supports_customer_owned_instrument() -> None:
    es = _families("Mi tarjeta fue clonada.", "es")
    pt = _families("Minha conta foi invadida.", "pt")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in pt


def test_p8_passive_participle_supports_dative_experiencer() -> None:
    es = _families("Me fue robada la tarjeta.", "es")
    pt = _families("Me foi roubado o cartão.", "pt")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in pt


def test_p8_generic_instrument_without_customer_anchor_is_not_positive() -> None:
    es = _families("Clonaron la tarjeta.", "es")
    pt = _families("Clonaram o cartão.", "pt")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in pt


def test_p8_explicit_third_person_instrument_is_not_customer_compromise() -> None:
    es = _families("Clonaron su tarjeta.", "es")
    pt = _families("Hackearam a conta dela.", "pt")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in pt


def test_p8_first_person_actor_does_not_count_as_customer_experiencer() -> None:
    es = _families("Cloné mi tarjeta.", "es")
    pt = _families("Clonei meu cartão.", "pt")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in pt


def test_p8_known_actor_theft_of_customer_instrument_remains_positive() -> None:
    es = _families("Mi hermano robó mi tarjeta.", "es")
    pt = _families("Meu irmão roubou meu cartão.", "pt")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in pt

def test_p8_possessive_on_other_noun_cannot_anchor_instrument() -> None:
    es = _families("Mi hermano dijo que clonaron la tarjeta.", "es")
    pt = _families("Meu irmão disse que clonaram o cartão.", "pt")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in pt


def test_p8_postnominal_customer_possession_is_supported() -> None:
    es = _families("Clonaron la tarjeta mía.", "es")
    pt = _families("Hackearam a conta minha.", "pt")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in pt

def test_p8_accented_third_person_predicate_remains_positive() -> None:
    propositions = _families("Clonó mi tarjeta.", "es")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in propositions

def test_r3_d1_inherits_denied_perform_frame_across_semicolon() -> None:
    es = build_positive_propositions(
        "Nadie hizo este pago; ni yo ni mi hijo.",
        "es",
    )
    pt = build_positive_propositions(
        "Ninguém fez este saque; nem eu, nem meu filho.",
        "pt",
    )

    es_item = next(
        item
        for item in es
        if item.rule == "R3-D1-elliptical-continuation"
    )
    pt_item = next(
        item
        for item in pt
        if item.rule == "R3-D1-elliptical-continuation"
    )

    assert es_item.family is PropositionFamily.PERFORMANCE_DENIAL
    assert pt_item.family is PropositionFamily.PERFORMANCE_DENIAL
    assert es_item.activity_ref == "linked_prior_activity"
    assert pt_item.activity_ref == "linked_prior_activity"


def test_r3_d1_supports_whitespace_dash_boundary() -> None:
    propositions = build_positive_propositions(
        "Ninguém fez este saque — nem eu, nem meu irmão.",
        "pt",
    )

    item = next(
        proposition
        for proposition in propositions
        if proposition.rule == "R3-D1-elliptical-continuation"
    )
    assert item.family is PropositionFamily.PERFORMANCE_DENIAL


def test_r3_d1_supports_comma_continuation_without_global_coreference() -> None:
    propositions = build_positive_propositions(
        "Nadie hizo este pago, ni yo ni mi hija.",
        "es",
    )

    item = next(
        proposition
        for proposition in propositions
        if proposition.rule == "R3-D1-elliptical-continuation"
    )
    assert item.family is PropositionFamily.PERFORMANCE_DENIAL


def test_r3_d1_supports_additive_self_inclusion_forms() -> None:
    es = _families("Nadie hizo este pago; yo tampoco.", "es")
    pt = _families("Ninguém fez este saque; eu também não.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL in es
    assert PropositionFamily.PERFORMANCE_DENIAL in pt


def test_r3_d1_requires_denied_prior_frame() -> None:
    es = build_positive_propositions(
        "Mi hermano hizo este pago; yo tampoco.",
        "es",
    )
    pt = build_positive_propositions(
        "Meu irmão fez este saque; eu também não.",
        "pt",
    )

    assert not any(
        item.rule == "R3-D1-elliptical-continuation"
        for item in (*es, *pt)
    )


def test_r3_d1_rejects_continuation_with_finite_domain_predicate() -> None:
    propositions = build_positive_propositions(
        "Nadie hizo este pago; yo tampoco autoricé este pago.",
        "es",
    )

    assert not any(
        item.rule == "R3-D1-elliptical-continuation"
        for item in propositions
    )


def test_r3_d1_does_not_cross_sentence_boundary() -> None:
    propositions = build_positive_propositions(
        "Nadie hizo este pago. Yo tampoco.",
        "es",
    )

    assert not any(
        item.rule == "R3-D1-elliptical-continuation"
        for item in propositions
    )


def test_r3_d1_can_inherit_authorization_denial() -> None:
    propositions = build_positive_propositions(
        "Nadie autorizó este pago; ni yo ni mi esposa.",
        "es",
    )

    item = next(
        proposition
        for proposition in propositions
        if proposition.rule == "R3-D1-elliptical-continuation"
    )
    assert item.family is PropositionFamily.AUTHORIZATION_DENIAL

def test_p5_exceeded_amount_authorization_is_positive() -> None:
    es = build_positive_propositions(
        "Mi hermano gastó más de lo que autoricé.",
        "es",
    )
    pt = build_positive_propositions(
        "Meu irmão gastou mais do que eu autorizei.",
        "pt",
    )

    es_item = next(
        item
        for item in es
        if item.rule == "P5-exceeded-authorization-amount"
    )
    pt_item = next(
        item
        for item in pt
        if item.rule == "P5-exceeded-authorization-amount"
    )

    assert es_item.family is PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE
    assert pt_item.family is PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE


def test_p5_portuguese_alem_do_que_amount_exceedance_is_positive() -> None:
    propositions = build_positive_propositions(
        "Minha irmã gastou além do que eu autorizei.",
        "pt",
    )

    assert any(
        item.rule == "P5-exceeded-authorization-amount"
        for item in propositions
    )


def test_p5_non_exceeded_authorized_amount_is_not_positive() -> None:
    es = build_positive_propositions(
        "Mi hermano gastó exactamente lo que autoricé.",
        "es",
    )
    pt = build_positive_propositions(
        "Meu irmão gastou exatamente o que eu autorizei.",
        "pt",
    )

    assert not any(
        item.rule == "P5-exceeded-authorization-amount"
        for item in (*es, *pt)
    )


def test_p5_limited_grant_then_out_of_scope_purchase_is_positive() -> None:
    es = build_positive_propositions(
        "Le di la tarjeta para la gasolina y compró otras cosas sin permiso.",
        "es",
    )
    pt = build_positive_propositions(
        "Dei o cartão ao meu irmão para gasolina e ele comprou outras coisas sem permissão.",
        "pt",
    )

    assert any(
        item.rule == "P5-exceeded-authorization-purpose"
        for item in es
    )
    assert any(
        item.rule == "P5-exceeded-authorization-purpose"
        for item in pt
    )


def test_p5_limited_grant_in_scope_action_without_denial_is_not_positive() -> None:
    es = build_positive_propositions(
        "Le di la tarjeta para la gasolina y compró gasolina.",
        "es",
    )
    pt = build_positive_propositions(
        "Dei o cartão ao meu irmão para gasolina e ele comprou gasolina.",
        "pt",
    )

    assert not any(
        item.rule == "P5-exceeded-authorization-purpose"
        for item in (*es, *pt)
    )


def test_p5_bare_permission_absence_is_supported_for_known_actor_use() -> None:
    es = _families("Mi hermano usó mi tarjeta sin permiso.", "es")
    pt = _families("Minha irmã usou minha conta sem permissão.", "pt")

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt


def test_p4_subsequent_specific_purchase_not_authorized_remains_positive() -> None:
    es = _families("Mi hermano hizo esta compra que no autoricé.", "es")
    pt = _families("Minha irmã fez esta compra que eu não autorizei.", "pt")

    assert PropositionFamily.AUTHORIZATION_DENIAL in es
    assert PropositionFamily.AUTHORIZATION_DENIAL in pt

def test_p5_later_permission_denial_does_not_relabel_earlier_use() -> None:
    propositions = build_positive_propositions(
        "Mi hermano usó mi tarjeta para gasolina y compró otra compra sin permiso.",
        "es",
    )

    assert not any(
        item.rule == "P5"
        and item.predicate_token_span is not None
        and item.activity_ref in {"explicit_activity", "known_actor_instrument_use"}
        for item in propositions
    )


def test_p5_exceeded_purpose_requires_prior_limited_grant() -> None:
    es = build_positive_propositions(
        "Mi hermano compró otra compra sin permiso.",
        "es",
    )
    pt = build_positive_propositions(
        "Meu irmão comprou outra compra sem permissão.",
        "pt",
    )

    assert not any(
        item.rule == "P5-exceeded-authorization-purpose"
        for item in (*es, *pt)
    )

def test_p5_preposed_permission_absence_remains_positive() -> None:
    es = _families("Sin mi permiso, mi hermano usó mi tarjeta.", "es")
    pt = _families("Sem minha permissão, minha irmã usou minha conta.", "pt")

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt
