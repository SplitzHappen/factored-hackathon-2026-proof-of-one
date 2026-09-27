from __future__ import annotations

import re
import unicodedata


def normalize_unauthorized_text(text: str) -> str:
    """Normalize customer text for deterministic explicit-assertion checks."""

    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(normalized.split())


# These patterns are deliberately assertion-oriented. They cover explicit
# non-recognition, first-person denial, lack of authorization, and direct
# statements that the activity belongs to someone else. They do not treat
# surprise, concern, unusualness, decline status, or a question about fraud as
# an unauthorized-activity assertion.
_UNAUTHORIZED_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Spanish: non-recognition.
    re.compile(r"\bno (?:reconozco|reconoci|identifico)\b"),
    re.compile(r"\b(?:desconozco|desconoci) (?:ese|esa|este|esta|el|la)?\s*(?:cargo|cobro|compra|pago|movimiento|operacion|transaccion)?\b"),
    # Spanish: explicit first-person denial / not mine.
    re.compile(r"\bno fui yo\b"),
    re.compile(r"\byo no (?:hice|realice|efectue|autorice|aprobe)\b"),
    re.compile(r"\bno (?:lo|la) (?:hice|realice|autorice|aprobe)\b"),
    re.compile(r"\b(?:ese|esa|este|esta|el|la) (?:cargo|cobro|compra|pago|movimiento|operacion|transaccion)(?: [a-z0-9-]+)? no (?:es|fue) mi[oa]\b"),
    re.compile(r"\bno (?:es|fue) mi[oa] (?:compra|operacion|transaccion)\b"),
    re.compile(r"\b(?:es|fue) (?:ajeno|ajena|de otra persona)\b"),
    re.compile(r"\b(?:lo|la|eso|esto) hizo otra persona\b"),
    # Spanish: explicit absence of authorization.
    re.compile(r"\bno (?:autorice|di autorizacion|di permiso|aprobe)\b"),
    re.compile(r"\byo (?:jamas|nunca) (?:autorice|aprobe|di autorizacion|di permiso)\b"),
    re.compile(r"\bsin mi (?:autorizacion|permiso|consentimiento)\b"),
    re.compile(r"\b(?:me|lo|la) (?:cobraron|cargaron|debitaron) sin (?:mi )?(?:autorizacion|permiso|consentimiento)\b"),
    re.compile(r"\bme hicieron un (?:cargo|cobro) sin mi (?:autorizacion|permiso|consentimiento)\b"),
    # Portuguese: non-recognition.
    re.compile(r"\bnao (?:reconheco|reconheci|identifico)\b"),
    re.compile(r"\bdesconheco (?:essa|esta|esse|este|a|o)?\s*(?:cobranca|compra|pagamento|lancamento|operacao|transacao)?\b"),
    # Portuguese: explicit first-person denial / not mine.
    re.compile(r"\bnao fui eu\b"),
    re.compile(r"\beu nao (?:fiz|realizei|efetuei|autorizei|aprovei)\b"),
    re.compile(r"\bnao (?:fiz|realizei|autorizei|aprovei) (?:isso|essa|esta|esse|este)?\s*(?:compra|operacao|transacao)?\b"),
    re.compile(r"\b(?:essa|esta|esse|este|a|o) (?:cobranca|compra|pagamento|lancamento|operacao|transacao)(?: [a-z0-9-]+)? nao (?:e|foi) minh[ao]\b"),
    re.compile(r"\bnao (?:e|foi) minh[ao] (?:compra|operacao|transacao)\b"),
    re.compile(r"\b(?:e|foi) (?:de outra pessoa|alheia|alheio)\b"),
    re.compile(r"\b(?:isso|isto|ela|ele) foi feito por outra pessoa\b"),
    # Portuguese: explicit absence of authorization.
    re.compile(r"\bnao (?:autorizei|dei autorizacao|dei permissao|aprovei)\b"),
    re.compile(r"\beu (?:jamais|nunca) (?:autorizei|aprovei|dei autorizacao|dei permissao)\b"),
    re.compile(r"\bsem (?:a )?minha (?:autorizacao|permissao|anuencia)\b"),
    re.compile(r"\b(?:me )?(?:cobraram|debitaram|lançaram|lancaram) sem (?:a )?minha (?:autorizacao|permissao)\b"),
    re.compile(r"\bfizeram uma (?:cobranca|compra|operacao|transacao) sem (?:a )?minha (?:autorizacao|permissao)\b"),
    # Common code-switch wording in the frozen ES/PT stress slice.
    re.compile(r"\b(?:that|this) (?:charge|transaction|purchase) (?:was not|wasn't|is not|isn't) mine\b"),
    re.compile(r"\bi did not (?:make|authorize|approve) (?:that|this) (?:charge|transaction|purchase)\b"),
)


def is_explicit_unauthorized_assertion(text: str) -> bool:
    """Return True only for an explicit customer unauthorized/non-recognition assertion."""

    normalized = normalize_unauthorized_text(text)
    return any(pattern.search(normalized) for pattern in _UNAUTHORIZED_PATTERNS)
