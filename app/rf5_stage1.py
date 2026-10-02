"""RF5 Stage 1 deterministic repair helpers.

This module is deliberately local and provider-free. It captures the bounded
Stage 1 implementation surface authorized by the Continuity RF5 final repair
scope record:

* monotonic raise-only cue coverage for M1 cue gaps;
* monotonic raise-only cue coverage for M2 money/payment-reference gaps;
* monotonic raise-only cue coverage for M4 scam/social-engineering gaps;
* a narrow FTP-2 failure-to-pay cleanup predicate that is not an escalation rule
  and must not be wired into suppression without replay evidence showing zero
  currently escalated positives lost.

The helper does not call, configure, or rely on a live semantic/provider layer.
It also does not decide IPA-M1 closure. Integration into the active escalation
path remains a separate product change/evidence gate.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RF5Stage1Finding:
    """One deterministic RF5 Stage 1 match."""

    family: str
    cue: str
    effect: str  # "raise" or "cleanup_candidate"
    anchor: str | None = None
    blocked_by: str | None = None


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(normalized.split())


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


_ACTIVITY = (
    r"cargo|cargos|cobro|cobros|compra|compras|pago|pagos|movimiento|movimientos|"
    r"operacion|operaciones|transaccion|transacciones|transferencia|transferencias|"
    r"debito|debitos|retiro|retiros|consumo|consumos|giro|giros|avance|avances|"
    r"cobranca|cobrancas|pagamento|pagamentos|lancamento|lancamentos|operacao|"
    r"operacoes|transacao|transacoes|pix|saque|saques|gasto|gastos|boleto|boletos|"
    r"ted|doc|movimento|movimentos|movimentacao|movimentacoes"
)
_ACCOUNT_OR_INSTRUMENT = (
    r"cuenta|cuentas|conta|contas|tarjeta|tarjetas|cartao|cartoes|app|aplicacion|"
    r"aplicativo|banca|internet banking|clave|senha|usuario|perfil"
)
_NO_AUTH = (
    r"sin (?:mi |mis |nuestra |nuestro )?(?:permiso|autorizacion|consentimiento|aprobacion|"
    r"conocimiento)"
    r"|sem (?:a |o )?(?:minha |meu |nossa |nosso )?(?:permissao|autorizacao|consentimento|"
    r"aprovacao|conhecimento)"
    r"|(?:yo|eu) (?:no|nao|nunca|jamas|jamais) (?:lo |la |los |las |o |a |os |as |me )?"
    r"(?:autorice|autorizei|aprobe|aprovei|pedi|solicite|solicitei)"
)
_NON_RECOGNITION = (
    r"(?:no|nao|nunca|jamas|jamais) (?:lo |la |los |las |o |a |os |as |me )?"
    r"(?:reconozco|reconoci|reconheco|reconheci|identifico|identifique|identifiquei)"
)
_AMOUNT = (
    r"(?:\$\s*)?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?"
    r"|(?:\$\s*)?\d+(?:[.,]\d+)?\s*(?:pesos|reais|dolares|euros|usd|brl|dop)"
    r"|(?:cien|doscientos|quinientos|mil|um|cem|quinhentos)\s+(?:pesos|reais|dolares)"
)
_SCAM = (
    r"estafa|estafaron|me estafaron|fraude|fraudulento|fraudulenta|phishing|suplantacion|"
    r"me enganaron|cai en una estafa|ca[yi] en un fraude|golpe|golpista|golpistas|"
    r"me deram um golpe|cai num golpe|cai em um golpe|cai em uma fraude|fui enganad[oa]"
)
_FAILURE_TO_PAY = (
    r"(?:no|nao|nunca|jamas|jamais) (?:pague|paguei|pude pagar|consegui pagar|"
    r"realice el pago|realizei o pagamento|hice el pago|fiz o pagamento)"
    r"|(?:se me olvido|me olvide de|olvide|esqueci de|me esqueci de) pagar"
    r"|(?:todavia|aun|ainda) (?:no|nao) (?:pague|paguei|he pagado|paguei)"
)
_DUE_CONTEXT = (
    r"cuota|cuotas|mensualidad|mensualidades|factura|facturas|boleto|boletos|prestamo|"
    r"prestamos|emprestimo|emprestimos|tarifa|tarifas|comision|comisiones|juros|interes|"
    r"intereses|parcela|parcelas|vencimiento|vencido|atrasad[oa]|mora"
)
_POSITIVE_LOSS_GUARD = (
    _NO_AUTH
    + r"|"
    + _NON_RECOGNITION
    + r"|desconocid[oa]|desconhecid[oa]|alguien|alguem|tercero|terceiro|hack|robo|robaron|roubo|roubaram|"
    + _SCAM
)

_M1_NO_AUTH_ACTIVITY = _rx(
    r"\b(?:" + _ACTIVITY + r"|" + _ACCOUNT_OR_INSTRUMENT + r")\b(?:\s+\S+){0,8}?\s+(?:" + _NO_AUTH + r")\b"
    r"|\b(?:" + _NO_AUTH + r")\b(?:\s+\S+){0,8}?\s+\b(?:" + _ACTIVITY + r"|" + _ACCOUNT_OR_INSTRUMENT + r")\b"
)
_M2_MONEY_DISOWNING = _rx(
    r"\b(?:" + _NON_RECOGNITION + r")\b(?:\s+\S+){0,10}?\s+(?:" + _AMOUNT + r")\b"
    r"|\b(?:" + _AMOUNT + r")\b(?:\s+\S+){0,10}?\s+(?:" + _NON_RECOGNITION + r")\b"
)
_M4_SCAM_ACTIVITY = _rx(
    r"\b(?:" + _SCAM + r")\b(?:\s+\S+){0,16}?\s+\b(?:" + _ACTIVITY + r"|" + _ACCOUNT_OR_INSTRUMENT + r")\b"
    r"|\b(?:" + _ACTIVITY + r"|" + _ACCOUNT_OR_INSTRUMENT + r")\b(?:\s+\S+){0,16}?\s+\b(?:" + _SCAM + r")\b"
)
_FTP2_CLEANUP_CANDIDATE = _rx(
    r"\b(?:" + _FAILURE_TO_PAY + r")\b(?:\s+\S+){0,10}?\s+\b(?:" + _DUE_CONTEXT + r")\b"
    r"|\b(?:" + _DUE_CONTEXT + r")\b(?:\s+\S+){0,10}?\s+\b(?:" + _FAILURE_TO_PAY + r")\b"
)
_POSITIVE_LOSS_GUARD_RX = _rx(r"\b(?:" + _POSITIVE_LOSS_GUARD + r")\b")


def rf5_stage1_findings(text: str) -> tuple[RF5Stage1Finding, ...]:
    """Return deterministic RF5 Stage 1 raise and cleanup-candidate findings."""

    normalized = _normalize(text)
    findings: list[RF5Stage1Finding] = []

    for family, pattern in (
        ("m1_no_authorization_activity", _M1_NO_AUTH_ACTIVITY),
        ("m2_money_reference_disowning", _M2_MONEY_DISOWNING),
        ("m4_scam_social_engineering_activity", _M4_SCAM_ACTIVITY),
    ):
        for match in pattern.finditer(normalized):
            findings.append(
                RF5Stage1Finding(
                    family=family,
                    cue=match.group(0),
                    effect="raise",
                    anchor=match.group(0),
                )
            )

    for match in _FTP2_CLEANUP_CANDIDATE.finditer(normalized):
        cue = match.group(0)
        blocked = "positive_loss_guard" if _POSITIVE_LOSS_GUARD_RX.search(cue) else None
        findings.append(
            RF5Stage1Finding(
                family="ftp2_failure_to_pay_cleanup_candidate",
                cue=cue,
                effect="cleanup_candidate",
                anchor=cue,
                blocked_by=blocked,
            )
        )

    return tuple(findings)


def rf5_stage1_should_raise(text: str) -> bool:
    """Return True when RF5 Stage 1 adds a deterministic raise-only cue."""

    return any(f.effect == "raise" for f in rf5_stage1_findings(text))


def rf5_stage1_failure_to_pay_cleanup_candidate(text: str) -> bool:
    """Return True for the narrow FTP-2 cleanup candidate when guards allow it.

    This is intentionally not an escalation decision. It is a predicate a later
    integration may use only after replay evidence confirms zero currently
    escalated positives are lost.
    """

    return any(
        f.family == "ftp2_failure_to_pay_cleanup_candidate" and f.blocked_by is None
        for f in rf5_stage1_findings(text)
    )
