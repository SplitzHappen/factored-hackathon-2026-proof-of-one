from app.rf5_stage1 import (
    rf5_stage1_failure_to_pay_cleanup_candidate,
    rf5_stage1_findings,
    rf5_stage1_should_raise,
)


def families(text: str) -> set[str]:
    return {finding.family for finding in rf5_stage1_findings(text)}


def test_m1_no_authorization_activity_raises() -> None:
    text = "Tengo un débito en mi cuenta sin mi autorización."

    assert rf5_stage1_should_raise(text)
    assert "m1_no_authorization_activity" in families(text)


def test_m2_money_reference_disowning_raises() -> None:
    text = "No reconozco este cargo por 1.250 pesos."

    assert rf5_stage1_should_raise(text)
    assert "m2_money_reference_disowning" in families(text)


def test_m4_scam_activity_raises() -> None:
    text = "Caí en una estafa y ahora hay una transferencia en mi cuenta."

    assert rf5_stage1_should_raise(text)
    assert "m4_scam_social_engineering_activity" in families(text)


def test_ordinary_failure_to_pay_is_cleanup_candidate_not_raise() -> None:
    text = "Se me olvidó pagar la cuota del préstamo."

    assert not rf5_stage1_should_raise(text)
    assert rf5_stage1_failure_to_pay_cleanup_candidate(text)


def test_failure_to_pay_with_positive_guard_is_not_cleanup_candidate() -> None:
    text = "No reconozco el cargo y tampoco pagué la cuota."

    assert rf5_stage1_should_raise(text)
    assert not rf5_stage1_failure_to_pay_cleanup_candidate(text)
