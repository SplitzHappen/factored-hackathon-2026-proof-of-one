from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import AuthenticatedSession, SupportedLanguage, TransactionQuery


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
