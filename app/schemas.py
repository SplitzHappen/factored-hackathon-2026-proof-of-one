from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Reject unknown fields at service boundaries."""

    model_config = ConfigDict(extra="forbid", strict=True)


class SupportedLanguage(StrEnum):
    ES = "es"
    PT = "pt"


class RouteDecision(StrEnum):
    ANSWER = "ANSWER"
    CLARIFY = "CLARIFY"
    ABSTAIN = "ABSTAIN"
    ESCALATE = "ESCALATE"


class HealthResponse(ContractModel):
    status: str
    service: str
    llm_connected: bool


class AuthenticatedSession(ContractModel):
    """Server-controlled authenticated context; never model-controlled."""

    session_id: UUID
    demo_persona_id: str = Field(min_length=1, max_length=128)
    customer_id: str = Field(min_length=1, max_length=128)
    language: SupportedLanguage


class TransactionQuery(ContractModel):
    """Bounded transaction filters. Deliberately contains no customer_id."""

    date_from: date | None = None
    date_to: date | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    transaction_type: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, max_length=80)
    limit: int = Field(default=10, ge=1, le=50)


class ConversationState(ContractModel):
    session_id: UUID
    language: SupportedLanguage
    previous_intent: str | None = Field(default=None, max_length=120)
    pending_query: TransactionQuery | None = None
    candidate_transaction_ids: list[str] = Field(default_factory=list, max_length=50)
    clarification_required: bool = False


class CustomerSummary(ContractModel):
    country: str
    detected_accent: str | None = None
    customer_status: str


class ProductRecord(ContractModel):
    product_id: str
    product_type: str
    currency: str = Field(min_length=3, max_length=3)
    current_balance: Decimal
    opening_date: date
    expiration_date: date | None = None
    product_status: str
    last_transaction_date: datetime | None = None


class TransactionRecord(ContractModel):
    transaction_id: str
    product_id: str
    occurred_at: datetime
    amount: Decimal
    currency: str = Field(min_length=3, max_length=3)
    transaction_type: str
    transaction_category: str | None = None
    channel: str
    merchant_name: str | None = None
    merchant_category: str | None = None
    transaction_country: str
    transaction_city: str | None = None
    status: str
    is_fraud: bool
    fraud_score: Decimal | None = None


class PolicyResult(ContractModel):
    route: RouteDecision
    reason_codes: list[str] = Field(default_factory=list, max_length=20)
    safe_to_answer: bool = False
    mandatory_escalation: bool = False


class EscalationRequest(ContractModel):
    session_id: UUID
    transaction_id: str | None = None
    reason_code: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=500)


class EscalationRecord(ContractModel):
    ticket_id: UUID
    session_id: UUID
    created_at: datetime
    persisted: bool
    verified: bool


class EvaluationRecord(ContractModel):
    case_id: str
    route: RouteDecision
    safe: bool
    correct: bool
    grounded: bool
    latency_ms: int = Field(ge=0)
    estimated_cost_usd: Decimal = Field(ge=0)
