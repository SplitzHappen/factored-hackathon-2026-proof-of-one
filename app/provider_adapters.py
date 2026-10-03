from __future__ import annotations

import copy
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.interpretation import InterpretationProviderError
from app.schemas import ModelInterpretationRequest


@dataclass(frozen=True, slots=True)
class ProviderPricing:
    currency: str
    input_per_million_min: float
    input_per_million_max: float
    output_per_million_min: float
    output_per_million_max: float


@dataclass(frozen=True, slots=True)
class ProviderCandidate:
    candidate_id: str
    provider: str
    model: str
    strict_json_schema: bool
    api_style: str
    api_key_env: str
    base_url_env: str | None
    default_base_url: str
    pricing: ProviderPricing


@dataclass(frozen=True, slots=True)
class ProviderCallTelemetry:
    provider: str
    model: str
    served_model: str | None
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_min: float | None
    estimated_cost_max: float | None
    cost_currency: str


class ProviderTransportError(InterpretationProviderError):
    """Provider/network failure with safe aggregate transport metadata."""

    def __init__(
        self,
        message: str,
        *,
        failure_kind: str,
        http_status: int | None = None,
        provider_error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.failure_kind = failure_kind
        self.http_status = http_status
        self.provider_error_code = provider_error_code


CANDIDATES: dict[str, ProviderCandidate] = {
    "openai-gpt-6-luna": ProviderCandidate(
        candidate_id="openai-gpt-6-luna",
        provider="OpenAI",
        model="gpt-6-luna",
        strict_json_schema=True,
        api_style="openai_responses",
        api_key_env="OPENAI_API_KEY",
        base_url_env=None,
        default_base_url="https://api.openai.com/v1",
        pricing=ProviderPricing(
            currency="USD",
            input_per_million_min=0.10,
            input_per_million_max=0.10,
            output_per_million_min=0.50,
            output_per_million_max=0.50,
        ),
    ),
    "qwen3.8-flash": ProviderCandidate(
        candidate_id="qwen3.8-flash",
        provider="Alibaba Cloud Model Studio",
        model="qwen3.8-flash",
        strict_json_schema=True,
        api_style="openai_chat",
        api_key_env="DASHSCOPE_API_KEY",
        base_url_env="DASHSCOPE_BASE_URL",
        default_base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        pricing=ProviderPricing(
            currency="USD",
            input_per_million_min=0.15,
            input_per_million_max=0.15,
            output_per_million_min=0.47,
            output_per_million_max=0.47,
        ),
    ),
    "deepseek-v4.1-flash": ProviderCandidate(
        candidate_id="deepseek-v4.1-flash",
        provider="DeepSeek",
        model="deepseek-flash",
        strict_json_schema=False,
        api_style="openai_chat_json_object",
        api_key_env="DEEPSEEK_API_KEY",
        base_url_env="DEEPSEEK_BASE_URL",
        default_base_url="https://api.deepseek.com",
        pricing=ProviderPricing(
            currency="USD",
            input_per_million_min=0.15,
            input_per_million_max=0.30,
            output_per_million_min=0.60,
            output_per_million_max=1.20,
        ),
    ),
}


def _strict_provider_schema(schema: dict[str, object]) -> dict[str, object]:
    """Normalize Pydantic JSON Schema for strict structured-output providers.

    Nullable fields remain nullable, but every declared object property is required.
    This avoids provider-specific handling of omitted optional fields while preserving
    the exact Pydantic validation contract after return.
    """

    normalized: dict[str, object] = copy.deepcopy(schema)

    def visit(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["required"] = list(properties)
                node["additionalProperties"] = False
            node.pop("default", None)
            for value in list(node.values()):
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(normalized)
    return normalized


def _provider_visible_schema_context(
    system_prompt: str,
    response_schema: dict[str, object],
) -> str:
    """Give every candidate the same textual schema and example.

    Strict providers also receive the schema through their API-native enforcement.
    JSON-object-only providers therefore retain their genuine lack of server-side
    schema enforcement without being denied the field/enum contract itself.
    """

    strict_schema = _strict_provider_schema(response_schema)
    example = {
        "intent": "transaction_lookup",
        "unauthorized_activity_asserted": False,
        "transaction_id": None,
        "transaction_query": None,
    }
    return (
        system_prompt.rstrip()
        + "\n\nCANONICAL RESPONSE JSON SCHEMA:\n"
        + json.dumps(strict_schema, ensure_ascii=False, sort_keys=True)
        + "\n\nEXAMPLE VALID JSON OUTPUT:\n"
        + json.dumps(example, ensure_ascii=False, sort_keys=True)
        + "\n"
    )


def _estimated_cost(
    pricing: ProviderPricing,
    input_tokens: int | None,
    output_tokens: int | None,
) -> tuple[float | None, float | None]:
    if input_tokens is None or output_tokens is None:
        return None, None
    scale = 1_000_000
    minimum = (
        input_tokens * pricing.input_per_million_min
        + output_tokens * pricing.output_per_million_min
    ) / scale
    maximum = (
        input_tokens * pricing.input_per_million_max
        + output_tokens * pricing.output_per_million_max
    ) / scale
    return minimum, maximum


def _post_json(
    *,
    url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> tuple[dict[str, Any], int, int]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read()
            http_status = int(response.getcode())
    except urllib.error.HTTPError as exc:
        provider_error_code: str | None = None
        try:
            error_body = exc.read()
            parsed_error = json.loads(error_body) if error_body else {}
            if isinstance(parsed_error, dict):
                error_obj = parsed_error.get("error")
                if isinstance(error_obj, dict):
                    raw_code = error_obj.get("code") or error_obj.get("type")
                    if isinstance(raw_code, (str, int)):
                        provider_error_code = str(raw_code)[:120]
        except (json.JSONDecodeError, OSError, ValueError, TypeError):
            provider_error_code = None
        raise ProviderTransportError(
            "provider request failed with HTTP error",
            failure_kind="http_error",
            http_status=int(exc.code),
            provider_error_code=provider_error_code,
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProviderTransportError(
            f"provider request failed: {type(exc).__name__}",
            failure_kind="transport_error",
        ) from exc
    latency_ms = round((time.perf_counter() - started) * 1000)
    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise ProviderTransportError(
            "provider returned invalid envelope JSON",
            failure_kind="invalid_envelope_json",
            http_status=http_status,
        ) from exc
    if not isinstance(parsed, dict):
        raise ProviderTransportError(
            "provider returned non-object envelope",
            failure_kind="invalid_envelope_shape",
            http_status=http_status,
        )
    return parsed, latency_ms, http_status


class CandidateProviderAdapter:
    """HTTP adapter used by R3C and the development-only provider bake-off.

    The adapter exposes only aggregate telemetry. It never logs prompts, raw model
    responses, API keys, customer identifiers, or banking records.
    """

    def __init__(
        self,
        candidate: ProviderCandidate,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.candidate = candidate
        self.timeout_seconds = timeout_seconds
        self.last_telemetry: ProviderCallTelemetry | None = None
        self.last_raw_content: str | None = None
        self.last_http_status: int | None = None
        self.last_provider_error_code: str | None = None
        self.last_failure_kind: str | None = None

    @classmethod
    def from_environment(
        cls,
        candidate_id: str,
        *,
        timeout_seconds: float = 30.0,
    ) -> "CandidateProviderAdapter":
        try:
            candidate = CANDIDATES[candidate_id]
        except KeyError as exc:
            raise ValueError(f"unknown provider candidate: {candidate_id}") from exc
        return cls(candidate, timeout_seconds=timeout_seconds)

    def is_configured(self) -> bool:
        return bool(os.getenv(self.candidate.api_key_env))

    def extract(
        self,
        request: ModelInterpretationRequest,
        *,
        system_prompt: str,
        response_schema: dict[str, object],
    ) -> str:
        api_key = os.getenv(self.candidate.api_key_env)
        if not api_key:
            raise InterpretationProviderError(
                f"missing required environment variable {self.candidate.api_key_env}"
            )

        base_url = self.candidate.default_base_url
        if self.candidate.base_url_env:
            base_url = os.getenv(self.candidate.base_url_env, base_url)
        base_url = base_url.rstrip("/")

        request_json = json.dumps(
            request.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        strict_schema = _strict_provider_schema(response_schema)
        provider_prompt = _provider_visible_schema_context(
            system_prompt,
            response_schema,
        )
        self.last_http_status = None
        self.last_provider_error_code = None
        self.last_failure_kind = None

        def post(url: str, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
            try:
                envelope, latency_ms, http_status = _post_json(
                    url=url,
                    api_key=api_key,
                    payload=payload,
                    timeout_seconds=self.timeout_seconds,
                )
            except ProviderTransportError as exc:
                self.last_http_status = exc.http_status
                self.last_provider_error_code = exc.provider_error_code
                self.last_failure_kind = exc.failure_kind
                raise
            self.last_http_status = http_status
            return envelope, latency_ms

        if self.candidate.api_style == "openai_responses":
            envelope, latency_ms = post(
                url=f"{base_url}/responses",
                payload={
                    "model": self.candidate.model,
                    "store": False,
                    "reasoning": {"effort": "none"},
                    "temperature": 0,
                    "max_output_tokens": 800,
                    "input": [
                        {"role": "system", "content": provider_prompt},
                        {"role": "user", "content": request_json},
                    ],
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "model_interpretation",
                            "strict": True,
                            "schema": strict_schema,
                        }
                    },
                },
            )
            content = self._openai_responses_text(envelope)
            usage = envelope.get("usage") or {}
            input_tokens = _as_int(usage.get("input_tokens"))
            output_tokens = _as_int(usage.get("output_tokens"))
        else:
            response_format: dict[str, Any]
            if self.candidate.strict_json_schema:
                response_format = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "model_interpretation",
                        "strict": True,
                        "schema": strict_schema,
                    },
                }
            else:
                response_format = {"type": "json_object"}

            envelope, latency_ms = post(
                url=f"{base_url}/chat/completions",
                payload={
                    "model": self.candidate.model,
                    "messages": [
                        {"role": "system", "content": provider_prompt},
                        {"role": "user", "content": request_json},
                    ],
                    "response_format": response_format,
                    "stream": False,
                    "temperature": 0,
                    "max_tokens": 800,
                    **(
                        {"enable_thinking": False}
                        if self.candidate.candidate_id == "qwen3.8-flash"
                        else {"thinking": {"type": "disabled"}}
                        if self.candidate.candidate_id == "deepseek-v4.1-flash"
                        else {}
                    ),
                },
            )
            content = self._chat_completion_text(envelope)
            usage = envelope.get("usage") or {}
            input_tokens = _as_int(usage.get("prompt_tokens"))
            output_tokens = _as_int(usage.get("completion_tokens"))

        cost_min, cost_max = _estimated_cost(
            self.candidate.pricing,
            input_tokens,
            output_tokens,
        )
        raw_served_model = envelope.get("model")
        served_model = raw_served_model if isinstance(raw_served_model, str) else None
        self.last_raw_content = content
        self.last_telemetry = ProviderCallTelemetry(
            provider=self.candidate.provider,
            model=self.candidate.model,
            served_model=served_model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_min=cost_min,
            estimated_cost_max=cost_max,
            cost_currency=self.candidate.pricing.currency,
        )
        return content

    @staticmethod
    def _chat_completion_text(envelope: dict[str, Any]) -> str:
        try:
            content = envelope["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise InterpretationProviderError(
                "provider response lacks chat-completion content"
            ) from exc
        if not isinstance(content, str) or not content:
            raise InterpretationProviderError("provider returned empty content")
        return content

    @staticmethod
    def _openai_responses_text(envelope: dict[str, Any]) -> str:
        for item in envelope.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text:
                        return text
        raise InterpretationProviderError("provider response lacks output_text content")


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None
