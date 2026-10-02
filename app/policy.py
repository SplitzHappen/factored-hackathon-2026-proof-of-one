from __future__ import annotations

from app.schemas import (
    PolicyInput,
    PolicyIntent,
    PolicyReason,
    PolicyResult,
    RouteDecision,
)


SUPPORTED_INTENTS = {
    PolicyIntent.ACCOUNT_PRODUCT_INFO,
    PolicyIntent.RECENT_TRANSACTION_HISTORY,
    PolicyIntent.TRANSACTION_LOOKUP,
    PolicyIntent.TRANSACTION_STATUS,
    PolicyIntent.PAYMENT_HISTORY,
}

PROHIBITED_ACTION_INTENTS = {
    PolicyIntent.MOVE_MONEY,
    PolicyIntent.MUTATE_PAYMENT,
    PolicyIntent.BLOCK_CARD_OR_ACCOUNT,
    PolicyIntent.MUTATE_ACCOUNT,
    PolicyIntent.DISPUTE_ACTION,
    PolicyIntent.CREDIT_ELIGIBILITY,
    PolicyIntent.MODIFY_PROFILE,
}


def route_policy(policy_input: PolicyInput) -> PolicyResult:
    """Return the authoritative deterministic route.

    Precedence is intentional:
    1. hard safety/escalation conditions (explicit unauthorized-activity report,
       then the RF4 fail-safe floor);
    2. prohibited/unsupported requests;
    3. clarification for supported requests;
    4. verified supported answer.
    """

    if policy_input.unauthorized_activity_asserted:
        return PolicyResult(
            route=RouteDecision.ESCALATE,
            reason_codes=[PolicyReason.UNAUTHORIZED_ACTIVITY_REPORTED],
            safe_to_answer=False,
            mandatory_escalation=True,
        )

    if policy_input.possible_unauthorized_activity:
        return PolicyResult(
            route=RouteDecision.ESCALATE,
            reason_codes=[PolicyReason.POSSIBLE_UNAUTHORIZED_ACTIVITY],
            safe_to_answer=False,
            mandatory_escalation=True,
        )

    if policy_input.interpretation_unavailable:
        return PolicyResult(
            route=RouteDecision.ESCALATE,
            reason_codes=[PolicyReason.INTERPRETATION_UNAVAILABLE],
            safe_to_answer=False,
            mandatory_escalation=False,
        )

    escalation_reasons: list[PolicyReason] = []
    if policy_input.trusted_data_conflict:
        escalation_reasons.append(PolicyReason.TRUSTED_DATA_CONFLICT)
    if policy_input.excluded_relationship_required:
        escalation_reasons.append(PolicyReason.EXCLUDED_RELATIONSHIP_REQUIRED)

    if escalation_reasons:
        return PolicyResult(
            route=RouteDecision.ESCALATE,
            reason_codes=escalation_reasons,
            safe_to_answer=False,
            mandatory_escalation=False,
        )

    if policy_input.intent is PolicyIntent.DECLINE_CAUSE:
        return PolicyResult(
            route=RouteDecision.ABSTAIN,
            reason_codes=[PolicyReason.UNSUPPORTED_CAUSAL_EXPLANATION],
            safe_to_answer=False,
            mandatory_escalation=False,
        )

    if policy_input.intent in PROHIBITED_ACTION_INTENTS:
        return PolicyResult(
            route=RouteDecision.ABSTAIN,
            reason_codes=[PolicyReason.PROHIBITED_BANKING_ACTION],
            safe_to_answer=False,
            mandatory_escalation=False,
        )

    if policy_input.intent not in SUPPORTED_INTENTS:
        return PolicyResult(
            route=RouteDecision.ABSTAIN,
            reason_codes=[PolicyReason.UNSUPPORTED_INTENT],
            safe_to_answer=False,
            mandatory_escalation=False,
        )

    clarification_reasons: list[PolicyReason] = []
    if not policy_input.ownership_verified:
        clarification_reasons.append(PolicyReason.OWNERSHIP_UNVERIFIED)
    if not policy_input.trusted_record_found:
        clarification_reasons.append(PolicyReason.TRUSTED_RECORD_MISSING)
    if policy_input.ambiguous_transaction_match:
        clarification_reasons.append(PolicyReason.AMBIGUOUS_TRANSACTION_MATCH)
    if policy_input.required_parameters_missing:
        clarification_reasons.append(PolicyReason.REQUIRED_PARAMETERS_MISSING)

    if clarification_reasons:
        return PolicyResult(
            route=RouteDecision.CLARIFY,
            reason_codes=clarification_reasons,
            safe_to_answer=False,
            mandatory_escalation=False,
        )

    return PolicyResult(
        route=RouteDecision.ANSWER,
        reason_codes=[PolicyReason.SUPPORTED_VERIFIED],
        safe_to_answer=True,
        mandatory_escalation=False,
    )
