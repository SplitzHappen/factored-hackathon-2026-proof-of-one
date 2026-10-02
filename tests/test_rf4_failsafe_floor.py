"""RF4 B-HYBRID fail-safe escalation floor.

The authoritative detector is unchanged; the floor adds escalations only when it
is silent, only on a denial / non-consent cue next to a money / instrument /
account mention, only through one centralized guard table, and always with the
distinct reason code ``possible_unauthorized_activity``.

Wording here is builder-written development material for these tests.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.demo_data import DEMO_PERSONAS
from app.failsafe_escalation import failsafe_findings, is_failsafe_escalation
from app.interpretation import InterpretationService
from app.main import create_app
from app.policy import route_policy
from app.schemas import (
    ModelInterpretation,
    PolicyInput,
    PolicyIntent,
    PolicyReason,
    RouteDecision,
)
from app.settings import Settings
from app.unauthorized_signals import is_explicit_unauthorized_assertion


def _escalates(text: str) -> bool:
    return is_explicit_unauthorized_assertion(text) or is_failsafe_escalation(text)


# ------------------------------------------------------------------ positives

# Reports the authoritative detector is silent on; the floor must carry them.
_FLOOR_ONLY_REPORTS = [
    "Me llegó el extracto con retiros en un cajero de otra ciudad; yo nunca estuve allá.",
    "Debitaram um empréstimo na minha conta sem eu ter pedido nada.",
    "Estão cobrando um seguro no meu cartão sem eu ter contratado.",
    "Toda quinzena some um valor da minha poupança sem nenhuma movimentação minha.",
]

# Genuine reports, whichever path catches them.
_REPORTS = _FLOOR_ONLY_REPORTS + [
    "Yo no di permiso para ningún débito y aun así me descontaron plata de la cuenta de ahorros.",
    "Mi saldo bajó a la mitad sin que yo autorizara ningún movimiento.",
    "Fizeram um Pix da minha conta sem a minha autorização.",
    "Nunca dei permissão para esse débito automático na minha conta.",
    "Essa transferência foi outra pessoa que fez, não eu.",
    "Hoy revisé la cuenta y el bono ya no está; nadie de la casa lo tocó.",
]

# Genuine reports framed by something a guard looks for; the guard must not
# swallow the report.
_GUARD_FRAMED_REPORTS = [
    # interface frame
    "No encuentro el menú de movimientos en la app nueva, pero alguien retiró plata de mi cuenta sin mi permiso.",
    "No ubico la opción de extractos tras la actualización, pero sí vi que sacaron plata sin mi permiso.",
    # prevention question after the event
    "Alguien usó mi tarjeta sin mi autorización; ¿cómo evito que vuelva a pasar?",
    "Fizeram um saque da minha conta sem minha autorização; como faço para bloquear o cartão?",
    # lawful cause next to a separate theft clause
    "Me embargaron la cuenta de nómina y además hicieron una compra con mi tarjeta que yo no hice.",
    "Teve um bloqueio judicial na minha conta e, além disso, alguém fez um Pix que eu não autorizei.",
    # failure to pay caused by the theft
    "No pude pagar la cuota porque me sacaron el dinero de la cuenta sin mi permiso.",
    "Não consegui pagar a fatura porque tiraram dinheiro da minha conta sem eu saber.",
]


@pytest.mark.parametrize("text", _FLOOR_ONLY_REPORTS)
def test_floor_carries_reports_the_detector_misses(text: str) -> None:
    assert not is_explicit_unauthorized_assertion(text)
    assert is_failsafe_escalation(text)


@pytest.mark.parametrize("text", _REPORTS + _GUARD_FRAMED_REPORTS)
def test_reports_escalate(text: str) -> None:
    assert _escalates(text)


# ------------------------------------------------------------------ negatives by class

# Lawful / administrative causes, including garnishment, embargo, tax authority,
# court order, fees, interest, collections and bank-initiated debits. Several carry
# an explicit non-consent cue so that the lawful-cause guard is exercised.
_LAWFUL_CAUSE = [
    ("Sin mi autorización me descontaron la cuota de manejo de la tarjeta; ¿por qué la cobran?", "lawful_cause"),
    ("No autoricé el débito, pero el banco dice que fue el cobro de intereses de mora; ¿es correcto?", "lawful_cause"),
    ("El banco me debitó la deuda de la tarjeta de la cuenta de ahorros sin mi consentimiento; ¿pueden hacer eso?", "lawful_cause"),
    ("Penhoraram meu salário por uma dívida antiga sem minha autorização; posso contestar?", "lawful_cause"),
    ("O banco descontou a parcela do empréstimo da minha conta sem eu autorizar; está certo?", "lawful_cause"),
    ("Houve um bloqueio judicial na minha conta e não reconheço o processo; onde vejo?", "lawful_cause"),
    ("Me embargaron el sueldo por orden judicial sin mi consentimiento; ¿cuánto me retienen?", "lawful_cause"),
    ("La DIAN me retuvo plata de la cuenta sin mi autorización por un impuesto pendiente.", "lawful_cause"),
    ("A Receita Federal bloqueou dinheiro da minha conta sem minha permissão; como consulto?", "lawful_cause"),
    ("Mi cuenta fue embargada por la DIAN y no autoricé ningún retiro; ¿qué hago?", "lawful_cause"),
    ("O juiz mandou penhorar o saldo da minha conta sem eu autorizar; como recorro?", "lawful_cause"),
    ("Me cobraron comisión por el retiro en otro cajero sin mi permiso.", "lawful_cause"),
    ("Cobraram juros do cheque especial sem minha autorização.", "lawful_cause"),
]
_LAWFUL_NO_CUE = [
    "La DIAN me embargó la cuenta de ahorros sin avisarme; ¿dónde veo la orden?",
    "Me retuvieron el salario por una orden judicial de alimentos.",
    "Reversaron un contracargo en mi tarjeta y el saldo quedó negativo; ¿qué significa?",
    "A Receita Federal bloqueou dinheiro da minha conta; como consulto o motivo?",
]

_APP_INTERFACE = [
    ("No reconozco el nuevo menú de la app; ¿dónde están mis tarjetas?", "interface"),
    ("Desde la actualización no reconozco la pantalla de pagos; ¿cómo programo uno?", "interface"),
    ("Não reconheço o novo layout do aplicativo; onde vejo o saldo da conta?", "interface"),
    ("Depois da atualização não reconheço os ícones; qual é o de transferências?", "interface"),
    ("La pantalla de inicio cambió y no la reconozco; ¿dónde veo mis transferencias?", "interface"),
]
_APP_NO_CUE = [
    "La app no reconoce mi tarjeta cuando intento inscribirla para pagos.",
    "No puedo entrar a mi cuenta, el token no me llega.",
    "Olvidé la contraseña de la banca en línea y no me deja ver el saldo.",
    "O app não reconhece meu cartão na hora de cadastrar no Pix.",
    "Não consigo vincular minha conta ao aplicativo novo.",
]

_PREVENTION_PROCEDURE = [
    ("¿Cómo evito que alguien use mi tarjeta sin mi autorización cuando viajo?", "worry_or_purpose"),
    ("¿El seguro de la tarjeta cubre compras no autorizadas?", "prevention_question"),
    ("Para una clase de educación financiera: ¿cómo se reporta un débito no autorizado?", "prevention_question"),
    ("Si alguien saca plata de mi cuenta sin mi permiso, ¿qué debo hacer?", "hypothetical"),
    ("Sin mi autorización nadie puede cambiar el límite de la tarjeta, ¿cierto?", "prevention_question"),
    ("Sin mi permiso, ¿pueden usar la tarjeta para cobrar la cuota?", "prevention_question"),
    ("Como faço para que ninguém faça Pix da minha conta sem minha permissão?", "worry_or_purpose"),
    ("O seguro do cartão cobre compras não autorizadas no exterior?", "prevention_question"),
    ("Se um dia usarem meu cartão sem minha autorização, quem eu procuro?", "hypothetical"),
    ("¿Es un uso no autorizado si uso la tarjeta en el exterior sin avisarle al banco?", "hypothetical"),
]

_FAILURE_TO_PAY = [
    ("No hice el pago de la tarjeta a tiempo; ¿cuánto me cobran de mora?", "failure_to_act"),
    ("Yo no realicé el pago del préstamo porque se me olvidó; ¿qué hago?", "failure_to_act"),
    ("Eu não fiz o pagamento da fatura porque esqueci; ainda dá tempo?", "failure_to_act"),
    ("Todavía no hice la transferencia del arriendo; ¿hasta qué hora puedo?", "failure_to_act"),
]
_FAILURE_TO_PAY_NO_CUE = [
    "Mi pago fue rechazado por fondos insuficientes; ¿lo puedo reintentar?",
    "No pude hacer la transferencia porque no tengo fondos en la cuenta.",
    "Meu Pix não foi porque estou sem saldo na conta.",
    "Não consegui fazer o pagamento do cartão por falta de limite.",
]

_OWN_ACTIVITY = [
    ("Me transfirieron dinero a la cuenta sin que yo lo pidiera; ¿de quién es?", "incoming"),
    ("Recebi um Pix de alguém que não conheço sem eu pedir; o que faço?", "incoming"),
    ("Mi cuenta fue vaciada por mi hermano sin mi permiso.", "named_actor"),
    ("Mi pago en el supermercado salió como no autorizado y me rechazaron la tarjeta.", "declined_own"),
    ("No he usado la tarjeta en meses, ¿sigue activa?", "no_event"),
    ("Me robaron los datos de la tarjeta y no fui yo, pero no hicieron ninguna compra con ellos.", "no_transaction"),
]


def _blockers(text: str) -> set[str | None]:
    return {finding.blocked_by for finding in failsafe_findings(text)}


@pytest.mark.parametrize(
    ("text", "guard"),
    _LAWFUL_CAUSE + _APP_INTERFACE + _PREVENTION_PROCEDURE + _FAILURE_TO_PAY + _OWN_ACTIVITY,
)
def test_guard_blocks_each_benign_class(text: str, guard: str) -> None:
    assert not is_failsafe_escalation(text)
    assert guard in _blockers(text)


@pytest.mark.parametrize("text", _LAWFUL_NO_CUE + _APP_NO_CUE + _FAILURE_TO_PAY_NO_CUE)
def test_benign_text_without_a_cue_never_reaches_the_floor(text: str) -> None:
    assert not is_failsafe_escalation(text)
    assert all(finding.blocked_by is not None for finding in failsafe_findings(text))


# ------------------------------------------------------------------ trigger contract


def test_cue_without_money_or_account_mention_does_not_fire() -> None:
    assert failsafe_findings("No fui yo, te lo juro.") == ()
    assert failsafe_findings("Sin mi permiso entraron a mi casa.") == ()


def test_money_mention_without_cue_does_not_fire() -> None:
    assert failsafe_findings("Quiero saber el saldo de mi cuenta de ahorros.") == ()
    assert not is_failsafe_escalation("Me llegó la transferencia de mi hermano.")


def test_affirmative_si_is_not_a_conditional() -> None:
    text = "No ubico el menú de cuentas, pero sí vi que alguien sacó plata sin mi permiso."
    assert is_failsafe_escalation(text)
    conditional = "No ubico el menú de cuentas, pero si alguien saca plata sin mi permiso, ¿qué hago?"
    assert not is_failsafe_escalation(conditional)


def test_floor_is_deterministic() -> None:
    corpus = [text for text, _ in _LAWFUL_CAUSE + _PREVENTION_PROCEDURE] + _REPORTS
    assert [failsafe_findings(t) for t in corpus] == [failsafe_findings(t) for t in corpus]


# ------------------------------------------------------------------ monotonicity / labelling


@pytest.mark.parametrize("text", _REPORTS + _GUARD_FRAMED_REPORTS + [t for t, _ in _LAWFUL_CAUSE])
def test_floor_is_only_consulted_when_the_detector_is_silent(text: str) -> None:
    detected = is_explicit_unauthorized_assertion(text)
    possible = InterpretationService._failsafe_floor(text, detected)
    assert not (detected and possible)
    assert possible == ((not detected) and is_failsafe_escalation(text))


def _policy(**overrides) -> PolicyInput:
    values = dict(
        intent=PolicyIntent.TRANSACTION_LOOKUP,
        unauthorized_activity_asserted=False,
        possible_unauthorized_activity=False,
        ownership_verified=True,
        trusted_record_found=True,
        trusted_data_conflict=False,
        excluded_relationship_required=False,
        ambiguous_transaction_match=False,
        required_parameters_missing=False,
    )
    values.update(overrides)
    return PolicyInput(**values)


def test_router_labels_floor_escalations_distinctly() -> None:
    floor = route_policy(_policy(possible_unauthorized_activity=True))
    assert floor.route is RouteDecision.ESCALATE
    assert floor.reason_codes == [PolicyReason.POSSIBLE_UNAUTHORIZED_ACTIVITY]
    assert floor.mandatory_escalation and not floor.safe_to_answer

    explicit = route_policy(
        _policy(unauthorized_activity_asserted=True, possible_unauthorized_activity=True)
    )
    assert explicit.reason_codes == [PolicyReason.UNAUTHORIZED_ACTIVITY_REPORTED]

    ordinary = route_policy(_policy())
    assert ordinary.route is RouteDecision.ANSWER


def test_policy_input_defaults_keep_prior_behaviour() -> None:
    legacy = PolicyInput(
        intent=PolicyIntent.TRANSACTION_LOOKUP,
        unauthorized_activity_asserted=False,
        ownership_verified=True,
        trusted_record_found=True,
        trusted_data_conflict=False,
        excluded_relationship_required=False,
        ambiguous_transaction_match=False,
        required_parameters_missing=False,
    )
    assert legacy.possible_unauthorized_activity is False
    assert route_policy(legacy).route is RouteDecision.ANSWER


def test_model_cannot_set_the_floor_signal() -> None:
    schema = ModelInterpretation.model_json_schema()
    assert "possible_unauthorized_activity" not in schema["properties"]
    with pytest.raises(Exception):
        ModelInterpretation.model_validate(
            {
                "intent": "transaction_lookup",
                "unauthorized_activity_asserted": False,
                "possible_unauthorized_activity": True,
            }
        )


# ------------------------------------------------------------------ HTTP: binding, tenant, disclosure

_OWNED = {"lucia": "DEMO-ES-1001", "rafael": "DEMO-PT-2001"}
_FOREIGN = {"lucia": "DEMO-PT-2001", "rafael": "DEMO-ES-1001"}
_UNOWNED = {"lucia": "DEMO-ES-9999", "rafael": "DEMO-PT-9999"}
_LANGUAGE = {"lucia": "es", "rafael": "pt"}
_FOREIGN_MARKERS = {
    "DEMO-PT-2001": ("Mercado Bairro", "219.90", "219,90", "BRL"),
    "DEMO-ES-1001": ("Mercado Central", "125000", "125.000", "COP"),
}
_SUFFIX = {
    "lucia": {"owned": " Es la transacción {ref}.", "none": "", "foreign": " Es la transacción {ref}.",
              "unowned": " Es la transacción {ref}."},
    "rafael": {"owned": " É a transação {ref}.", "none": "", "foreign": " É a transação {ref}.",
               "unowned": " É a transação {ref}."},
}
_REFERENCE = {"owned": _OWNED, "foreign": _FOREIGN, "unowned": _UNOWNED}
_STATUS_WORDS = ("aprobada", "aprovada", "pendiente", "pendente", "rechazada", "recusada")
_HTTP_FLOOR_REPORTS = [
    ("lucia", "Me llegó el extracto con retiros en un cajero de otra ciudad; yo nunca estuve allá."),
    ("rafael", "Debitaram um empréstimo na minha conta sem eu ter pedido nada."),
]


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


@pytest.mark.parametrize(("persona", "message"), _HTTP_FLOOR_REPORTS)
@pytest.mark.parametrize("reference", ["owned", "none", "foreign", "unowned"])
def test_floor_escalation_is_bound_labelled_and_discloses_nothing(
    tmp_path, persona, message, reference
) -> None:
    client, context = _client(tmp_path)
    ref = _REFERENCE[reference][persona] if reference in _REFERENCE else ""
    session, body = _turn(client, persona, message + _SUFFIX[persona][reference].format(ref=ref))

    assert body["route"] == "ESCALATE"
    assert body["reason_codes"] == ["possible_unauthorized_activity"]
    assert body["transactions"] == [] and body["products"] == []
    assert body["clarification_transaction_ids"] == []
    ticket_id = UUID(body["escalation_ticket_id"])
    resolved = context.store.resolve_verified_escalation_context(ticket_id)
    assert resolved is not None
    assert resolved.reason_code == "possible_unauthorized_activity"
    assert "posible" in resolved.summary or "possível" in resolved.summary
    assert str(resolved.session.session_id) == session["session_id"]
    assert resolved.session.tenant_id == session["tenant_id"]
    assert resolved.session.customer_id == DEMO_PERSONAS[persona].customer_id
    if reference == "owned":
        assert resolved.transaction_id == _OWNED[persona]
    else:
        assert resolved.transaction_id is None

    blob = str(body) + (resolved.summary or "")
    for markers in _FOREIGN_MARKERS.values():
        assert not any(marker in blob for marker in markers)
    lowered = body["response_text"].casefold()
    assert not any(status in lowered for status in _STATUS_WORDS)

    other, _ = _turn(client, "rafael" if persona == "lucia" else "lucia", "Hola")
    assert ticket_id not in context.store.list_verified_escalation_ticket_ids_for_tenant(
        other["tenant_id"]
    )


def test_explicit_report_keeps_its_original_reason_code(tmp_path) -> None:
    client, _ = _client(tmp_path)
    _, body = _turn(client, "lucia", "No reconozco este cargo de mi tarjeta.")
    assert body["route"] == "ESCALATE"
    assert body["reason_codes"] == ["unauthorized_activity_reported"]


@pytest.mark.parametrize(
    ("persona", "message"),
    [
        ("lucia", "Sin mi autorización me descontaron la cuota de manejo; ¿por qué la cobran?"),
        ("rafael", "Penhoraram meu salário por uma dívida antiga sem minha autorização; posso contestar?"),
        ("lucia", "No reconozco el nuevo menú de la app; ¿dónde están mis tarjetas?"),
        ("rafael", "O seguro do cartão cobre compras não autorizadas no exterior?"),
        ("lucia", "Mi pago fue rechazado por fondos insuficientes; ¿lo puedo reintentar?"),
    ],
)
def test_benign_turns_get_no_floor_ticket(tmp_path, persona, message) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, message)
    assert "possible_unauthorized_activity" not in (body["reason_codes"] or [])
    if body["route"] != "ESCALATE":
        assert context.store.list_verified_escalation_ticket_ids_for_tenant(
            session["tenant_id"]
        ) == []
