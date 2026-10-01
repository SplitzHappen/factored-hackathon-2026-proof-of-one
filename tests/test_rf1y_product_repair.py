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


# RF1Y repair families. Wording is family-level development material written for
# these tests, not RF1X fresh-probe text. Each entry names the denial-safety family
# that must license it.
_FAMILY_POSITIVES = [
    # 1. passive drain or use of the customer's account, card, or data
    ("passive_account_misuse", "Mi tarjeta fue clonada por desconocidos y hubo compras."),
    ("passive_account_misuse", "Mis datos fueron usados por un tercero sin mi autorización."),
    ("passive_account_misuse", "Mi cuenta de ahorros fue vaciada y yo no autoricé nada."),
    ("passive_account_misuse", "Meu cartão foi clonado por golpistas."),
    ("passive_account_misuse", "Foram usados meus dados sem minha permissão."),
    ("passive_account_misuse", "Minha conta corrente foi zerada, eu não autorizei."),
    # 2. Spanish double-clitic account drain
    ("double_clitic_drain", "Revisé mi cuenta y me la vaciaron anoche."),
    ("double_clitic_drain", "Tenía mis ahorros en la cuenta y me la dejaron en cero."),
    ("double_clitic_drain", "Un desconocido me la vació, la tarjeta prepago quedó sin saldo."),
    ("double_clitic_drain", "Revisé la cuenta y me la vaciaron con compras en una tienda."),
    ("double_clitic_drain", "Fui a la oficina del banco: me la vaciaron, la cuenta quedó en cero."),
    # 3. progressive or habitual use of the customer's account
    ("progressive_account_use", "Alguém anda usando minha conta para fazer pagamentos."),
    ("progressive_account_use", "Desconhecidos vêm usando a minha conta para mandar dinheiro."),
    ("progressive_account_use", "Andam usando minha conta sem minha autorização."),
    ("progressive_account_use", "Un desconocido ha estado usando mi cuenta para pagar cosas."),
    ("progressive_account_use", "Andan usando mi cuenta para transferir dinero."),
    # 4. fronted lack of permission with an article-only object
    ("fronted_permission_drain", "Sin mi consentimiento, vaciaron la cuenta."),
    ("fronted_permission_drain", "Sin mi autorización, un desconocido usó la tarjeta."),
    ("fronted_permission_drain", "Sem minha permissão, zeraram a conta."),
    ("fronted_permission_drain", "Sem autorização, alguém limpou o saldo."),
    # 5. drain of a quantified plural of the customer's accounts
    ("quantified_plural_drain", "Me limpiaron ambas cuentas el fin de semana."),
    ("quantified_plural_drain", "Esvaziaram minhas duas contas ontem."),
    ("quantified_plural_drain", "Nos vaciaron las tres cuentas que teníamos."),
    ("quantified_plural_drain", "Alguém zerou as duas contas."),
    # 6. the customer left without money by an impersonal or unnamed party
    ("no_money_drain", "Me dejaron sin un peso en la tarjeta."),
    ("no_money_drain", "Alguien me dejó sin plata, hay retiros que no hice."),
    ("no_money_drain", "Me deixaram sem um centavo na conta."),
    ("no_money_drain", "Me deixaram sem dinheiro, não fui eu que fiz esses saques."),
]

_RF1Y_FAMILY_NAMES = {
    "passive_account_misuse",
    "double_clitic_drain",
    "progressive_account_use",
    "fronted_permission_drain",
    "quantified_plural_drain",
    "no_money_drain",
}

# Near misses for the RF1Y families, each with the blocker that must name it.
_NAMED_NEGATIVES = [
    ("Mi tarjeta fue vaciada por el banco por una deuda, sin mi permiso.", "named_actor"),
    ("Mi cuenta fue vaciada por mi hermano sin mi permiso.", "named_actor"),
    ("Si me la vaciaron, ¿qué hago con la cuenta?", "conditional_protasis"),
    ("¿Me la vaciaron? No entiendo mi cuenta.", "interrogative_scope"),
    ("Las comisiones me vaciaron las dos cuentas.", "overt_subject"),
    ("Me dejaron sin un peso en la cuenta los intereses del crédito.", "post_verbal_cause"),
    (
        "Andam usando minha conta para fazer transferências para mim do meu salário.",
        "incoming_transfer",
    ),
    (
        "Me dejaron sin un centavo en la cuenta, pero ya me devolvieron todo.",
        "resolved_or_recognized",
    ),
]

# Benign controls the RF1Y families must not license at all.
_BENIGN = [
    "Mi cuenta fue vaciada para pagar la hipoteca como lo pedí.",
    "Minha conta foi zerada porque paguei a fatura.",
    "Mis datos fueron actualizados ayer.",
    "La casa la encontré vacía: me la vaciaron los ladrones.",
    "Me la dejaron en cero, la cuenta de correo, por spam.",
    "Estou usando minha conta para pagar boletos, qual o limite?",
    "Meu filho anda usando minha conta para pagar a escola, com minha autorização.",
    "Mi esposa anda usando mi cuenta para pagar la luz.",
    "Sin mi permiso no se puede cerrar la cuenta, ¿verdad?",
    "Sem minha autorização ninguém pode usar a conta, certo?",
    "Vacié las dos cuentas para comprar el carro.",
    "Cerré mis dos cuentas y pasé todo a otro banco.",
    "Me dejaron sin un peso los gastos del mes.",
    "Este mes me quedé sin un centavo por pagar el arriendo.",
    "La inflación me dejó sin plata.",
    "Me dejaron sin internet en la oficina.",
]

# 7. Non-recognition of the app, its version, or its interface is not a report.
_INTERFACE_NONRECOGNITION = [
    "No reconozco el nuevo diseño de la aplicación, ¿cómo hago un pago?",
    "Não reconheço a nova versão do aplicativo, onde vejo meus pagamentos?",
    "Desconozco la nueva interfaz, ¿dónde están las transferencias programadas?",
    "No reconozco este botón de la pantalla de transferencias.",
]
# Non-recognition of an activity stays a report, with or without app wording.
_RECOGNITION_REPORTS = [
    "No reconozco la app ni este cargo de 50 dólares.",
    "No reconozco esta transferencia que aparece en la app.",
    "Não reconheço essa compra no aplicativo.",
    "No reconozco la nueva versión de la app y hay un retiro que no hice.",
    "No reconozco el cargo, la app dice que fue en otra ciudad.",
    "No reconozco el sitio donde se hizo esta compra.",
    "No reconozco la página de la tienda que me cobró.",
]


@pytest.mark.parametrize(("family", "message"), _FAMILY_POSITIVES)
def test_rf1y_family_positives_are_unauthorized_assertions(family: str, message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True
    assert any(f.family == family and f.asserted for f in denial_safety_findings(message))


@pytest.mark.parametrize(("message", "blocker"), _NAMED_NEGATIVES)
def test_rf1y_near_misses_are_blocked_by_name(message: str, blocker: str) -> None:
    findings = [f for f in denial_safety_findings(message) if f.family in _RF1Y_FAMILY_NAMES]
    assert findings and all(not f.asserted for f in findings)
    assert any(f.blocked_by == blocker for f in findings)


@pytest.mark.parametrize("message", _BENIGN)
def test_rf1y_benign_controls_are_not_reports(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False
    assert not any(
        f.asserted for f in denial_safety_findings(message) if f.family in _RF1Y_FAMILY_NAMES
    )


@pytest.mark.parametrize("message", _INTERFACE_NONRECOGNITION)
def test_rf1y_interface_nonrecognition_is_not_a_report(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False
    recognition = [f for f in denial_safety_findings(message) if f.family == "non_recognition"]
    assert recognition and not any(f.asserted for f in recognition)


@pytest.mark.parametrize("message", _RECOGNITION_REPORTS)
def test_rf1y_activity_nonrecognition_stays_a_report(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True


def test_rf1y_cue_sin_mask_keeps_a_real_conditional() -> None:
    message = "Si me dejaron sin un centavo en la cuenta, ¿qué hago?"
    assert is_explicit_unauthorized_assertion(message) is False
    findings = [f for f in denial_safety_findings(message) if f.family == "no_money_drain"]
    assert findings and findings[0].blocked_by == "conditional_protasis"


# ---------------------------------------------------------------- HTTP
_OWNED = {"lucia": "DEMO-ES-1001", "rafael": "DEMO-PT-2001"}
_FOREIGN = {"lucia": "DEMO-PT-2001", "rafael": "DEMO-ES-1001"}
_UNOWNED = {"lucia": "DEMO-ES-9999", "rafael": "DEMO-PT-9999"}
_LANGUAGE = {"lucia": "es", "rafael": "pt"}
_FOREIGN_MARKERS = {
    "DEMO-PT-2001": ("Mercado Bairro", "219.90", "219,90", "BRL"),
    "DEMO-ES-1001": ("Mercado Central", "125000", "125.000", "COP"),
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


# One report per RF1Y family and language.
_HTTP_REPORTS = [
    ("lucia", "Mi cuenta fue vaciada por desconocidos."),
    ("rafael", "Minha conta foi esvaziada por alguém, não fui eu."),
    ("lucia", "Abrí la app y me la vaciaron, no queda nada."),
    ("rafael", "Alguém anda usando minha conta para fazer pagamentos."),
    ("lucia", "Un desconocido ha estado usando mi cuenta para pagar cosas."),
    ("lucia", "Sin mi autorización, vaciaron la cuenta."),
    ("rafael", "Sem minha permissão, alguém esvaziou a conta."),
    ("lucia", "Me vaciaron las dos cuentas anoche."),
    ("rafael", "Esvaziaram minhas duas contas ontem."),
    ("lucia", "Me dejaron sin un peso en la cuenta sin mi permiso."),
    ("rafael", "Me deixaram sem um centavo na conta."),
]


@pytest.mark.parametrize(("persona", "message"), _HTTP_REPORTS)
@pytest.mark.parametrize("reference", ["owned", "none", "amount", "foreign", "unowned"])
def test_rf1y_reports_escalate_bound_to_session_without_disclosure(
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
        ("lucia", "No reconozco el nuevo diseño de la aplicación, ¿dónde quedó la opción de pagos?"),
        ("rafael", "Não reconheço a nova versão do aplicativo; onde fica a tela de transferências?"),
        ("lucia", "Mi cuenta fue vaciada para pagar la hipoteca como lo pedí."),
        ("rafael", "Meu filho anda usando minha conta para pagar a escola, com minha autorização."),
        ("lucia", "Me dejaron sin un peso los gastos del mes. Es la transacción DEMO-ES-1001."),
    ],
)
def test_rf1y_benign_turns_create_no_ticket(tmp_path, persona, message) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, message)
    assert body["route"] != "ESCALATE"
    assert body.get("escalation_ticket_id") is None
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(session["tenant_id"]) == []
