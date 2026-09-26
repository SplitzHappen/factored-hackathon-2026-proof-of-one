from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    AuthenticatedSession,
    PolicyInput,
    PolicyIntent,
    SupportedLanguage,
    TransactionQuery,
    TransactionRecord,
)


def test_transaction_query_has_no_customer_identity_field() -> None:
    query = TransactionQuery(amount=Decimal("125.50"))

    assert "customer_id" not in query.model_dump()


def test_unknown_fields_fail_closed() -> None:
    with pytest.raises(ValidationError):
        TransactionQuery(
            amount=Decimal("125.50"),
            customer_id="other-customer",
        )


def test_type_coercion_fails_closed() -> None:
    with pytest.raises(ValidationError):
        TransactionQuery(amount="125.50")


def test_authenticated_session_requires_server_context_shape() -> None:
    session = AuthenticatedSession(
        session_id=uuid4(),
        demo_persona_id="demo-es-001",
        customer_id="customer-001",
        language=SupportedLanguage.ES,
    )

    assert session.customer_id == "customer-001"


def test_policy_input_has_no_fraud_label_or_score_surface() -> None:
    policy_input = PolicyInput(intent=PolicyIntent.TRANSACTION_STATUS)

    assert "is_fraud" not in policy_input.model_dump()
    assert "fraud_score" not in policy_input.model_dump()

    with pytest.raises(ValidationError):
        PolicyInput(
            intent=PolicyIntent.TRANSACTION_STATUS,
            is_fraud=True,
        )

    with pytest.raises(ValidationError):
        PolicyInput(
            intent=PolicyIntent.TRANSACTION_STATUS,
            fraud_score=Decimal("99.00"),
        )


def test_operational_transaction_contract_rejects_retrospective_fraud_fields() -> None:
    from datetime import datetime

    with pytest.raises(ValidationError):
        TransactionRecord(
            transaction_id="txn-001",
            product_id="prd-001",
            occurred_at=datetime(2026, 9, 26, 12, 0, 0),
            amount=Decimal("42.00"),
            currency="COP",
            transaction_type="Payment",
            channel="App",
            transaction_country="Colombia",
            status="Approved",
            is_fraud=True,
        )
