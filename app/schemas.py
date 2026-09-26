from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
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


class PolicyIntent(StrEnum):
    """Normalized intent classes consumed by deterministic policy."""

    ACCOUNT_PRODUCT_INFO = "account_product_info"
    RECENT_TRANSACTION_HISTORY = "recent_transaction_history"
    TRANSACTION_LOOKUP = "transaction_lookup"
    TRANSACTION_STATUS = "transaction_status"
    PAYMENT_HISTORY = "payment_history"
    DECLINE_CAUSE = "decline_cause"
    MOVE_MONEY = "move_money"
    MUTATE_PAYMENT = "mutate_payment"
    BLOCK_CARD_OR_ACCOUNT = "block_card_or_account"
    MUTATE_ACCOUNT = "mutate_account"
    DISPUTE_ACTION = "dispute_action"
    CREDIT_ELIGIBILITY = "credit_eligibility"
    MODIFY_PROFILE = "modify_profile"
    UNKNOWN = "unknown"


class PolicyReason(StrEnum):
    SUPPORTED_VERIFIED = "supported_verified"
    UNAUTHORIZED_ACTIVITY_REPORTED = "unauthorized_activity_reported"
    OWNERSHIP_UNVERIFIED = "ownership_unverified"
    TRUSTED_RECORD_MISSING = "trusted_record_missing"
    TRUSTED_DATA_CONFLICT = "trusted_data_conflict"
    EXCLUDED_RELATIONSHIP_REQUIRED = "excluded_relationship_required"
    AMBIGUOUS_TRANSACTION_MATCH = "ambiguous_transaction_match"
    REQUIRED_PARAMETERS_MISSING = "required_parameters_missing"
    UNSUPPORTED_CAUSAL_EXPLANATION = "unsupported_causal_explanation"
    PROHIBITED_BANKING_ACTION = "prohibited_banking_action"
    UNSUPPORTED_INTENT = "unsupported_intent"


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


class InterpretationStatus(StrEnum):
    VERIFIED = "verified"
    SAFE_FALLBACK = "safe_fallback"


class InterpretationFallbackReason(StrEnum):
    PROVIDER_FAILURE = "provider_failure"
    INVALID_STRUCTURED_OUTPUT = "invalid_structured_output"


class TransactionReferenceStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    REQUIRED_MISSING = "required_missing"
    VERIFIED = "verified"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND_OR_NOT_OWNED = "not_found_or_not_owned"


class ModelInterpretationRequest(ContractModel):
    """Provider-facing input. Deliberately excludes identity and banking records."""

    language: SupportedLanguage
    message: str = Field(min_length=1, max_length=4000)
    previous_intent: PolicyIntent | None = None


class ModelInterpretation(ContractModel):
    """Untrusted structured extraction returned by the language model."""

    intent: PolicyIntent
    unauthorized_activity_asserted: bool
    transaction_id: str | None = Field(default=None, min_length=1, max_length=128)
    transaction_query: TransactionQuery | None = None


class VerifiedInterpretation(ContractModel):
    """Post-checked language interpretation with deterministic transaction resolution."""

    status: InterpretationStatus
    language: SupportedLanguage
    intent: PolicyIntent
    unauthorized_activity_asserted: bool
    transaction_id: str | None = Field(default=None, min_length=1, max_length=128)
    transaction_query: TransactionQuery | None = None
    transaction_reference_status: TransactionReferenceStatus
    candidate_transaction_ids: list[
        Annotated[str, Field(min_length=1, max_length=128)]
    ] = Field(default_factory=list, max_length=50)
    provider_attempts: int = Field(ge=0, le=5)
    lexical_unauthorized_override: bool = False
    fallback_reason: InterpretationFallbackReason | None = None
    requires_human_fallback: bool = False


class ConversationState(ContractModel):
    session_id: UUID
    language: SupportedLanguage
    previous_intent: str | None = Field(default=None, max_length=120)
    pending_query: TransactionQuery | None = None
    candidate_transaction_ids: list[
        Annotated[str, Field(min_length=1, max_length=128)]
    ] = Field(default_factory=list, max_length=50)
    clarification_required: bool = False


class CustomerSummary(ContractModel):
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
    """Operational transaction projection.

    Retrospective fraud labels/reference scores are intentionally absent.
    """

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


class PolicyInput(ContractModel):
    """Deterministic facts/signals available to the policy router.

    This contract has no fraud label or score fields. A later interpreter may
    classify language into these bounded signals, but policy remains authoritative.
    """

    intent: PolicyIntent
    unauthorized_activity_asserted: bool
    ownership_verified: bool
    trusted_record_found: bool
    trusted_data_conflict: bool
    excluded_relationship_required: bool
    ambiguous_transaction_match: bool
    required_parameters_missing: bool


class PolicyResult(ContractModel):
    route: RouteDecision
    reason_codes: list[PolicyReason] = Field(default_factory=list, max_length=20)
    safe_to_answer: bool = False
    mandatory_escalation: bool = False


class EscalationRequest(ContractModel):
    session_id: UUID
    transaction_id: str | None = Field(default=None, min_length=1, max_length=128)
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
