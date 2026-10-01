from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import app.unauthorized_signals as unauthorized_signals
from app.bootstrap import build_app_context
from app.demo_data import DEMO_PERSONAS
from app.denial_safety import (
    denial_safety_assertion,
    denial_safety_findings,
    structural_assertion_demotion,
)
from app.language_scope import unsupported_language_dominant
from app.main import create_app
from app.settings import Settings
from app.unauthorized_grammar import PropositionMode, resolve_positive_propositions


# RF1Q repair families. Wording is family-level development material written for
# these tests, not RF1P fresh-probe text, so RF1P stays clean evidence of what
# was repaired.
_FAMILY_POSITIVES = [
    # 1. a product opened in the customer's name (identity misuse)
    ("identity_misuse", "Desconocidos sacaron un préstamo a mi nombre el mes pasado."),
    ("identity_misuse", "Alguien solicitó una cuenta de ahorros con mis datos."),
    ("identity_misuse", "Me enteré de que abrieron una tarjeta a mi nombre sin mi autorización."),
    ("identity_misuse", "Se emitió un crédito a mi nombre sin que yo lo pidiera."),
    ("identity_misuse", "Alguém abriu um cartão no meu nome pelo aplicativo."),
    ("identity_misuse", "Golpistas contrataram um empréstimo com meus dados."),
    ("identity_misuse", "Fizeram uma conta em meu nome sem a minha autorização."),
    # 2. denial of having opened or requested an existing product
    ("product_origination_denial", "Me llegó una tarjeta de crédito que yo nunca pedí."),
    ("product_origination_denial", "Hay un préstamo activo en mi perfil. Nunca lo solicité."),
    ("product_origination_denial", "Yo no tramité esa cuenta corriente."),
    ("product_origination_denial", "Aparece una chequera nueva; yo no la pedí."),
    ("product_origination_denial", "Chegou um cartão adicional que eu não solicitei."),
    ("product_origination_denial", "Tem um empréstimo no meu cadastro. Eu nunca pedi."),
    ("product_origination_denial", "Nunca contratei esse financiamento."),
    # 3. a product shown in the customer's records that is not theirs
    ("product_disownment", "La cuenta de ahorros que aparece en mi perfil no es mía."),
    ("product_disownment", "Una tarjeta que figura en mi app no me pertenece."),
    ("product_disownment", "O cartão que consta no aplicativo não é meu."),
    ("product_disownment", "A conta poupança que aparece no app não me pertence."),
    # 4. a relative's denial relayed through their own words
    ("relayed_denial", "Mi mamá me dijo que ella no reconoce dos compras de su tarjeta."),
    ("relayed_denial", "Mis padres aseguran que nunca hicieron esas transferencias."),
    ("relayed_denial", "Minha mãe disse que não reconhece um débito na conta dela."),
    ("relayed_denial", "Meu namorado jura que não fez aquele Pix."),
]

# Near misses for the RF1Q families: requests, plans, permission, questions,
# hypotheticals, hedges, not-yet, self-performed or relative-attributed items,
# bare possession statements, corrections, and activity that did not happen.
_FAMILY_NEGATIVES = [
    "Quiero abrir una cuenta a mi nombre.",
    "Me abrieron una cuenta a mi nombre en la sucursal, ¿cuándo llega la tarjeta?",
    "Mi esposo abrió una cuenta a mi nombre con mi permiso.",
    "¿Puede alguien abrir una tarjeta a mi nombre sin mi autorización?",
    "Abrí una cuenta a mi nombre ayer.",
    "Alguém pode abrir um cartão no meu nome?",
    "Quero tirar um cartão no meu nome.",
    "Tal vez alguien abrió una cuenta a mi nombre, no sé.",
    "Todavía no la pedí, ¿cómo solicito la tarjeta?",
    "Yo no la activé todavía.",
    "Nunca abrí una cuenta en otro banco.",
    "Eu nunca abri conta em outro banco.",
    "Ainda não pedi o cartão.",
    "Ainda não solicitei, pode me ajudar a pedir o cartão?",
    "No la pedí yo, la pidió mi esposa para mí.",
    "Meu marido pediu o cartão adicional; eu não pedi.",
    "Esse cartão não é meu.",
    "Esta cuenta no es mía, es de mi esposo.",
    "La tarjeta que aparece en mi app no es mía, es la de mi hija.",
    "La cuenta que tengo en mi perfil no es mía sino de la empresa.",
    "¿La tarjeta que aparece en mi perfil no es mía?",
    "Mi mamá dice que no hizo el pago de la luz.",
    "Mi hija dice que no reconoce el cargo, pero fue ella.",
    "Mi esposo me dice que no hizo esa compra, pero la hice yo.",
    "Mis papás dicen que no hicieron compras este mes.",
    "Nunca pedí, ¿cómo solicito una tarjeta?",
]

# Hypothetical / advice-only questions: no incident is asserted.
_HYPOTHETICALS = [
    "¿Qué hago si alguna vez aparece un retiro que no reconozco?",
    "O que devo fazer caso apareça uma compra que eu não reconheço?",
    "Supongamos que hay un cargo que no reconozco, ¿cómo lo reporto?",
    "¿Qué haría si algún día me aparece un cobro que no hice?",
    "Si alguien sacara un préstamo a mi nombre, ¿qué hago?",
    "Si la cuenta que aparece en mi perfil no es mía, ¿qué hago?",
    "Como devo proceder se um dia surgir um Pix que eu não reconheço?",
]

# Resolved or already-recognized items: no active report.
_RESOLVED = [
    "Había un retiro que no reconocía, pero ya me lo devolvieron.",
    "No reconocí la compra al principio; después me acordé de que era el gimnasio.",
    "Não reconheci o débito no começo, mas já lembrei: era a academia.",
    "O Pix que eu não reconhecia já foi estornado.",
    "Tenía un cargo que no reconocía y ya quedó resuelto.",
    "Mi hermana me cuenta que no reconoció ese débito en un primer momento, pero luego se acordó.",
]

# Boundary pins: these stay reports.
_STILL_REPORTS = [
    # A present-tense help question about an existing item (RF1H-B5 contract).
    "¿Cómo reporto una compra que no reconozco?",
    # A present-indicative protasis is ambiguous; the resolver's assertion stands.
    "¿Qué hago si tengo un cargo que no reconozco?",
    # A recall of something else does not resolve a present denial.
    "No reconozco este cargo, pero ya me acordé de bloquear la tarjeta.",
    # A resolved earlier item does not resolve a fresh one.
    "Ya me devolvieron un cargo el mes pasado, pero hoy apareció otro que no reconozco.",
    # Remembering something to do is not recognizing the item.
    "No reconozco este cargo; después me acordé de llamar al banco.",
    # "Acknowledged that" is not recognizing the item.
    "No reconocí el cargo de ayer y ya reconocí que me robaron la tarjeta.",
    # "En ese caso noté" is a Spanish preterite, not a Portuguese "caso" protasis.
    "En ese caso noté un cargo que no reconozco.",
    # A negated resolution is not a resolution.
    "No reconozco el cargo; ya lo reporté y no lo resolvieron.",
    # A demoted hypothetical does not hide a separate fresh report.
    "¿Cómo actúo si un día noto un cargo raro? Porque hoy me apareció uno que no hice.",
]


@pytest.mark.parametrize(("family", "message"), _FAMILY_POSITIVES)
def test_rf1q_family_positives_are_unauthorized_assertions(family: str, message: str) -> None:
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is True
    assert any(
        finding.asserted and finding.family == family
        for finding in denial_safety_findings(message)
    )


@pytest.mark.parametrize("message", _FAMILY_NEGATIVES)
def test_rf1q_family_near_misses_are_not_reported(message: str) -> None:
    assert not any(finding.asserted for finding in denial_safety_findings(message))
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is False


@pytest.mark.parametrize("message", _HYPOTHETICALS)
def test_rf1q_hypothetical_advice_questions_are_not_reports(message: str) -> None:
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is False


@pytest.mark.parametrize("message", _RESOLVED)
def test_rf1q_resolved_or_recognized_items_are_not_reports(message: str) -> None:
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is False


@pytest.mark.parametrize("message", _STILL_REPORTS)
def test_rf1q_boundary_cases_stay_reports(message: str) -> None:
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is True


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        ("¿Qué hago si alguna vez aparece un retiro que no reconozco?",
         "indefinite_hypothetical_protasis"),
        ("Como devo proceder se um dia surgir um Pix que eu não reconheço?",
         "indefinite_hypothetical_protasis"),
        ("No reconocí la compra al principio; después me acordé de que era el gimnasio.",
         "recalled_after"),
        ("Había un retiro que no reconocía, pero ya me lo devolvieron.", "resolved_after"),
    ],
)
def test_rf1q_structural_demotion_names_its_shape(message: str, reason: str) -> None:
    assertive = [
        proposition
        for language in ("es", "pt")
        for proposition in resolve_positive_propositions(message, language)
        if proposition.mode == PropositionMode.ASSERTIVE.value
    ]
    assert assertive, "the structural resolver asserts this shape"
    assert {
        structural_assertion_demotion(message, p.source_start, p.source_end) for p in assertive
    } == {reason}


@pytest.mark.parametrize(
    "message",
    [
        "¿Cómo reporto una compra que no reconozco?",
        "¿Qué hago si tengo un cargo que no reconozco?",
        "No reconozco este cargo, pero ya me acordé de bloquear la tarjeta.",
        "Hay un cargo de anoche en mi tarjeta que yo no hice.",
    ],
)
def test_rf1q_structural_demotion_leaves_other_assertions_authoritative(message: str) -> None:
    assertive = [
        proposition
        for language in ("es", "pt")
        for proposition in resolve_positive_propositions(message, language)
        if proposition.mode == PropositionMode.ASSERTIVE.value
    ]
    assert assertive
    assert all(
        structural_assertion_demotion(message, p.source_start, p.source_end) is None
        for p in assertive
    )


def test_rf1q_demotion_hands_the_decision_to_the_layer_not_to_false() -> None:
    # The demoted structural assertion is not a veto: the layer still decides,
    # and a non-assertive structural mode still vetoes the layer.
    message = "Tenía un cargo que no reconocía y ya quedó resuelto."
    assert denial_safety_assertion(message, frozenset({"assertive"})) is False
    assert denial_safety_assertion(
        "Me llegó una tarjeta de crédito que yo nunca pedí.", frozenset({"hypothetical"})
    ) is False


# ---------------------------------------------------------------- English scope
@pytest.mark.parametrize(
    "message",
    [
        "Is DEMO-ES-1001 approved? I never made that payment, it wasn't me.",
        "Tell me more about DEMO-PT-2001 please.",
        "someone used my card, fix it",
        "What is my balance?",
        "This debit is not mine.",
    ],
)
def test_rf1q_english_turns_are_outside_the_declared_scope(message: str) -> None:
    assert unsupported_language_dominant(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "¿Cuál es el estado de DEMO-ES-1001?",
        "Em que situação está a transação DEMO-PT-2001?",
        "No reconozco este movimiento; that charge wasn't mine.",
        "Mi app dice status pending en la transferencia.",
        "Oi, quero ver meu saldo, thanks.",
        "Hola, el cargo de Netflix no lo hice yo.",
        "",
    ],
)
def test_rf1q_spanish_and_portuguese_turns_stay_in_scope(message: str) -> None:
    assert unsupported_language_dominant(message) is False


def test_rf1q_identifiers_carry_no_language_signal() -> None:
    # Two references of different shape must classify identically, or the
    # route would reveal which one exists.
    assert unsupported_language_dominant(
        "Please list everything about DEMO-PT-2001."
    ) == unsupported_language_dominant("Please list everything about DEMO-ES-1999.")


# ---------------------------------------------------------------- HTTP
_OWNED = {"lucia": "DEMO-ES-1001", "rafael": "DEMO-PT-2001"}
_FOREIGN = {"lucia": "DEMO-PT-2001", "rafael": "DEMO-ES-1001"}
_NONEXISTENT = {"lucia": "DEMO-ES-1999", "rafael": "DEMO-PT-2999"}
_LANGUAGE = {"lucia": "es", "rafael": "pt"}
_FOREIGN_MARKERS = {
    "DEMO-PT-2001": ("Mercado Bairro", "219.90", "219,90", "BRL"),
    "DEMO-ES-1001": ("Mercado Central", "125000", "125.000", "COP"),
}
_OWN_MARKERS = {
    "lucia": ("Mercado Central", "125.000", "COP", "aprobada", "pendiente", "rechazada"),
    "rafael": ("Mercado Bairro", "219,90", "BRL", "aprovada", "pendente", "recusada"),
}


def _client(tmp_path):
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(context)), context


def _turn(client: TestClient, persona: str, message: str) -> tuple[dict, dict]:
    session = client.post(
        "/api/demo/sessions",
        json={"persona_id": persona, "language": _LANGUAGE[persona]},
    ).json()
    response = client.post(
        "/api/customer/turn",
        json={"message": message},
        headers={"X-Demo-Session": session["session_id"]},
    )
    assert response.status_code == 200
    return session, response.json()


def _escalation_context(context, session: dict, body: dict):
    assert body["route"] == "ESCALATE"
    assert body["reason_codes"] == ["unauthorized_activity_reported"]
    assert body["transactions"] == []
    assert body["products"] == []
    assert body["clarification_transaction_ids"] == []
    ticket_id = UUID(body["escalation_ticket_id"])
    resolved = context.store.resolve_verified_escalation_context(ticket_id)
    assert resolved is not None
    assert str(resolved.session.session_id) == session["session_id"]
    assert resolved.session.tenant_id == session["tenant_id"]
    assert resolved.session.customer_id == DEMO_PERSONAS[session["persona_id"]].customer_id
    assert ticket_id in context.store.list_verified_escalation_ticket_ids_for_tenant(
        session["tenant_id"]
    )
    return resolved


_HTTP_REPORTS = [
    ("lucia", "Desconocidos sacaron un préstamo a mi nombre. ¿Qué movimientos tiene?"),
    ("lucia", "Mi papá dice que no reconoce la transacción {ref}; le preocupa su cuenta."),
    ("lucia", "La cuenta corriente que aparece en mi perfil no es mía. Nunca la abrí."),
    ("rafael", "Alguém abriu um cartão no meu nome. Quero saber o saldo dele."),
    ("rafael", "Minha esposa diz que não reconhece a transação {ref}."),
    ("rafael", "Chegou um cartão adicional que eu não solicitei."),
]


@pytest.mark.parametrize(("persona", "message"), _HTTP_REPORTS)
@pytest.mark.parametrize("reference", ["owned", "foreign"])
def test_rf1q_reports_escalate_bound_to_session_without_disclosure(
    tmp_path, persona, message, reference
) -> None:
    client, context = _client(tmp_path)
    ref = (_OWNED if reference == "owned" else _FOREIGN)[persona]
    session, body = _turn(client, persona, message.format(ref=ref))
    resolved = _escalation_context(context, session, body)
    if "{ref}" in message and reference == "owned":
        assert resolved.transaction_id == ref
    else:
        assert resolved.transaction_id is None
    blob = str(body) + (resolved.summary or "")
    for markers in _FOREIGN_MARKERS.values():
        assert not any(marker in blob for marker in markers)
    lowered = body["response_text"].casefold()
    assert not any(
        status in lowered
        for status in ("aprobada", "aprovada", "pendiente", "pendente", "rechazada", "recusada")
    )
    other, _ = _turn(client, "rafael" if persona == "lucia" else "lucia", "Hola")
    assert UUID(body["escalation_ticket_id"]) not in (
        context.store.list_verified_escalation_ticket_ids_for_tenant(other["tenant_id"])
    )


@pytest.mark.parametrize(
    ("persona", "message"),
    [
        ("lucia", "¿Qué hago si alguna vez aparece un retiro que no reconozco?"),
        ("rafael", "O que devo fazer caso apareça uma compra que eu não reconheço?"),
        ("lucia", "Había un retiro que no reconocía, pero ya me lo devolvieron."),
        ("rafael", "Não reconheci o débito no começo, mas já lembrei: era a academia."),
        ("lucia", "Me abrieron una cuenta a mi nombre en la sucursal, ¿cuándo llega la tarjeta?"),
    ],
)
def test_rf1q_hypothetical_and_resolved_turns_create_no_unauthorized_ticket(
    tmp_path, persona, message
) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, message)
    assert "unauthorized_activity_reported" not in body["reason_codes"]
    assert body.get("escalation_ticket_id") is None
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(session["tenant_id"]) == []


@pytest.mark.parametrize("persona", ["lucia", "rafael"])
@pytest.mark.parametrize(
    "template",
    [
        "Is {ref} approved? I never made that payment, it wasn't me.",
        "Did {ref} go through? I want to know the amount.",
        "Can you show me the amount of {ref}? That one is not mine.",
    ],
)
def test_rf1q_english_turn_never_receives_owned_account_data(tmp_path, persona, template) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, template.format(ref=_OWNED[persona]))
    assert body["route"] != "ANSWER"
    assert body["transactions"] == []
    assert body["products"] == []
    assert body["clarification_transaction_ids"] == []
    assert not any(marker in body["response_text"] for marker in _OWN_MARKERS[persona])
    if body["route"] == "ABSTAIN":
        assert body["reason_codes"] == ["unsupported_intent"]
        assert body["handoff_available"] is True
        assert body.get("escalation_ticket_id") is None
    else:
        _escalation_context(context, session, body)


@pytest.mark.parametrize("persona", ["lucia", "rafael"])
def test_rf1q_english_balance_request_receives_no_products(tmp_path, persona) -> None:
    client, _ = _client(tmp_path)
    _, body = _turn(client, persona, "What is my balance on my accounts?")
    assert body["route"] == "ABSTAIN"
    assert body["products"] == []


@pytest.mark.parametrize("persona", ["lucia", "rafael"])
def test_rf1q_english_foreign_and_nonexistent_references_are_indistinguishable(
    tmp_path, persona
) -> None:
    client, _ = _client(tmp_path)
    responses = []
    for ref in (_FOREIGN[persona], _NONEXISTENT[persona]):
        _, body = _turn(client, persona, f"Please list everything you have about {ref}.")
        responses.append(
            (body["route"], body["intent"], body["reason_codes"], body["handoff_available"],
             body["response_text"], body["transactions"], body["clarification_transaction_ids"])
        )
    assert responses[0] == responses[1]


def test_rf1q_frozen_english_code_switch_atom_still_escalates(tmp_path) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, "lucia", "I did not make this purchase.")
    _escalation_context(context, session, body)


@pytest.mark.parametrize(
    ("persona", "message"),
    [
        ("lucia", "¿Cuál es el estado de la transacción DEMO-ES-1001? thanks"),
        ("rafael", "Em que situação está a transação DEMO-PT-2001?"),
    ],
)
def test_rf1q_spanish_and_portuguese_status_answers_are_unchanged(
    tmp_path, persona, message
) -> None:
    client, _ = _client(tmp_path)
    _, body = _turn(client, persona, message)
    assert body["route"] == "ANSWER"
    assert [tx["transaction_id"] for tx in body["transactions"]] == [_OWNED[persona]]
