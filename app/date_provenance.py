from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class ResolvedDateRange:
    date_from: date
    date_to: date


_ISO_DATE = re.compile(r"(?<!\d)(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?!\d)")
_DMY_DATE = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)")


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _previous_month(reference_date: date) -> tuple[date, date]:
    first_this_month = reference_date.replace(day=1)
    last_previous_month = first_this_month - timedelta(days=1)
    return last_previous_month.replace(day=1), last_previous_month


def _current_week(reference_date: date) -> tuple[date, date]:
    start = reference_date - timedelta(days=reference_date.weekday())
    return start, reference_date


def _previous_week(reference_date: date) -> tuple[date, date]:
    current_start = reference_date - timedelta(days=reference_date.weekday())
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=6)
    return previous_start, previous_end


def _parse_explicit_dates(message: str) -> list[date] | None:
    values: list[date] = []
    spans: list[tuple[int, int]] = []

    for match in _ISO_DATE.finditer(message):
        try:
            value = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
        values.append(value)
        spans.append(match.span())

    for match in _DMY_DATE.finditer(message):
        if any(not (match.end() <= start or match.start() >= end) for start, end in spans):
            continue
        try:
            value = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            return None
        values.append(value)

    return values


def resolve_message_date_range(
    message: str,
    reference_date: date,
) -> ResolvedDateRange | None:
    """Resolve only deterministic ES/PT date expressions supported by the contract."""

    normalized = _normalize(message)

    relative_rules: tuple[tuple[tuple[str, ...], tuple[date, date]], ...] = (
        (("ayer", "ontem"), (reference_date - timedelta(days=1),) * 2),
        (("hoy", "hoje"), (reference_date, reference_date)),
        (
            ("semana pasada", "semana passada"),
            _previous_week(reference_date),
        ),
        (
            ("esta semana", "esta semana"),
            _current_week(reference_date),
        ),
        (
            ("este mes", "este mes", "este mes", "este mes"),
            (reference_date.replace(day=1), reference_date),
        ),
        (
            ("mes pasado", "mes passado"),
            _previous_month(reference_date),
        ),
    )

    matched_ranges: list[tuple[date, date]] = []
    for phrases, resolved in relative_rules:
        if any(re.search(rf"\b{re.escape(phrase)}\b", normalized) for phrase in phrases):
            matched_ranges.append(resolved)

    explicit_dates = _parse_explicit_dates(normalized)
    if explicit_dates is None:
        return None
    if explicit_dates:
        if len(explicit_dates) > 2:
            return None
        explicit_dates = sorted(explicit_dates)
        matched_ranges.append((explicit_dates[0], explicit_dates[-1]))

    if len(matched_ranges) != 1:
        return None

    date_from, date_to = matched_ranges[0]
    if date_from > date_to or date_to > reference_date:
        return None
    return ResolvedDateRange(date_from=date_from, date_to=date_to)
