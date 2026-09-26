from __future__ import annotations

from app.policy import route_policy
from app.schemas import (
    PolicyInput,
    PolicyIntent,
    PolicyReason,
    RouteDecision,
)


def policy_input(intent: PolicyIntent, **updates: bool) -> PolicyInput:
    values: dict[str, object] = {
        "intent": intent,
        "unauthorized_activity_asserted": False,
        "ownership_verified": True,
        "trusted_record_found": True,
        "trusted_data_conflict": False,
        "excluded_relationship_required": False,
        "ambiguous_transaction_match": False,
        "required_parameters_missing": False,
    }
    values.update(updates)
    return PolicyInput(**values)


def test_verified_supported_intent_routes_to_answer() -> None:
    result = route_policy(policy_input(PolicyIntent.RECENT_TRANSACTION_HISTORY))

    assert result.route is RouteDecision.ANSWER
    assert result.reason_codes == [PolicyReason.SUPPORTED_VERIFIED]
    assert result.safe_to_answer is True
    assert result.mandatory_escalation is False


def test_ambiguity_routes_to_clarify_without_guessing() -> None:
    result = route_policy(
        policy_input(
            PolicyIntent.TRANSACTION_LOOKUP,
            ambiguous_transaction_match=True,
        )
    )

    assert result.route is RouteDecision.CLARIFY
    assert PolicyReason.AMBIGUOUS_TRANSACTION_MATCH in result.reason_codes
    assert result.safe_to_answer is False


def test_missing_parameters_route_to_clarify() -> None:
    result = route_policy(
        policy_input(
            PolicyIntent.TRANSACTION_LOOKUP,
            required_parameters_missing=True,
        )
    )

    assert result.route is RouteDecision.CLARIFY
    assert result.reason_codes == [PolicyReason.REQUIRED_PARAMETERS_MISSING]


def test_customer_unauthorized_assertion_is_hard_escalation() -> None:
    result = route_policy(
        policy_input(
            PolicyIntent.BLOCK_CARD_OR_ACCOUNT,
            unauthorized_activity_asserted=True,
        )
    )

    assert result.route is RouteDecision.ESCALATE
    assert result.reason_codes == [PolicyReason.UNAUTHORIZED_ACTIVITY_REPORTED]
    assert result.mandatory_escalation is True


def test_ownership_failure_escalates_before_any_answer() -> None:
    result = route_policy(
        policy_input(
            PolicyIntent.TRANSACTION_STATUS,
            ownership_verified=False,
        )
    )

    assert result.route is RouteDecision.ESCALATE
    assert result.reason_codes == [PolicyReason.OWNERSHIP_UNVERIFIED]
    assert result.safe_to_answer is False


def test_multiple_hard_data_failures_are_preserved_in_reason_codes() -> None:
    result = route_policy(
        policy_input(
            PolicyIntent.ACCOUNT_PRODUCT_INFO,
            trusted_record_found=False,
            trusted_data_conflict=True,
            excluded_relationship_required=True,
        )
    )

    assert result.route is RouteDecision.ESCALATE
    assert result.reason_codes == [
        PolicyReason.TRUSTED_RECORD_MISSING,
        PolicyReason.TRUSTED_DATA_CONFLICT,
        PolicyReason.EXCLUDED_RELATIONSHIP_REQUIRED,
    ]


def test_decline_cause_request_abstains_instead_of_inventing_reason() -> None:
    result = route_policy(policy_input(PolicyIntent.DECLINE_CAUSE))

    assert result.route is RouteDecision.ABSTAIN
    assert result.reason_codes == [PolicyReason.UNSUPPORTED_CAUSAL_EXPLANATION]
    assert result.mandatory_escalation is False


def test_prohibited_banking_action_abstains() -> None:
    result = route_policy(policy_input(PolicyIntent.MOVE_MONEY))

    assert result.route is RouteDecision.ABSTAIN
    assert result.reason_codes == [PolicyReason.PROHIBITED_BANKING_ACTION]


def test_unknown_intent_abstains() -> None:
    result = route_policy(policy_input(PolicyIntent.UNKNOWN))

    assert result.route is RouteDecision.ABSTAIN
    assert result.reason_codes == [PolicyReason.UNSUPPORTED_INTENT]


def test_hard_escalation_precedes_clarification_and_prohibited_action() -> None:
    result = route_policy(
        policy_input(
            PolicyIntent.DISPUTE_ACTION,
            unauthorized_activity_asserted=True,
            ambiguous_transaction_match=True,
            required_parameters_missing=True,
        )
    )

    assert result.route is RouteDecision.ESCALATE
    assert result.reason_codes == [PolicyReason.UNAUTHORIZED_ACTIVITY_REPORTED]


def test_data_safety_escalation_precedes_clarification() -> None:
    result = route_policy(
        policy_input(
            PolicyIntent.TRANSACTION_LOOKUP,
            ownership_verified=False,
            ambiguous_transaction_match=True,
        )
    )

    assert result.route is RouteDecision.ESCALATE
    assert result.reason_codes == [PolicyReason.OWNERSHIP_UNVERIFIED]


def test_prohibited_action_is_not_clarified_even_when_parameters_are_missing() -> None:
    result = route_policy(
        policy_input(
            PolicyIntent.MOVE_MONEY,
            required_parameters_missing=True,
            ambiguous_transaction_match=True,
        )
    )

    assert result.route is RouteDecision.ABSTAIN
    assert result.reason_codes == [PolicyReason.PROHIBITED_BANKING_ACTION]


def test_unknown_intent_is_not_clarified() -> None:
    result = route_policy(
        policy_input(
            PolicyIntent.UNKNOWN,
            required_parameters_missing=True,
        )
    )

    assert result.route is RouteDecision.ABSTAIN
    assert result.reason_codes == [PolicyReason.UNSUPPORTED_INTENT]
