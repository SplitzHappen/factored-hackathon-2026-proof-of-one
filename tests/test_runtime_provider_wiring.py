from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.deterministic_provider import DeterministicDemoInterpretationProvider
from app.main import create_app
from app.provider_adapters import CandidateProviderAdapter
from app.settings import Settings, load_settings


def _settings(tmp_path, provider: str = "deterministic") -> Settings:
    return Settings(
        bank_db_path=tmp_path / "demo.duckdb",
        runtime_db_path=tmp_path / "runtime.sqlite",
        data_mode="synthetic",
        interpretation_provider=provider,
    )


def test_default_runtime_uses_deterministic_interpreter(tmp_path) -> None:
    context = build_app_context(_settings(tmp_path))

    assert context.llm_connected is False
    assert isinstance(
        context.customer_service.interpreter.provider,
        DeterministicDemoInterpretationProvider,
    )


def test_settings_accept_selected_openai_provider(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_MODE", "synthetic")
    monkeypatch.setenv("BANK_DB_PATH", str(tmp_path / "demo.duckdb"))
    monkeypatch.setenv("RUNTIME_DB_PATH", str(tmp_path / "runtime.sqlite"))
    monkeypatch.setenv("INTERPRETATION_PROVIDER", "openai-gpt-6-luna")

    settings = load_settings()

    assert settings.interpretation_provider == "openai-gpt-6-luna"


def test_settings_reject_unknown_interpretation_provider(monkeypatch) -> None:
    monkeypatch.setenv("INTERPRETATION_PROVIDER", "unqualified-provider")

    with pytest.raises(ValueError, match="INTERPRETATION_PROVIDER"):
        load_settings()


def test_openai_runtime_provider_requires_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_app_context(_settings(tmp_path, provider="openai-gpt-6-luna"))


def test_openai_runtime_provider_wires_adapter_without_provider_call(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    context = build_app_context(_settings(tmp_path, provider="openai-gpt-6-luna"))

    assert context.llm_connected is True
    provider = context.customer_service.interpreter.provider
    assert isinstance(provider, CandidateProviderAdapter)
    assert provider.candidate.candidate_id == "openai-gpt-6-luna"
    assert provider.last_telemetry is None
    assert provider.last_raw_content is None


def test_health_and_readiness_surface_live_provider_configuration(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    context = build_app_context(_settings(tmp_path, provider="openai-gpt-6-luna"))
    client = TestClient(create_app(context))

    assert client.get("/health").json()["llm_connected"] is True
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["llm_connected"] is True
