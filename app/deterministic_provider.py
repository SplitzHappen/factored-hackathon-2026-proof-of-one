from __future__ import annotations

import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation

from app.interpretation import StructuredInterpretationProvider
from app.schemas import ModelInterpretationRequest, PolicyIntent


_TRANSACTION_ID = re.compile(r"\bDEMO-(?:ES|PT)-\d{4}\b", re.IGNORECASE)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(normalized.split())


class DeterministicDemoInterpretationProvider(StructuredInterpretationProvider):
    """Small deterministic interpreter for the public walking skeleton.

    It exists only so product integration does not depend on live provider selection.
    It has no banking-data access and returns the same structured contract expected
    from a later model adapter.
    """

    def extract(
        self,
        request: ModelInterpretationRequest,
        *,
        system_prompt: str,
        response_schema: dict[str, object],
    ) -> str:
        del system_prompt, response_schema
        message = _normalize(request.message)
        raw_id = _TRANSACTION_ID.search(request.message)
        transaction_id = raw_id.group(0).upper() if raw_id else None

        unauthorized = any(
            phrase in message
            for phrase in (
                "no reconozco",
                "no lo hice",
                "no la hice",
                "no autorice",
                "nao reconheco",
                "nao fui eu",
                "nao autorizei",
                "eu nao fiz",
            )
        )

        intent = self._intent(message, transaction_id is not None)
        amount = (
            self._explicit_amount(message)
            if transaction_id is None
            and intent in {
                PolicyIntent.TRANSACTION_LOOKUP,
                PolicyIntent.TRANSACTION_STATUS,
            }
            else None
        )

        return json.dumps(
            {
                "intent": intent.value,
                "unauthorized_activity_asserted": unauthorized,
                "transaction_id": transaction_id,
                "transaction_query": (
                    {"amount": str(amount)}
                    if amount is not None
                    else None
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    @staticmethod
    def _explicit_amount(message: str) -> Decimal | None:
        tokens = re.findall(r"(?<![A-Za-z0-9])\d+(?:[.,]\d{1,2})?(?![A-Za-z0-9])", message)
        if len(tokens) != 1:
            return None
        try:
            return Decimal(tokens[0].replace(",", "."))
        except InvalidOperation:
            return None

    @staticmethod
    def _intent(message: str, has_transaction_id: bool) -> PolicyIntent:
        if any(term in message for term in ("transfiere", "manda ", "transfira", "mova ")):
            return PolicyIntent.MOVE_MONEY
        if any(term in message for term in ("bloquea", "congelar", "bloqueie")):
            return PolicyIntent.BLOCK_CARD_OR_ACCOUNT
        if any(term in message for term in ("disputa", "disputar", "contestar")):
            return PolicyIntent.DISPUTE_ACTION
        if any(term in message for term in ("credito", "prestamo", "emprestimo")):
            return PolicyIntent.CREDIT_ELIGIBILITY
        if any(term in message for term in ("perfil", "datos personales", "dados pessoais")):
            return PolicyIntent.MODIFY_PROFILE
        if any(
            term in message
            for term in (
                "por que fue rechazada",
                "por que se rechazo",
                "por que a transacao",
                "o que causou",
                "que pudo haberlo provocado",
            )
        ):
            return PolicyIntent.DECLINE_CAUSE
        if any(
            term in message
            for term in (
                "actividad reciente",
                "ultimos movimientos",
                "ultimos lancamentos",
                "atividade recente",
            )
        ):
            return PolicyIntent.RECENT_TRANSACTION_HISTORY
        if any(term in message for term in ("estado", "status", "pendiente", "pendente")):
            return PolicyIntent.TRANSACTION_STATUS
        if has_transaction_id or any(
            term in message for term in ("transaccion", "transacao", "movimiento", "lancamento")
        ):
            return PolicyIntent.TRANSACTION_LOOKUP
        return PolicyIntent.UNKNOWN
