"""RF1I-R1 structural-resolver repair regressions.

RF1I (private regression revalidation of the merged RF1H-B5 candidate) found that
the structural resolver, now the only authoritative ES/PT path, no longer
recognized several explicit unauthorized-activity constructions that the retired
whole-message regex inventory used to cover, and treated one hypothetical
"if it turned out that ..." protasis as an assertion.

These tests pin the structural repairs using independently worded public
paraphrases. They intentionally do not reproduce any frozen private RF1A/RF1D
wording, and every positive is also exercised with the legacy regex inventory
disabled so a silent legacy fallback cannot satisfy them.
"""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

import app.unauthorized_signals as unauthorized_signals
from app.bootstrap import build_app_context
from app.main import create_app
from app.settings import Settings
from app.unauthorized_grammar import (
    PropositionMode,
    resolve_positive_propositions,
)


def _assertive_rules(message: str) -> set[str]:
    return {
        proposition.rule
        for language in ("es", "pt")
        for proposition in resolve_positive_propositions(message, language)
        if proposition.mode == PropositionMode.ASSERTIVE.value
    }


# (message, structural rule that must be among the assertive propositions)
_POSITIVES: list[tuple[str, str]] = [
    # Comma/conjunction-attached and cleft self-exculpation.
    ("Esa compra la hizo un desconocido, no fui yo.", "P2-R4-embedded-self-exculpation"),
    ("El retiro lo hizo otra persona, no yo.", "P2-R4-embedded-self-exculpation"),
    ("Esse saque foi outra pessoa, não eu.", "P2-R4-embedded-self-exculpation"),
    ("Esse pagamento não fui eu que fiz.", "P2-R4-embedded-self-exculpation"),
    # Negative quantifier over a numeral partitive.
    ("Ninguno de estos cuatro movimientos es mío.", "P1-neg-quantifier"),
    ("Nenhuma das duas compras é minha.", "P1-neg-quantifier"),
    # Closed "at no moment" negation idioms bind to the denied predicate.
    ("En ningún momento aprobé la compra DEMO-ES-1001.", "P4"),
    ("Em momento algum aprovei esse pagamento.", "P4"),
    # Lexically negative recognition verbs.
    ("Desconozco este movimiento.", "P7"),
    ("Desconheço esse lançamento.", "P7"),
    # First-person relative non-recognition of an indefinite activity/billed item.
    ("Me aparece un cargo que no reconozco de ninguna manera.", "P7"),
    ("Tem uma compra na fatura que eu não reconheço.", "P7"),
    ("Hay una suscripción de música que no reconozco.", "P7"),
    ("Surgiu uma mensalidade que eu desconheço.", "P7"),
    # Partitive pronominal object.
    ("Vi varios gastos y no reconozco ninguno de ellos.", "P7-R3-topic-default"),
    ("Vi vários gastos e não reconheço nenhum deles.", "P7-R3-topic-default"),
    # Consent denial inside a relative clause on a recurring-billing item.
    (
        "Me cobran una membresía a la cual nunca di mi consentimiento.",
        "P4-R4-relative-consent-denial",
    ),
    (
        "Cobraram uma mensalidade à qual nunca dei consentimento.",
        "P4-R4-relative-consent-denial",
    ),
    # Subjectless / passive third-party action with explicit permission absence.
    ("Usaron mi tarjeta en una tienda sin mi permiso.", "P5b"),
    ("Accedieron a mi cuenta sin que yo lo autorizara.", "P5b"),
    ("Minha conta foi acessada por terceiros sem a minha autorização.", "P5b"),
    ("Me cobraron de la cuenta sin mi autorización.", "P5b"),
    ("Nadie tenía autorización para utilizar mi cuenta.", "P5b"),
    ("Ninguém tinha autorização para usar minha conta.", "P5b"),
    # Unknown actor acting on a customer device/app target.
    ("Alguien entró a mi app del banco.", "P5"),
    ("Alguém acessou meu aplicativo.", "P5"),
    # Fraud copula with a transaction ID (gender agreement uses the noun).
    ("La compra DEMO-ES-1001 es fraudulenta.", "P6-copular"),
    ("A transação DEMO-PT-2001 é fraudulenta.", "P6-copular"),
    # Ownership denial across one bounded appositive relative clause.
    ("El cargo DEMO-ES-1001, que apareció ayer, no es mío.", "P1"),
    ("A compra DEMO-PT-2001, que passou ontem, não é minha.", "P1"),
]


@pytest.mark.parametrize(("message", "rule"), _POSITIVES)
def test_rf1i_r1_structural_positive_without_legacy_regex(
    monkeypatch: pytest.MonkeyPatch,
    message: str,
    rule: str,
) -> None:
    def fail_legacy_regex(*_args, **_kwargs):
        raise AssertionError("legacy whole-message regex inventory was consulted")

    monkeypatch.setattr(unauthorized_signals, "_matches_any", fail_legacy_regex)

    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is True
    assert rule in _assertive_rules(message)


_NEGATIVES: list[str] = [
    # Authorized or hypothetical third-party use is not an unauthorized report.
    "Mi esposo usó mi tarjeta con mi permiso.",
    "Mi hijo usó mi tarjeta porque yo se lo pedí.",
    "Meu filho usou meu cartão com a minha permissão.",
    "¿Qué pasa si usan mi cuenta sin que yo lo autorice?",
    "Se alguém usar meu cartão sem minha permissão, o que eu faço?",
    "O banco pode debitar minha conta sin minha autorização?",
    # First-person acts are never third-party use.
    "Yo usé la tarjeta sin que mi madre lo supiera.",
    # Exculpation must stay a closed form: authorized/known actor, retraction,
    # and a tail that is not the clause end do not qualify.
    "La transferencia la hizo mi esposa, no yo.",
    "Pensé que no fui yo, pero sí fui yo.",
    "El pago lo hizo otra persona, no yo, pero yo se lo pedí.",
    # Affirmed ownership and affirmed consent.
    "El cargo DEMO-ES-1001, que apareció ayer, es mío.",
    "A compra DEMO-PT-2001, que passou ontem, é minha.",
    "Me cobran una suscripción a la que sí di mi consentimiento.",
    # Bare permission denial without an anchor stays outside P4 (B2 boundary).
    "Yo no le di permiso.",
    "Eu não dei permissão.",
    # Non-recognition of knowledge/procedure is not activity disowning.
    "Desconozco cómo se presenta un reclamo.",
    "Desconheço como se abre uma contestação.",
    "Desconozco el nombre del comercio.",
    "Não desconheço essa compra.",
    "No desconozco este cargo.",
    # Unrelated uses of the closed idioms.
    "En ningún momento dudé del cajero.",
    "Em momento algum tive problema com o aplicativo.",
    # "If it turned out that ..." protases are hypothetical, with or without a
    # finite predicate after the frame.
    "Si resultara que la compra DEMO-ES-1001 no la hice yo, ¿qué sigue?",
    "Si resultase que el cargo DEMO-ES-1001 no es mío, ¿cómo procedo?",
    "Si resultara que el cargo DEMO-ES-1001 no lo hice yo, ¿cuál sería el proceso?",
    "Se resultar que a compra DEMO-PT-2001 não é minha, qual o procedimento?",
]


@pytest.mark.parametrize("message", _NEGATIVES)
def test_rf1i_r1_structural_negatives_stay_non_assertive(message: str) -> None:
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is False


def test_rf1i_r1_assertion_before_a_later_conditional_is_preserved() -> None:
    message = (
        "El cargo DEMO-ES-1001 no es mío, y si resultara que sí lo es, avísenme."
    )

    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is True


def _client(tmp_path):
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(context)), context


@pytest.mark.parametrize(
    ("persona_id", "reference_kind", "template"),
    [
        ("lucia", "owned", "Usaron mi tarjeta en la compra {txid} sin mi permiso."),
        ("lucia", "foreign", "Usaron mi tarjeta en la compra {txid} sin mi permiso."),
        ("lucia", "none", "Usaron mi tarjeta en una tienda sin mi permiso."),
        ("lucia", "owned", "La compra {txid} la hizo otra persona, no fui yo."),
        ("lucia", "foreign", "La compra {txid} la hizo otra persona, no fui yo."),
        ("lucia", "none", "Esa compra la hizo otra persona, no fui yo."),
        ("rafael", "owned", "Minha conta foi acessada sem a minha permissão na compra {txid}."),
        ("rafael", "foreign", "Minha conta foi acessada sem a minha permissão na compra {txid}."),
        ("rafael", "none", "Minha conta foi acessada por terceiros sem a minha autorização."),
        ("rafael", "owned", "O pagamento {txid}, que passou ontem, não é meu."),
        ("rafael", "foreign", "O pagamento {txid}, que passou ontem, não é meu."),
        ("rafael", "none", "Esse pagamento não fui eu que fiz."),
    ],
)
def test_rf1i_r1_http_routes_escalate_with_foreign_id_non_disclosure(
    tmp_path,
    persona_id: str,
    reference_kind: str,
    template: str,
) -> None:
    client, context = _client(tmp_path)
    owned = "DEMO-ES-1001" if persona_id == "lucia" else "DEMO-PT-2001"
    foreign = "DEMO-PT-2001" if persona_id == "lucia" else "DEMO-ES-1001"
    txid = {"owned": owned, "foreign": foreign, "none": ""}[reference_kind]
    message = template.format(txid=txid)

    session = client.post("/api/demo/sessions", json={"persona_id": persona_id})
    assert session.status_code == 201
    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session.json()["session_id"]},
        json={"message": message},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ESCALATE"
    assert body["reason_codes"] == ["unauthorized_activity_reported"]
    assert body["transactions"] == []
    assert body["clarification_transaction_ids"] == []
    assert body["escalation_ticket_id"] is not None

    with sqlite3.connect(context.store.path) as connection:
        row = connection.execute(
            "SELECT transaction_id, reason_code FROM escalation_tickets "
            "WHERE ticket_id = ?",
            (body["escalation_ticket_id"],),
        ).fetchone()
    assert row is not None
    assert row[0] == (owned if reference_kind == "owned" else None)
    assert row[1] == "unauthorized_activity_reported"
    if reference_kind == "foreign":
        assert foreign not in body["response_text"]
