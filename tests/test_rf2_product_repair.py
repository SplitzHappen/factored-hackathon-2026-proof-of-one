from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.demo_data import DEMO_PERSONAS
from app.denial_safety import denial_safety_findings, structural_assertion_demotion
from app.main import create_app
from app.settings import Settings
from app.unauthorized_signals import is_explicit_unauthorized_assertion, resolve_positive_propositions


# RF2 repair families. Wording is family-level development material written for
# these tests, not RF1Z fresh-probe text. Each entry names the denial-safety family
# that must license it.
_FAMILY_POSITIVES = [
    # P1. passive or quasi-passive depletion of the customer's account, card, or funds
    ("rf2_passive_depletion", "Mis ahorros fueron robados de la cuenta y yo no hice ningún retiro."),
    ("rf2_passive_depletion", "Fue vaciado mi saldo completo sin que yo lo autorizara."),
    ("rf2_passive_depletion", "Se retiraron todos mis ahorros mientras estaba de viaje."),
    ("rf2_passive_depletion", "Meu salário foi desviado da conta sem eu autorizar."),
    ("rf2_passive_depletion", "Foram sacadas todas as minhas economias, eu não saquei nada."),
    ("rf2_depleted_state", "Minha conta corrente amanheceu zerada e ninguém da minha família mexeu."),
    ("rf2_depleted_state", "Mi tarjeta prepago apareció en cero y yo no la usé."),
    ("rf2_depleted_state", "Minhas duas contas amanheceram zeradas e eu não fiz nenhum saque."),
    # P2. Spanish clitic drain of money named earlier
    ("rf2_clitic_drain", "Tenía la quincena en la cuenta y me la sacaron completa."),
    ("rf2_clitic_drain", "Ahorré dinero por meses y anoche me lo robaron de la cuenta."),
    ("rf2_clitic_drain", "Guardaba mis fondos en el banco y me los retiraron sin explicación."),
    ("rf2_clitic_drain", "Había plata en la tarjeta y alguien me la quitó."),
    # P3. ongoing, habitual, or present use of the customer's account or card
    ("rf2_ongoing_use", "Vienen usando mi tarjeta para comprar en internet desde hace una semana."),
    ("rf2_ongoing_use", "Un extraño está utilizando mi cuenta para hacer transferencias."),
    ("rf2_ongoing_use", "Alguien que no conozco usa mi tarjeta para pagar suscripciones."),
    ("rf2_ongoing_use", "Estão usando o meu cartão em sites que eu não conheço, não fui eu."),
    ("rf2_ongoing_use", "Uma pessoa que eu não conheço está usando minha conta para fazer Pix."),
    ("rf2_ongoing_use", "Vivem usando meus cartões para comprar, sem minha autorização."),
    # P4. fronted lack of authorization or consent
    ("rf2_fronted_non_consent", "Sin mi autorización, retiraron el saldo de la cuenta."),
    ("rf2_fronted_non_consent", "Sin que yo lo supiera, hicieron un pago con la tarjeta."),
    ("rf2_fronted_non_consent", "Sin haberlo pedido yo, gastaron todo el dinero de la tarjeta."),
    ("rf2_fronted_non_consent", "Sem minha autorização, tiraram o dinheiro da conta."),
    ("rf2_fronted_non_consent", "Sem que eu soubesse, transferiram o saldo para outra conta."),
    ("rf2_fronted_non_consent", "Sem o meu consentimento, alguém fez uma compra com o cartão."),
    # P5. money taken from several of the customer's cards or accounts
    ("rf2_plural_instrument_drain", "Me robaron dinero de las dos tarjetas que tengo."),
    ("rf2_plural_instrument_drain", "Sacaron plata de mis cuentas sin que yo diera permiso."),
    ("rf2_plural_instrument_drain", "Tiraram dinheiro dos meus dois cartões sem minha permissão."),
    ("rf2_plural_instrument_drain", "Alguien sacó todo de mis tarjetas."),
    # P6. no-money or ruin idioms with account-drain context
    ("rf2_ruin_idiom", "Me dejaron en la calle: alguien vació mi cuenta."),
    ("rf2_ruin_idiom", "Me deixaram na miséria, sumiu tudo da conta e eu não fiz nenhum saque."),
    ("rf2_no_money_state", "Desperté sin un centavo en la cuenta y yo no retiré nada."),
    ("rf2_no_money_state", "Fiquei sem nada na conta porque alguém sacou tudo sem minha permissão."),
    ("rf2_no_money_state", "Quedé sin plata en la tarjeta: me sacaron todo sin preguntarme."),
]

_RF2_FAMILY_NAMES = {
    "rf2_passive_depletion",
    "rf2_depleted_state",
    "rf2_clitic_drain",
    "rf2_ongoing_use",
    "rf2_fronted_non_consent",
    "rf2_plural_instrument_drain",
    "rf2_ruin_idiom",
    "rf2_no_money_state",
}

# Near misses for the RF2 families, each with the blocker that must name it.
_NAMED_NEGATIVES = [
    ("Mi saldo fue retirado por mi esposa mientras yo estaba de viaje.", "named_actor"),
    ("Mis ahorros fueron vaciados por las comisiones y yo no saqué nada.", "post_verbal_cause"),
    ("Tenía mis ahorros en la cuenta y mis hijos me los sacaron para la matrícula.", "named_actor"),
    ("Meus pais estão usando a minha conta para pagar o aluguel.", "overt_subject"),
    ("Si alguien está usando mi tarjeta sin mi permiso, ¿qué hago?", "conditional_protasis"),
    ("¿Están usando mi tarjeta para comprar en tiendas?", "interrogative_scope"),
    ("Sin que yo lo pidiera, me transfirieron el reembolso a la cuenta.", "incoming_transfer"),
    ("Mis hijos sacaron dinero de mis dos tarjetas con mi permiso.", "authorized_third_party"),
    ("Si me sacaron dinero de mis dos cuentas, ¿qué hago?", "conditional_protasis"),
    ("Me sacaron dinero de mis tres tarjetas, pero ya me lo devolvieron.", "resolved_or_recognized"),
    ("Las comisiones me dejaron en la ruina, ¿pueden revisar la tarifa?", "no_activity_anchor"),
    ("Quedé sin un peso en la cuenta después de pagar el arriendo.", "no_activity_anchor"),
    ("Mis ahorros fueron transferidos a la cuenta nueva como pedí.", "no_activity_anchor"),
    ("Tenía el celular en la mesa y me lo robaron en el bus; ¿cómo bloqueo la app?", "no_activity_anchor"),
]

# Benign controls the RF2 families must not license at all.
_BENIGN = [
    "Mis ahorros fueron retirados por mí para comprar la casa.",
    "Minha poupança foi zerada pelo banco por causa de um bloqueio judicial.",
    "Mi cuenta de nómina quedó en cero por las comisiones de este mes.",
    "Meu saldo foi zerado porque paguei a fatura inteira.",
    "Mis dos cuentas quedaron en cero cuando las cerré.",
    "Mi cuenta amaneció vacía, ¿me pueden decir por qué?",
    "Mis ahorros se los presté a mi hermano.",
    "Si me los sacan de la cuenta, ¿el banco responde?",
    "Mi esposa viene usando mi tarjeta para comprar el mercado, con mi permiso.",
    "Estoy usando mi cuenta para pagar los servicios.",
    "Mis clientes usan mi cuenta para depositarme los pagos.",
    "Como evitar que estranhos usem minha conta para fazer Pix?",
    "Con mi autorización, retiraron el saldo de la cuenta para el pago del crédito.",
    "Sin mi autorización no pueden sacar dinero de la cuenta, ¿verdad?",
    "Sem que eu pedisse, me depositaram o salário na conta.",
    "Sin mi autorización, mi esposo sacó dinero de la cuenta.",
    "Saqué dinero de mis dos cuentas para pagar la matrícula.",
    "Quero tirar dinheiro dos meus dois cartões de crédito, como faço?",
    "Me dejaron en la calle cuando cerró la empresa; ¿puedo pausar el crédito?",
    "Fiquei sem nada na conta depois das compras do mês.",
    "Me quedé sin plata este mes, ¿puedo diferir la cuota?",
    "Me dejaron limpio en el casino, ja.",
]

# B1. Non-recognition of the app, its version, or its interface after an adverb or
# navigation question is not a report, including when the resolver asserts it.
_INTERFACE_NONRECOGNITION = [
    "Depois da atualização não reconheço mais a tela; onde ficam os cartões?",
    "Con la nueva versión ya no reconozco el menú; ¿dónde está la sección de tarjetas?",
    "No reconozco bien la nueva app; ¿cómo llego a mis cuentas?",
    "Não reconheço mais o aplicativo, onde fica a área de cartões?",
    "Não reconheço mais o menu de pagamentos depois da atualização.",
]
# App- or menu-framed non-recognition of an activity stays a report.
_RECOGNITION_REPORTS = [
    "Depois da atualização não reconheço mais o menu e apareceu uma compra que eu não fiz.",
    "No reconozco el menú nuevo ni este cargo de la tarjeta.",
    "Não reconheço esse pagamento que apareceu no aplicativo novo.",
    "No reconozco ya la app y hay un retiro que no hice.",
]


@pytest.mark.parametrize(("family", "message"), _FAMILY_POSITIVES)
def test_rf2_family_positives_are_unauthorized_assertions(family: str, message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True
    assert any(f.family == family and f.asserted for f in denial_safety_findings(message))


@pytest.mark.parametrize(("message", "blocker"), _NAMED_NEGATIVES)
def test_rf2_near_misses_are_blocked_by_name(message: str, blocker: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False
    findings = [f for f in denial_safety_findings(message) if f.family in _RF2_FAMILY_NAMES]
    assert findings and all(not f.asserted for f in findings)
    assert any(f.blocked_by == blocker for f in findings)


@pytest.mark.parametrize("message", _BENIGN)
def test_rf2_benign_controls_are_not_reports(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False
    assert not any(
        f.asserted for f in denial_safety_findings(message) if f.family in _RF2_FAMILY_NAMES
    )


@pytest.mark.parametrize("message", _INTERFACE_NONRECOGNITION)
def test_rf2_interface_nonrecognition_is_not_a_report(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False
    recognition = [f for f in denial_safety_findings(message) if f.family == "non_recognition"]
    assert not any(f.asserted for f in recognition)


@pytest.mark.parametrize("message", _RECOGNITION_REPORTS)
def test_rf2_activity_nonrecognition_stays_a_report(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True


def test_rf2_structural_interface_demotion_is_scoped_to_the_proposition() -> None:
    message = "Depois da atualização não reconheço mais a tela; onde ficam os cartões?"
    propositions = [
        p for language in ("es", "pt") for p in resolve_positive_propositions(message, language)
    ]
    assert propositions
    assert all(
        structural_assertion_demotion(message, p.source_start, p.source_end)
        == "interface_nonrecognition"
        for p in propositions
        if p.mode == "assertive"
    )
    report = "Não reconheço mais o menu nem a compra de ontem."
    assert is_explicit_unauthorized_assertion(report) is True


def test_rf2_sin_mask_keeps_a_real_conditional() -> None:
    message = "Si alguien está usando mi tarjeta sin mi permiso, ¿qué hago?"
    assert is_explicit_unauthorized_assertion(message) is False
    findings = [f for f in denial_safety_findings(message) if f.family == "rf2_ongoing_use"]
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


# One report per RF2 family and language.
_HTTP_REPORTS = [
    ("lucia", "Mis ahorros fueron robados de la cuenta y yo no hice ningún retiro."),
    ("rafael", "Minha conta corrente amanheceu zerada e ninguém da minha família mexeu."),
    ("lucia", "Tenía la quincena en la cuenta y me la sacaron completa."),
    ("lucia", "Un extraño está utilizando mi cuenta para hacer transferencias."),
    ("rafael", "Uma pessoa que eu não conheço está usando minha conta para fazer Pix."),
    ("lucia", "Sin que yo lo supiera, hicieron un pago con la tarjeta."),
    ("rafael", "Sem minha autorização, tiraram o dinheiro da conta."),
    ("lucia", "Me robaron dinero de las dos tarjetas que tengo."),
    ("rafael", "Tiraram dinheiro dos meus dois cartões sem minha permissão."),
    ("lucia", "Me dejaron en la calle: alguien vació mi cuenta."),
    ("rafael", "Fiquei sem nada na conta porque alguém sacou tudo sem minha permissão."),
]


@pytest.mark.parametrize(("persona", "message"), _HTTP_REPORTS)
@pytest.mark.parametrize("reference", ["owned", "none", "amount", "foreign", "unowned"])
def test_rf2_reports_escalate_bound_to_session_without_disclosure(
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
        ("rafael", "Depois da atualização não reconheço mais a tela; onde ficam os cartões?"),
        ("lucia", "Con la nueva versión ya no reconozco el menú; ¿dónde está la sección de tarjetas?"),
        ("lucia", "Mis ahorros fueron retirados por mí para comprar la casa."),
        ("rafael", "Meus pais estão usando a minha conta para pagar o aluguel."),
        ("lucia", "Quedé sin un peso en la cuenta después de pagar el arriendo. Es la transacción DEMO-ES-1001."),
    ],
)
def test_rf2_benign_turns_create_no_ticket(tmp_path, persona, message) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, message)
    assert body["route"] != "ESCALATE"
    assert body.get("escalation_ticket_id") is None
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(session["tenant_id"]) == []
