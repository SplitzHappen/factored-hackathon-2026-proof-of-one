from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.main import create_app
from app.settings import Settings
from app.unauthorized_signals import is_explicit_unauthorized_assertion


@pytest.mark.parametrize(
    "message",
    [
        # Spanish: coordinated negation, quantifiers/correlatives, origin,
        # and productive plural morphology.
        "El cobro es de una suscripción que jamás contraté ni autoricé.",
        "Nunca pedí ese servicio ni lo autoricé.",
        "Ninguno de estos cargos es mío.",
        "Ni esta compra ni las otras dos son mías.",
        "La transferencia no salió de mí.",
        "Ese pago no provino de mí.",
        "Tengo compras no autorizadas en mi tarjeta.",
        "Aparecieron dos cargos no autorizados en mi cuenta.",
        "Las transferencias no fueron autorizadas por mí.",
        # Portuguese equivalents use independent surface forms.
        "A cobrança é de uma assinatura que eu nunca contratei nem autorizei.",
        "Jamais pedi esse serviço nem o autorizei.",
        "Nenhuma dessas compras é minha.",
        "Nem esse pagamento nem os outros são meus.",
        "A transferência não partiu de mim.",
        "Esse pagamento não veio de mim.",
        "Há compras não autorizadas no meu cartão.",
        "Apareceram pagamentos não autorizados na minha conta.",
        "As transferências não foram autorizadas por mim.",
    ],
)
def test_compositional_explicit_unauthorized_assertions(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True


@pytest.mark.parametrize(
    "message",
    [
        # Hypothetical / policy / security questions.
        "¿Qué pasaría si el pago DEMO-ES-1001 lo hubiera hecho alguien sin mi permiso?",
        "Si algún día veo un cargo que no hice, ¿a quién tengo que llamar?",
        "¿Cómo puedo protegerme de compras no autorizadas con mi tarjeta?",
        "É possível alguém fazer um Pix da minha conta sem a minha senha?",
        "Se eu perder o cartão e alguém comprar algo sem minha permissão, o banco devolve o dinheiro?",
        "Quais cuidados devo ter para evitar transações não autorizadas no Pix?",
        "¿Qué controles de seguridad tienen para prevenir transferencias no autorizadas?",
        "Acabo de hacer la transferencia DEMO-ES-1001; ¿qué controles de seguridad tienen para prevenir transferencias no autorizadas en mi cuenta?",
        "Quais controles de segurança existem para prevenir transações não autorizadas?",
        "A transação DEMO-PT-2001 tem proteção caso um dia alguém use meu cartão sem autorização?",
        # Descriptor clarification, retraction, and negated denial.
        "No reconozco el nombre que aparece en este cobro; ¿me pueden decir qué comercio es?",
        "Pensé que ese cargo no era mío, pero ya me acordé de que sí lo hice yo.",
        "No digo que no sea mío, solo quiero entender por qué aparece dos veces.",
        "Eu ia dizer que não fiz essa transferência, mas vi no app que fui eu mesmo.",
        "Não digo que não seja meu, só quero entender a descrição.",
    ],
)
def test_compositional_scope_controls_remain_negative(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is False


@pytest.mark.parametrize(
    "message",
    [
        # Scope words must not suppress a separate present assertion.
        "Tengo compras no autorizadas; ¿cómo puedo protegerme ahora?",
        "No reconozco el nombre del comercio y además no hice esa compra.",
        "Pensé que el cargo anterior era mío, pero este cargo no es mío.",
        "Há pagamentos não autorizados; quais cuidados devo tomar agora?",
        "Tengo transferencias no autorizadas; ¿qué controles de seguridad tienen para evitar que vuelva a pasar?",
        "Há transferências não autorizadas; quais controles de segurança devo ativar agora?",
        "Não reconheço o nome do comércio e também não fiz essa compra.",
        "Achei que a cobrança anterior era minha, mas essa compra não é minha.",
    ],
)
def test_scope_controls_do_not_hide_independent_current_assertions(message: str) -> None:
    assert is_explicit_unauthorized_assertion(message) is True


_HTTP_STRUCTURES = [
    (
        "lucia",
        "El cobro es de una suscripción que jamás contraté ni autoricé.",
        "El cobro {transaction_id} es de una suscripción que jamás contraté ni autoricé.",
    ),
    (
        "lucia",
        "Ninguno de estos cargos es mío.",
        "Ni el cargo {transaction_id} ni los otros dos son míos.",
    ),
    (
        "lucia",
        "La transferencia no salió de mí.",
        "La transferencia {transaction_id} no salió de mí.",
    ),
    (
        "lucia",
        "Tengo compras no autorizadas en mi tarjeta.",
        "Tengo compras no autorizadas en mi tarjeta, incluida {transaction_id}.",
    ),
    (
        "rafael",
        "A cobrança é de uma assinatura que eu nunca contratei nem autorizei.",
        "A cobrança {transaction_id} é de uma assinatura que eu nunca contratei nem autorizei.",
    ),
    (
        "rafael",
        "Nenhuma dessas compras é minha.",
        "Nem a compra {transaction_id} nem as outras são minhas.",
    ),
    (
        "rafael",
        "A transferência não partiu de mim.",
        "A transferência {transaction_id} não partiu de mim.",
    ),
    (
        "rafael",
        "Há compras não autorizadas no meu cartão.",
        "Há compras não autorizadas no meu cartão, incluindo {transaction_id}.",
    ),
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


def _session(client: TestClient, persona_id: str) -> dict:
    response = client.post("/api/demo/sessions", json={"persona_id": persona_id})
    assert response.status_code == 201
    return response.json()


def _http_cases():
    for persona_id, without_id, with_id_template in _HTTP_STRUCTURES:
        owned = "DEMO-ES-1001" if persona_id == "lucia" else "DEMO-PT-2001"
        foreign = "DEMO-PT-2001" if persona_id == "lucia" else "DEMO-ES-1001"
        yield pytest.param(
            persona_id,
            "owned",
            with_id_template.format(transaction_id=owned),
            id=f"{persona_id}-owned-{without_id[:20]}",
        )
        yield pytest.param(
            persona_id,
            "foreign",
            with_id_template.format(transaction_id=foreign),
            id=f"{persona_id}-foreign-{without_id[:20]}",
        )
        yield pytest.param(
            persona_id,
            "none",
            without_id,
            id=f"{persona_id}-none-{without_id[:20]}",
        )


@pytest.mark.parametrize(
    ("persona_id", "reference_kind", "message"),
    list(_http_cases()),
)
def test_compositional_http_matrix_preserves_escalation_and_ownership(
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
            "SELECT transaction_id, reason_code "
            "FROM escalation_tickets WHERE ticket_id = ?",
            (body["escalation_ticket_id"],),
        ).fetchone()

    assert row is not None
    assert row[1] == "unauthorized_activity_reported"

    if reference_kind == "owned":
        expected = "DEMO-ES-1001" if persona_id == "lucia" else "DEMO-PT-2001"
        assert row[0] == expected
    else:
        assert row[0] is None

    if reference_kind == "foreign":
        foreign = "DEMO-PT-2001" if persona_id == "lucia" else "DEMO-ES-1001"
        assert foreign not in body["response_text"]
        assert foreign not in str(body["transactions"])
        assert foreign not in str(body["clarification_transaction_ids"])
