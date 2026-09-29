from __future__ import annotations

from itertools import product

from app.unauthorized_grammar import (
    EvidenceAtomKind,
    PropositionFamily,
    analyze_foundation,
    build_positive_propositions,
)


# RF1H-G7D-P property surface.
#
# Every sentence generated in this file is DEVELOPMENT-KNOWN. None may be
# reused, paraphrased, transformed, or leaked into RF1J fresh wording,
# realistic-language-v2 held-back wording, or any held-back confirmation set.
#
# The frozen semantic baseline is the accepted G7 lineage before B2R-N:
# nested/right-of-attached-adverbial candidates must not acquire SELF atoms;
# true later referents may retain only their own SELF atom; an atom-free
# conservative drop is allowed because recall-only B2RL-02/B2RM-04 surfaces
# remain explicitly deferred and are not the pre-B3 SELF hazard.


def _fraud_atom_signatures(
    message: str,
    language: str,
) -> tuple[tuple[str | None, tuple[EvidenceAtomKind, ...]], ...]:
    analysis = analyze_foundation(message, language)
    signatures: list[tuple[str | None, tuple[EvidenceAtomKind, ...]]] = []

    for proposition in build_positive_propositions(message, language):
        if proposition.family is not PropositionFamily.FRAUD_CHARACTERIZATION:
            continue
        activity = (
            analysis.tokens[proposition.activity_token_span[0]].normalized
            if proposition.activity_token_span is not None
            else None
        )
        atoms = tuple(atom.kind for atom in proposition.counter_evidence)
        signatures.append((activity, atoms))

    return tuple(signatures)


def _assert_no_self_atom(message: str, language: str) -> None:
    for _, atoms in _fraud_atom_signatures(message, language):
        assert EvidenceAtomKind.SELF_PERFORMED not in atoms
        assert EvidenceAtomKind.SELF_AUTHORIZED not in atoms


def _assert_no_new_or_moved_self_atom(
    message: str,
    language: str,
    expected_activity: str,
    expected_atoms: tuple[EvidenceAtomKind, ...],
) -> None:
    signatures = _fraud_atom_signatures(message, language)
    atom_bearing = [
        (activity, atoms)
        for activity, atoms in signatures
        if EvidenceAtomKind.SELF_PERFORMED in atoms
        or EvidenceAtomKind.SELF_AUTHORIZED in atoms
    ]
    assert all(
        activity == expected_activity
        and atoms == expected_atoms
        for activity, atoms in atom_bearing
    )


def test_g7d_property_nested_attached_frames_never_donate_self_atoms() -> None:
    es_heads = (
        "La transferencia que salió de la cuenta",
        "La compra que apareció en el extracto",
    )
    pt_heads = (
        "A transferência que saiu da conta",
        "A compra que apareceu no extrato",
    )

    es_relative_internal = (
        "hice el pago",
        "autoricé el pago",
        "usé la tarjeta para el pago que hice",
        "hice la compra y el pago que autoricé",
    )
    pt_relative_internal = (
        "fiz o pagamento",
        "autorizei o pagamento",
        "usei o cartão para o pagamento que eu fiz",
        "fiz a compra e o pagamento que autorizei",
    )

    for head, coordinator, marker, frame in product(
        es_heads,
        ("y", "pero"),
        ("cuando", "mientras"),
        es_relative_internal,
    ):
        message = f"{head} {coordinator} {marker} {frame} volvió a aparecer fue un fraude."
        _assert_no_self_atom(message, "es")

    for head, coordinator, marker, frame in product(
        pt_heads,
        ("e", "mas", "porém"),
        ("quando", "enquanto"),
        pt_relative_internal,
    ):
        message = f"{head} {coordinator} {marker} {frame} voltou a aparecer foi golpe."
        _assert_no_self_atom(message, "pt")

    es_frame_subjects = (
        "el pago que hice salió",
        "el pago que autoricé salió",
        "la compra que hice apareció",
    )
    pt_frame_subjects = (
        "o pagamento que eu fiz saiu",
        "o pagamento que eu autorizei saiu",
        "a compra que eu fiz apareceu",
    )

    for head, marker, frame in product(
        es_heads,
        ("cuando", "mientras"),
        es_frame_subjects,
    ):
        _assert_no_self_atom(f"{head} {marker} {frame} fue un fraude.", "es")

    for head, marker, frame in product(
        pt_heads,
        ("quando", "enquanto"),
        pt_frame_subjects,
    ):
        _assert_no_self_atom(f"{head} {marker} {frame} foi golpe.", "pt")

    es_distant_frames = (
        "yo por fin después de todo hice el pago",
        "yo mismo ya por la tarde de ayer autoricé el pago",
        "por fin y después de mucho esperar hice el pago",
    )
    pt_distant_frames = (
        "eu enfim depois de muito tempo fiz o pagamento",
        "eu mesmo já na tarde de ontem autorizei o pagamento",
    )

    for head, marker, frame in product(
        es_heads,
        ("cuando", "mientras"),
        es_distant_frames,
    ):
        _assert_no_self_atom(f"{head} {marker} {frame} fue un fraude.", "es")

    for head, marker, frame in product(
        pt_heads,
        ("quando", "enquanto"),
        pt_distant_frames,
    ):
        _assert_no_self_atom(f"{head} {marker} {frame} foi golpe.", "pt")


def test_g7d_property_true_later_referent_keeps_only_its_own_self_atom() -> None:
    es_first_conjuncts = (
        "La compra que hice está bien",
        "El pago que hice salió bien",
    )
    pt_first_conjuncts = (
        "A compra que eu fiz está certa",
        "O pagamento que eu fiz saiu certo",
    )

    es_frames = (
        (
            "cuando usé la tarjeta la transferencia que hice",
            "transferencia",
            (EvidenceAtomKind.SELF_PERFORMED,),
        ),
        (
            "mientras revisé la cuenta la transferencia que autoricé",
            "transferencia",
            (EvidenceAtomKind.SELF_AUTHORIZED,),
        ),
        (
            "cuando yo por fin después de todo hice la transferencia que autoricé",
            "transferencia",
            (
                EvidenceAtomKind.SELF_PERFORMED,
                EvidenceAtomKind.SELF_AUTHORIZED,
            ),
        ),
    )
    pt_frames = (
        (
            "quando usei o cartão a transferência que eu fiz",
            "transferencia",
            (EvidenceAtomKind.SELF_PERFORMED,),
        ),
        (
            "enquanto revisei a conta a transferência que eu autorizei",
            "transferencia",
            (EvidenceAtomKind.SELF_AUTHORIZED,),
        ),
        (
            "quando eu enfim depois de muito tempo fiz a transferência que autorizei",
            "transferencia",
            (
                EvidenceAtomKind.SELF_PERFORMED,
                EvidenceAtomKind.SELF_AUTHORIZED,
            ),
        ),
    )

    for first, coordinator, frame in product(
        es_first_conjuncts,
        ("y", "pero"),
        es_frames,
    ):
        frame_text, expected_activity, expected_atoms = frame
        message = f"{first} {coordinator} {frame_text} fue un fraude."
        _assert_no_new_or_moved_self_atom(
            message,
            "es",
            expected_activity,
            expected_atoms,
        )

    for first, coordinator, frame in product(
        pt_first_conjuncts,
        ("e", "mas"),
        pt_frames,
    ):
        frame_text, expected_activity, expected_atoms = frame
        message = f"{first} {coordinator} {frame_text} foi golpe."
        _assert_no_new_or_moved_self_atom(
            message,
            "pt",
            expected_activity,
            expected_atoms,
        )


def test_g7d_property_fronted_frames_do_not_donate_self_atoms() -> None:
    cases = (
        (
            "Cuando hice el pago la transferencia fue un fraude.",
            "es",
            "transferencia",
        ),
        (
            "Cuando yo por fin después de todo hice el pago la transferencia fue un fraude.",
            "es",
            "transferencia",
        ),
        (
            "Quando eu fiz o pagamento a transferência foi golpe.",
            "pt",
            "transferencia",
        ),
        (
            "Quando eu enfim depois de muito tempo fiz o pagamento a transferência foi golpe.",
            "pt",
            "transferencia",
        ),
    )

    for message, language, expected_activity in cases:
        signatures = _fraud_atom_signatures(message, language)
        assert signatures == ((expected_activity, ()),)
