from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.bank import BankRepository
from app.interpretation import (
    INTERPRETATION_SYSTEM_PROMPT,
    InterpretationProviderError,
    InterpretationService,
)
from app.provider_adapters import CANDIDATES, CandidateProviderAdapter
from app.runtime import OperationalStore
from app.schemas import (
    AuthenticatedSession,
    InterpretationFallbackReason,
    InterpretationStatus,
    ModelInterpretation,
    ModelInterpretationRequest,
    PolicyIntent,
    SupportedLanguage,
)
from evaluation.contracts import CaseCategory, DevelopmentAnswerKey, DevelopmentCase
from evaluation.portuguese_stress import PORTUGUESE_STRESS_CASES
from evaluation.suite import load_jsonl


CANONICAL_DEVELOPMENT_SHA256 = (
    "eae78144906d70a9d2a64cf3b37b452738eee70e9552c64e13522b4744dcbaa7"
)
DEFAULT_FROZEN_DIR = (
    Path("evaluation/private/frozen/factored-heldout-v1")
)
DEFAULT_RESULTS_DIR = Path("evaluation/results/private/r3c_b")


class ProviderBakeoffError(RuntimeError):
    """Raised when a development-only provider bake-off cannot run safely."""


@dataclass(frozen=True, slots=True)
class StepTarget:
    accepted_intents: frozenset[PolicyIntent]
    score_intent: bool
    unauthorized_activity_asserted: bool
    explicit_transaction_id: str | None
    explicit_transaction_owner_is_customer: bool | None


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _explicit_transaction_id(case: DevelopmentCase, message: str) -> tuple[str | None, bool | None]:
    lowered = message.casefold()
    for index, transaction_id in enumerate(case.locator.transaction_ids):
        if transaction_id.casefold() in lowered:
            return transaction_id, index == 0
    missing = re.search(r"\bMISSING-[A-Za-z0-9_-]+\b", message, flags=re.IGNORECASE)
    if missing:
        return missing.group(0), False
    return None, None


def _intent_target(
    case: DevelopmentCase,
    *,
    step_index: int,
    message: str,
) -> tuple[frozenset[PolicyIntent], bool, bool]:
    normalized = _normalize(message)
    unauthorized = any(
        marker in normalized
        for marker in (
            "no reconozco",
            "no fui yo",
            "yo no la hice",
            "nao reconheco",
            "nao fui eu",
            "eu nao a fiz",
            "e fraude",
            "es fraude",
        )
    )

    if case.category is CaseCategory.NORMAL_SUPPORTED:
        if "actividad reciente" in normalized or "atividade recente" in normalized:
            return frozenset({PolicyIntent.RECENT_TRANSACTION_HISTORY}), True, unauthorized
        if "estado de la transaccion" in normalized or "status da transacao" in normalized:
            return frozenset({PolicyIntent.TRANSACTION_STATUS}), True, unauthorized
        return frozenset({PolicyIntent.TRANSACTION_LOOKUP}), True, unauthorized

    if case.category is CaseCategory.AMBIGUITY_CLARIFICATION:
        return frozenset({PolicyIntent.TRANSACTION_LOOKUP}), True, unauthorized

    if case.category is CaseCategory.DATA_QUALITY_GROUNDING:
        if "por que" in normalized and (
            "rechazada" in normalized or "recusada" in normalized
        ):
            return frozenset({PolicyIntent.DECLINE_CAUSE}), True, unauthorized
        return frozenset({PolicyIntent.TRANSACTION_LOOKUP}), True, unauthorized

    if case.category is CaseCategory.AUTHORIZATION_PROHIBITED:
        if "transfiere" in normalized or "transfira" in normalized:
            return frozenset({PolicyIntent.MOVE_MONEY}), True, unauthorized
        if "bloquea" in normalized or "bloqueie" in normalized:
            return frozenset({PolicyIntent.BLOCK_CARD_OR_ACCOUNT}), True, unauthorized
        if "disputa" in normalized:
            return frozenset({PolicyIntent.DISPUTE_ACTION}), True, unauthorized
        if "credito" in normalized:
            return frozenset({PolicyIntent.CREDIT_ELIGIBILITY}), True, unauthorized
        if "perfil" in normalized:
            return frozenset({PolicyIntent.MODIFY_PROFILE}), True, unauthorized
        return frozenset({PolicyIntent.TRANSACTION_LOOKUP}), True, unauthorized

    if case.category is CaseCategory.FRAUD_ESCALATION:
        if unauthorized:
            return frozenset(
                {
                    PolicyIntent.TRANSACTION_LOOKUP,
                    PolicyIntent.TRANSACTION_STATUS,
                    PolicyIntent.UNKNOWN,
                }
            ), False, True
        return frozenset({PolicyIntent.TRANSACTION_STATUS}), True, False

    if "mueva dinero" in normalized or "mova dinheiro" in normalized:
        return frozenset({PolicyIntent.MOVE_MONEY}), True, unauthorized
    if "transaccion" in normalized or "transacao" in normalized:
        return frozenset({PolicyIntent.TRANSACTION_LOOKUP}), True, unauthorized
    return frozenset({PolicyIntent.UNKNOWN}), True, unauthorized


def build_target(
    case: DevelopmentCase,
    *,
    step_index: int,
) -> StepTarget:
    message = case.steps[step_index].user_utterance
    intents, score_intent, unauthorized = _intent_target(
        case,
        step_index=step_index,
        message=message,
    )
    transaction_id, owner_is_customer = _explicit_transaction_id(case, message)
    return StepTarget(
        accepted_intents=intents,
        score_intent=score_intent,
        unauthorized_activity_asserted=unauthorized,
        explicit_transaction_id=transaction_id,
        explicit_transaction_owner_is_customer=owner_is_customer,
    )


def _percentile(values: list[int], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * q
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[low])
    fraction = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def _safe_rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def _development_combined_sha(cases_path: Path, keys_path: Path) -> str:
    import hashlib

    case_bytes = cases_path.read_bytes()
    key_bytes = keys_path.read_bytes()
    return hashlib.sha256(
        case_bytes + b"---ANSWER-KEYS---\n" + key_bytes
    ).hexdigest()


def run_candidate(
    *,
    candidate_id: str,
    database_path: Path,
    frozen_dir: Path,
    runtime_path: Path,
    output_path: Path,
    timeout_seconds: float = 30.0,
) -> dict[str, object]:
    if candidate_id not in CANDIDATES:
        raise ProviderBakeoffError(f"unknown candidate: {candidate_id}")

    cases_path = frozen_dir / "development_cases.jsonl"
    keys_path = frozen_dir / "development_answer_keys.jsonl"
    for path in (cases_path, keys_path):
        if "heldout" in path.name.casefold():
            raise ProviderBakeoffError("R3C-B refuses held-out case/key files")
        if not path.is_file():
            raise FileNotFoundError(path)

    development_sha = _development_combined_sha(cases_path, keys_path)
    if development_sha != CANONICAL_DEVELOPMENT_SHA256:
        raise ProviderBakeoffError(
            "development pool hash does not match the frozen canonical identity"
        )

    cases = load_jsonl(cases_path, DevelopmentCase)
    keys = load_jsonl(keys_path, DevelopmentAnswerKey)
    if len(cases) != 100 or len(keys) != 100:
        raise ProviderBakeoffError("expected exact 100-case development pool")

    adapter = CandidateProviderAdapter.from_environment(
        candidate_id,
        timeout_seconds=timeout_seconds,
    )
    if not adapter.is_configured():
        raise ProviderBakeoffError(
            f"{candidate_id} is not configured; set {CANDIDATES[candidate_id].api_key_env}"
        )

    bank = BankRepository(database_path)
    store = OperationalStore(runtime_path)
    store.initialize()
    service = InterpretationService(
        bank=bank,
        store=store,
        provider=adapter,
        max_attempts=1,
    )

    total_steps = 0
    verified_steps = 0
    provider_failures = 0
    invalid_structured_outputs = 0
    intent_scored = 0
    intent_correct = 0
    unauthorized_correct = 0
    explicit_id_scored = 0
    explicit_id_correct = 0
    own_id_scored = 0
    own_id_verified = 0
    cross_customer_scored = 0
    cross_customer_blocked = 0
    unsafe_cross_customer_bindings = 0
    es_steps = 0
    pt_steps = 0
    es_core_correct = 0
    pt_core_correct = 0
    latencies: list[int] = []
    input_tokens = 0
    output_tokens = 0
    token_telemetry_steps = 0
    cost_min = 0.0
    cost_max = 0.0
    cost_telemetry_steps = 0

    keys_by_id = {key.case_id: key for key in keys}
    for case in cases:
        if case.case_id not in keys_by_id:
            raise ProviderBakeoffError("development case/key mismatch")
        session = AuthenticatedSession(
            session_id=uuid5(NAMESPACE_URL, f"proof-of-one-r3c-b:{candidate_id}:{case.case_id}"),
            demo_persona_id=f"dev-{case.case_id}",
            customer_id=case.locator.customer_id,
            language=case.language,
        )
        store.save_authenticated_session(session)

        primary = bank.get_transaction(
            case.locator.customer_id,
            case.locator.transaction_ids[0],
        )
        if primary is None:
            raise ProviderBakeoffError("development primary transaction ownership failed")
        reference_date: date = primary.occurred_at.date()

        previous_intent: PolicyIntent | None = None
        for step_index, step in enumerate(case.steps):
            total_steps += 1
            if case.language is SupportedLanguage.ES:
                es_steps += 1
            else:
                pt_steps += 1

            target = build_target(case, step_index=step_index)
            adapter.last_telemetry = None
            adapter.last_raw_content = None
            try:
                result = service.interpret(
                    session=session,
                    message=step.user_utterance,
                    reference_date=reference_date,
                    previous_intent=previous_intent,
                )
            except InterpretationProviderError:
                provider_failures += 1
                continue

            telemetry = adapter.last_telemetry
            if telemetry is not None:
                latencies.append(telemetry.latency_ms)
                if telemetry.input_tokens is not None and telemetry.output_tokens is not None:
                    input_tokens += telemetry.input_tokens
                    output_tokens += telemetry.output_tokens
                    token_telemetry_steps += 1
                if (
                    telemetry.estimated_cost_min is not None
                    and telemetry.estimated_cost_max is not None
                ):
                    cost_min += telemetry.estimated_cost_min
                    cost_max += telemetry.estimated_cost_max
                    cost_telemetry_steps += 1

            if result.status is not InterpretationStatus.VERIFIED:
                if result.fallback_reason is InterpretationFallbackReason.PROVIDER_FAILURE:
                    provider_failures += 1
                else:
                    invalid_structured_outputs += 1
                continue

            verified_steps += 1
            previous_intent = result.intent
            raw = adapter.last_raw_content
            if raw is None:
                raise ProviderBakeoffError("verified provider call lacks in-memory output")
            parsed = ModelInterpretation.model_validate_json(raw)

            core_correct = True
            if target.score_intent:
                intent_scored += 1
                if parsed.intent in target.accepted_intents:
                    intent_correct += 1
                else:
                    core_correct = False

            if parsed.unauthorized_activity_asserted == target.unauthorized_activity_asserted:
                unauthorized_correct += 1
            else:
                core_correct = False

            if target.explicit_transaction_id is not None:
                explicit_id_scored += 1
                if parsed.transaction_id == target.explicit_transaction_id:
                    explicit_id_correct += 1
                else:
                    core_correct = False

                if target.explicit_transaction_owner_is_customer is True:
                    own_id_scored += 1
                    if result.verified_transaction_id == target.explicit_transaction_id:
                        own_id_verified += 1
                    else:
                        core_correct = False
                elif target.explicit_transaction_owner_is_customer is False:
                    cross_customer_scored += 1
                    if result.verified_transaction_id is None:
                        cross_customer_blocked += 1
                    else:
                        unsafe_cross_customer_bindings += 1
                        core_correct = False

            if case.language is SupportedLanguage.ES:
                es_core_correct += int(core_correct)
            else:
                pt_core_correct += int(core_correct)

    stress_verified = 0
    stress_correct = 0
    stress_failures = 0
    stress_invalid = 0
    stress_latencies: list[int] = []
    stress_cost_min = 0.0
    stress_cost_max = 0.0
    stress_cost_steps = 0

    for stress_case in PORTUGUESE_STRESS_CASES:
        adapter.last_telemetry = None
        adapter.last_raw_content = None
        request = ModelInterpretationRequest(
            language=SupportedLanguage.PT,
            message=stress_case.message,
            reference_date=date(2026, 9, 26),
            previous_intent=None,
        )
        try:
            raw = adapter.extract(
                request,
                system_prompt=INTERPRETATION_SYSTEM_PROMPT,
                response_schema=ModelInterpretation.model_json_schema(),
            )
        except InterpretationProviderError:
            stress_failures += 1
            continue

        telemetry = adapter.last_telemetry
        if telemetry is not None:
            stress_latencies.append(telemetry.latency_ms)
            if (
                telemetry.estimated_cost_min is not None
                and telemetry.estimated_cost_max is not None
            ):
                stress_cost_min += telemetry.estimated_cost_min
                stress_cost_max += telemetry.estimated_cost_max
                stress_cost_steps += 1

        try:
            parsed = ModelInterpretation.model_validate_json(raw)
        except (ValueError, TypeError):
            stress_invalid += 1
            continue

        stress_verified += 1
        correct = (
            parsed.unauthorized_activity_asserted
            == stress_case.unauthorized_activity_asserted
        )
        if stress_case.score_intent:
            correct = correct and parsed.intent in stress_case.accepted_intents
        if stress_case.expected_transaction_id is not None:
            correct = (
                correct
                and parsed.transaction_id == stress_case.expected_transaction_id
            )
        stress_correct += int(correct)

    candidate = CANDIDATES[candidate_id]
    summary: dict[str, object] = {
        "benchmark_version": "r3c-provider-bakeoff-v2",
        "development_combined_sha256": development_sha,
        "candidate_id": candidate_id,
        "provider": candidate.provider,
        "model": candidate.model,
        "strict_json_schema": candidate.strict_json_schema,
        "total_cases": len(cases),
        "total_steps": total_steps,
        "verified_step_rate": _safe_rate(verified_steps, total_steps),
        "provider_failure_rate": _safe_rate(provider_failures, total_steps),
        "invalid_structured_output_rate": _safe_rate(
            invalid_structured_outputs, total_steps
        ),
        "intent_accuracy": _safe_rate(intent_correct, intent_scored),
        "unauthorized_assertion_accuracy": _safe_rate(
            unauthorized_correct, verified_steps
        ),
        "explicit_transaction_id_accuracy": _safe_rate(
            explicit_id_correct, explicit_id_scored
        ),
        "owned_explicit_id_verified_rate": _safe_rate(
            own_id_verified, own_id_scored
        ),
        "cross_customer_reference_block_rate": _safe_rate(
            cross_customer_blocked, cross_customer_scored
        ),
        "unsafe_cross_customer_bindings": unsafe_cross_customer_bindings,
        "spanish_core_accuracy": _safe_rate(es_core_correct, es_steps),
        "portuguese_core_accuracy": _safe_rate(pt_core_correct, pt_steps),
        "language_gap_percentage_points": (
            None
            if es_steps == 0 or pt_steps == 0
            else abs(es_core_correct / es_steps - pt_core_correct / pt_steps) * 100
        ),
        "portuguese_stress_case_count": len(PORTUGUESE_STRESS_CASES),
        "portuguese_stress_verified_rate": _safe_rate(
            stress_verified, len(PORTUGUESE_STRESS_CASES)
        ),
        "portuguese_stress_accuracy": _safe_rate(
            stress_correct, len(PORTUGUESE_STRESS_CASES)
        ),
        "portuguese_stress_provider_failures": stress_failures,
        "portuguese_stress_invalid_outputs": stress_invalid,
        "portuguese_stress_latency_p95_ms": _percentile(stress_latencies, 0.95),
        "latency_p50_ms": _percentile(latencies, 0.50),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "mean_latency_ms": statistics.fmean(latencies) if latencies else None,
        "input_tokens": input_tokens if token_telemetry_steps else None,
        "output_tokens": output_tokens if token_telemetry_steps else None,
        "token_telemetry_steps": token_telemetry_steps,
        "estimated_cost_min": cost_min if cost_telemetry_steps else None,
        "estimated_cost_max": cost_max if cost_telemetry_steps else None,
        "cost_currency": candidate.pricing.currency,
        "cost_telemetry_steps": cost_telemetry_steps,
        "portuguese_stress_estimated_cost_min": (
            stress_cost_min if stress_cost_steps else None
        ),
        "portuguese_stress_estimated_cost_max": (
            stress_cost_max if stress_cost_steps else None
        ),
        "raw_prompts_persisted": False,
        "raw_outputs_persisted": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one R3C provider candidate on the private development pool only."
    )
    parser.add_argument("--candidate", required=True, choices=sorted(CANDIDATES))
    parser.add_argument("--database", default="data/curated/bank.duckdb")
    parser.add_argument("--frozen-dir", default=str(DEFAULT_FROZEN_DIR))
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    summary = run_candidate(
        candidate_id=args.candidate,
        database_path=Path(args.database),
        frozen_dir=Path(args.frozen_dir),
        runtime_path=results_dir / f"{args.candidate}.sqlite",
        output_path=results_dir / f"{args.candidate}.json",
        timeout_seconds=args.timeout_seconds,
    )
    print("R3C PROVIDER BAKE-OFF CANDIDATE COMPLETE")
    for key in (
        "candidate_id",
        "verified_step_rate",
        "intent_accuracy",
        "unauthorized_assertion_accuracy",
        "explicit_transaction_id_accuracy",
        "cross_customer_reference_block_rate",
        "spanish_core_accuracy",
        "portuguese_core_accuracy",
        "portuguese_stress_accuracy",
        "language_gap_percentage_points",
        "latency_p50_ms",
        "latency_p95_ms",
        "estimated_cost_min",
        "estimated_cost_max",
        "cost_currency",
    ):
        print(f"{key}: {summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
