from __future__ import annotations

import json
from collections import Counter
from itertools import product
from pathlib import Path
from typing import Iterable

import pytest

from app.unauthorized_grammar import (
    EvidenceAtomKind,
    PropositionFamily,
    analyze_foundation,
    build_positive_propositions,
)


# RF1H-B2 final structural property gate.
#
# Every message, template, slot value, generated row and serialized baseline
# entry in this file is DEVELOPMENT-KNOWN. None may be reused, paraphrased,
# transformed, translated, pattern-preserved, or leaked into RF1J fresh
# wording, realistic-language-v2 held-back wording, or any held-back set.
#
# Referent identity is source-position based. Normalized activity nouns are
# intentionally never used to decide whether a SELF atom belongs to the true
# P6 referent.

_SELF_KINDS = {
    EvidenceAtomKind.SELF_PERFORMED,
    EvidenceAtomKind.SELF_AUTHORIZED,
}
_BASELINE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "rf1h_g7f_pre_g7f_self_baseline.json"
)
_B2RQ_BASELINE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "rf1h_b2rq_pre_repair_self_baseline.json"
)

_RETAIN_EXACT = "retain_exact"
_REMOVE_STRICT = "remove_strict"
_PRESERVE_NONE = "preserve_none"


def _render_marked(template: str) -> tuple[str, int]:
    assert template.count("[[") == 1
    assert template.count("]]") == 1
    source_start = template.index("[[")
    message = template.replace("[[", "", 1).replace("]]", "", 1)
    return message, source_start


def _self_atom_signatures(
    message: str,
    language: str,
) -> frozenset[tuple[int, str]]:
    analysis = analyze_foundation(message, language)
    signatures: set[tuple[int, str]] = set()

    for proposition in build_positive_propositions(message, language):
        if proposition.family is not PropositionFamily.FRAUD_CHARACTERIZATION:
            continue
        for atom in proposition.counter_evidence:
            if atom.kind not in _SELF_KINDS:
                continue
            signatures.add(
                (
                    analysis.tokens[atom.activity_token_span[0]].start,
                    atom.kind.value,
                )
            )

    return frozenset(signatures)


def _assert_self_atoms_only_on_true_referent(
    message: str,
    language: str,
    true_source_start: int | None,
) -> None:
    analysis = analyze_foundation(message, language)

    for proposition in build_positive_propositions(message, language):
        if proposition.family is not PropositionFamily.FRAUD_CHARACTERIZATION:
            continue

        for atom in proposition.counter_evidence:
            if atom.kind not in _SELF_KINDS:
                continue

            assert true_source_start is not None
            assert proposition.activity_token_span is not None
            proposition_source_start = analysis.tokens[
                proposition.activity_token_span[0]
            ].start
            atom_source_start = analysis.tokens[
                atom.activity_token_span[0]
            ].start

            assert proposition_source_start == true_source_start
            assert atom_source_start == true_source_start


def _assert_lineage_transition(
    prior: frozenset[tuple[int, str]],
    current: frozenset[tuple[int, str]],
    transition: str,
) -> None:
    if transition == _RETAIN_EXACT:
        assert prior
        assert current == prior
        return

    if transition == _REMOVE_STRICT:
        assert prior
        assert current < prior
        return

    if transition == _PRESERVE_NONE:
        assert not prior
        assert not current
        return

    raise AssertionError(f"unknown lineage transition: {transition}")


def _attached_frame_cases() -> Iterable[tuple[str, str, int]]:
    es_heads = (
        "La [[transferencia]] que salió de la cuenta",
        "La [[transferencia]] de ayer",
        "La [[transferencia]] que apareció en el extracto",
    )
    pt_heads = (
        "A [[transferência]] que saiu da conta",
        "A [[transferência]] de ontem",
        "A [[transferência]] que apareceu no extrato",
    )
    es_links = ("", ",", " y", " pero", " y luego", " y volvió a aparecer")
    pt_links = (
        "",
        ",",
        " e",
        " mas",
        " porém",
        " porem",
        " e depois",
        " e voltou a aparecer",
    )
    es_markers = ("cuando", "mientras")
    pt_markers = ("quando", "enquanto")
    es_frames = (
        "hice el pago",
        "autoricé el pago",
        "usé la tarjeta para el pago que hice",
        "el pago que hice salió",
        "el pago que autoricé salió",
        "el pago yo mismo lo autoricé",
        "yo por fin después de todo hice el pago",
        "yo por fin después de todo usé la tarjeta para el pago que hice",
    )
    pt_frames = (
        "fiz o pagamento",
        "autorizei o pagamento",
        "usei o cartão para o pagamento que eu fiz",
        "o pagamento que eu fiz saiu",
        "o pagamento que eu autorizei saiu",
        "o pagamento eu mesmo o autorizei",
        "eu enfim depois de muito tempo fiz o pagamento",
        "eu enfim depois de muito tempo usei o cartão para o pagamento que eu fiz",
    )

    for head, link, marker, frame in product(
        es_heads,
        es_links,
        es_markers,
        es_frames,
    ):
        message, start = _render_marked(
            f"{head}{link} {marker} {frame} voltou a aparecer".replace(
                "voltou a aparecer", "volvió a aparecer"
            )
            + " fue un fraude."
        )
        yield message, "es", start

    for head, link, marker, frame in product(
        pt_heads,
        pt_links,
        pt_markers,
        pt_frames,
    ):
        message, start = _render_marked(
            f"{head}{link} {marker} {frame} voltou a aparecer foi golpe."
        )
        yield message, "pt", start

    explicit = (
        (
            "A [[transferência]] que e cobrada quando o pagamento que eu fiz saiu foi golpe.",
            "pt",
        ),
        (
            "La [[transferencia]], cuando el pago que hice salió, fue un fraude.",
            "es",
        ),
        (
            "La [[transferencia]] cuando el pago yo mismo lo autoricé fue un fraude.",
            "es",
        ),
        (
            "A [[transferência]], quando o pagamento que eu fiz saiu, foi golpe.",
            "pt",
        ),
    )
    for template, language in explicit:
        message, start = _render_marked(template)
        yield message, language, start


def _grid_q_cases() -> Iterable[tuple[str, str, int]]:
    es_subjects = (
        "La compra que hice está bien",
        "El pago que yo mismo autoricé salió bien",
    )
    pt_subjects = (
        "A compra que eu fiz está certa",
        "O pagamento que eu mesmo autorizei saiu certo",
    )
    es_connectors = (" y ", " pero ", ", ", " ")
    pt_connectors = (" e ", " mas ", ", ", " ")
    es_targets = ("la [[transferencia]]", "la [[compra]]")
    pt_targets = ("a [[transferência]]", "a [[compra]]")

    for subject, connector, target in product(
        es_subjects,
        es_connectors,
        es_targets,
    ):
        message, start = _render_marked(
            f"{subject}{connector}{target} fue un fraude."
        )
        yield message, "es", start

    for subject, connector, target in product(
        pt_subjects,
        pt_connectors,
        pt_targets,
    ):
        message, start = _render_marked(
            f"{subject}{connector}{target} foi golpe."
        )
        yield message, "pt", start

    es_fronts = (
        "Cuando",
        "Mientras",
        "Aunque",
        "Si",
        "Después de que",
    )
    pt_fronts = (
        "Quando",
        "Enquanto",
        "Embora",
        "Se",
        "Depois que",
    )
    es_subject_frames = (
        "el pago que hice salió",
        "la compra que autoricé apareció",
    )
    pt_subject_frames = (
        "o pagamento que eu fiz saiu",
        "a compra que eu autorizei apareceu",
    )

    for front, subject, comma in product(
        es_fronts,
        es_subject_frames,
        ("", ","),
    ):
        message, start = _render_marked(
            f"{front} {subject}{comma} la [[transferencia]] fue un fraude."
        )
        yield message, "es", start

    for front, subject, comma in product(
        pt_fronts,
        pt_subject_frames,
        ("", ","),
    ):
        message, start = _render_marked(
            f"{front} {subject}{comma} a [[transferência]] foi golpe."
        )
        yield message, "pt", start


def _true_later_self_cases() -> Iterable[tuple[str, str, int]]:
    es_first = (
        "La compra que hice está bien",
        "El pago que autoricé salió bien",
    )
    pt_first = (
        "A compra que eu fiz está certa",
        "O pagamento que eu autorizei saiu certo",
    )
    es_frames = (
        "cuando usé la tarjeta la [[transferencia]] que hice",
        "mientras revisé la cuenta la [[transferencia]] que autoricé",
        "cuando yo por fin después de todo hice la [[transferencia]] que autoricé",
    )
    pt_frames = (
        "quando usei o cartão a [[transferência]] que eu fiz",
        "enquanto revisei a conta a [[transferência]] que eu autorizei",
        "quando eu enfim depois de muito tempo fiz a [[transferência]] que autorizei",
    )

    for first, coordinator, frame in product(
        es_first,
        ("y", "pero"),
        es_frames,
    ):
        message, start = _render_marked(
            f"{first} {coordinator} {frame} fue un fraude."
        )
        yield message, "es", start

    for first, coordinator, frame in product(
        pt_first,
        ("e", "mas"),
        pt_frames,
    ):
        message, start = _render_marked(
            f"{first} {coordinator} {frame} foi golpe."
        )
        yield message, "pt", start


def _ordinary_and_same_noun_cases() -> Iterable[tuple[str, str, int]]:
    templates = (
        ("La [[transferencia]] que hice fue un fraude.", "es"),
        ("El [[pago]] que yo mismo autoricé fue un fraude.", "es"),
        ("O [[Pix]] que eu fiz foi golpe.", "pt"),
        (
            "La transferencia que hice está bien y la [[transferencia]] fue un fraude.",
            "es",
        ),
        (
            "O pagamento que eu fiz saiu bem mas o [[pagamento]] foi golpe.",
            "pt",
        ),
        (
            "Cuando el pago que hice salió, la [[transferencia]] fue un fraude.",
            "es",
        ),
        (
            "Quando o pagamento que eu fiz saiu, a [[transferência]] foi golpe.",
            "pt",
        ),
    )
    for template, language in templates:
        message, start = _render_marked(template)
        yield message, language, start


def _b2ro_residual_cases() -> Iterable[tuple[str, str, int | None]]:
    no_activity_true_referent = (
        (
            "Lo que me cobraron cuando hice el pago fue un fraude.",
            "es",
        ),
        (
            "O que me cobraram quando fiz o pagamento foi golpe.",
            "pt",
        ),
    )
    for message, language in no_activity_true_referent:
        yield message, language, None

    marked = (
        (
            "La [[transferencia]], aunque yo hice el pago, fue un fraude.",
            "es",
        ),
        (
            "La [[transferencia]] de ayer, porque hice el pago, fue un fraude.",
            "es",
        ),
        (
            "El [[cargo]] de ayer, después de que hice la compra, fue un fraude.",
            "es",
        ),
        (
            "A [[transferência]], porque eu fiz o pagamento, foi golpe.",
            "pt",
        ),
        (
            "A [[cobrança]] de ontem, depois que eu fiz a compra, foi golpe.",
            "pt",
        ),
        (
            "La [[transferencia]] que salió por el pago que hice fue un fraude.",
            "es",
        ),
        (
            "El [[cargo]] de la compra que hice fue un fraude.",
            "es",
        ),
        (
            "A [[cobrança]] para a compra que eu fiz foi golpe.",
            "pt",
        ),
        (
            "La [[transferencia]] que salió por la transferencia que hice fue un fraude.",
            "es",
        ),
        (
            "A [[transferência]] que apareceu com a transferência que eu fiz foi golpe.",
            "pt",
        ),
    )
    for template, language in marked:
        message, start = _render_marked(template)
        yield message, language, start


def _b2rp_structural_cases() -> Iterable[tuple[str, str, int]]:
    direct_relative = (
        (
            "El [[débito]] que reemplazó el retiro que yo realicé fue un fraude.",
            "es",
        ),
        (
            "El [[retiro]] que duplicó el retiro que yo realicé fue un fraude.",
            "es",
        ),
        (
            "O [[lançamento]] que substituiu o gasto que eu realizei foi golpe.",
            "pt",
        ),
        (
            "O [[gasto]] que duplicou o gasto que eu realizei foi golpe.",
            "pt",
        ),
    )
    for template, language in direct_relative:
        message, start = _render_marked(template)
        yield message, language, start

    for preposition, determiner in product(
        ("de", "con", "desde", "durante", "sin"),
        ("ese", "mi", "aquel"),
    ):
        message, start = _render_marked(
            f"El [[cargo]] {preposition} {determiner} retiro que hice ayer fue un fraude."
        )
        yield message, "es", start

    for preposition, determiner in product(
        ("de", "com", "desde", "durante", "sem"),
        ("este", "meu", "aquele"),
    ):
        message, start = _render_marked(
            f"O [[lançamento]] {preposition} {determiner} gasto que realizei ontem foi golpe."
        )
        yield message, "pt", start

    temporal = (
        (
            "El [[débito]] en cuanto yo realicé el retiro fue un fraude.",
            "es",
        ),
        (
            "La [[operación]] tan pronto como hice la transferencia fue fraudulenta.",
            "es",
        ),
    )
    for template, language in temporal:
        message, start = _render_marked(template)
        yield message, language, start


def _b2rq_structural_cases() -> Iterable[tuple[str, str, int]]:
    es_nested_pp = (
        ("aviso", "sobre", "pago", "autoricé"),
        ("membresía", "por", "transferencia", "hice"),
        ("recibo", "para", "retiro", "realicé"),
    )
    for head, preposition, activity, predicate in es_nested_pp:
        message, start = _render_marked(
            f"El [[{head}]] {preposition} el {activity} que {predicate} fue un fraude."
        )
        yield message, "es", start

    pt_nested_pp = (
        ("aviso", "sobre", "pagamento", "autorizei"),
        ("mensalidade", "para", "compra", "fiz"),
        ("recibo", "com", "saque", "realizei"),
    )
    for head, preposition, activity, predicate in pt_nested_pp:
        message, start = _render_marked(
            f"O [[{head}]] {preposition} o {activity} que eu {predicate} foi golpe."
        )
        yield message, "pt", start

    relative_cases = (
        (
            "El [[débito]] reciente que acompañó el pago que hice fue un fraude.",
            "es",
        ),
        (
            "El [[cargo]] de hoy que acompañó la compra que hice fue un fraude.",
            "es",
        ),
        (
            "El [[cobro]], que acompañó el retiro que realicé, fue un fraude.",
            "es",
        ),
        (
            "A [[cobrança]], que acompanhou o pix que eu fiz, foi golpe.",
            "pt",
        ),
        (
            "O [[débito]] o qual acompanhou o pagamento que eu fiz foi golpe.",
            "pt",
        ),
        (
            "O [[saque]] de hoje que acompanhou a compra que eu fiz foi golpe.",
            "pt",
        ),
        (
            "El [[cargo]] que apareció hoy y acompañó el pago que hice fue un fraude.",
            "es",
        ),
        (
            "O [[débito]] que apareceu hoje e acompanhou a compra que eu fiz foi golpe.",
            "pt",
        ),
    )
    for template, language in relative_cases:
        message, start = _render_marked(template)
        yield message, language, start

    pt_nested_forms = (
        "O [[débito]] com o meu pagamento que eu fiz foi golpe.",
        "A [[cobrança]] sobre a minha compra que eu fiz foi golpe.",
        "A [[cobrança]] pelo meu pix que eu autorizei foi golpe.",
        "O [[saque]] numa compra que eu fiz foi golpe.",
        "A [[cobrança]] àquela compra que eu fiz foi golpe.",
        "O [[débito]] com a nossa compra que eu fiz foi golpe.",
    )
    for template in pt_nested_forms:
        message, start = _render_marked(template)
        yield message, "pt", start


def _b2rr_structural_cases() -> Iterable[tuple[str, str, int]]:
    cases = (
        (
            "El [[formulario]] solicitando validar el retiro que realicé ayer fue un fraude.",
            "es",
        ),
        (
            "El [[recargo]] destinado a revisar el pago que autoricé ayer fue fraudulento.",
            "es",
        ),
        (
            "La [[alerta]] usada para verificar la transferencia que hice fue fraude.",
            "es",
        ),
        (
            "A [[tarifa]] exigida para processar a transferência que eu autorizei ontem foi golpe.",
            "pt",
        ),
        (
            "O [[comunicado]] pedindo verificar o pagamento que eu fiz ontem foi uma fraude.",
            "pt",
        ),
        (
            "A [[taxa]] criada para revisar o Pix que eu fiz foi golpe.",
            "pt",
        ),
    )
    for template, language in cases:
        message, start = _render_marked(template)
        yield message, language, start


def _b2rs_positive_license_challenge_cases() -> Iterable[tuple[str, str, int]]:
    cases = (
        (
            "Los 68 pesos agregados junto al retiro que hice fueron un fraude.",
            "es",
        ),
        (
            "Aquello que cargaron encima del pago que autoricé es fraude.",
            "es",
        ),
        (
            "El recargo ubicado entre la cuota mensual y la transferencia que hice es fraude.",
            "es",
        ),
        (
            "Me aplicaron un débito doble junto a la compra que hice y eso es fraude.",
            "es",
        ),
        (
            "R$ 47,50 lançados ao lado do Pix que eu fiz são golpe.",
            "pt",
        ),
        (
            "Aquilo que cobraram acima do pagamento que eu autorizei é fraude.",
            "pt",
        ),
        (
            "A tarifa posicionada entre a mensalidade e a compra que eu fiz é golpe.",
            "pt",
        ),
        (
            "Debitaram uma taxa extra junto do Pix que eu fiz e isso é golpe.",
            "pt",
        ),
    )
    for template, language in cases:
        message, start = _render_marked(template)
        yield message, language, start


def _retention_cases() -> Iterable[tuple[str, str, int, str]]:
    cases = (
        (
            "La [[transferencia]] que hice fue un fraude.",
            "es",
            "ordinary_relative",
        ),
        (
            "El [[pago]] que yo mismo autoricé fue un fraude.",
            "es",
            "ordinary_relative",
        ),
        (
            "O [[Pix]] que eu fiz foi golpe.",
            "pt",
            "ordinary_relative",
        ),
        (
            "A [[transferência]] que eu autorizei foi golpe.",
            "pt",
            "ordinary_relative",
        ),
        (
            "Cuando hice el [[pago]] fue un fraude.",
            "es",
            "clause_initial_subjectless",
        ),
        (
            "Quando eu fiz o [[pagamento]] foi golpe.",
            "pt",
            "clause_initial_subjectless",
        ),
        (
            "Me avisaron que la [[compra]] que hice fue un fraude.",
            "es",
            "complementizer_que",
        ),
        (
            "Me avisaram que a [[compra]] que eu fiz foi golpe.",
            "pt",
            "complementizer_que",
        ),
        (
            "Respecto a la [[compra]] que hice ayer, fue un fraude.",
            "es",
            "topicalized_pp",
        ),
        (
            "Quanto a esse [[saque]] que eu fiz, foi golpe.",
            "pt",
            "topicalized_pp",
        ),
        (
            "Revisé la compra y el [[pago]] que hice fue un fraude.",
            "es",
            "two_activity_true_later",
        ),
        (
            "Revisei a compra e o [[pagamento]] que fiz foi golpe.",
            "pt",
            "two_activity_true_later",
        ),
        (
            "El cargo que llegó ayer y el [[pago]] que hice fue un fraude.",
            "es",
            "relative_nominal_conjunct",
        ),
        (
            "O débito que chegou ontem e o [[pagamento]] que eu fiz foi golpe.",
            "pt",
            "relative_nominal_conjunct",
        ),
        (
            "La alerta y el [[pago]] que autoricé fue un fraude.",
            "es",
            "prior_nominal_conjunct",
        ),
        (
            "O aviso e a [[transferência]] que eu fiz foi golpe.",
            "pt",
            "prior_nominal_conjunct",
        ),
        (
            "Yo mismo hice este [[pago]] y fue un fraude.",
            "es",
            "direct_self_object",
        ),
        (
            "Eu mesma fiz este [[Pix]] e foi golpe.",
            "pt",
            "direct_self_object",
        ),
    )
    for template, language, class_id in cases:
        message, start = _render_marked(template)
        yield message, language, start, class_id


def _structural_cases() -> tuple[tuple[str, str, int | None], ...]:
    cases = (
        list(_attached_frame_cases())
        + list(_grid_q_cases())
        + list(_true_later_self_cases())
        + list(_ordinary_and_same_noun_cases())
        + list(_b2ro_residual_cases())
        + list(_b2rp_structural_cases())
        + list(_b2rq_structural_cases())
        + list(_b2rr_structural_cases())
        + list(_b2rs_positive_license_challenge_cases())
    )
    return tuple(dict.fromkeys(cases))


def test_g7f_property_no_wrong_referent_self_atom_by_source_position() -> None:
    cases = _structural_cases()
    assert len(cases) >= 700

    for message, language, true_source_start in cases:
        _assert_self_atoms_only_on_true_referent(
            message,
            language,
            true_source_start,
        )


def test_g7f_property_legitimate_self_retention_has_per_class_minimums() -> None:
    retained = Counter()

    for message, language, true_source_start, class_id in _retention_cases():
        _assert_self_atoms_only_on_true_referent(
            message,
            language,
            true_source_start,
        )
        signatures = _self_atom_signatures(message, language)
        on_true_referent = {
            signature
            for signature in signatures
            if signature[0] == true_source_start
        }
        assert on_true_referent
        retained[class_id] += len(on_true_referent)

    assert retained["ordinary_relative"] >= 4
    assert retained["clause_initial_subjectless"] >= 2
    assert retained["complementizer_que"] >= 2
    assert retained["topicalized_pp"] >= 2
    assert retained["two_activity_true_later"] >= 2
    assert retained["relative_nominal_conjunct"] >= 2
    assert retained["prior_nominal_conjunct"] >= 2
    assert retained["direct_self_object"] >= 2


def test_g7f_property_frozen_pre_g7f_lineage_distinguishes_retention_and_removal() -> None:
    baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))

    assert baseline["schema"] == "rf1h-g7f-pre-g7f-self-baseline-v1"
    assert (
        baseline["frozen_public_sha"]
        == "8e21f3ad69b75857db2c431e8b4f7625def86632"
    )
    assert baseline["classification"] == "DEVELOPMENT-KNOWN"
    assert len(baseline["cases"]) >= 16

    transitions = Counter()
    for case in baseline["cases"]:
        prior = frozenset(
            (
                atom["activity_source_start"],
                atom["kind"],
            )
            for atom in case["self_atoms"]
        )
        current = _self_atom_signatures(
            case["message"],
            case["language"],
        )
        transition = case["transition"]
        _assert_lineage_transition(prior, current, transition)
        transitions[transition] += 1

    assert transitions[_RETAIN_EXACT] >= 7
    assert transitions[_REMOVE_STRICT] >= 7
    assert transitions[_PRESERVE_NONE] >= 2


def test_b2rq_property_frozen_pre_repair_lineage_pins_exit_repair() -> None:
    baseline = json.loads(_B2RQ_BASELINE_PATH.read_text(encoding="utf-8"))

    assert baseline["schema"] == "rf1h-b2rq-pre-repair-self-baseline-v1"
    assert (
        baseline["frozen_public_sha"]
        == "e2d99180ef9ed982ce8e68cc1210b4f692129b80"
    )
    assert baseline["classification"] == "DEVELOPMENT-KNOWN"
    assert len(baseline["cases"]) >= 12

    transitions = Counter()
    for case in baseline["cases"]:
        prior = frozenset(
            (
                atom["activity_source_start"],
                atom["kind"],
            )
            for atom in case["self_atoms"]
        )
        current = _self_atom_signatures(
            case["message"],
            case["language"],
        )
        transition = case["transition"]
        _assert_lineage_transition(prior, current, transition)
        transitions[transition] += 1

    assert transitions[_RETAIN_EXACT] >= 4
    assert transitions[_REMOVE_STRICT] >= 6
    assert transitions[_PRESERVE_NONE] >= 2


def test_g7f_property_lineage_rejects_new_moved_kind_changed_and_oversuppressed_atoms() -> None:
    prior = frozenset({(10, "self_performed")})

    with pytest.raises(AssertionError):
        _assert_lineage_transition(
            prior,
            frozenset({(10, "self_performed"), (20, "self_performed")}),
            _RETAIN_EXACT,
        )

    with pytest.raises(AssertionError):
        _assert_lineage_transition(
            prior,
            frozenset({(11, "self_performed")}),
            _RETAIN_EXACT,
        )

    with pytest.raises(AssertionError):
        _assert_lineage_transition(
            prior,
            frozenset({(10, "self_authorized")}),
            _RETAIN_EXACT,
        )

    with pytest.raises(AssertionError):
        _assert_lineage_transition(
            prior,
            frozenset(),
            _RETAIN_EXACT,
        )

    with pytest.raises(AssertionError):
        _assert_lineage_transition(
            prior,
            prior,
            _REMOVE_STRICT,
        )


def test_b2_final_property_b2ro06_recall_control_has_no_wrong_referent() -> None:
    cases = (
        (
            "La [[transferencia]] que hice para el pago del alquiler fue un fraude.",
            "es",
        ),
        (
            "A [[transferência]] que eu fiz para o pagamento do aluguel foi golpe.",
            "pt",
        ),
    )
    for template, language in cases:
        message, true_source_start = _render_marked(template)
        _assert_self_atoms_only_on_true_referent(
            message,
            language,
            true_source_start,
        )


def test_b2_final_property_structural_gap_classes_use_source_position_identity() -> None:
    cases = tuple(_b2rp_structural_cases())
    assert len(cases) >= 36

    for message, language, true_source_start in cases:
        _assert_self_atoms_only_on_true_referent(
            message,
            language,
            true_source_start,
        )


def test_b2rs_property_positive_license_fails_closed_on_unlicensed_shapes() -> None:
    cases = tuple(_b2rs_positive_license_challenge_cases())
    assert len(cases) >= 8

    for message, language, true_source_start in cases:
        _assert_self_atoms_only_on_true_referent(
            message,
            language,
            true_source_start,
        )


def test_b2rr_property_prior_nominal_guard_uses_source_position_identity() -> None:
    cases = tuple(_b2rr_structural_cases())
    assert len(cases) >= 6

    for message, language, true_source_start in cases:
        _assert_self_atoms_only_on_true_referent(
            message,
            language,
            true_source_start,
        )


def test_b2_final_property_two_activity_retention_pins_referent_position() -> None:
    cases = tuple(
        case
        for case in _retention_cases()
        if case[3] == "two_activity_true_later"
    )
    assert len(cases) == 2

    for message, language, true_source_start, _ in cases:
        signatures = _self_atom_signatures(message, language)
        assert signatures
        assert {source_start for source_start, _ in signatures} == {
            true_source_start
        }

def test_g7f_property_surface_covers_required_structural_classes() -> None:
    cases = _structural_cases()
    messages = tuple(message for message, _, _ in cases)

    assert any(" yo mismo lo autoricé " in message for message in messages)
    assert any(" eu mesmo o autorizei " in message for message in messages)
    assert any(" que e cobrada " in message for message in messages)
    assert any(" y luego cuando " in message for message in messages)
    assert any(" e depois quando " in message for message in messages)
    assert any(" por fin después de todo " in message for message in messages)
    assert any(" enfim depois de muito tempo " in message for message in messages)
    assert any(message.startswith("Cuando ") for message in messages)
    assert any(message.startswith("Embora ") for message in messages)
    assert any("aunque yo hice el pago" in message for message in messages)
    assert any("porque eu fiz o pagamento" in message for message in messages)
    assert any("después de que hice la compra" in message for message in messages)
    assert any("de la compra que hice" in message for message in messages)
    assert any("para a compra que eu fiz" in message for message in messages)
    assert any("de ese retiro que hice" in message for message in messages)
    assert any("com meu gasto que realizei" in message for message in messages)
    assert any("desde mi retiro que hice" in message for message in messages)
    assert any("que reemplazó el retiro que yo realicé" in message for message in messages)
    assert any("que substituiu o gasto que eu realizei" in message for message in messages)
    assert any("en cuanto yo realicé el retiro" in message for message in messages)
    assert any("tan pronto como hice la transferencia" in message for message in messages)
    assert any("membresía" in message for message in messages)
    assert any("o meu pagamento" in message for message in messages)
    assert any("pelo meu pix" in message for message in messages)
    assert any("o qual acompanhou" in message for message in messages)
    assert any("que apareció hoy y acompañó" in message for message in messages)
    assert any("solicitando validar el retiro" in message for message in messages)
    assert any("destinado a revisar el pago" in message for message in messages)
    assert any("exigida para processar a transferência" in message for message in messages)
    assert any("pedindo verificar o pagamento" in message for message in messages)
    assert any(
        message.count("transferencia") >= 2
        for message, language, _ in cases
        if language == "es"
    )
    assert any(
        message.count("transferência") >= 2
        for message, language, _ in cases
        if language == "pt"
    )
