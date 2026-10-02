from __future__ import annotations

from datetime import date

from app.amounts import format_locale_amount
from app.bank import BankRepository
from app.interpretation import InterpretationService
from app.policy import route_policy
from app.runtime import OperationalStore
from app.schemas import (
    AuthenticatedSession,
    ConversationState,
    CustomerTurnResponse,
    EscalationRecord,
    EscalationRequest,
    InterpretationStatus,
    PolicyInput,
    PolicyIntent,
    PolicyReason,
    ProductRecord,
    RouteDecision,
    SupportedLanguage,
    TransactionQuery,
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
        account_products = (
            self.bank.list_customer_products(session.customer_id)
            if interpretation.intent is PolicyIntent.ACCOUNT_PRODUCT_INFO
            else []
        )
        trusted_record_missing = (
            missing_or_unowned
            or (
                interpretation.intent is PolicyIntent.ACCOUNT_PRODUCT_INFO
                and not account_products
            )
        )
        policy = route_policy(
            PolicyInput(
                intent=interpretation.intent,
                unauthorized_activity_asserted=(
                    interpretation.unauthorized_activity_asserted
                ),
                possible_unauthorized_activity=(
                    interpretation.possible_unauthorized_activity
                ),
                ownership_verified=not missing_or_unowned,
                trusted_record_found=not trusted_record_missing,
                trusted_data_conflict=False,
                excluded_relationship_required=False,
                interpretation_unavailable=(
                    interpretation.status is InterpretationStatus.SAFE_FALLBACK
                    and interpretation.requires_human_fallback
                ),
                ambiguous_transaction_match=(
                    reference_status is TransactionReferenceStatus.AMBIGUOUS
                ),
                required_parameters_missing=(
                    reference_status is TransactionReferenceStatus.REQUIRED_MISSING
                ),
            )
        )

        products = (
            account_products
            if policy.safe_to_answer
            and interpretation.intent is PolicyIntent.ACCOUNT_PRODUCT_INFO
            else []
        )
        transactions = self._answer_transactions(
            session=session,
            intent=interpretation.intent,
            verified_transaction_id=interpretation.verified_transaction_id,
            safe_to_answer=policy.safe_to_answer,
        )

        clarification_candidates: list[TransactionRecord] = []
        if (
            policy.route is RouteDecision.CLARIFY
            and reference_status is TransactionReferenceStatus.AMBIGUOUS
        ):
            for candidate_id in interpretation.candidate_transaction_ids[:10]:
                candidate = self.bank.get_transaction(
                    session.customer_id,
                    candidate_id,
                )
                if candidate is not None:
                    clarification_candidates.append(candidate)
        clarification_ids = [
            candidate.transaction_id for candidate in clarification_candidates
        ]

        ticket_id = None
        if policy.route is RouteDecision.ESCALATE:
            escalation = self.store.create_escalation_ticket(
                session,
                EscalationRequest(
                    session_id=session.session_id,
                    transaction_id=interpretation.verified_transaction_id,
                    reason_code=policy.reason_codes[0].value,
                    summary=self._escalation_summary(
                        session.language,
                        policy.reason_codes[0],
                    ),
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
                intent=interpretation.intent,
                reason_codes=policy.reason_codes,
                products=products,
                transactions=transactions,
                clarification_transactions=clarification_candidates,
                clarification_total_count=len(
                    interpretation.candidate_transaction_ids
                ),
            ),
            reason_codes=policy.reason_codes,
            products=products,
            transactions=transactions,
            clarification_transaction_ids=clarification_ids,
            escalation_ticket_id=ticket_id,
            handoff_available=(
                policy.route is RouteDecision.ABSTAIN
                or missing_or_unowned
            ),
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
            if transaction is None:
                return []
            if (
                intent is PolicyIntent.PAYMENT_HISTORY
                and transaction.transaction_type.casefold() != "payment"
            ):
                return []
            return [transaction]

        if intent is PolicyIntent.RECENT_TRANSACTION_HISTORY:
            return self.bank.list_recent_transactions(
                session.customer_id,
                limit=3,
            )

        if intent is PolicyIntent.PAYMENT_HISTORY:
            return self.bank.find_transactions(
                session.customer_id,
                TransactionQuery(
                    transaction_type="Payment",
                    limit=3,
                ),
            )

        return []

    def create_support_handoff(
        self,
        *,
        session: AuthenticatedSession,
    ) -> EscalationRecord:
        """Persist an explicit customer-requested demo support ticket."""

        return self.store.create_escalation_ticket(
            session,
            EscalationRequest(
                session_id=session.session_id,
                transaction_id=None,
                reason_code="customer_requested_support",
                summary=self._support_summary(session.language),
            ),
        )

    @staticmethod
    def _support_summary(language: SupportedLanguage) -> str:
        if language is SupportedLanguage.PT:
            return "O cliente solicitou revisão humana no demo."
        return "El cliente solicitó revisión humana en el demo."

    @staticmethod
    def _escalation_summary(
        language: SupportedLanguage,
        reason: PolicyReason,
    ) -> str:
        pt = language is SupportedLanguage.PT
        if reason is PolicyReason.UNAUTHORIZED_ACTIVITY_REPORTED:
            return (
                "Caso registrado após sinal explícito de atividade não reconhecida."
                if pt
                else "Caso registrado tras una señal explícita de actividad no reconocida."
            )
        if reason is PolicyReason.POSSIBLE_UNAUTHORIZED_ACTIVITY:
            return (
                "Caso registrado para revisão humana de possível atividade não reconhecida."
                if pt
                else "Caso registrado para revisión humana de posible actividad no reconocida."
            )
        if reason is PolicyReason.INTERPRETATION_UNAVAILABLE:
            return (
                "Caso registrado porque la interpretación automática no estuvo disponible."
                if not pt
                else "Caso registrado porque a interpretação automática não esteve disponível."
            )
        if reason is PolicyReason.TRUSTED_DATA_CONFLICT:
            return (
                "Caso registrado porque os dados verificados exigem revisão."
                if pt
                else "Caso registrado porque los datos verificados requieren revisión."
            )
        if reason is PolicyReason.EXCLUDED_RELATIONSHIP_REQUIRED:
            return (
                "Caso registrado porque a solicitação exige informação fora do escopo."
                if pt
                else "Caso registrado porque la solicitud requiere información fuera del alcance."
            )
        return (
            "Caso registrado para revisão humana no demo."
            if pt
            else "Caso registrado para revisión humana en el demo."
        )

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
        intent: PolicyIntent,
        reason_codes: list[PolicyReason],
        products: list[ProductRecord],
        transactions: list[TransactionRecord],
        clarification_transactions: list[TransactionRecord],
        clarification_total_count: int,
    ) -> str:
        pt = language is SupportedLanguage.PT

        if route is RouteDecision.ANSWER:
            if intent is PolicyIntent.ACCOUNT_PRODUCT_INFO:
                if not products:
                    raise RuntimeError(
                        "ACCOUNT_PRODUCT_INFO cannot answer without verified product facts"
                    )
                if pt:
                    details = "; ".join(
                        f"{product.product_type}: saldo "
                        f"{format_locale_amount(product.current_balance, product.currency, language)} "
                        f"({product.product_status})"
                        for product in products
                    )
                    return f"Produtos verificados da sua conta: {details}."
                details = "; ".join(
                    f"{product.product_type}: saldo "
                    f"{format_locale_amount(product.current_balance, product.currency, language)} "
                    f"({product.product_status})"
                    for product in products
                )
                return f"Productos verificados de tu cuenta: {details}."

            if intent is PolicyIntent.PAYMENT_HISTORY and not transactions:
                return (
                    "No encontré pagos recientes verificables en tu cuenta."
                    if not pt
                    else "Não encontrei pagamentos recentes verificáveis na sua conta."
                )

            if len(transactions) == 1:
                tx = transactions[0]
                localized_status = CustomerResolutionService._localized_status(
                    tx.status,
                    language,
                )
                if pt:
                    return (
                        f"A transação {tx.transaction_id} está {localized_status}. "
                        f"Valor registrado: "
                        f"{format_locale_amount(tx.amount, tx.currency, language)}."
                    )
                return (
                    f"La transacción {tx.transaction_id} está {localized_status}. "
                    f"Importe registrado: "
                    f"{format_locale_amount(tx.amount, tx.currency, language)}."
                )
            if transactions:
                if intent is PolicyIntent.PAYMENT_HISTORY:
                    if pt:
                        return (
                            f"Encontrei {len(transactions)} pagamentos recentes verificados "
                            "na sua conta."
                        )
                    return (
                        f"Encontré {len(transactions)} pagos recientes verificados "
                        "en tu cuenta."
                    )
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
                        "sua conta. Confira a referência ou solicite uma revisão humana neste demo."
                    )
                if clarification_transactions:
                    options = "; ".join(
                        f"{tx.transaction_id} — {tx.occurred_at.date().isoformat()} — "
                        f"{format_locale_amount(tx.amount, tx.currency, language)} — "
                        f"{tx.merchant_name or tx.transaction_type}"
                        for tx in clarification_transactions
                    )
                    shown = len(clarification_transactions)
                    count_note = (
                        f" Mostrando {shown} de {clarification_total_count} resultados."
                        if clarification_total_count > shown
                        else ""
                    )
                    return (
                        "Encontrei mais de uma possibilidade verificada na sua conta. "
                        f"{options}.{count_note} Envie uma referência explícita para uma nova "
                        "verificação."
                    )
                return "Preciso de mais detalhes para identificar o lançamento com segurança."
            if missing_record:
                return (
                    "No pude vincular esa referencia a un registro verificable de tu cuenta. "
                    "Revisa la referencia o solicita una revisión humana en este demo."
                )
            if clarification_transactions:
                options = "; ".join(
                    f"{tx.transaction_id} — {tx.occurred_at.date().isoformat()} — "
                    f"{format_locale_amount(tx.amount, tx.currency, language)} — "
                    f"{tx.merchant_name or tx.transaction_type}"
                    for tx in clarification_transactions
                )
                shown = len(clarification_transactions)
                count_note = (
                    f" Mostrando {shown} de {clarification_total_count} resultados."
                    if clarification_total_count > shown
                    else ""
                )
                return (
                    "Encontré más de una posibilidad verificada en tu cuenta. "
                    f"{options}.{count_note} Envía una referencia explícita para una nueva "
                    "verificación."
                )
            return "Necesito más detalles para identificar el movimiento de forma segura."

        if route is RouteDecision.ESCALATE:
            if PolicyReason.INTERPRETATION_UNAVAILABLE in reason_codes:
                return (
                    "No pude interpretar tu solicitud de forma confiable. Registré este caso "
                    "para revisión humana en el demo."
                    if not pt
                    else "Não consegui interpretar sua solicitação com confiança. Registrei "
                    "este caso para revisão humana no demo."
                )
            if PolicyReason.TRUSTED_DATA_CONFLICT in reason_codes:
                return (
                    "Registré este caso para revisión humana en el demo porque los datos "
                    "verificados requieren revisión."
                    if not pt
                    else "Registrei este caso para revisão humana no demo porque os dados "
                    "verificados exigem revisão."
                )
            if PolicyReason.EXCLUDED_RELATIONSHIP_REQUIRED in reason_codes:
                return (
                    "Registré este caso para revisión humana en el demo porque requiere "
                    "información fuera del alcance de este asistente."
                    if not pt
                    else "Registrei este caso para revisão humana no demo porque exige "
                    "informação fora do alcance deste assistente."
                )
            return (
                "Registré este caso para revisión humana en el demo."
                if not pt
                else "Registrei este caso para revisão humana no demo."
            )

        if PolicyReason.PROHIBITED_BANKING_ACTION in reason_codes:
            return (
                "No puedo ejecutar cambios o movimientos bancarios desde este asistente. "
                "Puedes solicitar una revisión humana en este demo."
                if not pt
                else "Não posso executar alterações ou movimentações bancárias neste "
                "assistente. Você pode solicitar uma revisão humana neste demo."
            )

        if PolicyReason.UNSUPPORTED_CAUSAL_EXPLANATION in reason_codes:
            return (
                "No tengo una causa verificada para explicar por qué esa operación tuvo "
                "ese resultado y no voy a inventarla. Puedes solicitar una revisión humana "
                "en este demo."
                if not pt
                else "Não tenho uma causa verificada para explicar por que essa operação "
                "teve esse resultado e não vou inventá-la. Você pode solicitar uma revisão "
                "humana neste demo."
            )

        return (
            "No puedo resolver esa solicitud de forma segura aquí. Puedes solicitar una revisión humana en este demo."
            if not pt
            else "Não consigo resolver essa solicitação com segurança aqui. Você pode solicitar uma revisão humana neste demo."
        )
