from app.interpretation import InterpretationService


def test_rf5_stage1_raise_reaches_active_failsafe_floor() -> None:
    message = "Tengo un débito en mi cuenta sin mi autorización."

    assert InterpretationService._failsafe_floor(message, unauthorized=False)


def test_rf5_stage1_floor_does_not_relabel_existing_unauthorized_assertion() -> None:
    message = "Tengo un débito en mi cuenta sin mi autorización."

    assert not InterpretationService._failsafe_floor(message, unauthorized=True)


def test_rf5_stage1_failure_to_pay_is_not_active_escalation() -> None:
    message = "Se me olvidó pagar la cuota del préstamo."

    assert not InterpretationService._failsafe_floor(message, unauthorized=False)
