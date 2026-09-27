from __future__ import annotations

from app.unauthorized_grammar import (
    LexicalTag,
    PredicateFamily,
    SelfRole,
    analyze_foundation,
    find_predicates,
    segment_clauses,
    tag_tokens,
    tokenize_with_source,
)


def _clause_texts(text: str, language: str) -> list[str]:
    analysis = analyze_foundation(text, language)
    return [
        text[clause.source_start : clause.source_end]
        for clause in analysis.clauses
    ]


def test_tolerant_transaction_ids_are_atomic_and_source_preserving() -> None:
    text = "Reviso demo es 1001 y DEMO-PT2001 ahora."
    tokens = tokenize_with_source(text)
    txids = [token for token in tokens if token.is_txid]

    assert [(token.txid_language, token.txid_digits) for token in txids] == [
        ("es", "1001"),
        ("pt", "2001"),
    ]
    assert [text[token.start : token.end] for token in txids] == [
        "demo es 1001",
        "DEMO-PT2001",
    ]
    assert all(token.normalized == "<txid>" for token in txids)


def test_decimal_descriptor_and_intra_word_punctuation_do_not_split_clauses() -> None:
    text = (
        "Um pagamento de R$ 1.200,00 em netflix.com e e-mail não foi meu. "
        "Depois apareceu outro."
    )
    clauses = _clause_texts(text, "pt")

    assert len(clauses) == 2
    assert "1.200,00" in clauses[0]
    assert "netflix.com" in clauses[0]
    assert "e-mail" in clauses[0]


def test_whitespace_dash_is_a_boundary_but_intra_word_hyphen_is_not() -> None:
    text = "Vi um e-mail pré-pago — depois fiz a compra."
    clauses = _clause_texts(text, "pt")

    assert clauses == ["Vi um e-mail pré-pago", "depois fiz a compra"]


def test_colon_only_splits_when_a_finite_predicate_follows() -> None:
    with_predicate = "Aviso: eu fiz a compra."
    without_predicate = "Descriptor: AMZN Mktp."

    assert _clause_texts(with_predicate, "pt") == ["Aviso", "eu fiz a compra"]
    assert _clause_texts(without_predicate, "pt") == ["Descriptor: AMZN Mktp"]


def test_spanish_simple_and_compound_predicate_features_are_generated() -> None:
    simple = analyze_foundation("No hice la compra.", "es")
    compound = analyze_foundation("No lo he hecho.", "es")

    assert any(
        match.form.family is PredicateFamily.PERFORM
        and match.form.lemma == "hacer"
        and match.form.person == 1
        and match.form.number == "singular"
        and match.form.tense_aspect == "preterite"
        for match in simple.predicates
    )
    assert any(
        match.form.family is PredicateFamily.PERFORM
        and match.form.lemma == "hacer"
        and match.form.person == 1
        and match.form.tense_aspect == "present_perfect"
        and match.token_end - match.token_start == 2
        for match in compound.predicates
    )


def test_portuguese_pluperfect_and_iterative_ter_compounds_are_distinguished() -> None:
    pluperfect = analyze_foundation("Eu tinha feito o Pix.", "pt")
    iterative = analyze_foundation("Eu tenho feito compras online.", "pt")

    assert any(
        match.form.family is PredicateFamily.PERFORM
        and match.form.lemma == "fazer"
        and match.form.tense_aspect == "pluperfect"
        for match in pluperfect.predicates
    )
    assert any(
        match.form.family is PredicateFamily.PERFORM
        and match.form.lemma == "fazer"
        and match.form.tense_aspect == "iterative_compound"
        for match in iterative.predicates
    )


def test_accent_collapsed_spanish_form_is_marked_ambiguous_not_silently_resolved() -> None:
    analysis = analyze_foundation("Yo no autorice ese cargo.", "es")
    authorize = [
        match
        for match in analysis.predicates
        if match.form.family is PredicateFamily.AUTHORIZE
        and match.form.lemma == "autorizar"
    ]

    assert any(
        match.form.tense_aspect == "preterite"
        and match.form.person == 1
        and match.accent_ambiguous
        for match in authorize
    )
    assert any(
        match.form.tense_aspect == "present_subjunctive"
        and not match.accent_ambiguous
        for match in authorize
    )


def test_nominal_activity_homograph_is_not_also_used_as_predicate() -> None:
    nominal = analyze_foundation("El pago aparece en mi cuenta.", "es")
    verbal = analyze_foundation("Pago la compra hoy.", "es")

    assert not any(
        match.form.family is PredicateFamily.PERFORM
        and match.form.lemma == "pagar"
        for match in nominal.predicates
    )
    assert any(
        match.form.family is PredicateFamily.PERFORM
        and match.form.lemma == "pagar"
        and match.form.person == 1
        for match in verbal.predicates
    )

    pago_index = next(
        index
        for index, token in enumerate(nominal.tokens)
        if token.normalized == "pago"
    )
    assert LexicalTag.ACTIVITY in nominal.tags[pago_index]


def test_self_roles_distinguish_subject_source_possessor_and_dative() -> None:
    analysis = analyze_foundation(
        "Yo no le di permiso; salió de mí; me avisaron de mi tarjeta.",
        "es",
    )

    roles = {item.role for item in analysis.self_evidence}
    assert SelfRole.SUBJECT in roles
    assert SelfRole.SOURCE in roles
    assert SelfRole.POSSESSOR in roles
    assert SelfRole.DATIVE in roles

    assert any(
        item.role is SelfRole.SUBJECT
        and item.implicit_from_predicate
        for item in analysis.self_evidence
    )


def test_portuguese_no_contraction_is_not_spanish_style_negation() -> None:
    analysis = analyze_foundation("No meu cartão, eu não fiz o Pix.", "pt")

    no_index = next(
        index
        for index, token in enumerate(analysis.tokens)
        if token.normalized == "no"
    )
    nao_index = next(
        index
        for index, token in enumerate(analysis.tokens)
        if token.normalized == "nao"
    )

    assert LexicalTag.NEGATOR not in analysis.tags[no_index]
    assert LexicalTag.NEGATOR in analysis.tags[nao_index]


def test_conditional_tags_require_structural_position_and_preserve_accent() -> None:
    es_assertive = analyze_foundation("Sí, yo hice la compra.", "es")
    es_conditional = analyze_foundation("Si alguien hizo la compra, avísame.", "es")
    pt_reflexive = analyze_foundation("No meu cartão se repetiu a cobrança.", "pt")
    pt_conditional = analyze_foundation("Se alguém fez o Pix, quero saber.", "pt")

    si_assertive = next(
        i for i, token in enumerate(es_assertive.tokens) if token.normalized == "si"
    )
    si_conditional = next(
        i for i, token in enumerate(es_conditional.tokens) if token.normalized == "si"
    )
    se_reflexive = next(
        i for i, token in enumerate(pt_reflexive.tokens) if token.normalized == "se"
    )
    se_conditional = next(
        i for i, token in enumerate(pt_conditional.tokens) if token.normalized == "se"
    )

    assert LexicalTag.CONDITIONAL not in es_assertive.tags[si_assertive]
    assert LexicalTag.CONDITIONAL in es_conditional.tags[si_conditional]
    assert LexicalTag.CONDITIONAL not in pt_reflexive.tags[se_reflexive]
    assert LexicalTag.CONDITIONAL in pt_conditional.tags[se_conditional]


def test_token_source_offsets_survive_diacritic_normalization() -> None:
    text = "Sí, el débito no es mío."
    tokens = tokenize_with_source(text)

    for token in tokens:
        assert text[token.start : token.end] == token.surface

    si = next(token for token in tokens if token.normalized == "si")
    debito = next(token for token in tokens if token.normalized == "debito")
    mio = next(token for token in tokens if token.normalized == "mio")
    assert si.had_acute is True
    assert debito.had_acute is True
    assert mio.had_acute is True




def test_spanish_mi_and_mi_accent_roles_remain_distinct() -> None:
    analysis = analyze_foundation("Mi tarjeta no salió de mí.", "es")
    possessor_spans = [
        item
        for item in analysis.self_evidence
        if item.role is SelfRole.POSSESSOR
    ]
    source_spans = [
        item
        for item in analysis.self_evidence
        if item.role is SelfRole.SOURCE
    ]

    assert len(possessor_spans) == 1
    assert len(source_spans) == 1


def test_portuguese_nos_subject_is_distinct_from_nos_clitic() -> None:
    subject = analyze_foundation("Nós fizemos a compra.", "pt")
    clitic = analyze_foundation("Nos cobraram duas vezes.", "pt")

    assert any(
        item.role is SelfRole.SUBJECT and not item.implicit_from_predicate
        for item in subject.self_evidence
    )
    assert not any(
        item.role is SelfRole.SUBJECT and not item.implicit_from_predicate
        for item in clitic.self_evidence
    )


def test_foundation_does_not_classify_unauthorized_activity() -> None:
    analysis = analyze_foundation("Eu não fiz essa compra.", "pt")

    assert hasattr(analysis, "tokens")
    assert hasattr(analysis, "predicates")
    assert not hasattr(analysis, "matched")
