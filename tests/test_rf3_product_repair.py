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


# RF3 repair families. Wording is family-level development material written for
# these tests, not RF2 fresh-probe text. Each entry names the denial-safety family
# that must license it.
_FAMILY_POSITIVES = [
    # P1. generalized depletion / value loss
    ("rf3_passive_event", "Se esfumó la plata de mi cuenta de ahorros y yo no hice ningún retiro."),
    ("rf3_passive_event", "Mi bono navideño fue retirado del cajero por un desconocido."),
    ("rf3_passive_event", "O limite do meu cartão ficou esgotado sem que eu comprasse nada."),
    ("rf3_passive_event", "Desapareceu o saldo da minha conta salário e eu não mexi em nada."),
    ("rf3_passive_event", "Mi cesantía fue sacada de la cuenta por alguien que no soy yo."),
    ("rf3_active_event", "Roubaram as economias da minha poupança."),
    # P2. pronoun / clitic / anaphora
    ("rf3_active_event", "Tenía la prima de servicios en la cuenta y un ladrón me la sacó."),
    ("rf3_active_event", "Mis ahorros estaban en la tarjeta y me los gastaron sin permiso."),
    ("rf3_active_event", "Os fundos da loja, levaram-nos da conta sem autorização nenhuma."),
    ("rf3_active_event", "Eu tinha deixado a reserva no cartão e alguém a gastou sem eu saber."),
    # P3. ongoing / habitual / present use
    ("rf3_active_event", "Un estafador sigue pagando servicios con mi tarjeta."),
    ("rf3_active_event", "Todos los días me hacen retiros de la cuenta en otra ciudad."),
    ("rf3_active_event", "Hay alguien comprando con mi tarjeta en farmacias que no conozco."),
    ("rf3_active_event", "Tem gente usando meu cartão em postos onde eu nunca abasteço, não sou eu."),
    ("rf3_active_event", "Um desconhecido continua sacando dinheiro da minha conta."),
    # P4. fronted or displaced non-consent
    ("rf3_active_event", "Sin que nadie me avisara, movieron el saldo de la tarjeta a otra persona."),
    ("rf3_active_event", "Sem que eu autorizasse, gastaram o dinheiro do cartão de débito."),
    ("rf3_active_event", "Pasaron mis ahorros a una cuenta ajena, y eso fue sin mi permiso."),
    ("rf3_active_event", "Yo nunca di permiso, pero transfirieron el dinero de mi cuenta."),
    # P5. plural / multiple instruments
    ("rf3_active_event", "Usaron mis tres tarjetas de crédito en el exterior y no fui yo."),
    ("rf3_active_event", "Esvaziaram minhas duas contas sem minha permissão."),
    ("rf3_active_event", "Sacaron dinero de la cuenta y de la tarjeta el mismo día sin que yo supiera."),
    # P6. no money / ruin, tied to an unauthorized action
    ("rf3_active_event", "Me quedé sin un peso porque un hacker vació mi cuenta."),
    ("rf3_active_event", "Estou liso: um golpista levou todo o saldo do meu cartão."),
    ("rf3_active_event", "Ando en la ruina desde que alguien se llevó lo de mi tarjeta sin permiso."),
    # P7. card or account data used for a subscription or contract (RF1U F5 gap)
    ("rf3_data_subscription", "Usaram os dados do meu cartão para assinar uma plataforma de filmes."),
    ("rf3_data_subscription", "Usaron los datos de mi tarjeta para afiliarse a un club de vinos."),
    ("rf3_data_subscription", "Utilizaron mis datos bancarios para contratar un plan de telefonía."),
]

_RF3_FAMILY_NAMES = {"rf3_active_event", "rf3_passive_event", "rf3_data_subscription"}

# Near misses for the RF3 families, each with the blocker that must name it.
_NAMED_NEGATIVES = [
    ("Mis hijos siguen usando mi tarjeta sin pedirme permiso.", "named_actor"),
    ("Mi cesantía fue retirada por mi esposo sin que yo supiera.", "named_actor"),
    ("Me cobraron la cuota del seguro de mi cuenta sin aviso.", "known_charge"),
    ("A mi mamá le vaciaron la cuenta sin permiso, ¿cómo la ayudo?", "third_party_dative"),
    ("Si alguien sigue usando mi tarjeta sin permiso, ¿la bloquean?", "conditional_protasis"),
    ("¿Están sacando dinero de mi cuenta sin mi autorización?", "interrogative_scope"),
    ("Usan mi tarjeta con mi autorización mientras viajo; no soy yo quien compra.", "authorized_third_party"),
    ("Mi vecina dice que le robaron dinero de la cuenta sin que ella supiera.", "reported_speech"),
]

# Benign controls the RF3 families must not license at all.
_BENIGN = [
    # B1. app, menu, or interface
    "No ubico la pestaña de tarjetas en la app nueva; ¿dónde quedó?",
    "Desapareció el botón de pagos de la aplicación y no sé cómo pagar.",
    "Sumiu a opção de Pix do aplicativo depois da atualização.",
    # B2. ordinary administration
    "Me cobran en dólares cuando uso la tarjeta en el exterior, ¿es normal?",
    "La cuenta quedó en cero porque transferí todo a mi otra cuenta.",
    "O dinheiro do salário sumiu da conta porque paguei o cartão inteiro.",
    "Mi esposa sacó dinero de mi cuenta para el mercado, como siempre.",
    "Pasaron el saldo de mi tarjeta vieja a la nueva sin problema.",
    "Transfirieron mis ahorros al CDT sin que yo tuviera que ir a la oficina.",
    "Sem que eu precisasse ir à agência, transferiram meu saldo para a nova conta.",
    "Un desconocido me depositó plata en la cuenta; ¿de quién es?",
    "Me transfirieron mi sueldo a la cuenta de nómina, ¿ya está?",
    "Hicieron un cargo en mi tarjeta por la suscripción que contraté.",
    "Mi saldo quedó vacío después de pagar la universidad.",
    "Un desconocido sacó plata del cajero de la esquina y luego se fue.",
    # B3. hypothetical, conditional, education, third party
    "¿Qué pasa si un hacker vacía mi cuenta mientras duermo?",
    "Los estafadores usan tarjetas ajenas en el extranjero, ¿cómo lo evitan?",
    "Li que golpistas estão esvaziando contas; minha conta está protegida?",
    "Caso alguém use meu cartão sem minha autorização, o que faço?",
    # P2 guard: no financial antecedent
    "Tenía el portátil en la mochila y me lo robaron en el metro.",
    "Deixei as chaves no carro e alguém as levou.",
]


@pytest.mark.parametrize(("family", "message"), _FAMILY_POSITIVES)
def test_rf3_family_positives_are_unauthorized_assertions(family: str, message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True
    assert any(f.family == family and f.asserted for f in denial_safety_findings(message))


@pytest.mark.parametrize(("message", "blocker"), _NAMED_NEGATIVES)
def test_rf3_near_misses_are_blocked_by_name(message: str, blocker: str) -> None:
    findings = [f for f in denial_safety_findings(message) if f.family in _RF3_FAMILY_NAMES]
    assert findings and all(not f.asserted for f in findings)
    assert any(f.blocked_by == blocker for f in findings)


@pytest.mark.parametrize("message", _BENIGN)
def test_rf3_benign_controls_are_not_reports(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False
    assert not any(
        f.asserted for f in denial_safety_findings(message) if f.family in _RF3_FAMILY_NAMES
    )


def test_rf3_si_prefix_mask_keeps_a_real_conditional() -> None:
    # "sigue" no longer reads as a conditional "si", but a real "si" still blocks.
    report = "Alguien sigue pagando con mi tarjeta y yo no fui."
    assert is_explicit_unauthorized_assertion(report) is True
    hypothetical = "Si alguien sigue pagando con mi tarjeta, ¿qué hago?"
    findings = [f for f in denial_safety_findings(hypothetical) if f.family == "rf3_active_event"]
    assert findings and all(f.blocked_by == "conditional_protasis" for f in findings)
    assert is_explicit_unauthorized_assertion(hypothetical) is False


def test_rf3_unfamiliar_place_needs_no_self_use() -> None:
    assert is_explicit_unauthorized_assertion("Me hacen compras en la tarjeta desde otro país.") is True
    assert (
        is_explicit_unauthorized_assertion(
            "Me hacen compras en la tarjeta desde otro país porque estoy de viaje."
        )
        is False
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


# One report per RF3 scope item and language.
_HTTP_REPORTS = [
    ("lucia", "Se esfumó la plata de mi cuenta de ahorros y yo no hice ningún retiro."),
    ("rafael", "Desapareceu o saldo da minha conta salário e eu não mexi em nada."),
    ("lucia", "Tenía la prima de servicios en la cuenta y un ladrón me la sacó."),
    ("rafael", "Eu tinha deixado a reserva no cartão e alguém a gastou sem eu saber."),
    ("lucia", "Un estafador sigue pagando servicios con mi tarjeta."),
    ("rafael", "Um desconhecido continua sacando dinheiro da minha conta."),
    ("lucia", "Sin que nadie me avisara, movieron el saldo de la tarjeta a otra persona."),
    ("rafael", "Esvaziaram minhas duas contas sem minha permissão."),
    ("lucia", "Me quedé sin un peso porque un hacker vació mi cuenta."),
    ("rafael", "Usaram os dados do meu cartão para assinar uma plataforma de filmes."),
]


@pytest.mark.parametrize(("persona", "message"), _HTTP_REPORTS)
@pytest.mark.parametrize("reference", ["owned", "none", "amount", "foreign", "unowned"])
def test_rf3_reports_escalate_bound_to_session_without_disclosure(
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
        ("lucia", "No ubico la pestaña de tarjetas en la app nueva; ¿dónde quedó?"),
        ("rafael", "O dinheiro do salário sumiu da conta porque paguei o cartão inteiro."),
        ("lucia", "Me cobran en dólares cuando uso la tarjeta en el exterior, ¿es normal?"),
        ("rafael", "Caso alguém use meu cartão sem minha autorização, o que faço?"),
        ("lucia", "Transfirieron mis ahorros al CDT sin que yo tuviera que ir a la oficina."),
    ],
)
def test_rf3_benign_turns_create_no_ticket(tmp_path, persona, message) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, message)
    assert body["route"] != "ESCALATE"
    assert body.get("escalation_ticket_id") is None
    assert context.store.list_verified_escalation_ticket_ids_for_tenant(session["tenant_id"]) == []
