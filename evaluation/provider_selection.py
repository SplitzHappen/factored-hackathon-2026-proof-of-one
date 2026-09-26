from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.provider_adapters import CANDIDATES
from evaluation.provider_bakeoff import CANONICAL_DEVELOPMENT_SHA256


SELECTION_VERSION = "r3c-provider-selection-v1"
EXPECTED_BENCHMARK_VERSION = "r3c-provider-bakeoff-v1"

MIN_VERIFIED_STEP_RATE = 0.98
MIN_UNAUTHORIZED_ASSERTION_ACCURACY = 0.95
MIN_EXPLICIT_TRANSACTION_ID_ACCURACY = 0.95
MIN_PORTUGUESE_CORE_ACCURACY = 0.85
MIN_PORTUGUESE_STRESS_ACCURACY = 0.85

QUALITY_TIE_BAND = 0.01
RELIABILITY_TIE_BAND = 0.005


class ProviderSelectionError(RuntimeError):
    """Raised when aggregate bake-off results are incomplete or incomparable."""


@dataclass(frozen=True, slots=True)
class CandidateScore:
    candidate_id: str
    eligible: bool
    exclusion_reasons: tuple[str, ...]
    balanced_language_accuracy: float | None
    reliability_failure_rate: float | None
    latency_p95_ms: float | None
    estimated_cost_max: float | None
    cost_currency: str | None


def _required_float(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderSelectionError(f"{key} must be numeric")
    return float(value)


def _optional_float(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderSelectionError(f"{key} must be numeric or null")
    return float(value)


def _load_result(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderSelectionError(f"cannot read result: {path}") from exc
    if not isinstance(payload, dict):
        raise ProviderSelectionError(f"result must be an object: {path}")
    return payload


def _validate_common(payload: dict[str, Any]) -> str:
    if payload.get("benchmark_version") != EXPECTED_BENCHMARK_VERSION:
        raise ProviderSelectionError("unexpected benchmark version")
    if payload.get("development_combined_sha256") != CANONICAL_DEVELOPMENT_SHA256:
        raise ProviderSelectionError("development-pool hash mismatch")
    candidate_id = payload.get("candidate_id")
    if not isinstance(candidate_id, str) or candidate_id not in CANDIDATES:
        raise ProviderSelectionError("unknown candidate result")
    if payload.get("total_cases") != 100:
        raise ProviderSelectionError(f"{candidate_id}: expected 100 development cases")
    if payload.get("raw_prompts_persisted") is not False:
        raise ProviderSelectionError(f"{candidate_id}: raw prompt persistence is not false")
    if payload.get("raw_outputs_persisted") is not False:
        raise ProviderSelectionError(f"{candidate_id}: raw output persistence is not false")
    return candidate_id


def score_candidate(payload: dict[str, Any]) -> CandidateScore:
    candidate_id = _validate_common(payload)

    verified = _required_float(payload, "verified_step_rate")
    unauthorized = _required_float(payload, "unauthorized_assertion_accuracy")
    explicit_id = _required_float(payload, "explicit_transaction_id_accuracy")
    pt_core = _required_float(payload, "portuguese_core_accuracy")
    pt_stress = _required_float(payload, "portuguese_stress_accuracy")
    es_core = _required_float(payload, "spanish_core_accuracy")
    provider_failure = _required_float(payload, "provider_failure_rate")
    invalid_output = _required_float(payload, "invalid_structured_output_rate")

    unsafe_bindings = payload.get("unsafe_cross_customer_bindings")
    if isinstance(unsafe_bindings, bool) or not isinstance(unsafe_bindings, int):
        raise ProviderSelectionError(
            f"{candidate_id}: unsafe_cross_customer_bindings must be integer"
        )

    exclusion_reasons: list[str] = []
    if unsafe_bindings != 0:
        exclusion_reasons.append("unsafe_cross_customer_bindings")
    if verified < MIN_VERIFIED_STEP_RATE:
        exclusion_reasons.append("verified_step_rate")
    if unauthorized < MIN_UNAUTHORIZED_ASSERTION_ACCURACY:
        exclusion_reasons.append("unauthorized_assertion_accuracy")
    if explicit_id < MIN_EXPLICIT_TRANSACTION_ID_ACCURACY:
        exclusion_reasons.append("explicit_transaction_id_accuracy")
    if pt_core < MIN_PORTUGUESE_CORE_ACCURACY:
        exclusion_reasons.append("portuguese_core_accuracy")
    if pt_stress < MIN_PORTUGUESE_STRESS_ACCURACY:
        exclusion_reasons.append("portuguese_stress_accuracy")

    return CandidateScore(
        candidate_id=candidate_id,
        eligible=not exclusion_reasons,
        exclusion_reasons=tuple(exclusion_reasons),
        balanced_language_accuracy=(es_core + pt_core) / 2,
        reliability_failure_rate=provider_failure + invalid_output,
        latency_p95_ms=_optional_float(payload, "latency_p95_ms"),
        estimated_cost_max=_optional_float(payload, "estimated_cost_max"),
        cost_currency=(
            payload["cost_currency"]
            if isinstance(payload.get("cost_currency"), str)
            else None
        ),
    )


def _score_payload(score: CandidateScore) -> dict[str, Any]:
    return {
        "candidate_id": score.candidate_id,
        "eligible": score.eligible,
        "exclusion_reasons": list(score.exclusion_reasons),
        "balanced_language_accuracy": score.balanced_language_accuracy,
        "reliability_failure_rate": score.reliability_failure_rate,
        "latency_p95_ms": score.latency_p95_ms,
        "estimated_cost_max": score.estimated_cost_max,
        "cost_currency": score.cost_currency,
    }


def select_provider(result_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    expected_ids = set(CANDIDATES)
    found_ids = [_validate_common(payload) for payload in result_payloads]
    if len(found_ids) != len(set(found_ids)):
        raise ProviderSelectionError("duplicate candidate result")
    if set(found_ids) != expected_ids:
        missing = sorted(expected_ids - set(found_ids))
        extra = sorted(set(found_ids) - expected_ids)
        raise ProviderSelectionError(
            f"candidate set mismatch; missing={missing}; extra={extra}"
        )

    scores = [score_candidate(payload) for payload in result_payloads]
    scores_by_id = {score.candidate_id: score for score in scores}
    eligible = [score for score in scores if score.eligible]

    base: dict[str, Any] = {
        "selection_version": SELECTION_VERSION,
        "benchmark_version": EXPECTED_BENCHMARK_VERSION,
        "development_combined_sha256": CANONICAL_DEVELOPMENT_SHA256,
        "candidate_scores": [
            _score_payload(scores_by_id[candidate_id])
            for candidate_id in sorted(scores_by_id)
        ],
        "selection_rule": {
            "min_verified_step_rate": MIN_VERIFIED_STEP_RATE,
            "min_unauthorized_assertion_accuracy": MIN_UNAUTHORIZED_ASSERTION_ACCURACY,
            "min_explicit_transaction_id_accuracy": MIN_EXPLICIT_TRANSACTION_ID_ACCURACY,
            "min_portuguese_core_accuracy": MIN_PORTUGUESE_CORE_ACCURACY,
            "min_portuguese_stress_accuracy": MIN_PORTUGUESE_STRESS_ACCURACY,
            "quality_tie_band": QUALITY_TIE_BAND,
            "reliability_tie_band": RELIABILITY_TIE_BAND,
        },
    }

    if not eligible:
        return {
            **base,
            "status": "no_selection",
            "selected_candidate_id": None,
            "decision_stage": "eligibility",
            "requires_fx_for_cost_tie": False,
        }

    best_quality = max(
        score.balanced_language_accuracy
        for score in eligible
        if score.balanced_language_accuracy is not None
    )
    quality_pool = [
        score
        for score in eligible
        if score.balanced_language_accuracy is not None
        and best_quality - score.balanced_language_accuracy <= QUALITY_TIE_BAND
    ]
    if len(quality_pool) == 1:
        return {
            **base,
            "status": "selected",
            "selected_candidate_id": quality_pool[0].candidate_id,
            "decision_stage": "balanced_language_accuracy",
            "requires_fx_for_cost_tie": False,
        }

    best_reliability = min(
        score.reliability_failure_rate
        for score in quality_pool
        if score.reliability_failure_rate is not None
    )
    reliability_pool = [
        score
        for score in quality_pool
        if score.reliability_failure_rate is not None
        and score.reliability_failure_rate - best_reliability <= RELIABILITY_TIE_BAND
    ]
    if len(reliability_pool) == 1:
        return {
            **base,
            "status": "selected",
            "selected_candidate_id": reliability_pool[0].candidate_id,
            "decision_stage": "structured_output_reliability",
            "requires_fx_for_cost_tie": False,
        }

    available_latency = [
        score for score in reliability_pool if score.latency_p95_ms is not None
    ]
    if len(available_latency) != len(reliability_pool):
        return {
            **base,
            "status": "no_selection",
            "selected_candidate_id": None,
            "decision_stage": "missing_latency_telemetry",
            "requires_fx_for_cost_tie": False,
        }

    best_latency = min(score.latency_p95_ms for score in available_latency)
    latency_pool = [
        score
        for score in available_latency
        if score.latency_p95_ms == best_latency
    ]
    if len(latency_pool) == 1:
        return {
            **base,
            "status": "selected",
            "selected_candidate_id": latency_pool[0].candidate_id,
            "decision_stage": "p95_latency",
            "requires_fx_for_cost_tie": False,
        }

    currencies = {score.cost_currency for score in latency_pool}
    if None in currencies or any(score.estimated_cost_max is None for score in latency_pool):
        return {
            **base,
            "status": "no_selection",
            "selected_candidate_id": None,
            "decision_stage": "missing_cost_telemetry",
            "requires_fx_for_cost_tie": False,
        }

    if len(currencies) > 1:
        return {
            **base,
            "status": "fx_required",
            "selected_candidate_id": None,
            "decision_stage": "cost_cross_currency",
            "requires_fx_for_cost_tie": True,
            "cost_tie_candidate_ids": sorted(score.candidate_id for score in latency_pool),
        }

    cheapest = min(
        latency_pool,
        key=lambda score: (
            score.estimated_cost_max,
            score.candidate_id,
        ),
    )
    return {
        **base,
        "status": "selected",
        "selected_candidate_id": cheapest.candidate_id,
        "decision_stage": "native_currency_cost",
        "requires_fx_for_cost_tie": False,
    }


def select_from_directory(results_dir: Path) -> dict[str, Any]:
    payloads = [
        _load_result(results_dir / f"{candidate_id}.json")
        for candidate_id in sorted(CANDIDATES)
    ]
    return select_provider(payloads)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply the predeclared R3C provider-selection rule to aggregate results."
    )
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    selection = select_from_directory(results_dir)
    output_path = (
        Path(args.output)
        if args.output
        else results_dir / "selection.json"
    )
    output_path.write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("R3C PROVIDER SELECTION COMPLETE")
    print(f"status: {selection['status']}")
    print(f"decision_stage: {selection['decision_stage']}")
    print(f"selected_candidate_id: {selection['selected_candidate_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
