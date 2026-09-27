from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.amounts import (
    extract_locale_amounts,
    extract_single_locale_amount,
    format_locale_amount,
    parse_locale_amount_token,
)
from app.bootstrap import build_app_context
from app.interpretation import InterpretationService
from app.main import create_app
from app.schemas import InterpretedTransactionQuery, SupportedLanguage
from app.settings import Settings


@pytest.mark.parametrize(
    ("language", "token", "expected"),
    [
        (SupportedLanguage.ES, "54.000", Decimal("54000")),
        (SupportedLanguage.ES, "125.000", Decimal("125000")),
        (SupportedLanguage.ES, "125000,00", Decimal("125000.00")),
        (SupportedLanguage.PT, "219,90", Decimal("219.90")),
        (SupportedLanguage.PT, "1.219,90", Decimal("1219.90")),
        (SupportedLanguage.PT, "8450", Decimal("8450")),
    ],
)
def test_locale_amount_tokens_normalize_to_canonical_decimal(
    language: SupportedLanguage,
    token: str,
    expected: Decimal,
) -> None:
    assert parse_locale_amount_token(token, language) == expected


@pytest.mark.parametrize(
    ("message", "language", "expected"),
    [
        ("estado del pago de $54.000 COP", SupportedLanguage.ES, [Decimal("54000")]),
        ("transacción de 125.000", SupportedLanguage.ES, [Decimal("125000")]),
        ("status do pagamento de R$ 219,90", SupportedLanguage.PT, [Decimal("219.90")]),
        ("status do pagamento de 1.219,90", SupportedLanguage.PT, [Decimal("1219.90")]),
    ],
)
def test_currency_symbols_and_codes_do_not_change_amount_normalization(
    message: str,
    language: SupportedLanguage,
    expected: list[Decimal],
) -> None:
    assert extract_locale_amounts(message, language) == expected


def test_ids_dates_and_times_do_not_supply_amount_provenance() -> None:
    message = "DEMO-ES-1001 del 2026-09-27 a las 12:30"
    assert extract_locale_amounts(message, SupportedLanguage.ES) == []


def test_non_locale_dot_decimal_is_not_partially_parsed() -> None:
    assert extract_locale_amounts("status do pagamento de 219.90", SupportedLanguage.PT) == []
    assert extract_single_locale_amount(
        "status do pagamento de 219.90",
        SupportedLanguage.PT,
    ) is None


@pytest.mark.parametrize(
    ("language", "message", "amount", "expected"),
    [
        (SupportedLanguage.ES, "$54.000 COP", Decimal("54000"), True),
        (SupportedLanguage.ES, "$54.000 COP", Decimal("54"), False),
        (SupportedLanguage.PT, "R$ 1.219,90", Decimal("1219.90"), True),
        (SupportedLanguage.PT, "R$ 1.219,90", Decimal("1.21990"), False),
    ],
)
def test_amount_provenance_compares_locale_normalized_values(
    language: SupportedLanguage,
    message: str,
    amount: Decimal,
    expected: bool,
) -> None:
    query = InterpretedTransactionQuery(amount=amount)
    assert InterpretationService._query_supported_by_message(
        query,
        message,
        language,
    ) is expected


@pytest.mark.parametrize(
    ("language", "amount", "currency", "expected"),
    [
        (SupportedLanguage.ES, Decimal("3250000.00"), "COP", "3.250.000,00 COP"),
        (SupportedLanguage.ES, Decimal("125000"), "COP", "125.000,00 COP"),
        (SupportedLanguage.PT, Decimal("8450.00"), "BRL", "8.450,00 BRL"),
        (SupportedLanguage.PT, Decimal("219.90"), "BRL", "219,90 BRL"),
    ],
)
def test_verified_amount_rendering_uses_supported_locale_separators(
    language: SupportedLanguage,
    amount: Decimal,
    currency: str,
    expected: str,
) -> None:
    assert format_locale_amount(amount, currency, language) == expected


def _client(tmp_path):
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(context))


def _session(client: TestClient, persona_id: str) -> dict:
    response = client.post("/api/demo/sessions", json={"persona_id": persona_id})
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    ("persona_id", "message", "expected_route", "expected_ids", "display"),
    [
        (
            "lucia",
            "¿Cuál es el estado del pago de 54.000?",
            "CLARIFY",
            ["DEMO-ES-1003", "DEMO-ES-1004"],
            None,
        ),
        (
            "lucia",
            "Busca la transacción de $125.000 COP.",
            "ANSWER",
            ["DEMO-ES-1001"],
            "125.000,00 COP",
        ),
        (
            "rafael",
            "Qual é o status do pagamento de R$ 219,90?",
            "ANSWER",
            ["DEMO-PT-2001"],
            "219,90 BRL",
        ),
    ],
)
def test_http_locale_amounts_resolve_owner_scoped_records(
    tmp_path,
    persona_id: str,
    message: str,
    expected_route: str,
    expected_ids: list[str],
    display: str | None,
) -> None:
    client = _client(tmp_path)
    session = _session(client, persona_id)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": message},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == expected_route
    if expected_route == "CLARIFY":
        assert body["clarification_transaction_ids"] == expected_ids
        assert body["reason_codes"] == ["ambiguous_transaction_match"]
    else:
        assert [tx["transaction_id"] for tx in body["transactions"]] == expected_ids
        assert display is not None
        assert display in body["response_text"]


def test_http_pt_thousands_decimal_is_parsed_even_when_no_owned_record_matches(
    tmp_path,
) -> None:
    client = _client(tmp_path)
    session = _session(client, "rafael")

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Qual é o status do pagamento de 1.219,90?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "CLARIFY"
    assert body["reason_codes"] == ["ownership_unverified", "trusted_record_missing"]
    assert body["clarification_transaction_ids"] == []
