from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import app.unauthorized_signals as unauthorized_signals
from app.bootstrap import build_app_context
from app.denial_safety import denial_safety_assertion, denial_safety_findings
from app.main import create_app
from app.settings import Settings


# RF1M follow-up families. Wording is family-level development material, not the
# RF1L fresh-probe text, so RF1L stays usable as evidence of what was repaired.
_FAMILY_POSITIVES = [
    # 1. clause-initial agency denial with a trailing coordinated clause
    ("non_performance", "Hay un cargo de anoche en mi tarjeta. No fui yo, y además tengo la tarjeta conmigo."),
    ("non_performance", "Apareceu um débito hoje cedo. Não fui eu, e o cartão está comigo."),
    # 2. first-person negated money movement pointing back at a movement
    ("non_movement", "Aparece una transferencia a otra cuenta. Yo no la mandé."),
    ("non_movement", "Hay un giro al exterior en mi cuenta. Yo no lo transferí."),
    ("non_movement", "Me sacaron plata del cajero y yo no toqué ese dinero."),
    ("non_movement", "Tem um Pix para um desconhecido. Eu não mandei."),
    ("non_movement", "Teve um saque de madrugada. Eu não saquei isso."),
    ("non_movement", "Zeraram minha conta e eu não mexi no saldo."),
    # 3. elliptical ownership denial over listed movements
    ("ownership_denial", "Revisé mis movimientos de ayer: tres compras en línea. Ninguna es mía."),
    ("ownership_denial", "Me llegaron varios cobros. Ninguno de ellos me pertenece."),
    ("ownership_denial", "Vi quatro lançamentos estranhos. Nenhum deles é meu."),
    ("ownership_denial", "Apareceram cobranças no cartão. Nenhuma me pertence."),
    # 4. emphatic / elliptical agency denial
    ("non_performance", "Hicieron un pago con mi tarjeta en otra ciudad. ¿Quién lo hizo? Yo desde luego que no."),
    ("non_performance", "Hubo un retiro raro anoche. Ese no fui yo."),
    ("non_performance", "Fizeram um Pix da minha conta. Quem fez? Eu com certeza não."),
    ("non_performance", "Teve uma compra estranha no cartão. Eu é que não fui."),
    ("non_performance", "De repente mi saldo bajó y no fui yo."),
    # 5. closed misspelling of the core reconocer stem
    ("non_recognition", "No reconosco ese cargo de ayer."),
]

# Near misses for the RF1M families. The layer must license none of them.
_FAMILY_NEGATIVES = [
    "Yo no envié el pago todavía, ¿puedo hacerlo hoy?",
    "Salió mal la transferencia. Yo no la envié todavía.",
    "El pago no salió. Yo no lo envié porque el banco no me dejó.",
    "Hay un retiro en mi cuenta. Yo no saqué esa plata, la sacó mi hermana con mi permiso.",
    "Hay un retiro. No fui yo, fue mi hijo y yo le di permiso.",
    "Teve um saque na conta. Não fui eu, foi minha filha com o meu cartão e eu autorizei.",
    "¿Hiciste la transferencia a tu mamá? Yo seguro que no, se me olvidó.",
    "O Pix não foi. Eu não enviei, o app travou.",
    "Esqueci de fazer o Pix. Eu não enviei.",
    "O Pix para minha mãe ainda não saiu. Eu não enviei ainda.",
    "Eu não enviei ainda o Pix para minha mãe.",
    "Si yo no la envié, ¿quién hizo la transferencia?",
    "¿Yo no la envié? Hay una transferencia rara.",
    "Hay una transferencia. Creo que yo no la envié, déjame revisar.",
    "Pensé que ninguno de los cargos era mío, pero ya vi que sí es mío.",
    "Achei que nenhum dos lançamentos era meu, mas era.",
    "Revisé los cargos. Ninguno es mío?",
    "Nenhuma dessas compras é minha? Acho que sim.",
    "¿Cuál de estos productos es mío? Ninguno es mío, lo sé.",
    "Yo seguro que no puedo pagar el cargo hoy.",
    "Eu é que não fiz o pagamento ainda, minha esposa vai fazer.",
    "Meu saldo caiu porque paguei o aluguel. Não fui eu que errei a senha.",
    "Mi saldo bajó porque pagué la renta, todo bien.",
    "Yo no moví mi carro, ¿por qué hay una multa?",
    "Eu não mexi em nada no app, por que o pagamento não saiu?",
    "no reconozo el nombre del comercio en este cargo",
    "No reconosco la letra de este documento.",
]


@pytest.mark.parametrize(("family", "message"), _FAMILY_POSITIVES)
def test_rf1m_family_positives_are_unauthorized_assertions(family: str, message: str) -> None:
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is True
    assert any(
        finding.asserted and finding.family == family
        for finding in denial_safety_findings(message)
    )


@pytest.mark.parametrize("message", _FAMILY_NEGATIVES)
def test_rf1m_layer_does_not_license_family_near_misses(message: str) -> None:
    assert denial_safety_assertion(message, frozenset()) is False
    assert not any(finding.asserted for finding in denial_safety_findings(message))


@pytest.mark.parametrize(
    ("message", "blocked_by"),
    [
        ("Hay un retiro. No fui yo, fue mi hijo y yo le di permiso.", "authorized_third_party"),
        ("¿Hiciste la transferencia a tu mamá? Yo seguro que no, se me olvidó.", "not_yet_or_causal"),
        ("Esqueci de fazer o Pix. Eu não enviei.", "not_yet_or_causal"),
        ("El pago no salió. Yo no lo envié porque el banco no me dejó.", "not_yet_or_causal"),
        ("Revisé los cargos. Ninguno es mío?", "interrogative_scope"),
        ("Mi saldo bajó porque pagué la renta. No fui yo.", "no_activity_anchor"),
    ],
)
def test_rf1m_findings_record_the_blocking_reason(message: str, blocked_by: str) -> None:
    findings = denial_safety_findings(message)
    assert findings
    assert {finding.blocked_by for finding in findings} == {blocked_by}


@pytest.mark.parametrize(
    "message",
    [
        # Negated grants are denials, not permission.
        "Hay un retiro. No fui yo, yo no le di permiso a nadie.",
        "Hay un retiro. No fui yo y nunca le di autorización a nadie.",
        # Forgetting an object (not forgetting to act) does not explain the activity.
        "Hay un cargo. No fui yo; olvidé mi tarjeta en el taxi y alguien la usó.",
        "Esqueci meu cartão no táxi. Teve um saque. Eu não saquei isso.",
        # A system failure in another sentence does not explain the movement.
        "Teve um saque na conta. Eu não saquei isso. O app travou ontem.",
    ],
)
def test_rf1m_new_blockers_stay_narrow(message: str) -> None:
    assert denial_safety_assertion(message, frozenset()) is True


def test_rf1m_money_movement_requires_explicit_subject_and_back_reference() -> None:
    # Without "yo" the verb reads as a failure to move money.
    assert not denial_safety_findings("Hay una transferencia. No la mandé.")
    # Indefinite/possessive objects are new movements, not the one disowned.
    assert not denial_safety_findings("Hay una transferencia. Yo no mandé el pago.")
    # A null object must close the sentence, not just a comma clause.
    assert not denial_safety_findings("Tem um Pix. Eu não enviei, o app travou.")


def test_rf1m_clause_initial_anaphora_is_limited_to_agency_families() -> None:
    (agency,) = denial_safety_findings(
        "Hay un cargo raro. No fui yo, y nadie más tiene acceso a mi banca en línea."
    )
    assert agency.asserted is True
    assert agency.anchor == "cargo"

    # A long, non-initial cue still may not borrow the previous anchor.
    (late,) = denial_safety_findings(
        "Hay un cargo raro. Me escribió mi hermano ayer y no fui yo a la fiesta del sábado."
    )
    assert late.asserted is False
    assert late.blocked_by == "no_activity_anchor"


def test_rf1m_agent_reference_extends_anaphora_by_exactly_one_sentence() -> None:
    (reached,) = denial_safety_findings(
        "Hubo un pago en otra ciudad. No sé quién lo hizo. Yo seguro que no."
    )
    assert reached.asserted is True
    assert reached.anchor == "pago"

    # The intervening sentence must be a "who did it" continuation.
    (unreached,) = denial_safety_findings(
        "Hubo un pago en otra ciudad. Mañana viajo a Medellín. Yo seguro que no."
    )
    assert unreached.blocked_by == "no_activity_anchor"

    # And the look-back never reaches three sentences back.
    (too_far,) = denial_safety_findings(
        "Hubo un pago en otra ciudad. Estoy de viaje. No sé quién lo hizo. Yo seguro que no."
    )
    assert too_far.blocked_by == "no_activity_anchor"


def test_rf1m_layer_never_consults_legacy_regex_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_legacy_regex(*_args, **_kwargs):
        raise AssertionError("legacy whole-message regex inventory was consulted")

    monkeypatch.setattr(unauthorized_signals, "_matches_any", fail_legacy_regex)
    for _family, message in _FAMILY_POSITIVES:
        assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is True


@pytest.mark.parametrize("mode", ["hypothetical", "uncertain", "authorized_third_party", "retracted"])
def test_rf1m_structural_non_assertive_modes_still_veto(mode: str) -> None:
    message = "Tem um Pix para um desconhecido. Eu não mandei."
    assert denial_safety_assertion(message, frozenset()) is True
    assert denial_safety_assertion(message, frozenset({mode})) is False


# ---------------------------------------------------------------- HTTP matrix
_OWNED = {"lucia": "DEMO-ES-1001", "rafael": "DEMO-PT-2001"}
_FOREIGN = {"lucia": "DEMO-PT-2001", "rafael": "DEMO-ES-1001"}
_FOREIGN_MARKERS = {
    "DEMO-PT-2001": ("Mercado Bairro", "219.90", "219,90", "BRL"),
    "DEMO-ES-1001": ("Mercado Central", "125000", "125.000", "COP"),
}
_HTTP_CASES = [
    ("lucia", "es", "¿Ya salió la transacción {ref}? No sé quién la hizo. Yo seguro que no.",
     "Hay un retiro en mi cuenta. No fui yo, y la tarjeta está conmigo."),
    ("lucia", "es", "La transferencia {ref} salió de mi cuenta. Yo no la mandé.",
     "Me llegaron varios cobros. Ninguno de ellos me pertenece."),
    ("rafael", "pt", "A transação {ref} já foi concluída? Não sei quem fez. Eu é que não fui.",
     "Teve um saque na conta. Não fui eu, e o cartão está comigo."),
    ("rafael", "pt", "O Pix {ref} saiu da minha conta. Eu não enviei.",
     "Vi quatro lançamentos estranhos. Nenhum deles é meu."),
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
    assert body["products"] == []
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
def test_rf1m_owned_denial_escalates_without_status_answer(
    tmp_path, persona, language, with_ref, no_ref
) -> None:
    client, context = _client(tmp_path)
    owned = _OWNED[persona]
    session, body = _turn(client, persona, language, with_ref.format(ref=owned))
    resolved = _escalation_context(context, session, body)
    assert resolved.transaction_id == owned
    lowered = body["response_text"].casefold()
    assert not any(
        status in lowered
        for status in ("aprobada", "aprovada", "pendiente", "pendente", "rechazada", "recusada")
    )


@pytest.mark.parametrize(("persona", "language", "with_ref", "no_ref"), _HTTP_CASES)
def test_rf1m_foreign_denial_escalates_without_disclosure_or_attachment(
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
def test_rf1m_unreferenced_denial_escalates_with_session_only_ticket(
    tmp_path, persona, language, with_ref, no_ref
) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, language, no_ref)
    resolved = _escalation_context(context, session, body)
    assert resolved.transaction_id is None


@pytest.mark.parametrize(
    ("persona", "language", "message"),
    [
        ("lucia", "es", "La transferencia {ref} no salió. Yo no la envié todavía."),
        ("rafael", "pt", "O Pix {ref} não saiu. Esqueci de enviar. Eu não enviei."),
    ],
)
def test_rf1m_near_misses_are_not_unauthorized_escalations(
    tmp_path, persona, language, message
) -> None:
    client, _ = _client(tmp_path)
    _, body = _turn(client, persona, language, message.format(ref=_OWNED[persona]))
    assert "unauthorized_activity_reported" not in body["reason_codes"]
