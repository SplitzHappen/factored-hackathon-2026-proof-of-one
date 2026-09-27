from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.schemas import SupportedLanguage


# ES-CO and PT-BR both use "." as the thousands separator and "," as the
# decimal separator. Currency symbols/codes are deliberately outside the token
# so "$54.000 COP" and "R$ 219,90" normalize through the same parser.
_LOCALE_AMOUNT_TOKEN = re.compile(
    r"(?<![\w.,:/-])(?:\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)(?![\w.,:/-])"
)


def parse_locale_amount_token(
    token: str,
    language: SupportedLanguage,
) -> Decimal | None:
    """Parse one ES-CO/PT-BR numeric amount token into canonical Decimal form."""

    if language not in {SupportedLanguage.ES, SupportedLanguage.PT}:
        return None

    candidate = token.strip()
    if not _LOCALE_AMOUNT_TOKEN.fullmatch(candidate):
        return None

    canonical = candidate.replace(".", "").replace(",", ".")
    try:
        value = Decimal(canonical)
    except InvalidOperation:
        return None
    return value if value >= 0 else None


def extract_locale_amounts(
    message: str,
    language: SupportedLanguage,
) -> list[Decimal]:
    """Return locale-normalized numeric amount tokens in message order."""

    amounts: list[Decimal] = []
    for match in _LOCALE_AMOUNT_TOKEN.finditer(message):
        parsed = parse_locale_amount_token(match.group(0), language)
        if parsed is not None:
            amounts.append(parsed)
    return amounts


def extract_single_locale_amount(
    message: str,
    language: SupportedLanguage,
) -> Decimal | None:
    """Return an amount only when exactly one locale-valid numeric token exists."""

    amounts = extract_locale_amounts(message, language)
    return amounts[0] if len(amounts) == 1 else None


def format_locale_amount(
    amount: Decimal,
    currency: str,
    language: SupportedLanguage,
) -> str:
    """Render a verified amount with ES-CO/PT-BR separators and currency code."""

    if language not in {SupportedLanguage.ES, SupportedLanguage.PT}:
        raise ValueError("Unsupported amount locale")

    quantized = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    canonical = f"{quantized:,.2f}"
    whole, fractional = canonical.split(".")
    localized = f"{whole.replace(',', '.')},{fractional}"
    return f"{localized} {currency}"
