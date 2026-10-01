from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.demo_data import DEMO_PERSONAS
from app.denial_safety import denial_safety_findings
from app.main import create_app
from app.settings import Settings
from app.unauthorized_signals import is_explicit_unauthorized_assertion


# RF1U repair families. Wording is family-level development material written for
# these tests, not RF1T fresh-probe text, so RF1T stays clean evidence of what was
# repaired. Each entry names the denial-safety family that must license it.
_FAMILY_POSITIVES = [
    # 1. an activity item characterized as fraudulent
    ("fraud_characterization", "Esto fue un consumo fraudulento con la tarjeta débito."),
    ("fraud_characterization", "Me cargaron dos pagos fraudulentos el fin de semana."),
    ("fraud_characterization", "Necesito denunciar un retiro fraudulento del cajero."),
    ("fraud_characterization", "Esse foi um saque fraudulento, eu estava viajando."),
    ("fraud_characterization", "Quero contestar um débito fraudulento na conta poupança."),
    # 2. an activity item characterized as unknown or not recognized
    ("unknown_characterization", "En el resumen figuran tres consumos desconocidos."),
    ("unknown_characterization", "Este giro desconocido salió anoche de la cuenta."),
    ("unknown_characterization", "Encontré un pago no reconocido de una aerolínea."),
    ("unknown_characterization", "Constam dois boletos desconhecidos no aplicativo."),
    ("unknown_characterization", "Vejo um saque não reconhecido feito em outra cidade."),
    ("unknown_characterization", "Hay un cargo de origen desconocido en el estado de cuenta."),
    # 3. first-person non-recognition of a Brazilian "movimento"
    ("non_recognition", "Desconheço esses movimentos de sábado."),
    ("non_recognition", "Não reconheço este movimento de cinquenta reais."),
    # 4. an unnamed party did it, explicitly not the customer
    ("third_party_authorship", "El giro fue enviado por un desconocido, no por mí."),
    ("third_party_authorship", "Ese pago lo realizó alguien más, y no yo."),
    ("third_party_authorship", "O boleto foi pago por terceiros, não por mim."),
    ("third_party_authorship", "Foi alguém, não eu, quem fez esse saque."),
    # 5. the customer's personal or card data used for financial activity
    ("data_misuse", "Utilizaron mis datos bancarios para pedir un microcrédito."),
    ("data_misuse", "Usaron los datos de mi tarjeta para pagar una suscripción."),
    ("data_misuse", "Usaram meu CPF para tirar um empréstimo consignado."),
    ("data_misuse", "Realizaram um saque usando meus dados bancários."),
    # 6. a scam the customer fell for, then activity in their name
    ("scam_activity", "Me timaron con un mensaje falso y pidieron un préstamo a mi nombre."),
    ("scam_activity", "Fui vítima de phishing e compraram passagens no meu nome."),
    ("scam_activity", "Sofrí un fraude por correo; después transfirieron plata de mi cuenta."),
    ("scam_activity", "Fui enganado num site falso. Fizeram um pagamento com meu cartão."),
]

# Near misses for the RF1U families, each with the blocker that must name it. They
# cover the scope's preservation constraints: advice and information requests,
# hypotheticals, hedges, negated presence, resolved or recognized items, incoming
# money, delegation, named actors, a scam with no transaction, and topic mentions.
_NAMED_NEGATIVES = [
    ("¿Cómo detectar un consumo fraudulento?", "interrogative_scope"),
    ("Quisiera consejos para reconocer pagos fraudulentos en línea.", "informational_request"),
    ("Me interesa saber cómo reportar un retiro desconocido.", "informational_request"),
    ("Si llego a ver un giro desconocido, los llamo.", "conditional_protasis"),
    ("Pode ser um débito fraudulento, mas não tenho certeza.", "uncertainty_hedge"),
    ("No hay ningún consumo desconocido este mes.", "negated_presence"),
    ("Hoje não apareceu nenhum boleto desconhecido.", "negated_presence"),
    ("Tenía un pago fraudulento pero ya lo reversaron.", "resolved_or_recognized"),
    ("Ya identifiqué el consumo desconocido: era el gimnasio.", "resolved_or_recognized"),
    ("No principio era um gasto desconhecido, mas era da minha esposa.", "resolved_or_recognized"),
    ("Me entró una transferencia desconocida de 50 mil.", "incoming_transfer"),
    ("Recebemos um ted desconhecido na conta da empresa.", "incoming_transfer"),
    ("El retiro lo hizo un desconocido, no yo, pero yo se lo encargué.", "delegated_by_customer"),
    ("Meus filhos usaram meus dados para fazer uma compra no mercado.", "named_actor"),
    ("Casi caí en una estafa y casi hicieron un pago a mi nombre.", "near_miss"),
    ("Vi un reportaje sobre consumos fraudulentos en general.", "general_topic"),
]

# Benign controls that must stay non-reports: no cue, or a blocked one.
_BENIGN = [
    "¿Cuál es el estado de mi pago de ayer?",
    "Quero ver os movimentos da minha conta desta semana.",
    "Quiero consultar el movimiento de la cuenta del lunes.",
    "Mi compra en la farmacia fue rechazada, ¿por qué?",
    "Tentei pagar o mercado e a transação foi negada.",
    "Me llegó un mensaje de un número desconocido sobre mi tarjeta.",
    "Recibí un giro de un remitente desconocido.",
    "Usaram meus dados para me cadastrar numa newsletter.",
    "Me estafaron con un producto que nunca llegó a mi casa.",
    "Fui vítima de um golpe no Facebook e perdi o perfil.",
    "O pagamento foi feito pela minha irmã, não por mim.",
    "La transferencia la hizo otra persona con mi autorización.",
    "¿Es fraudulenta esta página web?",
    "Desconozco el código que aparece en este cargo.",
]

# Reports that keep escalating next to a blocker-shaped phrase elsewhere.
_STILL_REPORTS = [
    # a resolved item, then a fresh one
    "El cargo desconocido de enero ya me lo devolvieron, pero hoy hay otro cargo desconocido.",
    # an outgoing transfer is not incoming money even with "me hicieron"
    "Me hicieron una transferencia fraudulenta desde mi cuenta corriente.",
    # a charge notification is not incoming money
    "Me llegó un cobro desconocido de 40 dólares.",
    # an invoice the customer received is not incoming money
    "Recebi a fatura e consta um gasto desconhecido.",
    # belief verbs report, as in the structural grammar
    "Creo que es una compra fraudulenta.",
    # the scam licence may sit in the next sentence
    "Caí en un phishing. Después sacaron un avance a mi nombre.",
    # a misspelled gender agreement does not defeat the report
    "Tengo una compra fraudulento en la tarjeta.",
]


def _families(message: str) -> set[str]:
    return {finding.family for finding in denial_safety_findings(message) if finding.asserted}


@pytest.mark.parametrize(("family", "message"), _FAMILY_POSITIVES)
def test_rf1u_family_positives_are_unauthorized_assertions(family: str, message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True
    assert family in _families(message)


@pytest.mark.parametrize(("message", "blocker"), _NAMED_NEGATIVES)
def test_rf1u_near_misses_are_blocked_by_name(message: str, blocker: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False
    assert blocker in {finding.blocked_by for finding in denial_safety_findings(message)}


@pytest.mark.parametrize("message", _BENIGN)
def test_rf1u_benign_controls_are_not_reports(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False


@pytest.mark.parametrize("message", _STILL_REPORTS)
def test_rf1u_boundaries_stay_reports(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True


# U-P01 follow-up: a vocative, greeting, or interjection before the copula (or before
# a bare item at the start of its clause) must not defeat the report; a lead clause
# that is only a hedge or a prior belief still keeps it unasserted.
_LEADING_VOCATIVE_REPORTS = [
    ("fraud_characterization", "Buenas noches, es un consumo fraudulento."),
    ("fraud_characterization", "Disculpe, fue un retiro fraudulento del cajero."),
    ("fraud_characterization", "Pessoal, é um saque fraudulento."),
    ("unknown_characterization", "Hola, es un débito no reconocido de anoche."),
    ("unknown_characterization", "Boa tarde, foi uma transação desconhecida."),
    ("unknown_characterization", "Oye, un giro desconocido en mi cuenta."),
]
_LEADING_HEDGE_CLAUSES = [
    "Quizá, es un consumo fraudulento.",
    "A lo mejor, es un retiro desconocido.",
    "Talvez, é um saque fraudulento.",
    "Não tenho certeza, é uma transação desconhecida.",
    "Pensaba, es un débito fraudulento, pero no.",
]


@pytest.mark.parametrize(("family", "message"), _LEADING_VOCATIVE_REPORTS)
def test_rf1u_leading_vocative_does_not_defeat_the_report(family: str, message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True
    assert family in _families(message)


@pytest.mark.parametrize("message", _LEADING_HEDGE_CLAUSES)
def test_rf1u_leading_hedge_clause_keeps_the_copula_unasserted(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False
    assert "uncertainty_hedge" in {
        finding.blocked_by for finding in denial_safety_findings(message)
    }


def test_rf1u_characterization_needs_the_item_itself() -> None:
    # The adjective must characterize the activity item, not a party next to it.
    for message in (
        "Hay una transferencia de un remitente desconocido.",
        "Tem um pix de uma pessoa desconhecida.",
    ):
        assert not any(
            finding.family == "unknown_characterization"
            for finding in denial_safety_findings(message)
        ), message


def test_rf1u_scam_alone_is_not_a_report() -> None:
    findings = [
        finding
        for finding in denial_safety_findings("Caí num golpe pelo telefone ontem.")
        if finding.family == "scam_activity"
    ]
    assert findings
    assert all(finding.blocked_by == "no_activity_anchor" for finding in findings)


@pytest.mark.parametrize(
    "message",
    [
        "Caí en una estafa. ¿Si hicieron un pago a mi nombre, qué hago?",
        "Me aplicaram um golpe; se fizeram uma compra no meu nome eu aviso.",
    ],
)
def test_rf1u_scam_licence_respects_question_and_conditional_scope(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False


def test_rf1u_negated_transaction_after_a_scam_is_not_a_licence() -> None:
    message = "Me estafaron, pero no hicieron ninguna compra a mi nombre."
    assert is_explicit_unauthorized_assertion(message) is False


# ---------------------------------------------------------------- HTTP
_OWNED = {"lucia": "DEMO-ES-1001", "rafael": "DEMO-PT-2001"}
_FOREIGN = {"lucia": "DEMO-PT-2001", "rafael": "DEMO-ES-1001"}
_UNOWNED = {"lucia": "DEMO-ES-9999", "rafael": "DEMO-PT-9999"}
_LANGUAGE = {"lucia": "es", "rafael": "pt"}
_FOREIGN_MARKERS = {
    "DEMO-PT-2001": ("Mercado Bairro", "219.90", "219,90", "BRL"),
    "DEMO-ES-1001": ("Mercado Central", "125000", "125.000", "COP"),
}
_OWN_MARKERS = {
    "lucia": ("Mercado Central", "125.000", "COP"),
    "rafael": ("Mercado Bairro", "219,90", "BRL"),
}
_STATUS_WORDS = ("aprobada", "aprovada", "pendiente", "pendente", "rechazada", "recusada")
_SUFFIX = {
    "lucia": {
        "owned": " Es la transacción {ref}.",
        "none": "",
        "amount": " Fue por 80.000 pesos.",
        "foreign": " Es la transacción {ref}.",
        "unowned": " Es la transacción {ref}.",
    },
    "rafael": {
        "owned": " É a transação {ref}.",
        "none": "",
        "amount": " Foi de R$ 75,00.",
        "foreign": " É a transação {ref}.",
        "unowned": " É a transação {ref}.",
    },
}
_REFERENCE = {"owned": _OWNED, "foreign": _FOREIGN, "unowned": _UNOWNED}


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


# One report per RF1U family and language.
_HTTP_REPORTS = [
    ("lucia", "Esto es un retiro fraudulento."),
    ("rafael", "Isso é um pix fraudulento."),
    ("lucia", "Me apareció un consumo desconocido en la tarjeta."),
    ("rafael", "Tenho um gasto não reconhecido no cartão."),
    ("lucia", "Desconozco este giro de la cuenta."),
    ("rafael", "Desconheço esses movimentos da conta."),
    ("lucia", "El retiro fue hecho por un tercero, no por mí."),
    ("rafael", "O pix foi enviado por outra pessoa, não por mim."),
    ("lucia", "Usaron mis datos personales para pagar en un casino en línea."),
    ("rafael", "Utilizaram os dados do meu cartão para fazer um pix."),
    ("lucia", "Fui víctima de una estafa y pagaron servicios a mi nombre."),
    ("rafael", "Caí em um golpe e realizaram uma transferência no meu nome."),
]


@pytest.mark.parametrize(("persona", "message"), _HTTP_REPORTS)
@pytest.mark.parametrize("reference", ["owned", "none", "amount", "foreign", "unowned"])
def test_rf1u_reports_escalate_bound_to_session_without_disclosure(
    tmp_path, persona, message, reference
) -> None:
    client, context = _client(tmp_path)
    ref = _REFERENCE[reference][persona] if reference in _REFERENCE else ""
    session, body = _turn(client, persona, message + _SUFFIX[persona][reference].format(ref=ref))
    resolved = _escalation_context(context, session, body)
    if reference in {"foreign", "unowned"}:
        assert resolved.transaction_id is None
    blob = str(body) + (resolved.summary or "")
    for markers in _FOREIGN_MARKERS.values():
        assert not any(marker in blob for marker in markers)
    lowered = body["response_text"].casefold()
    assert not any(status in lowered for status in _STATUS_WORDS)
    other, _ = _turn(client, "rafael" if persona == "lucia" else "lucia", "Hola")
    assert UUID(body["escalation_ticket_id"]) not in (
        context.store.list_verified_escalation_ticket_ids_for_tenant(other["tenant_id"])
    )


@pytest.mark.parametrize(
    ("persona", "message"),
    [
        ("lucia", "Buenas noches, es un consumo fraudulento. Es la transacción {ref}."),
        ("rafael", "Boa tarde, é uma transação desconhecida. É a transação {ref}."),
    ],
)
def test_rf1u_leading_vocative_with_owned_id_escalates_not_answers(
    tmp_path, persona, message
) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, message.format(ref=_OWNED[persona]))
    _escalation_context(context, session, body)
    lowered = body["response_text"].casefold()
    assert not any(status in lowered for status in _STATUS_WORDS)


@pytest.mark.parametrize(
    ("persona", "message"),
    [
        ("lucia", "Tenía un pago fraudulento pero ya lo reversaron. Es la DEMO-ES-1001."),
        ("lucia", "¿Cómo detectar un consumo fraudulento?"),
        ("lucia", "Me entró una transferencia desconocida de 50 mil."),
        ("lucia", "El retiro lo hizo un desconocido, no yo, pero yo se lo encargué."),
        ("rafael", "Hoje não apareceu nenhum boleto desconhecido. Qual é meu saldo?"),
        ("rafael", "Meus filhos usaram meus dados para fazer uma compra no mercado."),
        ("rafael", "Quase caí num golpe, mas desliguei a tempo."),
    ],
)
def test_rf1u_benign_turns_create_no_ticket(tmp_path, persona, message) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, message)
    assert "unauthorized_activity_reported" not in body["reason_codes"]
    assert body.get("escalation_ticket_id") is None
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(session["tenant_id"]) == []


@pytest.mark.parametrize("persona", ["lucia", "rafael"])
def test_rf1u_owned_status_check_still_answers(tmp_path, persona) -> None:
    client, context = _client(tmp_path)
    message = {
        "lucia": "¿Cuál es el estado de la transacción DEMO-ES-1001?",
        "rafael": "Qual é o status da transação DEMO-PT-2001?",
    }[persona]
    session, body = _turn(client, persona, message)
    assert body["route"] == "ANSWER"
    assert body.get("escalation_ticket_id") is None
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(session["tenant_id"]) == []


@pytest.mark.parametrize("persona", ["lucia", "rafael"])
@pytest.mark.parametrize(
    "message",
    [
        "This is a fraudulent charge. Status of {ref}?",
        "I have an unknown charge on my card. Show me {ref}.",
        "Someone else made that transfer, not me. What about {ref}?",
    ],
)
def test_rf1u_english_path_b_is_unchanged(tmp_path, persona, message) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, message.format(ref=_OWNED[persona]))
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
