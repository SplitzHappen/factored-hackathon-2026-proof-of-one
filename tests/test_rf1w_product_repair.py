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


# RF1W repair families. Wording is family-level development material written for
# these tests, not RF1V fresh-probe text. Each entry names the denial-safety family
# that must license it.
_FAMILY_POSITIVES = [
    # 1. taken data used through a back-reference (U-P29 class)
    ("data_misuse_backref", "Clonaron los datos de mi tarjeta y los usaron para pagar un hotel."),
    ("data_misuse_backref", "Hackearon mis datos bancarios y con ellos hicieron un retiro."),
    ("data_misuse_backref", "Alguien robó mis datos y los usó para comprar boletos."),
    ("data_misuse_backref", "Furtaram meus dados e fizeram um saque com eles."),
    ("data_misuse_backref", "Vazaram os dados do meu cartão e os usaram para pagar boletos."),
    ("data_misuse_backref", "Alguém roubou meus dados e usou eles para fazer um pix."),
    # 2. impersonal activity using the customer's own account
    ("account_use", "Fizeram dois saques utilizando minha conta."),
    ("account_use", "Realizaram compras usando a minha conta corrente."),
    ("account_use", "Hicieron un retiro usando mi cuenta."),
    # 3. the customer's account drained by an impersonal or unnamed party
    ("account_drain", "Un desconocido me vació la cuenta sin mi autorización."),
    ("account_drain", "Me limpiaron la cuenta de ahorros el fin de semana."),
    ("account_drain", "Hackers vaciaron mi cuenta corriente."),
    ("account_drain", "Me dejaron la cuenta en cero de un día para otro."),
    ("account_drain", "Golpistas esvaziaram minha conta poupança."),
    ("account_drain", "Alguém limpou minha conta durante a madrugada."),
    ("account_drain", "Deixaram minha conta zerada ontem."),
]

_RF1W_FAMILY_NAMES = {"data_misuse_backref", "account_use", "account_drain"}

# Near misses for the RF1W families, each with the blocker that must name it.
_NAMED_NEGATIVES = [
    ("¿Qué pasa si alguien me vació la cuenta?", "conditional_protasis"),
    ("¿Alguien me vació la cuenta?", "interrogative_scope"),
    ("Os juros zeraram minha conta.", "overt_subject"),
    ("Las comisiones me vaciaron la cuenta este mes.", "overt_subject"),
    ("Meus pais fizeram uma compra usando minha conta.", "overt_subject"),
    ("Fizeram uma transferência para mim usando minha conta.", "incoming_transfer"),
    ("Hicieron el pago de mi sueldo usando mi cuenta.", "incoming_transfer"),
    ("Me vaciaron la cuenta pero ya me reintegraron todo.", "resolved_or_recognized"),
]

# Benign controls the RF1W families must not license at all.
_BENIGN = [
    "Vacié mi cuenta para pagar el semestre.",
    "Mi cuenta quedó vacía porque pagué el crédito.",
    "Zerei minha conta para investir.",
    "Minha conta está zerada porque paguei o aluguel.",
    "Limpiaron la cuenta de correo basura.",
    "Zeraram a conta de luz com desconto.",
    "Vaciaron la cuenta de mi empresa anterior cuando cerró.",
    "Tomaron mis datos para el sorteo y con ellos hicieron el pago del premio.",
    "Le di mis datos a la tienda y con ellos hicieron el cobro acordado.",
    "Robaron mis datos, pero no hicieron ninguna compra con ellos.",
    "Pegaram meus dados para criar um perfil falso numa rede social.",
    "Atualizei meus dados e usei eles para fazer o pagamento.",
    "Fiz uma transferência usando minha conta poupança.",
    "Como faço um pagamento usando minha conta no aplicativo?",
    "Não fizeram nenhuma compra usando minha conta.",
    "Mi carrito de compras está vacío.",
    "Si me vacían la cuenta, ¿el banco responde?",
    "Fizeram o estorno usando minha conta.",
]


@pytest.mark.parametrize(("family", "message"), _FAMILY_POSITIVES)
def test_rf1w_family_positives_are_unauthorized_assertions(family: str, message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True
    assert any(f.family == family and f.asserted for f in denial_safety_findings(message))


@pytest.mark.parametrize(("message", "blocker"), _NAMED_NEGATIVES)
def test_rf1w_near_misses_are_blocked_by_name(message: str, blocker: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False
    findings = [f for f in denial_safety_findings(message) if f.family in _RF1W_FAMILY_NAMES]
    assert findings and all(not f.asserted for f in findings)
    assert any(f.blocked_by == blocker for f in findings)



@pytest.mark.parametrize("message", _BENIGN)
def test_rf1w_benign_controls_are_not_reports(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False
    assert not any(
        f.asserted for f in denial_safety_findings(message) if f.family in _RF1W_FAMILY_NAMES
    )


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


# One report per RF1W family and language.
_HTTP_REPORTS = [
    ("lucia", "Hackearon mis datos y los usaron para pagar en una tienda en línea."),
    ("rafael", "Clonaram meus dados e fizeram compras com eles."),
    ("lucia", "Hicieron transferencias usando mi cuenta."),
    ("rafael", "Fiquei sabendo de um golpe e fizeram um saque utilizando minha conta."),
    ("lucia", "Alguien me vació la cuenta de ahorros sin mi consentimiento."),
    ("rafael", "Zeraram minha conta corrente sem eu saber."),
]


@pytest.mark.parametrize(("persona", "message"), _HTTP_REPORTS)
@pytest.mark.parametrize("reference", ["owned", "none", "amount", "foreign", "unowned"])
def test_rf1w_reports_escalate_bound_to_session_without_disclosure(
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
        ("lucia", "Vacié mi cuenta para pagar el semestre. Es la transacción DEMO-ES-1001."),
        ("rafael", "Fiz uma transferência usando minha conta. É a transação DEMO-PT-2001."),
        ("lucia", "Le di mis datos a la tienda y con ellos hicieron el cobro acordado."),
        ("rafael", "Os juros zeraram minha conta."),
    ],
)
def test_rf1w_benign_turns_create_no_ticket(tmp_path, persona, message) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, message)
    assert body["route"] != "ESCALATE"
    assert body.get("escalation_ticket_id") is None
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(session["tenant_id"]) == []
