from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import app.unauthorized_signals as unauthorized_signals
from app.bootstrap import build_app_context
from app.denial_safety import denial_safety_assertion, denial_safety_findings
from app.main import create_app
from app.settings import Settings


# Explicit first-person denials the structural resolver leaves silent or marks
# QUESTIONED. The layer must turn each into an unauthorized-activity assertion.
_LAYER_POSITIVES = [
    "Aparece un retiro que no solicité.",
    "¿Pueden revisar el cargo que no reconozco?",
    "Apareceu um saque que eu não solicitei.",
    "Podem verificar a cobrança que eu não reconheço?",
    "Cobraram uma compra que não reconheço, podem ajudar?",
    "Vi un cobro raro. No es mío.",
    "Vi uma cobrança estranha. Não é minha.",
    "Nadie me avisó y desconozco la operación registrada ayer.",
    "Não é verdade que eu tenha feito esse débito.",
    "No es verdad que yo haya autorizado ese cargo.",
    "Ninguna de las compras de anoche, ni siquiera la primera, las hice.",
    "Nenhum dos saques de hoje fui eu que fiz.",
    "El giro de esta mañana no fue realizado por mí.",
    "O boleto pago hoje não foi efetuado por mim.",
    "¿Por qué me cobraron el consumo si yo no compré nada?",
    "En este caso no reconozco el cargo de ayer.",
    "No reconozco un cargo que me apareció, me ayudan?",
    "No lo hice yo, pues estaba de viaje; es un pago raro.",
]

# Hard negatives that share the layer's cue vocabulary. The layer itself must not
# license any of them, whatever the structural resolver decides.
_LAYER_NEGATIVES = [
    "Si no reconozco un cargo, ¿qué debo hacer?",
    "¿Qué pasa si no autoricé una compra?",
    "Se eu não reconhecer uma compra, o que faço?",
    "E se eu não reconheço um lançamento?",
    "¿No reconozco este cargo o sí?",
    "Não reconheço essa compra?",
    "Pensé que no había hecho esa compra, pero sí la hice.",
    "Achei que não tinha feito esse Pix, mas fui eu mesmo.",
    "Mi vecina dice que no reconoce un cargo en su tarjeta.",
    "Meu irmão disse que não fez uma transferência.",
    "No es que no reconozca el cargo, solo quiero el detalle.",
    "Não é que eu não reconheça a compra, só quero o comprovante.",
    "Creo que no hice esa compra, déjame revisar.",
    "Acho que não fiz esse pagamento, vou conferir.",
    "Todavía no hice la transferencia, ¿puedo hacerla hoy?",
    "Ainda não fiz o pagamento do boleto.",
    "No hice la transferencia porque no tenía saldo.",
    "Não fiz o Pix porque o app travou.",
    "No reconozco el nombre del comercio en este cargo.",
    "Não reconheço o nome da loja nessa compra.",
    "No desconozco este cargo.",
    "Não desconheço essa compra.",
    "No pagué la cuota del mes, ¿hay recargo?",
    "Reconozco todos los cargos de este mes.",
    "Mi esposa usó mi tarjeta con mi permiso para la compra.",
    "¿Cómo sé si un cargo es fraude?",
    "Como me protejo de transações não autorizadas?",
    "No reconozco este número de teléfono que me llamó.",
    "No autoricé que me enviaran publicidad.",
    "Esta cuenta no es mía, es de mi esposo.",
    "Esse cartão não é meu.",
    "Si uno no reconoce un cargo, el banco lo investiga.",
    "Caso eu não reconheça uma compra, o que faço?",
]


@pytest.mark.parametrize("message", _LAYER_POSITIVES)
def test_rf1k_explicit_denials_are_unauthorized_assertions(message: str) -> None:
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is True


@pytest.mark.parametrize("message", _LAYER_NEGATIVES)
def test_rf1k_layer_does_not_license_scoped_or_unanchored_cues(message: str) -> None:
    assert denial_safety_assertion(message, frozenset()) is False
    assert not any(finding.asserted for finding in denial_safety_findings(message))


@pytest.mark.parametrize(
    "mode",
    [
        "hypothetical",
        "uncertain",
        "information_request",
        "descriptor_clarification",
        "authorized_third_party",
        "retracted",
        "reported_prior_belief",
    ],
)
def test_rf1k_structural_non_assertive_modes_veto_the_layer(mode: str) -> None:
    message = "Aparece un retiro que no solicité."
    assert denial_safety_assertion(message, frozenset()) is True
    assert denial_safety_assertion(message, frozenset({mode})) is False
    assert denial_safety_assertion(message, frozenset({"questioned", mode})) is False


def test_rf1k_questioned_mode_is_rechecked_rather_than_vetoing() -> None:
    assert denial_safety_assertion(
        "¿Por qué me cobraron el consumo si yo no compré nada?",
        frozenset({"questioned"}),
    ) is True
    assert denial_safety_assertion(
        "¿No reconozco este cargo o sí?",
        frozenset({"questioned"}),
    ) is False


def test_rf1k_layer_never_consults_legacy_regex_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_legacy_regex(*_args, **_kwargs):
        raise AssertionError("legacy whole-message regex inventory was consulted")

    monkeypatch.setattr(unauthorized_signals, "_matches_any", fail_legacy_regex)

    assert unauthorized_signals.is_explicit_unauthorized_assertion(
        "Aparece un retiro que no solicité."
    ) is True
    assert unauthorized_signals.is_explicit_unauthorized_assertion(
        "Si no reconozco un cargo, ¿qué debo hacer?"
    ) is False


@pytest.mark.parametrize(
    ("message", "blocked_by"),
    [
        ("Si no reconozco un cargo, ¿qué debo hacer?", "conditional_protasis"),
        ("Não reconheço essa compra?", "interrogative_scope"),
        ("Achei que não fiz esse Pix, mas fui eu mesmo.", "prior_belief"),
        ("Acho que não fiz esse pagamento, vou conferir.", "uncertainty_hedge"),
        ("Todavía no hice la transferencia, ¿puedo hacerla hoy?", "not_yet_or_causal"),
        ("No reconozco el nombre del comercio en este cargo.", "descriptor_clarification"),
        ("No autoricé que me enviaran publicidad.", "no_activity_anchor"),
    ],
)
def test_rf1k_findings_record_the_blocking_reason(message: str, blocked_by: str) -> None:
    findings = denial_safety_findings(message)
    assert findings
    assert {finding.blocked_by for finding in findings} == {blocked_by}


def test_rf1k_short_follow_up_borrows_previous_sentence_anchor_only() -> None:
    (finding,) = denial_safety_findings("Vi un cobro raro. No es mío.")
    assert finding.asserted is True
    assert finding.anchor == "cobro"

    (unanchored,) = denial_safety_findings("Recibí un correo raro. No es mío.")
    assert unanchored.asserted is False
    assert unanchored.blocked_by == "no_activity_anchor"


# ---------------------------------------------------------------- HTTP matrix
_OWNED = {"lucia": "DEMO-ES-1001", "rafael": "DEMO-PT-2001"}
_FOREIGN = {"lucia": "DEMO-PT-2001", "rafael": "DEMO-ES-1001"}
_FOREIGN_MARKERS = {
    "DEMO-PT-2001": ("Mercado Bairro", "219.90", "219,90", "BRL"),
    "DEMO-ES-1001": ("Mercado Central", "125000", "125.000", "COP"),
}
_HTTP_CASES = [
    ("lucia", "es", "Se hizo un retiro {ref} de mi cuenta que yo no solicité.", "Se hizo un retiro de mi cuenta que yo no solicité."),
    ("rafael", "pt", "Foi feito um saque {ref} da minha conta que eu não pedi.", "Foi feito um saque da minha conta que eu não pedi."),
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


def _turn(client: TestClient, persona: str, language: str, message: str) -> tuple[dict, dict]:
    session = client.post(
        "/api/demo/sessions",
        json={"persona_id": persona, "language": language},
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
    assert body["clarification_transaction_ids"] == []
    ticket_id = UUID(body["escalation_ticket_id"])
    resolved = context.store.resolve_verified_escalation_context(ticket_id)
    assert resolved is not None
    assert str(resolved.session.session_id) == session["session_id"]
    assert resolved.session.tenant_id == session["tenant_id"]
    assert ticket_id in context.store.list_verified_escalation_ticket_ids_for_tenant(
        session["tenant_id"]
    )
    assert resolved.reason_code == "unauthorized_activity_reported"
    return resolved


@pytest.mark.parametrize(("persona", "language", "with_ref", "no_ref"), _HTTP_CASES)
def test_rf1k_owned_denial_escalates_with_owned_attachment(
    tmp_path, persona, language, with_ref, no_ref
) -> None:
    client, context = _client(tmp_path)
    owned = _OWNED[persona]
    session, body = _turn(client, persona, language, with_ref.format(ref=owned))
    resolved = _escalation_context(context, session, body)
    assert resolved.transaction_id == owned


@pytest.mark.parametrize(("persona", "language", "with_ref", "no_ref"), _HTTP_CASES)
def test_rf1k_foreign_denial_escalates_without_disclosure_or_attachment(
    tmp_path, persona, language, with_ref, no_ref
) -> None:
    client, context = _client(tmp_path)
    foreign = _FOREIGN[persona]
    session, body = _turn(client, persona, language, with_ref.format(ref=foreign))
    resolved = _escalation_context(context, session, body)
    assert resolved.transaction_id is None
    blob = str(body) + (resolved.summary or "")
    assert not any(marker in blob for marker in _FOREIGN_MARKERS[foreign])


@pytest.mark.parametrize(("persona", "language", "with_ref", "no_ref"), _HTTP_CASES)
def test_rf1k_unreferenced_denial_escalates_with_session_only_ticket(
    tmp_path, persona, language, with_ref, no_ref
) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, language, no_ref)
    resolved = _escalation_context(context, session, body)
    assert resolved.transaction_id is None


@pytest.mark.parametrize(
    ("persona", "language", "message"),
    [
        ("lucia", "es", "Pensé que no reconocía el pago {ref}, pero ya vi que es mío."),
        ("rafael", "pt", "Qual é o status do pagamento {ref}?"),
    ],
)
def test_rf1k_non_assertions_are_not_unauthorized_escalations(
    tmp_path, persona, language, message
) -> None:
    client, _ = _client(tmp_path)
    _, body = _turn(client, persona, language, message.format(ref=_OWNED[persona]))
    assert "unauthorized_activity_reported" not in body["reason_codes"]
