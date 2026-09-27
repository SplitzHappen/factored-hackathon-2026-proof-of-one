from __future__ import annotations

import sqlite3
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.interpretation import InterpretationService
from app.main import create_app
from app.settings import Settings
from app.unauthorized_signals import is_explicit_unauthorized_assertion
from evaluation.realistic_language import load_realistic_language_suite


def _client(tmp_path):
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(context)), context


def _session(client: TestClient, persona_id: str) -> dict:
    response = client.post("/api/demo/sessions", json={"persona_id": persona_id})
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    ("persona_id", "reference_kind", "message"),
    [
        # Spanish — owned reference.
        ("lucia", "owned", "Ese cargo DEMO-ES-1001 no es mío."),
        ("lucia", "owned", "Yo jamás autoricé la transacción DEMO-ES-1001."),
        ("lucia", "owned", "Me cargaron DEMO-ES-1001 sin mi autorización."),
        # Spanish — foreign reference must not become disclosed/attached.
        ("lucia", "foreign", "No reconozco el cobro DEMO-PT-2001."),
        ("lucia", "foreign", "La transacción DEMO-PT-2001 fue de otra persona."),
        ("lucia", "foreign", "Yo no realicé DEMO-PT-2001 ni di autorización."),
        # Spanish — no transaction ID.
        ("lucia", "none", "Esa compra es ajena; yo no hice esa operación."),
        ("lucia", "none", "Me hicieron un cobro sin mi permiso."),
        ("lucia", "none", "No fui yo quien hizo esa compra."),
        # Portuguese — owned reference.
        ("rafael", "owned", "Essa cobrança DEMO-PT-2001 não é minha."),
        ("rafael", "owned", "Eu jamais autorizei a transação DEMO-PT-2001."),
        ("rafael", "owned", "Me cobraram DEMO-PT-2001 sem a minha autorização."),
        # Portuguese — foreign reference must not become disclosed/attached.
        ("rafael", "foreign", "Não reconheço a cobrança DEMO-ES-1001."),
        ("rafael", "foreign", "A transação DEMO-ES-1001 foi de outra pessoa."),
        ("rafael", "foreign", "Eu não realizei DEMO-ES-1001 nem dei autorização."),
        # Portuguese — no transaction ID.
        ("rafael", "none", "Essa compra é de outra pessoa; eu não fiz essa operação."),
        ("rafael", "none", "Fizeram uma cobrança sem a minha permissão."),
        ("rafael", "none", "Não fui eu quem fez essa compra."),
    ],
)
def test_http_unauthorized_paraphrases_escalate_without_cross_customer_disclosure(
    tmp_path,
    persona_id: str,
    reference_kind: str,
    message: str,
) -> None:
    client, context = _client(tmp_path)
    session = _session(client, persona_id)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
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
            "SELECT transaction_id FROM escalation_tickets WHERE ticket_id = ?",
            (body["escalation_ticket_id"],),
        ).fetchone()
    assert row is not None

    if reference_kind == "owned":
        expected = "DEMO-ES-1001" if persona_id == "lucia" else "DEMO-PT-2001"
        assert row[0] == expected
    else:
        assert row[0] is None

    if reference_kind == "foreign":
        foreign = "DEMO-PT-2001" if persona_id == "lucia" else "DEMO-ES-1001"
        assert foreign not in body["response_text"]


@pytest.mark.parametrize(
    "message",
    [
        "Ese pago me preocupa y quiero revisarlo.",
        "La compra se ve rara, ¿qué pasó?",
        "¿Esto podría ser fraude?",
        "¿Es de otra persona?",
        "No sé si yo autoricé esa compra.",
        "Esse pagamento está estranho e quero conferir.",
        "Essa compra me preocupa; o que aconteceu?",
        "Isso pode ser fraude?",
        "É de outra pessoa?",
        "Não lembro se eu autorizei essa compra.",
    ],
)
def test_concern_or_uncertainty_alone_is_not_unauthorized_assertion(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False


def test_all_frozen_realistic_language_unauthorized_positives_hit_lexical_backstop() -> None:
    cases, _ = load_realistic_language_suite()
    positives = [case for case in cases if case.unauthorized_activity_asserted]

    assert len(positives) == 6
    for case in positives:
        assert InterpretationService._lexical_unauthorized_assertion(
            case.message,
            case.language.value,
        ) is True


def test_frozen_realistic_language_negatives_do_not_trigger_lexical_backstop() -> None:
    cases, _ = load_realistic_language_suite()
    negatives = [case for case in cases if not case.unauthorized_activity_asserted]

    assert negatives
    for case in negatives:
        assert InterpretationService._lexical_unauthorized_assertion(
            case.message,
            case.language.value,
        ) is False
