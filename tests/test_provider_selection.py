from __future__ import annotations

from copy import deepcopy

from evaluation.provider_bakeoff import CANONICAL_DEVELOPMENT_SHA256
from evaluation.provider_selection import ProviderSelectionError, select_provider


def _payload(
    candidate_id: str,
    *,
    es: float = 0.96,
    pt: float = 0.94,
    stress: float = 0.94,
    verified: float = 1.0,
    unauthorized: float = 1.0,
    tx_id: float = 1.0,
    provider_failure: float = 0.0,
    invalid: float = 0.0,
    unsafe: int = 0,
    latency: float = 900.0,
    cost: float = 0.001,
    currency: str = "USD",
) -> dict[str, object]:
    return {
        "benchmark_version": "r3c-provider-bakeoff-v1",
        "development_combined_sha256": CANONICAL_DEVELOPMENT_SHA256,
        "candidate_id": candidate_id,
        "provider": candidate_id,
        "model": candidate_id,
        "strict_json_schema": candidate_id != "deepseek-v4.1-flash",
        "total_cases": 100,
        "total_steps": 110,
        "verified_step_rate": verified,
        "provider_failure_rate": provider_failure,
        "invalid_structured_output_rate": invalid,
        "intent_accuracy": 0.95,
        "unauthorized_assertion_accuracy": unauthorized,
        "explicit_transaction_id_accuracy": tx_id,
        "owned_explicit_id_verified_rate": 1.0,
        "cross_customer_reference_block_rate": 1.0,
        "unsafe_cross_customer_bindings": unsafe,
        "spanish_core_accuracy": es,
        "portuguese_core_accuracy": pt,
        "language_gap_percentage_points": abs(es - pt) * 100,
        "portuguese_stress_case_count": 16,
        "portuguese_stress_verified_rate": 1.0,
        "portuguese_stress_accuracy": stress,
        "portuguese_stress_provider_failures": 0,
        "portuguese_stress_invalid_outputs": 0,
        "portuguese_stress_latency_p95_ms": latency,
        "latency_p50_ms": latency / 2,
        "latency_p95_ms": latency,
        "mean_latency_ms": latency * 0.7,
        "input_tokens": 10000,
        "output_tokens": 1000,
        "token_telemetry_steps": 110,
        "estimated_cost_min": cost,
        "estimated_cost_max": cost,
        "cost_currency": currency,
        "cost_telemetry_steps": 110,
        "portuguese_stress_estimated_cost_min": 0.0001,
        "portuguese_stress_estimated_cost_max": 0.0001,
        "raw_prompts_persisted": False,
        "raw_outputs_persisted": False,
    }


def _three() -> list[dict[str, object]]:
    return [
        _payload("openai-gpt-5.6-luna"),
        _payload("qwen3.7-flash", currency="CNY"),
        _payload("deepseek-v4.1-flash"),
    ]


def test_ineligible_candidate_cannot_win_on_quality() -> None:
    payloads = _three()
    payloads[0] = _payload(
        "openai-gpt-5.6-luna",
        es=1.0,
        pt=1.0,
        stress=0.80,
    )
    payloads[1] = _payload("qwen3.7-flash", es=0.97, pt=0.96, currency="CNY")

    result = select_provider(payloads)

    assert result["selected_candidate_id"] == "qwen3.7-flash"
    openai = next(
        score
        for score in result["candidate_scores"]
        if score["candidate_id"] == "openai-gpt-5.6-luna"
    )
    assert "portuguese_stress_accuracy" in openai["exclusion_reasons"]


def test_quality_winner_selected_outside_one_point_band() -> None:
    payloads = _three()
    payloads[0] = _payload("openai-gpt-5.6-luna", es=0.99, pt=0.98)
    payloads[1] = _payload("qwen3.7-flash", es=0.95, pt=0.94, currency="CNY")
    payloads[2] = _payload("deepseek-v4.1-flash", es=0.94, pt=0.93)

    result = select_provider(payloads)

    assert result["status"] == "selected"
    assert result["decision_stage"] == "balanced_language_accuracy"
    assert result["selected_candidate_id"] == "openai-gpt-5.6-luna"


def test_reliability_breaks_quality_tie_band() -> None:
    payloads = _three()
    payloads[0] = _payload(
        "openai-gpt-5.6-luna",
        es=0.97,
        pt=0.96,
        provider_failure=0.0,
        invalid=0.0,
    )
    payloads[1] = _payload(
        "qwen3.7-flash",
        es=0.971,
        pt=0.961,
        provider_failure=0.01,
        invalid=0.0,
        currency="CNY",
    )
    payloads[2] = _payload(
        "deepseek-v4.1-flash",
        es=0.965,
        pt=0.955,
        provider_failure=0.02,
        invalid=0.0,
    )

    result = select_provider(payloads)

    assert result["decision_stage"] == "structured_output_reliability"
    assert result["selected_candidate_id"] == "openai-gpt-5.6-luna"


def test_latency_breaks_close_quality_and_reliability() -> None:
    payloads = _three()
    payloads[0] = _payload(
        "openai-gpt-5.6-luna",
        provider_failure=0.001,
        latency=700,
    )
    payloads[1] = _payload(
        "qwen3.7-flash",
        provider_failure=0.002,
        latency=550,
        currency="CNY",
    )
    payloads[2] = _payload(
        "deepseek-v4.1-flash",
        provider_failure=0.003,
        latency=800,
    )

    result = select_provider(payloads)

    assert result["decision_stage"] == "p95_latency"
    assert result["selected_candidate_id"] == "qwen3.7-flash"


def test_cross_currency_exact_latency_tie_requires_fx() -> None:
    payloads = _three()
    payloads[0] = _payload("openai-gpt-5.6-luna", latency=600, cost=0.001)
    payloads[1] = _payload(
        "qwen3.7-flash",
        latency=600,
        cost=0.005,
        currency="CNY",
    )
    payloads[2] = _payload("deepseek-v4.1-flash", latency=700, cost=0.0008)

    # Keep DeepSeek outside the quality tie band so the exact-latency finalists are
    # the USD/CNY pair only.
    payloads[2]["spanish_core_accuracy"] = 0.90
    payloads[2]["portuguese_core_accuracy"] = 0.90

    result = select_provider(payloads)

    assert result["status"] == "fx_required"
    assert result["requires_fx_for_cost_tie"] is True
    assert result["selected_candidate_id"] is None
    assert result["cost_tie_candidate_ids"] == [
        "openai-gpt-5.6-luna",
        "qwen3.7-flash",
    ]


def test_no_eligible_candidate_returns_no_selection() -> None:
    payloads = [
        _payload(candidate_id, verified=0.90, currency=("CNY" if "qwen" in candidate_id else "USD"))
        for candidate_id in (
            "openai-gpt-5.6-luna",
            "qwen3.7-flash",
            "deepseek-v4.1-flash",
        )
    ]

    result = select_provider(payloads)

    assert result["status"] == "no_selection"
    assert result["decision_stage"] == "eligibility"
    assert result["selected_candidate_id"] is None


def test_candidate_set_and_development_hash_are_fail_closed() -> None:
    payloads = _three()
    payloads.pop()
    try:
        select_provider(payloads)
    except ProviderSelectionError as exc:
        assert "candidate set mismatch" in str(exc)
    else:
        raise AssertionError("missing candidate should fail")

    payloads = _three()
    broken = deepcopy(payloads[0])
    broken["development_combined_sha256"] = "0" * 64
    payloads[0] = broken
    try:
        select_provider(payloads)
    except ProviderSelectionError as exc:
        assert "development-pool hash mismatch" in str(exc)
    else:
        raise AssertionError("hash mismatch should fail")
