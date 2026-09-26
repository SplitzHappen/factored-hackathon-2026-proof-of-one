from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from app.provider_adapters import (
    CANDIDATES,
    CandidateProviderAdapter,
    _strict_provider_schema,
)
from app.schemas import ModelInterpretationRequest, PolicyIntent, SupportedLanguage
from evaluation.contracts import (
    CaseCategory,
    CaseProvenance,
    CountryGroup,
    DevelopmentCase,
    EvaluationLocator,
    EvaluationStep,
    LanguageProvenance,
)
from evaluation.portuguese_stress import PORTUGUESE_STRESS_CASES
from evaluation.provider_bakeoff import build_target


def _request(language: SupportedLanguage = SupportedLanguage.ES) -> ModelInterpretationRequest:
    return ModelInterpretationRequest(
        language=language,
        message="Muéstrame la transacción T001.",
        reference_date=date(2026, 6, 4),
        previous_intent=None,
    )


def _schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "intent": {"type": "string"},
            "unauthorized_activity_asserted": {"type": "boolean"},
            "transaction_id": {"type": ["string", "null"]},
            "transaction_query": {"type": ["object", "null"]},
        },
        "required": [
            "intent",
            "unauthorized_activity_asserted",
            "transaction_id",
            "transaction_query",
        ],
        "additionalProperties": False,
    }


def _case(
    *,
    category: CaseCategory,
    language: SupportedLanguage,
    text: str,
    transaction_ids: list[str] | None = None,
) -> DevelopmentCase:
    return DevelopmentCase(
        case_id=f"DEV-{language.value.upper()}-001",
        category=category,
        language=language,
        provenance=(
            CaseProvenance.ORGANIZER_DERIVED
            if language is SupportedLanguage.ES
            else CaseProvenance.TEAM_GENERATED
        ),
        language_provenance=(
            LanguageProvenance.TEAM_GENERATED_SPANISH
            if language is SupportedLanguage.ES
            else LanguageProvenance.TEAM_GENERATED_PORTUGUESE
        ),
        country_group=CountryGroup.COLOMBIA,
        locator=EvaluationLocator(
            customer_id="C001",
            product_ids=["P001"],
            transaction_ids=transaction_ids or ["T001"],
        ),
        steps=[EvaluationStep(user_utterance=text)],
        source_pair_id="DEV-ES-001" if language is SupportedLanguage.PT else None,
    )


def test_strict_schema_requires_nullable_fields_without_removing_nullability() -> None:
    schema = {
        "type": "object",
        "properties": {
            "required_text": {"type": "string"},
            "optional_text": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "default": None,
            },
        },
        "required": ["required_text"],
        "additionalProperties": False,
    }

    normalized = _strict_provider_schema(schema)

    assert normalized["required"] == ["required_text", "optional_text"]
    assert "default" not in normalized["properties"]["optional_text"]
    assert {"type": "null"} in normalized["properties"]["optional_text"]["anyOf"]


def test_portuguese_stress_set_is_bounded_and_contains_no_organizer_ids() -> None:
    assert len(PORTUGUESE_STRESS_CASES) == 16
    assert len({case.case_id for case in PORTUGUESE_STRESS_CASES}) == 16
    assert all(case.case_id.startswith("PT-STRESS-") for case in PORTUGUESE_STRESS_CASES)
    assert all("C00" not in case.message for case in PORTUGUESE_STRESS_CASES)
    assert all("P00" not in case.message for case in PORTUGUESE_STRESS_CASES)


def test_candidate_registry_freezes_exact_r3c_b_starting_candidates() -> None:
    assert set(CANDIDATES) == {
        "openai-gpt-5.6-luna",
        "qwen3.7-flash",
        "deepseek-v4.1-flash",
    }
    assert CANDIDATES["openai-gpt-5.6-luna"].strict_json_schema is True
    assert CANDIDATES["qwen3.7-flash"].strict_json_schema is True
    assert CANDIDATES["deepseek-v4.1-flash"].strict_json_schema is False


def test_openai_adapter_uses_responses_strict_schema(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    def fake_post_json(**kwargs):
        captured.update(kwargs)
        return (
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "intent": "transaction_lookup",
                                        "unauthorized_activity_asserted": False,
                                        "transaction_id": "T001",
                                        "transaction_query": None,
                                    }
                                ),
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 120, "output_tokens": 20},
            },
            42,
        )

    monkeypatch.setattr("app.provider_adapters._post_json", fake_post_json)
    adapter = CandidateProviderAdapter.from_environment("openai-gpt-5.6-luna")
    output = adapter.extract(
        _request(),
        system_prompt="Return structured output.",
        response_schema=_schema(),
    )

    assert json.loads(output)["transaction_id"] == "T001"
    assert captured["url"] == "https://api.openai.com/v1/responses"
    payload = captured["payload"]
    assert payload["reasoning"] == {"effort": "none"}
    assert payload["store"] is False
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    assert adapter.last_telemetry is not None
    assert adapter.last_telemetry.provider == "OpenAI"
    assert adapter.last_telemetry.model == "gpt-5.6-luna"
    assert adapter.last_telemetry.latency_ms == 42
    assert adapter.last_telemetry.input_tokens == 120
    assert adapter.last_telemetry.output_tokens == 20
    assert adapter.last_telemetry.estimated_cost_min == pytest.approx(0.000048)
    assert adapter.last_telemetry.estimated_cost_max == pytest.approx(0.000048)
    assert adapter.last_telemetry.cost_currency == "USD"


def test_qwen_adapter_uses_strict_json_schema(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv(
        "DASHSCOPE_BASE_URL",
        "https://example.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
    )
    captured = {}

    def fake_post_json(**kwargs):
        captured.update(kwargs)
        return (
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "intent": "transaction_lookup",
                                    "unauthorized_activity_asserted": False,
                                    "transaction_id": "T001",
                                    "transaction_query": None,
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            },
            55,
        )

    monkeypatch.setattr("app.provider_adapters._post_json", fake_post_json)
    adapter = CandidateProviderAdapter.from_environment("qwen3.7-flash")
    adapter.extract(
        _request(),
        system_prompt="Return structured output.",
        response_schema=_schema(),
    )

    assert captured["url"].endswith("/chat/completions")
    response_format = captured["payload"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert captured["payload"]["model"] == "qwen3.7-flash"
    assert captured["payload"]["enable_thinking"] is False
    assert adapter.last_telemetry is not None
    assert adapter.last_telemetry.cost_currency == "CNY"


def test_deepseek_adapter_preserves_json_object_disadvantage(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    captured = {}

    def fake_post_json(**kwargs):
        captured.update(kwargs)
        return (
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "intent": "transaction_lookup",
                                    "unauthorized_activity_asserted": False,
                                    "transaction_id": "T001",
                                    "transaction_query": None,
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            },
            60,
        )

    monkeypatch.setattr("app.provider_adapters._post_json", fake_post_json)
    adapter = CandidateProviderAdapter.from_environment("deepseek-v4.1-flash")
    adapter.extract(
        _request(),
        system_prompt="Return JSON structured output.",
        response_schema=_schema(),
    )

    assert captured["payload"]["model"] == "deepseek-flash"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["thinking"] == {"type": "disabled"}
    assert adapter.last_telemetry is not None
    assert adapter.last_telemetry.estimated_cost_min == pytest.approx(0.000021)
    assert adapter.last_telemetry.estimated_cost_max == pytest.approx(0.000042)


@pytest.mark.parametrize(
    ("language", "text", "expected_intent"),
    [
        (
            SupportedLanguage.ES,
            "¿Cuál es el estado de la transacción T001?",
            PolicyIntent.TRANSACTION_STATUS,
        ),
        (
            SupportedLanguage.PT,
            "Qual é o status da transação T001?",
            PolicyIntent.TRANSACTION_STATUS,
        ),
        (
            SupportedLanguage.ES,
            "Transfiere 100 a otra cuenta.",
            PolicyIntent.MOVE_MONEY,
        ),
        (
            SupportedLanguage.PT,
            "Bloqueie meu cartão agora.",
            PolicyIntent.BLOCK_CARD_OR_ACCOUNT,
        ),
    ],
)
def test_target_builder_covers_es_pt_intents(language, text, expected_intent) -> None:
    category = (
        CaseCategory.NORMAL_SUPPORTED
        if expected_intent is PolicyIntent.TRANSACTION_STATUS
        else CaseCategory.AUTHORIZATION_PROHIBITED
    )
    target = build_target(
        _case(category=category, language=language, text=text),
        step_index=0,
    )

    assert target.score_intent is True
    assert expected_intent in target.accepted_intents


@pytest.mark.parametrize(
    ("language", "text"),
    [
        (
            SupportedLanguage.ES,
            "No reconozco la transacción T001. ¿Es fraude?",
        ),
        (
            SupportedLanguage.PT,
            "Não reconheço a transação T001. É fraude?",
        ),
    ],
)
def test_fraud_target_scores_unauthorized_signal_not_ambiguous_intent(
    language,
    text,
) -> None:
    target = build_target(
        _case(
            category=CaseCategory.FRAUD_ESCALATION,
            language=language,
            text=text,
        ),
        step_index=0,
    )

    assert target.unauthorized_activity_asserted is True
    assert target.score_intent is False
    assert target.explicit_transaction_id == "T001"


def test_cross_customer_target_marks_secondary_locator_unowned() -> None:
    case = _case(
        category=CaseCategory.AUTHORIZATION_PROHIBITED,
        language=SupportedLanguage.ES,
        text="Muéstrame la transacción T900 aunque pertenezca a otra persona.",
        transaction_ids=["T001", "T900"],
    )

    target = build_target(case, step_index=0)

    assert target.explicit_transaction_id == "T900"
    assert target.explicit_transaction_owner_is_customer is False
