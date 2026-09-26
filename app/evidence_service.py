from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.bank import BankRepository
from app.behavioral_evidence import (
    BehavioralEvidenceResult,
    behavioral_evidence_contract_sha256,
    compute_behavioral_evidence,
)
from app.runtime import OperationalStore
from app.schemas import AuthenticatedSession, ContractModel


class EvidenceAccessPath(StrEnum):
    CUSTOMER_SESSION = "customer_session"
    VERIFIED_ESCALATION_TICKET = "verified_escalation_ticket"


class EvidenceAccessError(RuntimeError):
    """Raised when a claimed customer session is not server-persisted exactly."""


class TransactionBehavioralEvidence(ContractModel):
    """Target-free behavioral evidence returned through a verified access path."""

    transaction_id: str = Field(min_length=1, max_length=128)
    access_path: EvidenceAccessPath
    ticket_id: UUID | None = None
    behavioral_evidence_contract_sha256: str = Field(
        min_length=64,
        max_length=64,
    )
    evidence: BehavioralEvidenceResult


class BehavioralEvidenceService:
    """Connect frozen behavioral semantics to verified runtime access paths.

    This service has no dependency on policy routing and has no authority to
    escalate, suppress escalation, prioritize a queue, or authorize an action.
    """

    def __init__(
        self,
        bank_repository: BankRepository,
        operational_store: OperationalStore,
    ) -> None:
        self.bank_repository = bank_repository
        self.operational_store = operational_store

    def for_customer_session(
        self,
        session: AuthenticatedSession,
        transaction_id: str,
    ) -> TransactionBehavioralEvidence | None:
        """Return evidence only for the exact persisted customer session."""

        persisted = self.operational_store.get_authenticated_session(
            session.session_id
        )
        if persisted is None:
            raise EvidenceAccessError(
                "Customer evidence requires a persisted authenticated session."
            )
        if persisted != session:
            raise EvidenceAccessError(
                "Customer evidence session does not match server-persisted identity."
            )

        return self._build(
            authenticated_customer_id=session.customer_id,
            transaction_id=transaction_id,
            access_path=EvidenceAccessPath.CUSTOMER_SESSION,
            ticket_id=None,
        )

    def for_verified_escalation_ticket(
        self,
        ticket_id: UUID,
    ) -> TransactionBehavioralEvidence | None:
        """Return evidence through ticket -> session -> customer -> transaction."""

        context = self.operational_store.resolve_verified_escalation_context(
            ticket_id
        )
        if context is None:
            return None

        return self._build(
            authenticated_customer_id=context.session.customer_id,
            transaction_id=context.transaction_id,
            access_path=EvidenceAccessPath.VERIFIED_ESCALATION_TICKET,
            ticket_id=context.ticket_id,
        )

    def _build(
        self,
        *,
        authenticated_customer_id: str,
        transaction_id: str,
        access_path: EvidenceAccessPath,
        ticket_id: UUID | None,
    ) -> TransactionBehavioralEvidence | None:
        facts = self.bank_repository.get_behavioral_evidence_input(
            authenticated_customer_id,
            transaction_id,
        )
        if facts is None:
            return None

        return TransactionBehavioralEvidence(
            transaction_id=transaction_id,
            access_path=access_path,
            ticket_id=ticket_id,
            behavioral_evidence_contract_sha256=(
                behavioral_evidence_contract_sha256()
            ),
            evidence=compute_behavioral_evidence(facts),
        )
