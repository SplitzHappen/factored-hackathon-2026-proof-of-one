from __future__ import annotations

import pytest

import app.unauthorized_signals as unauthorized_signals
from app.unauthorized_grammar import PropositionMode, resolve_positive_propositions


def _structural_boolean(message: str) -> bool:
    return any(
        proposition.mode == PropositionMode.ASSERTIVE.value
        for language in ("es", "pt")
        for proposition in resolve_positive_propositions(message, language)
    )


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("No hice esta compra.", True),
        ("Eu não fiz esta compra.", True),
        ("Es un fraude.", True),
        ("¿Es un fraude?", False),
        ("É fraude?", False),
        ("No hice esta transferencia, pero sí la hice.", False),
        ("Ia dizer que eu não fiz esta transferência.", False),
        (
            "Pensé que no hice esta transferencia, "
            "pero esta otra compra no es mía.",
            True,
        ),
        (
            "Achei que eu não fiz esta transferência, "
            "mas esta outra compra não é minha.",
            True,
        ),
    ],
)
def test_b5_public_wrapper_matches_structural_resolution(
    message: str,
    expected: bool,
) -> None:
    structural = _structural_boolean(message)

    assert structural is expected
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is expected


def test_b5_public_wrapper_bypasses_legacy_regex_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_legacy_regex(*_args, **_kwargs):
        raise AssertionError("legacy whole-message regex inventory was consulted")

    monkeypatch.setattr(unauthorized_signals, "_matches_any", fail_legacy_regex)

    assert unauthorized_signals.is_explicit_unauthorized_assertion(
        "No hice esta compra."
    ) is True
    assert unauthorized_signals.is_explicit_unauthorized_assertion(
        "¿Es un fraude?"
    ) is False
