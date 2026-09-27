from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.customer_service import CustomerResolutionService
from app.schemas import (
    PolicyIntent,
    PolicyReason,
    RouteDecision,
    SupportedLanguage,
    TransactionRecord,
)


def _candidate(index: int, *, currency: str, amount: Decimal) -> TransactionRecord:
    return TransactionRecord(
        transaction_id=f"DEMO-CAND-{index:04d}",
        product_id="DEMO-PROD-001",
        occurred_at=datetime(2026, 9, index + 1, 12, 0, tzinfo=timezone.utc),
        amount=amount,
        currency=currency,
        transaction_type="Payment",
        transaction_category="Retail",
        channel="App",
        merchant_name=f"Merchant {index}",
        merchant_category="Retail",
        transaction_country="Colombia" if currency == "COP" else "Brazil",
        transaction_city="Bogota" if currency == "COP" else "Sao Paulo",
        status="Approved",
    )


@pytest.mark.parametrize(
    ("language", "currency", "amount", "amount_text", "count_text", "prompt_text"),
    [
        (
            SupportedLanguage.ES,
            "COP",
            Decimal("54000"),
            "54.000,00 COP",
            "Mostrando 10 de 12 resultados.",
            "Envía una referencia explícita para una nueva verificación.",
        ),
        (
            SupportedLanguage.PT,
            "BRL",
            Decimal("142.75"),
            "142,75 BRL",
            "Mostrando 10 de 12 resultados.",
            "Envie uma referência explícita para uma nova verificação.",
        ),
    ],
)
def test_clarification_candidates_show_context_and_truncation(
    language: SupportedLanguage,
    currency: str,
    amount: Decimal,
    amount_text: str,
    count_text: str,
    prompt_text: str,
) -> None:
    candidates = [
        _candidate(index, currency=currency, amount=amount)
        for index in range(10)
    ]

    response = CustomerResolutionService._response_text(
        language=language,
        route=RouteDecision.CLARIFY,
        intent=PolicyIntent.TRANSACTION_LOOKUP,
        reason_codes=[PolicyReason.AMBIGUOUS_TRANSACTION_MATCH],
        products=[],
        transactions=[],
        clarification_transactions=candidates,
        clarification_total_count=12,
    )

    assert "DEMO-CAND-0000" in response
    assert "2026-09-01" in response
    assert amount_text in response
    assert "Merchant 0" in response
    assert count_text in response
    assert prompt_text in response


def test_clarification_does_not_claim_truncation_when_all_candidates_are_shown() -> None:
    candidates = [
        _candidate(index, currency="COP", amount=Decimal("54000"))
        for index in range(2)
    ]

    response = CustomerResolutionService._response_text(
        language=SupportedLanguage.ES,
        route=RouteDecision.CLARIFY,
        intent=PolicyIntent.TRANSACTION_LOOKUP,
        reason_codes=[PolicyReason.AMBIGUOUS_TRANSACTION_MATCH],
        products=[],
        transactions=[],
        clarification_transactions=candidates,
        clarification_total_count=2,
    )

    assert "Mostrando" not in response
    assert "DEMO-CAND-0000" in response
    assert "DEMO-CAND-0001" in response
