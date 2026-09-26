from __future__ import annotations

from datetime import date

from app.bank import BankRepository
from app.interpretation import InterpretationService
from app.policy import route_policy
from app.runtime import OperationalStore
from app.schemas import (
    AuthenticatedSession,
    ConversationState,
    CustomerTurnResponse,
    EscalationRequest,
    PolicyInput,
    PolicyIntent,
    PolicyReason,
    RouteDecision,
    SupportedLanguage,
    TransactionRecord,
    TransactionReferenceStatus,
)


class CustomerResolutionService:
    """End-to-end deterministic orchestration after language interpretation."""

    def __init__(
        self,
        *,
        bank: BankRepository,
        store: OperationalStore,
        interpreter: InterpretationService,
        synthetic_data: bool,
    ) -> None:
        self.bank = bank
        self.store = store
        self.interpreter = interpreter
        self.synthetic_data = synthetic_data

    def resolve_turn(
        self,
        *,
        session: AuthenticatedSession,
        message: str,
        reference_date: date,
    ) -> CustomerTurnResponse:
        previous_state = self.store.get_conversation_state(session)
        previous_intent = (
            PolicyIntent(previous_state.previous_intent)
            if previous_state is not None and previous_state.previous_intent is not None
            else None
        )
        interpretation = self.interpreter.interpret(
            session=session,
            message=message,
            reference_date=reference_date,
            previous_intent=previous_intent,
        )

        reference_status = interpretation.transaction_reference_status
        missing_or_unowned = (
            reference_status is TransactionReferenceStatus.NOT_FOUND_OR_NOT_OWNED
        )
        policy = route_policy(
            PolicyInput(
                intent=interpretation.intent,
                unauthorized_activity_asserted=(
                    interpretation.unauthorized_activity_asserted
                ),
                ownership_verified=not missing_or_unowned,
                trusted_record_found=not missing_or_unowned,
                trusted_data_conflict=False,
                excluded_relationship_required=False,
                ambiguous_transaction_match=(
                    reference_status is TransactionReferenceStatus.AMBIGUOUS
                ),
                required_parameters_missing=(
                    reference_status is TransactionReferenceStatus.REQUIRED_MISSING
                ),
            )
        )

        transactions = self._answer_transactions(
            session=session,
            intent=interpretation.intent,
            verified_transaction_id=interpretation.verified_transaction_id,
            safe_to_answer=policy.safe_to_answer,
        )

        clarification_ids = (
            interpretation.candidate_transaction_ids[:10]
            if policy.route is RouteDecision.CLARIFY
            and reference_status is TransactionReferenceStatus.AMBIGUOUS
            else []
        )

        ticket_id = None
        if policy.route is RouteDecision.ESCALATE:
            escalation = self.store.create_escalation_ticket(
                session,
                EscalationRequest(
                    session_id=session.session_id,
                    transaction_id=interpretation.verified_transaction_id,
                    reason_code=policy.reason_codes[0].value,
                    summary=self._escalation_summary(session.language),
                ),
            )
            ticket_id = escalation.ticket_id

        self.store.save_conversation_state(
            session,
            ConversationState(
                session_id=session.session_id,
                language=session.language,
                previous_intent=interpretation.intent.value,
                pending_query=None,
                candidate_transaction_ids=interpretation.candidate_transaction_ids,
                clarification_required=policy.route is RouteDecision.CLARIFY,
            ),
        )

        return CustomerTurnResponse(
            session_id=session.session_id,
            route=policy.route,
            intent=interpretation.intent,
            response_text=self._response_text(
                language=session.language,
                route=policy.route,
                reason_codes=policy.reason_codes,
                transactions=transactions,
                clarification_transaction_ids=clarification_ids,
            ),
            reason_codes=policy.reason_codes,
            transactions=transactions,
            clarification_transaction_ids=clarification_ids,
            escalation_ticket_id=ticket_id,
            handoff_available=policy.route in {
                RouteDecision.ABSTAIN,
                RouteDecision.ESCALATE,
            }
            or missing_or_unowned,
            synthetic_data=self.synthetic_data,
        )

    def _answer_transactions(
        self,
        *,
        session: AuthenticatedSession,
        intent: PolicyIntent,
        verified_transaction_id: str | None,
        safe_to_answer: bool,
    ) -> list[TransactionRecord]:
        if not safe_to_answer:
            return []

        if verified_transaction_id is not None:
            transaction = self.bank.get_transaction(
                session.customer_id,
                verified_transaction_id,
            )
            return [transaction] if transaction is not None else []

        if intent in {
            PolicyIntent.RECENT_TRANSACTION_HISTORY,
            PolicyIntent.PAYMENT_HISTORY,
        }:
            return self.bank.list_recent_transactions(
                session.customer_id,
                limit=3,
            )

        return []

    @staticmethod
    def _escalation_summary(language: SupportedLanguage) -> str:
        if language is SupportedLanguage.PT:
            return "O cliente informou atividade que não reconhece; encaminhamento humano verificado."
        return "El cliente informó actividad que no reconoce; derivación humana verificada."

    @staticmethod
    def _localized_status(
        status: str,
        language: SupportedLanguage,
    ) -> str:
        labels = {
            "Approved": {
                SupportedLanguage.ES: "aprobada",
                SupportedLanguage.PT: "aprovada",
            },
            "Pending": {
                SupportedLanguage.ES: "pendiente",
                SupportedLanguage.PT: "pendente",
            },
            "Declined": {
                SupportedLanguage.ES: "rechazada",
                SupportedLanguage.PT: "recusada",
            },
            "Reversed": {
                SupportedLanguage.ES: "revertida",
                SupportedLanguage.PT: "estornada",
            },
        }
        return labels.get(status, {}).get(language, status)

    @staticmethod
    def _response_text(
        *,
        language: SupportedLanguage,
        route: RouteDecision,
        reason_codes: list[PolicyReason],
        transactions: list[TransactionRecord],
        clarification_transaction_ids: list[str],
    ) -> str:
        pt = language is SupportedLanguage.PT

        if route is RouteDecision.ANSWER:
            if len(transactions) == 1:
                tx = transactions[0]
                localized_status = CustomerResolutionService._localized_status(
                    tx.status,
                    language,
                )
                if pt:
                    return (
                        f"A transação {tx.transaction_id} está {localized_status}. "
                        f"Valor registrado: {tx.amount} {tx.currency}."
                    )
                return (
                    f"La transacción {tx.transaction_id} está {localized_status}. "
                    f"Importe registrado: {tx.amount} {tx.currency}."
                )
            if transactions:
                if pt:
                    return (
                        f"Encontrei {len(transactions)} lançamentos recentes verificados "
                        "na sua conta."
                    )
                return (
                    f"Encontré {len(transactions)} movimientos recientes verificados "
                    "en tu cuenta."
                )
            return (
                "La información solicitada está verificada."
                if not pt
                else "A informação solicitada está verificada."
            )

        if route is RouteDecision.CLARIFY:
            missing_record = any(
                reason in {
                    PolicyReason.OWNERSHIP_UNVERIFIED,
                    PolicyReason.TRUSTED_RECORD_MISSING,
                }
                for reason in reason_codes
            )
            if pt:
                if missing_record:
                    return (
                        "Não consegui vincular essa referência a um registro verificável da "
                        "sua conta. Confira a referência ou use o atendimento humano."
                    )
                options = ", ".join(clarification_transaction_ids)
                return (
                    "Encontrei mais de uma possibilidade. Escolha uma destas referências: "
                    f"{options}."
                )
            if missing_record:
                return (
                    "No pude vincular esa referencia a un registro verificable de tu cuenta. "
                    "Revisa la referencia o utiliza la atención humana."
                )
            options = ", ".join(clarification_transaction_ids)
            return (
                "Encontré más de una posibilidad. Elige una de estas referencias: "
                f"{options}."
            )

        if route is RouteDecision.ESCALATE:
            return (
                "Registré una derivación humana verificada por la actividad que indicaste "
                "que no reconoces."
                if not pt
                else "Registrei um encaminhamento humano verificado para a atividade que "
                "você informou não reconhecer."
            )

        if PolicyReason.PROHIBITED_BANKING_ACTION in reason_codes:
            return (
                "No puedo ejecutar cambios o movimientos bancarios desde este asistente. "
                "La atención humana está disponible para continuar."
                if not pt
                else "Não posso executar alterações ou movimentações bancárias neste "
                "assistente. O atendimento humano está disponível para continuar."
            )

        if PolicyReason.UNSUPPORTED_CAUSAL_EXPLANATION in reason_codes:
            return (
                "No tengo una causa verificada para ese rechazo y no voy a inventarla. "
                "La atención humana está disponible para revisarlo."
                if not pt
                else "Não tenho uma causa verificada para essa recusa e não vou inventá-la. "
                "O atendimento humano está disponível para revisar."
            )

        return (
            "No puedo resolver esa solicitud de forma segura aquí. La atención humana está disponible."
            if not pt
            else "Não consigo resolver essa solicitação com segurança aqui. O atendimento humano está disponível."
        )
