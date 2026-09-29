from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.unauthorized_grammar import (
    EvidenceAtomKind,
    LexicalTag,
    PredicateFamily,
    PropositionFamily,
    analyze_foundation,
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



def test_b2r_a1_response_particle_does_not_negate_perform_predicate() -> None:
    es = _families("No, yo hice esa compra.", "es")
    pt = _families("Não, eu fiz essa compra.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL not in es
    assert PropositionFamily.PERFORMANCE_DENIAL not in pt


def test_b2r_a1_tag_negation_does_not_negate_prior_perform_predicate() -> None:
    es = _families("Yo lo hice, ¿no?", "es")
    pt = _families("Eu fiz isso, não?", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL not in es
    assert PropositionFamily.PERFORMANCE_DENIAL not in pt


def test_b2r_a1_matrix_negation_does_not_attach_to_embedded_perform_predicate() -> None:
    es = _families("No sé si hice esa compra.", "es")
    pt = _families("Não sei se fiz essa compra.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL not in es
    assert PropositionFamily.PERFORMANCE_DENIAL not in pt


def test_b2r_a1_canonical_performance_denial_remains_positive() -> None:
    es = _families("Yo no hice esa compra.", "es")
    pt = _families("Eu não fiz essa compra.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL in es
    assert PropositionFamily.PERFORMANCE_DENIAL in pt



def test_b2r_a2_negated_known_actor_use_is_not_positive() -> None:
    es = _families("Mi hermano nunca usó mi tarjeta sin permiso.", "es")
    pt = _families("Meu irmão nunca usou meu cartão sem permissão.", "pt")

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt


def test_b2r_a2_negated_fraud_characterization_is_not_positive() -> None:
    es = _families("Esta compra no es un fraude.", "es")
    pt = _families("Essa cobrança não é golpe.", "pt")

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in pt


def test_b2r_a2_negated_compromise_is_not_positive() -> None:
    es = _families("No me robaron la tarjeta, la perdí.", "es")
    pt = _families("Não clonaram meu cartão, eu errei a senha.", "pt")

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in pt


def test_b2r_a2_negated_amount_exceedance_is_not_positive() -> None:
    es = build_positive_propositions(
        "Mi hermano no gastó más de lo que autoricé.",
        "es",
    )
    pt = build_positive_propositions(
        "Meu filho nunca gasta mais do que eu autorizo.",
        "pt",
    )

    assert not any(
        item.rule == "P5-exceeded-authorization-amount"
        for item in (*es, *pt)
    )


def test_b2r_a2_negated_purpose_exceedance_is_not_positive() -> None:
    es = build_positive_propositions(
        "Le di la tarjeta para la gasolina y no compró nada sin permiso.",
        "es",
    )
    pt = build_positive_propositions(
        "Dei o cartão para gasolina e não comprou nada sem permissão.",
        "pt",
    )

    assert not any(
        item.rule == "P5-exceeded-authorization-purpose"
        for item in (*es, *pt)
    )


def test_b2r_a2_double_negated_permission_absence_is_not_positive() -> None:
    es = _families(
        "Mi hermano usó mi tarjeta, pero no sin permiso.",
        "es",
    )
    pt = _families(
        "Meu irmão usou meu cartão, mas não sem permissão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt



def test_b2r_a3_third_person_denial_does_not_borrow_customer_subject() -> None:
    es = _families("Mi hijo no hizo esa compra, la hice yo.", "es")
    pt = _families("Meu filho não fez essa compra, eu fiz.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL not in es
    assert PropositionFamily.PERFORMANCE_DENIAL not in pt


def test_b2r_a3_authorization_denial_does_not_borrow_customer_subject() -> None:
    es = _families("Yo hice la compra y mi esposa no la aprobó.", "es")
    pt = _families("Eu fiz a compra e minha esposa não a aprovou.", "pt")

    assert PropositionFamily.AUTHORIZATION_DENIAL not in es
    assert PropositionFamily.AUTHORIZATION_DENIAL not in pt


def test_b2r_a3_incoming_transfer_denial_does_not_use_unrelated_customer_subject() -> None:
    es = _families("Yo pedí un reembolso y no me hicieron la transferencia.", "es")
    pt = _families("Eu pedi um reembolso e não me fizeram a transferência.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL not in es
    assert PropositionFamily.PERFORMANCE_DENIAL not in pt


def test_b2r_a3_explicit_customer_subject_still_binds_to_first_person_predicate() -> None:
    es = _families("Yo no hice esa compra.", "es")
    pt = _families("Eu não fiz essa compra.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL in es
    assert PropositionFamily.PERFORMANCE_DENIAL in pt


def test_b2r_a3_pro_drop_customer_subject_still_binds_to_first_person_predicate() -> None:
    es = _families("No hice esa compra.", "es")
    pt = _families("Não fiz essa compra.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL in es
    assert PropositionFamily.PERFORMANCE_DENIAL in pt



def test_b2r_a3_future_performance_refusal_is_not_past_denial() -> None:
    es = _families("No pagaré ese cargo.", "es")
    pt = _families("Não pagarei essa cobrança.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL not in es
    assert PropositionFamily.PERFORMANCE_DENIAL not in pt


def test_b2r_a3_conditional_authorization_is_not_past_denial() -> None:
    es = _families("Yo nunca autorizaría esa compra.", "es")
    pt = _families("Eu nunca autorizaria essa compra.", "pt")

    assert PropositionFamily.AUTHORIZATION_DENIAL not in es
    assert PropositionFamily.AUTHORIZATION_DENIAL not in pt


def test_b2r_a3_habitual_present_performance_is_not_past_denial() -> None:
    es = _families("No hago compras por internet.", "es")
    pt = _families("Eu não faço compras nesse site.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL not in es
    assert PropositionFamily.PERFORMANCE_DENIAL not in pt


def test_b2r_a3_directive_subjunctive_is_not_customer_authorization_denial() -> None:
    es = _families("Por favor, no autorice ese cargo.", "es")
    pt = _families("Por favor, não autorize essa cobrança.", "pt")

    assert PropositionFamily.AUTHORIZATION_DENIAL not in es
    assert PropositionFamily.AUTHORIZATION_DENIAL not in pt


def test_b2r_a3_past_performance_denial_remains_positive() -> None:
    es = _families("Yo no hice esa compra.", "es")
    pt = _families("Eu não fiz essa compra.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL in es
    assert PropositionFamily.PERFORMANCE_DENIAL in pt


def test_b2r_a3_past_authorization_denial_remains_positive() -> None:
    es = _families("Yo no autoricé esa compra.", "es")
    pt = _families("Eu não autorizei essa compra.", "pt")

    assert PropositionFamily.AUTHORIZATION_DENIAL in es
    assert PropositionFamily.AUTHORIZATION_DENIAL in pt



def test_b2r_a4_unknown_actor_mention_does_not_relabel_customer_use() -> None:
    es = _families("Ayer alguien me ayudó en el cajero y usé mi tarjeta.", "es")
    pt = _families("Ontem alguém me ajudou no caixa e usei meu cartão.", "pt")

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt


def test_b2r_a4_customer_amount_action_is_not_third_party_exceedance() -> None:
    es = _families(
        "Con mi hermano en la tienda gasté más de lo que autoricé.",
        "es",
    )
    pt = _families(
        "Com meu irmão na loja gastei mais do que autorizei.",
        "pt",
    )

    assert not any(
        proposition.rule == "P5-exceeded-authorization-amount"
        for proposition in build_positive_propositions(
            "Con mi hermano en la tienda gasté más de lo que autoricé.",
            "es",
        )
    )
    assert not any(
        proposition.rule == "P5-exceeded-authorization-amount"
        for proposition in build_positive_propositions(
            "Com meu irmão na loja gastei mais do que autorizei.",
            "pt",
        )
    )


def test_b2r_a4_customer_purpose_action_is_not_third_party_exceedance() -> None:
    es_text = (
        "Le di la tarjeta a mi hermano para la gasolina "
        "y yo compré otras cosas sin permiso."
    )
    pt_text = (
        "Dei o cartão ao meu irmão para gasolina "
        "e eu comprei outras coisas sem permissão."
    )

    assert not any(
        proposition.rule == "P5-exceeded-authorization-purpose"
        for proposition in build_positive_propositions(es_text, "es")
    )
    assert not any(
        proposition.rule == "P5-exceeded-authorization-purpose"
        for proposition in build_positive_propositions(pt_text, "pt")
    )


def test_b2r_a4_third_party_exceedance_controls_remain_positive() -> None:
    es = build_positive_propositions(
        "Mi hermano gastó más de lo que yo autoricé.",
        "es",
    )
    pt = build_positive_propositions(
        "Meu irmão gastou mais do que eu autorizei.",
        "pt",
    )

    assert any(
        proposition.rule == "P5-exceeded-authorization-amount"
        for proposition in es
    )
    assert any(
        proposition.rule == "P5-exceeded-authorization-amount"
        for proposition in pt
    )



def test_b2r_a5_spanish_possessive_mi_is_not_self_source() -> None:
    possessive = _families(
        "La transferencia no salió de mi cuenta.",
        "es",
    )
    pronoun = _families(
        "La transferencia no salió de mí.",
        "es",
    )

    assert PropositionFamily.ORIGINATION_DENIAL not in possessive
    assert PropositionFamily.ORIGINATION_DENIAL in pronoun


def test_b2r_a5_third_person_relational_victim_blocks_p6() -> None:
    es = _families(
        "El cargo fraudulento de mi vecino salió en las noticias.",
        "es",
    )
    pt = _families(
        "A cobrança fraudulenta do meu pai foi estornada.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in pt


def test_b2r_a5_third_person_dative_victim_blocks_p6_and_p8() -> None:
    es_p6 = _families(
        "La compra fraudulenta que le hicieron a mi mamá me preocupa.",
        "es",
    )
    es_p8 = _families(
        "A mi hermano le clonaron la tarjeta.",
        "es",
    )
    pt_p8 = _families(
        "Ao meu irmão clonaram o cartão.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es_p6
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in es_p8
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in pt_p8


def test_b2r_a5_p8_dative_does_not_cross_reporting_frame() -> None:
    es = _families(
        "Me dijeron que clonaron la tarjeta.",
        "es",
    )
    pt = _families(
        "Me disseram que clonaram o cartão.",
        "pt",
    )

    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in es
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY not in pt


def test_b2r_a5_customer_controls_remain_positive() -> None:
    es_p6 = _families(
        "Este cargo fraudulento apareció hoy.",
        "es",
    )
    es_p8 = _families(
        "A mí me clonaron la tarjeta.",
        "es",
    )
    pt_p8 = _families(
        "Clonaram meu cartão.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION in es_p6
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in es_p8
    assert PropositionFamily.COMPROMISE_LINKED_ACTIVITY in pt_p8


def test_b2r_a5_unaccented_de_da_are_not_permission_predicates() -> None:
    es = _families(
        "Yo no encuentro el número de autorización de esta compra.",
        "es",
    )
    pt = _families(
        "Eu não encontro o número da autorização desta compra.",
        "pt",
    )

    assert PropositionFamily.AUTHORIZATION_DENIAL not in es
    assert PropositionFamily.AUTHORIZATION_DENIAL not in pt



def test_b2r_a6_p7_rejects_overt_non_activity_object_heads() -> None:
    es = _families(
        "No reconozco este correo que me llegó.",
        "es",
    )
    pt = _families(
        "Não reconheço esse site.",
        "pt",
    )

    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in pt


def test_b2r_a6_p7_non_activity_head_beats_embedded_activity_reference() -> None:
    es = _families(
        "No reconozco a la persona que me escribió sobre la compra.",
        "es",
    )
    pt = _families(
        "Não reconheço o remetente do SMS sobre o Pix.",
        "pt",
    )

    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in pt


def test_b2r_a6_p7_rejects_preposed_non_activity_target_with_clitic() -> None:
    es = _families(
        "Este correo no lo reconozco.",
        "es",
    )
    pt = _families(
        "Esse site eu não o reconheço.",
        "pt",
    )

    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in pt


def test_b2r_a6_p7_activity_object_remains_positive() -> None:
    es = _families(
        "No reconozco este cargo.",
        "es",
    )
    pt = _families(
        "Não reconheço este Pix.",
        "pt",
    )

    assert PropositionFamily.ACTIVITY_NONRECOGNITION in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION in pt


def test_b2r_a6_p7_demonstrative_pronoun_keeps_topic_default() -> None:
    es = build_positive_propositions(
        "No reconozco esto.",
        "es",
    )
    pt = build_positive_propositions(
        "Não reconheço isso.",
        "pt",
    )

    es_item = next(
        item
        for item in es
        if item.family is PropositionFamily.ACTIVITY_NONRECOGNITION
    )
    pt_item = next(
        item
        for item in pt
        if item.family is PropositionFamily.ACTIVITY_NONRECOGNITION
    )

    assert es_item.activity_ref == "topic_transaction"
    assert pt_item.activity_ref == "topic_transaction"



def test_b2r_b1_argumentless_self_exculpation_is_p2_in_both_languages() -> None:
    es = build_positive_propositions("No fui yo.", "es")
    pt = build_positive_propositions("Não fui eu.", "pt")

    es_item = next(
        item for item in es
        if item.rule == "P2-R3-self-exculpation"
    )
    pt_item = next(
        item for item in pt
        if item.rule == "P2-R3-self-exculpation"
    )

    assert es_item.family is PropositionFamily.PERFORMANCE_DENIAL
    assert pt_item.family is PropositionFamily.PERFORMANCE_DENIAL
    assert es_item.activity_ref == "topic_transaction"
    assert pt_item.activity_ref == "topic_transaction"


def test_b2r_b1_self_exculpation_links_nearest_prior_activity() -> None:
    es = build_positive_propositions(
        "Este cargo apareció ayer. No fui yo.",
        "es",
    )
    pt = build_positive_propositions(
        "Apareceu um Pix. Não fui eu.",
        "pt",
    )

    es_item = next(
        item for item in es
        if item.rule == "P2-R3-self-exculpation"
    )
    pt_item = next(
        item for item in pt
        if item.rule == "P2-R3-self-exculpation"
    )

    assert es_item.activity_ref == "linked_prior_activity"
    assert pt_item.activity_ref == "linked_prior_activity"
    assert es_item.activity_token_span is not None
    assert pt_item.activity_token_span is not None


def test_b2r_b1_self_exculpation_can_link_prior_transaction_id() -> None:
    propositions = build_positive_propositions(
        "DEMO-ES-1001. No fui yo.",
        "es",
    )

    item = next(
        proposition
        for proposition in propositions
        if proposition.rule == "P2-R3-self-exculpation"
    )
    assert item.activity_ref == "linked_prior_txid"
    assert item.activity_token_span is not None


def test_b2r_b1_closed_cleft_self_exculpation_remains_positive() -> None:
    es = _families(
        "No fui yo quien hizo esa compra.",
        "es",
    )
    pt = _families(
        "Não fui eu quem fez essa compra.",
        "pt",
    )

    assert PropositionFamily.PERFORMANCE_DENIAL in es
    assert PropositionFamily.PERFORMANCE_DENIAL in pt


def test_b2r_b1_self_exculpation_does_not_become_general_fui_parser() -> None:
    es = _families(
        "No fui yo al banco.",
        "es",
    )
    pt = _families(
        "Não fui eu ao banco.",
        "pt",
    )

    assert PropositionFamily.PERFORMANCE_DENIAL not in es
    assert PropositionFamily.PERFORMANCE_DENIAL not in pt



def test_b2r_b2_existential_activity_nouns_recover_authorization_denial() -> None:
    es = _families(
        "Tengo compras no autorizadas en mi tarjeta.",
        "es",
    )
    pt = _families(
        "Há compras não autorizadas no meu cartão.",
        "pt",
    )

    assert PropositionFamily.AUTHORIZATION_DENIAL in es
    assert PropositionFamily.AUTHORIZATION_DENIAL in pt


def test_b2r_b2_bare_clause_initial_activity_before_denied_participle_is_nominal() -> None:
    es = _families(
        "Compra no autorizada.",
        "es",
    )
    pt = _families(
        "Compra não autorizada.",
        "pt",
    )

    assert PropositionFamily.AUTHORIZATION_DENIAL in es
    assert PropositionFamily.AUTHORIZATION_DENIAL in pt


def test_b2r_b2_mixed_message_keeps_unauthorized_activity_positive() -> None:
    propositions = build_positive_propositions(
        "Tengo compras no autorizadas; ¿cómo puedo protegerme ahora?",
        "es",
    )

    assert any(
        item.family is PropositionFamily.AUTHORIZATION_DENIAL
        for item in propositions
    )


def test_b2r_b2_quantifier_and_numeral_contexts_keep_activity_nominal() -> None:
    es = analyze_foundation(
        "Tengo dos pagos no autorizados.",
        "es",
    )
    pt = analyze_foundation(
        "Há muitas compras não autorizadas.",
        "pt",
    )

    es_activity = next(
        index
        for index, token in enumerate(es.tokens)
        if token.normalized == "pagos"
    )
    pt_activity = next(
        index
        for index, token in enumerate(pt.tokens)
        if token.normalized == "compras"
    )

    assert LexicalTag.ACTIVITY in es.tags[es_activity]
    assert LexicalTag.ACTIVITY in pt.tags[pt_activity]
    assert not any(
        predicate.token_start == es_activity
        and predicate.form.family is PredicateFamily.PERFORM
        for predicate in es.predicates
    )
    assert not any(
        predicate.token_start == pt_activity
        and predicate.form.family is PredicateFamily.PERFORM
        for predicate in pt.predicates
    )


def test_b2r_b2_contracted_determiner_context_keeps_activity_nominal() -> None:
    pt = analyze_foundation(
        "O detalhe desta compra apareceu.",
        "pt",
    )

    activity_index = next(
        index
        for index, token in enumerate(pt.tokens)
        if token.normalized == "compra"
    )

    assert LexicalTag.ACTIVITY in pt.tags[activity_index]
    assert not any(
        predicate.token_start == activity_index
        and predicate.form.family is PredicateFamily.PERFORM
        for predicate in pt.predicates
    )



def test_b2r_b3_spanish_provenir_irregular_form_supports_p3() -> None:
    propositions = build_positive_propositions(
        "Ese pago no provino de mí.",
        "es",
    )

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.ORIGINATION_DENIAL
    )
    assert item.rule == "P3"
    assert item.activity_ref == "explicit_activity"


def test_b2r_b3_permission_absence_allows_intervening_article() -> None:
    es = _families(
        "Esta compra llegó sin la mi autorización.",
        "es",
    )
    pt = _families(
        "Me cobraram DEMO-PT-2001 sem a minha autorização.",
        "pt",
    )

    assert PropositionFamily.AUTHORIZATION_DENIAL in es
    assert PropositionFamily.AUTHORIZATION_DENIAL in pt


def test_b2r_b3_permission_absence_without_article_remains_positive() -> None:
    es = _families(
        "Esta transferencia llegó sin mi autorización.",
        "es",
    )
    pt = _families(
        "Este Pix apareceu sem minha autorização.",
        "pt",
    )

    assert PropositionFamily.AUTHORIZATION_DENIAL in es
    assert PropositionFamily.AUTHORIZATION_DENIAL in pt



def test_b2r_b4_negative_quantifier_over_activity_supports_p1() -> None:
    es = build_positive_propositions(
        "Ninguno de estos cargos es mío.",
        "es",
    )
    pt = build_positive_propositions(
        "Nenhuma dessas compras é minha.",
        "pt",
    )

    assert PropositionFamily.OWNERSHIP_DENIAL in {
        item.family for item in es
    }
    assert PropositionFamily.OWNERSHIP_DENIAL in {
        item.family for item in pt
    }


def test_b2r_b4_correlative_negative_ownership_supports_p1() -> None:
    es = build_positive_propositions(
        "Ni esta compra ni las otras dos son mías.",
        "es",
    )
    pt = build_positive_propositions(
        "Nem esta compra nem as outras duas são minhas.",
        "pt",
    )

    es_item = next(
        item for item in es
        if item.family is PropositionFamily.OWNERSHIP_DENIAL
    )
    pt_item = next(
        item for item in pt
        if item.family is PropositionFamily.OWNERSHIP_DENIAL
    )

    assert es_item.rule == "P1-correlative"
    assert pt_item.rule == "P1-correlative"


def test_b2r_b4_correlative_negative_ownership_supports_txid_arm() -> None:
    propositions = build_positive_propositions(
        "Ni el cargo DEMO-ES-1001 ni los otros dos son míos.",
        "es",
    )

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.OWNERSHIP_DENIAL
    )
    assert item.rule == "P1-correlative"
    assert item.activity_token_span is not None


def test_b2r_b4_unrelated_negative_quantifier_does_not_bind_to_p1() -> None:
    propositions = build_positive_propositions(
        "Nadie dijo que este cargo es mío.",
        "es",
    )

    assert PropositionFamily.OWNERSHIP_DENIAL not in {
        item.family for item in propositions
    }


def test_b2r_b4_local_no_ownership_denial_remains_p1() -> None:
    propositions = build_positive_propositions(
        "Este cargo no es mío.",
        "es",
    )

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.OWNERSHIP_DENIAL
    )
    assert item.rule == "P1"



def test_b2r_b5_subjectless_spanish_fraud_preserves_frozen_positive() -> None:
    propositions = build_positive_propositions(
        "Es un fraude.",
        "es",
    )

    item = next(
        proposition
        for proposition in propositions
        if proposition.rule == "P6-subjectless-es-compat"
    )
    assert item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    assert item.activity_token_span is None
    assert item.activity_ref == "topic_transaction"


def test_b2r_b5_subjectless_spanish_fraud_binds_same_clause_txid() -> None:
    propositions = build_positive_propositions(
        "Es un fraude: DEMO-ES-1001.",
        "es",
    )

    item = next(
        proposition
        for proposition in propositions
        if proposition.rule == "P6-subjectless-es-compat"
    )
    assert item.activity_token_span is not None
    assert item.activity_ref == "linked_same_clause_txid"


def test_b2r_b5_subjectless_p6_does_not_override_overt_non_activity_subject() -> None:
    propositions = build_positive_propositions(
        "Este correo es un fraude.",
        "es",
    )

    assert not any(
        item.rule == "P6-subjectless-es-compat"
        for item in propositions
    )


def test_b2r_b5_subjectless_p6_does_not_expand_portuguese_declarative() -> None:
    propositions = build_positive_propositions(
        "É fraude.",
        "pt",
    )

    assert not any(
        item.rule == "P6-subjectless-es-compat"
        for item in propositions
    )
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in {
        item.family for item in propositions
    }


def test_b2r_b5_subjectless_p6_rejects_questioned_forms() -> None:
    inverted = build_positive_propositions(
        "¿Es un fraude?",
        "es",
    )
    terminal_only = build_positive_propositions(
        "Es un fraude?",
        "es",
    )

    assert not any(
        item.rule == "P6-subjectless-es-compat"
        for item in inverted
    )
    assert not any(
        item.rule == "P6-subjectless-es-compat"
        for item in terminal_only
    )



def test_b2r_b6_same_clause_d3_supports_comma_splice() -> None:
    es = build_positive_propositions(
        "Mi hermano usó mi tarjeta, yo no le di permiso.",
        "es",
    )
    pt = build_positive_propositions(
        "Minha irmã usou minha conta, eu não lhe dei permissão.",
        "pt",
    )

    es_link = next(
        item for item in es
        if item.rule == "P4-R3-permission-backlink"
    )
    pt_link = next(
        item for item in pt
        if item.rule == "P4-R3-permission-backlink"
    )

    assert es_link.activity_ref == "linked_instrument_use"
    assert pt_link.activity_ref == "linked_instrument_use"


def test_b2r_b6_same_clause_d3_supports_coordination() -> None:
    es = build_positive_propositions(
        "Mi hermano usó mi tarjeta y yo no le di permiso.",
        "es",
    )
    pt = build_positive_propositions(
        "Minha irmã usou minha conta e eu não lhe dei permissão.",
        "pt",
    )

    assert any(
        item.rule == "P4-R3-permission-backlink"
        for item in es
    )
    assert any(
        item.rule == "P4-R3-permission-backlink"
        for item in pt
    )


def test_b2r_b6_known_actor_expansion_supports_primo_backlink() -> None:
    propositions = build_positive_propositions(
        "Mi primo cogió mi tarjeta; yo no le di permiso.",
        "es",
    )

    assert any(
        item.rule == "P4-R3-permission-backlink"
        for item in propositions
    )


def test_b2r_b6_known_actor_expansion_supports_portuguese_kinship() -> None:
    propositions = build_positive_propositions(
        "Meu sobrinho usou minha conta; eu não lhe dei permissão.",
        "pt",
    )

    assert any(
        item.rule == "P4-R3-permission-backlink"
        for item in propositions
    )


def test_b2r_b6_same_clause_d3_rejects_intervening_finite_predicate() -> None:
    propositions = build_positive_propositions(
        "Mi hermano usó mi tarjeta, hizo otra compra, yo no le di permiso.",
        "es",
    )

    assert not any(
        item.rule == "P4-R3-permission-backlink"
        and item.activity_ref == "linked_instrument_use"
        for item in propositions
    )



def test_b2r_b7_known_actor_perform_with_customer_instrument_is_p5() -> None:
    es = _families(
        "Mi hijo hizo compras con mi tarjeta sin permiso.",
        "es",
    )
    pt = _families(
        "Meu filho fez compras no meu cartão sem minha permissão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt


def test_b2r_b7_unknown_actor_perform_with_customer_instrument_is_p5() -> None:
    es = build_positive_propositions(
        "Alguien hizo compras con mi tarjeta.",
        "es",
    )
    pt = build_positive_propositions(
        "Alguém sacou dinheiro da minha conta.",
        "pt",
    )

    assert any(
        item.family is PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE
        and item.predicate_token_span is not None
        for item in es
    )
    assert any(
        item.family is PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE
        and item.predicate_token_span is not None
        for item in pt
    )


def test_b2r_b7_perform_without_customer_instrument_remains_outside_p5() -> None:
    propositions = build_positive_propositions(
        "Alguien hizo una compra.",
        "es",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in {
        item.family for item in propositions
    }


def test_b2r_b7_perform_requires_instrumental_or_locative_complement() -> None:
    propositions = build_positive_propositions(
        "Alguien hizo una compra; mi tarjeta quedó en casa.",
        "es",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in {
        item.family for item in propositions
    }


def test_b2r_b7_known_actor_perform_still_requires_permission_absence() -> None:
    es = _families(
        "Mi hijo hizo compras con mi tarjeta.",
        "es",
    )
    pt = _families(
        "Meu filho fez compras no meu cartão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt



@pytest.mark.parametrize(
    ("message", "language"),
    [
        (
            "Le presté la tarjeta a mi hijo para el súper y compró ropa sin permiso.",
            "es",
        ),
        (
            "Le pasé la tarjeta a mi hija para la gasolina y compró ropa sin permiso.",
            "es",
        ),
        (
            "Le dejé la tarjeta a mi hijo para la farmacia y compró ropa sin permiso.",
            "es",
        ),
        (
            "Emprestei o cartão para minha filha comprar remédio e ela comprou roupas sem permissão.",
            "pt",
        ),
        (
            "Deixei o cartão com meu filho para comprar remédio e ele comprou roupas sem permissão.",
            "pt",
        ),
    ],
)
def test_b2r_b8_closed_limited_grant_verbs_support_exceeded_purpose(
    message: str,
    language: str,
) -> None:
    propositions = build_positive_propositions(message, language)

    assert any(
        item.rule == "P5-exceeded-authorization-purpose"
        for item in propositions
    )


def test_b2r_b8_limited_grant_can_link_immediately_prior_primary_clause() -> None:
    propositions = build_positive_propositions(
        "Le di la tarjeta a mi hija para la gasolina; compró ropa sin permiso.",
        "es",
    )

    assert any(
        item.rule == "P5-exceeded-authorization-purpose"
        for item in propositions
    )


def test_b2r_b8_limited_grant_does_not_jump_over_intervening_primary_clause() -> None:
    propositions = build_positive_propositions(
        "Le di la tarjeta a mi hija para la gasolina; llamé al banco; compró ropa sin permiso.",
        "es",
    )

    assert not any(
        item.rule == "P5-exceeded-authorization-purpose"
        for item in propositions
    )


def test_b2r_b8_local_grant_verbs_do_not_become_general_p4_predicates() -> None:
    es = build_positive_propositions(
        "Yo no presté permiso para esta compra.",
        "es",
    )
    pt = build_positive_propositions(
        "Eu não emprestei permissão para esta compra.",
        "pt",
    )

    assert PropositionFamily.AUTHORIZATION_DENIAL not in {
        item.family for item in (*es, *pt)
    }



def test_b2r_b9_p6_accepts_customer_existential_frame() -> None:
    es = _families(
        "Hay un cargo fraudulento.",
        "es",
    )
    pt = _families(
        "Há uma cobrança fraudulenta.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION in pt


def test_b2r_b9_p6_accepts_customer_instrument_locative_anchor() -> None:
    es = _families(
        "Un cargo fraudulento apareció en mi tarjeta.",
        "es",
    )
    pt = _families(
        "Uma cobrança fraudulenta apareceu no meu cartão.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION in pt


def test_b2r_b9_p6_matches_audit_existential_plus_instrument_case() -> None:
    propositions = build_positive_propositions(
        "Hay un cargo fraudulento en mi tarjeta.",
        "es",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION in {
        item.family for item in propositions
    }


def test_b2r_b9_instrument_locative_requires_customer_possession() -> None:
    es = _families(
        "Un cargo fraudulento apareció en su tarjeta.",
        "es",
    )
    pt = _families(
        "Uma cobrança fraudulenta apareceu no cartão dela.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in pt



def test_b2r_b10_unaccented_pt_copula_supports_p1_ownership_denial() -> None:
    propositions = build_positive_propositions(
        "Este debito nao e meu.",
        "pt",
    )

    assert PropositionFamily.OWNERSHIP_DENIAL in {
        item.family for item in propositions
    }


def test_b2r_b10_unaccented_pt_copula_supports_p6_fraud_noun() -> None:
    propositions = build_positive_propositions(
        "Este Pix e um golpe.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION in {
        item.family for item in propositions
    }


def test_b2r_b10_unaccented_pt_copula_supports_p6_fraud_adjective() -> None:
    propositions = build_positive_propositions(
        "Este debito e fraudulento.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION in {
        item.family for item in propositions
    }


def test_b2r_b10_unaccented_pt_e_conjunction_does_not_create_p1() -> None:
    propositions = build_positive_propositions(
        "Este debito nao apareceu e meu cartao foi bloqueado.",
        "pt",
    )

    assert PropositionFamily.OWNERSHIP_DENIAL not in {
        item.family for item in propositions
    }


def test_b2r_b10_unaccented_pt_e_conjunction_does_not_create_p6() -> None:
    propositions = build_positive_propositions(
        "Este Pix saiu e um golpe foi reportado.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in {
        item.family for item in propositions
    }



def test_b2r_b11_f20_spanish_participial_amount_exceedance() -> None:
    propositions = build_positive_propositions(
        "Mi hijo gastó más de lo autorizado.",
        "es",
    )

    assert any(
        item.rule == "P5-exceeded-authorization-amount"
        for item in propositions
    )


def test_b2r_b11_f20_portuguese_alem_do_participial_amount_exceedance() -> None:
    propositions = build_positive_propositions(
        "Meu irmão gastou além do combinado.",
        "pt",
    )

    assert any(
        item.rule == "P5-exceeded-authorization-amount"
        for item in propositions
    )


def test_b2r_b11_f20_portuguese_mais_do_que_o_participial_amount_exceedance() -> None:
    propositions = build_positive_propositions(
        "Meu irmão gastou mais do que o autorizado.",
        "pt",
    )

    assert any(
        item.rule == "P5-exceeded-authorization-amount"
        for item in propositions
    )


def test_b2r_b11_f20_participial_exceedance_still_requires_known_actor() -> None:
    propositions = build_positive_propositions(
        "Gastou além do combinado.",
        "pt",
    )

    assert not any(
        item.rule == "P5-exceeded-authorization-amount"
        for item in propositions
    )


def test_b2r_b11_f20_participial_exceedance_still_requires_third_party_action() -> None:
    propositions = build_positive_propositions(
        "Com meu irmão na loja, gastei além do combinado.",
        "pt",
    )

    assert not any(
        item.rule == "P5-exceeded-authorization-amount"
        for item in propositions
    )


def test_b2r_b11_f20_participial_exceedance_respects_action_denial() -> None:
    propositions = build_positive_propositions(
        "Meu irmão não gastou além do combinado.",
        "pt",
    )

    assert not any(
        item.rule == "P5-exceeded-authorization-amount"
        for item in propositions
    )



def test_b2r_c1_f12_self_performed_fraud_carries_counter_evidence() -> None:
    es = build_positive_propositions(
        "La transferencia que yo mismo hice fue un fraude.",
        "es",
    )
    pt = build_positive_propositions(
        "Eu mesmo fiz esse Pix e foi um golpe.",
        "pt",
    )

    es_p6 = next(
        item for item in es
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    pt_p6 = next(
        item for item in pt
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert EvidenceAtomKind.SELF_PERFORMED in {
        atom.kind for atom in es_p6.counter_evidence
    }
    assert EvidenceAtomKind.SELF_PERFORMED in {
        atom.kind for atom in pt_p6.counter_evidence
    }
    assert all(
        atom.activity_token_span == es_p6.activity_token_span
        for atom in es_p6.counter_evidence
    )
    assert all(
        atom.activity_token_span == pt_p6.activity_token_span
        for atom in pt_p6.counter_evidence
    )


def test_b2r_c1_f12_self_authorized_fraud_carries_counter_evidence() -> None:
    es = build_positive_propositions(
        "Esta transferencia que yo autoricé fue un fraude.",
        "es",
    )
    pt = build_positive_propositions(
        "Este Pix que eu autorizei foi um golpe.",
        "pt",
    )

    es_p6 = next(
        item for item in es
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    pt_p6 = next(
        item for item in pt
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert EvidenceAtomKind.SELF_AUTHORIZED in {
        atom.kind for atom in es_p6.counter_evidence
    }
    assert EvidenceAtomKind.SELF_AUTHORIZED in {
        atom.kind for atom in pt_p6.counter_evidence
    }


def test_b2r_c1_f12_third_party_performance_does_not_create_self_counter_evidence() -> None:
    es = build_positive_propositions(
        "La transferencia que mi hermano hizo fue un fraude.",
        "es",
    )
    pt = build_positive_propositions(
        "Esse Pix que meu irmão fez foi um golpe.",
        "pt",
    )

    es_p6 = next(
        item for item in es
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    pt_p6 = next(
        item for item in pt
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert not es_p6.counter_evidence
    assert not pt_p6.counter_evidence


def test_b2r_c1_f12_separate_unauthorized_proposition_remains_independent() -> None:
    es = build_positive_propositions(
        "La transferencia que yo mismo hice fue un fraude. Este cargo no es mío.",
        "es",
    )
    pt = build_positive_propositions(
        "Eu mesmo fiz esse Pix e foi um golpe. Este débito não é meu.",
        "pt",
    )

    for propositions in (es, pt):
        p6 = next(
            item for item in propositions
            if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
        )
        assert p6.counter_evidence
        assert any(
            item.family is PropositionFamily.OWNERSHIP_DENIAL
            for item in propositions
        )



def test_b2r_c2_f14_p2_clitic_links_prior_activity_in_spanish_and_portuguese() -> None:
    es = build_positive_propositions(
        "Me apareció un cobro raro. No lo hice yo.",
        "es",
    )
    pt = build_positive_propositions(
        "Recebi uma cobrança estranha. Eu não a fiz.",
        "pt",
    )

    es_p2 = next(
        item for item in es
        if item.family is PropositionFamily.PERFORMANCE_DENIAL
        and item.rule == "P2-R3-activity-anaphora"
    )
    pt_p2 = next(
        item for item in pt
        if item.family is PropositionFamily.PERFORMANCE_DENIAL
        and item.rule == "P2-R3-activity-anaphora"
    )

    assert es_p2.activity_ref == "linked_prior_activity"
    assert pt_p2.activity_ref == "linked_prior_activity"
    assert es_p2.activity_token_span is not None
    assert pt_p2.activity_token_span is not None


def test_b2r_c2_f14_p4_clitic_links_prior_activity_in_spanish_and_portuguese() -> None:
    es = build_positive_propositions(
        "Me apareció un cobro raro. No lo autoricé.",
        "es",
    )
    pt = build_positive_propositions(
        "Recebi uma cobrança estranha. Eu não a autorizei.",
        "pt",
    )

    es_p4 = next(
        item for item in es
        if item.family is PropositionFamily.AUTHORIZATION_DENIAL
        and item.rule == "P4-R3-activity-anaphora"
    )
    pt_p4 = next(
        item for item in pt
        if item.family is PropositionFamily.AUTHORIZATION_DENIAL
        and item.rule == "P4-R3-activity-anaphora"
    )

    assert es_p4.activity_ref == "linked_prior_activity"
    assert pt_p4.activity_ref == "linked_prior_activity"


def test_b2r_c2_f14_p4_demonstrative_links_prior_activity_in_both_languages() -> None:
    es = build_positive_propositions(
        "Me apareció un cobro raro. Eso no lo autoricé.",
        "es",
    )
    pt = build_positive_propositions(
        "Recebi uma cobrança estranha. Isso eu não autorizei.",
        "pt",
    )

    es_p4 = next(
        item for item in es
        if item.family is PropositionFamily.AUTHORIZATION_DENIAL
        and item.rule == "P4-R3-activity-anaphora"
    )
    pt_p4 = next(
        item for item in pt
        if item.family is PropositionFamily.AUTHORIZATION_DENIAL
        and item.rule == "P4-R3-activity-anaphora"
    )

    assert es_p4.activity_ref == "linked_prior_activity"
    assert pt_p4.activity_ref == "linked_prior_activity"


def test_b2r_c2_f14_same_clause_activity_precedes_d2_backlink() -> None:
    es = build_positive_propositions(
        "Me apareció un cobro raro. Esta compra no la hice yo.",
        "es",
    )
    pt = build_positive_propositions(
        "Recebi uma cobrança estranha. Esta compra eu não fiz.",
        "pt",
    )

    es_p2 = next(
        item for item in es
        if item.family is PropositionFamily.PERFORMANCE_DENIAL
        and item.clause_index == 1
    )
    pt_p2 = next(
        item for item in pt
        if item.family is PropositionFamily.PERFORMANCE_DENIAL
        and item.clause_index == 1
    )

    assert es_p2.activity_ref == "explicit_activity"
    assert pt_p2.activity_ref == "explicit_activity"
    assert es_p2.rule == "P2"
    assert pt_p2.rule == "P2"


def test_b2r_c2_f14_anaphor_without_prior_activity_keeps_topic_default() -> None:
    es = build_positive_propositions("No lo hice yo.", "es")
    pt = build_positive_propositions("Eu não a autorizei.", "pt")

    es_p2 = next(
        item for item in es
        if item.family is PropositionFamily.PERFORMANCE_DENIAL
    )
    pt_p4 = next(
        item for item in pt
        if item.family is PropositionFamily.AUTHORIZATION_DENIAL
    )

    assert es_p2.activity_ref == "topic_transaction"
    assert pt_p4.activity_ref == "topic_transaction"
    assert es_p2.rule == "P2"
    assert pt_p4.rule == "P4"



def test_b2r_e1a_p7_closed_modifiers_reach_activity_head() -> None:
    es_examples = (
        "No reconozco este otro cargo.",
        "No reconozco estos dos cargos.",
        "No reconozco el segundo cargo.",
        "No reconozco el último cargo.",
    )
    pt_examples = (
        "Não reconheço essa outra compra.",
        "Não reconheço essas duas compras.",
        "Não reconheço a última compra.",
    )

    for text in es_examples:
        assert PropositionFamily.ACTIVITY_NONRECOGNITION in _families(
            text,
            "es",
        )
    for text in pt_examples:
        assert PropositionFamily.ACTIVITY_NONRECOGNITION in _families(
            text,
            "pt",
        )


def test_b2r_e1a_preposed_modified_activity_remains_targetable() -> None:
    es = _families("Este otro cargo no lo reconozco.", "es")
    pt = _families("Essa outra compra eu não reconheço.", "pt")

    assert PropositionFamily.ACTIVITY_NONRECOGNITION in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION in pt


def test_b2r_e1a_modified_non_activity_head_remains_rejected() -> None:
    es = _families("No reconozco este otro correo.", "es")
    pt = _families("Não reconheço esse outro site.", "pt")

    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in es
    assert PropositionFamily.ACTIVITY_NONRECOGNITION not in pt


def test_b2r_e1a_p6_closed_modifiers_preserve_customer_anchor() -> None:
    es = _families("Esta otra compra fue un fraude.", "es")
    pt = _families("Essa outra compra foi golpe.", "pt")

    assert PropositionFamily.FRAUD_CHARACTERIZATION in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION in pt



def test_b2r_e1b_f12_direct_object_self_action_keeps_same_referent_atom() -> None:
    es = build_positive_propositions(
        "Yo hice esta transferencia y fue un fraude.",
        "es",
    )
    pt = build_positive_propositions(
        "Eu autorizei este Pix e foi um golpe.",
        "pt",
    )

    es_p6 = next(
        item for item in es
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    pt_p6 = next(
        item for item in pt
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert EvidenceAtomKind.SELF_PERFORMED in {
        atom.kind for atom in es_p6.counter_evidence
    }
    assert EvidenceAtomKind.SELF_AUTHORIZED in {
        atom.kind for atom in pt_p6.counter_evidence
    }


def test_b2r_e1b_f12_unrelated_self_action_does_not_attach_to_fraud_p6() -> None:
    es = build_positive_propositions(
        "Yo pagué la factura, pero este cargo es un fraude.",
        "es",
    )
    pt = build_positive_propositions(
        "Eu paguei a fatura, mas esta cobrança é golpe.",
        "pt",
    )

    es_p6 = next(
        item for item in es
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    pt_p6 = next(
        item for item in pt
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert not es_p6.counter_evidence
    assert not pt_p6.counter_evidence


def test_b2r_e1b_f12_unrelated_authorization_does_not_attach_to_later_fraud_p6() -> None:
    es = build_positive_propositions(
        "Autoricé el pago del gimnasio, pero este otro cargo es un fraude.",
        "es",
    )
    pt = build_positive_propositions(
        "Eu autorizei o Pix da academia, mas esta outra cobrança foi golpe.",
        "pt",
    )

    es_p6 = next(
        item for item in es
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    pt_p6 = next(
        item for item in pt
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert not es_p6.counter_evidence
    assert not pt_p6.counter_evidence


def test_b2r_e1b_p6_does_not_skip_unanchored_nearer_activity_np() -> None:
    es = build_positive_propositions(
        "Autoricé este pago, pero cargo es un fraude.",
        "es",
    )
    pt = build_positive_propositions(
        "Eu autorizei este Pix, mas cobrança foi golpe.",
        "pt",
    )

    assert not any(
        item.family is PropositionFamily.FRAUD_CHARACTERIZATION
        for item in es
    )
    assert not any(
        item.family is PropositionFamily.FRAUD_CHARACTERIZATION
        for item in pt
    )



def test_b2r_e2a_p1_does_not_borrow_activity_across_segment_boundary() -> None:
    es = _families(
        "La culpa no es mía, el cargo apareció solo.",
        "es",
    )
    pt = _families(
        "A culpa não é minha, a compra apareceu sozinha.",
        "pt",
    )

    assert PropositionFamily.OWNERSHIP_DENIAL not in es
    assert PropositionFamily.OWNERSHIP_DENIAL not in pt


def test_b2r_e2a_p1_response_particle_does_not_negate_copula() -> None:
    es = _families("No, es mío ese cargo.", "es")
    pt = _families("Não, é meu esse pagamento.", "pt")

    assert PropositionFamily.OWNERSHIP_DENIAL not in es
    assert PropositionFamily.OWNERSHIP_DENIAL not in pt


def test_b2r_e2a_p1_embedded_negation_does_not_negate_copula() -> None:
    es = _families("El cargo que no entendía es mío.", "es")
    pt = _families("A compra que eu não lembrava é minha.", "pt")

    assert PropositionFamily.OWNERSHIP_DENIAL not in es
    assert PropositionFamily.OWNERSHIP_DENIAL not in pt


def test_b2r_e2a_p1_does_not_jump_from_non_activity_subject_to_later_activity() -> None:
    es = _families(
        "Ese correo no es mío, pero la compra sí la hice.",
        "es",
    )
    pt = _families(
        "Esse email não é meu, mas a compra eu fiz.",
        "pt",
    )

    assert PropositionFamily.OWNERSHIP_DENIAL not in es
    assert PropositionFamily.OWNERSHIP_DENIAL not in pt


def test_b2r_e2a_p1_postcopular_activity_fallback_remains_bounded_positive() -> None:
    es = _families("No es mío ese cargo.", "es")
    pt = _families("Não é meu esse pagamento.", "pt")

    assert PropositionFamily.OWNERSHIP_DENIAL in es
    assert PropositionFamily.OWNERSHIP_DENIAL in pt



def test_b2r_e2b_pt_terminal_postverbal_nao_remains_valid() -> None:
    pt = _families("Eu fiz essa compra não.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL in pt


def test_b2r_e2b_spanish_postverbal_no_does_not_bind() -> None:
    es = _families("Yo hice no esa compra.", "es")

    assert PropositionFamily.PERFORMANCE_DENIAL not in es


def test_b2r_e2b_pt_nonterminal_postverbal_nao_does_not_bind() -> None:
    pt = _families("Eu fiz não essa compra.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL not in pt


def test_b2r_e2b_pt_terminal_nao_does_not_cross_original_distance_bound() -> None:
    pt = _families("Eu fiz essa compra ontem não.", "pt")

    assert PropositionFamily.PERFORMANCE_DENIAL not in pt



def test_b2r_e3a_nearer_known_actor_beats_farther_unknown_actor() -> None:
    es = _families(
        "Alguien habló con mi hermano y mi hermano usó mi tarjeta.",
        "es",
    )
    pt = _families(
        "Alguém falou com meu irmão e meu irmão usou minha conta.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt


def test_b2r_e3a_nearer_known_actor_with_permission_absence_remains_positive() -> None:
    es = _families(
        "Alguien habló con mi hermano y mi hermano usó mi tarjeta sin permiso.",
        "es",
    )
    pt = _families(
        "Alguém falou com meu irmão e meu irmão usou minha conta sem permissão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt


def test_b2r_e3a_same_clause_d3_rejects_first_person_action() -> None:
    es = build_positive_propositions(
        "Con mi hermano, usé mi tarjeta, yo no le di permiso.",
        "es",
    )
    pt = build_positive_propositions(
        "Com meu irmão, usei meu cartão, eu não lhe dei permissão.",
        "pt",
    )

    assert not any(
        item.rule == "P4-R3-permission-backlink"
        for item in es
    )
    assert not any(
        item.rule == "P4-R3-permission-backlink"
        for item in pt
    )



def test_b2r_e3b_known_actor_relational_victims_block_false_customer_anchor() -> None:
    es = _families(
        "El cargo fraudulento de mi sobrino apareció hoy.",
        "es",
    )
    pt = _families(
        "A cobrança fraudulenta do meu cunhado apareceu hoje.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in pt


def test_b2r_e3b_existing_relational_victim_terms_remain_blocking() -> None:
    es = _families(
        "El cargo fraudulento de mi vecino apareció hoy.",
        "es",
    )
    pt = _families(
        "A cobrança fraudulenta do meu pai apareceu hoje.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION not in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION not in pt



def test_b2r_e3c_d2_article_before_non_activity_noun_does_not_backlink_p2() -> None:
    es = build_positive_propositions(
        "Me apareció un cobro raro. Yo no hice la llamada.",
        "es",
    )
    pt = build_positive_propositions(
        "Recebi uma cobrança estranha. Eu não fiz a mensagem.",
        "pt",
    )

    assert not any(
        item.rule == "P2-R3-activity-anaphora"
        for item in es
    )
    assert not any(
        item.rule == "P2-R3-activity-anaphora"
        for item in pt
    )


def test_b2r_e3c_d2_article_before_non_activity_noun_does_not_backlink_p4() -> None:
    es = build_positive_propositions(
        "Me apareció un cobro raro. Yo no autoricé la llamada.",
        "es",
    )
    pt = build_positive_propositions(
        "Recebi uma cobrança estranha. Eu não autorizei a mensagem.",
        "pt",
    )

    assert not any(
        item.rule == "P4-R3-activity-anaphora"
        for item in es
    )
    assert not any(
        item.rule == "P4-R3-activity-anaphora"
        for item in pt
    )


def test_b2r_e3c_d2_clitic_backlinks_remain_positive() -> None:
    es = build_positive_propositions(
        "Me apareció un cobro raro. No la hice yo.",
        "es",
    )
    pt = build_positive_propositions(
        "Recebi uma cobrança estranha. Eu não a autorizei.",
        "pt",
    )

    assert any(
        item.rule == "P2-R3-activity-anaphora"
        for item in es
    )
    assert any(
        item.rule == "P4-R3-activity-anaphora"
        for item in pt
    )



_PUBLIC_POSITIVE_SOURCE_FILES = (
    "test_unauthorized_breadth.py",
    "test_unauthorized_compositional.py",
)


def _parse_public_test_source(filename: str) -> ast.Module:
    source_path = Path(__file__).with_name(filename)
    return ast.parse(source_path.read_text(encoding="utf-8"))


def _literal_assignment(module: ast.Module, name: str):
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"missing frozen public assignment: {name}")


def _function_literal_assignment(
    module: ast.Module,
    function_name: str,
    assignment_name: str,
):
    function = next(
        (
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef)
            and node.name == function_name
        ),
        None,
    )
    assert function is not None, function_name

    for node in function.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == assignment_name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(
        f"missing frozen public assignment: {function_name}.{assignment_name}"
    )


def _parametrize_literal_values(
    module: ast.Module,
    function_name: str,
):
    function = next(
        (
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef)
            and node.name == function_name
        ),
        None,
    )
    assert function is not None, function_name

    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if len(decorator.args) < 2:
            continue
        try:
            return ast.literal_eval(decorator.args[1])
        except (TypeError, ValueError):
            continue
    raise AssertionError(f"missing literal parametrize values: {function_name}")


def _frozen_public_positive_inventory() -> tuple[str, ...]:
    breadth = _parse_public_test_source(_PUBLIC_POSITIVE_SOURCE_FILES[0])
    compositional = _parse_public_test_source(_PUBLIC_POSITIVE_SOURCE_FILES[1])
    messages: set[str] = set()

    breadth_http = _parametrize_literal_values(
        breadth,
        "test_http_unauthorized_paraphrases_escalate_without_cross_customer_disclosure",
    )
    messages.update(row[2] for row in breadth_http)

    messages.update(_literal_assignment(breadth, "_AUDIT_MISS_CASES"))

    audit_templates = _function_literal_assignment(
        breadth,
        "_audit_http_cases",
        "templates",
    )
    for persona_id, template in audit_templates:
        owned = "DEMO-ES-1001" if persona_id == "lucia" else "DEMO-PT-2001"
        foreign = "DEMO-PT-2001" if persona_id == "lucia" else "DEMO-ES-1001"
        for transaction_id in (owned, foreign, None):
            suffix = f": {transaction_id}" if transaction_id is not None else ""
            messages.add(template.format(suffix=suffix))

    symmetry = _parametrize_literal_values(
        breadth,
        "test_unauthorized_backstop_preserves_language_and_form_symmetry",
    )
    for left, right in symmetry:
        messages.add(left)
        messages.add(right)

    compositional_explicit = _parametrize_literal_values(
        compositional,
        "test_compositional_explicit_unauthorized_assertions",
    )
    messages.update(compositional_explicit)

    compositional_independent = _parametrize_literal_values(
        compositional,
        "test_scope_controls_do_not_hide_independent_current_assertions",
    )
    messages.update(compositional_independent)

    http_structures = _literal_assignment(compositional, "_HTTP_STRUCTURES")
    for persona_id, without_id, with_id_template in http_structures:
        owned = "DEMO-ES-1001" if persona_id == "lucia" else "DEMO-PT-2001"
        foreign = "DEMO-PT-2001" if persona_id == "lucia" else "DEMO-ES-1001"
        messages.add(with_id_template.format(transaction_id=owned))
        messages.add(with_id_template.format(transaction_id=foreign))
        messages.add(without_id)

    return tuple(sorted(messages))


def test_b2r_e4_frozen_public_positive_inventory_yields_unresolved_proposition() -> None:
    inventory = _frozen_public_positive_inventory()

    assert len(inventory) == 130
    for message in inventory:
        propositions = (
            *build_positive_propositions(message, "es"),
            *build_positive_propositions(message, "pt"),
        )
        assert any(
            item.mode == "unresolved"
            for item in propositions
        ), message



def test_b2r_g1_f12_relative_head_keeps_same_referent_atom() -> None:
    es = build_positive_propositions(
        "La transferencia que yo mismo hice fue un fraude.",
        "es",
    )
    pt = build_positive_propositions(
        "O Pix que eu fiz foi um golpe.",
        "pt",
    )

    es_p6 = next(
        item for item in es
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    pt_p6 = next(
        item for item in pt
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert EvidenceAtomKind.SELF_PERFORMED in {
        atom.kind for atom in es_p6.counter_evidence
    }
    assert EvidenceAtomKind.SELF_PERFORMED in {
        atom.kind for atom in pt_p6.counter_evidence
    }


def test_b2r_g1_f12_resumptive_clitic_keeps_same_referent_atom() -> None:
    es = build_positive_propositions(
        "Esta compra la hice yo y fue un fraude.",
        "es",
    )
    pt = build_positive_propositions(
        "Esta transferência eu a fiz e foi golpe.",
        "pt",
    )

    es_p6 = next(
        item for item in es
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    pt_p6 = next(
        item for item in pt
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert EvidenceAtomKind.SELF_PERFORMED in {
        atom.kind for atom in es_p6.counter_evidence
    }
    assert EvidenceAtomKind.SELF_PERFORMED in {
        atom.kind for atom in pt_p6.counter_evidence
    }


def test_b2r_g1_f12_subordinate_or_finite_barrier_blocks_unrelated_atom() -> None:
    es = build_positive_propositions(
        "El cargo fraudulento salió después de que pagué la luz.",
        "es",
    )
    pt = build_positive_propositions(
        "Essa cobrança fraudulenta apareceu logo depois que eu fiz um Pix para minha mãe.",
        "pt",
    )

    es_p6 = next(
        item for item in es
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    pt_p6 = next(
        item for item in pt
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert not es_p6.counter_evidence
    assert not pt_p6.counter_evidence


def test_b2r_g1_f12_article_or_preposition_is_not_resumptive_clitic() -> None:
    es = build_positive_propositions(
        "Este cargo fraudulento apareció en la app cuando pagué el gimnasio.",
        "es",
    )
    pt = build_positive_propositions(
        "Essa cobrança fraudulenta chegou a mim quando eu paguei o aluguel.",
        "pt",
    )

    es_p6 = next(
        item for item in es
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )
    pt_p6 = next(
        item for item in pt
        if item.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert not es_p6.counter_evidence
    assert not pt_p6.counter_evidence

def test_b2r_g2_p1_postcopular_fallback_rejects_preexisting_nominal_subject() -> None:
    es = _families("La culpa no es mía de este cargo.", "es")
    pt = _families("O erro não é meu nessa cobrança.", "pt")

    assert PropositionFamily.OWNERSHIP_DENIAL not in es
    assert PropositionFamily.OWNERSHIP_DENIAL not in pt


def test_b2r_g2_p1_postcopular_fallback_rejects_prepositional_activity() -> None:
    es = _families("No es mío por ese cargo.", "es")
    pt = _families("Não é meu nessa cobrança.", "pt")

    assert PropositionFamily.OWNERSHIP_DENIAL not in es
    assert PropositionFamily.OWNERSHIP_DENIAL not in pt


def test_b2r_g2_p1_elliptical_coordinated_activity_subject_remains_positive() -> None:
    es = _families("Este cargo y el otro no son míos.", "es")
    pt = _families("Essa compra e a outra não são minhas.", "pt")

    assert PropositionFamily.OWNERSHIP_DENIAL in es
    assert PropositionFamily.OWNERSHIP_DENIAL in pt


def test_b2r_g2_p1_coordinator_remains_barrier_for_clause_transition() -> None:
    es = _families("Este cargo apareció y el correo no es mío.", "es")
    pt = _families("Essa compra apareceu e o email não é meu.", "pt")

    assert PropositionFamily.OWNERSHIP_DENIAL not in es
    assert PropositionFamily.OWNERSHIP_DENIAL not in pt

def test_b2r_g3_prior_clause_d3_rejects_first_person_actions() -> None:
    es_use = build_positive_propositions(
        "Usé mi tarjeta con mi hermano. No le di permiso.",
        "es",
    )
    es_perform = build_positive_propositions(
        "Hice esta compra con mi hermano. No le di permiso.",
        "es",
    )
    pt_use = build_positive_propositions(
        "Usei meu cartão com meu irmão. Não lhe dei permissão.",
        "pt",
    )
    pt_perform = build_positive_propositions(
        "Fiz esta compra com meu irmão. Não lhe dei permissão.",
        "pt",
    )

    for propositions in (es_use, es_perform, pt_use, pt_perform):
        assert not any(
            item.rule == "P4-R3-permission-backlink"
            for item in propositions
        )


def test_b2r_g3_prior_clause_d3_preserves_third_person_backlink() -> None:
    es = build_positive_propositions(
        "Mi hermano usó mi tarjeta. No le di permiso.",
        "es",
    )
    pt = build_positive_propositions(
        "Meu irmão usou meu cartão. Não lhe dei permissão.",
        "pt",
    )

    assert any(
        item.rule == "P4-R3-permission-backlink"
        for item in es
    )
    assert any(
        item.rule == "P4-R3-permission-backlink"
        for item in pt
    )

def test_b2r_g4_pt_terminal_nao_does_not_cross_new_coordinated_subject() -> None:
    performance = _families(
        "Eu a fiz e ela não.",
        "pt",
    )
    authorization = _families(
        "Eu o autorizei e ele não.",
        "pt",
    )

    assert PropositionFamily.PERFORMANCE_DENIAL not in performance
    assert PropositionFamily.AUTHORIZATION_DENIAL not in authorization


def test_b2r_g4_unknown_actor_survives_embedded_known_actor_modifier() -> None:
    es = _families(
        "Alguien del trabajo de mi esposa usó mi tarjeta.",
        "es",
    )
    pt = _families(
        "Alguém da família do meu marido usou meu cartão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt


def test_b2r_g4_unknown_actor_survives_known_actor_inside_relative_modifier() -> None:
    es = _families(
        "Alguien que conoce a mi hijo usó mi tarjeta.",
        "es",
    )
    pt = _families(
        "Alguém que conhece meu filho usou meu cartão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt

def test_b2r_g5a_later_known_subject_outside_relative_regains_precedence() -> None:
    es = _families(
        "Alguien que llamó dijo que mi hijo usó mi tarjeta.",
        "es",
    )
    pt = _families(
        "Alguém que ligou disse que meu irmão usou meu cartão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt


def test_b2r_g5a_complementizer_que_does_not_embed_later_known_actor() -> None:
    es = _families(
        "Le conté a alguien que mi hijo usó mi tarjeta.",
        "es",
    )
    pt = _families(
        "Contei para alguém que meu filho usou meu cartão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt

def test_b2r_g5b_p1_elliptical_coordination_accepts_demonstrative_other() -> None:
    es = _families(
        "Este cargo y este otro no son míos.",
        "es",
    )
    pt = _families(
        "Essa compra e essa outra não são minhas.",
        "pt",
    )

    assert PropositionFamily.OWNERSHIP_DENIAL in es
    assert PropositionFamily.OWNERSHIP_DENIAL in pt


def test_b2r_g5b_p1_elliptical_coordination_accepts_numbered_others() -> None:
    es = _families(
        "Este cargo y los otros dos no son míos.",
        "es",
    )
    pt = _families(
        "Esse Pix e os outros dois não são meus.",
        "pt",
    )

    assert PropositionFamily.OWNERSHIP_DENIAL in es
    assert PropositionFamily.OWNERSHIP_DENIAL in pt


def test_b2r_g5b_p1_elliptical_coordination_accepts_temporal_de_ellipsis() -> None:
    es = _families(
        "El cargo de hoy y el de ayer no son míos.",
        "es",
    )
    pt = _families(
        "A compra de hoje e a de ontem não são minhas.",
        "pt",
    )

    assert PropositionFamily.OWNERSHIP_DENIAL in es
    assert PropositionFamily.OWNERSHIP_DENIAL in pt

def test_b2r_g5c_p6_skips_embedded_activity_referent_in_spanish() -> None:
    message = "La transferencia que salió cuando hice el pago fue un fraude."
    analysis = analyze_foundation(message, "es")
    propositions = build_positive_propositions(message, "es")

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert item.activity_token_span is not None
    assert (
        analysis.tokens[item.activity_token_span[0]].normalized
        == "transferencia"
    )
    assert not item.counter_evidence


def test_b2r_g5c_p6_skips_embedded_activity_referent_in_portuguese() -> None:
    message = "A transferência que apareceu quando eu fiz o pagamento foi golpe."
    analysis = analyze_foundation(message, "pt")
    propositions = build_positive_propositions(message, "pt")

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert item.activity_token_span is not None
    assert (
        analysis.tokens[item.activity_token_span[0]].normalized
        == "transferencia"
    )
    assert not item.counter_evidence


def test_b2r_g5c_p6_preserves_valid_que_relative_activity_head() -> None:
    es = _families(
        "La transferencia que hice fue un fraude.",
        "es",
    )
    pt = _families(
        "O Pix que eu fiz foi golpe.",
        "pt",
    )

    assert PropositionFamily.FRAUD_CHARACTERIZATION in es
    assert PropositionFamily.FRAUD_CHARACTERIZATION in pt

def test_b2r_g5d_p6_que_on_fraud_noun_does_not_donate_self_counter_evidence() -> None:
    message = "Esta transferencia fue un fraude que descubrí cuando hice el reclamo."
    analysis = analyze_foundation(message, "es")
    propositions = build_positive_propositions(message, "es")

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert item.activity_token_span is not None
    assert (
        analysis.tokens[item.activity_token_span[0]].normalized
        == "transferencia"
    )
    assert not item.counter_evidence


def test_b2r_g5d_pt_terminal_nao_distinguishes_accented_e_and_nem_barrier() -> None:
    accented_performance = _families(
        "Eu fiz é não.",
        "pt",
    )
    accented_authorization = _families(
        "Eu autorizei é não.",
        "pt",
    )
    nem_barrier = _families(
        "Eu fiz nem ela não.",
        "pt",
    )

    assert PropositionFamily.PERFORMANCE_DENIAL in accented_performance
    assert PropositionFamily.AUTHORIZATION_DENIAL in accented_authorization
    assert PropositionFamily.PERFORMANCE_DENIAL not in nem_barrier


def test_b2r_g5d_pt_terminal_nao_authorization_positive_control() -> None:
    pt = _families(
        "Eu autorizei essa compra não.",
        "pt",
    )

    assert PropositionFamily.AUTHORIZATION_DENIAL in pt

def test_b2r_g6a_fronted_adverbial_keeps_main_p6_referent_with_comma() -> None:
    cases = (
        ("Cuando hice el pago, la transferencia fue un fraude.", "es", "transferencia"),
        ("Quando eu fiz o pagamento, a transferência foi golpe.", "pt", "transferencia"),
    )

    for message, language, expected_activity in cases:
        analysis = analyze_foundation(message, language)
        propositions = build_positive_propositions(message, language)
        item = next(
            proposition
            for proposition in propositions
            if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
        )

        assert item.activity_token_span is not None
        assert (
            analysis.tokens[item.activity_token_span[0]].normalized
            == expected_activity
        )
        assert not item.counter_evidence


def test_b2r_g6a_fronted_adverbial_keeps_main_p6_referent_without_comma() -> None:
    cases = (
        ("Cuando hice el pago la transferencia fue un fraude.", "es", "transferencia"),
        ("Quando eu fiz o pagamento a transferência foi golpe.", "pt", "transferencia"),
    )

    for message, language, expected_activity in cases:
        analysis = analyze_foundation(message, language)
        propositions = build_positive_propositions(message, language)
        item = next(
            proposition
            for proposition in propositions
            if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
        )

        assert item.activity_token_span is not None
        assert (
            analysis.tokens[item.activity_token_span[0]].normalized
            == expected_activity
        )
        assert not item.counter_evidence


def test_b2r_g6a_fronted_frame_relative_does_not_select_embedded_activity() -> None:
    message = "Cuando hice el pago que me pidieron la transferencia fue un fraude."
    analysis = analyze_foundation(message, "es")
    propositions = build_positive_propositions(message, "es")

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert item.activity_token_span is not None
    assert (
        analysis.tokens[item.activity_token_span[0]].normalized
        == "transferencia"
    )
    assert not item.counter_evidence


def test_b2r_g6a_nested_relative_under_adverbial_does_not_escape_embedding() -> None:
    cases = (
        (
            "La transferencia que apareció cuando hice el pago que me pidieron fue un fraude.",
            "es",
        ),
        (
            "A transferência que apareceu quando eu fiz o pagamento que me pediram foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.activity_token_span is not None
            and proposition.counter_evidence
            for proposition in propositions
        )

def test_b2r_g6b_complementizer_adverb_known_subject_regains_precedence() -> None:
    es = _families(
        "Le conté a alguien que ayer mi hijo usó mi tarjeta.",
        "es",
    )
    pt = _families(
        "Contei para alguém que ontem meu filho usou meu cartão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt


def test_b2r_g6b_complementizer_copula_known_subject_regains_precedence() -> None:
    es = _families(
        "Le conté a alguien que fue mi hijo quien usó mi tarjeta.",
        "es",
    )
    pt = _families(
        "Contei para alguém que foi meu filho quem usou meu cartão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE not in pt


def test_b2r_g6b_unlisted_relative_verb_still_embeds_known_actor() -> None:
    es = _families(
        "Alguien que conoce a mi hijo usó mi tarjeta.",
        "es",
    )
    pt = _families(
        "Alguém que conhece meu filho usou meu cartão.",
        "pt",
    )

    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in es
    assert PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE in pt

def test_b2r_g7a_coordinated_conjunct_does_not_attach_prior_activity_spanish() -> None:
    message = "Hice el pago y cuando usé la tarjeta la compra fue un fraude."
    analysis = analyze_foundation(message, "es")
    propositions = build_positive_propositions(message, "es")

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert item.activity_token_span is not None
    assert analysis.tokens[item.activity_token_span[0]].normalized == "compra"
    assert not item.counter_evidence


def test_b2r_g7a_coordinated_conjunct_does_not_attach_prior_activity_portuguese() -> None:
    message = "Eu fiz o pagamento e quando usei o cartão a compra foi golpe."
    analysis = analyze_foundation(message, "pt")
    propositions = build_positive_propositions(message, "pt")

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert item.activity_token_span is not None
    assert analysis.tokens[item.activity_token_span[0]].normalized == "compra"
    assert not item.counter_evidence


def test_b2r_g7a_coordinated_frame_with_comma_keeps_true_p6_referent() -> None:
    message = "Hice el pago y cuando usé la tarjeta, la compra fue un fraude."
    analysis = analyze_foundation(message, "es")
    propositions = build_positive_propositions(message, "es")

    item = next(
        proposition
        for proposition in propositions
        if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
    )

    assert item.activity_token_span is not None
    assert analysis.tokens[item.activity_token_span[0]].normalized == "compra"
    assert not item.counter_evidence


def test_b2r_g7a_relative_internal_coordination_still_anchors_nested_activity() -> None:
    cases = (
        (
            "La transferencia que salió y que apareció cuando hice el pago fue un fraude.",
            "es",
        ),
        (
            "A transferência que apareceu e sumiu quando eu fiz o pagamento foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.activity_token_span is not None
            and proposition.counter_evidence
            for proposition in propositions
        )

def test_b2r_g7b_long_relative_internal_y_e_keeps_nested_activity_embedded() -> None:
    cases = (
        (
            "La transferencia que salió de la cuenta y apareció cuando hice el pago fue un fraude.",
            "es",
        ),
        (
            "A transferência que saiu da conta e apareceu quando eu fiz o pagamento foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7b_long_relative_internal_pero_mas_keeps_nested_activity_embedded() -> None:
    cases = (
        (
            "La transferencia que salió de la cuenta pero apareció cuando hice el pago fue un fraude.",
            "es",
        ),
        (
            "A transferência que saiu da conta mas apareceu quando eu fiz o pagamento foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7b_coordinated_b2ri02_nested_relative_stays_embedded() -> None:
    cases = (
        (
            "La transferencia que apareció y salió cuando hice el pago que me pidieron fue un fraude.",
            "es",
        ),
        (
            "A transferência que apareceu e saiu quando eu fiz o pagamento que me pediram foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7b_relative_internal_coordination_does_not_donate_self_authorized() -> None:
    cases = (
        (
            "La transferencia que salió de la cuenta y apareció cuando autoricé el pago fue un fraude.",
            "es",
        ),
        (
            "A transferência que saiu da conta e apareceu quando autorizei o pagamento foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7b_true_conjunct_boundary_still_restores_later_referent() -> None:
    cases = (
        (
            "La compra que hice está bien y cuando hice el pago la transferencia fue un fraude.",
            "es",
            "transferencia",
        ),
        (
            "A compra que eu fiz está certa e quando eu fiz o pagamento a transferência foi golpe.",
            "pt",
            "transferencia",
        ),
    )

    for message, language, expected_activity in cases:
        analysis = analyze_foundation(message, language)
        propositions = build_positive_propositions(message, language)
        item = next(
            proposition
            for proposition in propositions
            if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
        )
        assert item.activity_token_span is not None
        assert (
            analysis.tokens[item.activity_token_span[0]].normalized
            == expected_activity
        )
        assert not item.counter_evidence

def test_b2r_g7c_immediate_y_e_relative_frame_stays_embedded() -> None:
    cases = (
        (
            "La transferencia que salió de la cuenta y cuando hice el pago volvió a aparecer fue un fraude.",
            "es",
        ),
        (
            "A transferência que saiu da conta e quando eu fiz o pagamento voltou a aparecer foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7c_immediate_pero_mas_relative_frame_stays_embedded() -> None:
    cases = (
        (
            "La transferencia que salió de la cuenta pero cuando hice el pago volvió a aparecer fue un fraude.",
            "es",
        ),
        (
            "A transferência que saiu da conta mas quando eu fiz o pagamento voltou a aparecer foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7c_immediate_relative_frame_does_not_donate_self_authorized() -> None:
    cases = (
        (
            "La transferencia que salió de la cuenta y cuando autoricé el pago volvió a aparecer fue un fraude.",
            "es",
        ),
        (
            "A transferência que saiu da conta e quando autorizei o pagamento voltou a aparecer foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7c_immediate_mientras_enquanto_relative_frame_stays_embedded() -> None:
    cases = (
        (
            "La transferencia que salió de la cuenta y mientras hacía el pago volvió a aparecer fue un fraude.",
            "es",
        ),
        (
            "A transferência que saiu da conta e enquanto eu fazia o pagamento voltou a aparecer foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7c_immediate_coordinated_b2ri02_nested_relative_stays_embedded() -> None:
    cases = (
        (
            "La transferencia que apareció y cuando hice el pago que me pidieron salió fue un fraude.",
            "es",
        ),
        (
            "A transferência que apareceu e quando eu fiz o pagamento que me pediram saiu foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )

def test_b2r_g7d_a_pp_nested_relative_self_stays_embedded() -> None:
    cases = (
        (
            "La transferencia que salió de la cuenta y cuando usé la tarjeta para el pago que hice volvió a aparecer fue un fraude.",
            "es",
        ),
        (
            "A transferência que saiu da conta e quando usei o cartão para o pagamento que eu fiz voltou a aparecer foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7d_a_coordinated_object_self_authorized_stays_embedded() -> None:
    cases = (
        (
            "La transferencia que salió de la cuenta y cuando hice la compra y el pago que autoricé volvió a aparecer fue un fraude.",
            "es",
        ),
        (
            "A transferência que saiu da conta e quando fiz a compra e o pagamento que autorizei voltou a aparecer foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7d_a_post_pp_relative_self_stays_embedded() -> None:
    cases = (
        (
            "La transferencia que salió de la cuenta y cuando pagué con la tarjeta el cargo que autoricé volvió a aparecer fue un fraude.",
            "es",
        ),
        (
            "A transferência que saiu da conta e quando paguei com o cartão a cobrança que autorizei voltou a aparecer foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )


def test_b2r_g7d_a_short_coordinated_b2ri02_nonobject_stays_embedded() -> None:
    cases = (
        (
            "La transferencia que apareció y cuando usé la tarjeta en el pago que hice salió fue un fraude.",
            "es",
        ),
        (
            "A transferência que apareceu e quando usei o cartão para o pagamento que eu fiz saiu foi golpe.",
            "pt",
        ),
    )

    for message, language in cases:
        propositions = build_positive_propositions(message, language)
        assert not any(
            proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
            and proposition.counter_evidence
            for proposition in propositions
        )

def test_b2r_g7d_b_frame_subject_relative_self_stays_with_outer_head() -> None:
    cases = (
        (
            "La compra que apareció cuando el pago que autoricé salió fue un fraude.",
            "es",
            "compra",
        ),
        (
            "La transferencia que salió cuando el pago que hice salió fue un fraude.",
            "es",
            "transferencia",
        ),
        (
            "A compra que apareceu quando o pagamento que eu autorizei saiu foi golpe.",
            "pt",
            "compra",
        ),
        (
            "A transferência que saiu quando o pagamento que eu fiz saiu foi golpe.",
            "pt",
            "transferencia",
        ),
    )

    for message, language, expected_activity in cases:
        analysis = analyze_foundation(message, language)
        propositions = build_positive_propositions(message, language)
        item = next(
            proposition
            for proposition in propositions
            if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
        )
        assert item.activity_token_span is not None
        assert (
            analysis.tokens[item.activity_token_span[0]].normalized
            == expected_activity
        )
        assert not item.counter_evidence


def test_b2r_g7d_b_preserves_coordinated_relative_restoration_control() -> None:
    cases = (
        (
            "Hice el pago cuando me pidieron y la transferencia que salió fue un fraude.",
            "es",
            "transferencia",
        ),
        (
            "Fiz o pagamento quando me pediram e a transferência que saiu foi golpe.",
            "pt",
            "transferencia",
        ),
    )

    for message, language, expected_activity in cases:
        analysis = analyze_foundation(message, language)
        propositions = build_positive_propositions(message, language)
        item = next(
            proposition
            for proposition in propositions
            if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
        )
        assert item.activity_token_span is not None
        assert (
            analysis.tokens[item.activity_token_span[0]].normalized
            == expected_activity
        )
        assert not item.counter_evidence


def test_b2r_g7d_b_preserves_ordinary_post_frame_relative_referent() -> None:
    cases = (
        (
            "Hice el pago cuando la transferencia que salió fue un fraude.",
            "es",
            "transferencia",
        ),
        (
            "Fiz o pagamento quando a transferência que saiu foi golpe.",
            "pt",
            "transferencia",
        ),
    )

    for message, language, expected_activity in cases:
        analysis = analyze_foundation(message, language)
        propositions = build_positive_propositions(message, language)
        item = next(
            proposition
            for proposition in propositions
            if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
        )
        assert item.activity_token_span is not None
        assert (
            analysis.tokens[item.activity_token_span[0]].normalized
            == expected_activity
        )
        assert not item.counter_evidence


def test_b2r_g7d_b_does_not_move_relative_self_atom_to_prior_activity() -> None:
    cases = (
        (
            "Hice el pago cuando la compra que hice fue un fraude.",
            "es",
            "compra",
            "pago",
        ),
        (
            "Fiz o pagamento quando a compra que eu fiz foi golpe.",
            "pt",
            "compra",
            "pagamento",
        ),
    )

    for message, language, expected_activity, forbidden_activity in cases:
        analysis = analyze_foundation(message, language)
        propositions = build_positive_propositions(message, language)
        fraud_items = [
            proposition
            for proposition in propositions
            if proposition.family is PropositionFamily.FRAUD_CHARACTERIZATION
        ]
        item = fraud_items[0]
        assert item.activity_token_span is not None
        assert (
            analysis.tokens[item.activity_token_span[0]].normalized
            == expected_activity
        )
        assert not any(
            proposition.activity_token_span is not None
            and analysis.tokens[
                proposition.activity_token_span[0]
            ].normalized == forbidden_activity
            and proposition.counter_evidence
            for proposition in fraud_items
        )

