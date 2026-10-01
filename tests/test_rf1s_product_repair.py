from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.demo_data import DEMO_PERSONAS
from app.denial_safety import denial_safety_findings, structural_assertion_demotion
from app.main import create_app
from app.settings import Settings
from app.unauthorized_grammar import PropositionMode, resolve_positive_propositions
from app.unauthorized_signals import is_explicit_unauthorized_assertion


# RF1S repair families. Wording is family-level development material written for
# these tests, not RF1R fresh-probe text, so RF1R stays clean evidence of what was
# repaired. Each entry names the denial-safety family that must license it.
_FAMILY_POSITIVES = [
    # 1. an item observed in the customer's records, then disowned in a relative clause
    ("non_origination", "Veo un cobro recurrente de una app de música que yo nunca agregué."),
    ("non_origination", "Me sale un débito mensual a un club de vinos de Chile que jamás programé."),
    ("product_origination_denial", "En el resumen aparece un CDT a seis meses que nunca abrí."),
    ("product_origination_denial", "En la central de riesgo me figura un microcrédito que yo jamás solicité."),
    ("product_origination_denial", "Me cobran una póliza funeraria cada mes; nunca acepté esa póliza."),
    ("product_origination_denial", "No meu extrato aparece um seguro residencial que eu nunca contratei."),
    # 2. impersonation / identity theft by an unnamed party
    ("impersonation", "Una persona se hizo pasar por mí en la oficina y pidió el saldo de mi cuenta."),
    ("impersonation", "Me están suplantando: ya van dos llamadas del banco por créditos que no reconozco."),
    ("impersonation", "Usaron mis documentos para tramitar una tarjeta en otra ciudad."),
    ("impersonation", "Uma pessoa estranha se passou por mim no telefone do banco."),
    # 3. credential takeover: a credential change the customer disowns
    ("credential_takeover", "Alguien cambió el correo de mi perfil y ya no me llegan las alertas."),
    ("credential_takeover", "Me llegó un aviso de que actualizaron mi número de teléfono; yo no hice ese cambio."),
    ("credential_takeover", "Modificaron la clave de la banca virtual sin mi consentimiento."),
    ("credential_takeover", "Mudaram o e-mail da minha conta e eu nunca o alterei."),
    # 4. an unnamed party performed activity tied to the customer's account
    ("unnamed_actor_activity", "Alguien está usando mi tarjeta de crédito en tiendas de ropa."),
    ("unnamed_actor_activity", "Un tercero retiró dinero de mi cuenta de ahorros en un cajero de Cúcuta."),
    ("unnamed_actor_activity", "Abrí la aplicación y me di cuenta de que alguien pagó dos recargas de celular."),
    ("unnamed_actor_activity", "Percebi no aplicativo que alguém fez três compras com meu cartão."),
    # 5. a relay by a relative or by someone acting for the account holder
    ("third_party_denial", "Escribo por mi abuelo: de su cuenta salieron 900 mil y no fue él."),
    ("third_party_denial", "Soy la representante legal de la señora Gómez; vio retiros que ella no hizo."),
    ("third_party_denial", "Sou o procurador do seu Antônio e ele não reconhece dois saques da conta dele."),
    # 6. activity nouns the repair adds (a cash advance)
    ("non_performance", "Tengo un avance en la tarjeta de crédito que yo no hice."),
]

# Near misses for the RF1S families: incoming money, delegation, a requested or
# self-made change, a declined offer, a named actor, activity with no tie to the
# customer's account, non-banking impersonation, and a relay with no denial.
_FAMILY_NEGATIVES = [
    "Alguien me consignó 120 mil esta mañana, ¿ya se ve en el saldo?",
    "Un cliente hizo una transferencia a mi cuenta por la venta del carro.",
    "Alguém me fez um pix de 80 reais, já caiu?",
    "En la app vi que alguien me transfirió 120 mil, ¿ya está disponible?",
    "Alguien hizo la transferencia desde mi cuenta por mí, como le pedí.",
    "Me restablecieron la clave en la sucursal como pedí; ¿cuándo puedo entrar?",
    "Cambié el correo de mi perfil la semana pasada, ¿ya quedó?",
    "Me cambiaron el número de celular en la oficina porque perdí el anterior.",
    "Nunca acepté esa póliza porque era muy cara; ¿tienen otra más barata?",
    "No acepté el crédito que me ofrecieron por teléfono.",
    "La compra del mercado la hizo mi esposo con la tarjeta adicional que le di.",
    "Alguien hizo una compra grande en la tienda donde trabajo.",
    "Un desconocido sacó plata del cajero que está al lado de mi casa.",
    "Alguien se hace pasar por mí en Facebook vendiendo cosas.",
    "Alguien se hace pasar por mí en Facebook pidiendo plata prestada.",
    "Como apoderado de don Julio necesito el certificado de su cuenta de ahorros.",
    "Escribo por mi papá, que necesita un certificado de su cuenta.",
    "En mi estado de cuenta está el CDT que yo mismo abrí en febrero; ¿qué tasa paga?",
    "Me aparece la póliza que contraté con el crédito hipotecario.",
    "La compra la hizo mi esposa con mi tarjeta; no fue él.",
    "Me faltan 200 mil para pagar el arriendo.",
]

# Over-escalation control 1: the customer's own attempted payment was declined or
# labelled "not authorized" by the bank.
_OWN_DECLINED = [
    "Mi recarga del celular salió no autorizada y tuve que hacerla en efectivo.",
    "Mi pago de la matrícula salió no autorizado y me lo rechazaron dos veces.",
    "Traté de pagar el peaje y el datáfono marcó transacción no autorizada; ¿qué pasa?",
    "Estaba pagando el gimnasio desde la app y la operación quedó como no autorizada; ¿me la rechazaron?",
    "Al retirar en el cajero me dio no autorizado, ¿tengo algún bloqueo?",
    "Fui pagar o estacionamento e a maquininha mostrou transação não autorizada; por que recusaram?",
    "Meu pagamento do condomínio não foi autorizado e foi recusado no app.",
]

# Boundary pins: a decline mentioned next to a genuine report stays a report.
_DECLINE_STILL_REPORTS = [
    "Me rechazaron la tarjeta porque había compras no autorizadas que yo no hice.",
    "Intenté pagar y en la app vi un cargo no autorizado de una tienda que no conozco.",
    "Hay un débito no autorizado en mi cuenta de nómina.",
    "Mi pago fue rechazado y además aparece una transferencia no autorizada de 2 millones.",
    "Mi pago a la plataforma no fue autorizado por mí y no sé por qué no pasó.",
]

# Over-escalation control 2: the item was resolved, recognized, or attributed.
_RESOLVED = [
    "Ya se aclaró lo de la transferencia que no reconocía; ¿cuál es mi cupo?",
    "Lo del débito que no reconocí ya quedó resuelto, gracias.",
    "Ya me reintegraron lo que alguien había sacado de mi cuenta en mayo.",
    "No reconocía ese cobro al principio, pero resultó ser de mi esposa.",
    "El retiro que no reconocí fue mi hijo, ya hablé con él.",
    "Já foi resolvido o débito que eu não reconhecia; qual é meu limite?",
]

# Boundary pins: a resolution that does not cover the reported item, a fresh
# event after a resolution, a present-tense denial, and unauthorized family use.
_RESOLVED_STILL_REPORTS = [
    "Ya me devolvieron lo de abril, pero hoy hay otro cobro que no reconozco.",
    "Ya me devolvieron lo de abril, pero alguien volvió a sacar plata de mi cuenta.",
    "No reconocí la compra, la hizo mi sobrino sin mi permiso.",
    "Ya está resuelto lo del CDT; hoy alguien usó mi tarjeta en otra ciudad.",
    "Ya me devolvieron lo de marzo. Ayer apareció un cargo que no reconocí.",
    "No reconocí el cargo; le pregunté a mi hijo y no fue mi hijo.",
]

# Hypothetical / advice questions over the RF1S families.
_HYPOTHETICALS = [
    "¿Qué debo hacer si un día una persona se hace pasar por mí en una sucursal?",
    "Si alguna vez alguien cambia mi contraseña, ¿cómo me entero?",
    "¿Cómo puedo saber si un tercero usó mi tarjeta?",
    "Si algún día un tercero retirara fondos de mi cuenta, ¿el banco responde?",
    "Supongamos que aparece un seguro que nunca acepté, ¿qué debo hacer?",
    "En caso de que mi mamá vea retiros que ella no hizo, ¿quién debe llamar?",
    "O que acontece se alguém se passar por mim no banco?",
]


def _families(message: str) -> set[str]:
    return {finding.family for finding in denial_safety_findings(message) if finding.asserted}


@pytest.mark.parametrize(("family", "message"), _FAMILY_POSITIVES)
def test_rf1s_family_positives_are_unauthorized_assertions(family: str, message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True
    assert family in _families(message)


@pytest.mark.parametrize("message", _FAMILY_NEGATIVES)
def test_rf1s_family_near_misses_are_not_reported(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False


@pytest.mark.parametrize("message", _OWN_DECLINED)
def test_rf1s_own_declined_payment_is_not_an_unauthorized_report(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False


@pytest.mark.parametrize("message", _DECLINE_STILL_REPORTS)
def test_rf1s_decline_next_to_a_genuine_report_stays_a_report(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True


@pytest.mark.parametrize("message", _RESOLVED)
def test_rf1s_resolved_or_recognized_items_are_not_reports(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False


@pytest.mark.parametrize("message", _RESOLVED_STILL_REPORTS)
def test_rf1s_resolution_boundaries_stay_reports(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True


@pytest.mark.parametrize("message", _HYPOTHETICALS)
def test_rf1s_hypothetical_advice_questions_are_not_reports(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False


# ---------------------------------------------------------------- demotion
def _assertive_spans(message: str) -> list[tuple[int, int]]:
    return [
        (proposition.source_start, proposition.source_end)
        for language in ("es", "pt")
        for proposition in resolve_positive_propositions(message, language)
        if proposition.mode == PropositionMode.ASSERTIVE.value
    ]


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        ("Mi pago de la matrícula salió no autorizado y me lo rechazaron dos veces.", "declined_own_attempt"),
        ("Ya se aclaró lo de la transferencia que no reconocía; ¿cuál es mi cupo?", "resolved_before"),
        ("No reconocí el retiro del viernes; fue mi hija.", "recognized_attribution"),
        ("Lo del débito que no reconocí ya quedó resuelto, gracias.", "resolved_after"),
    ],
)
def test_rf1s_structural_demotion_names_its_shape(message: str, reason: str) -> None:
    spans = _assertive_spans(message)
    assert spans, "the resolver must assert this shape for the demotion to matter"
    assert {structural_assertion_demotion(message, start, end) for start, end in spans} == {reason}


@pytest.mark.parametrize(
    "message",
    [
        "Hay un pago no autorizado en mi cuenta.",
        "Me rechazaron la tarjeta porque había compras no autorizadas que yo no hice.",
        "No reconocí la compra, la hizo mi sobrino sin mi permiso.",
        "No reconozco el cargo; era de una tienda que no conozco.",
    ],
)
def test_rf1s_demotion_leaves_other_assertions_authoritative(message: str) -> None:
    spans = _assertive_spans(message)
    assert spans
    assert any(structural_assertion_demotion(message, start, end) is None for start, end in spans)
    assert is_explicit_unauthorized_assertion(message) is True


def test_rf1s_demotion_hands_the_decision_to_the_layer_not_to_false() -> None:
    # The own-declined label is demoted, but a credential takeover in the same
    # message is a separate report the layer still licenses.
    message = (
        "Mi pago salió no autorizado y me lo rechazaron; además alguien cambió el correo de mi perfil."
    )
    spans = _assertive_spans(message)
    assert spans
    assert all(
        structural_assertion_demotion(message, start, end) == "declined_own_attempt"
        for start, end in spans
    )
    assert is_explicit_unauthorized_assertion(message) is True
    assert "credential_takeover" in _families(message)


def test_rf1s_blockers_are_named_for_audit() -> None:
    cases = {
        "En la app vi que alguien me transfirió 120 mil, ¿ya está disponible?": "incoming_transfer",
        "Alguien hizo la transferencia desde mi cuenta por mí, como le pedí.": (
            "delegated_by_customer"
        ),
        "Me restablecieron la clave en la sucursal como pedí; ¿cuándo puedo entrar?": (
            "customer_requested"
        ),
        "Alguien se hace pasar por mí en Facebook pidiendo plata prestada.": "non_bank_context",
        "Me cambiaron el número de celular en la oficina porque perdí el anterior.": (
            "change_not_disowned"
        ),
    }
    for message, blocker in cases.items():
        assert blocker in {
            finding.blocked_by for finding in denial_safety_findings(message)
        }, message


# ---------------------------------------------------------------- HTTP
_OWNED = {"lucia": "DEMO-ES-1001", "rafael": "DEMO-PT-2001"}
_FOREIGN = {"lucia": "DEMO-PT-2001", "rafael": "DEMO-ES-1001"}
_LANGUAGE = {"lucia": "es", "rafael": "pt"}
_FOREIGN_MARKERS = {
    "DEMO-PT-2001": ("Mercado Bairro", "219.90", "219,90", "BRL"),
    "DEMO-ES-1001": ("Mercado Central", "125000", "125.000", "COP"),
}
_OWN_MARKERS = {
    "lucia": ("Mercado Central", "125.000", "COP"),
    "rafael": ("Mercado Bairro", "219,90", "BRL"),
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
    ("lucia", "Me sale un débito mensual a un club de vinos que jamás programé. Referencia {ref}."),
    ("lucia", "Una persona se hizo pasar por mí en la oficina; ¿qué pasó con {ref}?"),
    ("lucia", "Alguien cambió el correo de mi perfil. ¿Cuál es el estado de {ref}?"),
    ("lucia", "Escribo por mi abuelo: de su cuenta salieron 900 mil y no fue él. Ref {ref}."),
    ("lucia", "Tengo un avance en la tarjeta que yo no hice; muéstrame {ref}."),
    ("rafael", "Percebi no aplicativo que alguém fez compras com meu cartão. E a {ref}?"),
    ("rafael", "Mudaram o e-mail da minha conta e eu nunca o alterei. Qual o status de {ref}?"),
]


@pytest.mark.parametrize(("persona", "message"), _HTTP_REPORTS)
@pytest.mark.parametrize("reference", ["owned", "foreign"])
def test_rf1s_reports_escalate_bound_to_session_without_disclosure(
    tmp_path, persona, message, reference
) -> None:
    client, context = _client(tmp_path)
    ref = (_OWNED if reference == "owned" else _FOREIGN)[persona]
    session, body = _turn(client, persona, message.format(ref=ref))
    resolved = _escalation_context(context, session, body)
    if reference == "foreign":
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
        ("lucia", "Mi recarga del celular salió no autorizada y tuve que hacerla en efectivo."),
        ("lucia", "Ya se aclaró lo de la transferencia que no reconocía; ¿cuál es mi saldo?"),
        ("lucia", "No reconocía ese cobro al principio, pero resultó ser de mi esposa."),
        ("lucia", "¿Qué debo hacer si un día una persona se hace pasar por mí en una sucursal?"),
        ("lucia", "Me restablecieron la clave en la sucursal como pedí."),
        ("rafael", "Fui pagar o estacionamento e a maquininha mostrou transação não autorizada; por que recusaram?"),
        ("rafael", "Já foi resolvido o débito que eu não reconhecia; qual é meu saldo?"),
    ],
)
def test_rf1s_declined_resolved_and_hypothetical_turns_create_no_ticket(
    tmp_path, persona, message
) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, message)
    assert "unauthorized_activity_reported" not in body["reason_codes"]
    assert body.get("escalation_ticket_id") is None
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(session["tenant_id"]) == []


@pytest.mark.parametrize("persona", ["lucia", "rafael"])
def test_rf1s_resolved_turn_still_answers_the_balance(tmp_path, persona) -> None:
    client, _ = _client(tmp_path)
    message = {
        "lucia": "Ya se aclaró lo de la transferencia que no reconocía; ¿cuál es mi saldo?",
        "rafael": "Já foi resolvido o débito que eu não reconhecia; qual é meu saldo?",
    }[persona]
    _, body = _turn(client, persona, message)
    assert body["route"] == "ANSWER"
    assert body["products"]


@pytest.mark.parametrize("persona", ["lucia", "rafael"])
@pytest.mark.parametrize(
    "message",
    [
        "Someone is pretending to be me and changed the email on my profile. Status of {ref}?",
        "My grandfather says money left his account and it wasn't him. Show me {ref}.",
        "Somebody used my card at a store I've never been to. What about {ref}?",
    ],
)
def test_rf1s_english_path_b_is_unchanged(tmp_path, persona, message) -> None:
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


def test_rf1s_relay_ticket_is_bound_to_the_reporting_session_only(tmp_path) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(
        client,
        "lucia",
        f"Soy la cuidadora de mi tía; en la cuenta {_FOREIGN['lucia']} hay retiros que ella no hizo.",
    )
    resolved = _escalation_context(context, session, body)
    assert resolved.transaction_id is None
    blob = str(body) + (resolved.summary or "")
    assert not any(marker in blob for marker in _FOREIGN_MARKERS[_FOREIGN["lucia"]])
    other, _ = _turn(client, "rafael", "Olá")
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(other["tenant_id"]) == []
