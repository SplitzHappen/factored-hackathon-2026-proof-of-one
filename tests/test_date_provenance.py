from __future__ import annotations

from datetime import date

import pytest

from app.date_provenance import ResolvedDateRange, resolve_message_date_range


REFERENCE_DATE = date(2026, 6, 4)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "Muéstrame lo de ayer.",
            ResolvedDateRange(date(2026, 6, 3), date(2026, 6, 3)),
        ),
        (
            "Mostre o que aconteceu ontem.",
            ResolvedDateRange(date(2026, 6, 3), date(2026, 6, 3)),
        ),
        (
            "Muéstrame lo de hoy.",
            ResolvedDateRange(date(2026, 6, 4), date(2026, 6, 4)),
        ),
        (
            "Mostre o que aconteceu hoje.",
            ResolvedDateRange(date(2026, 6, 4), date(2026, 6, 4)),
        ),
        (
            "Muéstrame la semana pasada.",
            ResolvedDateRange(date(2026, 5, 25), date(2026, 5, 31)),
        ),
        (
            "Mostre a semana passada.",
            ResolvedDateRange(date(2026, 5, 25), date(2026, 5, 31)),
        ),
        (
            "Muéstrame este mes.",
            ResolvedDateRange(date(2026, 6, 1), date(2026, 6, 4)),
        ),
        (
            "Mostre este mês.",
            ResolvedDateRange(date(2026, 6, 1), date(2026, 6, 4)),
        ),
        (
            "Mostre os movimentos deste mês.",
            ResolvedDateRange(date(2026, 6, 1), date(2026, 6, 4)),
        ),
        (
            "Busca 2026-06-02.",
            ResolvedDateRange(date(2026, 6, 2), date(2026, 6, 2)),
        ),
        (
            "Busca desde 2026-06-01.",
            ResolvedDateRange(date(2026, 6, 1), date(2026, 6, 4)),
        ),
        (
            "Busque até 03/06/2026.",
            ResolvedDateRange(None, date(2026, 6, 3)),
        ),
        (
            "Busca entre 2026-06-01 y 2026-06-03.",
            ResolvedDateRange(date(2026, 6, 1), date(2026, 6, 3)),
        ),
    ],
)
def test_supported_date_phrases_resolve_deterministically(
    message: str,
    expected: ResolvedDateRange,
) -> None:
    assert resolve_message_date_range(message, REFERENCE_DATE) == expected


@pytest.mark.parametrize(
    "message",
    [
        "Muéstrame lo que hay entre mis movimientos.",
        "Busca algo de la semana.",
        "Busca algo del mes.",
        "Muéstrame mañana.",
        "Mostre amanhã.",
        "Busca 2030-01-01.",
        "Busca entre 2026-06-01 y 2030-01-01.",
        "Busca entre 2026-06-03 y 2026-06-01.",
        "Busca ayer 2026-06-01.",
    ],
)
def test_ambiguous_or_future_date_phrases_fail_closed(message: str) -> None:
    assert resolve_message_date_range(message, REFERENCE_DATE) is None
